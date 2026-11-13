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
from app.terrain.multi_resolution import MultiResolutionTerrainCatalog
from app.terrain.inventory import Mola128InventoryService


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
            expected_start_rc=start_rc,
            expected_dest_rc=dest_rc,
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

    def check_data_availability(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
    ) -> Dict[str, Any]:
        """Check availability of multi-resolution elevation datasets for a candidate route area."""
        if min_lat > max_lat:
            raise ValueError(f"min_lat ({min_lat}) cannot be greater than max_lat ({max_lat})")
        if min_lon > max_lon:
            raise ValueError(f"min_lon ({min_lon}) cannot be greater than max_lon ({max_lon})")

        # Query multi-resolution catalog
        intersecting = MultiResolutionTerrainCatalog.find_intersecting_dtms_bbox(
            min_lat, min_lon, max_lat, max_lon
        )

        # Check local files and availability
        inventory = Mola128InventoryService().get_inventory_report()
        downloaded_mola_tiles = [t.tile_id for t in inventory.tiles if t.is_downloaded]

        # Check if the region is covered by our active builder footprint
        in_active_mola_footprint = (
            min_lat >= MOLA_128_LAT_MIN
            and max_lat <= MOLA_128_LAT_MAX
            and min_lon >= MOLA_128_LON_MIN
            and max_lon <= MOLA_128_LON_MAX
        )

        # Check intersection with other downloaded MOLA tiles
        covered_mola_tiles = []
        for t in inventory.tiles:
            if t.is_downloaded:
                # Check overlap
                lat_overlap = not (max_lat < t.lat_min or min_lat > t.lat_max)
                lon_overlap = not (max_lon < t.lon_min or min_lon > t.lon_max)
                if lat_overlap and lon_overlap:
                    covered_mola_tiles.append(t.tile_id)

        # Check local CTX DTM availability
        ctx_available = False
        ctx_product_id = "ctx-dtm-p21-009323"
        ctx_prof = MultiResolutionTerrainCatalog.get_product(ctx_product_id)
        if ctx_prof and ctx_prof.status == "analysis_ready":
            lat_overlap = not (max_lat < ctx_prof.lat_min or min_lat > ctx_prof.lat_max)
            lon_overlap = not (max_lon < ctx_prof.lon_min or min_lon > ctx_prof.lon_max)
            if lat_overlap and lon_overlap:
                ctx_available = True

        available_tiers = ["global_coarse"]  # MOLA 4 ppd is always available
        if covered_mola_tiles:
            available_tiers.append("global_base")
        if ctx_available:
            available_tiers.append("regional")

        highest_res_m = 14800.0  # MOLA 4 default
        recommended_product = "mola-megdr-4"
        if covered_mola_tiles:
            highest_res_m = 463.08
            recommended_product = "mola-megdr-128"
        if ctx_available:
            highest_res_m = 20.0
            recommended_product = ctx_product_id

        routing_eligible = in_active_mola_footprint

        notes = []
        if not routing_eligible:
            if covered_mola_tiles:
                notes.append(
                    f"Region intersects downloaded MOLA tile(s) {covered_mola_tiles}, but active single-tile engine is loaded for megt00n000hb."
                )
            else:
                notes.append(
                    f"Region is outside currently downloaded MOLA 128 regional tiles (acquired: {downloaded_mola_tiles})."
                )
        else:
            notes.append(
                "Region is fully inside the active validated MOLA 128 ppd footprint; A* and Dijkstra pathfinding are fully eligible."
            )

        if ctx_available:
            notes.append(
                "High-resolution 20 m/px USGS CTX numerical DTM is available for micro-terrain hazard inspection."
            )

        return {
            "bounding_box": {
                "min_lat": min_lat,
                "min_lon": min_lon,
                "max_lat": max_lat,
                "max_lon": max_lon,
            },
            "routing_eligible": routing_eligible,
            "available_tiers": available_tiers,
            "intersecting_products_count": len(intersecting),
            "intersecting_products": [
                {
                    "product_id": p.product_id,
                    "instrument": p.instrument,
                    "tier": p.tier,
                    "pixel_spacing_m": p.pixel_spacing_m,
                    "vertical_datum": p.vertical_datum,
                    "status": p.status,
                }
                for p in intersecting
            ],
            "highest_available_resolution_m": highest_res_m,
            "recommended_product": recommended_product,
            "downloaded_mola_tiles": downloaded_mola_tiles,
            "supported_algorithms": ["astar", "dijkstra"] if routing_eligible else [],
            "scientific_notes": notes,
        }

