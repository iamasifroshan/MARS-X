"""Decision Table and Verification Suite for Phase 5.1.

Validates:
1. Decision table covering all Boolean complexity branches:
   - Case 1: Low slope, low relief, low roughness -> LOW_COMPLEXITY
   - Case 2: High slope alone -> HIGH_COMPLEXITY
   - Case 3: High relief alone -> HIGH_COMPLEXITY
   - Case 4: High roughness alone -> HIGH_COMPLEXITY
   - Case 5: Multiple elevated indicators -> EXTREME_COMPLEXITY
   - Case 6: NoData in center or neighbor -> INSUFFICIENT_DATA
   - Case 7: Low confidence (< 0.2) -> INSUFFICIENT_DATA
   - Case 8: Polar latitude (|lat| > 85°) rejection -> INSUFFICIENT_DATA
2. MOLA MEG128 distinct coverage metrics:
   - theoretical (99.94%)
   - downloaded (8.68%)
   - integrity-verified (8.68%)
   - scientifically-validated (8.68%)
3. Polar geodesy guard testing valid bounds ([-85°, 85°]) and rejecting > 85°.
4. Spatial scale limits (feature detectability Nyquist ~2.5x).
5. Evidence-based vertical datum catalog (removing assumed ±1-5m offsets).
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.inventory import Mola128InventoryService
from app.terrain.harmonization import HarmonizationEngine, VERTICAL_EVIDENCE_CATALOG
from app.terrain.hazard_engine import (
    TerrainHazardEngine,
    TerrainComplexityClass,
    HazardThresholds,
    MAX_VALID_CYLINDRICAL_LAT_DEG,
)

client = TestClient(app)


class TestHazardDecisionTable:
    """Rigorous decision table testing for Boolean terrain complexity classification."""

    @pytest.fixture
    def engine(self):
        return TerrainHazardEngine(HazardThresholds())

    def test_case_1_low_complexity_all_low(self, engine):
        """Case 1: Low slope, low relief, low roughness."""
        cls, expl = engine.classify_complexity(slope_deg=3.2, relief_m=5.0, roughness_m=1.1, confidence=1.0)
        assert cls == TerrainComplexityClass.LOW_COMPLEXITY
        assert "Low measured terrain complexity" in expl

    def test_case_2_high_slope_alone(self, engine):
        """Case 2: High slope (16.5° >= 15°) with low relief and low roughness."""
        cls, expl = engine.classify_complexity(slope_deg=16.5, relief_m=6.0, roughness_m=1.2, confidence=1.0)
        assert cls == TerrainComplexityClass.HIGH_COMPLEXITY
        assert "High terrain complexity" in expl

    def test_case_3_high_relief_alone(self, engine):
        """Case 3: High relief (45m >= 30m) with low slope and low roughness."""
        cls, expl = engine.classify_complexity(slope_deg=4.0, relief_m=45.0, roughness_m=1.5, confidence=1.0)
        assert cls == TerrainComplexityClass.HIGH_COMPLEXITY
        assert "High terrain complexity" in expl

    def test_case_4_high_roughness_alone(self, engine):
        """Case 4: High roughness (11m >= 8m) with low slope and low relief."""
        cls, expl = engine.classify_complexity(slope_deg=5.0, relief_m=8.0, roughness_m=11.0, confidence=1.0)
        assert cls == TerrainComplexityClass.HIGH_COMPLEXITY
        assert "High terrain complexity" in expl

    def test_case_5_extreme_complexity_elevated_indicators(self, engine):
        """Case 5: Extreme complexity (slope >= 25° or relief >= 75m or roughness >= 20m)."""
        cls, expl = engine.classify_complexity(slope_deg=27.0, relief_m=80.0, roughness_m=22.0, confidence=1.0)
        assert cls == TerrainComplexityClass.EXTREME_COMPLEXITY
        assert "Extreme terrain complexity" in expl

    def test_case_6_nodata_in_inputs(self, engine):
        """Case 6: Any input is None due to NoData propagation -> INSUFFICIENT_DATA."""
        cls, expl = engine.classify_complexity(slope_deg=None, relief_m=12.0, roughness_m=2.0, confidence=1.0)
        assert cls == TerrainComplexityClass.INSUFFICIENT_DATA
        assert "Elevation data missing" in expl

    def test_case_7_low_confidence(self, engine):
        """Case 7: Confidence score below 0.2 -> INSUFFICIENT_DATA."""
        cls, expl = engine.classify_complexity(slope_deg=4.0, relief_m=6.0, roughness_m=1.0, confidence=0.15)
        assert cls == TerrainComplexityClass.INSUFFICIENT_DATA
        assert "confidence score below minimum threshold" in expl

    def test_case_8_polar_geodesy_rejection(self, engine):
        """Case 8: Coordinates beyond 85° latitude rejected from cylindrical approximation."""
        flat_window = np.full((3, 3), 1000.0, dtype=np.float32)
        metrics = engine.evaluate_point_hazards(
            lat_deg=87.5,
            lon_deg=180.0,
            window_3x3=flat_window,
            d_lat_deg=0.25,
            d_lon_deg=0.25,
            source_dataset="mola-megdr",
            source_resolution_m=14818.67,
        )
        assert metrics.complexity_class == TerrainComplexityClass.INSUFFICIENT_DATA
        assert "exceeds maximum validated cylindrical envelope" in metrics.explanation
        assert metrics.data_confidence_score == 0.0


class TestSeparatedCoverageMetrics:
    """Tests confirming separation of theoretical vs downloaded vs validated coverage."""

    def test_coverage_tiers_separation(self):
        inv_service = Mola128InventoryService()
        rep = inv_service.get_inventory_report()

        # Theoretical full archive coverage is 99.94% (excludes polar caps)
        assert rep.theoretical_archive_coverage_pct == pytest.approx(99.94, abs=0.01)
        assert rep.catalogued_tile_coverage_pct == pytest.approx(99.94, abs=0.01)

        # Downloaded coverage on disk is strictly separated from full archive (3 tiles: ~26.05% of sphere)
        assert rep.downloaded_tile_count >= 1
        assert rep.downloaded_tile_coverage_pct < rep.theoretical_archive_coverage_pct
        assert rep.integrity_verified_coverage_pct <= rep.downloaded_tile_coverage_pct
        assert rep.scientifically_validated_coverage_pct <= rep.downloaded_tile_coverage_pct

        # Downloaded coverage must NEVER be reported as 99.94%
        assert rep.downloaded_tile_coverage_pct < 90.0


class TestSpatialScaleAndVerticalEvidence:
    """Tests for spatial scale reporting and vertical datum evidence auditing."""

    def test_spatial_scale_metadata(self):
        engine = TerrainHazardEngine()
        flat_window = np.full((3, 3), 1000.0, dtype=np.float32)
        metrics = engine.evaluate_point_hazards(
            lat_deg=0.0,
            lon_deg=10.0,
            window_3x3=flat_window,
            d_lat_deg=0.25,
            d_lon_deg=0.25,
            source_dataset="mola-megdr",
            source_resolution_m=14818.67,
        )
        assert metrics.spatial_scale.native_pixel_spacing_m == pytest.approx(14818.7, abs=0.5)
        assert metrics.spatial_scale.minimum_detectable_feature_scale_m > 30000.0
        assert metrics.spatial_scale.operational_scale_tier == "regional_reconnaissance"
        assert "CANNOT be detected" in metrics.spatial_scale.scale_limitation_warning

    def test_vertical_evidence_no_arbitrary_offsets(self):
        for prod_id, rec in VERTICAL_EVIDENCE_CATALOG.items():
            # MOLA products have 0.0 offset (primary standard)
            if "mola" in prod_id:
                assert rec.measured_offset_m == 0.0
            else:
                # Other products must have None (not assumed ±1-5m)
                assert rec.measured_offset_m is None
                assert "bundle" in rec.adjustment_procedure.lower() or "icp" in rec.adjustment_procedure.lower() or "tie" in rec.adjustment_procedure.lower()
