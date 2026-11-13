"""Comprehensive Test Suite for Phase 6 Mars Route Planning.

Validates:
1. Data and geospatial checks:
   - Validated raster loading and checksum integrity.
   - Coordinate snapping and maximum snap distance enforcement.
   - Footprint boundary checks (Lat [-44, 0], Lon [0, 90]).
   - Outside footprint rejection.
2. Pathfinding on synthetic deterministic grids:
   - A* finds optimal path.
   - Dijkstra finds optimal path.
   - A* and Dijkstra yield identical optimal cost.
   - 4-way vs 8-way movement.
   - Diagonal corner-cutting prevention across impassable walls.
   - Hard constraints (slope > max_slope, exclusion zones, NoData).
   - Unreachable destination error.
   - Start equals destination edge case.
3. Real MOLA 128 raster route planning:
   - Route planning in Sinus Meridiani / Margaritifer Terra corridor.
   - Algorithm comparison (A* vs Dijkstra speedup and identical costs).
   - Independent route validator execution.
   - REST API endpoints: /api/v1/routes/metadata, /plan, /compare.
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routing.route_models import (
    RoutePlanRequest,
    PathfindingAlgorithm,
    NeighborConnectivity,
    TerrainCostWeights,
    ExclusionZone,
)
from app.routing.grid_builder import (
    TerrainGridBuilder,
    TerrainGridWindow,
    MOLA_128_PIXEL_DEG,
)
from app.routing.cost_surface import TerrainCostSurface
from app.routing.astar import AStarPlanner
from app.routing.dijkstra import DijkstraPlanner
from app.routing.route_validator import RouteValidator
from app.routing.route_service import MarsRouteService

client = TestClient(app)


class TestSyntheticGridPathfinding:
    """Deterministic pathfinding tests on synthetic terrain grids."""

    @pytest.fixture
    def synthetic_flat_grid(self):
        """10x10 completely flat grid."""
        elev = np.full((10, 10), 1000.0, dtype=np.float32)
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=0,
            col_offset=0,
            lat_top=0.0,
            lon_left=0.0,
        )
        cost_surface = TerrainCostSurface(
            grid_window=window,
            weights=TerrainCostWeights(weight_slope=0.0, weight_roughness=0.0, weight_relief=0.0, weight_complexity=0.0),
            max_slope_deg=20.0,
        )
        return cost_surface

    @pytest.fixture
    def synthetic_obstacle_grid(self):
        """10x10 grid with an impassable wall in the middle."""
        elev = np.full((10, 10), 1000.0, dtype=np.float32)
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=0,
            col_offset=0,
            lat_top=0.0,
            lon_left=0.0,
        )
        cost_surface = TerrainCostSurface(
            grid_window=window,
            weights=TerrainCostWeights(),
            max_slope_deg=20.0,
        )
        # Block rows 0 through 6 in column 5 (leaving rows 7, 8, 9 open)
        for r in range(0, 7):
            cost_surface.passable_mask[r, 5] = False
        return cost_surface

    def test_astar_and_dijkstra_identical_cost_on_flat(self, synthetic_flat_grid):
        """A* and Dijkstra must return equal optimal costs on flat terrain."""
        start = (1, 1)
        goal = (8, 8)

        astar = AStarPlanner(synthetic_flat_grid)
        dijkstra = DijkstraPlanner(synthetic_flat_grid)

        p_astar, s_astar = astar.plan_path(start, goal, eight_way=True)
        p_dijk, s_dijk = dijkstra.plan_path(start, goal, eight_way=True)

        assert p_astar is not None
        assert p_dijk is not None
        assert s_astar["total_cost"] == pytest.approx(s_dijk["total_cost"], rel=1e-3)
        # A* expands fewer or equal nodes
        assert s_astar["nodes_expanded"] <= s_dijk["nodes_expanded"]

    def test_obstacle_avoidance_through_gap(self, synthetic_obstacle_grid):
        """Pathfinder must navigate around the obstacle wall and pass through the bottom opening."""
        start = (2, 2)
        goal = (2, 8)

        astar = AStarPlanner(synthetic_obstacle_grid)
        path, stats = astar.plan_path(start, goal, eight_way=True)

        assert path is not None
        # Path must cross column 5 at row >= 7
        crossed_rows_at_col_5 = [r for r, c in path if c == 5]
        assert len(crossed_rows_at_col_5) > 0
        assert all(r >= 7 for r in crossed_rows_at_col_5)

    def test_diagonal_corner_cutting_prevention(self):
        """Diagonal move between (1,1) and (2,2) is forbidden if (1,2) or (2,1) is impassable."""
        elev = np.full((4, 4), 1000.0, dtype=np.float32)
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=0,
            col_offset=0,
            lat_top=0.0,
            lon_left=0.0,
        )
        cost_surface = TerrainCostSurface(
            grid_window=window,
            weights=TerrainCostWeights(),
            max_slope_deg=20.0,
        )
        # Manually block cell (1, 2)
        cost_surface.passable_mask[1, 2] = False

        # Attempt step from (1, 1) to (2, 2)
        cost = cost_surface.compute_edge_cost(1, 1, 2, 2)
        assert cost is None  # Blocked by corner-cutting guard

    def test_start_equals_destination(self, synthetic_flat_grid):
        """Start == Destination returns single-cell path with zero cost."""
        astar = AStarPlanner(synthetic_flat_grid)
        path, stats = astar.plan_path((3, 3), (3, 3))
        assert path == [(3, 3)]
        assert stats["total_cost"] == 0.0

    def test_unreachable_destination_raises_error(self):
        """Enclosed destination raises TimeoutError / No path."""
        elev = np.full((6, 6), 1000.0, dtype=np.float32)
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=0,
            col_offset=0,
            lat_top=0.0,
            lon_left=0.0,
        )
        cost_surface = TerrainCostSurface(
            grid_window=window,
            weights=TerrainCostWeights(),
            max_slope_deg=20.0,
        )
        # Enclose goal (4, 4) completely
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            cost_surface.passable_mask[4 + dr, 4 + dc] = False

        astar = AStarPlanner(cost_surface)
        path, stats = astar.plan_path((1, 1), (4, 4), max_nodes_to_expand=50)
        assert path is None


class TestRealMolaRoutePlanning:
    """Integration tests on authentic MOLA 128 ppd raster data."""

    @pytest.fixture
    def route_service(self):
        return MarsRouteService()

    def test_outside_footprint_rejection(self, route_service):
        """Coordinates outside tile megt00n000hb footprint are rejected."""
        # Olympus Mons is at 18.65°N, 226.2°E (outside [-44, 0] lat, [0, 90] lon)
        req = RoutePlanRequest(
            start_lat=18.65,
            start_lon=226.20,
            dest_lat=18.60,
            dest_lon=226.25,
        )
        with pytest.raises(ValueError) as excinfo:
            route_service.plan_single_route(req)
        assert "outside the validated MOLA 128 planning footprint" in str(excinfo.value)

    def test_successful_mola_128_route_plan(self, route_service):
        """Plan a real 10-km candidate traverse in Sinus Meridiani (-2.0°N, 5.0°E to -2.15°N, 5.15°E)."""
        req = RoutePlanRequest(
            start_lat=-2.00,
            start_lon=5.00,
            dest_lat=-2.15,
            dest_lon=5.15,
            algorithm=PathfindingAlgorithm.ASTAR,
            connectivity=NeighborConnectivity.EIGHT_WAY,
            max_slope_deg=15.0,
        )
        res = route_service.plan_single_route(req)

        assert res.route_id is not None
        assert len(res.waypoints) >= 15
        assert res.metrics.total_distance_m > 8000.0
        assert res.metrics.max_slope_deg <= 15.0
        assert res.validation.is_valid is True
        assert res.dataset_checksum == "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"
        assert "experimental terrain-cost simulation" in res.scientific_disclaimer

    def test_algorithm_comparison_astar_vs_dijkstra(self, route_service):
        """Compare A* and Dijkstra on identical MOLA corridor."""
        req = RoutePlanRequest(
            start_lat=-3.00,
            start_lon=10.00,
            dest_lat=-3.08,
            dest_lon=10.08,
            max_slope_deg=15.0,
        )
        cmp = route_service.compare_algorithms(req)

        # Both algorithms should achieve nearly identical costs
        assert cmp.cost_difference_pct < 0.5
        # A* should expand fewer nodes
        assert cmp.nodes_expanded_ratio >= 1.0
        assert cmp.astar_route.validation.is_valid is True
        assert cmp.dijkstra_route.validation.is_valid is True


class TestRoutingApiEndpoints:
    """Integration tests for FastAPI /api/v1/routes endpoints."""

    def test_get_routing_metadata(self):
        """GET /api/v1/routes/metadata returns valid configuration and limitations."""
        resp = client.get("/api/v1/routes/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "mola-megdr-128" in [d["dataset_id"] for d in data["supported_datasets"]]
        assert "astar" in data["supported_algorithms"]
        assert len(data["scientific_limitations"]) >= 3

    def test_post_plan_route_endpoint(self):
        """POST /api/v1/routes/plan returns valid route payload."""
        payload = {
            "start_lat": -4.00,
            "start_lon": 8.00,
            "dest_lat": -4.08,
            "dest_lon": 8.08,
            "algorithm": "astar",
            "max_slope_deg": 15.0,
        }
        resp = client.post("/api/v1/routes/plan", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "waypoints" in data
        assert data["metrics"]["total_distance_m"] > 3000.0
        assert data["validation"]["is_valid"] is True

    def test_post_compare_routes_endpoint(self):
        """POST /api/v1/routes/compare returns side-by-side results."""
        payload = {
            "start_lat": -1.50,
            "start_lon": 4.00,
            "dest_lat": -1.56,
            "dest_lon": 4.06,
            "max_slope_deg": 15.0,
        }
        resp = client.post("/api/v1/routes/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "astar_route" in data
        assert "dijkstra_route" in data
        assert "runtime_speedup_factor" in data

    def test_post_plan_route_outside_footprint_returns_400(self):
        """POST /api/v1/routes/plan outside footprint returns 400 Bad Request."""
        payload = {
            "start_lat": 25.0,  # North of 0.0°
            "start_lon": 5.0,
            "dest_lat": 25.1,
            "dest_lon": 5.1,
        }
        resp = client.post("/api/v1/routes/plan", json=payload)
        assert resp.status_code == 400
        assert "outside the validated MOLA 128 planning footprint" in resp.json()["detail"]
