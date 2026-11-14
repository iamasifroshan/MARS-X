"""Phase 8.7.2: Discovery Data Semantics & Metadata Closure Test Suite.

Verifies:
1. Strict epistemological separation across all 18 discovery candidates:
   - derived_measurement for high-resolution terrain DTMs
   - mapped_geological_interpretation for SIM 3292 units, structures, and landing site locations
   - indicative_proxy for TES thermal inertia contrasts
   - composite_interpretation for multi-dataset intersections
2. Absence of false claims that raw pushbroom CCD sensor data (CTX/HiRISE) is hosted locally
   without clarifying derived photogrammetric DTM products vs PDS archive EDR/RDR records.
3. Separation of source scale vs raster pixel spacing:
   - SIM 3292 geological features specify 1:20,000,000 cartographic scale, NOT raster pixel resolution.
   - Raster products specify grid spacing (CTX 20.0m, HiRISE 1.01m, MOLA 463.08m / 14,818.67m, TES ~3km, THEMIS ~231.5m).
4. Vertical datum audit:
   - Explicit confirmation that all elevations are areoid heights referenced to the MOLA Areoid.
   - Separation of areoid heights from reference-sphere radii.
5. Bitwise elevation benchmark preservation:
   - Tyrrhena CTX DTM: +2189.49 m at (-4.600°, 66.317°E)
   - Apollinaris Sulci CTX DTM: -2930.77 m at (4.700°, 168.250°E)
   - Holden Crater HiRISE DTM: -1132.14 m at (-28.500°, 309.020°E)
6. Zero double negatives in coordinate display across all candidates.
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.science.discovery_service import (
    get_discovery_service,
    CANDIDATE_DISCOVERIES,
)

client = TestClient(app)


def test_primary_evidence_class_partitioning():
    """Verify all 18 candidate discoveries have strictly partitioned primary_evidence_class."""
    terrain_ids = {"disc-terr-tyrrhena-ctx", "disc-terr-apollinaris-ctx", "disc-terr-holden-hirise"}
    thermal_ids = {"disc-therm-sinus-meridiani", "disc-therm-tharsis-dust"}
    composite_ids = {"disc-multi-tyrrhena-corridor", "disc-multi-meridiani-gateway"}
    interpretation_ids = {
        "disc-land-curiosity", "disc-land-opportunity", "disc-land-spirit", "disc-land-pathfinder", "disc-land-viking1",
        "disc-geol-olympus-mons", "disc-geol-valles-marineris", "disc-geol-noachis-massifs",
        "disc-struct-syrtis-ridges", "disc-struct-cerberus-graben", "disc-struct-shalbatana-channel",
    }

    assert len(CANDIDATE_DISCOVERIES) == 18

    for d in CANDIDATE_DISCOVERIES:
        disc_id = d["id"]
        primary_class = d.get("primary_evidence_class")
        assert primary_class is not None, f"{disc_id} missing primary_evidence_class"

        if disc_id in terrain_ids:
            assert primary_class == "derived_measurement", (
                f"{disc_id} should be derived_measurement, got {primary_class}"
            )
        elif disc_id in thermal_ids:
            assert primary_class == "indicative_proxy", (
                f"{disc_id} should be indicative_proxy, got {primary_class}"
            )
        elif disc_id in composite_ids:
            assert primary_class == "composite_interpretation", (
                f"{disc_id} should be composite_interpretation, got {primary_class}"
            )
        elif disc_id in interpretation_ids:
            assert primary_class == "mapped_geological_interpretation", (
                f"{disc_id} should be mapped_geological_interpretation, got {primary_class}"
            )
        else:
            pytest.fail(f"Unaccounted discovery candidate ID: {disc_id}")


def test_evidence_classes_epistemological_separation():
    """Verify the 5-class evidence breakdown exists for all candidates."""
    for d in CANDIDATE_DISCOVERIES:
        disc_id = d["id"]
        ec = d.get("evidence_classes", {})

        # Ensure all 5 classes are present as non-empty lists
        for key in [
            "direct_sensor_observations",
            "derived_measurements",
            "mapped_geological_interpretations",
            "indicative_proxies",
            "potential_investigations",
        ]:
            assert key in ec, f"{disc_id} missing {key} in evidence_classes"
            assert isinstance(ec[key], list), f"{disc_id} {key} must be list"
            assert len(ec[key]) >= 1, f"{disc_id} {key} must not be empty"

        # Check that direct sensor observations clarify PDS archive status / photogrammetric DTM context
        direct_obs = " ".join(ec["direct_sensor_observations"]).lower()
        if "ctx" in disc_id or "hirise" in disc_id:
            assert "pds" in direct_obs or "derived" in direct_obs or "dtm" in direct_obs, (
                f"{disc_id} direct sensor observations should clarify PDS archive status: {direct_obs}"
            )


def test_primary_source_metadata_scale_vs_resolution():
    """Verify primary_source separates cartographic scale from raster pixel spacing."""
    for d in CANDIDATE_DISCOVERIES:
        disc_id = d["id"]
        ps = d.get("primary_source")
        assert ps is not None, f"{disc_id} missing primary_source"
        assert "feature_or_product" in ps
        assert "source_type" in ps
        assert "native_scale_or_spacing" in ps

        scale_or_spacing = ps["native_scale_or_spacing"]
        source_type = ps["source_type"]

        # Geological interpretations must report map scale 1:20,000,000, NOT raster pixel resolution
        if source_type in ("geological_map_polygon", "geological_structural_trace", "landing_site_record"):
            assert "1:20,000,000" in scale_or_spacing, (
                f"{disc_id} geological feature should report 1:20,000,000 cartographic scale, got {scale_or_spacing}"
            )
            # Ensure it does not mistakenly quote 463m or MOLA resolution as the map feature's native scale
            assert "463" not in scale_or_spacing, (
                f"{disc_id} geological feature incorrectly quoted MOLA pixel spacing as native scale"
            )

        # High-res terrain DTMs must report meter-scale raster spacing
        if "tyrrhena-ctx" in disc_id or "apollinaris-ctx" in disc_id:
            assert "20" in scale_or_spacing and ("m/px" in scale_or_spacing or "m" in scale_or_spacing)
        elif "holden-hirise" in disc_id:
            assert "1.01" in scale_or_spacing or "1 m" in scale_or_spacing


def test_vertical_reference_audit_semantics():
    """Verify vertical reference audit reports areoid heights across all elevation sources."""
    for d in CANDIDATE_DISCOVERIES:
        ps = d.get("primary_source", {})
        v_datum = ps.get("vertical_datum")
        v_type = ps.get("vertical_datum_type")

        assert v_type == "areoid_height", (
            f"{d['id']} vertical_datum_type must be 'areoid_height', got {v_type}"
        )
        assert "mola areoid" in v_datum.lower(), (
            f"{d['id']} vertical_datum must reference MOLA Areoid, got {v_datum}"
        )

    # Check via profile API
    resp = client.get("/api/v1/discovery/profile?lat=-4.600&lon=66.317")
    assert resp.status_code == 200
    prof = resp.json()

    assert "vertical_reference_audit" in prof
    vra = prof["vertical_reference_audit"]
    assert vra["vertical_datum_type"] == "areoid_height"
    assert "mola areoid" in vra["vertical_datum"].lower()
    assert "areoid heights" in vra["sphere_mixing_warning"].lower()
    assert "gmm-3" in vra["reference_surface"].lower()


def test_coordinate_display_zero_double_negatives():
    """Verify coordinate_display across all candidates contains zero double negatives."""
    double_negative_pattern = re.compile(r"-\d+(\.\d+)?°[SW]")
    for d in CANDIDATE_DISCOVERIES:
        cd = d.get("coordinate_display", "")
        assert not double_negative_pattern.search(cd), f"Double negative in {d['id']}: {cd}"


def test_elevation_benchmarks_bitwise_preserved():
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


def test_api_candidates_response_schema():
    """Verify /api/v1/discovery/list returns new primary_source and 5-class evidence."""
    resp = client.get("/api/v1/discovery/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "discoveries" in data
    discoveries = data["discoveries"]
    assert len(discoveries) == 18

    first = discoveries[0]
    assert "primary_source" in first
    assert "native_scale_or_spacing" in first["primary_source"]
    assert "vertical_datum_type" in first["primary_source"]
    assert "evidence_classes" in first
    assert "direct_sensor_observations" in first["evidence_classes"]
    assert "mapped_geological_interpretations" in first["evidence_classes"]
