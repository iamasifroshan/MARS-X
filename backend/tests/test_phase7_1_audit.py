"""Phase 7.1 Independent Scientific Data Audit Test Suite.

Verifies:
1. MOLA 128 ppd checksums, PDS label parameters, and zero-median boundary continuity.
2. CTX GeoTIFF physical properties, affine transform, and resolution of the area discrepancy.
3. Horizontal CRS planetary sphere radius differences (3,396,000 m vs 3,396,190 m).
4. Vertical datum classification and Ames Stereo Pipeline pc_align evidence assessment.
5. Cross-resolution elevation validation reproducibility (Method A and Method B) and sign convention.
6. HiRISE lifecycle state enforcement (discovered, zero local raster bytes).
"""

import os
import math
import hashlib
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

from app.main import app
from app.geospatial import MARS_EQUATORIAL_RADIUS_M
from app.terrain.multi_resolution import MultiResolutionTerrainCatalog
from app.terrain.harmonization import VERTICAL_EVIDENCE_CATALOG, VerticalCompatibilityStatus
from app.terrain.validation import DatasetValidationRegistry
from app.routing.grid_builder import TerrainGridBuilder


@pytest.fixture
def client():
    return TestClient(app)


def recompute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ── 1. MOLA 128 ppd Checksums, Labels & Boundary Continuity ──────────────────

def test_mola_physical_checksums():
    """Verify bit-for-bit SHA-256 hashes of all three acquired MOLA 128 raw tiles."""
    expected = {
        "megt00n000hb.img": (129761280, "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"),
        "megt44n000hb.img": (129761280, "14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36"),
        "megt00n090hb.img": (129761280, "764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e"),
    }
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    for fname, (expected_size, expected_hash) in expected.items():
        p = os.path.join(raw_dir, fname)
        assert os.path.exists(p), f"Missing file: {fname}"
        assert os.path.getsize(p) == expected_size
        assert recompute_sha256(p) == expected_hash


def test_mola_pds_labels_parameters():
    """Verify PDS label parameters independently across all three tiles."""
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    for tid in ["megt00n000hb", "megt44n000hb", "megt00n090hb"]:
        lbl_path = os.path.join(raw_dir, f"{tid}.lbl")
        assert os.path.exists(lbl_path)
        with open(lbl_path, "r") as f:
            props = {}
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip().strip('"')
            assert props.get("FILE_RECORDS") == "5632"
            assert props.get("RECORD_BYTES") == "23040"
            assert props.get("SAMPLE_BITS") == "16"
            assert props.get("SAMPLE_TYPE") == "MSB_INTEGER"
            assert props.get("MAP_PROJECTION_TYPE") == "SIMPLE CYLINDRICAL"
            assert "3396.0" in props.get("A_AXIS_RADIUS", "")
            assert "128.0" in props.get("MAP_RESOLUTION", "")


def test_mola_equator_boundary_continuity():
    """Verify continuity along Equator seam (megt44n000hb line 5631 vs megt00n000hb line 0)."""
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    p_44n = os.path.join(raw_dir, "megt44n000hb.img")
    p_00n = os.path.join(raw_dir, "megt00n000hb.img")

    t_44n = np.memmap(p_44n, dtype=">i2", mode="r", shape=(5632, 11520))
    t_00n = np.memmap(p_00n, dtype=">i2", mode="r", shape=(5632, 11520))

    diff = t_44n[5631, :].astype(float) - t_00n[0, :].astype(float)
    # Median difference across all 11,520 columns must be exactly 0.0 m (no datum shift)
    assert np.median(diff) == 0.0
    # Mean slope across equator must be gentle natural terrain (< 5.0 deg)
    mean_slope_deg = np.degrees(np.arctan(np.mean(np.abs(diff)) / 463.08))
    assert mean_slope_deg < 5.0


def test_mola_meridian_boundary_continuity():
    """Verify continuity along 90°E Meridian seam (megt00n000hb column 11519 vs megt00n090hb column 0)."""
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    p_000 = os.path.join(raw_dir, "megt00n000hb.img")
    p_090 = os.path.join(raw_dir, "megt00n090hb.img")

    t_000 = np.memmap(p_000, dtype=">i2", mode="r", shape=(5632, 11520))
    t_090 = np.memmap(p_090, dtype=">i2", mode="r", shape=(5632, 11520))

    diff = t_090[:, 0].astype(float) - t_000[:, 11519].astype(float)
    # Median difference across all 5,632 rows must be exactly 0.0 m (no step discontinuity)
    assert np.median(diff) == 0.0
    assert np.mean(np.abs(diff)) < 25.0


# ── 2. CTX GeoTIFF Validation & Area Discrepancy Resolution ──────────────────

def test_ctx_physical_checksum_and_properties():
    """Verify CTX file integrity, float32 format, IAU:49910 CRS, and valid pixel counts."""
    ctx_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "raw",
            "ctx",
            "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
        )
    )
    assert os.path.exists(ctx_path)
    assert os.path.getsize(ctx_path) == 12734013
    assert recompute_sha256(ctx_path) == "a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2"

    with rasterio.open(ctx_path) as src:
        assert src.width == 1692
        assert src.height == 3472
        assert src.dtypes[0] == "float32"
        assert src.nodata == -32767.0
        assert abs(src.res[0] - 20.0128) < 0.01
        assert "49910" in src.crs.to_string() or "Equirectangular" in src.crs.to_string()

        arr = src.read(1, masked=True)
        valid = arr.compressed()
        # Verified valid pixel count is exactly 4,281,370 (54 isolated internal NoData pixels)
        assert len(valid) == 4281370
        assert abs(valid.min() - 797.6) < 1.0
        assert abs(valid.max() - 2514.3) < 1.0


def test_ctx_area_calculations_and_discrepancy_resolution():
    """Resolve the critical area discrepancy between grid, spherical, and valid pixel areas."""
    ctx_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "raw",
            "ctx",
            "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
        )
    )
    with rasterio.open(ctx_path) as src:
        dx_m = src.bounds.right - src.bounds.left
        dy_m = src.bounds.top - src.bounds.bottom
        grid_area_km2 = (dx_m * dy_m) / 1e6

        # 1. Projected grid area ~2352.87 km²
        assert 2350.0 < grid_area_km2 < 2355.0

        # 2. Valid data area (4.28M pixels * 20.0128^2) ~1714.77 km²
        valid_px_count = 4281424
        valid_data_area_km2 = (valid_px_count * (src.res[0] * src.res[1])) / 1e6
        assert 1710.0 < valid_data_area_km2 < 1720.0

    # 3. Spherical bounding box area calculated by MultiResolutionTerrainCatalog
    catalog = MultiResolutionTerrainCatalog()
    overlap = catalog.calculate_product_overlap("mola-megdr-128", "ctx-dtm-p21-009323")
    assert overlap.has_overlap is True
    # Spherical bounding box is 2410.1 km², NOT 3889.3 km²
    assert 2408.0 < overlap.overlap_area_km2 < 2412.0
    assert overlap.overlap_area_km2 != 3889.3


# ── 3. Horizontal CRS Scale Analysis ─────────────────────────────────────────

def test_horizontal_crs_radius_discrepancy():
    """Verify geodetic scaling discrepancy resulting from ΔR = 190 m between MOLA and IAU:49910."""
    r_mola = 3396000.0
    r_iau = 3396190.0
    delta_r = r_iau - r_mola
    assert delta_r == 190.0

    # Scale difference ~55.95 ppm
    ppm = (delta_r / r_mola) * 1e6
    assert 55.0 < ppm < 57.0

    # Arc length per degree difference
    d_mola = (math.pi / 180.0) * r_mola
    d_iau = (math.pi / 180.0) * r_iau
    diff_per_deg_m = d_iau - d_mola
    assert abs(diff_per_deg_m - 3.316) < 0.01

    # Over the CTX swath latitude span (1.184 deg), linear shift is ~3.93 m (< 0.2 CTX pixel)
    delta_lat_deg = 1.18425
    total_lat_scaling_m = delta_lat_deg * diff_per_deg_m
    assert total_lat_scaling_m < 4.0  # Well below CTX 20.01 m pixel resolution


# ── 4. Vertical Datum Classification & Evidence ──────────────────────────────

def test_vertical_datum_evidence_classification():
    """Verify that CTX DTM is classified as compatible_with_documented_transformation with no arbitrary offsets."""
    record = VERTICAL_EVIDENCE_CATALOG.get("ctx-dtm-p21-009323")
    assert record is not None
    assert record.compatibility_status == VerticalCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION
    # Measured offset must be None to prevent arbitrary additive shifting
    assert record.measured_offset_m is None
    assert "Ames Stereo Pipeline" in record.original_vertical_reference
    assert "pc_align" in record.adjustment_procedure


# ── 5. Cross-Resolution Numerical Comparison & Sign Convention ───────────────

def test_cross_resolution_point_sampling_and_sign_convention():
    """Verify Method A point sampling produces consistent negative delta (z_CTX - z_MOLA < 0)."""
    catalog = MultiResolutionTerrainCatalog()
    res = catalog.compare_overlapping_rasters("mola-megdr-128", "ctx-dtm-p21-009323", sample_grid_dim=15)

    assert res.sample_points_count > 100
    assert 1950.0 < res.mean_elevation_b_m < 2050.0  # CTX ~1996m
    assert 2000.0 < res.mean_elevation_a_m < 2100.0  # MOLA ~2054m
    # Crucial sign convention check: CTX is deeper in craters than MOLA -> negative delta
    assert -70.0 < res.mean_delta_m < -45.0
    assert 35.0 < res.std_delta_m < 65.0


def test_cross_resolution_common_support_aggregation():
    """Verify Method B: aggregating CTX pixels into MOLA footprints matches point sampling mean delta."""
    builder = TerrainGridBuilder()
    ctx_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "raw",
            "ctx",
            "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
        )
    )

    diffs = []
    with rasterio.open(ctx_path) as src:
        # Sample across a sparse grid of MOLA cells (step=4)
        for m_line in range(540, 640, 4):
            for m_samp in range(8470, 8510, 4):
                mola_val = float(builder._memmap[m_line, m_samp])
                if mola_val == -32768:
                    continue
                cell_lat = -(m_line + 0.5) / 128.0
                cell_lon = (m_samp + 0.5) / 128.0
                half_deg = 0.5 / 128.0

                x_min = (cell_lon - half_deg) * (3396190.0 * np.pi / 180.0)
                x_max = (cell_lon + half_deg) * (3396190.0 * np.pi / 180.0)
                y_min = (cell_lat - half_deg) * (3396190.0 * np.pi / 180.0)
                y_max = (cell_lat + half_deg) * (3396190.0 * np.pi / 180.0)

                r_top, c_left = src.index(x_min, y_max)
                r_bot, c_right = src.index(x_max, y_min)
                r_start, r_end = max(min(r_top, r_bot), 0), min(max(r_top, r_bot), src.height)
                c_start, c_end = max(min(c_left, c_right), 0), min(max(c_left, c_right), src.width)

                if r_end > r_start and c_end > c_start:
                    sub = src.read(1, window=((r_start, r_end), (c_start, c_end)), masked=True)
                    valid = sub.compressed()
                    if len(valid) >= 50:
                        diffs.append(float(np.mean(valid)) - mola_val)

    assert len(diffs) > 50
    mean_agg_diff = float(np.mean(diffs))
    # Aggregated cell delta must also be negative and consistent with point sampling
    assert -70.0 < mean_agg_diff < -45.0


# ── 6. HiRISE Lifecycle & Zero-Byte Enforcement ──────────────────────────────

def test_hirise_lifecycle_and_zero_local_raster():
    """Verify that HiRISE products have no local raster files and maintain discovered state."""
    hirise_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "hirise")
    )
    # Directory must not exist or be empty
    assert not os.path.exists(hirise_dir) or len(os.listdir(hirise_dir)) == 0

    catalog = MultiResolutionTerrainCatalog()
    for hid in ["hirise-dtm-schiaparelli", "hirise-dtm-jezero"]:
        prod = catalog.get_product(hid)
        assert prod is not None
        assert prod.status in ["catalogued", "discovered"]

        rep = DatasetValidationRegistry.get_report(hid)
        assert rep is not None
        assert rep.raster_available_locally is False
        assert rep.lifecycle_state == "discovered"
        assert rep.is_analysis_ready is False


def test_api_hirise_compare_guard(client):
    """Verify API prevents comparing unavailable HiRISE rasters."""
    resp = client.get(
        "/api/v1/terrain/compare-products?product_a=mola-megdr-128&product_b=hirise-dtm-schiaparelli&run_raster_analysis=true"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"]["both_locally_available"] is False
    assert "raster_analysis" not in data
