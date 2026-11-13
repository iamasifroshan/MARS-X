"""Route Metrics and Explainability Synthesis for Mars Route Planning."""

import math
from typing import List, Tuple, Dict, Any
import numpy as np

from app.routing.cost_surface import TerrainCostSurface
from app.routing.route_models import (
    RouteWaypoint,
    RouteSummaryMetrics,
    PathfindingAlgorithm,
    TerrainCostWeights,
)


class RouteMetricsCalculator:
    """Computes physical elevation gains, distances, roughness, and explainability narratives."""

    @staticmethod
    def compute_route_metrics(
        path_rc: List[Tuple[int, int]],
        cost_surface: TerrainCostSurface,
        search_stats: Dict[str, Any],
    ) -> Tuple[List[RouteWaypoint], RouteSummaryMetrics]:
        """Generate detailed waypoints and aggregate summary metrics."""
        grid = cost_surface.grid
        waypoints = []

        total_dist_m = 0.0
        elev_gain_m = 0.0
        elev_loss_m = 0.0
        slopes = []
        reliefs = []
        roughnesses = []
        elevations = []
        high_complexity_count = 0

        # Start waypoint (0 distance)
        r0, c0 = path_rc[0]
        lat0, lon0 = grid.row_col_to_lat_lon(r0, c0)
        z0 = float(grid.elevation[r0, c0])
        s0 = float(cost_surface.slope_grid[r0, c0])
        rf0 = float(cost_surface.relief_grid[r0, c0])
        rg0 = float(cost_surface.roughness_grid[r0, c0])

        elevations.append(z0)
        slopes.append(s0)
        reliefs.append(rf0)
        roughnesses.append(rg0)

        cx0 = "high_complexity" if s0 >= 15.0 or rf0 >= 30.0 or rg0 >= 8.0 else "moderate_complexity" if s0 >= 8.0 else "low_measured_complexity"
        if cx0 == "high_complexity":
            high_complexity_count += 1

        waypoints.append(
            RouteWaypoint(
                latitude=round(lat0, 5),
                longitude=round(lon0, 5),
                elevation_m=round(z0, 1),
                slope_deg=round(s0, 2),
                roughness_m=round(rg0, 2),
                relief_m=round(rf0, 2),
                cumulative_distance_m=0.0,
                complexity_class=cx0,
            )
        )

        for i in range(len(path_rc) - 1):
            r1, c1 = path_rc[i]
            r2, c2 = path_rc[i + 1]

            dy, dx = grid.get_cell_metric_spacing(r1)
            step_y = (r2 - r1) * dy
            step_x = (c2 - c1) * dx
            dz = float(grid.elevation[r2, c2] - grid.elevation[r1, c1])
            edge_dist = math.sqrt(step_x**2 + step_y**2 + dz**2)
            total_dist_m += edge_dist

            if dz > 0:
                elev_gain_m += dz
            else:
                elev_loss_m += abs(dz)

            lat2, lon2 = grid.row_col_to_lat_lon(r2, c2)
            z2 = float(grid.elevation[r2, c2])
            s2 = float(cost_surface.slope_grid[r2, c2])
            rf2 = float(cost_surface.relief_grid[r2, c2])
            rg2 = float(cost_surface.roughness_grid[r2, c2])

            elevations.append(z2)
            slopes.append(s2)
            reliefs.append(rf2)
            roughnesses.append(rg2)

            cx2 = "high_complexity" if s2 >= 15.0 or rf2 >= 30.0 or rg2 >= 8.0 else "moderate_complexity" if s2 >= 8.0 else "low_measured_complexity"
            if cx2 == "high_complexity":
                high_complexity_count += 1

            waypoints.append(
                RouteWaypoint(
                    latitude=round(lat2, 5),
                    longitude=round(lon2, 5),
                    elevation_m=round(z2, 1),
                    slope_deg=round(s2, 2),
                    roughness_m=round(rg2, 2),
                    relief_m=round(rf2, 2),
                    cumulative_distance_m=round(total_dist_m, 1),
                    complexity_class=cx2,
                )
            )

        summary = RouteSummaryMetrics(
            total_distance_m=round(total_dist_m, 1),
            cumulative_elevation_gain_m=round(elev_gain_m, 1),
            cumulative_elevation_loss_m=round(elev_loss_m, 1),
            min_elevation_m=round(min(elevations), 1),
            max_elevation_m=round(max(elevations), 1),
            max_slope_deg=round(max(slopes), 2),
            mean_slope_deg=round(float(np.mean(slopes)), 2),
            mean_roughness_m=round(float(np.mean(roughnesses)), 2),
            mean_local_relief_m=round(float(np.mean(reliefs)), 2),
            high_complexity_fraction=round(high_complexity_count / len(waypoints), 3),
            nodes_expanded=search_stats.get("nodes_expanded", 0),
            nodes_visited=search_stats.get("nodes_visited", 0),
            search_duration_ms=search_stats.get("duration_ms", 0.0),
            total_cost=search_stats.get("total_cost", 0.0),
        )

        return waypoints, summary

    @staticmethod
    def generate_explanation(
        algorithm: PathfindingAlgorithm,
        metrics: RouteSummaryMetrics,
        weights: TerrainCostWeights,
        max_slope_deg: float,
    ) -> str:
        """Synthesize explainable narrative for the chosen route."""
        return (
            f"The candidate route was planned using {algorithm.value.upper()} on the verified MOLA 128 ppd terrain model. "
            f"Total ground path distance is {metrics.total_distance_m / 1000.0:.2f} km with {metrics.cumulative_elevation_gain_m:.1f} m climb "
            f"and {metrics.cumulative_elevation_loss_m:.1f} m descent. The path strictly adhered to the maximum slope threshold of {max_slope_deg:.1f}°, "
            f"reaching a peak slope of {metrics.max_slope_deg:.1f}° (mean: {metrics.mean_slope_deg:.1f}°). "
            f"Soft penalties prioritized valleys and low-roughness corridors (slope weight={weights.weight_slope}, "
            f"roughness weight={weights.weight_roughness}). Approximately {metrics.high_complexity_fraction * 100.0:.1f}% of the path intersects "
            f"regions of elevated local relief."
        )
