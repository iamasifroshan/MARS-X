"""High-Level Route Planning Service for Marswalk Traverses.

Coordinates grid extraction, cost surface evaluation, algorithm execution (A* and Dijkstra),
validation, metrics calculation, and algorithm comparison.
"""

import uuid
from typing import Tuple, Dict, Any, Optional

from app.routing.route_models import (
    RoutePlanRequest,
    RoutePlanResponse,
    RouteComparisonResponse,
    PathfindingAlgorithm,
    NeighborConnectivity,
)
from app.routing.grid_builder import (
    TerrainGridBuilder,
    MOLA_128_CHECKSUM,
    MOLA_128_PIXEL_DEG,
    MOLA_128_LAT_MIN,
    MOLA_128_LAT_MAX,
    MOLA_128_LON_MIN,
    MOLA_128_LON_MAX,
)
from app.routing.cost_surface import TerrainCostSurface
from app.routing.astar import AStarPlanner
from app.routing.dijkstra import DijkstraPlanner
from app.routing.route_validator import RouteValidator
from app.routing.route_metrics import RouteMetricsCalculator


class MarsRouteService:
    """Core application service orchestrating Mars terrain pathfinding."""

    def __init__(self, raw_mola_path: Optional[str] = None):
        self.builder = TerrainGridBuilder(raw_mola_path)

    def plan_single_route(self, request: RoutePlanRequest) -> RoutePlanResponse:
        """Execute single route planning using requested algorithm."""
        # Check footprint
        if not self.builder.is_coordinate_in_footprint(request.start_lat, request.start_lon):
            raise ValueError(
                f"Start coordinate ({request.start_lat:.4f}°N, {request.start_lon:.4f}°E) is outside the "
                f"validated MOLA 128 planning footprint (Lat [{MOLA_128_LAT_MIN}°, {MOLA_128_LAT_MAX}°], "
                f"Lon [{MOLA_128_LON_MIN}°, {MOLA_128_LON_MAX}°E])."
            )
        if not self.builder.is_coordinate_in_footprint(request.dest_lat, request.dest_lon):
            raise ValueError(
                f"Destination coordinate ({request.dest_lat:.4f}°N, {request.dest_lon:.4f}°E) is outside the "
                f"validated MOLA 128 planning footprint (Lat [{MOLA_128_LAT_MIN}°, {MOLA_128_LAT_MAX}°], "
                f"Lon [{MOLA_128_LON_MIN}°, {MOLA_128_LON_MAX}°E])."
            )

        # Snap coordinates
        snapped_start_lat, snapped_start_lon, snap_dist_start, _, _ = self.builder.snap_coordinate(
            request.start_lat, request.start_lon, request.max_snapping_distance_m
        )
        snapped_dest_lat, snapped_dest_lon, snap_dist_dest, _, _ = self.builder.snap_coordinate(
            request.dest_lat, request.dest_lon, request.max_snapping_distance_m
        )

        # Extract local window around corridor
        grid_window, start_rc, dest_rc = self.builder.extract_bounded_window(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            dest_lat=request.dest_lat,
            dest_lon=request.dest_lon,
            margin_pixels=30,
            max_window_pixels=600,
        )

        # Build cost surface
        cost_surface = TerrainCostSurface(
            grid_window=grid_window,
            weights=request.cost_weights,
            max_slope_deg=request.max_slope_deg,
            exclusion_zones=request.exclusion_zones,
        )

        eight_way = (request.connectivity == NeighborConnectivity.EIGHT_WAY)

        # Run selected planner
        if request.algorithm == PathfindingAlgorithm.ASTAR:
            planner = AStarPlanner(cost_surface)
            path_rc, stats = planner.plan_path(
                start_rc=start_rc,
                goal_rc=dest_rc,
                eight_way=eight_way,
                max_nodes_to_expand=request.max_search_nodes,
            )
        else:
            planner = DijkstraPlanner(cost_surface)
            path_rc, stats = planner.plan_path(
                start_rc=start_rc,
                goal_rc=dest_rc,
                eight_way=eight_way,
                max_nodes_to_expand=request.max_search_nodes,
            )

        if not path_rc:
            raise ValueError(
                "No traversable terrain corridor found between start and destination. "
                "The destination is either completely blocked by steep slopes (> max_slope_deg) "
                "or search resource limits were reached."
            )

        # Validate
        validation_res = RouteValidator.validate_route(
            path_rc=path_rc,
            cost_surface=cost_surface,
            max_slope_deg=request.max_slope_deg,
        )

        if not validation_res.is_valid:
            raise ValueError(
                f"Generated route failed independent scientific verification: {validation_res.failed_checks[0]}"
            )

        # Compute metrics & waypoints
        waypoints, metrics = RouteMetricsCalculator.compute_route_metrics(
            path_rc=path_rc,
            cost_surface=cost_surface,
            search_stats=stats,
        )

        explanation = RouteMetricsCalculator.generate_explanation(
            algorithm=request.algorithm,
            metrics=metrics,
            weights=request.cost_weights,
            max_slope_deg=request.max_slope_deg,
        )

        return RoutePlanResponse(
            route_id=str(uuid.uuid4())[:8],
            algorithm=request.algorithm,
            requested_start=(request.start_lat, request.start_lon),
            requested_dest=(request.dest_lat, request.dest_lon),
            snapped_start=(snapped_start_lat, snapped_start_lon),
            snapped_dest=(snapped_dest_lat, snapped_dest_lon),
            snapping_distance_start_m=round(snap_dist_start, 1),
            snapping_distance_dest_m=round(snap_dist_dest, 1),
            waypoints=waypoints,
            metrics=metrics,
            validation=validation_res,
            dataset_id=request.dataset_id,
            dataset_checksum=MOLA_128_CHECKSUM,
            native_resolution_m=463.08,
            planning_grid_spacing_m=463.08,
            cost_weights=request.cost_weights,
            max_slope_threshold_deg=request.max_slope_deg,
            explanation=explanation,
        )

    def compare_algorithms(self, request: RoutePlanRequest) -> RouteComparisonResponse:
        """Run both A* and Dijkstra on identical mission parameters and compare metrics."""
        req_astar = request.model_copy(update={"algorithm": PathfindingAlgorithm.ASTAR})
        req_dijkstra = request.model_copy(update={"algorithm": PathfindingAlgorithm.DIJKSTRA})

        res_astar = self.plan_single_route(req_astar)
        res_dijkstra = self.plan_single_route(req_dijkstra)

        cost_diff = abs(res_astar.metrics.total_cost - res_dijkstra.metrics.total_cost)
        cost_diff_pct = (cost_diff / max(res_dijkstra.metrics.total_cost, 1e-6)) * 100.0
        dist_diff = abs(res_astar.metrics.total_distance_m - res_dijkstra.metrics.total_distance_m)

        speedup = (
            res_dijkstra.metrics.search_duration_ms / max(res_astar.metrics.search_duration_ms, 0.01)
            if res_astar.metrics.search_duration_ms > 0 else 1.0
        )
        expanded_ratio = (
            res_dijkstra.metrics.nodes_expanded / max(res_astar.metrics.nodes_expanded, 1)
        )

        # Check if geometry coordinates are identical
        astar_pts = [(w.latitude, w.longitude) for w in res_astar.waypoints]
        dijk_pts = [(w.latitude, w.longitude) for w in res_dijkstra.waypoints]
        geometries_identical = (astar_pts == dijk_pts)

        synthesis = (
            f"A* and Dijkstra returned path costs within {cost_diff_pct:.4f}% of each other. "
            f"A* expanded {res_astar.metrics.nodes_expanded} nodes vs Dijkstra's {res_dijkstra.metrics.nodes_expanded} nodes "
            f"({expanded_ratio:.1f}x reduction in search space). Both paths satisfy all hard slope constraints."
        )

        return RouteComparisonResponse(
            request=request,
            astar_route=res_astar,
            dijkstra_route=res_dijkstra,
            cost_difference=round(cost_diff, 2),
            cost_difference_pct=round(cost_diff_pct, 4),
            distance_difference_m=round(dist_diff, 1),
            runtime_speedup_factor=round(speedup, 2),
            nodes_expanded_ratio=round(expanded_ratio, 2),
            path_geometries_identical=geometries_identical,
            scientific_synthesis=synthesis,
        )
