"""
Test Suite for Phase 8.3.1: Numerical Consistency, Raster Registration & Planetary Projection Audit.

Validates:
1. Exact bit-for-bit numerical reproducibility of MOLA and CTX benchmark coordinates.
2. Resolution regime separation (oversampled_resampled_visualization vs undersampled_decimated_overview).
3. Multi-tile footprint-aware window selection across all three MOLA 128 ppd tiles (00n000, 44n000, 00n090).
4. Elevation profile provenance and Mars spherical geodesic geometry (R = 3,396,190 m).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_exact_mola_128_sinus_meridiani_reproducibility():
    """Verify Sinus Meridiani (-2.0 deg N, 5.0 deg E) reproduces exact raw binary value -909.0 m."""
    res = client.get("/api/v1/terrain/elevation/point?lat=-2.0&lon=5.0")
    assert res.status_code == 200
    data = res.json()
    assert data["elevation_m"] == -909.0
    assert "megt00n000hb" in data["dataset_id"]
    assert abs(data["native_resolution_m"] - 463.08) < 0.1
    assert "IAU:49900" in data["crs"]
    assert data["is_nodata"] is False
    assert data["is_valid"] is True


def test_exact_mola_4_olympus_mons_reproducibility():
    """Verify Olympus Mons (18.65 deg N, 226.2 deg E) reproduces exact COG value +20009.0 m."""
    res = client.get("/api/v1/terrain/elevation/point?lat=18.65&lon=226.2")
    assert res.status_code == 200
    data = res.json()
    assert data["elevation_m"] == 20009.0
    assert data["dataset_id"] == "mola-megdr-4"
    assert abs(data["native_resolution_m"] - 14818.67) < 1.0
    assert "IAU:49900" in data["crs"]
    assert data["is_nodata"] is False
    assert data["is_valid"] is True


def test_exact_ctx_tyrrhena_terra_reproducibility():
    """Verify Tyrrhena Terra CTX DTM (-4.600 deg N, 66.317 deg E) reproduces exact GeoTIFF value +2189.49 m."""
    res = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317")
    assert res.status_code == 200
    data = res.json()
    assert data["elevation_m"] == 2189.49
    assert data["dataset_id"] == "ctx-dtm-p21-009323"
    assert abs(data["native_resolution_m"] - 20.0128) < 0.001
    assert "IAU:49910" in data["crs"]
    assert data["is_nodata"] is False
    assert data["is_valid"] is True


def test_display_vs_native_sampling_regimes():
    """Verify distinction between native resolution and viewport display sampling regimes."""
    # 1. CTX oversampled window: small geographic bounds with high pixel count -> disp_res < src_res
    res_over = client.get(
        "/api/v1/terrain/render/window?min_lon=66.25&min_lat=-4.65&max_lon=66.35&max_lat=-4.55&width=512&height=512"
    )
    assert res_over.status_code == 200
    assert res_over.headers["x-source-dataset"] == "ctx-dtm-p21-009323"
    assert "20.0" in res_over.headers["x-source-resolution"]
    assert res_over.headers["x-sampling-regime"] == "oversampled_resampled_visualization"
    assert float(res_over.headers["x-sampling-ratio"]) < 1.0
    assert res_over.headers["x-output-dimensions"] == "512x512"

    # 2. MOLA 128 decimated overview: broad geographic bounds -> disp_res > src_res
    res_under = client.get(
        "/api/v1/terrain/render/window?min_lon=10.0&min_lat=-30.0&max_lon=60.0&max_lat=-10.0&width=256&height=256"
    )
    assert res_under.status_code == 200
    assert "mola-megdr-128" in res_under.headers["x-source-dataset"]
    assert "463.0" in res_under.headers["x-source-resolution"]
    assert res_under.headers["x-sampling-regime"] == "undersampled_decimated_overview"
    assert float(res_under.headers["x-sampling-ratio"]) > 1.0


def test_footprint_aware_selection_mola_tiles():
    """Verify multi-tile footprint awareness routes windows to the correct regional MOLA tile."""
    # Tile 44n000 (Northern hemisphere: lat 0 to 44, lon 0 to 90)
    res_44 = client.get(
        "/api/v1/terrain/render/window/metadata?min_lon=20.0&min_lat=10.0&max_lon=30.0&max_lat=20.0&width=256&height=256"
    )
    assert res_44.status_code == 200
    meta_44 = res_44.json()
    assert meta_44["dataset_id"] == "mola-megdr-128"
    assert "140221" in meta_44["source_checksum"]  # Checksum for megt44n000hb

    # Tile 00n090 (Eastern hemisphere: lat -44 to 0, lon 90 to 180)
    res_90 = client.get(
        "/api/v1/terrain/render/window/metadata?min_lon=100.0&min_lat=-25.0&max_lon=120.0&max_lat=-15.0&width=256&height=256"
    )
    assert res_90.status_code == 200
    meta_90 = res_90.json()
    assert meta_90["dataset_id"] == "mola-megdr-128"
    assert "764946" in meta_90["source_checksum"]  # Checksum for megt00n090hb

    # Outside all MOLA 128 tiles -> falls back to Global MOLA 4 ppd
    res_global = client.get(
        "/api/v1/terrain/render/window/metadata?min_lon=200.0&min_lat=10.0&max_lon=220.0&max_lat=20.0&width=256&height=256"
    )
    assert res_global.status_code == 200
    meta_global = res_global.json()
    assert meta_global["dataset_id"] == "mola-megdr-4"
    assert "25f16f" in meta_global["source_checksum"]


def test_elevation_profile_preset_provenance():
    """Verify all 4 profile presets return authentic datasets and non-zero geodesic metrics."""
    # CTX Crater Rim preset
    res_ctx = client.get(
        "/api/v1/terrain/elevation/profile?start_lat=-4.600&start_lon=66.317&end_lat=-4.640&end_lon=66.350&num_samples=25"
    )
    assert res_ctx.status_code == 200
    data_ctx = res_ctx.json()
    assert data_ctx["datasets_used"] == ["ctx-dtm-p21-009323"]
    assert data_ctx["points"][0]["elevation_m"] == 2189.49
    assert data_ctx["points"][0]["resolution_m"] == 20.0128
    assert data_ctx["total_distance_m"] > 2000

    # Sinus Meridiani preset
    res_sinus = client.get(
        "/api/v1/terrain/elevation/profile?start_lat=-2.000&start_lon=5.000&end_lat=-2.150&end_lon=5.180&num_samples=25"
    )
    assert res_sinus.status_code == 200
    data_sinus = res_sinus.json()
    assert "mola-megdr-128" in data_sinus["datasets_used"][0]
    assert data_sinus["points"][0]["elevation_m"] == -909.0
    assert data_sinus["points"][0]["resolution_m"] == 463.08
