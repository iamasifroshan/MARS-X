"""Phase 8.8.4 Route Intelligence & Scientific Traverse Analysis Test Suite.

Validates:
1. High-resolution elevation profile sampling, cumulative distance monotonicity, and local gradients.
2. Terrain intelligence, slope exposure breakdown, RMSD roughness index, and NoData verification.
3. USGS SIM 3292 chronostratigraphic unit intersections, contact boundaries, and structural features.
4. MGS TES thermal inertia sampling, regolith interpretation, calibration notices, and temperature prohibition.
5. Proximity analysis linking Phase 8.7 science discoveries to route mileposts with evidence classification.
6. Leg-by-leg multi-stop traverse analysis and aggregated analytics with junction deduplication.
7. FastAPI HTTP contracts for route analysis, traverse analysis, and metadata endpoints.
8. Bitwise preservation of authoritative IEEE 754 Float32 elevation benchmarks.
"""

import math
import struct
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.marswalk.marswalk_models import MarswalkRouteRequest
from app.marswalk.marswalk_planner import MarswalkPlanner, TERRAIN_SOURCES, clear_route_cache
from app.marswalk.multi_stop_models import MultiStopRouteRequest, ScienceStop
from app.marswalk.multi_stop_planner import MultiStopPlanner, clear_multi_stop_cache
from app.marswalk.route_intelligence_service import get_route_intelligence_service

client = TestClient(app)


# ==============================================================================
# 1. Elevation Profile Intelligence Tests
# ==============================================================================


class TestElevationProfileIntelligence:
    """Verifies elevation profile extraction, cumulative distance, and local gradients."""

    @pytest.fixture(autouse=True)
    def setup_route(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_name="Tyrrhena Channel Head",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Tyrrhena Channel Mouth",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        self.route = MarswalkPlanner.plan_route(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_route(self.route)

    def test_elevation_profile_point_count_and_monotonic_distance(self):
        """Profile points match route path points and cumulative distance is strictly non-decreasing."""
        points = self.report.elevation_profile.points
        assert len(points) == len(self.route.path_points)
        assert len(points) > 5

        # Check distance monotonicity
        assert points[0].distance_m == 0.0
        for i in range(1, len(points)):
            assert points[i].distance_m >= points[i - 1].distance_m
            assert points[i].sample_index == i

        # Terminal distance equals route total surface distance
        assert abs(points[-1].distance_m - self.report.surface_distance_m) < 1e-2

    def test_elevation_profile_extremes_and_net_change(self):
        """Profile min, max, gain, loss, and net change match analytical definitions."""
        p_summary = self.report.elevation_profile
        elevs = [p.elevation_m for p in p_summary.points]

        assert p_summary.min_elevation_m == round(min(elevs), 2)
        assert p_summary.max_elevation_m == round(max(elevs), 2)
        assert p_summary.net_elevation_change_m == round(elevs[-1] - elevs[0], 2)
        assert p_summary.cumulative_elevation_gain_m >= 0.0
        assert p_summary.cumulative_elevation_loss_m >= 0.0
        assert "MOLA Areoid" in p_summary.vertical_datum

    def test_local_gradient_calculation(self):
        """Local vertical gradients (dz / ds * 100) are computed correctly along the profile."""
        points = self.report.elevation_profile.points
        assert points[0].local_gradient_pct == 0.0

        for i in range(1, len(points)):
            dz = points[i].elevation_m - points[i - 1].elevation_m
            ds = points[i].distance_m - points[i - 1].distance_m
            if ds > 1e-3:
                expected_grad = round((dz / ds) * 100.0, 2)
                assert abs(points[i].local_gradient_pct - expected_grad) < 0.1


# ==============================================================================
# 2. Terrain Intelligence & Roughness Tests
# ==============================================================================


class TestTerrainIntelligenceAndRoughness:
    """Verifies slope distribution, roughness index, and NoData verification."""

    @pytest.fixture(autouse=True)
    def setup_route(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        self.route = MarswalkPlanner.plan_route(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_route(self.route)

    def test_slope_exposure_bands_sum_to_total_distance(self):
        """Sum of slope exposure band distances equals total surface distance."""
        t_summary = self.report.terrain_intelligence
        bands = t_summary.slope_exposure_bands

        total_band_dist = sum(b.distance_m for b in bands)
        assert abs(total_band_dist - self.report.surface_distance_m) < 1.0

        # Percentage sum ~ 100%
        total_pct = sum(b.percentage for b in bands)
        assert abs(total_pct - 100.0) < 1.0

    def test_roughness_index_computation(self):
        """Topographic roughness index is non-negative and classification is populated."""
        t_summary = self.report.terrain_intelligence
        assert t_summary.roughness_index_m >= 0.0
        assert len(t_summary.roughness_classification) > 5
        assert "relief" in t_summary.roughness_classification.lower() or "regolith" in t_summary.roughness_classification.lower()

    def test_zero_nodata_on_verified_route(self):
        """A valid terrain route must have 0.0% NoData exposure."""
        t_summary = self.report.terrain_intelligence
        assert t_summary.nodata_pct == 0.0
        assert t_summary.nodata_distance_m == 0.0
        assert t_summary.coverage_status == "complete_verified_coverage"


# ==============================================================================
# 3. Geological Route Context (USGS SIM 3292)
# ==============================================================================


class TestGeologicalRouteContext:
    """Verifies SIM 3292 unit intersection, contact crossings, and cartographic scale caveats."""

    @pytest.fixture(autouse=True)
    def setup_route(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        self.route = MarswalkPlanner.plan_route(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_route(self.route)

    def test_geological_unit_intersection(self):
        """Route intersects authentic USGS SIM 3292 units (eNh in Tyrrhena Terra)."""
        geo = self.report.geological_context
        assert len(geo.units_traversed) >= 1

        primary_unit = geo.units_traversed[0]
        assert primary_unit.unit_code in ["eNh", "lNv", "mNh", "Undivided"]
        assert primary_unit.traversed_pct > 0.0
        assert primary_unit.traversed_length_m > 0.0

    def test_cartographic_scale_and_uncertainty_disclaimer(self):
        """SIM 3292 metadata strictly documents 1:20M scale and 5-10 km positional uncertainty."""
        geo = self.report.geological_context
        assert geo.published_scale == "1:20,000,000"
        assert geo.positional_uncertainty_km == 5.0
        assert "1:20,000,000" in geo.limitations_disclaimer
        assert "NOT direct" in geo.limitations_disclaimer

    def test_nearby_structures_query(self):
        """Nearby structural features from SIM 3292 Global Structure are identified within corridor."""
        geo = self.report.geological_context
        # Nearby structures list should be populated (or empty if in flat basin)
        assert isinstance(geo.nearby_structures, list)
        for s in geo.nearby_structures:
            assert s.distance_from_route_km >= 0.0
            assert len(s.morphology) > 0


# ==============================================================================
# 4. Thermophysical Context (MGS TES Thermal Inertia)
# ==============================================================================


class TestThermophysicalContext:
    """Verifies TES thermal inertia sampling, regolith interpretation, and temperature prohibition."""

    @pytest.fixture(autouse=True)
    def setup_route(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        self.route = MarswalkPlanner.plan_route(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_route(self.route)

    def test_tes_thermal_inertia_sampling(self):
        """Thermal inertia samples are populated in TIU units."""
        therm = self.report.thermophysical_context
        assert therm.units == "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)"
        assert therm.mean_tiu is not None
        assert 50.0 <= therm.mean_tiu <= 2500.0
        assert len(therm.samples) > 0

    def test_regolith_interpretation_and_temperature_prohibition(self):
        """Thermal inertia provides grain-size/regolith interpretation and prohibits temperature labeling."""
        therm = self.report.thermophysical_context
        assert len(therm.predominant_interpretation) > 10
        assert "temperature" in therm.temperature_prohibition_disclaimer.lower()
        assert "PROHIBITION" in therm.temperature_prohibition_disclaimer


# ==============================================================================
# 5. Science Opportunity Analysis (Phase 8.7 Discoveries)
# ==============================================================================


class TestScienceOpportunityAnalysis:
    """Verifies that nearby candidate discoveries are linked to route mileposts."""

    @pytest.fixture(autouse=True)
    def setup_route(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        self.route = MarswalkPlanner.plan_route(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_route(self.route)

    def test_nearby_discoveries_identified_with_evidence_class(self):
        """Identifies cataloged discoveries within corridor and verifies evidence classification."""
        opps = self.report.nearby_science_opportunities
        assert len(opps) >= 1

        # Tyrrhena CTX discovery should be closest
        tyrrhena_opp = next((o for o in opps if "tyrrhena" in o.discovery_id), None)
        assert tyrrhena_opp is not None
        assert tyrrhena_opp.distance_from_route_km < 50.0
        assert tyrrhena_opp.evidence_class in [
            "direct_sensor_observation",
            "derived_measurement",
            "mapped_geological_interpretation",
            "indicative_proxy",
        ]
        assert "Candidate investigation" in tyrrhena_opp.potential_investigation


# ==============================================================================
# 6. Multi-Leg Traverse Aggregation & Deduplication
# ==============================================================================


class TestMultiLegTraverseAggregation:
    """Verifies multi-stop traverse leg-by-leg analysis and junction deduplication."""

    @pytest.fixture(autouse=True)
    def setup_traverse(self):
        clear_multi_stop_cache()
        req = MultiStopRouteRequest(
            start_name="Base Camp",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Science Hab",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            stops=[
                ScienceStop(stop_id="s1", name="Fluvial Bed", lat=-4.602, lon=66.320, is_mandatory=True),
                ScienceStop(stop_id="s2", name="Terraced Scarp", lat=-4.604, lon=66.322, is_mandatory=True),
            ],
        )
        self.traverse = MultiStopPlanner.plan_multi_stop_traverse(req)
        self.intel_svc = get_route_intelligence_service()
        self.report = self.intel_svc.analyze_multi_stop_traverse(self.traverse)

    def test_multi_leg_structure_and_individual_reports(self):
        """Traverse produces 3 individual leg intelligence reports."""
        assert self.report.total_legs == 3
        assert len(self.report.legs) == 3

        for i, leg_rep in enumerate(self.report.legs):
            assert leg_rep.leg_index == i
            assert leg_rep.surface_distance_m > 0
            assert len(leg_rep.elevation_profile.points) > 0
            assert leg_rep.terrain_intelligence.mean_slope_deg > 0

    def test_junction_vertex_deduplication_in_aggregated_profile(self):
        """Aggregated elevation profile deduplicates junction vertices across consecutive legs."""
        leg_point_counts = [len(leg.elevation_profile.points) for leg in self.report.legs]
        expected_agg_count = sum(leg_point_counts) - (len(self.report.legs) - 1)
        actual_agg_count = len(self.report.aggregated_elevation_profile.points)

        assert actual_agg_count == expected_agg_count

        # Check distance monotonicity across aggregated profile
        agg_pts = self.report.aggregated_elevation_profile.points
        for i in range(1, len(agg_pts)):
            assert agg_pts[i].distance_m >= agg_pts[i - 1].distance_m

        assert abs(agg_pts[-1].distance_m - self.report.total_surface_distance_m) < 1.0


# ==============================================================================
# 7. FastAPI Route Intelligence API Endpoints
# ==============================================================================


class TestRouteIntelligenceApiEndpoints:
    """Verifies FastAPI HTTP contracts for analysis endpoints."""

    def test_get_metadata_endpoint(self):
        """GET /api/v1/marswalk/analysis/metadata returns 200 with complete specification."""
        res = client.get("/api/v1/marswalk/analysis/metadata")
        assert res.status_code == 200
        data = res.json()
        assert data["version"] == "8.8.4"
        assert len(data["scientific_rules"]) >= 5
        assert len(data["terrain_datasets"]) >= 4

    def test_get_nonexistent_route_analysis_returns_404(self):
        """GET /api/v1/marswalk/analysis/route/mw-fake999 returns 404."""
        res = client.get("/api/v1/marswalk/analysis/route/mw-fake999")
        assert res.status_code == 404

    def test_get_nonexistent_traverse_analysis_returns_404(self):
        """GET /api/v1/marswalk/analysis/multi-stop/mst-fake999 returns 404."""
        res = client.get("/api/v1/marswalk/analysis/multi-stop/mst-fake999")
        assert res.status_code == 404

    def test_live_route_and_traverse_analysis_flow(self):
        """End-to-end API flow: plan route -> analyze route, plan traverse -> analyze traverse."""
        # 1. Plan route
        r_plan = client.post("/api/v1/marswalk/route", json={
            "start_lat": -4.600,
            "start_lon": 66.317,
            "dest_lat": -4.605,
            "dest_lon": 66.325,
            "preferred_source": "ctx-tyrrhena",
        })
        assert r_plan.status_code == 200
        route_id = r_plan.json()["route_id"]

        # 2. Get route intelligence
        r_intel = client.get(f"/api/v1/marswalk/analysis/route/{route_id}")
        assert r_intel.status_code == 200
        intel_data = r_intel.json()
        assert intel_data["route_id"] == route_id
        assert intel_data["elevation_profile"]["total_samples"] > 5
        assert len(intel_data["geological_context"]["units_traversed"]) >= 1


# ==============================================================================
# 8. Bitwise Elevation Benchmark Preservation & Coordinate Notation
# ==============================================================================


class TestElevationBenchmarkPreservation:
    """Confirms bitwise IEEE 754 Float32 preservation for all three Mars elevation benchmarks."""

    def test_tyrrhena_ctx_dtm_bitwise_hex(self):
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-tyrrhena")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0x4508d7c3", f"Tyrrhena hex mismatch: {raw_hex}"
        assert abs(val - 2189.485107421875) < 1e-6
        assert round(val, 2) == 2189.49

    def test_apollinaris_sulci_dtm_bitwise_hex(self):
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-apollinaris")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=4.700,
            start_lon=168.250,
            dest_lat=4.706,
            dest_lon=168.258,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0xc5372c4c", f"Apollinaris hex mismatch: {raw_hex}"
        assert abs(val - (-2930.7685546875)) < 1e-6
        assert round(val, 2) == -2930.77

    def test_holden_hirise_dtm_bitwise_hex(self):
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "hirise-holden")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=-28.500,
            start_lon=309.020,
            dest_lat=-28.502,
            dest_lon=309.022,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0xc48d849f", f"Holden hex mismatch: {raw_hex}"
        assert abs(val - (-1132.1444091796875)) < 1e-6
        assert round(val, 2) == -1132.14
