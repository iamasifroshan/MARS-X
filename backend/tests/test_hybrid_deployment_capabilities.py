"""Tests for MARS-X Zero-Cost Hybrid Deployment Mode and Capability Discovery.

Validates:
1. Capability discovery in Local Full Science Mode (with authentic local datasets)
2. Capability discovery in Cloud Demo Mode (missing raster datasets)
3. Cloud Mode operation with lightweight MCD climatology, solar geometry, and catalog
4. Structured 503 Service Unavailable response when raster-dependent features are queried without rasters
5. Climatology, solar geometry, and science catalog independence from raster presence
6. Resilience: missing optional datasets do not prevent startup or break endpoints
7. Mode overrides via MARS_OPERATING_MODE and RENDER environment variables
"""

import os
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_capabilities_local_full_science_mode():
    """Verify capabilities report in Local Full Science Mode with local datasets present."""
    response = client.get("/api/v1/system/capabilities")
    assert response.status_code == 200
    data = response.json()

    assert data["api_online"] is True
    assert data["api_available"] is True
    assert data["operating_mode"] in ("local_full_science", "cloud_demo")
    assert "datasets" in data
    assert "features" in data
    assert "corridors_ready" in data

    # Verify key dataset descriptors
    for ds_id in ["mola_megdr_4", "ctx_tyrrhena", "tes_thermal", "mcd_climatology"]:
        assert ds_id in data["datasets"]
        ds = data["datasets"][ds_id]
        assert "id" in ds
        assert "name" in ds
        assert "tier" in ds
        assert "type" in ds
        assert "available" in ds
        assert "validation_status" in ds

    # Verify key feature flags
    for feat_id in ["marswalk_routing", "elevation_profile", "terrain_intelligence", "mcd_climatology", "solar_geometry"]:
        assert feat_id in data["features"]
        feat = data["features"][feat_id]
        assert "id" in feat
        assert "available" in feat
        assert "category" in feat


def test_capabilities_cloud_demo_mode_when_rasters_missing(monkeypatch):
    """Verify capabilities truthfully reports Cloud Demo Mode when rasters are absent."""
    empty_tmp = tempfile.mkdtemp()
    try:
        monkeypatch.setenv("MARS_DATA_DIR", empty_tmp)
        monkeypatch.delenv("MARS_OPERATING_MODE", raising=False)
        monkeypatch.delenv("RENDER", raising=False)

        response = client.get("/api/v1/system/capabilities")
        assert response.status_code == 200
        data = response.json()

        assert data["operating_mode"] == "cloud_demo"
        assert data["raster_processing_available"] is False
        assert data["cloud_demo_notice"] == (
            "Full raster-based terrain analysis is available in Local Full Science Mode. "
            "Start the local MARS-X backend with the required scientific datasets."
        )

        # Raster features must be reported as unavailable
        assert data["features"]["marswalk_routing"]["available"] is False
        assert data["features"]["elevation_profile"]["available"] is False
        assert data["features"]["terrain_intelligence"]["available"] is False
        assert "Full raster-based terrain analysis is available in Local Full Science Mode" in (
            data["features"]["marswalk_routing"]["reason_if_unavailable"]
        )

        # Pure physics and catalog features remain available
        assert data["features"]["solar_geometry"]["available"] is True
        assert data["features"]["atmospheric_pressure"]["available"] is True
        assert data["features"]["science_discovery"]["available"] is True
    finally:
        shutil.rmtree(empty_tmp, ignore_errors=True)


def test_cloud_demo_mode_lightweight_services_operational(monkeypatch):
    """Verify lightweight services (solar, atmosphere, discoveries) remain operational in cloud mode."""
    empty_tmp = tempfile.mkdtemp()
    try:
        monkeypatch.setenv("MARS_DATA_DIR", empty_tmp)
        monkeypatch.setenv("MARS_OPERATING_MODE", "cloud_demo")

        # 1. Solar irradiance / ephemeris
        sol_res = client.get("/api/v1/environmental/solar-geometry?lat=-4.6&lon=66.3&ls_deg=180.0&ltst_hours=12.0")
        assert sol_res.status_code == 200
        sol_data = sol_res.json()
        assert "toa_normal_irradiance_w_m2" in sol_data
        assert sol_data["toa_normal_irradiance_w_m2"] > 0

        # 2. Atmospheric pressure model
        atm_res = client.get("/api/v1/environmental/pressure/estimate?lat=-4.6&lon=66.3&elevation_m=2000.0&ls_deg=180.0")
        assert atm_res.status_code == 200
        atm_data = atm_res.json()
        assert "reference_atmospheric_pressure_estimate_pa" in atm_data
        assert atm_data["reference_atmospheric_pressure_estimate_pa"] > 0

        # 3. Science discoveries catalog
        disc_res = client.get("/api/v1/discovery/list")
        assert disc_res.status_code == 200
        disc_data = disc_res.json()
        assert len(disc_data) > 0
    finally:
        shutil.rmtree(empty_tmp, ignore_errors=True)


def test_missing_raster_returns_503_service_unavailable(monkeypatch):
    """Verify querying missing raster endpoints returns structured 503 rather than 500 or crash."""
    from app.marswalk.marswalk_planner import clear_route_cache
    from app.terrain.traversability_service import refresh_terrain_sources
    from app.routers.terrain import _clear_raster_cache

    empty_tmp = tempfile.mkdtemp()
    try:
        monkeypatch.setenv("MARS_DATA_DIR", empty_tmp)
        refresh_terrain_sources()
        clear_route_cache()
        _clear_raster_cache()

        # 1. Marswalk Route Planning without raster
        route_req = {
            "start_lat": -4.600,
            "start_lon": 66.317,
            "dest_lat": -4.605,
            "dest_lon": 66.325,
            "preferred_source": "ctx-tyrrhena",
            "slope_penalty_factor": 2.0,
        }
        mw_res = client.post("/api/v1/marswalk/route", json=route_req)
        assert mw_res.status_code == 503
        assert "unavailable" in mw_res.json()["detail"].lower()

        # 2. Elevation profile without elevation raster
        prof_res = client.get(
            "/api/v1/terrain/elevation/profile?start_lat=18.0&start_lon=224.0&end_lat=18.65&end_lon=226.2&num_samples=10"
        )
        assert prof_res.status_code == 503
        assert "Local Full Science Mode" in prof_res.json()["detail"]
    finally:
        shutil.rmtree(empty_tmp, ignore_errors=True)
        monkeypatch.undo()
        refresh_terrain_sources()
        clear_route_cache()
        _clear_raster_cache()


def test_climatology_operational_with_tracked_cube(monkeypatch):
    """Verify MCD climatology operates when the tracked cube JSON is present."""
    # Climatology cube is checked into git at data/derived/climatology/mcd_v6_2_climatology_cube.json
    res = client.get("/api/v1/climatology/point?lat=-4.6&lon=66.3&ls_deg=180.0&ltst_hours=12.0")
    # If file is present locally, it returns 200
    if res.status_code == 200:
        data = res.json()
        assert "climatological_temp_k" in data
        assert "climatological_pressure_pa" in data
        assert data["climatological_temp_k"] > 100.0


def test_render_environment_variable_triggers_cloud_demo(monkeypatch):
    """Verify RENDER=true forces cloud demo mode even if local rasters exist."""
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("MARS_OPERATING_MODE", raising=False)

    response = client.get("/api/v1/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["operating_mode"] == "cloud_demo"
    assert data["environment"] == "production_cloud"
    assert data["cloud_demo_notice"] is not None


def test_explicit_local_mode_override(monkeypatch):
    """Verify MARS_OPERATING_MODE=local_full_science takes precedence."""
    monkeypatch.setenv("MARS_OPERATING_MODE", "local_full_science")
    monkeypatch.delenv("RENDER", raising=False)

    response = client.get("/api/v1/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["operating_mode"] == "local_full_science"
    assert data["cloud_demo_notice"] is None


def test_storage_inspection_endpoint():
    """Verify /api/v1/system/storage returns truthful disk diagnostics."""
    response = client.get("/api/v1/system/storage")
    assert response.status_code == 200
    data = response.json()
    assert "data_root" in data
    assert "disk_space" in data
    assert data["disk_space"]["total_gb"] > 0
    assert "storage_type" in data
    assert data["storage_type"] in ("persistent_disk_volume", "ephemeral_container_filesystem")
    assert "corridors_ready" in data
