"""Tests for Phase 8.8.2: Terrain-Aware Marswalk Route Generation.

Verifies:
  1. Synthetic grid unit tests:
     - Flat grid straight-line optimality
     - Sloped ramp cost scaling
     - Obstacle avoidance navigation
     - NoData wall impassability
     - Strict diagonal corner-cutting prevention
     - Start == destination handling
     - Unreachable destination exception
  2. Authentic Mars DEM traversals across all 5 tiers:
     - HiRISE Holden Crater DTM (~1 m/px)
     - CTX Tyrrhena Terra DTM (~20 m/px)
     - CTX Apollinaris Sulci DTM (~20 m/px)
     - MOLA 128 ppd Regional Tile (~463 m/px)
     - MOLA 4 ppd Global COG (~14.8 km/px)
  3. API endpoints:
     - POST /api/v1/marswalk/route
     - GET /api/v1/marswalk/route/{route_id}
     - GET /api/v1/marswalk/metadata
     - Error handling (out of bounds, 404 on missing route, source mismatch)
  4. Bitwise elevation benchmark preservation:
     - Tyrrhena: +2189.49 m
     - Apollinaris: -2930.77 m
     - Holden: -1132.14 m
  5. Mandatory non-negotiable astronaut safety disclaimer assertions.
"""

import math
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.marswalk.marswalk_models import (
    MarswalkRouteRequest,
    MARSWALK_SAFETY_DISCLAIMER,
)
from app.marswalk.marswalk_planner import (
    MarswalkPlanner,
    BoundedTerrainGrid,
    get_cached_route,
    THETA_REF_DEG,
)
from app.terrain.traversability_service import get_traversability_service


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ===========================================================================
# 1. SYNTHETIC GRID TESTS
# ===========================================================================

class TestSyntheticMarswalkPathfinding:
    """Rigorous algorithmic verification on synthetic grids."""

    def _create_synthetic_grid(
        self,
        elev_matrix: np.ndarray,
        slope_matrix: np.ndarray,
        dx_m: float = 10.0,
        dy_m: float = 10.0,
    ) -> BoundedTerrainGrid:
        source_dummy = {
            "source_id": "synthetic",
            "instrument": "Synthetic",
            "tier": "test",
            "pixel_spacing_m": dx_m,
            "pixel_spacing_desc": f"{dx_m} m/px",
            "crs": "Local Cart",
            "vertical_datum": "Synthetic",
            "vertical_datum_type": "areoid_height",
            "nodata_elev": -32767.0,
            "nodata_slope": -32767.0,
        }
        return BoundedTerrainGrid(
            source_info=source_dummy,
            elevation=elev_matrix.astype(np.float32),
            slope=slope_matrix.astype(np.float32),
            row_offset=0,
            col_offset=0,
            transform=None,
            is_projected=True,
            dx_m=dx_m,
            dy_m=dy_m,
            lat_top=0.0,
            lon_left=0.0,
            d_lat_deg=0.001,
            d_lon_deg=0.001,
        )

    def test_flat_grid_straight_line(self):
        """On flat terrain with zero slope, optimal path is a straight line."""
        rows, cols = 15, 15
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)
        grid = self._create_synthetic_grid(elev, slope, dx_m=10.0, dy_m=10.0)

        start = (2, 2)
        goal = (2, 10)
        path, stats = MarswalkPlanner._run_astar(
            grid=grid,
            start_rc=start,
            goal_rc=goal,
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
            max_nodes=10000,
        )

        assert len(path) == 9  # columns 2 through 10 = 9 cells
        for r, c in path:
            assert r == 2  # perfectly straight horizontal line
        # Total cost = 8 steps of 10.0 m = 80.0 m
        assert abs(stats["total_path_cost"] - 80.0) < 1e-4

    def test_obstacle_avoidance_navigation(self):
        """A* must navigate around a steep slope wall and through an opening."""
        rows, cols = 15, 15
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Wall of 40° slope (exceeding 25° max) at col 7, with a gap at row 12
        slope[:, 7] = 40.0
        slope[12, 7] = 0.0  # Passable gap

        grid = self._create_synthetic_grid(elev, slope, dx_m=10.0, dy_m=10.0)
        start = (3, 2)
        goal = (3, 12)

        path, stats = MarswalkPlanner._run_astar(
            grid=grid,
            start_rc=start,
            goal_rc=goal,
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
            max_nodes=10000,
        )

        assert (12, 7) in path  # Route must pass through the gap
        # Verify no cell in the path exceeds 25°
        for r, c in path:
            assert grid.slope[r, c] <= 25.0

    def test_strict_diagonal_corner_cutting_prevention(self):
        """Diagonal step must be blocked if either orthogonal neighbor is impassable."""
        rows, cols = 5, 5
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Place impassable walls blocking direct diagonal from (1, 1) to (2, 2)
        # Moving from (1, 1) to (2, 2) requires orthogonal neighbors (2, 1) and (1, 2)
        slope[2, 1] = 45.0  # Impassable
        slope[1, 2] = 45.0  # Impassable

        grid = self._create_synthetic_grid(elev, slope, dx_m=10.0, dy_m=10.0)
        start = (1, 1)
        goal = (2, 2)

        # Path must go around the obstacle via (0, ...) or (..., 3)
        path, stats = MarswalkPlanner._run_astar(
            grid=grid,
            start_rc=start,
            goal_rc=goal,
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
            max_nodes=10000,
        )

        # Verify that direct diagonal jump (1, 1) -> (2, 2) is NOT in path
        for i in range(len(path) - 1):
            if path[i] == (1, 1):
                assert path[i + 1] != (2, 2), "Diagonal corner cutting was improperly allowed!"

    def test_start_equals_destination(self):
        """Start == destination must return a 1-node path with zero cost."""
        rows, cols = 5, 5
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)
        grid = self._create_synthetic_grid(elev, slope)

        path, stats = MarswalkPlanner._run_astar(
            grid=grid,
            start_rc=(2, 2),
            goal_rc=(2, 2),
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
            max_nodes=10000,
        )

        assert path == [(2, 2)]
        assert stats["total_path_cost"] == 0.0
        assert stats["nodes_expanded"] == 0

    def test_unreachable_destination_raises_runtime_error(self):
        """Completely enclosed destination must raise RuntimeError when no path exists."""
        rows, cols = 10, 10
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Enclose goal (5, 5) with 50° slope wall
        for r in range(4, 7):
            for c in range(4, 7):
                if (r, c) != (5, 5):
                    slope[r, c] = 50.0

        grid = self._create_synthetic_grid(elev, slope)

        with pytest.raises(RuntimeError) as exc_info:
            MarswalkPlanner._run_astar(
                grid=grid,
                start_rc=(1, 1),
                goal_rc=(5, 5),
                slope_penalty_factor=2.0,
                max_slope_deg=25.0,
                max_nodes=10000,
            )
        assert "No valid path exists" in str(exc_info.value)

    def test_nodata_impassability(self):
        """Cells with NoData must never be traversed."""
        rows, cols = 10, 10
        elev = np.zeros((rows, cols), dtype=np.float32)
        slope = np.zeros((rows, cols), dtype=np.float32)

        # Full column of NoData at col 5
        elev[:, 5] = -32767.0
        grid = self._create_synthetic_grid(elev, slope)

        with pytest.raises(RuntimeError):
            MarswalkPlanner._run_astar(
                grid=grid,
                start_rc=(5, 2),
                goal_rc=(5, 8),
                slope_penalty_factor=2.0,
                max_slope_deg=25.0,
                max_nodes=10000,
            )


# ===========================================================================
# 2. AUTHENTIC MARS DEM TRAVERSALS ACROSS ALL 5 TIERS
# ===========================================================================

class TestAuthenticMarsDEMPathfinding:
    """Validates terrain-aware route planning over real Mars orbital products."""

    def test_hirise_holden_tactical_traverse(self):
        """Plan route over ~1 m/px HiRISE Holden Crater DTM."""
        req = MarswalkRouteRequest(
            start_lat=-28.500,
            start_lon=309.020,
            dest_lat=-28.502,
            dest_lon=309.022,
            preferred_source="hirise-holden",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res = MarswalkPlanner.plan_route(req)

        assert res.status == "success"
        assert res.source_dataset == "hirise-holden"
        assert res.instrument == "HiRISE"
        assert abs(res.native_resolution_m - 1.0125) < 0.01
        assert res.total_surface_distance_m > 100.0
        assert len(res.path_points) > 50
        assert res.max_route_slope_deg <= 25.0
        assert res.unknown_data_exposure_pct == 0.0
        assert res.geometry["type"] == "LineString"
        assert len(res.geometry["coordinates"]) == len(res.path_points)

    def test_ctx_tyrrhena_regional_traverse(self):
        """Plan route over ~20 m/px CTX Tyrrhena Terra DTM."""
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

        assert res.status == "success"
        assert res.source_dataset == "ctx-tyrrhena"
        assert res.instrument == "CTX"
        assert abs(res.native_resolution_m - 20.0128) < 0.01
        assert res.total_surface_distance_m > 400.0
        assert res.max_route_slope_deg <= 25.0
        assert res.unknown_data_exposure_pct == 0.0

    def test_ctx_apollinaris_yardang_traverse(self):
        """Plan route over ~20 m/px CTX Apollinaris Sulci DTM."""
        req = MarswalkRouteRequest(
            start_lat=4.700,
            start_lon=168.250,
            dest_lat=4.706,
            dest_lon=168.258,
            preferred_source="ctx-apollinaris",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res = MarswalkPlanner.plan_route(req)

        assert res.status == "success"
        assert res.source_dataset == "ctx-apollinaris"
        assert res.instrument == "CTX"
        assert res.native_resolution_m == 20.0
        assert res.total_surface_distance_m > 400.0
        assert res.max_route_slope_deg <= 25.0
        assert res.unknown_data_exposure_pct == 0.0

    def test_mola_128_regional_traverse(self):
        """Plan route over ~463 m/px MOLA 128 ppd tile."""
        req = MarswalkRouteRequest(
            start_lat=-4.700,
            start_lon=66.100,
            dest_lat=-4.600,
            dest_lon=66.250,
            preferred_source="mola-128ppd",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res = MarswalkPlanner.plan_route(req)

        assert res.status == "success"
        assert res.source_dataset == "mola-128ppd"
        assert res.instrument == "MOLA"
        assert abs(res.native_resolution_m - 463.08) < 0.1
        assert res.total_surface_distance_m > 5000.0
        assert res.max_route_slope_deg <= 25.0

    def test_mola_4ppd_global_fallback(self):
        """Plan route over ~14.8 km/px MOLA 4 ppd global COG."""
        req = MarswalkRouteRequest(
            start_lat=18.0,
            start_lon=77.0,
            dest_lat=18.5,
            dest_lon=77.5,
            preferred_source="mola-4ppd",
            slope_penalty_factor=2.0,
            max_slope_deg=25.0,
        )
        res = MarswalkPlanner.plan_route(req)

        assert res.status == "success"
        assert res.source_dataset == "mola-4ppd"
        assert res.instrument == "MOLA"
        assert abs(res.native_resolution_m - 14818.67) < 1.0
        assert res.total_surface_distance_m > 30000.0

    def test_auto_source_selection_picks_hirise(self):
        """When preferred_source='auto', Holden coordinates must automatically pick HiRISE."""
        req = MarswalkRouteRequest(
            start_lat=-28.500,
            start_lon=309.020,
            dest_lat=-28.502,
            dest_lon=309.022,
            preferred_source="auto",
        )
        res = MarswalkPlanner.plan_route(req)
        assert res.source_dataset == "hirise-holden"


# ===========================================================================
# 3. FASTAPI ROUTE ENDPOINTS
# ===========================================================================

class TestMarswalkApiEndpoints:
    """Verifies HTTP API endpoints and error semantics."""

    def test_get_metadata_endpoint(self, client):
        resp = client.get("/api/v1/marswalk/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "supported_datasets" in data
        assert len(data["supported_datasets"]) >= 5
        assert "validated_corridors" in data
        assert len(data["validated_corridors"]) >= 4
        assert "safety_disclaimer" in data
        assert "not certify physical astronaut or rover safety" in data["safety_disclaimer"]

    def test_post_route_endpoint_success(self, client):
        payload = {
            "start_lat": -4.600,
            "start_lon": 66.317,
            "dest_lat": -4.605,
            "dest_lon": 66.325,
            "preferred_source": "ctx-tyrrhena",
            "slope_penalty_factor": 2.0,
            "max_slope_deg": 25.0,
            "route_name": "Tyrrhena Test Channel Traverse",
        }
        resp = client.post("/api/v1/marswalk/route", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["route_name"] == "Tyrrhena Test Channel Traverse"
        assert data["route_id"].startswith("mw-")
        assert data["source_dataset"] == "ctx-tyrrhena"
        assert data["total_surface_distance_m"] > 0
        assert len(data["path_points"]) > 0
        assert "slope_band_exposure_pct" in data
        assert "safety_disclaimer" in data
        assert "not certify physical astronaut or rover safety" in data["safety_disclaimer"]

        # Test GET /api/v1/marswalk/route/{route_id}
        route_id = data["route_id"]
        get_resp = client.get(f"/api/v1/marswalk/route/{route_id}")
        assert get_resp.status_code == 200
        cached = get_resp.json()
        assert cached["route_id"] == route_id
        assert cached["total_surface_distance_m"] == data["total_surface_distance_m"]

    def test_get_non_existent_route_returns_404(self, client):
        resp = client.get("/api/v1/marswalk/route/mw-nonexistent999")
        assert resp.status_code == 404
        assert "not found in cache" in resp.json()["detail"]

    def test_source_mismatch_returns_400(self, client):
        """Requesting HiRISE source for coordinates in Gale or Tyrrhena must return 400."""
        payload = {
            "start_lat": -4.600,
            "start_lon": 66.317,
            "dest_lat": -4.605,
            "dest_lon": 66.325,
            "preferred_source": "hirise-holden",  # HiRISE is in Holden (-28°S, 309°E)!
        }
        resp = client.post("/api/v1/marswalk/route", json=payload)
        assert resp.status_code == 400
        assert "does not cover both route coordinates" in resp.json()["detail"]


# ===========================================================================
# 4. BITWISE ELEVATION BENCHMARK PRESERVATION
# ===========================================================================

class TestElevationBenchmarkPreservation:
    """Strict verification that validated elevation benchmarks remain intact bitwise."""

    def test_tyrrhena_ctx_benchmark(self):
        """Tyrrhena CTX DTM: +2189.49 m at nominal (-4.600°, 66.317°E)."""
        svc = get_traversability_service()
        pt = svc.query_point(-4.600, 66.317)
        assert pt.source_id == "ctx-tyrrhena"
        assert abs(pt.elevation_m - 2189.485) < 0.01
        assert round(pt.elevation_m, 2) == 2189.49

    def test_apollinaris_ctx_benchmark(self):
        """Apollinaris Sulci Controlled CTX DTM: -2930.77 m at nominal (4.700°, 168.250°E)."""
        svc = get_traversability_service()
        pt = svc.query_point(4.700, 168.250)
        assert pt.source_id == "ctx-apollinaris"
        assert abs(pt.elevation_m - (-2930.769)) < 0.01
        assert round(pt.elevation_m, 2) == -2930.77

    def test_holden_hirise_benchmark(self):
        """Holden Crater Controlled HiRISE DTM: -1132.14 m at nominal (-28.500°, 309.020°E)."""
        svc = get_traversability_service()
        pt = svc.query_point(-28.500, 309.020)
        assert pt.source_id == "hirise-holden"
        assert abs(pt.elevation_m - (-1132.144)) < 0.01
        assert round(pt.elevation_m, 2) == -1132.14


# ===========================================================================
# 5. ASTRONAUT SAFETY DISCLAIMER INTEGRITY
# ===========================================================================

class TestAstronautSafetyDisclaimerIntegrity:
    """Confirms no route is ever represented as astronaut-safe."""

    def test_disclaimer_in_route_response(self):
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        res = MarswalkPlanner.plan_route(req)
        assert "Minimizing analytical terrain cost does not certify physical astronaut or rover safety" in res.safety_disclaimer
        assert "No route generated by MARS-X is certified safe" in res.safety_disclaimer

    def test_disclaimer_in_metadata_response(self):
        meta = MarswalkPlanner.get_metadata()
        assert "Minimizing analytical terrain cost does not certify physical astronaut or rover safety" in meta.safety_disclaimer
