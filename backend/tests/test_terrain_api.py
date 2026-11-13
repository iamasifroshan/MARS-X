"""Integration tests for MARS-X Terrain API endpoints."""

import os
import tempfile
import numpy as np
import rasterio
from rasterio.transform import from_origin
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_terrain_datasets_list():
    """Verify GET /api/v1/terrain/datasets returns registered numerical DTMs."""
    response = client.get("/api/v1/terrain/datasets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    ids = [d["dataset_id"] for d in data]
    assert "mola-megdr" in ids
    assert "hrsc-dtm" in ids
    assert "hirise-dtm" in ids
    assert "ctx-dtm" in ids

    # All must be strictly numerical DTMs
    for d in data:
        assert d["is_numerical_dtm"] is True
        assert "MOLA Areoid" in d["elevation_unit"]


def test_api_terrain_coverage_mola():
    """Verify GET /api/v1/terrain/coverage?dataset_id=mola-megdr."""
    response = client.get("/api/v1/terrain/coverage?dataset_id=mola-megdr")
    assert response.status_code == 200
    cov = response.json()
    assert cov["dataset_id"] == "mola-megdr"
    assert cov["is_global"] is True
    assert cov["lat_min"] == -88.0
    assert cov["lat_max"] == 88.0
    assert cov["total_area_approx_pct"] > 95.0


def test_api_terrain_coverage_hirise():
    """Verify GET /api/v1/terrain/coverage?dataset_id=hirise-dtm."""
    response = client.get("/api/v1/terrain/coverage?dataset_id=hirise-dtm")
    assert response.status_code == 200
    cov = response.json()
    assert cov["dataset_id"] == "hirise-dtm"
    assert cov["is_global"] is False
    assert cov["total_area_approx_pct"] < 1.0


def test_api_terrain_coverage_not_found():
    """Verify 404 for unknown dataset."""
    response = client.get("/api/v1/terrain/coverage?dataset_id=nonexistent-dtm")
    assert response.status_code == 404


def test_api_terrain_summary_endpoint():
    """Verify GET /api/v1/terrain/summary?dataset_id=hrsc-dtm."""
    response = client.get("/api/v1/terrain/summary?dataset_id=hrsc-dtm")
    assert response.status_code == 200
    summary = response.json()
    assert summary["dataset_id"] == "hrsc-dtm"
    assert "HRSC" in summary["instrument"]
    assert "MOLA Areoid" in summary["elevation_unit"]


def test_api_terrain_metadata_not_downloaded():
    """Verify 404 without fabrication when raw file is not yet downloaded (e.g. hrsc-dtm)."""
    response = client.get("/api/v1/terrain/metadata?dataset_id=hrsc-dtm")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "not yet been downloaded" in detail
    assert "cannot be fabricated" in detail


def test_api_terrain_metadata_downloaded_mola():
    """Verify 200 with real inspected metadata for downloaded mola-megdr."""
    response = client.get("/api/v1/terrain/metadata?dataset_id=mola-megdr")
    assert response.status_code == 200
    meta = response.json()
    assert meta["dataset_id"] == "mola-megdr"
    assert meta["width"] == 1440
    assert meta["height"] == 720
    assert meta["is_mars_crs"] is True


def test_api_terrain_metadata_with_real_raster_file():
    """Verify GET /api/v1/terrain/metadata with a valid on-disk GeoTIFF file."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        width, height = 10, 10
        transform = from_origin(0.0, 0.0, 0.01, 0.01)
        mars_crs = rasterio.crs.CRS.from_proj4("+proj=longlat +a=3396190 +b=3396190 +no_defs")
        data = np.full((1, height, width), 100, dtype=np.int16)

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
            nodata=-32768,
        ) as dst:
            dst.write(data)

        response = client.get(f"/api/v1/terrain/metadata?dataset_id=test-mola&file_path={tmp_path}")
        assert response.status_code == 200
        meta = response.json()
        assert meta["dataset_id"] == "test-mola"
        assert meta["width"] == 10
        assert meta["height"] == 10
        assert meta["is_mars_crs"] is True
        assert meta["nodata_value"] == -32768.0

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

