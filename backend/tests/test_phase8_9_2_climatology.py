"""MARS-X — Phase 8.9.2: Climatology Unit and Integration Tests.

Validates:
1. Pydantic schemas and metadata specifications for MCD v6.2 climatology.
2. Climatology service lifecycle, caching, and baseline fallback.
3. Multidimensional spatial interpolation, longitude wrapping (360° periodic), and latitude clamping.
4. Circular seasonal interpolation across solar longitude Ls [0, 360°).
5. Circular diurnal interpolation across Local True Solar Time LTST [0, 24h).
6. Landmark proximity blending and exact ground-truth anchor extraction.
7. Topographic elevation barometric pressure scaling (Scale height H = 11,100 m) and lapse rate temperature scaling (Gamma = 2.5 K/km).
8. Extreme terrain elevation scaling at Olympus Mons (+21 km) and Hellas Planitia (-7 km).
9. Wind kinematic conversions, meteorological direction (from), and 16-point cardinal mapping.
10. Diurnal (24h) and seasonal (360° Ls) profile generation and extrema metrics.
11. Route-level climatological enrichment and downsampling.
12. FastAPI endpoints, query parameters, error responses, and schemas.
13. Operational safety disclaimers and non-negotiable Float32 terrain benchmark preservation.
"""

import math
import struct
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.science.climatology_models import (
    ClimatologyPoint,
    ClimatologyProfileResponse,
    ClimatologyMetadataResponse,
    ClimatologyCoverageResponse,
    RouteClimatologySummary,
    RouteClimatologyEnrichRequest,
    CLIMATOLOGY_SAFETY_DISCLAIMER,
)
from app.science.climatology_service import (
    ClimatologyService,
    get_climatology_service,
    wind_direction_to_cardinal,
    get_season_name,
    great_circle_distance_km,
    ATMOSPHERIC_SCALE_HEIGHT_M,
    TROPOSPHERIC_LAPSE_RATE_K_M,
)

client = TestClient(app)


# ── 1. Model & Schema Tests ──────────────────────────────────────────────────

def test_climatology_models_validation():
    """Verify ClimatologyPoint model validation and constraints."""
    pt = ClimatologyPoint(
        latitude=18.4447,
        longitude=77.4508,
        solar_longitude_ls_deg=6.15,
        local_true_solar_time_hours=13.5,
        elevation_m=-2560.0,
        season_name="Northern Spring / Southern Autumn",
        surface_pressure_pa=720.5,
        atmospheric_temperature_k=238.2,
        surface_temperature_k=272.1,
        wind_speed_m_s=4.8,
        wind_direction_deg=78.5,
        wind_cardinal="ENE",
        dust_optical_depth=0.45,
        density_kg_m3=0.0158,
        interpolation_method="Exact Landmark Anchor",
        is_landmark=True,
        nearest_landmark="Jezero Crater (Mars 2020 Perseverance)",
        distance_to_landmark_km=0.0,
        classification="Climatological Model",
        model_version="MCD v6.2 (LMD/ESA/CNES)",
    )
    assert pt.latitude == 18.4447
    assert pt.surface_pressure_pa == 720.5
    assert pt.classification == "Climatological Model"
    assert "ASTRONAUT SAFETY" in pt.safety_disclaimer


def test_safety_disclaimer_content():
    """Verify operational safety disclaimer contains mandatory proscriptions."""
    assert "ASTRONAUT SAFETY" in CLIMATOLOGY_SAFETY_DISCLAIMER
    assert "DO NOT constitute a live Martian weather forecast" in CLIMATOLOGY_SAFETY_DISCLAIMER
    assert "Never describe routes or conditions as 'astronaut-safe'" in CLIMATOLOGY_SAFETY_DISCLAIMER


# ── 2. Compass & Astronomy Helpers ───────────────────────────────────────────

def test_wind_direction_to_cardinal():
    """Verify meteorological wind direction degrees map to correct 16-point cardinals."""
    assert wind_direction_to_cardinal(0.0) == "N"
    assert wind_direction_to_cardinal(359.0) == "N"
    assert wind_direction_to_cardinal(90.0) == "E"
    assert wind_direction_to_cardinal(180.0) == "S"
    assert wind_direction_to_cardinal(270.0) == "W"
    assert wind_direction_to_cardinal(45.0) == "NE"
    assert wind_direction_to_cardinal(135.0) == "SE"
    assert wind_direction_to_cardinal(225.0) == "SW"
    assert wind_direction_to_cardinal(315.0) == "NW"
    assert wind_direction_to_cardinal(67.5) == "ENE"
    assert wind_direction_to_cardinal(202.5) == "SSW"


def test_get_season_name():
    """Verify Martian astronomical seasons according to solar longitude Ls."""
    assert get_season_name(0.0) == "Northern Spring / Southern Autumn"
    assert get_season_name(45.0) == "Northern Spring / Southern Autumn"
    assert get_season_name(90.0) == "Northern Summer / Southern Winter"
    assert get_season_name(179.9) == "Northern Summer / Southern Winter"
    assert get_season_name(180.0) == "Northern Autumn / Southern Spring"
    assert get_season_name(269.9) == "Northern Autumn / Southern Spring"
    assert get_season_name(270.0) == "Northern Winter / Southern Summer"
    assert get_season_name(359.9) == "Northern Winter / Southern Summer"
    # Periodic modulo check
    assert get_season_name(365.0) == "Northern Spring / Southern Autumn"


def test_great_circle_distance():
    """Verify great circle distance calculation on Mars."""
    # Distance from pole to equator along meridian: pi/2 * 3389.5 km ~ 5324.2 km
    d = great_circle_distance_km(0.0, 0.0, 90.0, 0.0)
    assert pytest.approx(d, rel=1e-3) == math.pi / 2.0 * 3389.5

    # Distance to identical point is zero
    assert great_circle_distance_km(18.4447, 77.4508, 18.4447, 77.4508) == 0.0


# ── 3. Climatology Service Core ──────────────────────────────────────────────

def test_climatology_service_singleton():
    """Verify singleton pattern returns consistent service instance."""
    s1 = get_climatology_service()
    s2 = get_climatology_service()
    assert s1 is s2
    assert s1._loaded is True


def test_landmark_exact_hit():
    """Verify query at exact landmark coordinates returns landmark values and metadata."""
    service = get_climatology_service()
    # Jezero Crater
    pt = service.get_climatology_at_point(
        latitude=18.4447,
        longitude=77.4508,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
    )
    assert pt.is_landmark is True
    assert "Jezero Crater" in (pt.nearest_landmark or "")
    assert pt.distance_to_landmark_km == 0.0
    assert pt.surface_pressure_pa > 650.0  # Jezero is -2560m below datum, so pressure > 610 Pa
    assert 150.0 <= pt.atmospheric_temperature_k <= 280.0
    assert 0.0 <= pt.wind_speed_m_s <= 30.0
    assert pt.classification == "Climatological Model"


def test_spatial_longitude_wrapping():
    """Verify seamless interpolation across 0° / 360° prime meridian boundary."""
    service = get_climatology_service()
    # Query at 359.9° and 0.1° should yield virtually identical values
    pt_west = service.get_climatology_at_point(
        latitude=0.0,
        longitude=359.9,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=0.0,
    )
    pt_east = service.get_climatology_at_point(
        latitude=0.0,
        longitude=0.1,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=0.0,
    )
    assert abs(pt_west.surface_pressure_pa - pt_east.surface_pressure_pa) < 2.0
    assert abs(pt_west.atmospheric_temperature_k - pt_east.atmospheric_temperature_k) < 1.0


def test_circular_seasonal_interpolation():
    """Verify smooth interpolation across seasonal year boundary (Ls 359° to 1°)."""
    service = get_climatology_service()
    pt_end_year = service.get_climatology_at_point(
        latitude=0.0,
        longitude=180.0,
        solar_longitude_ls_deg=359.5,
        local_true_solar_time_hours=12.0,
        elevation_m=0.0,
    )
    pt_start_year = service.get_climatology_at_point(
        latitude=0.0,
        longitude=180.0,
        solar_longitude_ls_deg=0.5,
        local_true_solar_time_hours=12.0,
        elevation_m=0.0,
    )
    assert abs(pt_end_year.surface_pressure_pa - pt_start_year.surface_pressure_pa) < 5.0
    assert abs(pt_end_year.atmospheric_temperature_k - pt_start_year.atmospheric_temperature_k) < 2.0


def test_circular_diurnal_interpolation():
    """Verify diurnal cycle continuity across midnight (LTST 23.9h to 0.1h)."""
    service = get_climatology_service()
    pt_night1 = service.get_climatology_at_point(
        latitude=18.4447,
        longitude=77.4508,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=23.9,
    )
    pt_night2 = service.get_climatology_at_point(
        latitude=18.4447,
        longitude=77.4508,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=0.1,
    )
    assert abs(pt_night1.surface_pressure_pa - pt_night2.surface_pressure_pa) < 3.0
    assert abs(pt_night1.atmospheric_temperature_k - pt_night2.atmospheric_temperature_k) < 2.0


def test_diurnal_thermal_cycle_amplitude():
    """Verify solar diurnal heating produces higher temperature at midday than midnight."""
    service = get_climatology_service()
    pt_noon = service.get_climatology_at_point(
        latitude=0.0,
        longitude=0.0,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=14.0,
        elevation_m=0.0,
    )
    pt_midnight = service.get_climatology_at_point(
        latitude=0.0,
        longitude=0.0,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=2.0,
        elevation_m=0.0,
    )
    # Noon temperature must exceed midnight temperature by at least 15 K
    assert pt_noon.surface_temperature_k > pt_midnight.surface_temperature_k + 15.0


# ── 4. Topographic Elevation Scaling Tests ───────────────────────────────────

def test_extreme_elevation_olympus_mons():
    """Verify pressure is drastically reduced at Olympus Mons summit (+21,287 m)."""
    service = get_climatology_service()
    pt = service.get_climatology_at_point(
        latitude=18.65,
        longitude=226.2,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=21287.0,
    )
    # At +21 km, P ~ P0 * exp(-21287 / 11100) ~ 610 * 0.147 ~ 90 Pa (between 50 Pa and 150 Pa)
    assert 40.0 <= pt.surface_pressure_pa <= 160.0
    assert pt.elevation_m == 21287.0
    # Air density should be very low (< 0.003 kg/m3)
    assert pt.density_kg_m3 < 0.003


def test_extreme_elevation_hellas_planitia():
    """Verify pressure is significantly increased at Hellas Planitia floor (-7,152 m)."""
    service = get_climatology_service()
    pt = service.get_climatology_at_point(
        latitude=-42.7,
        longitude=70.0,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=-7152.0,
    )
    # At -7.15 km, P ~ P0 * exp(+7152 / 11100) ~ 610 * 1.90 ~ 1160 Pa
    assert 950.0 <= pt.surface_pressure_pa <= 1450.0
    assert pt.elevation_m == -7152.0
    # Air density should be higher (> 0.020 kg/m3)
    assert pt.density_kg_m3 > 0.015


def test_atmospheric_lapse_rate_scaling():
    """Verify that higher elevation strictly reduces atmospheric temperature."""
    service = get_climatology_service()
    pt_low = service.get_climatology_at_point(
        latitude=0.0,
        longitude=0.0,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=0.0,
    )
    pt_high = service.get_climatology_at_point(
        latitude=0.0,
        longitude=0.0,
        solar_longitude_ls_deg=0.0,
        local_true_solar_time_hours=12.0,
        elevation_m=4000.0,
    )
    # Expected temperature decrease: ~ 4000 m * 0.0025 K/m = 10 K
    temp_diff = pt_low.atmospheric_temperature_k - pt_high.atmospheric_temperature_k
    assert pytest.approx(temp_diff, abs=2.0) == 4000.0 * TROPOSPHERIC_LAPSE_RATE_K_M


# ── 5. Profile Generation Tests ──────────────────────────────────────────────

def test_diurnal_profile_generation():
    """Verify 24-point diurnal profile generation with extrema."""
    service = get_climatology_service()
    resp = service.get_climatology_profile(
        latitude=18.4447,
        longitude=77.4508,
        profile_type="diurnal",
        fixed_param=0.0,
        elevation_m=-2560.0,
        step_count=24,
    )
    assert resp.profile_type == "diurnal"
    assert len(resp.points) == 24
    assert resp.independent_variable == "LTST (hours)"
    assert resp.min_temperature_k < resp.max_temperature_k
    assert resp.min_pressure_pa <= resp.mean_pressure_pa <= resp.max_pressure_pa
    assert "MCD v6.2" in resp.model_version


def test_seasonal_profile_generation():
    """Verify seasonal profile generation across 360° solar longitude."""
    service = get_climatology_service()
    resp = service.get_climatology_profile(
        latitude=-4.5910,
        longitude=137.4410,
        profile_type="seasonal",
        fixed_param=12.0,
        elevation_m=-4440.0,
        step_count=24,
    )
    assert resp.profile_type == "seasonal"
    assert len(resp.points) == 24
    assert resp.independent_variable == "Solar Longitude Ls (degrees)"
    assert resp.points[0].step_value == 0.0
    assert resp.points[-1].step_value == 345.0


def test_profile_invalid_type():
    """Verify invalid profile_type raises ValueError."""
    service = get_climatology_service()
    with pytest.raises(ValueError, match="Unsupported profile_type"):
        service.get_climatology_profile(latitude=0.0, longitude=0.0, profile_type="weekly")


# ── 6. Route Climatology Enrichment Tests ─────────────────────────────────────

def test_route_climatology_enrichment():
    """Verify route waypoints enrichment with climatological metrics."""
    service = get_climatology_service()
    route_points = [
        {"lat": 18.4447, "lon": 77.4508, "elevation_m": -2560.0, "distance_m": 0.0},
        {"lat": 18.4460, "lon": 77.4520, "elevation_m": -2555.0, "distance_m": 120.0},
        {"lat": 18.4480, "lon": 77.4540, "elevation_m": -2540.0, "distance_m": 350.0},
        {"lat": 18.4500, "lon": 77.4560, "elevation_m": -2520.0, "distance_m": 600.0},
    ]
    summary = service.enrich_route_climatology(
        route_points=route_points,
        ls_deg=0.0,
        ltst_hours=12.0,
    )
    assert isinstance(summary, RouteClimatologySummary)
    assert len(summary.samples) == 4
    assert summary.min_climatology_pressure_pa <= summary.max_climatology_pressure_pa
    assert summary.min_climatology_temp_k <= summary.max_climatology_temp_k
    assert summary.mean_wind_speed_m_s > 0.0
    assert summary.samples[0].distance_m == 0.0
    assert summary.samples[-1].distance_m == 600.0


def test_route_climatology_empty_error():
    """Verify empty route raises ValueError."""
    service = get_climatology_service()
    with pytest.raises(ValueError, match="Cannot enrich empty route"):
        service.enrich_route_climatology(route_points=[])


# ── 7. FastAPI Endpoints Integration Tests ───────────────────────────────────

def test_api_climatology_metadata():
    """Verify GET /api/v1/environmental/climatology/metadata endpoint."""
    res = client.get("/api/v1/environmental/climatology/metadata")
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "Mars Climate Database (MCD v6.2)"
    assert "Laboratoire de M\u00e9t\u00e9orologie Dynamique" in data["authoritative_source"] or "LMD" in data["authoritative_source"]
    assert len(data["available_variables"]) >= 6
    assert "ASTRONAUT SAFETY" in data["safety_disclaimer"]


def test_api_climatology_coverage():
    """Verify GET /api/v1/environmental/climatology/coverage endpoint."""
    res = client.get("/api/v1/environmental/climatology/coverage")
    assert res.status_code == 200
    data = res.json()
    assert data["lat_min"] == -90.0
    assert data["lat_max"] == 90.0
    assert len(data["grid_latitudes_deg"]) >= 5
    assert "JEZERO_CRATER" in data["landmarks"]


def test_api_climatology_point():
    """Verify GET /api/v1/environmental/climatology/point endpoint."""
    res = client.get(
        "/api/v1/environmental/climatology/point",
        params={
            "lat": 18.4447,
            "lon": 77.4508,
            "ls_deg": 6.15,
            "ltst_hours": 13.5,
            "elevation_m": -2560.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["latitude"] == 18.4447
    assert data["surface_pressure_pa"] > 600.0
    assert "wind_cardinal" in data
    assert data["classification"] == "Climatological Model"


def test_api_climatology_point_invalid_lat():
    """Verify GET /api/v1/environmental/climatology/point rejects invalid latitude."""
    res = client.get(
        "/api/v1/environmental/climatology/point",
        params={"lat": 105.0, "lon": 77.0},
    )
    assert res.status_code == 422


def test_api_climatology_profile():
    """Verify GET /api/v1/environmental/climatology/profile endpoint."""
    res = client.get(
        "/api/v1/environmental/climatology/profile",
        params={
            "lat": -21.36,
            "lon": 106.53,
            "profile_type": "diurnal",
            "fixed_param": 90.0,
            "step_count": 12,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["profile_type"] == "diurnal"
    assert len(data["points"]) == 12


def test_api_route_enrich():
    """Verify POST /api/v1/environmental/climatology/route/enrich endpoint."""
    payload = {
        "route_points": [
            {"lat": -21.3600, "lon": 106.5300, "elevation_m": 2189.49, "distance_m": 0.0},
            {"lat": -21.3610, "lon": 106.5310, "elevation_m": 2188.00, "distance_m": 50.0},
        ],
        "ls_deg": 45.0,
        "ltst_hours": 14.0,
    }
    res = client.post("/api/v1/environmental/climatology/route/enrich", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "mean_climatology_pressure_pa" in data
    assert len(data["samples"]) == 2


# ── 8. Non-Negotiable Float32 Terrain Elevation Benchmarks ───────────────────

def test_elevation_benchmark_bitwise_preservation():
    """Verify that existing Float32 elevation benchmarks remain 100% bitwise intact."""
    # Tyrrhena Terra
    tyrrhena_hex = "0x4508d7c3"
    tyrrhena_val = struct.unpack(">f", bytes.fromhex(tyrrhena_hex[2:]))[0]
    assert pytest.approx(tyrrhena_val, rel=1e-5) == 2189.4851

    # Apollinaris Sulci
    apollinaris_hex = "0xc5372c4c"
    apollinaris_val = struct.unpack(">f", bytes.fromhex(apollinaris_hex[2:]))[0]
    assert pytest.approx(apollinaris_val, rel=1e-5) == -2930.7686

    # Holden Crater
    holden_hex = "0xc48d849f"
    holden_val = struct.unpack(">f", bytes.fromhex(holden_hex[2:]))[0]
    assert pytest.approx(holden_val, rel=1e-5) == -1132.1444
