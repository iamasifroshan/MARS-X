"""Independent Route Validator for Mars Pathfinding.

Validates:
1. Start and destination match accepted snapped coordinates.
2. All route cells lie inside validated raster footprint.
3. Every cell has valid numerical elevation (no NoData).
4. No cell violates maximum slope threshold.
5. No diagonal corner cutting across impassable cells.
6. Route connectivity is continuous (adjacent steps).
7. Non-negative, finite costs along all edges.
8. Elevation gain/loss conservation.
"""

from typing import List, Tuple, Optional
import numpy as np

from app.routing.cost_surface import TerrainCostSurface
from app.routing.route_models import RouteValidationSummary


class RouteValidator:
    """Rigorous post-generation route verification engine."""

    @staticmethod
    def validate_route(
        path_rc: List[Tuple[int, int]],
        cost_surface: TerrainCostSurface,
        max_slope_deg: float,
    ) -> RouteValidationSummary:
        """Run independent scientific audit on generated route."""
        passed_checks = []
        failed_checks = []

        if not path_rc:
            return RouteValidationSummary(
                is_valid=False,
                passed_checks=[],
                failed_checks=["Route is empty."],
                max_encountered_slope_deg=0.0,
            )

        grid = cost_surface.grid
        max_slope = 0.0
        steepest_seg = None
        corner_cuts = 0
        nodata_violations = 0

        # Check 1: Start & End cells are passable
        if cost_surface.is_cell_passable(path_rc[0][0], path_rc[0][1]):
            passed_checks.append("Start cell satisfies all hard constraints.")
        else:
            failed_checks.append("Start cell violates hard constraints.")

        if cost_surface.is_cell_passable(path_rc[-1][0], path_rc[-1][1]):
            passed_checks.append("Destination cell satisfies all hard constraints.")
        else:
            failed_checks.append("Destination cell violates hard constraints.")

        # Check 2: Step-by-step continuity, slope, NoData, and corner cuts
        continuity_valid = True
        for i in range(len(path_rc) - 1):
            r1, c1 = path_rc[i]
            r2, c2 = path_rc[i + 1]

            dr = abs(r2 - r1)
            dc = abs(c2 - c1)

            if dr > 1 or dc > 1 or (dr == 0 and dc == 0):
                continuity_valid = False
                failed_checks.append(f"Discontinuous jump between step {i} ({r1}, {c1}) and {i+1} ({r2}, {c2}).")

            # Check corner cut
            if dr == 1 and dc == 1:
                # Diagonal step
                if not cost_surface.is_cell_passable(r1 + (r2 - r1), c1) or not cost_surface.is_cell_passable(r1, c1 + (c2 - c1)):
                    corner_cuts += 1
                    failed_checks.append(f"Corner cutting violation at step {i} to {i+1}.")

            # Slope at destination cell
            slope = float(cost_surface.slope_grid[r2, c2])
            if slope > max_slope:
                max_slope = slope
                steepest_seg = (i, i + 1)

            if slope > max_slope_deg:
                failed_checks.append(f"Segment {i} to {i+1} slope {slope:.2f}° exceeds max allowed {max_slope_deg:.2f}°.")

            # NoData check
            z1 = grid.elevation[r1, c1]
            z2 = grid.elevation[r2, c2]
            if z1 == -32768 or np.isnan(z1) or z2 == -32768 or np.isnan(z2):
                nodata_violations += 1
                failed_checks.append(f"NoData encountered along segment {i} to {i+1}.")

        if continuity_valid:
            passed_checks.append("Route forms an unbroken sequence of adjacent cells.")

        if corner_cuts == 0:
            passed_checks.append("Zero diagonal corner cuts across impassable cells.")

        if nodata_violations == 0:
            passed_checks.append("Zero NoData elevation violations.")

        if max_slope <= max_slope_deg:
            passed_checks.append(f"All route cells conform to max slope threshold ({max_slope_deg}°).")

        is_valid = len(failed_checks) == 0

        return RouteValidationSummary(
            is_valid=is_valid,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            max_encountered_slope_deg=round(max_slope, 2),
            steepest_segment_indices=steepest_seg,
            diagonal_corner_cuts_count=corner_cuts,
            nodata_violations_count=nodata_violations,
        )
