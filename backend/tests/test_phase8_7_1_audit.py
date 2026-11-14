"""Phase 8.7.1: Science Discovery Scientific Audit & Verification Test Suite.

Verifies:
1. Coordinate notation compliance (no double negatives like '-4.600°S' or '-28.500°S').
2. Epistemological 4-class evidence matrix across all 18 candidate discoveries.
3. Separation of measured observations, derived measurements, indicative proxies, and potential investigations.
4. SIM 3292 geological data terminology (1,311 polygon features, 44 distinct unit codes, 3,800 contacts, 3,593 structures, 9 landing sites).
5. Exclusion of 'Border' neatlines from genuine geological contact proximity queries.
6. Thermophysical qualifications (TES ~0.50% LUT step nominal proxy; THEMIS 8-bit visual DN, NOT calibrated radiance/temperature).
7. Deterministic multi-site physical comparisons without arbitrary automated confidence scores.
8. Bitwise preservation of MOLA, CTX, and HiRISE elevation benchmarks (+2189.49m, -2930.77m, -1132.14m).
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.science.discovery_service import (
    get_discovery_service,
    CANDIDATE_DISCOVERIES,
    format_planetary_coord,
)

client = TestClient(app)


def test_coordinate_notation_no_double_negatives():
    """Verify all candidate discoveries and formatting functions produce zero double negatives."""
    double_negative_pattern = re.compile(r"-\d+(\.\d+)?°[SW]")

    # Check candidate discovery fields
    for d in CANDIDATE_DISCOVERIES:
        coord_disp = d.get("coordinate_display", "")
        assert not double_negative_pattern.search(coord_disp), f"Double negative found in {d['id']}: {coord_disp}"
        # Check title and descriptions
        assert not double_negative_pattern.search(d.get("title", "")), f"Double negative in title: {d['title']}"
        assert not double_negative_pattern.search(d.get("scientific_significance", ""))

    # Verify format_planetary_coord helper
    assert format_planetary_coord(-4.600, 66.317) == "4.600°S, 66.317°E"
    assert format_planetary_coord(4.700, 168.250) == "4.700°N, 168.250°E"
    assert format_planetary_coord(-28.500, 309.020) == "28.500°S, 309.020°E"
    assert format_planetary_coord(18.650, 226.200) == "18.650°N, 226.200°E"


def test_epistemological_evidence_classes_all_candidates():
    """Verify every candidate discovery has a valid primary_evidence_class and 4-class matrix."""
    valid_classes = {
        "measured_observation", "derived_measurement", "indicative_proxy", "composite_evidence",
        "mapped_geological_interpretation", "composite_interpretation", "direct_sensor_observation"
    }

    for d in CANDIDATE_DISCOVERIES:
        disc_id = d["id"]
        # Primary class
        assert "primary_evidence_class" in d, f"{disc_id} missing primary_evidence_class"
        assert d["primary_evidence_class"] in valid_classes, f"{disc_id} invalid class {d['primary_evidence_class']}"

        # 4-class matrix
        assert "evidence_classes" in d, f"{disc_id} missing evidence_classes dict"
        ec = d["evidence_classes"]
        for key in ["measured_observations", "derived_measurements", "indicative_proxies", "potential_investigations"]:
            assert key in ec, f"{disc_id} missing {key} in evidence_classes"
            assert isinstance(ec[key], list), f"{disc_id} {key} must be a list"
            assert len(ec[key]) >= 1, f"{disc_id} {key} list is empty"

        # Limitations must qualify proxies
        assert "scientific_limitations" in d or "limitations" in d


def test_geological_framework_terminology_and_contact_neatline_exclusion():
    """Verify SIM 3292 framework terminology and exclusion of neatline 'Border' contacts."""
    service = get_discovery_service()

    # Query science profile at Tyrrhena Terra (-4.6°, 66.317°E)
    profile = service.get_science_profile(-4.600, 66.317)

    # 1. Geological framework terminology
    gf = profile.get("geological_framework_summary")
    assert gf is not None
    assert gf["total_polygons"] == 1311
    assert gf["distinct_unit_codes"] == 44
    assert gf["total_contacts"] == 3800
    assert gf["total_structures"] == 3593
    assert gf["landing_site_multipoints"] == 9
    assert "1,311 polygon features representing 44 distinct" in gf["rigor_note"]

    # 2. Nearest contact must NOT be 'Border' neatline!
    nearest_contact = profile["derived_measurements"].get("nearest_geological_contact")
    if nearest_contact:
        assert nearest_contact["contact_type"] != "Border", "Neatline border was returned as contact!"


def test_thermophysical_qualification_semantics():
    """Verify TES and THEMIS qualifications prevent misrepresenting proxies as temperature/radiance."""
    resp = client.get("/api/v1/discovery/profile?lat=-2.000&lon=5.000")
    assert resp.status_code == 200
    prof = resp.json()

    # TES thermophysical qualifications
    ti = prof["indicative_proxies"]["thermal_inertia"]
    assert "unvalidated nominal proxy" in ti["uncertainty_qualification"].lower()
    assert "not temperature" in ti["temperature_warning"].lower()
    assert ti["mathematical_step_resolution_pct"] == 0.50

    # THEMIS imagery qualifications
    themis = prof["direct_observations"]["themis_qualitative_imagery"]
    assert themis["in_regional_coverage"] is True
    assert "not calibrated radiance or temperature" in themis["semantics_note"].lower()
    assert themis["is_raw_100m_raster"] is False


def test_transparent_multi_site_comparison_engine():
    """Verify multi-site comparison uses deterministic physical metrics without arbitrary scores."""
    # Test with mixed input: discovery IDs, coordinate strings, and dicts
    body = {
        "locations": [
            "disc-terr-tyrrhena-ctx",
            "disc-land-curiosity",
            "-2.0,5.0",
            {"lat": 18.65, "lon": 226.2, "label": "Olympus Mons"},
        ]
    }
    resp = client.post("/api/v1/discovery/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["comparison_count"] == 4
    assert len(data["sites"]) == 4

    summary = data["summary"]
    assert summary["count"] == 4
    assert summary["highest_elevation_site"]["elevation_m"] > 20000.0  # Olympus Mons (~21.2 km)
    assert summary["lowest_elevation_site"]["elevation_m"] < -4000.0   # Gale Crater (~ -4.4 km)
    assert summary["highest_thermal_inertia_site"]["ti"] > 500.0      # Sinus Meridiani (~724 TIU)
    assert len(summary["geological_diversity"]) >= 2

    # Verify methodology notes explain physical rankings
    assert "methodology_notes" in data
    notes = " ".join(data["methodology_notes"]).lower()
    assert "deterministic physical metrics" in notes
    assert "no arbitrary automated confidence scoring" in notes


def test_numerical_elevation_benchmarks_100pct_preserved():
    """Confirm all three verified elevation benchmarks remain 100% bitwise preserved."""
    # Benchmark 1: Tyrrhena Terra CTX DTM (+2189.49 m)
    r1 = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317&preferred_source=ctx")
    assert r1.status_code == 200
    assert r1.json()["elevation_m"] == 2189.49

    # Benchmark 2: Apollinaris Sulci Controlled CTX DTM (-2930.77 m)
    r2 = client.get("/api/v1/terrain/elevation/point?lat=4.700&lon=168.250")
    assert r2.status_code == 200
    assert r2.json()["elevation_m"] == -2930.77

    # Benchmark 3: Holden Crater Controlled HiRISE DTM (-1132.14 m)
    r3 = client.get("/api/v1/terrain/elevation/point?lat=-28.500&lon=309.020")
    assert r3.status_code == 200
    assert r3.json()["elevation_m"] == -1132.14
