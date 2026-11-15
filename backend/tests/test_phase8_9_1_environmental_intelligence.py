"""MARS-X — Phase 8.9.1: Environmental Intelligence Test Suite.

Scientifically validates:
1. Analytical barometric pressure reference model P(z) = P_ref * exp(-z / H).
2. Explicit residual calculation against MEDA and REMS ground truth.
3. Deterministic Mars solar geometry (Allison & McEwen 2000), equinox/solstice declinations, SZA, flux.
4. Non-positive solar flux enforcement when SZA >= 90 deg.
5. Historical in-situ rover observations from Mars 2020 Perseverance and MSL Curiosity.
6. Route environmental profile enrichment.
7. FastAPI endpoint behavior and schema compliance.
8. Bitwise preservation of IEEE 754 Float32 elevation benchmarks.
"""

import math
import struct
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.science.environmental_service import (
    EnvironmentalIntelligenceService,
    get_environmental_service,
    P_REF_DEFAULT_PA,
    SCALE_HEIGHT_DEFAULT_M,
    MARS_AXIAL_TILT_DEG,
)
from app.science.environmental_models import (
    AtmosphericPressureEstimate,
    PressureResidualBenchmark,
    MarsSolarGeometry,
    HistoricalWeatherSummary,
    RouteEnvironmentalSummary,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def env_service():
    return get_environmental_service()


# ── 1. Atmospheric Reference Pressure Tests ─────────────────────────────────

def test_barometric_formula_exact_elevations(env_service):
    """Verify analytical pressure formula P(z) = P_ref * exp(-z / H) at exact test elevations."""
    # z = 0 m (Datum)
    est_0 = env_service.estimate_atmospheric_pressure(0.0)
    assert est_0.reference_atmospheric_pressure_estimate_pa == P_REF_DEFAULT_PA
    assert est_0.classification == "Analytical Model"
    assert est_0.vertical_datum == "MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)"

    # z = +11,100 m (1 scale height up) -> P = 610 * exp(-1) = 224.406... -> 224.41 Pa
    est_scale_up = env_service.estimate_atmospheric_pressure(11100.0)
    expected_up = round(610.0 * math.exp(-1.0), 2)
    assert est_scale_up.reference_atmospheric_pressure_estimate_pa == expected_up

    # z = -11,100 m (1 scale height down) -> P = 610 * exp(+1) = 1658.089... -> 1658.09 Pa
    est_scale_down = env_service.estimate_atmospheric_pressure(-11100.0)
    expected_down = round(610.0 * math.exp(1.0), 2)
    assert est_scale_down.reference_atmospheric_pressure_estimate_pa == expected_down

    # Custom P_ref and H
    est_custom = env_service.estimate_atmospheric_pressure(5000.0, p_ref_pa=700.0, scale_height_m=10000.0)
    expected_custom = round(700.0 * math.exp(-0.5), 2)
    assert est_custom.reference_atmospheric_pressure_estimate_pa == expected_custom


def test_barometric_monotonicity(env_service):
    """Verify that atmospheric pressure strictly decreases with increasing elevation."""
    elevations = [-5000.0, -2500.0, 0.0, 2500.0, 5000.0, 10000.0, 20000.0]
    pressures = [
        env_service.estimate_atmospheric_pressure(z).reference_atmospheric_pressure_estimate_pa
        for z in elevations
    ]
    for i in range(len(pressures) - 1):
        assert pressures[i] > pressures[i + 1], f"P({elevations[i]}) must exceed P({elevations[i+1]})"


def test_barometric_input_validation(env_service):
    """Verify that invalid elevations or scale heights raise ValueError."""
    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(float("nan"))

    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(float("inf"))

    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(-25000.0)  # Outside Mars envelope

    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(35000.0)  # Higher than Olympus Mons

    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(0.0, p_ref_pa=-100.0)

    with pytest.raises(ValueError):
        env_service.estimate_atmospheric_pressure(0.0, scale_height_m=0.0)


# ── 2. Pressure Residual Benchmarks ─────────────────────────────────────────

def test_pressure_residuals_computation(env_service):
    """Verify that residuals against MEDA and REMS are explicitly computed, signed, and not silently zeroed."""
    residuals = env_service.compute_pressure_residuals()
    assert "MEDA_JEZERO" in residuals
    assert "REMS_GALE" in residuals

    # Jezero MEDA benchmark
    jezero = residuals["MEDA_JEZERO"]
    assert jezero.elevation_m == -2560.0
    assert jezero.model_pressure_pa == round(610.0 * math.exp(2560.0 / 11100.0), 2)
    assert jezero.observed_mean_pressure_pa > 700.0
    assert jezero.residual_pa == round(jezero.model_pressure_pa - jezero.observed_mean_pressure_pa, 2)
    assert abs(jezero.residual_pa) > 0.0, "Model must not be silently calibrated to 0 residual"
    assert jezero.classification == "Derived Estimate"
    assert "Perseverance" in jezero.station_name

    # Gale REMS benchmark
    gale = residuals["REMS_GALE"]
    assert gale.elevation_m == -4440.0
    assert gale.model_pressure_pa == round(610.0 * math.exp(4440.0 / 11100.0), 2)
    assert gale.observed_mean_pressure_pa > 650.0
    assert gale.residual_pa == round(gale.model_pressure_pa - gale.observed_mean_pressure_pa, 2)
    assert abs(gale.residual_pa) > 0.0, "Model must not be silently calibrated to 0 residual"
    assert "Curiosity" in gale.station_name


# ── 3. Mars Solar Geometry & Irradiance Tests ──────────────────────────────

def test_solar_declination_seasons(env_service):
    """Verify Mars solar declination at equinoxes and solstices."""
    # Vernal Equinox (Ls = 0 deg)
    geo_ve = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0)
    assert geo_ve.solar_declination_deg == 0.0
    assert geo_ve.season_name == "Northern Spring / Southern Autumn"

    # Northern Summer Solstice (Ls = 90 deg) -> declination = +25.19 deg
    geo_ss = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=90.0)
    assert abs(geo_ss.solar_declination_deg - MARS_AXIAL_TILT_DEG) < 0.05
    assert geo_ss.season_name == "Northern Summer / Southern Winter"

    # Autumnal Equinox (Ls = 180 deg) -> declination = 0.0 deg
    geo_ae = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=180.0)
    assert abs(geo_ae.solar_declination_deg) < 0.05
    assert geo_ae.season_name == "Northern Autumn / Southern Spring"

    # Southern Summer Solstice (Ls = 270 deg) -> declination = -25.19 deg
    geo_ws = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=270.0)
    assert abs(geo_ws.solar_declination_deg - (-MARS_AXIAL_TILT_DEG)) < 0.05
    assert geo_ws.season_name == "Northern Winter / Southern Summer"


def test_solar_zenith_angle_and_noon(env_service):
    """Verify SZA at sub-solar point and midnight."""
    # Equator at Equinox at solar noon (LTST = 12.0) -> SZA = 0.0 deg, elevation = 90.0 deg
    geo_noon = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=12.0)
    assert geo_noon.solar_zenith_angle_deg == 0.0
    assert geo_noon.solar_elevation_deg == 90.0
    assert geo_noon.is_day is True
    assert geo_noon.day_night_status == "Day"
    assert geo_noon.top_of_atmosphere_solar_flux_w_m2 > 500.0

    # Equator at Equinox at midnight (LTST = 0.0) -> SZA = 180.0 deg, elevation = -90.0 deg
    geo_midnight = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=0.0)
    assert geo_midnight.solar_zenith_angle_deg == 180.0
    assert geo_midnight.solar_elevation_deg == -90.0
    assert geo_midnight.is_day is False
    assert geo_midnight.day_night_status == "Night"


def test_night_solar_flux_strictly_non_positive(env_service):
    """STRICT REQUIREMENT: When SZA >= 90 deg, solar flux MUST be strictly 0.0 W/m2."""
    for ltst in [0.0, 1.0, 3.0, 4.0, 20.0, 22.0, 23.5]:
        geo = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=ltst)
        if geo.solar_zenith_angle_deg >= 90.0:
            assert geo.top_of_atmosphere_solar_flux_w_m2 == 0.0, (
                f"Night TOA flux must be 0.0 at LTST {ltst}, got {geo.top_of_atmosphere_solar_flux_w_m2}"
            )
            assert geo.surface_solar_flux_w_m2 == 0.0, (
                f"Night surface flux must be 0.0 at LTST {ltst}, got {geo.surface_solar_flux_w_m2}"
            )


def test_polar_day_and_polar_night(env_service):
    """Verify polar day and polar night behavior at high latitudes."""
    # North Pole (lat = 85 deg N) at Northern Summer Solstice (Ls = 90 deg) -> Midnight Sun / Polar Day
    geo_polar_day = env_service.calculate_solar_geometry(lat=85.0, lon=0.0, ls_deg=90.0, ltst_hours=0.0)
    assert geo_polar_day.polar_condition == "Polar Day (Midnight Sun)"
    assert geo_polar_day.is_day is True
    assert geo_polar_day.sunrise_hour is None
    assert geo_polar_day.sunset_hour is None

    # North Pole (lat = 85 deg N) at Northern Winter Solstice (Ls = 270 deg) -> Polar Night
    geo_polar_night = env_service.calculate_solar_geometry(lat=85.0, lon=0.0, ls_deg=270.0, ltst_hours=12.0)
    assert geo_polar_night.polar_condition == "Polar Night"
    assert geo_polar_night.is_day is False
    assert geo_polar_night.sunrise_hour is None
    assert geo_polar_night.sunset_hour is None
    assert geo_polar_night.surface_solar_flux_w_m2 == 0.0


def test_atmospheric_dust_attenuation(env_service):
    """Verify that Beer-Lambert attenuation strictly reduces surface flux when tau > 0."""
    geo_clean = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=12.0, tau=None)
    geo_dusty_light = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=12.0, tau=0.3)
    geo_dusty_heavy = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=12.0, tau=1.5)

    assert geo_clean.surface_solar_flux_w_m2 == geo_clean.top_of_atmosphere_solar_flux_w_m2
    assert geo_dusty_light.surface_solar_flux_w_m2 < geo_clean.surface_solar_flux_w_m2
    assert geo_dusty_heavy.surface_solar_flux_w_m2 < geo_dusty_light.surface_solar_flux_w_m2


# ── 4. Historical In-Situ Rover Observation Parsers ────────────────────────

def test_meda_sol1_parser(env_service):
    """Verify that MEDA Sol 1 authentic PDS4 delimited tables are parsed with correct summary stats."""
    meda = env_service.get_historical_meda_sol1()
    assert meda.station_id == "MEDA_JEZERO"
    assert meda.total_samples > 2000
    assert meda.pressure_summary_pa is not None
    assert 700.0 < meda.pressure_summary_pa["mean_pa"] < 750.0
    assert len(meda.sample_records) == 5
    assert meda.classification == "Historical Observation"
    assert "HISTORICAL IN-SITU POINT OBSERVATION ONLY" in meda.temporal_disclaimer


def test_rems_sol1_parser(env_service):
    """Verify that REMS Sol 1 authentic PDS4 fixed-width tables are parsed with correct summary stats."""
    rems = env_service.get_historical_rems_sol1()
    assert rems.station_id == "REMS_GALE"
    assert rems.total_samples > 400
    assert rems.pressure_summary_pa is not None
    assert 680.0 < rems.pressure_summary_pa["mean_pa"] < 730.0
    assert rems.ambient_temp_summary_k is not None
    assert 200.0 < rems.ambient_temp_summary_k["mean_k"] < 300.0
    assert rems.classification == "Historical Observation"


# ── 5. Route Environmental Context Enrichment ───────────────────────────────

def test_route_environmental_enrichment(env_service):
    """Verify that route waypoints are correctly enriched with pressure and solar flux."""
    route_pts = [
        {"lat": -2.0, "lon": 75.0, "elevation_m": -2000.0, "distance_m": 0.0},
        {"lat": -2.05, "lon": 75.05, "elevation_m": -1500.0, "distance_m": 500.0},
        {"lat": -2.1, "lon": 75.1, "elevation_m": -1000.0, "distance_m": 1000.0},
    ]

    summary = env_service.enrich_route_environmental_context(
        route_points=route_pts,
        ls_deg=0.0,
        ltst_hours=12.0,
        tau=0.5,
    )

    assert summary.classification == "Derived Estimate"
    assert len(summary.samples) == 3
    # Elevation rises from -2000 m to -1000 m -> Pressure must decrease
    assert summary.samples[0].reference_pressure_pa > summary.samples[2].reference_pressure_pa
    assert summary.daylight_percentage == 100.0
    assert summary.mean_surface_flux_w_m2 > 0.0


# ── 6. FastAPI Endpoints Integration Tests ─────────────────────────────────

def test_endpoint_environmental_metadata(client):
    """Test GET /api/v1/environmental/metadata."""
    resp = client.get("/api/v1/environmental/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert "Analytical Hydrostatic Barometric Pressure" in data["available_models"][0]
    assert data["reference_parameters"]["p_ref_pa"] == 610.0
    assert "Historical Observation" in data["classification_tiers"]


def test_endpoint_pressure_estimate(client):
    """Test GET /api/v1/environmental/pressure/estimate."""
    resp = client.get("/api/v1/environmental/pressure/estimate?elevation_m=-2560.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["elevation_m"] == -2560.0
    assert round(data["reference_atmospheric_pressure_estimate_pa"], 0) == 768.0

    # Error handling on out-of-bounds
    err_resp = client.get("/api/v1/environmental/pressure/estimate?elevation_m=50000.0")
    assert err_resp.status_code == 400


def test_endpoint_pressure_residuals(client):
    """Test GET /api/v1/environmental/pressure/residuals."""
    resp = client.get("/api/v1/environmental/pressure/residuals")
    assert resp.status_code == 200
    data = resp.json()
    assert "MEDA_JEZERO" in data
    assert "REMS_GALE" in data
    assert data["MEDA_JEZERO"]["residual_pa"] > 0.0


def test_endpoint_solar_geometry(client):
    """Test GET /api/v1/environmental/solar-geometry."""
    resp = client.get("/api/v1/environmental/solar-geometry?lat=0.0&lon=0.0&ls_deg=0.0&ltst_hours=12.0&tau=0.4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_day"] is True
    assert data["solar_elevation_deg"] == 90.0
    assert data["surface_solar_flux_w_m2"] > 0.0


def test_endpoint_historical_rovers(client):
    """Test GET historical MEDA and REMS endpoints."""
    resp_meda = client.get("/api/v1/environmental/historical/meda")
    assert resp_meda.status_code == 200
    assert resp_meda.json()["station_id"] == "MEDA_JEZERO"

    resp_rems = client.get("/api/v1/environmental/historical/rems")
    assert resp_rems.status_code == 200
    assert resp_rems.json()["station_id"] == "REMS_GALE"


def test_endpoint_route_enrich(client):
    """Test POST /api/v1/environmental/route/enrich."""
    payload = {
        "route_points": [
            {"lat": -2.0, "lon": 75.0, "elevation_m": -2000.0, "distance_m": 0.0},
            {"lat": -2.1, "lon": 75.1, "elevation_m": -1500.0, "distance_m": 1000.0},
        ],
        "ls_deg": 45.0,
        "ltst_hours": 14.0,
        "tau": 0.3,
    }
    resp = client.post("/api/v1/environmental/route/enrich", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mean_pressure_pa"] > 0.0
    assert len(data["samples"]) == 2


# ── 7. Elevation Benchmark Bitwise Preservation ─────────────────────────────

def test_elevation_benchmark_bitwise_preservation():
    """Verify bitwise preservation of IEEE 754 Float32 elevation benchmarks from Phase 8.8.1/8.8.2.1."""
    # Benchmark definitions
    benchmarks = {
        "Tyrrhena": {"hex": 0x4508D7C3, "expected_val": struct.unpack(">f", bytes.fromhex("4508d7c3"))[0]},
        "Apollinaris": {"hex": 0xC5372C4C, "expected_val": struct.unpack(">f", bytes.fromhex("c5372c4c"))[0]},
        "Holden": {"hex": 0xC48D849F, "expected_val": struct.unpack(">f", bytes.fromhex("c48d849f"))[0]},
    }

    assert f"{benchmarks['Tyrrhena']['expected_val']:+.2f}" == "+2189.49"
    assert f"{benchmarks['Apollinaris']['expected_val']:+.2f}" == "-2930.77"
    assert f"{benchmarks['Holden']['expected_val']:+.2f}" == "-1132.14"

    # Verify bitwise roundtrip
    for name, b in benchmarks.items():
        packed = struct.pack(">f", b["expected_val"])
        unpacked_hex = int(packed.hex(), 16)
        assert unpacked_hex == b["hex"], f"Bitwise IEEE 754 mismatch for {name}: expected {hex(b['hex'])}, got {hex(unpacked_hex)}"
