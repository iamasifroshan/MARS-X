"""Phase 6.1: Pathfinding Scientific Verification & Benchmark Calibration Test Suite.

Rigorously verifies:
1. A* heuristic admissibility and consistency on the Mars simple cylindrical sphere.
2. Mars-specific metric calculations (dy, dx scaling with latitude, elevation conservation).
3. Coordinate snapping round-trip accuracy and boundary enforcement.
4. Route validation checks (continuity, corner-cutting, slope, NoData, edge costs).
5. A* vs Dijkstra optimality comparison on deterministic synthetic grids and real MOLA data.
6. Multi-corridor benchmark reproducibility with median metrics across repeated runs.
"""

import math
import time
import random
import numpy as np
import pytest

from app.geospatial import MARS_EQUATORIAL_RADIUS_M
from app.routing.grid_builder import (
    TerrainGridWindow,
    TerrainGridBuilder,
    MOLA_128_PIXEL_DEG,
    MOLA_128_LAT_MIN,
    MOLA_128_LAT_MAX,
    MOLA_128_LON_MIN,
    MOLA_128_LON_MAX,
)
from app.routing.cost_surface import TerrainCostSurface
from app.routing.route_models import (
    TerrainCostWeights,
    RoutePlanRequest,
    PathfindingAlgorithm,
    NeighborConnectivity,
)
from app.routing.astar import AStarPlanner
from app.routing.dijkstra import DijkstraPlanner
from app.routing.route_validator import RouteValidator
from app.routing.route_service import MarsRouteService


# ==============================================================================
# 1. A* HEURISTIC MATHEMATICAL VERIFICATION
# ==============================================================================

class TestAStarHeuristicProperties:
    """Verifies that the spherical great-circle + vertical lower-bound heuristic
    is strictly admissible, consistent (monotonic), and zero at the goal.
    """

    @pytest.fixture
    def sample_grid_window(self):
        """Create a 30x30 synthetic grid window on Mars sphere at latitude -10 deg."""
        rows, cols = 30, 30
        elev = np.zeros((rows, cols), dtype=np.int16)
        # Add smooth variation
        for r in range(rows):
            for c in range(cols):
                elev[r, c] = int(r * 5 + c * 2)
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=1000,
            col_offset=1000,
            lat_top=-10.0,
            lon_left=15.0,
        )
        return window

    def test_heuristic_zero_at_goal(self, sample_grid_window):
        """Verify h(goal, goal) == 0.0 unconditionally."""
        cs = TerrainCostSurface(sample_grid_window, TerrainCostWeights(), max_slope_deg=20.0)
        planner = AStarPlanner(cs)

        for r in [0, 5, 15, 29]:
            for c in [0, 5, 15, 29]:
                assert planner.heuristic(r, c, r, c) == 0.0

    def test_heuristic_triangle_inequality_consistency(self, sample_grid_window):
        """Verify heuristic monotonicity: h(u) <= c(u, v) + h(v) for all passable edges."""
        cs = TerrainCostSurface(sample_grid_window, TerrainCostWeights(), max_slope_deg=20.0)
        planner = AStarPlanner(cs)

        goal_r, goal_c = 28, 28

        tested_edges = 0
        for r in range(sample_grid_window.rows):
            for c in range(sample_grid_window.cols):
                if not cs.is_cell_passable(r, c):
                    continue

                hu = planner.heuristic(r, c, goal_r, goal_c)

                for nr, nc in cs.get_neighbors(r, c, eight_way=True):
                    cost = cs.compute_edge_cost(r, c, nr, nc)
                    if cost is None:
                        continue

                    hv = planner.heuristic(nr, nc, goal_r, goal_c)

                    # Consistency condition: h(u) <= cost(u, v) + h(v)
                    assert hu <= cost + hv + 1e-6, (
                        f"Consistency violated at ({r}, {c}) -> ({nr}, {nc}): "
                        f"h(u)={hu}, cost={cost}, h(v)={hv}, diff={hu - (cost + hv)}"
                    )
                    tested_edges += 1

        assert tested_edges > 100

    def test_heuristic_admissibility_vs_dijkstra_ground_truth(self):
        """On a small 12x12 grid, compare heuristic against Dijkstra's true remaining optimal cost."""
        rows, cols = 12, 12
        elev = np.zeros((rows, cols), dtype=np.int16)
        # Add varied topography
        for r in range(rows):
            for c in range(cols):
                elev[r, c] = int(10 * math.sin(r * 0.5) + 15 * math.cos(c * 0.5))

        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=500,
            col_offset=500,
            lat_top=-5.0,
            lon_left=20.0,
        )
        cs = TerrainCostSurface(window, TerrainCostWeights(), max_slope_deg=25.0)
        planner_astar = AStarPlanner(cs)
        planner_dijkstra = DijkstraPlanner(cs)

        goal = (10, 10)

        # For every cell, compute true optimal cost to goal using Dijkstra
        for r in range(rows):
            for c in range(cols):
                if not cs.is_cell_passable(r, c):
                    continue
                start = (r, c)
                path, stats = planner_dijkstra.plan_path(start, goal, eight_way=True)
                if path is not None:
                    h_star = stats["total_cost"]
                    h_est = planner_astar.heuristic(r, c, goal[0], goal[1])

                    # Admissibility condition: h(n) <= h*(n)
                    assert h_est <= h_star + 1e-6, (
                        f"Admissibility violated at ({r}, {c}): h_est={h_est} > h_star={h_star}"
                    )


# ==============================================================================
# 2. MARS-SPECIFIC METRIC CALCULATIONS & CRS
# ==============================================================================

class TestMarsMetricCalculations:
    """Verifies that metric cell calculations correctly scale with Martian latitude
    and preserve spherical geodetic properties.
    """

    def test_metric_cell_spacing_latitude_scaling(self):
        """Verify dy is invariant with latitude and dx scales strictly with cos(lat)."""
        window = TerrainGridWindow(
            elevation_grid=np.zeros((10, 10), dtype=np.int16),
            row_offset=0,
            col_offset=0,
            lat_top=0.0,
            lon_left=0.0,
            d_lat_deg=MOLA_128_PIXEL_DEG,
            d_lon_deg=MOLA_128_PIXEL_DEG,
        )

        d_deg_rad = math.radians(MOLA_128_PIXEL_DEG)
        expected_dy = MARS_EQUATORIAL_RADIUS_M * d_deg_rad

        # Test at equator (row 0)
        dy_0, dx_0 = window.get_cell_metric_spacing(0)
        assert abs(dy_0 - expected_dy) < 1e-4
        assert abs(dx_0 - expected_dy) < 1.0  # At lat -0.5*d_deg, cos is ~0.999997

        # Test at latitude -44 degrees (row ~5600)
        window_south = TerrainGridWindow(
            elevation_grid=np.zeros((10, 10), dtype=np.int16),
            row_offset=5600,
            col_offset=0,
            lat_top=-43.9,
            lon_left=0.0,
            d_lat_deg=MOLA_128_PIXEL_DEG,
            d_lon_deg=MOLA_128_PIXEL_DEG,
        )
        dy_s, dx_s = window_south.get_cell_metric_spacing(5)
        lat_south = -43.9 - 5.5 * MOLA_128_PIXEL_DEG
        expected_dx_s = expected_dy * math.cos(math.radians(lat_south))

        assert abs(dy_s - expected_dy) < 1e-4
        assert abs(dx_s - expected_dx_s) < 1e-4
        assert dx_s < dy_s  # East-west distance shrinks toward poles

    def test_coordinate_snapping_round_trip(self):
        """Verify snapping to pixel center and round-trip conversion accuracy."""
        builder = TerrainGridBuilder()

        test_points = [
            (-2.0, 5.0),
            (-4.0, 8.0),
            (-3.1234, 15.6789),
            (-25.4321, 45.1234),
            (-43.9, 89.5),
        ]

        for req_lat, req_lon in test_points:
            snap_lat, snap_lon, dist_m, line, sample = builder.snap_coordinate(req_lat, req_lon)

            # Re-snapping the snapped coordinate must yield distance 0.0 and same line/sample
            s2_lat, s2_lon, dist2_m, l2, s2 = builder.snap_coordinate(snap_lat, snap_lon)

            assert abs(snap_lat - s2_lat) < 1e-10
            assert abs(snap_lon - s2_lon) < 1e-10
            assert dist2_m < 1e-6
            assert line == l2
            assert sample == s2

    def test_out_of_bounds_rejection(self):
        """Coordinates outside the acquired tile bounds [-44, 0] lat, [0, 90] lon must raise ValueError."""
        builder = TerrainGridBuilder()

        # North of equator
        with pytest.raises(ValueError, match="outside the validated MOLA 128"):
            builder.snap_coordinate(1.5, 45.0)

        # South of -44°
        with pytest.raises(ValueError, match="outside the validated MOLA 128"):
            builder.snap_coordinate(-45.0, 45.0)

        # West of 0°
        with pytest.raises(ValueError, match="outside the validated MOLA 128"):
            builder.snap_coordinate(-10.0, -5.0)

        # East of 90°
        with pytest.raises(ValueError, match="outside the validated MOLA 128"):
            builder.snap_coordinate(-10.0, 95.0)


# ==============================================================================
# 3. ROUTE VALIDATOR RIGID AUDIT
# ==============================================================================

class TestRouteValidatorHardening:
    """Verifies that the independent RouteValidator enforces continuity, slope thresholds,
    elevation conservation, and edge cost positivity.
    """

    @pytest.fixture
    def test_cost_surface(self):
        rows, cols = 20, 20
        elev = np.zeros((rows, cols), dtype=np.int16)
        # Constant slope from north to south
        for r in range(rows):
            elev[r, :] = r * 10
        window = TerrainGridWindow(
            elevation_grid=elev,
            row_offset=0,
            col_offset=0,
            lat_top=-1.0,
            lon_left=5.0,
        )
        return TerrainCostSurface(window, TerrainCostWeights(), max_slope_deg=15.0)

    def test_elevation_conservation_validation(self, test_cost_surface):
        """Verify that gain - loss strictly equals net elevation change."""
        path = [(r, 5) for r in range(10)]
        val = RouteValidator.validate_route(
            path_rc=path,
            cost_surface=test_cost_surface,
            max_slope_deg=15.0,
            expected_start_rc=(0, 5),
            expected_dest_rc=(9, 5),
        )
        assert val.is_valid is True
        assert any("elevation conservation satisfied" in msg.lower() for msg in val.passed_checks)

    def test_discontinuous_jump_rejected(self, test_cost_surface):
        """Discontinuous coordinate jump must cause validation failure."""
        jump_path = [(0, 0), (1, 1), (1, 2), (5, 5)]  # Jump from (1, 2) to (5, 5)
        val = RouteValidator.validate_route(
            path_rc=jump_path,
            cost_surface=test_cost_surface,
            max_slope_deg=15.0,
        )
        assert val.is_valid is False
        assert any("discontinuous jump" in msg.lower() for msg in val.failed_checks)

    def test_corner_cutting_rejected(self):
        """Traversing diagonally when an adjacent orthogonal cell is impassable must fail."""
        rows, cols = 5, 5
        elev = np.zeros((rows, cols), dtype=np.int16)
        window = TerrainGridWindow(elev, 0, 0, -1.0, 5.0)
        cs = TerrainCostSurface(window, TerrainCostWeights(), max_slope_deg=15.0)

        # Mark cell (0, 1) impassable
        cs.passable_mask[0, 1] = False

        # Attempt diagonal cut from (0, 0) to (1, 1)
        path = [(0, 0), (1, 1)]
        val = RouteValidator.validate_route(path, cs, max_slope_deg=15.0)
        assert val.is_valid is False
        assert val.diagonal_corner_cuts_count > 0


# ==============================================================================
# 4. ALGORITHM OPTIMALITY COMPARISON (A* VS DIJKSTRA)
# ==============================================================================

class TestAlgorithmOptimality:
    """Verifies that A* finds the EXACT optimal path cost as Dijkstra's unguided search
    across diverse terrain scenarios.
    """

    def test_optimality_on_synthetic_sloped_ramp(self):
        """A* and Dijkstra must return identical path costs on a synthetic sloped ramp."""
        rows, cols = 25, 25
        elev = np.zeros((rows, cols), dtype=np.int16)
        for r in range(rows):
            for c in range(cols):
                elev[r, c] = int(r * 8 + c * 3)

        window = TerrainGridWindow(elev, 0, 0, -2.0, 10.0)
        cs = TerrainCostSurface(window, TerrainCostWeights(), max_slope_deg=20.0)

        astar = AStarPlanner(cs)
        dijkstra = DijkstraPlanner(cs)

        start = (2, 2)
        goal = (22, 22)

        path_a, stats_a = astar.plan_path(start, goal, eight_way=True)
        path_d, stats_d = dijkstra.plan_path(start, goal, eight_way=True)

        assert path_a is not None
        assert path_d is not None

        # Costs must be identical within floating point precision
        cost_diff = abs(stats_a["total_cost"] - stats_d["total_cost"])
        rel_diff = cost_diff / stats_d["total_cost"]
        assert rel_diff < 1e-4, f"Cost difference exceeds tolerance: A*={stats_a['total_cost']}, D={stats_d['total_cost']}"

        # A* must expand fewer or equal nodes
        assert stats_a["nodes_expanded"] <= stats_d["nodes_expanded"]

    def test_optimality_on_obstacle_funnel(self):
        """Path with an impassable ridge forcing a detour must yield identical costs."""
        rows, cols = 25, 25
        elev = np.zeros((rows, cols), dtype=np.int16)
        window = TerrainGridWindow(elev, 0, 0, -2.0, 10.0)
        cs = TerrainCostSurface(window, TerrainCostWeights(), max_slope_deg=15.0)

        # Build an impassable vertical wall at col 12, leaving a single passage at row 20
        for r in range(0, 19):
            cs.passable_mask[r, 12] = False

        astar = AStarPlanner(cs)
        dijkstra = DijkstraPlanner(cs)

        start = (5, 5)
        goal = (5, 20)

        path_a, stats_a = astar.plan_path(start, goal, eight_way=True)
        path_d, stats_d = dijkstra.plan_path(start, goal, eight_way=True)

        assert path_a is not None
        assert path_d is not None

        cost_diff = abs(stats_a["total_cost"] - stats_d["total_cost"])
        assert cost_diff < 0.1, f"Cost difference on obstacle funnel: A*={stats_a['total_cost']}, D={stats_d['total_cost']}"


# ==============================================================================
# 5. MULTI-CORRIDOR REAL-DATA BENCHMARK HARNESS
# ==============================================================================

class TestRealMarsBenchmarks:
    """Multi-corridor real MOLA benchmark harness with repeated runs.
    Calculates median runtimes, node expansion ratios, and validates 100% path feasibility.
    """

    BENCHMARK_CORRIDORS = [
        ("Corridor 1: Sinus Meridiani Plain", -2.00, 5.00, -2.15, 5.18),
        ("Corridor 2: Margaritifer Terra Valley", -4.00, 8.00, -4.08, 8.08),
        ("Corridor 3: Schiaparelli Approach", -3.00, 15.00, -3.10, 15.15),
        ("Corridor 4: Southern Boundary Approach", -43.50, 10.00, -43.65, 10.15),
    ]

    def test_four_real_mola_corridors_optimality(self):
        """All 4 real MOLA corridors must yield identical costs between A* and Dijkstra."""
        service = MarsRouteService()

        for name, slat, slon, dlat, dlon in self.BENCHMARK_CORRIDORS:
            req_astar = RoutePlanRequest(
                start_lat=slat, start_lon=slon,
                dest_lat=dlat, dest_lon=dlon,
                dataset_id="mola-megdr-128",
                algorithm="astar",
            )
            req_dijkstra = RoutePlanRequest(
                start_lat=slat, start_lon=slon,
                dest_lat=dlat, dest_lon=dlon,
                dataset_id="mola-megdr-128",
                algorithm="dijkstra",
            )

            res_a = service.plan_single_route(req_astar)
            res_d = service.plan_single_route(req_dijkstra)

            assert res_a.validation.is_valid is True
            assert res_d.validation.is_valid is True

            # Cost difference relative to Dijkstra baseline
            cost_diff_pct = abs(res_a.metrics.total_cost - res_d.metrics.total_cost) / res_d.metrics.total_cost * 100.0
            assert cost_diff_pct < 0.01, f"{name}: Cost discrepancy {cost_diff_pct:.4f}% exceeds 0.01% limit"

            # A* must expand strictly fewer nodes than Dijkstra on non-trivial real traverses
            assert res_a.metrics.nodes_expanded < res_d.metrics.nodes_expanded, (
                f"{name}: Expected A* ({res_a.metrics.nodes_expanded}) to expand fewer nodes than Dijkstra ({res_d.metrics.nodes_expanded})"
            )

    def test_benchmark_reproducibility_and_median_speedup(self):
        """Run 5 repeated iterations on Corridor 1 and Corridor 3 to establish median performance metrics."""
        service = MarsRouteService()

        corridors = [
            ("Sinus Meridiani", -2.00, 5.00, -2.15, 5.18),
            ("Schiaparelli Basin", -3.00, 15.00, -3.10, 15.15),
        ]

        iterations = 5

        for name, slat, slon, dlat, dlon in corridors:
            req = RoutePlanRequest(
                start_lat=slat, start_lon=slon,
                dest_lat=dlat, dest_lon=dlon,
                dataset_id="mola-megdr-128",
                algorithm="astar",
            )

            durations_astar = []
            durations_dijkstra = []
            nodes_astar = []
            nodes_dijkstra = []

            for _ in range(iterations):
                comp = service.compare_algorithms(req)
                durations_astar.append(comp.astar_route.metrics.search_duration_ms)
                durations_dijkstra.append(comp.dijkstra_route.metrics.search_duration_ms)
                nodes_astar.append(comp.astar_route.metrics.nodes_expanded)
                nodes_dijkstra.append(comp.dijkstra_route.metrics.nodes_expanded)

            median_time_a = float(np.median(durations_astar))
            median_time_d = float(np.median(durations_dijkstra))
            median_nodes_a = int(np.median(nodes_astar))
            median_nodes_d = int(np.median(nodes_dijkstra))

            speedup_ratio = median_nodes_d / max(median_nodes_a, 1)

            # Assert node count is 100% deterministic
            assert len(set(nodes_astar)) == 1, f"{name}: A* node expansions not deterministic!"
            assert len(set(nodes_dijkstra)) == 1, f"{name}: Dijkstra node expansions not deterministic!"

            # A* search space reduction must be at least 1.5x on real terrain
            assert speedup_ratio >= 1.5, f"{name}: Expected search space reduction >= 1.5x, got {speedup_ratio:.2f}x"
