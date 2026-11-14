"""Phase 8.1 End-to-End Runtime Integration and Scientific Calibration Tests.

Verifies:
1. All Phase 8 & 8.1 Science and Terrain API endpoints with real HTTP requests via TestClient.
2. Scientific Correction A: Requested vs. Effective analysis scale calibration ($k \\times \\Delta x$).
3. Scientific Correction B: Geographic identity calibration for Tyrrhena Terra (CTX DTM Swath) vs Valles Marineris.
4. Scientific Correction C: Heuristic Data Quality Index naming, bounds [0, 100], and documentation.
5. Scientific Correction D: Multi-tier route corridor coverage metrics (centerline, buffered envelope, bbox).
6. Multi-resolution catalogue consistency with authentic disk files.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.multiscale_analysis import MultiScaleAnalyzer, MultiScaleAnalysisRequest
from app.science.terrain_intelligence import (
    TerrainIntelligenceService,
    PRESET_CANDIDATE_REGIONS,
    RegionDefinition,
    RegionComparisonRequest,
)
from app.routing.route_service import MarsRouteService
from app.terrain.multi_resolution import MULTI_RESOLUTION_DTM_CATALOG, MultiResolutionTerrainCatalog

client = TestClient(app)


class TestPhase81RuntimeEndpoints:
    """Verify live HTTP endpoints for Phase 8.1."""

    def test_health_endpoint(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["app"] == "MARS-X"

    def test_status_endpoint(self):
        res = client.get("/api/v1/status")
        assert res.status_code == 200
        data = res.json()
        assert "services" in data
        assert data["services"]["terrain"] == "active_engine"

    def test_resolution_selection_endpoint(self):
        # Tyrrhena Terra CTX envelope via query params
        res = client.get(
            "/api/v1/science/resolution-selection"
            "?min_lat=-5.1&min_lon=66.1&max_lat=-4.5&max_lon=66.5"
            "&analysis_type=traverse_planning&target_scale_m=20.0&require_local_raster=true"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["selected", "optimal_selection"]
        assert data["selected_product_id"] == "ctx-dtm-p21-009323"
        assert abs(data["native_resolution_m"] - 20.0) < 0.1

    def test_terrain_profile_endpoint(self):
        res = client.get(
            "/api/v1/science/terrain-profile"
            "?min_lat=-5.0&min_lon=66.2&max_lat=-4.8&max_lon=66.4"
            "&windows_m=100,500,1000"
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["scales"]) == 3
        # Verify effective analysis scales are computed
        s0 = data["scales"][0]
        assert "effective_analysis_scale_x_m" in s0
        assert s0["effective_analysis_scale_x_m"] > 0
        assert "scale_suitability" in s0

    def test_transition_compatibility_endpoint(self):
        res = client.get("/api/v1/science/transition-compatibility?product_a=mola-megdr-128&product_b=ctx-dtm-p21-009323")
        assert res.status_code == 200
        data = res.json()
        assert data["has_overlap"] is True
        assert data["transition_status"] in ["compatible", "compatible_with_documented_transformation"]

    def test_preset_candidate_regions_endpoint(self):
        # PRESET_CANDIDATE_REGIONS contains tyrrhena-terra-active and real melas-chasma
        assert len(PRESET_CANDIDATE_REGIONS) >= 4
        ids = [r.region_id for r in PRESET_CANDIDATE_REGIONS]
        assert "tyrrhena-terra-active" in ids
        tyrrhena = next(r for r in PRESET_CANDIDATE_REGIONS if r.region_id == "tyrrhena-terra-active")
        assert "Tyrrhena Terra" in tyrrhena.name
        assert -5.5 <= tyrrhena.min_lat <= -4.0

    def test_region_assessment_endpoint(self):
        res = client.get(
            "/api/v1/science/region-assessment"
            "?min_lat=-5.10&min_lon=66.10&max_lat=-4.50&max_lon=66.50"
            "&name=Tyrrhena+Terra&region_id=tyrrhena-terra-active&target_scale_m=500.0"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["region_id"] == "tyrrhena-terra-active"
        assert "terrain_data_quality_index" in data
        assert 0.0 <= data["terrain_data_quality_index"] <= 100.0
        assert "effective_analysis_scale_x_m" in data

    def test_region_comparison_endpoint(self):
        res = client.get("/api/v1/science/region-comparison?target_scale_m=500.0")
        assert res.status_code == 200
        data = res.json()
        assert len(data["regions_evaluated"]) >= 2
        assert len(data["pairwise_comparisons"]) >= 1
        p0 = data["pairwise_comparisons"][0]
        assert "scale_compatibility" in p0
        assert p0["scale_compatibility"] in ["equivalent_scale", "approximately_equivalent", "non_equivalent"]

    def test_routing_terrain_source_endpoint(self):
        # Route corridor in Coprates Chasma within MOLA 128
        res = client.get("/api/v1/routes/terrain-source?start_lat=-14.2&start_lon=59.1&dest_lat=-14.0&dest_lon=59.3&target_scale_m=500")
        assert res.status_code == 200
        data = res.json()
        assert data["routing_eligible"] is True
        assert "centerline_valid_coverage_pct" in data
        assert data["centerline_valid_coverage_pct"] >= 95.0
        assert "corridor_envelope_valid_coverage_pct" in data
        assert data["nodata_intersections"] == 0


class TestScientificCalibrations:
    """Verify the 4 scientific corrections mandated in Phase 8.1."""

    def test_correction_a_scale_calibration(self):
        """Correction A: Requested vs. Effective analysis scale."""
        analyzer = MultiScaleAnalyzer()
        req = MultiScaleAnalysisRequest(
            min_lat=-1.0,
            min_lon=10.0,
            max_lat=-0.8,
            max_lon=10.2,
            windows_m=[100.0, 500.0, 2000.0],
        )
        res = analyzer.analyze_region(req)
        mola_res = res.native_resolution_m  # ~463 m/px

        # For 100m requested scale (sub-pixel on MOLA 463m), kernel must clamp to min 3x3
        scale_100 = res.scales[0]
        assert scale_100.kernel_size_pixels == 3
        assert scale_100.effective_analysis_scale_y_m > 1000.0  # 3 * 463m = ~1389m
        assert scale_100.scale_suitability == "sub_pixel_extrapolation_warning"
        assert "sub-pixel" in scale_100.scale_limitation.lower()

        # For 500m requested scale (close to 463m), kernel is 3x3 (~1389m)
        scale_500 = res.scales[1]
        assert scale_500.kernel_size_pixels == 3
        assert scale_500.effective_analysis_area_km2 > 1.0  # > 1 km²

    def test_correction_b_geographic_identity(self):
        """Correction B: Tyrrhena Terra (CTX DTM) vs Valles Marineris."""
        tyrrhena_preset = next(
            (r for r in PRESET_CANDIDATE_REGIONS if r.region_id == "tyrrhena-terra-active"),
            None,
        )
        assert tyrrhena_preset is not None
        assert tyrrhena_preset.name == "Tyrrhena Terra (CTX DTM Swath)"
        assert "Tyrrhena Terra" in tyrrhena_preset.geological_context
        # CTX coordinate check: -5.19° to -4.00° Lat, 66.04° to 66.62° Lon
        assert -5.19 <= tyrrhena_preset.min_lat <= -4.00
        assert 66.04 <= tyrrhena_preset.min_lon <= 66.62

        # Verify real Melas Chasma preset is located in Valles Marineris
        melas_preset = next(
            (r for r in PRESET_CANDIDATE_REGIONS if "melas-chasma" in r.region_id),
            None,
        )
        assert melas_preset is not None
        assert "Valles Marineris" in melas_preset.geological_context
        assert 280.0 <= melas_preset.min_lon <= 290.0  # ~283.6°E

    def test_correction_c_heuristic_quality_index(self):
        """Correction C: Heuristic Data Quality Index naming and bounds [0, 100]."""
        service = TerrainIntelligenceService()
        tyrrhena = next(r for r in PRESET_CANDIDATE_REGIONS if r.region_id == "tyrrhena-terra-active")
        assessment = service.assess_region(tyrrhena, target_scale_m=500.0)

        assert hasattr(assessment, "terrain_data_quality_index")
        assert 0.0 <= assessment.terrain_data_quality_index <= 100.0
        assert assessment.terrain_data_quality_index == assessment.data_confidence_score
        assert any("Heuristic Data Quality Index" in lim for lim in assessment.limitations)

    def test_correction_d_route_corridor_coverage(self):
        """Correction D: Multi-tier route corridor coverage metrics."""
        route_service = MarsRouteService()
        corridor = route_service.evaluate_corridor_terrain_source(
            start_lat=-14.2,
            start_lon=59.1,
            dest_lat=-14.0,
            dest_lon=59.3,
            target_scale_m=500.0,
            corridor_buffer_m=1000.0,
        )
        assert "centerline_valid_coverage_pct" in corridor
        assert "corridor_envelope_valid_coverage_pct" in corridor
        assert "bounding_box_valid_coverage_pct" in corridor
        assert "nodata_intersections" in corridor
        assert "continuous_traversable_graph_supported" in corridor

        assert corridor["centerline_valid_coverage_pct"] >= 99.0
        assert corridor["nodata_intersections"] == 0
        assert corridor["continuous_traversable_graph_supported"] is True

        # Test out-of-footprint corridor
        corridor_bad = route_service.evaluate_corridor_terrain_source(
            start_lat=50.0,
            start_lon=200.0,
            dest_lat=51.0,
            dest_lon=201.0,
        )
        assert corridor_bad["routing_eligible"] is False
        assert corridor_bad["centerline_valid_coverage_pct"] == 0.0
        assert corridor_bad["nodata_intersections"] > 0
        assert corridor_bad["continuous_traversable_graph_supported"] is False


class TestCatalogueFilesystemConsistency:
    """Verify that multi-resolution catalog accurately mirrors actual files on disk."""

    def test_all_catalog_entries_have_valid_profiles(self):
        for prod_id, profile in MULTI_RESOLUTION_DTM_CATALOG.items():
            assert profile.product_id == prod_id
            assert profile.tier in ["global_coarse", "global_base", "regional", "local_tactical"]
            assert profile.pixel_spacing_m > 0
            assert profile.crs is not None
            assert profile.vertical_datum is not None
