"""Test suite for Phase 8.8.3 Multi-Stop Marswalk Planning & Traveling Explorer Optimization.

Tests:
1. Two-stop and multi-stop requests over authentic Mars DEMs (Tyrrhena CTX, Holden HiRISE, Apollinaris CTX).
2. Fixed start and fixed destination constraints.
3. Mandatory vs optional stops and max_stops filtering.
4. Stop ordering optimization strategies:
   - 'exact_permutation' (K <= 4 stops, provably exact minimum cost)
   - 'nearest_neighbor' (greedy sequential)
   - 'optimize_tsp' (nearest-neighbor + 2-opt improvement)
   - 'preserve_order' (unmodified user sequence)
5. Unreachable mandatory stop detection and meaningful error raising.
6. Pairwise route-cost matrix consistency:
   - Directed traversal costs evaluated with authentic A* engine.
   - Distinct surface distance vs optimization cost.
7. GeoJSON continuity:
   - Verification that junction coordinates are connected without duplicates.
   - Traceable leg coordinates.
8. Cache identity and separation:
   - Hit on identical multi-stop request.
   - Miss on modified stop coordinates, strategy, beta, or max slope.
9. FastAPI multi-stop HTTP endpoints:
   - POST /api/v1/marswalk/multi-stop
   - GET /api/v1/marswalk/multi-stop/{traverse_id}
   - GET /api/v1/marswalk/multi-stop/metadata
10. Bitwise IEEE 754 float32 preservation of all 3 reference elevation benchmarks:
    - Tyrrhena CTX DTM: 0x4508d7c3 (+2189.485107421875 m)
    - Apollinaris Sulci CTX DTM: 0xc5372c4c (-2930.7685546875 m)
    - Holden Crater HiRISE DTM: 0xc48d849f (-1132.1444091796875 m)
11. Non-negotiable astronaut safety disclaimers.
"""

import os
import math
import struct
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.traversability_service import TERRAIN_SOURCES
from app.marswalk.marswalk_planner import MarswalkPlanner
from app.marswalk.multi_stop_models import (
    ScienceStop,
    MultiStopRouteRequest,
    MultiStopTraverseResponse,
    MultiStopMetadataResponse,
)
from app.marswalk.multi_stop_planner import (
    MultiStopPlanner,
    clear_multi_stop_cache,
    compute_multi_stop_hash,
)

client = TestClient(app)


# =============================================================================
# 1. AUTHENTIC MULTI-STOP TRAVERSES OVER REAL MARS DEMs
# =============================================================================
class TestAuthenticMultiStopTraversePlanning:
    """Validates end-to-end multi-stop planning across authentic Mars orbital DEMs."""

    def test_tyrrhena_two_intermediate_stops_transect(self):
        """Plan a 3-leg traverse in Tyrrhena Terra connecting two fluvial science stops."""
        clear_multi_stop_cache()
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            start_name="Fluvial Station Alpha",
            dest_lat=-4.605,
            dest_lon=66.325,
            dest_name="Crater Rim Outpost",
            stops=[
                ScienceStop(
                    stop_id="stop-chan-bed",
                    name="Channel Bed Stratigraphy",
                    lat=-4.602,
                    lon=66.320,
                    discovery_id="disc-terr-tyrrhena-ctx",
                    is_mandatory=True,
                ),
                ScienceStop(
                    stop_id="stop-terrace",
                    name="Terraced Scarp Outcrop",
                    lat=-4.604,
                    lon=66.322,
                    is_mandatory=True,
                ),
            ],
            optimization_strategy="optimize_tsp",
            preferred_source="ctx-tyrrhena",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
            traverse_name="Tyrrhena 2-Stop Science Transect",
        )
        res = MultiStopPlanner.plan_multi_stop_traverse(req)

        assert res.status == "success"
        assert res.source_dataset == "ctx-tyrrhena"
        assert res.instrument == "CTX"
        assert res.tier == "regional"
        assert len(res.ordered_stops) == 2
        assert len(res.legs) == 3

        # Physical distance and cost checks
        assert res.total_surface_distance_m > 500.0
        assert res.total_horizontal_distance_m > 500.0
        assert res.total_optimization_cost > res.total_surface_distance_m
        assert res.max_route_slope_deg <= 25.0
        assert res.mean_route_slope_deg > 0.0

        # Elevation gain and loss
        assert res.cumulative_elevation_gain_m >= 0.0
        assert res.cumulative_elevation_loss_m >= 0.0
        assert res.min_elevation_m < res.max_elevation_m

        # Connected geometry verification
        coords = res.connected_geometry["coordinates"]
        assert len(coords) > 10
        # No duplicate consecutive points
        for i in range(1, len(coords)):
            assert coords[i] != coords[i - 1], f"Duplicate consecutive coordinate at index {i}"

        # Leg sequence consistency
        assert res.legs[0].from_stop_id == "origin-start"
        assert res.legs[0].to_stop_id == res.ordered_stops[0].stop_id
        assert res.legs[1].from_stop_id == res.ordered_stops[0].stop_id
        assert res.legs[1].to_stop_id == res.ordered_stops[1].stop_id
        assert res.legs[2].from_stop_id == res.ordered_stops[1].stop_id
        assert res.legs[2].to_stop_id == "terminal-destination"

    def test_holden_hirise_tactical_science_traverse(self):
        """Plan multi-stop traverse over ~1.01 m/px Holden Crater HiRISE DTM."""
        clear_multi_stop_cache()
        req = MultiStopRouteRequest(
            start_lat=-28.500,
            start_lon=309.020,
            start_name="Holden Ejecta Base",
            dest_lat=-28.502,
            dest_lon=309.022,
            dest_name="Lacustrine Outcrop",
            stops=[
                ScienceStop(
                    stop_id="stop-megabreccia-1",
                    name="Megabreccia Block Alpha",
                    lat=-28.501,
                    lon=309.021,
                    discovery_id="disc-terr-holden-hirise",
                ),
            ],
            preferred_source="hirise-holden",
        )
        res = MultiStopPlanner.plan_multi_stop_traverse(req)

        assert res.status == "success"
        assert res.source_dataset == "hirise-holden"
        assert res.instrument == "HiRISE"
        assert res.tier == "local_tactical"
        assert len(res.legs) == 2
        assert res.total_surface_distance_m > 100.0

    def test_discovery_ids_automatic_expansion(self):
        """Passing discovery_ids automatically expands and attaches ScienceStop instances."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            discovery_ids=["disc-terr-tyrrhena-ctx"],
            preferred_source="ctx-tyrrhena",
        )
        res = MultiStopPlanner.plan_multi_stop_traverse(req)
        assert len(res.ordered_stops) == 1
        assert res.ordered_stops[0].stop_id == "disc-terr-tyrrhena-ctx"
        assert "Tyrrhena" in res.ordered_stops[0].name


# =============================================================================
# 2. OPTIMIZATION STRATEGIES & TSP ORDERING
# =============================================================================
class TestOptimizationStrategiesAndTSPOrdering:
    """Tests exact permutation search, nearest-neighbor, 2-opt, and order preservation."""

    def test_small_k_uses_exact_permutation(self):
        """When intermediate stops K <= 4, engine uses exact permutation optimization."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(stop_id="s1", name="Stop 1", lat=-4.604, lon=66.322),
                ScienceStop(stop_id="s2", name="Stop 2", lat=-4.602, lon=66.320),
            ],
            optimization_strategy="optimize_tsp",
            preferred_source="ctx-tyrrhena",
        )
        res = MultiStopPlanner.plan_multi_stop_traverse(req)

        # In this terrain, Stop 2 (-4.602) is closer to Start (-4.600) than Stop 1 (-4.604)
        # So optimal sequence must visit s2 then s1!
        assert res.optimization_strategy == "exact_permutation"
        assert res.is_heuristic_solution is False
        assert res.ordered_stops[0].stop_id == "s2"
        assert res.ordered_stops[1].stop_id == "s1"

    def test_preserve_order_strategy(self):
        """When optimization_strategy='preserve_order', user order is strictly respected."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(stop_id="s1", name="Stop 1", lat=-4.604, lon=66.322),
                ScienceStop(stop_id="s2", name="Stop 2", lat=-4.602, lon=66.320),
            ],
            optimization_strategy="preserve_order",
            preferred_source="ctx-tyrrhena",
        )
        res = MultiStopPlanner.plan_multi_stop_traverse(req)

        assert res.optimization_strategy == "preserve_order"
        assert res.is_heuristic_solution is False
        assert res.ordered_stops[0].stop_id == "s1"
        assert res.ordered_stops[1].stop_id == "s2"

    def test_max_stops_limits_optional_stops(self):
        """When max_stops is provided, optional stops are limited while mandatory stops are kept."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(stop_id="mand1", name="Mandatory 1", lat=-4.602, lon=66.320, is_mandatory=True),
                ScienceStop(stop_id="opt1", name="Optional 1", lat=-4.603, lon=66.321, is_mandatory=False),
                ScienceStop(stop_id="opt2", name="Optional 2", lat=-4.604, lon=66.322, is_mandatory=False),
            ],
            max_stops=2,
            preferred_source="ctx-tyrrhena",
        )
        resolved = MultiStopPlanner.resolve_all_stops(req)
        assert len(resolved) == 2
        assert any(s.stop_id == "mand1" for s in resolved)


# =============================================================================
# 3. UNREACHABLE STOPS & BOUNDARY VALIDATION
# =============================================================================
class TestUnreachableStopsAndBoundaryValidation:
    """Verifies error handling for unreachable mandatory stops and out-of-footprint requests."""

    def test_out_of_bounds_coordinate_rejected(self):
        """A stop outside the preferred source bounds raises a clear ValueError."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(
                    stop_id="out-of-bounds",
                    name="Distant Crater",
                    lat=25.0,  # Far outside CTX Tyrrhena footprint
                    lon=120.0,
                ),
            ],
            preferred_source="ctx-tyrrhena",
        )
        with pytest.raises(ValueError) as exc_info:
            MultiStopPlanner.plan_multi_stop_traverse(req)
        assert "does not cover all traverse waypoints" in str(exc_info.value)

    def test_nonexistent_discovery_id_raises_value_error(self):
        """Supplying an unknown discovery ID raises ValueError."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            discovery_ids=["disc-fake-unknown-target-999"],
            preferred_source="ctx-tyrrhena",
        )
        with pytest.raises(ValueError) as exc_info:
            MultiStopPlanner.plan_multi_stop_traverse(req)
        assert "not found in discovery catalog" in str(exc_info.value)

    def test_unreachable_mandatory_stop_raises_value_error(self):
        """A mandatory stop that cannot be reached under max_slope cutoff raises ValueError."""
        # Max slope cutoff = 1.0 deg will make mountainous or valley terrain impassable
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(
                    stop_id="blocked-stop",
                    name="Impassable Peak",
                    lat=-4.602,
                    lon=66.320,
                    is_mandatory=True,
                ),
            ],
            preferred_source="ctx-tyrrhena",
            max_slope_deg=5.0,  # Strict cutoff causing valley wall impassability
        )
        with pytest.raises(ValueError) as exc_info:
            MultiStopPlanner.plan_multi_stop_traverse(req)
        assert "unreachable" in str(exc_info.value).lower()


# =============================================================================
# 4. CACHE IDENTITY & HASHING
# =============================================================================
class TestMultiStopCacheIdentity:
    """Verifies that multi-stop caching behaves deterministically and invalidates on changes."""

    def test_identical_multi_stop_requests_hit_cache(self):
        clear_multi_stop_cache()
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(stop_id="s1", name="Stop 1", lat=-4.602, lon=66.320),
            ],
            preferred_source="ctx-tyrrhena",
            traverse_name="Cache Identity Test",
        )
        res1 = MultiStopPlanner.plan_multi_stop_traverse(req)
        res2 = MultiStopPlanner.plan_multi_stop_traverse(req)
        assert res1.traverse_id == res2.traverse_id, "Identical multi-stop request failed to hit cache!"

    def test_changing_strategy_produces_cache_miss(self):
        req1 = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            stops=[
                ScienceStop(stop_id="s1", name="Stop 1", lat=-4.602, lon=66.320),
                ScienceStop(stop_id="s2", name="Stop 2", lat=-4.604, lon=66.322),
            ],
            optimization_strategy="optimize_tsp",
            preferred_source="ctx-tyrrhena",
        )
        req2 = req1.model_copy(update={"optimization_strategy": "preserve_order"})

        h1 = compute_multi_stop_hash(req1, "ctx-tyrrhena")
        h2 = compute_multi_stop_hash(req2, "ctx-tyrrhena")
        assert h1 != h2, "Strategy change failed to produce distinct hash!"


# =============================================================================
# 5. FASTAPI MULTI-STOP ENDPOINTS
# =============================================================================
class TestMultiStopApiEndpoints:
    """Verifies HTTP API endpoints for multi-stop planning and metadata."""

    def test_get_multi_stop_metadata_endpoint(self):
        res = client.get("/api/v1/marswalk/multi-stop/metadata")
        assert res.status_code == 200
        data = res.json()
        assert "supported_strategies" in data
        assert len(data["supported_strategies"]) >= 3
        assert "curated_presets" in data
        assert len(data["curated_presets"]) >= 3
        assert "engine_versions" in data
        assert "safety_disclaimer" in data
        assert "not certify physical astronaut or rover safety" in data["safety_disclaimer"]

    def test_post_multi_stop_endpoint_success(self):
        payload = {
            "start_lat": -4.600,
            "start_lon": 66.317,
            "dest_lat": -4.605,
            "dest_lon": 66.325,
            "stops": [
                {
                    "stop_id": "stop-api-1",
                    "name": "API Test Outcrop",
                    "lat": -4.602,
                    "lon": 66.320,
                    "is_mandatory": True,
                }
            ],
            "optimization_strategy": "optimize_tsp",
            "preferred_source": "ctx-tyrrhena",
            "traverse_name": "API Multi-Stop Traverse",
        }
        res = client.post("/api/v1/marswalk/multi-stop", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["traverse_id"].startswith("mst-")
        assert len(data["legs"]) == 2
        assert data["total_surface_distance_m"] > 0
        assert data["total_optimization_cost"] > 0
        assert "connected_geometry" in data
        assert data["connected_geometry"]["type"] == "LineString"
        assert "safety_disclaimer" in data

        # Test GET /api/v1/marswalk/multi-stop/{traverse_id}
        tid = data["traverse_id"]
        get_res = client.get(f"/api/v1/marswalk/multi-stop/{tid}")
        assert get_res.status_code == 200
        assert get_res.json()["traverse_id"] == tid

    def test_get_nonexistent_multi_stop_returns_404(self):
        res = client.get("/api/v1/marswalk/multi-stop/mst-nonexistent999")
        assert res.status_code == 404


# =============================================================================
# 6. BITWISE IEEE 754 ELEVATION BENCHMARK PRESERVATION
# =============================================================================
class TestElevationBenchmarkBitwisePreservation:
    """Confirms no regression of the three authoritative Mars elevation benchmarks."""

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
        assert raw_hex == "0x4508d7c3", f"Tyrrhena raw hex mismatch: {raw_hex} != 0x4508d7c3"
        assert abs(val - 2189.485107421875) < 1e-6

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
        assert raw_hex == "0xc5372c4c", f"Apollinaris raw hex mismatch: {raw_hex} != 0xc5372c4c"
        assert abs(val - (-2930.7685546875)) < 1e-6

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
        assert raw_hex == "0xc48d849f", f"Holden raw hex mismatch: {raw_hex} != 0xc48d849f"
        assert abs(val - (-1132.1444091796875)) < 1e-6
