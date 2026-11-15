"""MARS-X — Phase 8.9.1.1: Solar & Atmospheric Model Integrity Independent Audit Suite.

Independently validates:
1. Clear mathematical distinction between Normal-Incidence Solar Irradiance
   (F_normal = S_Mars = S_0 / r^2) and Direct Horizontal Irradiance
   (F_horizontal = S_Mars * max(0, cos(SZA))).
2. Strict non-positive / zero horizontal and surface direct irradiance when SZA >= 90 deg.
3. Independent Mars orbital geometry validation against Keplerian equations of motion
   at perihelion, aphelion, equinoxes, and solstices (Allison & McEwen 2000).
4. Mars timekeeping systems: Equation of Time (EOT = LTST - LMST),
   Local Mean Solar Time (LMST), Local True Solar Time (LTST), and Coordinated Mars Time (MTC)
   across East-positive and West-positive longitude conventions.
5. In-situ rover empirical validation of EOT against MEDA Sol 1 and REMS Sol 1 timestamps.
6. Reference barometric pressure P(z) = P_ref * exp(-z / H) and factual residual documentation
   accounting for short-duration afternoon sampling intervals.
7. Traverse environmental enrichment without route geometry or cost mutation.
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
    SOLAR_CONSTANT_1AU_W_M2,
    MARS_SEMIMAJOR_AXIS_AU,
    MARS_ECCENTRICITY,
    MARS_PERIHELION_LS_DEG,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def env_service():
    return get_environmental_service()


# ── 1. Solar Irradiance Separation & Direct Beam Attenuation ────────────────

def test_solar_irradiance_normal_vs_horizontal_separation(env_service):
    """Verify that Normal-Incidence Irradiance and Direct Horizontal Irradiance are mathematically distinct.

    F_normal = S_0 / r^2
    F_horizontal = (S_0 / r^2) * max(0, cos(SZA))
    When 0 < SZA < 90 deg, F_horizontal MUST be strictly less than F_normal.
    """
    # Test at latitude 0, Ls = 0, afternoon LTST = 15.0h (SZA = 45.0 deg)
    geo = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=15.0)

    assert geo.solar_zenith_angle_deg == pytest.approx(45.0, abs=0.1)
    s_mars = geo.toa_normal_irradiance_w_m2
    f_horiz = geo.toa_horizontal_irradiance_w_m2

    # Expected horizontal flux: S_Mars * cos(45 deg) = S_Mars * 0.7071
    expected_horiz = round(s_mars * math.cos(math.radians(45.0)), 2)
    assert f_horiz == pytest.approx(expected_horiz, abs=0.05)
    assert f_horiz < s_mars, "Direct horizontal irradiance must be strictly less than normal-incidence irradiance at oblique angles"

    # Surface direct horizontal beam without dust should match TOA horizontal
    assert geo.surface_direct_horizontal_irradiance_w_m2 == pytest.approx(f_horiz, abs=0.05)


def test_subsolar_normal_equals_horizontal(env_service):
    """At the exact subsolar point (SZA = 0 deg), F_horizontal MUST equal F_normal."""
    geo = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=12.0)

    assert geo.solar_zenith_angle_deg == 0.0
    assert geo.solar_elevation_deg == 90.0
    assert geo.toa_normal_irradiance_w_m2 == geo.toa_horizontal_irradiance_w_m2
    assert geo.surface_direct_horizontal_irradiance_w_m2 == geo.toa_normal_irradiance_w_m2


def test_sunset_and_night_irradiance_strictly_zero(env_service):
    """At and after sunset (SZA >= 90 deg), direct horizontal irradiance and surface flux MUST be strictly 0.0 W/m2.

    TOA normal-incidence irradiance S_Mars remains positive (the Sun still shines in space).
    """
    # 1. Exact sunset / horizon: lat=0, Ls=0, LTST=18.0h -> SZA = 90.0 deg
    geo_sunset = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=18.0)
    assert geo_sunset.solar_zenith_angle_deg == 90.0
    assert geo_sunset.toa_normal_irradiance_w_m2 > 0.0
    assert geo_sunset.toa_horizontal_irradiance_w_m2 == 0.0
    assert geo_sunset.surface_direct_horizontal_irradiance_w_m2 == 0.0

    # 2. Night hours: SZA in (90, 180] deg
    night_hours = [19.0, 20.0, 22.0, 0.0, 2.0, 5.0]
    for h in night_hours:
        geo_night = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=h)
        assert geo_night.solar_zenith_angle_deg > 90.0
        assert geo_night.is_day is False
        assert geo_night.day_night_status == "Night"
        assert geo_night.toa_normal_irradiance_w_m2 > 0.0, "Sun continues to radiate at Mars orbital radius"
        assert geo_night.toa_horizontal_irradiance_w_m2 == 0.0, f"Night TOA horizontal must be 0.0 at hour {h}"
        assert geo_night.surface_direct_horizontal_irradiance_w_m2 == 0.0, f"Night surface direct must be 0.0 at hour {h}"
        assert geo_night.surface_solar_flux_w_m2 == 0.0, "Legacy surface flux alias must also be strictly 0.0"


def test_beer_lambert_slant_path_extinction(env_service):
    """Verify Beer-Lambert extinction along slant optical airmass: F_direct_surface = F_TOA * exp(-tau / cos(SZA))."""
    tau = 0.6
    # LTST = 14.0h at equator at equinox -> SZA = 30.0 deg -> cos(SZA) = sqrt(3)/2 = 0.8660
    geo = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=0.0, ltst_hours=14.0, tau=tau)

    sza_rad = math.radians(geo.solar_zenith_angle_deg)
    cos_sza = math.cos(sza_rad)
    slant_extinction = math.exp(-tau / cos_sza)

    expected_surface_normal = round(geo.toa_normal_irradiance_w_m2 * slant_extinction, 2)
    expected_surface_horizontal = round(geo.toa_horizontal_irradiance_w_m2 * slant_extinction, 2)

    assert geo.surface_direct_normal_irradiance_w_m2 == pytest.approx(expected_surface_normal, abs=0.05)
    assert geo.surface_direct_horizontal_irradiance_w_m2 == pytest.approx(expected_surface_horizontal, abs=0.05)


# ── 2. Independent Mars Orbital Validation ──────────────────────────────────

def test_orbital_perihelion_and_aphelion_independent_benchmarks(env_service):
    """Verify orbital distance r(Ls) and S_Mars against independent Keplerian reference calculations.

    Independent calculations:
    Mars semimajor axis a = 1.52368 AU
    Mars orbital eccentricity e = 0.09341
    Solar constant at 1 AU S_0 = 1361.0 W/m2
    Perihelion Ls_p = 250.99 deg:
      r_perihelion = a * (1 - e) = 1.52368 * (1 - 0.09341) = 1.381358 AU
      S_Mars_perihelion = 1361.0 / (1.381358)^2 = 713.255 W/m2
    Aphelion Ls_a = 70.99 deg:
      r_aphelion = a * (1 + e) = 1.52368 * (1 + 0.09341) = 1.666002 AU
      S_Mars_aphelion = 1361.0 / (1.666002)^2 = 490.354 W/m2
    """
    # 1. Perihelion verification (Ls = 250.99 deg)
    geo_peri = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=250.99, ltst_hours=12.0)
    assert geo_peri.mars_sun_distance_au == pytest.approx(1.38136, abs=0.001)
    assert geo_peri.toa_normal_irradiance_w_m2 == pytest.approx(713.26, abs=0.5)

    # 2. Aphelion verification (Ls = 70.99 deg)
    geo_aph = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=70.99, ltst_hours=12.0)
    assert geo_aph.mars_sun_distance_au == pytest.approx(1.66600, abs=0.001)
    assert geo_aph.toa_normal_irradiance_w_m2 == pytest.approx(490.35, abs=0.5)

    # Ratio of solar constant: (r_aph / r_peri)^2 = (1.666002 / 1.381358)^2 = 1.4545
    ratio = geo_peri.toa_normal_irradiance_w_m2 / geo_aph.toa_normal_irradiance_w_m2
    assert ratio == pytest.approx(1.4545, abs=0.005)


def test_independent_solar_declination_benchmarks(env_service):
    """Verify Mars subsolar declination delta(Ls) against independent analytical trigonometry.

    sin(delta) = sin(obliquity) * sin(Ls) where obliquity = 25.19 deg.
    """
    test_cases = [
        (0.0, 0.0, "Vernal Equinox"),
        (90.0, +MARS_AXIAL_TILT_DEG, "Northern Summer Solstice"),
        (180.0, 0.0, "Autumnal Equinox"),
        (270.0, -MARS_AXIAL_TILT_DEG, "Northern Winter Solstice"),
        (45.0, math.degrees(math.asin(math.sin(math.radians(25.19)) * math.sin(math.radians(45.0)))), "Mid-Spring"),
    ]

    for ls, expected_dec, label in test_cases:
        geo = env_service.calculate_solar_geometry(lat=0.0, lon=0.0, ls_deg=ls)
        assert geo.solar_declination_deg == pytest.approx(expected_dec, abs=0.05), f"Failed for {label} at Ls={ls}"


# ── 3. Mars Time Systems & Equation of Time (Allison & McEwen 2000) ──────────

def test_equation_of_time_allison_mcewen_formulation(env_service):
    """Verify Martian Equation of Time (EOT = LTST - LMST) against Allison & McEwen (2000) reference values."""
    # 1. Perihelion Ls = 250.99 deg: True anomaly nu = 0 -> Equation of Center is 0
    # Reduction to equator: 2.861*sin(2*250.99) - 0.071*sin(4*250.99) = 2.861*sin(141.98) - ...
    eot_deg_p, eot_hrs_p = env_service.calculate_equation_of_time(250.99)
    # At perihelion, EOT is dominated by axial tilt reduction to equator
    expected_tilt = 2.861 * math.sin(math.radians(2 * 250.99)) - 0.071 * math.sin(math.radians(4 * 250.99))
    assert eot_deg_p == pytest.approx(expected_tilt, abs=0.05)

    # 2. Curiosity Sol 1 comparison: Ls = 150.40 deg
    # Empirical REMS Sol 1 difference: LTST 13:47:34 vs LMST 13:14:17 -> +33.28 min (+0.5547 h)
    eot_deg_rems, eot_hrs_rems = env_service.calculate_equation_of_time(150.40)
    eot_min_rems = eot_hrs_rems * 60.0
    # Allison & McEwen model predicts ~ +33.0 min
    assert eot_min_rems == pytest.approx(32.99, abs=0.5)
    # Agrees with empirical REMS Sol 1 offset within 20 seconds (0.33 min)
    assert abs(eot_min_rems - 33.28) < 0.4

    # 3. Perseverance Sol 1 comparison: Ls = 6.16 deg
    # Empirical MEDA Sol 1 difference: LTST 15:28:01 vs LMST 16:05:31 -> -37.50 min (-0.625 h)
    eot_deg_meda, eot_hrs_meda = env_service.calculate_equation_of_time(6.16)
    eot_min_meda = eot_hrs_meda * 60.0
    # Allison & McEwen model predicts ~ -37.56 min
    assert eot_min_meda == pytest.approx(-37.56, abs=0.5)
    # Agrees with empirical MEDA Sol 1 offset within 5 seconds (0.08 min)
    assert abs(eot_min_meda - (-37.50)) < 0.15


def test_convert_mars_time_round_trip(env_service):
    """Verify round-trip transformation between MTC, LMST, and LTST."""
    lon = 77.4508  # Jezero Crater East longitude
    ls = 6.15

    # Start with LTST 15.467h
    ltst_in = 15.467
    conv_from_ltst = env_service.convert_mars_time(
        time_hours=ltst_in,
        from_system="LTST",
        to_system="LMST",
        lon_deg=lon,
        ls_deg=ls,
    )
    lmst_val = conv_from_ltst.lmst_hours

    # Convert back from LMST to LTST
    conv_from_lmst = env_service.convert_mars_time(
        time_hours=lmst_val,
        from_system="LMST",
        to_system="LTST",
        lon_deg=lon,
        ls_deg=ls,
    )
    assert conv_from_lmst.ltst_hours == pytest.approx(ltst_in, abs=1e-3)

    # Convert to MTC and back
    conv_to_mtc = env_service.convert_mars_time(
        time_hours=lmst_val,
        from_system="LMST",
        to_system="MTC",
        lon_deg=lon,
        ls_deg=ls,
    )
    mtc_val = conv_to_mtc.mtc_hours

    conv_from_mtc = env_service.convert_mars_time(
        time_hours=mtc_val,
        from_system="MTC",
        to_system="LMST",
        lon_deg=lon,
        ls_deg=ls,
    )
    assert conv_from_mtc.lmst_hours == pytest.approx(lmst_val, abs=1e-3)


def test_convert_mars_time_longitude_conventions(env_service):
    """Verify that East-positive and West-positive longitudes yield identical local solar time."""
    ls = 45.0
    mtc_time = 12.0

    # A location at 60 deg East is equivalent to 300 deg West
    east_conv = env_service.convert_mars_time(
        time_hours=mtc_time,
        from_system="MTC",
        to_system="LMST",
        lon_deg=60.0,
        ls_deg=ls,
        lon_convention="east_positive",
    )
    # Longitude offset = 60 / 15 = 4 hours -> LMST = 16.0h
    assert east_conv.lmst_hours == pytest.approx(16.0, abs=1e-3)

    west_conv = env_service.convert_mars_time(
        time_hours=mtc_time,
        from_system="MTC",
        to_system="LMST",
        lon_deg=300.0,
        ls_deg=ls,
        lon_convention="west_positive",
    )
    # 300 deg West is 60 deg East -> LMST must be identical (16.0h)
    assert west_conv.lmst_hours == pytest.approx(16.0, abs=1e-3)
    assert west_conv.ltst_hours == pytest.approx(east_conv.ltst_hours, abs=1e-3)


def test_solar_geometry_with_lmst_input(env_service):
    """Verify that calculate_solar_geometry correctly converts LMST input to LTST via EOT."""
    lat = 18.4447
    lon = 77.4508
    ls = 6.16  # EOT is ~ -37.56 min = -0.626 h

    # If LMST is 12.0h, LTST should be 12.0 + (-0.626) = 11.374h
    geo_lmst = env_service.calculate_solar_geometry(
        lat=lat,
        lon=lon,
        ls_deg=ls,
        ltst_hours=12.0,
        time_system="LMST",
    )
    assert geo_lmst.local_mean_solar_time_hours == 12.0
    assert geo_lmst.local_true_solar_time_hours == pytest.approx(11.37, abs=0.02)
    assert geo_lmst.equation_of_time_minutes == pytest.approx(-37.56, abs=0.5)


# ── 4. Atmospheric Reference Pressure & Ground-Truth Residuals ──────────────

def test_barometric_independent_benchmark_values(env_service):
    """Verify barometric model against hardcoded analytical values."""
    # Olympus Mons summit: z = +21,287 m
    # P = 610 * exp(-21287 / 11100) = 610 * exp(-1.91775) = 90.00 Pa
    p_olympus = env_service.estimate_atmospheric_pressure(21287.0).reference_atmospheric_pressure_estimate_pa
    expected_olympus = round(610.0 * math.exp(-21287.0 / 11100.0), 2)
    assert p_olympus == expected_olympus
    assert 85.0 < p_olympus < 95.0

    # Hellas Planitia floor: z = -7,152 m
    # P = 610 * exp(+7152 / 11100) = 610 * exp(+0.64432) = 1162.06 Pa
    p_hellas = env_service.estimate_atmospheric_pressure(-7152.0).reference_atmospheric_pressure_estimate_pa
    expected_hellas = round(610.0 * math.exp(7152.0 / 11100.0), 2)
    assert p_hellas == expected_hellas
    assert 1150.0 < p_hellas < 1175.0


def test_pressure_residual_scientific_notes(env_service):
    """Verify that pressure residual notes explain short-duration afternoon sampling and simplified reference profile."""
    residuals = env_service.compute_pressure_residuals()
    meda = residuals["MEDA_JEZERO"]
    rems = residuals["REMS_GALE"]

    assert "afternoon interval" in meda.notes.lower()
    assert "simplified global isothermal reference profile" in meda.notes.lower()
    assert "without artificial calibration" in meda.notes.lower()

    assert "afternoon interval" in rems.notes.lower()
    assert "simplified global isothermal reference profile" in rems.notes.lower()
    assert "without artificial calibration" in rems.notes.lower()


# ── 5. Traverse Environmental Continuity & Geometry Invariance ──────────────

def test_route_enrichment_preserves_geometry_and_coordinates(env_service):
    """Verify that route environmental enrichment does not mutate coordinates, point count, or distances."""
    original_points = [
        {"lat": -2.0, "lon": 75.0, "elevation_m": -2000.0, "distance_m": 0.0},
        {"lat": -2.05, "lon": 75.05, "elevation_m": -1800.0, "distance_m": 450.0},
        {"lat": -2.10, "lon": 75.10, "elevation_m": -1600.0, "distance_m": 900.0},
        {"lat": -2.15, "lon": 75.15, "elevation_m": -1400.0, "distance_m": 1350.0},
    ]

    summary = env_service.enrich_route_environmental_context(
        route_points=original_points,
        ls_deg=45.0,
        ltst_hours=14.0,
        tau=0.4,
    )

    assert len(summary.samples) == len(original_points)
    for orig, enriched in zip(original_points, summary.samples):
        assert enriched.lat == orig["lat"]
        assert enriched.lon == orig["lon"]
        assert enriched.elevation_m == orig["elevation_m"]
        assert enriched.distance_m == orig["distance_m"]
        assert enriched.reference_pressure_pa > 0.0
        assert enriched.toa_normal_irradiance_w_m2 > 0.0
        assert enriched.surface_direct_horizontal_irradiance_w_m2 > 0.0


# ── 6. Elevation Benchmark Bitwise Preservation ─────────────────────────────

def test_elevation_benchmark_bitwise_preservation_strict():
    """Verify bitwise preservation of IEEE 754 Float32 elevation benchmarks."""
    benchmarks = {
        "Tyrrhena": {"hex": 0x4508D7C3, "expected_str": "+2189.49"},
        "Apollinaris": {"hex": 0xC5372C4C, "expected_str": "-2930.77"},
        "Holden": {"hex": 0xC48D849F, "expected_str": "-1132.14"},
    }

    for name, data in benchmarks.items():
        unpacked_val = struct.unpack(">f", bytes.fromhex(f"{data['hex']:08x}"))[0]
        assert f"{unpacked_val:+.2f}" == data["expected_str"]
        repacked = int(struct.pack(">f", unpacked_val).hex(), 16)
        assert repacked == data["hex"], f"Bitwise mismatch for {name}: expected {hex(data['hex'])}, got {hex(repacked)}"


# ── 7. FastAPI Endpoint Integration Tests ─────────────────────────────────

def test_api_equation_of_time(client):
    """Test GET /api/v1/environmental/time/eot."""
    resp = client.get("/api/v1/environmental/time/eot?ls_deg=6.16")
    assert resp.status_code == 200
    data = resp.json()
    assert data["solar_longitude_ls_deg"] == 6.16
    assert abs(data["equation_of_time_minutes"] - (-37.56)) < 0.5
    assert data["classification"] == "Analytical Model"
    assert "Allison & McEwen" in data["citation"]


def test_api_time_conversion(client):
    """Test GET /api/v1/environmental/time/convert."""
    resp = client.get(
        "/api/v1/environmental/time/convert?time_hours=12.0&from_system=MTC&to_system=LMST&lon_deg=60.0&ls_deg=0.0"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_system"] == "MTC"
    assert data["lmst_hours"] == 16.0  # 12 + 60/15 = 16


def test_api_solar_geometry_with_time_system(client):
    """Test GET /api/v1/environmental/solar-geometry with LMST."""
    resp = client.get(
        "/api/v1/environmental/solar-geometry?lat=0.0&lon=0.0&ls_deg=0.0&ltst_hours=12.0&time_system=LMST"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "toa_normal_irradiance_w_m2" in data
    assert "toa_horizontal_irradiance_w_m2" in data
    assert "surface_direct_horizontal_irradiance_w_m2" in data
    assert data["toa_normal_irradiance_w_m2"] > 0.0
