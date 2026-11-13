"""A* Pathfinding Algorithm for Mars Terrain-Constrained Routing.

Uses an admissible and consistent Euclidean lower-bound heuristic scaled to
physical Martian metres, guaranteeing optimal path costs under the non-negative
cost model C >= L.
"""

import time
import math
import heapq
from typing import Tuple, List, Optional, Dict, Set, Any

from app.geospatial import MARS_EQUATORIAL_RADIUS_M
from app.routing.cost_surface import TerrainCostSurface


class AStarPlanner:
    """A* graph pathfinding engine on Mars terrain cost surfaces."""

    def __init__(self, cost_surface: TerrainCostSurface):
        self.cost_surface = cost_surface
        self.grid = cost_surface.grid

    def heuristic(self, r: int, c: int, goal_r: int, goal_c: int) -> float:
        """Admissible and consistent lower-bound heuristic on Mars sphere.

        Computes the great-circle geodesic surface distance D_gc combined with
        vertical differential delta_z via Minkowski's 3D lower bound:
            h(u, G) = alpha * sqrt(D_gc(u, G)^2 + (z_G - z_u)^2)
        where alpha = 0.999 is a safety scaling factor that strictly guarantees
        consistency (h(u) <= c(u, v) + h(v)) across latitude-dependent metric grid
        spacings and floating-point discretization while maintaining 99.9% tightness.
        At goal (r == goal_r and c == goal_c), h is exactly 0.0.
        """
        if r == goal_r and c == goal_c:
            return 0.0

        lat_u = self.grid.row_lats_rad[r]
        lon_u = self.grid.col_lons_rad[c]
        cos_lat_u = self.grid.row_cos_lat[r]

        lat_g = self.grid.row_lats_rad[goal_r]
        lon_g = self.grid.col_lons_rad[goal_c]
        cos_lat_g = self.grid.row_cos_lat[goal_r]

        dlat = lat_g - lat_u
        dlon = lon_g - lon_u
        a = (
            math.sin(dlat * 0.5) ** 2
            + cos_lat_u * cos_lat_g * (math.sin(dlon * 0.5) ** 2)
        )
        d_gc = 2.0 * MARS_EQUATORIAL_RADIUS_M * math.asin(min(1.0, math.sqrt(max(0.0, a))))
        dz = float(self.grid.elevation[goal_r, goal_c] - self.grid.elevation[r, c])
        return 0.999 * math.sqrt(d_gc * d_gc + dz * dz)

    def plan_path(
        self,
        start_rc: Tuple[int, int],
        goal_rc: Tuple[int, int],
        eight_way: bool = True,
        max_nodes_to_expand: int = 150000,
    ) -> Tuple[Optional[List[Tuple[int, int]]], Dict[str, Any]]:
        """Compute optimal terrain-constrained route using A* search.

        Returns: (path_cells, search_stats)
        """
        start_time = time.perf_counter()

        start_r, start_c = start_rc
        goal_r, goal_c = goal_rc

        if not self.cost_surface.is_cell_passable(start_r, start_c):
            raise ValueError(f"Start cell ({start_r}, {start_c}) violates hard terrain constraints (slope/NoData).")
        if not self.cost_surface.is_cell_passable(goal_r, goal_c):
            raise ValueError(f"Goal cell ({goal_r}, {goal_c}) violates hard terrain constraints (slope/NoData).")

        if start_rc == goal_rc:
            return [start_rc], {
                "nodes_expanded": 0,
                "nodes_visited": 1,
                "duration_ms": 0.0,
                "total_cost": 0.0,
            }

        # Priority queue item: (f_score, g_score, (r, c))
        open_set = []
        h_start = self.heuristic(start_r, start_c, goal_r, goal_c)
        heapq.heappush(open_set, (h_start, 0.0, start_rc))

        g_score: Dict[Tuple[int, int], float] = {start_rc: 0.0}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_set: Set[Tuple[int, int]] = set()

        nodes_expanded = 0

        while open_set:
            if nodes_expanded >= max_nodes_to_expand:
                raise TimeoutError(
                    f"A* search exceeded maximum node expansion limit ({max_nodes_to_expand} nodes). "
                    "Goal is either too distant or enclosed by impassable terrain."
                )

            _, current_g, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            closed_set.add(current)
            nodes_expanded += 1

            if current == goal_rc:
                # Reconstruct path
                path = []
                curr = goal_rc
                while curr in came_from:
                    path.append(curr)
                    curr = came_from[curr]
                path.append(start_rc)
                path.reverse()

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                stats = {
                    "nodes_expanded": nodes_expanded,
                    "nodes_visited": len(g_score),
                    "duration_ms": round(elapsed_ms, 2),
                    "total_cost": round(current_g, 2),
                }
                return path, stats

            cr, cc = current
            for neighbor in self.cost_surface.get_neighbors(cr, cc, eight_way=eight_way):
                if neighbor in closed_set:
                    continue

                nr, nc = neighbor
                edge_cost = self.cost_surface.compute_edge_cost(cr, cc, nr, nc)
                if edge_cost is None:
                    continue

                tentative_g = current_g + edge_cost
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self.heuristic(nr, nc, goal_r, goal_c)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return None, {
            "nodes_expanded": nodes_expanded,
            "nodes_visited": len(g_score),
            "duration_ms": round(elapsed_ms, 2),
            "total_cost": float("inf"),
        }
