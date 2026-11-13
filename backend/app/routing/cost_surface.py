"""Terrain Cost Surface Engine for Mars Route Planning.

Calculates edge traversal costs between neighboring cells:
- Base physical metric distance L.
- Soft penalties: slope, roughness, relief, and discrete complexity.
- Impassable hard constraints: NoData, max slope threshold, exclusion zones, and diagonal corner-cutting.
"""

import math
import numpy as np
from typing import Tuple, Optional, List

from app.routing.grid_builder import TerrainGridWindow
from app.routing.route_models import TerrainCostWeights, ExclusionZone
from app.terrain.hazard_engine import TerrainHazardEngine, HazardThresholds


class TerrainCostSurface:
    """Computes edge traversal costs and evaluates hard constraints over a TerrainGridWindow."""

    def __init__(
        self,
        grid_window: TerrainGridWindow,
        weights: TerrainCostWeights,
        max_slope_deg: float = 15.0,
        exclusion_zones: Optional[List[ExclusionZone]] = None,
    ):
        self.grid = grid_window
        self.weights = weights
        self.max_slope_deg = max_slope_deg
        self.exclusion_zones = exclusion_zones or []

        # Precompute per-cell slope, roughness, and relief grids
        self._precompute_terrain_metrics()

    def _precompute_terrain_metrics(self):
        """Compute slope, roughness, and relief across the window using 3x3 kernels."""
        rows, cols = self.grid.rows, self.grid.cols
        self.slope_grid = np.zeros((rows, cols), dtype=np.float32)
        self.roughness_grid = np.zeros((rows, cols), dtype=np.float32)
        self.relief_grid = np.zeros((rows, cols), dtype=np.float32)
        self.passable_mask = np.ones((rows, cols), dtype=bool)

        elev = self.grid.elevation

        # Mark NoData as impassable
        nodata_mask = (elev == -32768) | np.isnan(elev)
        self.passable_mask[nodata_mask] = False

        # Mark exclusion zones as impassable
        for ez in self.exclusion_zones:
            for r in range(rows):
                for c in range(cols):
                    lat, lon = self.grid.row_col_to_lat_lon(r, c)
                    if ez.lat_min <= lat <= ez.lat_max and ez.lon_min <= lon <= ez.lon_max:
                        self.passable_mask[r, c] = False

        # Calculate metrics for each cell with 1-pixel interior boundary
        for r in range(rows):
            dy, dx = self.grid.get_cell_metric_spacing(r)
            r_start = max(0, r - 1)
            r_end = min(rows, r + 2)

            for c in range(cols):
                if not self.passable_mask[r, c]:
                    continue

                c_start = max(0, c - 1)
                c_end = min(cols, c + 2)
                sub = elev[r_start:r_end, c_start:c_end]

                # If full 3x3 window available without edge clipping
                if sub.shape == (3, 3):
                    s = TerrainHazardEngine.compute_slope_horn(sub, dy, dx)
                    rf = TerrainHazardEngine.compute_local_relief(sub)
                    rg = TerrainHazardEngine.compute_roughness(sub)

                    if s is not None:
                        self.slope_grid[r, c] = s
                        if s > self.max_slope_deg:
                            self.passable_mask[r, c] = False
                    else:
                        self.passable_mask[r, c] = False  # Neighbor had NoData

                    if rf is not None:
                        self.relief_grid[r, c] = rf
                    if rg is not None:
                        self.roughness_grid[r, c] = rg

    def is_cell_passable(self, r: int, c: int) -> bool:
        """Check if cell is within bounds and satisfies all hard constraints."""
        if not self.grid.is_in_bounds(r, c):
            return False
        return bool(self.passable_mask[r, c])

    def compute_edge_cost(
        self, r1: int, c1: int, r2: int, c2: int
    ) -> Optional[float]:
        """Compute traversal cost from cell (r1, c1) to cell (r2, c2).

        Returns None if hard constraints are violated (impassable edge).
        """
        # Hard constraint checks on endpoints
        if not self.is_cell_passable(r1, c1) or not self.is_cell_passable(r2, c2):
            return None

        dr = r2 - r1
        dc = c2 - c1

        # Prevent diagonal corner cutting: both orthogonal neighbors must be passable
        if dr != 0 and dc != 0:
            if not self.is_cell_passable(r1 + dr, c1) or not self.is_cell_passable(r1, c1 + dc):
                return None

        # Compute metric physical distance L
        dy, dx = self.grid.get_cell_metric_spacing(r1)
        step_y = dr * dy
        step_x = dc * dx
        dz = float(self.grid.elevation[r2, c2] - self.grid.elevation[r1, c1])
        # 3D surface physical distance
        L = math.sqrt(step_x**2 + step_y**2 + dz**2)

        # Soft penalties on destination cell
        slope = float(self.slope_grid[r2, c2])
        relief = float(self.relief_grid[r2, c2])
        roughness = float(self.roughness_grid[r2, c2])

        # Normalized penalty factors
        # Slope penalty: normalized against max_slope_deg
        f_s = min(slope / max(self.max_slope_deg, 1.0), 1.0)
        # Roughness penalty: normalized against 10m threshold
        f_r = min(roughness / 10.0, 1.0)
        # Local relief penalty: normalized against 40m threshold
        f_l = min(relief / 40.0, 1.0)
        # Discrete complexity penalty
        f_c = 1.0 if slope >= 15.0 or relief >= 30.0 or roughness >= 8.0 else 0.3 if slope >= 8.0 else 0.0

        # Cost formulation: C = L * (1 + ws*fs + wr*fr + wl*fl + wc*fc)
        penalty_multiplier = 1.0 + (
            self.weights.weight_slope * f_s
            + self.weights.weight_roughness * f_r
            + self.weights.weight_relief * f_l
            + self.weights.weight_complexity * f_c
        )

        return L * penalty_multiplier

    def get_neighbors(
        self, r: int, c: int, eight_way: bool = True
    ) -> List[Tuple[int, int]]:
        """Return valid passable neighbors for cell (r, c)."""
        if eight_way:
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        valid = []
        for dr, dc in deltas:
            nr = r + dr
            nc = c + dc
            if self.is_cell_passable(nr, nc):
                # Diagonal corner cutting check
                if dr != 0 and dc != 0:
                    if not self.is_cell_passable(r + dr, c) or not self.is_cell_passable(r, c + dc):
                        continue
                valid.append((nr, nc))
        return valid
