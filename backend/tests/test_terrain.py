"""Tests for MARS-X planetary geodesy, terrain processing, and raster ingestion."""

import os
import math
import tempfile
import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.geospatial import (
    is_valid_mars_crs,
    planetocentric_to_planetographic,
    planetographic_to_planetocentric,
    compute_mars_ground_resolution,
    normalize_east_longitude,
    MARS_EQUATORIAL_RADIUS_M,
    MARS_POLAR_RADIUS_M,
)
from app.terrain.crs_validator import (
    validate_and_identify_crs,
    PlanetaryCRSValidationError,
)
from app.terrain.processor import (
    create_valid_data_mask,
    calculate_slope_grid,
    calculate_terrain_roughness,
    compute_latitudinal_metric_spacing,
)
from app.terrain.raster_inspector import inspect_raster_file
from app.terrain.provenance import (
    list_terrain_datasets,
    get_terrain_dataset_coverage,
    get_terrain_dataset_summary,
)
from app.terrain.elevation_service import TerrainDataEngine


# ── 1. Planetary CRS Validation ─────────────────────────────────────────────

def test_crs_validation_mars_sphere():
    """Verify IAU 2000 / 2015 Mars sphere codes are recognized."""
    res_2000 = validate_and_identify_crs("IAU:49900")
    assert res_2000["is_valid_mars"] is True
    assert res_2000["semi_major_axis_m"] == MARS_EQUATORIAL_RADIUS_M

    res_2015 = validate_and_identify_crs("IAU_2015:49900")
    assert res_2015["is_valid_mars"] is True


def test_crs_validation_mars_equirectangular_and_alias():
    """Verify ESRI:104905 and Mars Trek alias EPSG:104905."""
    res_esri = validate_and_identify_crs("ESRI:104905")
    assert res_esri["is_valid_mars"] is True

    res_alias = validate_and_identify_crs("EPSG:104905")
    assert res_alias["is_valid_mars"] is True


def test_crs_strict_rejection_earth_web_mercator():
    """Strictly reject Earth EPSG:3857 to prevent invalid distortion."""
    with pytest.raises(PlanetaryCRSValidationError):
        validate_and_identify_crs("EPSG:3857")

    with pytest.raises(PlanetaryCRSValidationError):
        validate_and_identify_crs("urn:ogc:def:crs:EPSG::3857")


# ── 2. Geodetic Coordinate Transformations ─────────────────────────────────

def test_planetocentric_planetographic_conversion():
    """Verify planetocentric to planetographic latitude conversion."""
    # Equator and poles must be invariant
    assert planetocentric_to_planetographic(0.0) == 0.0
    assert planetocentric_to_planetographic(90.0) == 90.0
    assert planetocentric_to_planetographic(-90.0) == -90.0

    # At 45 deg planetocentric, planetographic should be ~45.34 deg on Mars (0.34 deg difference)
    lat_g = planetocentric_to_planetographic(45.0)
    diff = lat_g - 45.0
    assert 0.30 <= diff <= 0.38, f"Expected ~0.34 deg shift on Mars ellipsoid; got {diff}"

    # Round trip should match original
    lat_c_back = planetographic_to_planetocentric(lat_g)
    assert math.isclose(lat_c_back, 45.0, abs_tol=1e-6)


def test_positive_east_longitude_normalization():
    """Verify positive East [0, 360) normalization."""
    assert normalize_east_longitude(0.0) == 0.0
    assert normalize_east_longitude(359.5) == 359.5
    assert normalize_east_longitude(-10.0) == 350.0
    assert normalize_east_longitude(370.0) == 10.0


def test_latitudinal_metric_ground_resolution():
    """Verify physical ground distance scaling with cos(latitude)."""
    # At equator (lat=0), dx for 1 degree
    dx_eq, dy_eq = compute_mars_ground_resolution(0.0, 1.0, 1.0)
    expected_dx_eq = (math.pi * MARS_EQUATORIAL_RADIUS_M) / 180.0
    assert math.isclose(dx_eq, expected_dx_eq, rel_tol=1e-4)

    # At 60 deg N, east-west dx must be halved (cos(60) = 0.5)
    dx_60, dy_60 = compute_mars_ground_resolution(60.0, 1.0, 1.0)
    assert math.isclose(dx_60, dx_eq * 0.5, rel_tol=1e-3)
    # North-south spacing remains constant
    assert math.isclose(dy_60, dy_eq, rel_tol=1e-3)


# ── 3. NoData and Valid-Data Mask Handling ──────────────────────────────────

def test_create_valid_data_mask_filters_nodata_and_outliers():
    """Ensure -32768, NaN, and unphysical values are excluded from valid mask."""
    data = np.array([
        [-32768.0, 100.0, 200.0],
        [np.nan, 500.0, -99999.0],  # -99999 is unphysical
        [1500.0, 30000.0, -500.0],  # 30000 is beyond Olympus Mons summit
    ], dtype=np.float32)

    mask = create_valid_data_mask(data, nodata_value=-32768.0)
    assert mask[0, 0] is np.False_  # -32768 excluded
    assert mask[0, 1] is np.True_   # 100 valid
    assert mask[0, 2] is np.True_   # 200 valid
    assert mask[1, 0] is np.False_  # NaN excluded
    assert mask[1, 1] is np.True_   # 500 valid
    assert mask[1, 2] is np.False_  # -99999 excluded
    assert mask[2, 0] is np.True_   # 1500 valid
    assert mask[2, 1] is np.False_  # 30000 excluded
    assert mask[2, 2] is np.True_   # -500 valid (valid depression)


# ── 4. Slope Calculation & Scientific Safeguards ───────────────────────────

def test_slope_never_treats_nodata_as_safe_terrain():
    """CRITICAL: If any neighbor in stencil is NoData, slope output MUST be NaN."""
    elevation = np.array([
        [100.0, 100.0, 100.0],
        [100.0, 100.0, -32768.0],  # Missing cell on right edge
        [100.0, 100.0, 100.0],
    ], dtype=np.float32)

    valid_mask = create_valid_data_mask(elevation, nodata_value=-32768.0)
    slope_deg, valid_slope_mask = calculate_slope_grid(
        elevation=elevation,
        dx_m=100.0,
        dy_m=100.0,
        valid_mask=valid_mask,
    )

    # Center cell (1, 1) has an invalid neighbor at (1, 2)
    # Output slope MUST be NaN, NOT a false vertical cliff or zero
    assert np.isnan(slope_deg[1, 1])
    assert valid_slope_mask[1, 1] is np.False_


def test_slope_on_flat_plain_is_zero():
    """Flat 5x5 terrain must yield 0 deg slope on all interior cells."""
    elevation = np.full((5, 5), 120.0, dtype=np.float32)
    slope_deg, valid_slope_mask = calculate_slope_grid(
        elevation=elevation,
        dx_m=50.0,
        dy_m=50.0,
    )

    interior_slopes = slope_deg[1:4, 1:4]
    assert np.allclose(interior_slopes, 0.0, atol=1e-5)
    assert np.all(valid_slope_mask[1:4, 1:4])


def test_slope_on_uniform_ramp():
    """Uniform incline dz/dx = 0.5 must yield slope = arctan(0.5) ~ 26.565 deg."""
    dx = 10.0
    dy = 10.0
    # Elevation rises by 5m per 10m column (gradient = 0.5)
    elevation = np.array([
        [0.0, 5.0, 10.0, 15.0],
        [0.0, 5.0, 10.0, 15.0],
        [0.0, 5.0, 10.0, 15.0],
        [0.0, 5.0, 10.0, 15.0],
    ], dtype=np.float32)

    slope_deg, valid_slope_mask = calculate_slope_grid(
        elevation=elevation,
        dx_m=dx,
        dy_m=dy,
    )

    expected_deg = math.degrees(math.atan(0.5))  # ~26.565 deg
    assert np.isclose(slope_deg[1, 1], expected_deg, atol=1e-2)
    assert np.isclose(slope_deg[2, 2], expected_deg, atol=1e-2)


# ── 5. Rasterio Metadata Inspection & Synthetic GeoTIFF ────────────────────

def test_raster_metadata_inspection_with_synthetic_geotiff():
    """Create a temporary Mars GeoTIFF and verify Rasterio metadata inspection."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        width, height = 20, 20
        # 128 px/deg resolution on Mars: ~0.0078125 deg
        res_deg = 1.0 / 128.0
        transform = from_origin(0.0, 10.0, res_deg, res_deg)
        nodata_val = -32768.0

        # Mars 2000 Sphere PROJ string
        mars_crs = rasterio.crs.CRS.from_proj4("+proj=longlat +a=3396190 +b=3396190 +no_defs")

        synthetic_elevation = np.full((1, height, width), 250.0, dtype=np.int16)
        # Add a crater depression in center
        synthetic_elevation[0, 8:12, 8:12] = -150
        # Add some NoData values in corner
        synthetic_elevation[0, 0:2, 0:2] = int(nodata_val)

        with rasterio.open(
            tmp_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="int16",
            crs=mars_crs,
            transform=transform,
            nodata=nodata_val,
        ) as dst:
            dst.write(synthetic_elevation)

        # Inspect using MARS-X raster inspector
        meta = inspect_raster_file(tmp_path, dataset_id="synthetic-mola-test")

        assert meta.dataset_id == "synthetic-mola-test"
        assert meta.width == width
        assert meta.height == height
        assert meta.band_count == 1
        assert meta.nodata_value == nodata_val
        assert meta.dtype == "int16"
        assert meta.is_mars_crs is True
        assert meta.resolution.pixel_width == pytest.approx(res_deg, rel=1e-4)
        assert meta.resolution.metric_spacing_equator_m == pytest.approx(463.08, abs=1.0)
        assert meta.bounds.min_x == 0.0
        assert meta.bounds.max_y == 10.0

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_raster_inspection_missing_file_raises_error():
    """Verify that a non-existent raster file path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        inspect_raster_file("E:/MARS-X/data/raw/non_existent_raster.tif")


# ── 6. Dataset Provenance and Coverage Registry ────────────────────────────

def test_terrain_provenance_registry_contains_4_core_products():
    """Verify MOLA, HRSC, HiRISE, and CTX numerical DTMs are registered."""
    datasets = list_terrain_datasets()
    ids = [d.dataset_id for d in datasets]
    assert "mola-megdr" in ids
    assert "hrsc-dtm" in ids
    assert "hirise-dtm" in ids
    assert "ctx-dtm" in ids

    for d in datasets:
        assert d.is_numerical_dtm is True
        assert "MOLA Areoid" in d.elevation_unit


def test_terrain_coverage_retrieval():
    """Verify global vs regional coverage footprints."""
    mola_cov = get_terrain_dataset_coverage("mola-megdr")
    assert mola_cov is not None
    assert mola_cov.is_global is True
    assert mola_cov.lat_min == -88.0
    assert mola_cov.lat_max == 88.0
    assert mola_cov.total_area_approx_pct > 95.0

    hirise_cov = get_terrain_dataset_coverage("hirise-dtm")
    assert hirise_cov is not None
    assert hirise_cov.is_global is False
    assert hirise_cov.total_area_approx_pct < 1.0


# ── 7. Elevation Point Query Zero-Fabrication Enforcement ──────────────────

def test_elevation_point_query_unloaded_dataset_refuses_fabrication():
    """Engine must honestly report that un-downloaded datasets cannot return fake elevation."""
    test_engine = TerrainDataEngine()
    from app.terrain.models import ElevationPointQuery

    query = ElevationPointQuery(latitude=18.38, longitude=77.58, dataset_id="hrsc-dtm")
    res = test_engine.query_elevation_point(query)

    assert res.is_valid is False
    assert res.elevation_m is None
    assert "not yet downloaded" in res.status_note

