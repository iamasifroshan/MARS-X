"""Phase 8.6: Scientific Data Integration Test Suite.

Verifies:
1. USGS SIM 3292 Geological Map (Polygons, Contacts, Structure, Landing Sites).
2. MGS TES Global Thermal Inertia (Putzig & Mellon 2007) and lithological interpretation.
3. 2001 Mars Odyssey THEMIS 100m Regional IR mosaics and temperature query prohibition.
4. Multi-DTM point elevation and exact preservation of the Tyrrhena CTX benchmark (+2189.49 m).
5. Authoritative Scientific Dataset Provenance Registry API endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_geology_metadata():
    """Verify USGS SIM 3292 metadata endpoint returns correct feature layers and CRS."""
    resp = client.get("/api/v1/geology/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert "SIM 3292" in data["title"]
    assert "Tanaka" in data["authors"]
    assert "GCS_Mars_2000_Sphere" in data["crs"]
    assert "layers" in data
    assert "geology" in data["layers"]
    assert "contacts" in data["layers"]
    assert "structure" in data["layers"]
    assert "landing_sites" in data["layers"]
    assert data["layers"]["geology"]["feature_count"] == 1311
    assert data["layers"]["contacts"]["feature_count"] == 3800
    assert data["layers"]["structure"]["feature_count"] == 3593
    assert data["layers"]["landing_sites"]["feature_count"] == 9


def test_geology_legend_and_unit_details():
    """Verify the 44 chronostratigraphic units and single unit lookup."""
    resp = client.get("/api/v1/geology/legend")
    assert resp.status_code == 200
    legend = resp.json()
    assert len(legend) == 44

    # Test single unit lookup
    resp_unit = client.get("/api/v1/geology/units/mAl")
    assert resp_unit.status_code == 200
    unit = resp_unit.json()
    assert unit["unit"] == "mAl"
    assert "Middle Amazonian lowland unit" in unit["description"]
    assert unit["chronostratigraphic_period"] == "Amazonian"


def test_geology_point_and_viewport_queries():
    """Verify point-in-polygon resolution and GeoJSON viewport query."""
    # Tyrrhena Terra coordinates (lat=-4.6, lon=66.317)
    resp = client.get("/api/v1/geology/point?lat=-4.6&lon=66.317")
    assert resp.status_code == 200
    point_geo = resp.json()
    assert point_geo["unit"] == "eNh"
    assert point_geo["chronostratigraphic_period"] == "Noachian"

    # Viewport GeoJSON query
    resp_vp = client.get(
        "/api/v1/geology/viewport?min_lon=0&min_lat=-10&max_lon=30&max_lat=10&layer=geology&limit=10"
    )
    assert resp_vp.status_code == 200
    fc = resp_vp.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    assert "geometry" in fc["features"][0]
    assert "properties" in fc["features"][0]


def test_thermal_inertia_metadata_and_units():
    """Verify MGS TES Thermal Inertia metadata strictly specifies tiu and prohibits temperature."""
    resp = client.get("/api/v1/thermal/metadata")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["dataset_id"] == "tes-thermal-inertia-putzig-2007"
    assert "Putzig" in meta["citation"]
    assert "J m^-2 K^-1 s^-1/2" in meta["units"]
    assert "NOT temperature" in meta["prohibition_disclaimer"]


def test_thermal_inertia_point_queries():
    """Verify physical thermal inertia values at Sinus Meridiani and Tharsis dust plains."""
    # Sinus Meridiani (coarse basaltic / hematite lag plains, high thermal inertia)
    resp_sm = client.get("/api/v1/thermal/point?lat=-2.0&lon=5.0&product=dayside")
    assert resp_sm.status_code == 200
    data_sm = resp_sm.json()
    assert not data_sm["is_nodata"]
    assert data_sm["thermal_inertia_tiu"] is not None
    assert 400.0 <= data_sm["thermal_inertia_tiu"] <= 900.0
    assert "sand" in data_sm["physical_interpretation"].lower() or "rock" in data_sm["physical_interpretation"].lower()

    # Tharsis Montes dust mantle (insulating dust mantle, low thermal inertia < 100 tiu)
    resp_th = client.get("/api/v1/thermal/point?lat=10.0&lon=-110.0&product=dayside")
    assert resp_th.status_code == 200
    data_th = resp_th.json()
    assert not data_th["is_nodata"]
    assert data_th["thermal_inertia_tiu"] is not None
    assert 50.0 <= data_th["thermal_inertia_tiu"] <= 120.0
    assert "dust" in data_th["physical_interpretation"].lower()


def test_thermal_window_rendering():
    """Verify window rendering returns valid RGBA PNG."""
    resp = client.get(
        "/api/v1/thermal/render/window?min_lon=0&min_lat=-10&max_lon=30&max_lat=10&product=dayside&width=128&height=128"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 1000


def test_themis_infrared_metadata_and_rendering():
    """Verify THEMIS 100m IR mosaic metadata and window rendering."""
    resp = client.get("/api/v1/themis/metadata")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["dataset_id"] == "themis-ir-mosaics-regional"
    assert meta["regional_tile"] == "N-30_000 (Sinus Meridiani / Tyrrhena corridor)"
    assert meta["measurement_semantics"]["quantitative_analysis_supported"] is False

    # Render window
    resp_render = client.get(
        "/api/v1/themis/render/window?min_lon=0&min_lat=-10&max_lon=10&max_lat=0&mode=day&width=128&height=128"
    )
    assert resp_render.status_code == 200
    assert resp_render.headers["content-type"] == "image/png"
    assert len(resp_render.content) > 1000


def test_themis_point_temperature_prohibition():
    """Verify that querying temperature from THEMIS visual mosaics is strictly rejected with HTTP 400."""
    resp = client.get("/api/v1/themis/point?lat=-5.0&lon=10.0")
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "SCIENTIFIC PROHIBITION" in detail
    assert "temperature" in detail.lower()


def test_multi_dtm_numerical_consistency():
    """Verify all three numerical DTMs are sampled correctly, with Tyrrhena benchmark 100% preserved."""
    # 1. Tyrrhena CTX Benchmark: lat=-4.600, lon=66.317 -> elevation must be EXACTLY +2189.49 m
    resp_tyr = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317&preferred_source=ctx")
    assert resp_tyr.status_code == 200
    data_tyr = resp_tyr.json()
    assert data_tyr["elevation_m"] == 2189.49
    assert data_tyr["dataset_id"] == "ctx-dtm-p21-009323"
    assert data_tyr["native_resolution_m"] == 20.0128

    # 2. Apollinaris Sulci Controlled CTX DTM: lat=4.700, lon=168.250 -> -2930.77 m
    resp_t01 = client.get("/api/v1/terrain/elevation/point?lat=4.700&lon=168.250")
    assert resp_t01.status_code == 200
    data_t01 = resp_t01.json()
    assert data_t01["elevation_m"] == -2930.77
    assert data_t01["dataset_id"] == "ctx-dtm-controlled-t01-000893"
    assert data_t01["native_resolution_m"] == 20.0

    # 3. Holden Crater Controlled HiRISE DTM: lat=-28.500, lon=309.020 -> -1132.14 m
    resp_hi = client.get("/api/v1/terrain/elevation/point?lat=-28.500&lon=309.020")
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert data_hi["elevation_m"] == -1132.14
    assert data_hi["dataset_id"] == "hirise-dtm-controlled-esp-011635"
    assert data_hi["native_resolution_m"] == 1.01


def test_scientific_provenance_endpoints():
    """Verify Scientific Provenance Registry endpoints return complete authoritative metadata."""
    resp = client.get("/api/v1/science/provenance")
    assert resp.status_code == 200
    data = resp.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 23

    # Test single product lookup
    resp_single = client.get("/api/v1/science/provenance/ctx-dtm-controlled-t01-000893")
    assert resp_single.status_code == 200
    d = resp_single.json()
    assert d["dataset_id"] == "ctx-dtm-controlled-t01-000893"
    assert "T01_000893" in d["product_id"]
    assert "sha256" in d
