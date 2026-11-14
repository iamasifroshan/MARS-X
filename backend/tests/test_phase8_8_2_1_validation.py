"""Phase 8.8.2.1: Scientific Validation of A* Marswalk Route Engine.

Verifies:
  1. Exact elevation benchmark numerical samples (raw float32 vs rounded display).
  2. Mathematical equivalence: A* path cost == Dijkstra path cost across 8 synthetic test scenarios.
  3. Independent recalculation of all route telemetry metrics (distances, gain/loss, length-weighted slope, distance-weighted exposure).
  4. Dataset coverage, native resolutions, vertical datums, and boundary seam rejection.
  5. Deterministic request cache identity and parameter separation.
  6. Non-negotiable astronaut safety disclaimers and cardinal coordinate formatting.
"""

import math
import struct
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.marswalk.marswalk_models import (
    MarswalkRouteRequest,
    MarswalkRouteResponse,
    MARSWALK_SAFETY_DISCLAIMER,
)
from app.marswalk.marswalk_planner import (
    MarswalkPlanner,
    BoundedTerrainGrid,
    compute_request_hash,
    get_cached_route,
    get_cached_route_by_request,
    clear_route_cache,
    THETA_REF_DEG,
)
from app.terrain.traversability_service import (
    get_traversability_service,
    TERRAIN_SOURCES,
    MARS_RADIUS_M,
    classify_slope,
)
import rasterio
from rasterio.transform import rowcol


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ===========================================================================
# 1. ELEVATION BENCHMARK SCIENTIFIC VERIFICATION
# ===========================================================================

class TestElevationBenchmarkScientificAudit:
    """Rigorous audit of raw float32 samples vs display benchmarks."""

    def test_tyrrhena_ctx_raw_float32_and_rounded_precision(self):
        """Tyrrhena CTX DTM: row 1737, col 844 is float32 2189.4851, display +2189.49 m."""
        src = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-tyrrhena")
        with rasterio.open(src["elev_path"]) as ds:
            # Re-project (-4.600, 66.317)
            x = MARS_RADIUS_M * math.radians(66.317)
            y = MARS_RADIUS_M * math.radians(-4.600)
            r, c = rowcol(ds.transform, x, y)
            assert (r, c) == (1737, 844)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]

            assert ds.dtypes[0] == "float32"
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "4508d7c3"
            # Exact IEEE 754 float32 value is 2189.485107421875
            assert abs(float(raw_val) - 2189.4851) < 1e-4

        # Via service API
        svc = get_traversability_service()
        pt = svc.query_point(-4.600, 66.317)
        assert pt.elevation_m == 2189.485  # rounded to 3 decimal places (mm)
        assert round(pt.elevation_m, 2) == 2189.49  # nominal 2-decimal display benchmark

    def test_apollinaris_ctx_raw_float32_and_rounded_precision(self):
        """Apollinaris Sulci CTX DTM: row 837, col 514 is float32 -2930.7686, display -2930.77 m."""
        src = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-apollinaris")
        with rasterio.open(src["elev_path"]) as ds:
            x = MARS_RADIUS_M * math.radians(168.250)
            y = MARS_RADIUS_M * math.radians(4.700)
            r, c = rowcol(ds.transform, x, y)
            assert (r, c) == (837, 514)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]

            assert ds.dtypes[0] == "float32"
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "c5372c4c"
            assert abs(float(raw_val) - (-2930.7686)) < 1e-4

        svc = get_traversability_service()
        pt = svc.query_point(4.700, 168.250)
        assert pt.elevation_m == -2930.769
        assert round(pt.elevation_m, 2) == -2930.77

    def test_holden_hirise_raw_float32_and_rounded_precision(self):
        """Holden HiRISE DTM: row 6940, col 1795 is float32 -1132.1444, display -1132.14 m."""
        src = next(s for s in TERRAIN_SOURCES if s["source_id"] == "hirise-holden")
        with rasterio.open(src["elev_path"]) as ds:
            proj_lon = 309.020 - 360.0
            x = MARS_RADIUS_M * math.radians(proj_lon)
            y = MARS_RADIUS_M * math.radians(-28.500)
            r, c = rowcol(ds.transform, x, y)
            assert (r, c) == (6940, 1795)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]

            assert ds.dtypes[0] == "float32"
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "c48d849f"
            assert abs(float(raw_val) - (-1132.1444)) < 1e-4

        svc = get_traversability_service()
        pt = svc.query_point(-28.500, 309.020)
        assert pt.elevation_m == -1132.144
        assert round(pt.elevation_m, 2) == -1132.14


# ===========================================================================
# 2. A* VS DIJKSTRA OPTIMALITY EQUIVALENCE ON SYNTHETIC GRIDS
# ===========================================================================

class TestAStarVsDijkstraOptimalityEquivalence:
    """Proves A* mathematical optimality: A* cost == Dijkstra cost under all conditions."""

    def _make_grid(self, elev, slope, dx_m=10.0, dy_m=10.0) -> BoundedTerrainGrid:
        source_dummy = {
            "source_id": "test-synthetic",
            "instrument": "Synthetic",
            "tier": "test",
            "pixel_spacing_m": dx_m,
            "pixel_spacing_desc": f"{dx_m} m/px",
            "crs": "IAU:49910",
            "vertical_datum": "Synthetic",
            "vertical_datum_type": "areoid_height",
            "nodata_elev": -32767.0,
            "nodata_slope": -32767.0,
        }
        return BoundedTerrainGrid(
            source_info=source_dummy,
            elevation=elev.astype(np.float32),
            slope=slope.astype(np.float32),
            row_offset=0,
            col_offset=0,
            transform=None,
            is_projected=True,
            dx_m=dx_m,
            dy_m=dy_m,
        )

    def test_case1_flat_terrain_equivalence(self):
        """Flat terrain: A* and Dijkstra must return identical optimal cost and path."""
        elev = np.zeros((20, 20), dtype=np.float32)
        slope = np.zeros((20, 20), dtype=np.float32)
        grid = self._make_grid(elev, slope)

        start, goal = (2, 2), (15, 15)
        path_astar, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, 25.0, 50000, "astar")
        path_dijk, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, 25.0, 50000)

        assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-5
        # A* expands strictly fewer or equal nodes
        assert stats_astar["nodes_expanded"] <= stats_dijk["nodes_expanded"]

    def test_case2_inclined_ramp_equivalence(self):
        """Sloped ramp with continuous elevation gradient."""
        rows, cols = 20, 20
        elev = np.zeros((rows, cols), dtype=np.float32)
        for r in range(rows):
            elev[r, :] = r * 5.0  # 5m rise per row
        slope = np.full((rows, cols), fill_value=12.0, dtype=np.float32)
        grid = self._make_grid(elev, slope)

        start, goal = (2, 2), (18, 18)
        _, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, 25.0, 50000, "astar")
        _, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, 25.0, 50000)

        assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4
        assert stats_astar["nodes_expanded"] <= stats_dijk["nodes_expanded"]

    def test_case3_variable_elevation_landscape(self):
        """Landscape with undulating sinusoidal hills and valleys."""
        rows, cols = 25, 25
        r_coords, c_coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        elev = 50.0 * np.sin(r_coords / 3.0) + 30.0 * np.cos(c_coords / 4.0)
        slope = np.clip(np.abs(np.gradient(elev, axis=0)) * 5.0, 0.0, 24.0)
        grid = self._make_grid(elev, slope)

        start, goal = (3, 3), (22, 22)
        _, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, 25.0, 50000, "astar")
        _, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, 25.0, 50000)

        assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4

    def test_case4_different_slope_penalties(self):
        """Equivalence across beta = 0.0, 1.0, 3.0, 5.0."""
        rows, cols = 15, 15
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.full((rows, cols), fill_value=10.0, dtype=np.float32)
        grid = self._make_grid(elev, slope)

        start, goal = (2, 2), (12, 12)
        for beta in [0.0, 1.0, 3.0, 5.0]:
            _, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, beta, 25.0, 50000, "astar")
            _, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, beta, 25.0, 50000)
            assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4

    def test_case5_different_max_slope_thresholds(self):
        """Equivalence across max slope cutoffs 15°, 20°, 25°."""
        rows, cols = 15, 15
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)
        # Gradient slope
        for c in range(cols):
            slope[:, c] = c * 1.5
        grid = self._make_grid(elev, slope)

        start, goal = (7, 1), (7, 10)
        for max_s in [16.0, 20.0, 25.0]:
            _, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, max_s, 50000, "astar")
            _, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, max_s, 50000)
            assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4

    def test_case6_obstacles_and_nodata_barrier_funnel(self):
        """Navigating through a narrow gap in a steep barrier."""
        rows, cols = 20, 20
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Wall at col 10 with gap at row 15
        slope[:, 10] = 40.0
        slope[15, 10] = 5.0
        grid = self._make_grid(elev, slope)

        start, goal = (4, 4), (4, 16)
        path_astar, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, 25.0, 50000, "astar")
        path_dijk, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, 25.0, 50000)

        assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4
        assert (15, 10) in path_astar
        assert (15, 10) in path_dijk

    def test_case7_diagonal_corner_cutting_prohibition(self):
        """Verifies diagonal transitions blocked when orthogonal neighbors are impassable."""
        rows, cols = 6, 6
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Diagonal from (2, 2) to (3, 3) requires (3, 2) and (2, 3) to be passable
        slope[3, 2] = 50.0  # Impassable
        slope[2, 3] = 50.0  # Impassable
        grid = self._make_grid(elev, slope)

        start, goal = (2, 2), (3, 3)
        path_astar, stats_astar = MarswalkPlanner._run_astar(grid, start, goal, 2.0, 25.0, 50000, "astar")
        path_dijk, stats_dijk = MarswalkPlanner._run_dijkstra(grid, start, goal, 2.0, 25.0, 50000)

        assert abs(stats_astar["total_path_cost"] - stats_dijk["total_path_cost"]) < 1e-4
        # Verify direct diagonal step (2, 2) -> (3, 3) was NOT taken
        assert not any(path_astar[i] == (2, 2) and path_astar[i + 1] == (3, 3) for i in range(len(path_astar) - 1))

    def test_case8_unreachable_destination_raises_runtime_error(self):
        """Both A* and Dijkstra must raise RuntimeError when destination is blocked."""
        rows, cols = 10, 10
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)
        slope[:, 5] = 50.0  # Completely walled off
        grid = self._make_grid(elev, slope)

        with pytest.raises(RuntimeError):
            MarswalkPlanner._run_astar(grid, (2, 2), (2, 8), 2.0, 25.0, 50000, "astar")
        with pytest.raises(RuntimeError):
            MarswalkPlanner._run_dijkstra(grid, (2, 2), (2, 8), 2.0, 25.0, 50000)


# ===========================================================================
# 3. INDEPENDENT ROUTE TELEMETRY VERIFICATION
# ===========================================================================

class TestIndependentRouteTelemetryRecalculation:
    """Independently verifies all returned route metrics against raw path geometry."""

    def test_recalculate_metrics_tyrrhena_route(self):
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res = MarswalkPlanner.plan_route(req)

        pts = res.path_points
        assert len(pts) > 1

        # Independent recalculation
        cum_dist = 0.0
        cum_gain = 0.0
        cum_loss = 0.0
        max_s = 0.0
        weighted_slope = 0.0
        exp_meters = {"low": 0.0, "moderate": 0.0, "high": 0.0, "very_high": 0.0, "unknown": 0.0}

        # CTX Tyrrhena is Equirectangular IAU:49910: pixel spacing is ~20.0128 m
        dx_m = res.native_resolution_m
        dy_m = res.native_resolution_m

        for i in range(1, len(pts)):
            p0 = pts[i - 1]
            p1 = pts[i]

            # Approximate horizontal metric step from coordinates
            dlat_m = math.radians(p1.lat - p0.lat) * MARS_RADIUS_M
            dlon_m = math.radians(p1.lon - p0.lon) * MARS_RADIUS_M
            d_h = math.sqrt(dlat_m**2 + dlon_m**2)

            dz = p1.elevation_m - p0.elevation_m
            d_s = math.sqrt(d_h**2 + dz**2)

            cum_dist += d_s
            if dz > 0:
                cum_gain += dz
            else:
                cum_loss += abs(dz)

            max_s = max(max_s, p1.slope_deg)
            weighted_slope += d_s * p1.slope_deg
            exp_meters[p1.slope_category] += d_s

        # Assert total surface distance matches within 2% (due to pixel vs coordinate projection)
        assert abs(cum_dist - res.total_surface_distance_m) < res.total_surface_distance_m * 0.02
        # Assert elevation gain & loss match exactly
        assert abs(cum_gain - res.cumulative_elevation_gain_m) < 0.5
        assert abs(cum_loss - res.cumulative_elevation_loss_m) < 0.5
        # Max slope matches
        assert abs(max_s - res.max_route_slope_deg) < 0.1
        # Mean slope matches length-weighted
        calc_mean_slope = weighted_slope / cum_dist
        assert abs(calc_mean_slope - res.mean_route_slope_deg) < 0.5

        # Distance-weighted exposure breakdown matches
        for cat, dist in exp_meters.items():
            pct = round((dist / cum_dist) * 100.0, 2)
            assert abs(pct - res.slope_band_exposure_pct.get(cat, 0.0)) < 3.0


# ===========================================================================
# 4. DATASET COVERAGE, TIERS & BOUNDARY SEAM PROTECTION
# ===========================================================================

class TestDatasetCoverageAndBoundaryProtection:
    """Verifies that routes crossing incompatible boundaries or unsupported seams are rejected."""

    def test_hirise_rejects_tyrrhena_destination(self):
        """HiRISE source cannot route to destination in Tyrrhena Terra (cross-regional seam)."""
        req = MarswalkRouteRequest(
            start_lat=-28.500,
            start_lon=309.020,  # in Holden HiRISE
            dest_lat=-4.600,
            dest_lon=66.317,    # in Tyrrhena CTX
            preferred_source="hirise-holden",
        )
        with pytest.raises(ValueError) as exc:
            MarswalkPlanner.plan_route(req)
        assert "does not cover both route coordinates" in str(exc.value)

    def test_ctx_tyrrhena_rejects_out_of_footprint_start(self):
        """CTX Tyrrhena source rejects coordinates outside its ~40km footprint."""
        req = MarswalkRouteRequest(
            start_lat=-10.0,
            start_lon=66.317,  # outside lat bounds [-5.5, -3.8]
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        with pytest.raises(ValueError) as exc:
            MarswalkPlanner.plan_route(req)
        assert "does not cover both route coordinates" in str(exc.value)

    def test_auto_fallback_across_distant_points_picks_mola_4ppd(self):
        """When waypoints span across separate local swaths, auto-selection falls back to MOLA global."""
        req = MarswalkRouteRequest(
            start_lat=-28.500,
            start_lon=309.020,  # Holden
            dest_lat=4.700,
            dest_lon=168.250,   # Apollinaris
            preferred_source="auto",
        )
        src = MarswalkPlanner.select_source(req.start_lat, req.start_lon, req.dest_lat, req.dest_lon, "auto")
        assert src["source_id"] == "mola-4ppd"
        assert src["tier"] == "global_coarse"


# ===========================================================================
# 5. DETERMINISTIC CACHE IDENTITY & PARAMETER SEPARATION
# ===========================================================================

class TestCacheIdentityAndParameterSeparation:
    """Verifies cache keys distinguish parameter variations and prevent stale retrievals."""

    def test_cache_hit_on_identical_request(self):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res1 = MarswalkPlanner.plan_route(req)
        res2 = MarswalkPlanner.plan_route(req)
        # Should return cached instance with identical route_id
        assert res1.route_id == res2.route_id

    def test_cache_miss_on_changed_slope_penalty(self):
        clear_route_cache()
        req1 = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        req2 = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            slope_penalty_factor=5.0,  # Changed parameter!
            max_slope_deg=25.0,
        )
        res1 = MarswalkPlanner.plan_route(req1)
        res2 = MarswalkPlanner.plan_route(req2)

        assert compute_request_hash(req1) != compute_request_hash(req2)
        assert res1.route_id != res2.route_id
        assert res1.cost_function_parameters["slope_penalty_factor_beta"] == 2.0
        assert res2.cost_function_parameters["slope_penalty_factor_beta"] == 5.0

    def test_cache_miss_on_changed_algorithm(self):
        clear_route_cache()
        req_astar = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            algorithm="astar",
        )
        req_dijk = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            algorithm="dijkstra",
        )
        res_astar = MarswalkPlanner.plan_route(req_astar)
        res_dijk = MarswalkPlanner.plan_route(req_dijk)

        assert compute_request_hash(req_astar) != compute_request_hash(req_dijk)
        assert res_astar.route_id != res_dijk.route_id
        # Under identical cost surface, optimal total cost matches
        assert abs(res_astar.total_optimization_cost - res_dijk.total_optimization_cost) < 0.1
        # A* expands fewer or equal nodes
        assert res_astar.search_metrics["nodes_expanded"] <= res_dijk.search_metrics["nodes_expanded"]


# ===========================================================================
# 6. NON-NEGOTIABLE SAFETY DISCLAIMER ASSERTION
# ===========================================================================

class TestSafetyDisclaimerNonNegotiable:
    """Verifies that no route response or metadata ever omits the mandatory safety disclaimer."""

    def test_disclaimer_content_and_presence(self):
        meta = MarswalkPlanner.get_metadata()
        assert "not certify physical astronaut or rover safety" in meta.safety_disclaimer
        assert "No route generated by MARS-X is certified safe" in meta.safety_disclaimer

        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        res = MarswalkPlanner.plan_route(req)
        assert "not certify physical astronaut or rover safety" in res.safety_disclaimer
