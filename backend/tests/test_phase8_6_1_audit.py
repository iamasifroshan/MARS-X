"""Phase 8.6.1: Scientific Integration Verification & Correction Test Suite.

Audits and verifies:
1. MOLA 4 ppd resolution calculation, native dimensions, and clerical discrepancy reconciliation.
2. USGS SIM 3292 Geological unit count (exact 44 distinct units across 1,311 polygon features).
3. USGS SIM 3292 CRS verification (GCS_Mars_2000_Sphere, decimal degrees, and 3 known landmark points).
4. MGS TES Global Thermal Inertia calibration, quantization uncertainty (+/-2.5%), and indicative interpretations.
5. 2001 Mars Odyssey THEMIS 100m IR resolution semantics (100m nadir camera vs. 256 ppd mosaic tile grid).
"""

import os
import math
import struct
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.science.geology_service import get_geology_service
from app.science.thermal_service import get_thermal_service, get_themis_service

client = TestClient(app)


def test_mola_4ppd_resolution_audit():
    """Verify equatorial pixel spacing and clarify the 4,630.8 m/px clerical discrepancy."""
    # Mars radii
    r_iau = 3396190.0  # IAU Mars 2000 Sphere
    r_mola = 3396000.0  # MOLA Mission Datum Sphere

    # 4 ppd equatorial circumferences and pixel spacing:
    # Circumference = 2 * pi * R
    # 4 ppd = 1440 pixels per 360 degrees
    spacing_iau = (2.0 * math.pi * r_iau) / (360.0 * 4.0)
    spacing_mola = (2.0 * math.pi * r_mola) / (360.0 * 4.0)

    assert round(spacing_iau, 2) == 14818.67
    assert round(spacing_mola, 2) == 14817.85

    # 128 ppd resolution
    spacing_128 = (2.0 * math.pi * r_iau) / (360.0 * 128.0)
    assert round(spacing_128, 2) == 463.08

    # Clarification: 4,630.8 m/px was an accidental 10x multiplication of 463.08
    # rather than the true 32x downsampling ratio (128 / 4 = 32)
    assert round(spacing_128 * 10, 1) == 4630.8
    assert round(spacing_128 * 32, 2) == 14818.67

    # Check that the terrain service reports the correct ~14,818.7 m resolution outside 128 ppd coverage
    resp = client.get("/api/v1/terrain/elevation/point?lat=60.0&lon=10.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "mola-megdr-4"
    assert round(data["native_resolution_m"], 1) == 14818.7


def test_geological_unit_count_audit():
    """Verify exact 44 distinct chronostratigraphic units in SIM 3292 DBF and legend API."""
    service = get_geology_service()
    legend = service.get_legend()

    # The actual shapefile DBF contains exactly 44 units, not 39
    assert len(legend) == 44

    # Verify no null or empty unit codes
    unit_codes = [u["unit"] for u in legend]
    assert "" not in unit_codes
    assert None not in unit_codes
    assert len(set(unit_codes)) == 44

    # Verify total polygon features in geology layer is exactly 1311
    meta = service.get_metadata()
    assert meta["layers"]["geology"]["feature_count"] == 1311

    # Verify API endpoint matches
    resp = client.get("/api/v1/geology/legend")
    assert resp.status_code == 200
    assert len(resp.json()) == 44


def test_geological_crs_and_landmark_identification():
    """Verify GCS_Mars_2000_Sphere CRS, projection distortion notes, and 3 landmark locations."""
    service = get_geology_service()
    meta = service.get_metadata()

    # Verify CRS and projection distortion explanation
    assert "GCS_Mars_2000_Sphere" in meta["crs"]
    assert "R=3,396,190" in meta["display_transformation_note"]
    assert "NOT eliminate projection distortion" in meta["display_transformation_note"]
    assert "sec(phi)" in meta["display_transformation_note"]

    # Landmark 1: Olympus Mons Caldera/Edifice (lat=18.65, lon=226.2 / -133.8W)
    pt_om = service.query_point(18.65, 226.2)
    assert pt_om is not None
    assert pt_om["unit"] == "Ave"
    assert "Amazonian volcanic edifice" in pt_om["unit_name"]
    assert pt_om["chronostratigraphic_period"] == "Amazonian"
    assert "GCS_Mars_2000_Sphere" in pt_om["crs"]

    # Landmark 2: Gale Crater Floor / Transition (lat=-5.4, lon=137.8)
    pt_gale = service.query_point(-5.4, 137.8)
    assert pt_gale is not None
    assert pt_gale["unit"] == "Htu"
    assert "Hesperian" in pt_gale["chronostratigraphic_period"]

    # Landmark 3: Tyrrhena Terra Highlands (lat=-4.6, lon=66.317)
    pt_tyr = service.query_point(-4.6, 66.317)
    assert pt_tyr is not None
    assert pt_tyr["unit"] == "eNh"
    assert "Early Noachian highland unit" in pt_tyr["unit_name"]
    assert pt_tyr["chronostratigraphic_period"] == "Noachian"


def test_tes_thermal_inertia_calibration_audit():
    """Verify TES thermal inertia calibration metadata, unvalidated nominal proxy status, and indicative descriptions."""
    resp_meta = client.get("/api/v1/thermal/metadata")
    assert resp_meta.status_code == 200
    meta = resp_meta.json()

    assert "calibration" in meta
    assert meta["calibration"]["quantization_uncertainty_pct"] == 2.5
    assert meta["calibration"]["mathematical_step_resolution_pct"] == 0.50
    assert meta["calibration"]["uncertainty_status"] == "unvalidated_nominal_estimate"
    assert "790-step" in meta["calibration"]["method"]
    assert "I(t) = 50.0 * (50.0 ** t)" in meta["calibration"]["formula"]
    assert meta["calibration"]["endpoints_tiu"]["i_0"] == 50.0
    assert meta["calibration"]["endpoints_tiu"]["i_789"] == 2500.0
    assert "legend_calibrated_estimate" in meta["calibration"]["measurement_status"]

    # Point query check
    resp_pt = client.get("/api/v1/thermal/point?lat=-2.0&lon=5.0&product=dayside")
    assert resp_pt.status_code == 200
    pt = resp_pt.json()
    assert pt["calibrated_thermal_inertia_estimate_tiu"] == pt["thermal_inertia_tiu"]
    assert pt["quantization_uncertainty_pct"] == 2.5
    assert pt["mathematical_step_resolution_pct"] == 0.50
    assert pt["uncertainty_status"] == "unvalidated_nominal_estimate"
    assert "Unvalidated nominal proxy" in pt["uncertainty_statement"]
    assert pt["calibration_status"] == "legend_calibrated_estimate"
    assert pt["physical_interpretation"].startswith("Indicative:")


def test_themis_resolution_and_grid_semantics_audit():
    """Verify THEMIS metadata distinguishes 100m nadir camera from 256 ppd mosaic grid."""
    resp = client.get("/api/v1/themis/metadata")
    assert resp.status_code == 200
    meta = resp.json()

    assert meta["is_raw_100m_raster"] is False
    assert meta["delivered_mosaic_grid_resolution_ppd"] == 256.0
    assert meta["nominal_instrument_nadir_resolution_m"] == 100.0
    assert meta["delivered_pixel_width_equator_m"] == 231.55
    assert "100 m/px" in meta["native_camera_resolution"]
    assert "256 ppd" in meta["mosaic_grid_resolution"]
    assert "231.55 m/px" in meta["mosaic_grid_resolution"]
    assert "cosine convergence" in meta["mosaic_grid_resolution"].lower()
    assert "NOT a 100 m/px raster" in meta["resolution_qualification"]
    assert meta["measurement_semantics"]["quantitative_analysis_supported"] is False
