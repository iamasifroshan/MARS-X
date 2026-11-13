"""Comprehensive Unit and Integration Tests for Phase 5.

Validates:
1. MOLA 4 ppd raw data and PDS label consistency.
2. MOLA 128 ppd tile inventory generation and coverage percentage calculation.
3. Generalized tile adjacency, shared coordinates, and 0/360 wraparound.
4. Dataset lifecycle states, valid and invalid transitions.
5. Strict horizontal and vertical CRS compatibility checks.
6. Anti-upsampling enforcement and unvalidated data gating.
7. Slope computation on synthetic surfaces with analytically known gradients.
8. Local relief and roughness calculations on synthetic surfaces.
9. NoData propagation through slope and hazard classification.
10. Terrain discontinuity detection (scarps vs flat terrain).
11. Data confidence scoring and explainable complexity classification.
12. All new Phase 5 REST API endpoints (/validation, /inventory, /inventory/adjacency, /compatibility, /hazards, /hazards/metadata).
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.inventory import (
    Mola128InventoryService,
    build_tile_id,
    parse_tile_id,
)
from app.terrain.validation import (
    DatasetValidationRegistry,
    DatasetLifecycleState,
    VALID_STATE_TRANSITIONS,
)
from app.terrain.harmonization import (
    HarmonizationEngine,
    HorizontalCompatibilityStatus,
    VerticalCompatibilityStatus,
    AlignmentDecision,
)
from app.terrain.hazard_engine import (
    TerrainHazardEngine,
    TerrainComplexityClass,
    HazardThresholds,
)

client = TestClient(app)


class TestMolaValidationAndInventory:
    """Tests for MOLA data validation and tile inventory logic."""

    def test_mola_4ppd_validation_report(self):
        """Verify MOLA 4 ppd report reflects analysis-ready status and authentic checksum."""
        rep = DatasetValidationRegistry.get_report("mola-megdr-4")
        assert rep is not None
        assert rep.is_analysis_ready is True
        assert rep.lifecycle_state == DatasetLifecycleState.ANALYSIS_READY
        assert rep.source_checksum == "25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c"
        assert len(rep.evidence_checks) >= 4

    def test_lifecycle_state_transitions(self):
        """Verify valid and disallowed lifecycle transitions."""
        # Valid progression: REGISTERED -> DISCOVERED -> DOWNLOADED
        assert DatasetValidationRegistry.can_transition(
            DatasetLifecycleState.REGISTERED, DatasetLifecycleState.DISCOVERED
        ) is True
        assert DatasetValidationRegistry.can_transition(
            DatasetLifecycleState.DISCOVERED, DatasetLifecycleState.DOWNLOADED
        ) is True

        # Disallowed jump: REGISTERED directly to ANALYSIS_READY
        assert DatasetValidationRegistry.can_transition(
            DatasetLifecycleState.REGISTERED, DatasetLifecycleState.ANALYSIS_READY
        ) is False

    def test_mola_128_tile_inventory(self):
        """Verify inventory calculates exactly 16 expected tiles and detects local sample."""
        inv_service = Mola128InventoryService()
        report = inv_service.get_inventory_report()

        assert report.expected_tile_count == 16
        assert report.downloaded_tile_count >= 1
        assert report.missing_tile_count <= 15
        assert len(report.tiles) == 16

        # Check sample tile megt00n000hb is recognized
        sample = next(t for t in report.tiles if t.tile_id == "megt00n000hb")
        assert sample.download_status == "available_locally"
        assert sample.validation_status == "scientifically_validated"
        assert sample.expected_lines == 5632
        assert sample.expected_samples == 11520

    def test_tile_adjacency_north_south(self):
        """Test north-south boundary sharing at lat=0.0 between megt00n000hb and megt44n000hb."""
        res = Mola128InventoryService.check_adjacency("megt00n000hb", "megt44n000hb")
        assert res.is_adjacent is True
        assert res.adjacency_type == "north_south"
        assert res.shared_coordinate == 0.0
        assert res.coordinate_axis == "latitude"

    def test_tile_adjacency_east_west_wraparound(self):
        """Test east-west 0°/360° longitudinal wraparound between megt00n000hb and megt00n270hb."""
        res = Mola128InventoryService.check_adjacency("megt00n000hb", "megt00n270hb")
        assert res.is_adjacent is True
        assert res.adjacency_type == "east_west"
        assert res.wraparound is True
        assert res.shared_coordinate == 0.0

    def test_tile_adjacency_diagonal_and_non_adjacent(self):
        """Test diagonal corner touch (not adjacent edge) and distant non-adjacent tiles."""
        diag = Mola128InventoryService.check_adjacency("megt00n000hb", "megt44n090hb")
        assert diag.is_adjacent is False
        assert diag.adjacency_type == "diagonal_corner"

        non_adj = Mola128InventoryService.check_adjacency("megt00n000hb", "megt88n180hb")
        assert non_adj.is_adjacent is False
        assert non_adj.adjacency_type == "non_adjacent"


class TestHarmonizationEngine:
    """Tests for horizontal CRS and vertical datum harmonization."""

    def test_compatibility_mola_megdr4_with_mola128(self):
        """MOLA 4 and MOLA 128 share IAU:49900 and GMM3 areoid; direct alignment permitted."""
        res = HarmonizationEngine.assess_compatibility("mola-megdr-4", "mola-megdr-128")
        assert res.horizontal_status == HorizontalCompatibilityStatus.IDENTICAL
        assert res.vertical_status == VerticalCompatibilityStatus.COMPATIBLE
        assert res.decision == AlignmentDecision.PERMITTED_DIRECT
        assert res.anti_upsampling_enforced is True

    def test_compatibility_blocks_unvalidated_dataset(self):
        """Comparison with un-downloaded HiRISE must be blocked with unvalidated status."""
        res = HarmonizationEngine.assess_compatibility("mola-megdr-4", "hirise-dtm-jezero")
        assert res.decision == AlignmentDecision.BLOCKED_UNVALIDATED_DATA
        assert any("not analysis-ready" in r for r in res.reasons_blocked)

    def test_compatibility_invalid_product_raises_error(self):
        """Querying an unknown product must raise ValueError."""
        with pytest.raises(ValueError):
            HarmonizationEngine.assess_compatibility("mola-megdr-4", "nonexistent-product")


class TestHazardEngine:
    """Tests for hazard algorithms using synthetic surfaces with analytically known properties."""

    def test_slope_on_synthetic_plane(self):
        """Test Horn slope on a synthetic inclined plane with 10% slope (dz/dx = 0.1)."""
        dy = 100.0  # 100m post-spacing
        dx = 100.0

        # Uniform ramp: z = 0.1 * x (rises 10m every 100m)
        window = np.array([
            [0.0, 10.0, 20.0],
            [0.0, 10.0, 20.0],
            [0.0, 10.0, 20.0],
        ], dtype=np.float32)

        slope_deg = TerrainHazardEngine.compute_slope_horn(window, dy, dx)
        assert slope_deg is not None
        # arctan(0.1) in degrees ≈ 5.71°
        expected_deg = math.degrees(math.atan(0.1))
        assert slope_deg == pytest.approx(expected_deg, abs=1e-2)

    def test_slope_on_flat_plain_is_zero(self):
        """Flat terrain must yield exactly 0.0° slope."""
        flat = np.full((3, 3), 1500.0, dtype=np.float32)
        slope = TerrainHazardEngine.compute_slope_horn(flat, 100.0, 100.0)
        assert slope == pytest.approx(0.0, abs=1e-6)

    def test_slope_propagates_nodata(self):
        """If any pixel in 3x3 window is NoData (-32768 or NaN), slope must return None."""
        window_with_nodata = np.array([
            [10.0, 10.0, 10.0],
            [10.0, -32768.0, 10.0],
            [10.0, 10.0, 10.0],
        ], dtype=np.float32)
        slope = TerrainHazardEngine.compute_slope_horn(window_with_nodata, 100.0, 100.0)
        assert slope is None

    def test_local_relief_and_roughness(self):
        """Test relief (max-min) and roughness (sample std dev) on known array."""
        window = np.array([
            [10.0, 20.0, 30.0],
            [15.0, 25.0, 35.0],
            [20.0, 30.0, 40.0],
        ], dtype=np.float32)
        relief = TerrainHazardEngine.compute_local_relief(window)
        assert relief == pytest.approx(30.0, abs=1e-4)

        roughness = TerrainHazardEngine.compute_roughness(window)
        assert roughness is not None
        assert roughness == pytest.approx(float(np.std(window, ddof=1)), abs=1e-4)

    def test_discontinuity_detection(self):
        """Scarp detection with steep slope and high relief."""
        is_disc, desc = TerrainHazardEngine.detect_discontinuity(slope_deg=28.0, relief_m=120.0, roughness_m=15.0)
        assert is_disc is True
        assert "Major scarp" in desc

        is_flat, _ = TerrainHazardEngine.detect_discontinuity(slope_deg=2.0, relief_m=5.0, roughness_m=1.0)
        assert is_flat is False

    def test_insufficient_data_classification(self):
        """Low confidence or missing slope must be classified as INSUFFICIENT_DATA, never low-risk."""
        engine = TerrainHazardEngine()
        cls, expl = engine.classify_complexity(slope_deg=None, relief_m=10.0, roughness_m=2.0, confidence=0.0)
        assert cls == TerrainComplexityClass.INSUFFICIENT_DATA


class TestPhase5ApiEndpoints:
    """Integration tests for all new Phase 5 FastAPI endpoints."""

    def test_get_validation_summary(self):
        """GET /api/v1/terrain/validation returns all registered products with lifecycle states."""
        resp = client.get("/api/v1/terrain/validation")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5

        p_ids = [d["product_id"] for d in data]
        assert "mola-megdr-4" in p_ids
        assert "hirise-dtm-jezero" in p_ids

        # HiRISE must not be analysis ready
        hirise = next(d for d in data if d["product_id"] == "hirise-dtm-jezero")
        assert hirise["is_analysis_ready"] is False
        assert hirise["lifecycle_state"] == "discovered"

    def test_get_product_validation_report(self):
        """GET /api/v1/terrain/products/{id}/validation returns specific product report."""
        resp = client.get("/api/v1/terrain/products/mola-megdr-4/validation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["product_id"] == "mola-megdr-4"
        assert data["lifecycle_state"] == "analysis_ready"
        assert data["source_checksum"] is not None

    def test_get_inventory(self):
        """GET /api/v1/terrain/inventory returns 16-tile MOLA inventory."""
        resp = client.get("/api/v1/terrain/inventory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["expected_tile_count"] == 16
        assert data["downloaded_tile_count"] >= 1
        assert "total_surface_coverage_pct" in data

    def test_check_adjacency_endpoint(self):
        """GET /api/v1/terrain/inventory/adjacency?tile_a=...&tile_b=..."""
        resp = client.get("/api/v1/terrain/inventory/adjacency?tile_a=megt00n000hb&tile_b=megt44n000hb")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_adjacent"] is True
        assert data["adjacency_type"] == "north_south"

    def test_get_compatibility_endpoint(self):
        """GET /api/v1/terrain/compatibility?product_a=...&product_b=..."""
        resp = client.get("/api/v1/terrain/compatibility?product_a=mola-megdr-4&product_b=mola-megdr-128")
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "permitted_direct"
        assert data["anti_upsampling_enforced"] is True

    def test_get_hazard_metadata_endpoint(self):
        """GET /api/v1/terrain/hazards/metadata returns algorithm information."""
        resp = client.get("/api/v1/terrain/hazards/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "Horn" in data["slope_algorithm"]
        assert "thresholds" in data

    def test_evaluate_hazards_endpoint_olympus_mons(self):
        """GET /api/v1/terrain/hazards at Olympus Mons caldera (18.65°N, 226.20°E)."""
        resp = client.get("/api/v1/terrain/hazards?lat=18.65&lon=226.20&dataset_id=mola-megdr")
        assert resp.status_code == 200
        data = resp.json()
        assert data["latitude"] == 18.65
        assert data["longitude"] == 226.20
        assert data["elevation_m"] > 19000.0
        assert data["slope_deg"] is not None
        assert data["complexity_class"] in [
            "moderate_complexity", "high_complexity", "extreme_complexity"
        ]
        assert "safety_disclaimer" in data
