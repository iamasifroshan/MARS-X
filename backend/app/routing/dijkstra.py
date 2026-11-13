"""Dijkstra Pathfinding Algorithm for Mars Terrain Routing.

Computes the provably optimal baseline path on the identical terrain graph
and cost surface without heuristic guidance.
"""

import time
import heapq
from typing import Tuple, List, Optional, Dict, Set, Any

from app.routing.cost_surface import TerrainCostSurface


class DijkstraPlanner:
    """Dijkstra graph pathfinding engine on Mars terrain cost surfaces."""

    def __init__(self, cost_surface: TerrainCostSurface):
        self.cost_surface = cost_surface
        self.grid = cost_surface.grid

    def plan_path(
        self,
        start_rc: Tuple[int, int],
        goal_rc: Tuple[int, int],
        eight_way: bool = True,
        max_nodes_to_expand: int = 150000,
    ) -> Tuple[Optional[List[Tuple[int, int]]], Dict[str, Any]]:
        """Compute optimal terrain-constrained route using Dijkstra's algorithm.

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

        # Priority queue item: (cumulative_cost, (r, c))
        pq = [(0.0, start_rc)]

        dist: Dict[Tuple[int, int], float] = {start_rc: 0.0}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        visited: Set[Tuple[int, int]] = set()

        nodes_expanded = 0

        while pq:
            if nodes_expanded >= max_nodes_to_expand:
                raise TimeoutError(
                    f"Dijkstra search exceeded maximum node expansion limit ({max_nodes_to_expand} nodes). "
                    "Goal is either too distant or enclosed by impassable terrain."
                )

            current_cost, current = heapq.heappop(pq)

            if current in visited:
                continue

            visited.add(current)
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
                    "nodes_visited": len(dist),
                    "duration_ms": round(elapsed_ms, 2),
                    "total_cost": round(current_cost, 2),
                }
                return path, stats

            cr, cc = current
            for neighbor in self.cost_surface.get_neighbors(cr, cc, eight_way=eight_way):
                if neighbor in visited:
                    continue

                nr, nc = neighbor
                edge_cost = self.cost_surface.compute_edge_cost(cr, cc, nr, nc)
                if edge_cost is None:
                    continue

                new_cost = current_cost + edge_cost
                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    came_from[neighbor] = current
                    heapq.heappush(pq, (new_cost, neighbor))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return None, {
            "nodes_expanded": nodes_expanded,
            "nodes_visited": len(dist),
            "duration_ms": round(elapsed_ms, 2),
            "total_cost": float("inf"),
        }
