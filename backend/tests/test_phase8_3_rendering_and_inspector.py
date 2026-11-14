"""
Test Suite for Phase 8.3: Multi-Resolution Terrain Rendering & Interactive Elevation Inspection.

Validates:
1. Multi-resolution point elevation queries (CTX 20m -> MOLA 128 -> Global MOLA 4 ppd -> Out of Bounds).
2. Provenance metadata and bit-level checksum reporting.
3. Spherical geodesic profile sampling (Mars R = 3,396,190 m) and terrain relief calculations.
4. Windowed progressive raster rendering and memory caching.
5. In-band metadata headers separating source resolution from display resolution.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_point_elevation_ctx_valid():
    """Verify point elevation inside authentic USGS CTX DTM returns 20m resolution and IAU:49910."""
    res = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert "ctx" in data["dataset_id"]
    assert "IAU:49910" in data["crs"]
    assert abs(data["native_resolution_m"] - 20.0128) < 0.1
    assert data["elevation_m"] is not None
    # Tyrrhena Terra crater rim elevation ~ 2189 metres
    assert 2000 < data["elevation_m"] < 2300
    assert data["is_nodata"] is False
    assert "a4edb9" in data["source_checksum"]


def test_point_elevation_mola_128_tile():
    """Verify point elevation in MOLA 128 ppd tile megt00n000hb returns 463m resolution and IAU:49900."""
    res = client.get("/api/v1/terrain/elevation/point?lat=-2.000&lon=5.000")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert "megt00n000hb" in data["dataset_id"]
    assert "IAU:49900" in data["crs"]
    assert abs(data["native_resolution_m"] - 463.08) < 0.1
    assert data["elevation_m"] is not None
    assert data["is_nodata"] is False
    assert "f57274" in data["source_checksum"]


def test_point_elevation_global_mola_fallback():
    """Verify fallback to Global MOLA 4 ppd for Olympus Mons."""
    res = client.get("/api/v1/terrain/elevation/point?lat=18.65&lon=226.2")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert "mola-megdr-4" in data["dataset_id"]
    assert "IAU:49900" in data["crs"]
    assert abs(data["native_resolution_m"] - 14818.67) < 1.0
    # Olympus Mons summit elevation is > 18000 m
    assert data["elevation_m"] > 18000
    assert data["is_nodata"] is False
    assert "25f16f" in data["source_checksum"]


def test_point_elevation_out_of_bounds():
    """Verify out-of-bounds coordinates return validation error."""
    res = client.get("/api/v1/terrain/elevation/point?lat=95.0&lon=45.0")
    assert res.status_code == 422


def test_point_elevation_longitude_wrapping():
    """Verify negative longitude and positive 0-360 longitude map to the same raster location."""
    res_pos = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317")
    res_neg = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=-293.683")
    assert res_pos.status_code == 200
    assert res_neg.status_code == 200
    data_pos = res_pos.json()
    data_neg = res_neg.json()
    assert data_pos["dataset_id"] == data_neg["dataset_id"]
    assert data_pos["elevation_m"] == data_neg["elevation_m"]


def test_elevation_profile_ctx_transect():
    """Verify Great-Circle geodesic profile sampling within CTX DTM."""
    res = client.get(
        "/api/v1/terrain/elevation/profile?start_lat=-4.600&start_lon=66.317&end_lat=-4.640&end_lon=66.350&num_samples=25"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["num_samples"] == 25
    assert len(data["points"]) == 25
    assert data["total_distance_m"] > 2000
    assert "ctx-dtm-p21-009323" in data["datasets_used"]
    assert data["max_elevation_m"] >= data["min_elevation_m"]
    assert data["elevation_gain_m"] >= 0.0
    assert data["elevation_loss_m"] >= 0.0


def test_elevation_profile_global_mola():
    """Verify Great-Circle geodesic profile across Olympus Mons flank."""
    res = client.get(
        "/api/v1/terrain/elevation/profile?start_lat=18.0&start_lon=224.0&end_lat=18.65&end_lon=226.2&num_samples=20"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["num_samples"] == 20
    assert len(data["points"]) == 20
    assert "mola-megdr-4" in data["datasets_used"]
    assert data["max_elevation_m"] - data["min_elevation_m"] > 1000.0


def test_elevation_profile_invalid_coords():
    """Verify invalid start/end coordinates return HTTP 422."""
    res = client.get(
        "/api/v1/terrain/elevation/profile?start_lat=95.0&start_lon=0.0&end_lat=0.0&end_lon=0.0"
    )
    assert res.status_code == 422


def test_window_render_ctx():
    """Verify progressive windowed rendering from CTX GeoTIFF."""
    res = client.get(
        "/api/v1/terrain/render/window?min_lon=66.1&min_lat=-4.8&max_lon=66.5&max_lat=-4.5&width=128&height=128"
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert res.headers["x-source-dataset"] == "ctx-dtm-p21-009323"
    assert "20.0" in res.headers["x-source-resolution"]
    assert "a4edb9" in res.headers["x-source-checksum"]
    assert res.headers["x-cache-status"] in ["MISS", "HIT"]


def test_window_render_mola_128():
    """Verify progressive windowed rendering from regional MOLA 128 ppd tile."""
    res = client.get(
        "/api/v1/terrain/render/window?min_lon=10.0&min_lat=-5.0&max_lon=15.0&max_lat=-2.0&width=128&height=128"
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert res.headers["x-source-dataset"] == "mola-megdr-128"
    assert "463.0" in res.headers["x-source-resolution"]


def test_window_render_caching():
    """Verify that repeated requests hit in-memory cache."""
    url = "/api/v1/terrain/render/window?min_lon=66.2&min_lat=-4.7&max_lon=66.4&max_lat=-4.6&width=64&height=64"
    res1 = client.get(url)
    assert res1.status_code == 200
    res2 = client.get(url)
    assert res2.status_code == 200
    assert res2.headers["x-cache-status"] == "HIT"


def test_window_render_metadata():
    """Verify companion JSON metadata endpoint for window rendering."""
    res = client.get(
        "/api/v1/terrain/render/window/metadata?min_lon=66.1&min_lat=-4.8&max_lon=66.5&max_lat=-4.5&width=128&height=128"
    )
    assert res.status_code == 200
    meta = res.json()
    assert meta["dataset_id"] == "ctx-dtm-p21-009323"
    assert meta["width"] == 128
    assert meta["height"] == 128
    assert abs(meta["source_resolution_m"] - 20.0128) < 0.1
