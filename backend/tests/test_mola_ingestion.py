"""Validation tests for real MOLA MEGDR sample acquisition, ingestion, and processing."""

import os
import json
import pytest
import numpy as np
import rasterio

from app.terrain.pds_parser import PDS3LabelParser, read_pds3_image_binary
from app.terrain.raster_inspector import inspect_raster_file
from app.terrain.ingestion import compute_sha256
from app.terrain.elevation_service import TerrainDataEngine
from app.terrain.models import ElevationPointQuery

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "mola"))

LBL_PATH = os.path.join(RAW_DIR, "megt90n000cb.lbl")
IMG_PATH = os.path.join(RAW_DIR, "megt90n000cb.img")
PROV_PATH = os.path.join(RAW_DIR, "megt90n000cb_provenance.json")

ELEV_COG_PATH = os.path.join(PROC_DIR, "mola_megt90n000cb_elevation.tif")
SLOPE_COG_PATH = os.path.join(PROC_DIR, "mola_megt90n000cb_slope.tif")
ROUGH_COG_PATH = os.path.join(PROC_DIR, "mola_megt90n000cb_roughness.tif")


@pytest.mark.skipif(not os.path.exists(LBL_PATH), reason="MOLA raw sample not downloaded")
def test_real_mola_pds_label_parsing():
    """Verify programmatic parsing of official NASA PDS3 label megt90n000cb.lbl."""
    lbl = PDS3LabelParser.parse_label_file(LBL_PATH)

    assert lbl["DATA_SET_ID"] == "MGS-M-MOLA-5-MEGDR-L3-V1.0"
    assert lbl["PRODUCT_ID"] == "MEGT90N000CB.IMG"
    assert lbl["RECORD_TYPE"] == "FIXED_LENGTH"
    assert int(lbl["RECORD_BYTES"]) == 2880

    image_obj = lbl["IMAGE"]
    assert int(image_obj["LINES"]) == 720
    assert int(image_obj["LINE_SAMPLES"]) == 1440
    assert int(image_obj["SAMPLE_BITS"]) == 16
    assert image_obj["SAMPLE_TYPE"] == "MSB_INTEGER"
    assert image_obj["UNIT"] == "METER"

    proj_obj = lbl["IMAGE_MAP_PROJECTION"]
    assert proj_obj["MAP_PROJECTION_TYPE"] == "SIMPLE CYLINDRICAL"
    assert float(proj_obj["MAP_RESOLUTION"]) == 4.0
    assert float(proj_obj["MAXIMUM_LATITUDE"]) == 90.0
    assert float(proj_obj["MINIMUM_LATITUDE"]) == -90.0
    assert float(proj_obj["WESTERNMOST_LONGITUDE"]) == 0.0
    assert float(proj_obj["EASTERNMOST_LONGITUDE"]) == 360.0


@pytest.mark.skipif(not os.path.exists(IMG_PATH), reason="MOLA raw sample not downloaded")
def test_real_mola_binary_reading_and_elevation_ranges():
    """Read binary .img and verify authentic Martian topography bounds."""
    lbl = PDS3LabelParser.parse_label_file(LBL_PATH)
    arr, meta = read_pds3_image_binary(IMG_PATH, lbl)

    assert arr.shape == (720, 1440)
    assert arr.dtype == np.float32

    # Verify physical Mars elevation extrema:
    # Minimum must be deep depression in Hellas Basin (~ -8 km)
    # Maximum must be peak of Olympus Mons (~ +21 km)
    min_elev = float(np.min(arr))
    max_elev = float(np.max(arr))

    assert -8500.0 <= min_elev <= -7500.0, f"Expected Hellas basin floor ~ -8km; got {min_elev}m"
    assert 20000.0 <= max_elev <= 22000.0, f"Expected Olympus Mons peak ~ +21km; got {max_elev}m"


@pytest.mark.skipif(not os.path.exists(PROV_PATH), reason="MOLA provenance missing")
def test_real_mola_provenance_and_checksum_integrity():
    """Verify SHA-256 checksums recorded in provenance match raw files on disk."""
    with open(PROV_PATH, "r", encoding="utf-8") as f:
        prov = json.load(f)

    lbl_sha_expected = prov["files"]["label"]["sha256"]
    img_sha_expected = prov["files"]["image"]["sha256"]

    assert compute_sha256(LBL_PATH) == lbl_sha_expected
    assert compute_sha256(IMG_PATH) == img_sha_expected


@pytest.mark.skipif(not os.path.exists(ELEV_COG_PATH), reason="Processed COGs missing")
def test_real_mola_elevation_cog_inspection():
    """Verify generated Cloud Optimized GeoTIFF using Rasterio."""
    meta = inspect_raster_file(ELEV_COG_PATH, dataset_id="mola-megdr-sample")

    assert meta.driver == "GTiff"
    assert meta.width == 1440
    assert meta.height == 720
    assert meta.band_count == 1
    assert meta.nodata_value == -32768.0
    assert meta.is_mars_crs is True
    assert meta.bounds.min_x == 0.0
    assert meta.bounds.max_x == 360.0
    assert meta.bounds.min_y == -90.0
    assert meta.bounds.max_y == 90.0
    assert pytest.approx(meta.resolution.pixel_width, 1e-4) == 0.25
    assert pytest.approx(meta.resolution.pixel_height, 1e-4) == 0.25

    with rasterio.open(ELEV_COG_PATH) as src:
        # Verify internal overviews exist for COG
        assert len(src.overviews(1)) >= 2, "COG should have at least 2 overview levels"
        assert src.is_tiled is True


@pytest.mark.skipif(not os.path.exists(SLOPE_COG_PATH), reason="Slope COG missing")
def test_real_mola_slope_and_roughness_products():
    """Verify generated slope and roughness products."""
    with rasterio.open(SLOPE_COG_PATH) as src_slope:
        slope_data = src_slope.read(1)
        valid_slopes = slope_data[slope_data != -32768.0]
        assert len(valid_slopes) > 0
        # Slopes must be non-negative and realistic
        assert np.min(valid_slopes) >= 0.0
        assert np.max(valid_slopes) < 60.0

    with rasterio.open(ROUGH_COG_PATH) as src_rough:
        rough_data = src_rough.read(1)
        valid_rough = rough_data[rough_data != -32768.0]
        assert len(valid_rough) > 0
        assert np.min(valid_rough) >= 0.0


@pytest.mark.skipif(not os.path.exists(ELEV_COG_PATH), reason="Processed COGs missing")
def test_real_mola_elevation_point_sampling():
    """Query real elevation at known Martian landmarks."""
    engine = TerrainDataEngine()
    engine.register_local_raster("mola-megdr", ELEV_COG_PATH)

    # 1. Olympus Mons Caldera (~18.65°N, 226.2°E)
    olympus_query = ElevationPointQuery(latitude=18.65, longitude=226.2, dataset_id="mola-megdr")
    olympus_res = engine.query_elevation_point(olympus_query)
    assert olympus_res.is_valid is True
    assert olympus_res.elevation_m is not None
    assert olympus_res.elevation_m > 16000.0, f"Olympus Mons should be >16,000m; got {olympus_res.elevation_m}"

    # 2. Hellas Planitia floor (~ -42°N, 70°E)
    hellas_query = ElevationPointQuery(latitude=-42.0, longitude=70.0, dataset_id="mola-megdr")
    hellas_res = engine.query_elevation_point(hellas_query)
    assert hellas_res.is_valid is True
    assert hellas_res.elevation_m is not None
    assert hellas_res.elevation_m < -5000.0, f"Hellas floor should be <-5,000m; got {hellas_res.elevation_m}"

