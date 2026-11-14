"""
Test Suite for Phase 8.2: Emergency Runtime Recovery, Real Terrain Rendering & UI Reconstruction.
Verifies authentic numerical raster rendering endpoints for Global MOLA, MOLA 128 ppd, and USGS CTX DTM.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_and_status():
    """Verify backend health and status endpoints return HTTP 200 with online status."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_status = client.get("/api/v1/status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "ok"


def test_render_global_mola_east():
    """Verify East hemisphere Global MOLA renders as valid RGBA PNG."""
    res = client.get("/api/v1/terrain/render/global-mola?hemisphere=east")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(res.content) > 10000


def test_render_global_mola_west():
    """Verify West hemisphere Global MOLA renders as valid RGBA PNG."""
    res = client.get("/api/v1/terrain/render/global-mola?hemisphere=west")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(res.content) > 10000


def test_render_mola_128_tiles():
    """Verify regional MOLA 128 ppd tiles render as valid RGBA PNG."""
    for tile_id in ["00n000", "44n000", "00n090"]:
        res = client.get(f"/api/v1/terrain/render/mola-128-tile?tile_id={tile_id}")
        assert res.status_code == 200, f"Tile {tile_id} failed: {res.text}"
        assert res.headers["content-type"] == "image/png"
        assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(res.content) > 1000


def test_render_ctx_dtm():
    """Verify authentic USGS 20m CTX numerical DTM renders as valid RGBA PNG."""
    res = client.get("/api/v1/terrain/render/ctx-dtm")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(res.content) > 1000


def test_terrain_layers_catalog():
    """Verify /api/v1/terrain/layers includes authentic CTX and MOLA layers as available."""
    res = client.get("/api/v1/terrain/layers")
    assert res.status_code == 200
    layers = res.json()
    layer_ids = [l["layer_id"] for l in layers]

    assert "mola-elevation-global" in layer_ids
    assert "ctx-dtm-p21-009323" in layer_ids

    ctx_layer = next(l for l in layers if l["layer_id"] == "ctx-dtm-p21-009323")
    assert ctx_layer["is_available"] is True
    assert ctx_layer["crs"] == "IAU:49910"
    assert ctx_layer["unit"] == "metres"


def test_render_invalid_parameters():
    """Verify invalid hemisphere or tile_id parameters are rejected."""
    res_bad_hemi = client.get("/api/v1/terrain/render/global-mola?hemisphere=north")
    assert res_bad_hemi.status_code == 422

    res_bad_tile = client.get("/api/v1/terrain/render/mola-128-tile?tile_id=99n999")
    assert res_bad_tile.status_code == 422
