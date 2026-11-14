"""Comprehensive Verification Test Suite for Phase 8: Resolution-Aware Terrain Intelligence.

Validates:
1. Resolution Selection Engine: local availability, scale suitability, footprint overlap, lifecycle guards.
2. Multi-Scale Topographic Analysis: physical window translation, moving standard deviation, complexity classes.
3. Multi-Resolution Transition Intelligence: footprint intersection, 55.95 ppm scale drift, vertical datum alignment, anti-upsampling rules.
4. Terrain Intelligence & Region Comparison: deterministic scoring, transparent weight accounting, multi-region comparison at equal scales.
5. Adaptive Route Corridor Evaluation: corridor bounds, unsupported segment detection, route provenance.
6. FastAPI Mission Intelligence Endpoints: schemas, error handling, bounding-box validation.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.resolution_selector import (
    ResolutionSelector,
    ResolutionSelectionRequest,
    AnalysisType,
)
from app.terrain.multiscale_analysis import (
    MultiScaleAnalyzer,
    MultiScaleAnalysisRequest,
)
from app.terrain.resolution_transition import (
    ResolutionTransitionService,
    ResolutionTransitionRequest,
    TransitionCompatibilityStatus,
)
from app.science.terrain_intelligence import (
    TerrainIntelligenceService,
    RegionDefinition,
    RegionComparisonRequest,
    PRESET_CANDIDATE_REGIONS,
)
from app.routing.route_service import MarsRouteService


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Stage 1: Resolution Selection Tests ────────────────────────────────────────

def test_resolution_selection_local_available_mola():
    """Verify that MOLA 128 ppd is selected for regional survey inside valid bounds."""
    selector = ResolutionSelector()
    req = ResolutionSelectionRequest(
        min_lat=-10.0,
        min_lon=20.0,
        max_lat=-5.0,
        max_lon=25.0,
        analysis_type=AnalysisType.REGIONAL_SURVEY,
        require_local_raster=True,
    )
    res = selector.select_resolution(req)
    assert res.status == "selected"
    assert res.selected_product_id == "mola-megdr-128"
    assert res.coverage_percentage >= 99.0
    assert res.native_resolution_m == pytest.approx(463.08, abs=1.0)
    assert "mola-megdr-128" in res.selection_rationale


def test_resolution_selection_rejects_discovered_hirise():
    """Verify that discovered HiRISE is never selected when local raster is required."""
    selector = ResolutionSelector()
    req = ResolutionSelectionRequest(
        min_lat=-1.11,
        min_lon=13.80,
        max_lat=-0.77,
        max_lon=13.92,
        analysis_type=AnalysisType.SITE_INSPECTION,
        target_scale_m=1.0,
        require_local_raster=True,
    )
    res = selector.select_resolution(req)
    # HiRISE is discovered (0 local bytes), so selector falls back to available baseline or reports insufficient
    assert res.selected_product_id != "hirise-dtm-schiaparelli"
    # HiRISE should be in rejected_products for availability
    rejected_ids = [r.product_id for r in res.rejected_products]
    assert "hirise-dtm-schiaparelli" in rejected_ids
    hirise_rej = next(r for r in res.rejected_products if r.product_id == "hirise-dtm-schiaparelli")
    assert hirise_rej.stage == "availability"


def test_resolution_selection_ctx_in_melas_chasma():
    """Verify that CTX DTM is selected when requesting hazard assessment inside Melas Chasma."""
    selector = ResolutionSelector()
    req = ResolutionSelectionRequest(
        min_lat=-4.80,
        min_lon=66.10,
        max_lat=-4.50,
        max_lon=66.40,
        analysis_type=AnalysisType.HAZARD_ASSESSMENT,
        target_scale_m=20.0,
        require_local_raster=True,
    )
    res = selector.select_resolution(req)
    assert res.status == "selected"
    assert res.selected_product_id == "ctx-dtm-p21-009323"
    assert res.native_resolution_m == pytest.approx(20.01, abs=0.5)


def test_resolution_selection_partial_coverage_reported():
    """Verify that partial footprint overlap is accurately reported."""
    selector = ResolutionSelector()
    # Spanning across CTX border into uncovered longitude
    req = ResolutionSelectionRequest(
        min_lat=-4.80,
        min_lon=65.00,  # Starts outside CTX
        max_lat=-4.50,
        max_lon=66.40,
        analysis_type=AnalysisType.HAZARD_ASSESSMENT,
        target_scale_m=20.0,
        min_coverage_pct=90.0,
    )
    res = selector.select_resolution(req)
    # Coverage of CTX is partial for this broad box
    ctx_eval = next((c for c in res.evaluated_candidates if c.product_id == "ctx-dtm-p21-009323"), None)
    assert ctx_eval is not None
    assert ctx_eval.coverage_percentage < 90.0


# ── Stage 2: Multi-Scale Topographic Analysis Tests ─────────────────────────────

def test_multiscale_analysis_kernel_sizing():
    """Verify that target physical windows in metres convert to odd pixel kernels k >= 3."""
    analyzer = MultiScaleAnalyzer()
    req = MultiScaleAnalysisRequest(
        min_lat=-5.0,
        min_lon=66.2,
        max_lat=-4.8,
        max_lon=66.4,
        dataset_id="ctx-dtm-p21-009323",
        windows_m=[60.0, 100.0, 200.0, 500.0],
    )
    res = analyzer.analyze_region(req)
    assert len(res.scales) == 4
    for s in res.scales:
        assert s.neighborhood_pixels >= 3
        assert s.neighborhood_pixels % 2 == 1  # Guaranteed odd kernel
        assert s.window_m in [60.0, 100.0, 200.0, 500.0]
        assert s.complexity_class in ["low_complexity", "moderate_complexity", "high_complexity", "insufficient_data"]


def test_multiscale_analysis_metrics_monotonicity_or_scaling():
    """Verify that local relief and roughness scale with physical window diameter."""
    analyzer = MultiScaleAnalyzer()
    req = MultiScaleAnalysisRequest(
        min_lat=-5.0,
        min_lon=66.2,
        max_lat=-4.8,
        max_lon=66.4,
        dataset_id="ctx-dtm-p21-009323",
        windows_m=[100.0, 500.0],
    )
    res = analyzer.analyze_region(req)
    s100 = res.scales[0]
    s500 = res.scales[1]
    # In natural Martian terrain, moving standard deviation over larger window is >= smaller window
    assert s500.mean_roughness_m >= s100.mean_roughness_m * 0.8
    assert s100.mean_slope_deg > 0.0
    assert s100.valid_data_pct > 0.0


# ── Stage 3: Multi-Resolution Transition Intelligence Tests ───────────────────

def test_transition_mola_ctx_compatible_with_transformation():
    """Verify transition between MOLA 128 ppd and CTX DTM is COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION."""
    req = ResolutionTransitionRequest(
        product_a="mola-megdr-128",
        product_b="ctx-dtm-p21-009323",
    )
    eval_res = ResolutionTransitionService.evaluate_transition(req)
    assert eval_res.has_overlap is True
    assert eval_res.overlap_area_km2 > 1000.0
    assert eval_res.transition_status == TransitionCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION
    assert eval_res.horizontal_scale_drift_ppm == pytest.approx(55.95, abs=0.1)
    assert "coarse_to_fine_upsampling_with_claimed_microrelief" in eval_res.forbidden_operations
    assert "region_partitioning" in eval_res.permitted_operations


def test_transition_disjoint_products_insufficient_overlap():
    """Verify that disjoint products report INSUFFICIENT_OVERLAP and forbid cross-pathfinding."""
    req = ResolutionTransitionRequest(
        product_a="ctx-dtm-p21-009323",     # Melas Chasma (~66°E)
        product_b="hirise-dtm-schiaparelli", # Schiaparelli (~13.8°E)
    )
    eval_res = ResolutionTransitionService.evaluate_transition(req)
    assert eval_res.has_overlap is False
    assert eval_res.transition_status == TransitionCompatibilityStatus.INSUFFICIENT_OVERLAP
    assert "cross_product_pathfinding" in eval_res.forbidden_operations


# ── Stage 4: Terrain Intelligence & Region Comparison Tests ───────────────────

def test_terrain_intelligence_single_region_assessment():
    """Verify assessment of Melas Chasma region produces deterministic scores and classes."""
    service = TerrainIntelligenceService()
    region = PRESET_CANDIDATE_REGIONS[0]
    assessment = service.assess_region(region, target_scale_m=500.0)
    assert assessment.region_id == region.region_id
    assert assessment.data_availability == "local_verified"
    assert assessment.data_confidence_score > 70.0
    assert "coverage_component" in assessment.confidence_breakdown
    assert assessment.mean_slope_deg > 0.0


def test_terrain_intelligence_multi_region_comparison():
    """Verify pairwise contrast between candidate regions at equivalent scale."""
    service = TerrainIntelligenceService()
    req = RegionComparisonRequest(
        regions=[PRESET_CANDIDATE_REGIONS[0], PRESET_CANDIDATE_REGIONS[1]],
        target_scale_m=500.0,
    )
    comp = service.compare_regions(req)
    assert len(comp.regions_evaluated) == 2
    assert len(comp.pairwise_comparisons) == 1
    pair = comp.pairwise_comparisons[0]
    assert pair.region_a_id == PRESET_CANDIDATE_REGIONS[0].region_id
    assert pair.region_b_id == PRESET_CANDIDATE_REGIONS[1].region_id
    assert len(comp.methodological_notes) >= 3


# ── Stage 5: Adaptive Route Corridor Source Evaluation Tests ───────────────────

def test_route_corridor_source_evaluation_within_mola():
    """Verify route corridor inside active MOLA 128 tile is approved for planning."""
    route_service = MarsRouteService()
    corridor = route_service.evaluate_corridor_terrain_source(
        start_lat=-14.2,
        start_lon=59.1,
        dest_lat=-14.0,
        dest_lon=59.3,
    )
    assert corridor["routing_eligible"] is True
    assert corridor["primary_terrain_product"] == "mola-megdr-128"
    assert corridor["primary_resolution_m"] == pytest.approx(463.08, abs=1.0)
    assert len(corridor["unsupported_segments"]) == 0


def test_route_corridor_source_evaluation_outside_mola_rejected():
    """Verify route corridor outside active footprint is flagged as ineligible."""
    route_service = MarsRouteService()
    corridor = route_service.evaluate_corridor_terrain_source(
        start_lat=50.0,  # Outside active tile (Lat [-44, 0])
        start_lon=20.0,
        dest_lat=51.0,
        dest_lon=21.0,
    )
    assert corridor["routing_eligible"] is False
    assert len(corridor["unsupported_segments"]) > 0


# ── Stage 6: FastAPI Endpoints Tests ──────────────────────────────────────────

def test_api_resolution_selection_endpoint(client):
    """Test GET /api/v1/science/resolution-selection."""
    res = client.get(
        "/api/v1/science/resolution-selection",
        params={
            "min_lat": -10.0,
            "min_lon": 20.0,
            "max_lat": -5.0,
            "max_lon": 25.0,
            "analysis_type": "regional_survey",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "selected"
    assert data["selected_product_id"] == "mola-megdr-128"


def test_api_terrain_profile_endpoint(client):
    """Test GET /api/v1/science/terrain-profile."""
    res = client.get(
        "/api/v1/science/terrain-profile",
        params={
            "min_lat": -5.0,
            "min_lon": 66.2,
            "max_lat": -4.8,
            "max_lon": 66.4,
            "dataset_id": "ctx-dtm-p21-009323",
            "windows_m": "100,500",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["scales"]) == 2
    assert data["selected_product_id"] == "ctx-dtm-p21-009323"


def test_api_transition_compatibility_endpoint(client):
    """Test GET /api/v1/science/transition-compatibility."""
    res = client.get(
        "/api/v1/science/transition-compatibility",
        params={
            "product_a": "mola-megdr-128",
            "product_b": "ctx-dtm-p21-009323",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_overlap"] is True
    assert data["horizontal_scale_drift_ppm"] == pytest.approx(55.95, abs=0.1)


def test_api_region_assessment_endpoint(client):
    """Test GET /api/v1/science/region-assessment."""
    res = client.get(
        "/api/v1/science/region-assessment",
        params={
            "min_lat": -5.1,
            "min_lon": 66.1,
            "max_lat": -4.5,
            "max_lon": 66.5,
            "name": "Melas Chasma Test",
            "target_scale_m": 500.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data_confidence_score"] > 50.0
    assert data["analysis_scale_m"] == 500.0


def test_api_region_comparison_endpoint(client):
    """Test GET /api/v1/science/region-comparison."""
    res = client.get("/api/v1/science/region-comparison", params={"target_scale_m": 500.0})
    assert res.status_code == 200
    data = res.json()
    assert len(data["regions_evaluated"]) >= 2
    assert len(data["pairwise_comparisons"]) >= 1


def test_api_routing_terrain_source_endpoint(client):
    """Test GET /api/v1/routing/terrain-source."""
    res = client.get(
        "/api/v1/routing/terrain-source",
        params={
            "start_lat": -14.2,
            "start_lon": 59.1,
            "dest_lat": -14.0,
            "dest_lon": 59.3,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["routing_eligible"] is True
    assert data["primary_terrain_product"] == "mola-megdr-128"
