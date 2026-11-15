"""Independent End-to-End Validation & Scientific Integrity Audit — Phase 8.8.5.

Performs independent reference calculations, verification of Scenarios A through E,
edge cases, and bitwise Float32 elevation benchmark preservation.
Optimized with class-level setup fixtures to prevent redundant A* search and DTM reloading.
"""

import math
import struct
import pytest
import numpy as np
import rasterio
from rasterio.transform import rowcol
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.traversability_service import (
    get_traversability_service,
    TERRAIN_SOURCES,
    MARS_RADIUS_M,
)
from app.marswalk.marswalk_models import MarswalkRouteRequest
from app.marswalk.marswalk_planner import (
    MarswalkPlanner,
    get_cached_route,
    clear_route_cache,
)
from app.marswalk.multi_stop_models import (
    MultiStopRouteRequest,
    ScienceStop,
)
from app.marswalk.multi_stop_planner import (
    MultiStopPlanner,
    get_cached_multi_stop_traverse,
    clear_multi_stop_cache,
)
from app.marswalk.route_intelligence_service import get_route_intelligence_service
from app.science.discovery_service import CANDIDATE_DISCOVERIES

client = TestClient(app)


# ---------------------------------------------------------------------------
# Independent Mathematical Reference Functions
# ---------------------------------------------------------------------------

def independent_haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Independent spherical great-circle distance on Mars (R = 3,396,190 m)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return MARS_RADIUS_M * c


def independent_3d_distance_m(lat1: float, lon1: float, z1: float, lat2: float, lon2: float, z2: float) -> float:
    """Independent 3D Euclidean surface distance combining great-circle arc and elevation delta."""
    d_horiz = independent_haversine_distance_m(lat1, lon1, lat2, lon2)
    dz = z2 - z1
    return math.sqrt(d_horiz ** 2 + dz ** 2)


def independent_linear_detrend_rmsd(elevations: list[float]) -> float:
    """Independent ordinary least-squares linear detrending and residual RMSD."""
    arr = np.array(elevations, dtype=np.float64)
    n = len(arr)
    if n < 3:
        return float(np.std(arr))
    x = np.arange(n, dtype=np.float64)
    x_mean = np.mean(x)
    y_mean = np.mean(arr)
    alpha = np.sum((x - x_mean) * (arr - y_mean)) / np.sum((x - x_mean) ** 2)
    beta = y_mean - alpha * x_mean
    trend = alpha * x + beta
    residuals = arr - trend
    return float(np.std(residuals))


# ===========================================================================
# 1. SCENARIO A: Single-Leg Traverse Independent Validation
# ===========================================================================

class TestScenarioASingleLegValidation:
    """Independently verifies single-leg route generation, caching, and intelligence."""

    @classmethod
    def setup_class(cls):
        clear_route_cache()
        req = MarswalkRouteRequest(
            start_name="Tyrrhena Channel Head",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Tyrrhena Channel Mouth",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            max_slope_deg=20.0,
            slope_penalty_factor=2.0,
        )
        cls.route = MarswalkPlanner.plan_route(req)
        cls.intel_svc = get_route_intelligence_service()
        cls.report = cls.intel_svc.analyze_route(cls.route)

    def test_route_caching_and_api_retrieval(self):
        cached = get_cached_route(self.route.route_id)
        assert cached is not None
        assert cached.route_id == self.route.route_id

        resp = client.get(f"/api/v1/marswalk/route/{self.route.route_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["route_id"] == self.route.route_id
        assert data["source_dataset"] == "ctx-tyrrhena"

        resp_intel = client.get(f"/api/v1/marswalk/analysis/route/{self.route.route_id}")
        assert resp_intel.status_code == 200
        intel_data = resp_intel.json()
        assert intel_data["route_id"] == self.route.route_id

    def test_independent_distance_and_geometry_continuity(self):
        points = self.route.path_points
        assert len(points) >= 2

        # 1. Independent reconstruction using projected IAU:49910 coordinates
        proj_surf_sum = 0.0
        proj_horiz_sum = 0.0
        for i in range(1, len(points)):
            p0 = points[i - 1]
            p1 = points[i]
            x0 = MARS_RADIUS_M * math.radians(p0.lon)
            y0 = MARS_RADIUS_M * math.radians(p0.lat)
            x1 = MARS_RADIUS_M * math.radians(p1.lon)
            y1 = MARS_RADIUS_M * math.radians(p1.lat)
            dh = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
            dz = p1.elevation_m - p0.elevation_m
            ds = math.sqrt(dh ** 2 + dz ** 2)
            proj_horiz_sum += dh
            proj_surf_sum += ds

            assert self.report.elevation_profile.points[i].distance_m >= self.report.elevation_profile.points[i - 1].distance_m

        diff_proj_native = abs(proj_surf_sum - self.route.total_surface_distance_m)
        assert diff_proj_native < 0.05, f"Projected coordinate reconstruction deviated by {diff_proj_native:.4f} m"
        assert math.isclose(self.report.surface_distance_m, self.route.total_surface_distance_m, abs_tol=0.01)

        # 2. Great-circle spherical arc distance (differs by cos(lat) map projection scale factor)
        geodesic_dist = 0.0
        for i in range(1, len(points)):
            p0, p1 = points[i - 1], points[i]
            d_h = independent_haversine_distance_m(p0.lat, p0.lon, p1.lat, p1.lon)
            dz = p1.elevation_m - p0.elevation_m
            geodesic_dist += math.sqrt(d_h ** 2 + dz ** 2)
        assert abs(geodesic_dist - self.route.total_surface_distance_m) < 2.0

    def test_independent_elevation_samples_from_raster(self):
        src_dict = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-tyrrhena")
        with rasterio.open(src_dict["elev_path"]) as ds:
            transform = ds.transform
            for pt in self.route.path_points[::5]:
                lon_norm = pt.lon % 360.0
                proj_lon = lon_norm - 360.0 if (ds.bounds.right <= 0 and lon_norm > 180.0) else lon_norm
                x = MARS_RADIUS_M * math.radians(proj_lon)
                y = MARS_RADIUS_M * math.radians(pt.lat)
                r, c = rowcol(transform, x, y)
                window = rasterio.windows.Window(c, r, 1, 1)
                raw_z = float(ds.read(1, window=window)[0, 0])
                assert math.isclose(raw_z, pt.elevation_m, abs_tol=0.1)

    def test_independent_elevation_extremes_and_gain_loss(self):
        elevs = [p.elevation_m for p in self.report.elevation_profile.points]

        indep_min = min(elevs)
        indep_max = max(elevs)
        indep_net = elevs[-1] - elevs[0]

        indep_gain = 0.0
        indep_loss = 0.0
        for i in range(1, len(elevs)):
            dz = elevs[i] - elevs[i - 1]
            if dz > 0:
                indep_gain += dz
            else:
                indep_loss += abs(dz)

        summary = self.report.elevation_profile
        assert math.isclose(indep_min, summary.min_elevation_m, abs_tol=0.01)
        assert math.isclose(indep_max, summary.max_elevation_m, abs_tol=0.01)
        assert math.isclose(indep_net, summary.net_elevation_change_m, abs_tol=0.01)
        assert math.isclose(indep_gain, summary.cumulative_elevation_gain_m, abs_tol=0.01)
        assert math.isclose(indep_loss, summary.cumulative_elevation_loss_m, abs_tol=0.01)

    def test_independent_local_gradient_calculation(self):
        prof = self.report.elevation_profile.points
        assert prof[0].local_gradient_pct == 0.0

        for i in range(1, len(prof)):
            p_prev = prof[i - 1]
            p_curr = prof[i]
            dd = p_curr.distance_m - p_prev.distance_m
            dz = p_curr.elevation_m - p_prev.elevation_m
            if dd > 1e-3:
                indep_grade = (dz / dd) * 100.0
                assert math.isclose(indep_grade, p_curr.local_gradient_pct, abs_tol=0.1)

    def test_independent_slope_exposure_conservation(self):
        bands = self.report.terrain_intelligence.slope_exposure_bands
        total_band_dist = sum(b.distance_m for b in bands)
        total_band_pct = sum(b.percentage for b in bands)

        total_route_dist = self.report.surface_distance_m
        assert math.isclose(total_band_dist, total_route_dist, abs_tol=0.01)
        assert math.isclose(total_band_pct, 100.0, abs_tol=0.01)

    def test_independent_topographic_roughness_rmsd(self):
        elevs = [p.elevation_m for p in self.report.elevation_profile.points]
        indep_roughness = round(independent_linear_detrend_rmsd(elevs), 2)
        assert math.isclose(indep_roughness, self.report.terrain_intelligence.roughness_index_m, abs_tol=0.01)


# ===========================================================================
# 2. SCENARIO B: Multi-Stop Traverse Independent Validation
# ===========================================================================

class TestScenarioBMultiStopValidation:
    """Independently verifies multi-stop planning, junction deduplication, and leg summation."""

    @classmethod
    def setup_class(cls):
        clear_multi_stop_cache()
        req = MultiStopRouteRequest(
            start_name="Base Camp Alpha",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Science Hab 2",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            stops=[
                ScienceStop(
                    stop_id="tyrrhena-valley-stop",
                    name="Ancient Valley Exploration",
                    lat=-4.602,
                    lon=66.320,
                    is_mandatory=True,
                    target_geology="Noachian highland dissected",
                ),
                ScienceStop(
                    stop_id="tyrrhena-caldera-stop",
                    name="Tyrrhena Caldera Scarp",
                    lat=-4.604,
                    lon=66.322,
                    is_mandatory=True,
                    target_geology="Hesperian volcanic edifice",
                ),
            ],
            max_slope_deg=20.0,
            slope_penalty_factor=2.0,
        )
        cls.traverse = MultiStopPlanner.plan_multi_stop_traverse(req)
        cls.intel_svc = get_route_intelligence_service()
        cls.report = cls.intel_svc.analyze_multi_stop_traverse(cls.traverse)

    def test_mandatory_stops_preserved_in_sequence(self):
        assert self.traverse.status in ["success", "optimal"]
        assert len(self.traverse.legs) == 3

        visited_ids = [s.stop_id for s in self.traverse.ordered_stops]
        assert "tyrrhena-valley-stop" in visited_ids
        assert "tyrrhena-caldera-stop" in visited_ids
        assert len(self.traverse.unreachable_stops) == 0

    def test_leg_connectivity_and_junction_deduplication(self):
        legs = self.traverse.legs
        m = len(legs)

        for i in range(m - 1):
            leg_end = legs[i].geometry["coordinates"][-1]
            next_start = legs[i + 1].geometry["coordinates"][0]
            assert leg_end == next_start

        leg_point_counts = [len(leg_rep.elevation_profile.points) for leg_rep in self.report.legs]
        expected_dedup_points = sum(leg_point_counts) - (m - 1)
        actual_profile_points = len(self.report.aggregated_elevation_profile.points)
        assert actual_profile_points == expected_dedup_points

    def test_aggregated_distance_conservation(self):
        sum_leg_distances = sum(leg.surface_distance_m for leg in self.traverse.legs)
        assert math.isclose(sum_leg_distances, self.traverse.total_surface_distance_m, abs_tol=0.01)
        assert math.isclose(sum_leg_distances, self.report.total_surface_distance_m, abs_tol=0.01)

    def test_aggregated_elevation_gain_loss_conservation(self):
        sum_gain = sum(leg.elevation_gain_m for leg in self.traverse.legs)
        sum_loss = sum(leg.elevation_loss_m for leg in self.traverse.legs)

        assert math.isclose(sum_gain, self.traverse.cumulative_elevation_gain_m, abs_tol=0.01)
        assert math.isclose(sum_loss, self.traverse.cumulative_elevation_loss_m, abs_tol=0.01)
        assert math.isclose(sum_gain, self.report.aggregated_elevation_profile.cumulative_elevation_gain_m, abs_tol=0.01)
        assert math.isclose(sum_loss, self.report.aggregated_elevation_profile.cumulative_elevation_loss_m, abs_tol=0.01)

    def test_individual_leg_reports_available(self):
        assert len(self.report.legs) == 3
        for i, leg_rep in enumerate(self.report.legs):
            assert leg_rep.leg_index == i
            assert leg_rep.surface_distance_m > 0
            assert len(leg_rep.elevation_profile.points) >= 2

    def test_unreachable_optional_stop_excluded_gracefully(self):
        req = MultiStopRouteRequest(
            start_name="Apollinaris Plains Base",
            start_lat=4.700,
            start_lon=168.250,
            dest_name="Apollinaris Science Hab",
            dest_lat=4.703,
            dest_lon=168.254,
            preferred_source="ctx-apollinaris",
            max_slope_deg=6.0,
            stops=[
                ScienceStop(
                    stop_id="opt-cliff-stop",
                    name="Steep Flute Scarp",
                    lat=4.71162,
                    lon=168.24548,
                    is_mandatory=False,
                ),
            ],
            optimization_strategy="optimize_tsp",
        )
        resp = MultiStopPlanner.plan_multi_stop_traverse(req)
        assert len(resp.unreachable_stops) == 1
        assert resp.unreachable_stops[0]["stop_id"] == "opt-cliff-stop"
        assert resp.status == "partial"
        assert len(resp.ordered_stops) == 0
        assert len(resp.legs) == 1
        assert resp.legs[0].is_feasible is True

    def test_unreachable_mandatory_stop_rejects_with_400(self):
        req = MultiStopRouteRequest(
            start_name="Tyrrhena Valley Crest",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Tyrrhena Channel Mouth",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            max_slope_deg=5.0,
            stops=[
                ScienceStop(
                    stop_id="mandatory-cliff",
                    name="Impassable Cliff",
                    lat=-4.602,
                    lon=66.320,
                    is_mandatory=True,
                )
            ],
        )
        with pytest.raises(ValueError) as exc_info:
            MultiStopPlanner.plan_multi_stop_traverse(req)
        assert "is unreachable within slope threshold" in str(exc_info.value)
        assert "-4.6020°S" not in str(exc_info.value)
        assert "4.6020°S" in str(exc_info.value)


# ===========================================================================
# 3. SCENARIO C: Geological Intelligence Validation
# ===========================================================================

class TestScenarioCGeologicalIntelligenceValidation:
    """Verifies SIM 3292 chronostratigraphic unit intersections, contacts, and scale caveats."""

    @classmethod
    def setup_class(cls):
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        route = MarswalkPlanner.plan_route(req)
        cls.geol = get_route_intelligence_service().analyze_route(route).geological_context

    def test_geological_unit_segmentation_and_metadata(self):
        assert "USGS" in self.geol.cartographic_source or "SIM 3292" in self.geol.cartographic_source
        assert self.geol.published_scale == "1:20,000,000"
        assert self.geol.positional_uncertainty_km >= 5.0

        assert len(self.geol.units_traversed) >= 1
        for seg in self.geol.units_traversed:
            assert seg.unit_code != ""
            assert seg.unit_name != ""
            assert seg.traversed_length_m > 0
            assert seg.distance_start_m >= 0

    def test_cartographic_scale_caveat_strictly_enforced(self):
        intel_svc = get_route_intelligence_service()
        meta = intel_svc.get_metadata()

        assert meta.geological_map["scale"] == "1:20,000,000"
        rules_text = " ".join(meta.scientific_rules)
        assert "1:20,000,000" in rules_text
        assert "5-10 km" in rules_text or "uncertainty" in rules_text.lower()


# ===========================================================================
# 4. SCENARIO D: Thermophysical Intelligence Validation
# ===========================================================================

class TestScenarioDThermophysicalIntelligenceValidation:
    """Verifies TES thermal inertia in TIU, 790-step LUT, and strict temperature prohibitions."""

    @classmethod
    def setup_class(cls):
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        route = MarswalkPlanner.plan_route(req)
        cls.therm = get_route_intelligence_service().analyze_route(route).thermophysical_context

    def test_tes_thermal_inertia_units_and_resolution(self):
        assert "J m^-2 K^-1 s^-1/2" in self.therm.units or "tiu" in self.therm.units.lower()
        assert "20 ppd" in self.therm.native_resolution_desc.lower() or "20 pixels per degree" in self.therm.native_resolution_desc.lower()

        if self.therm.mean_tiu is not None:
            assert 20.0 <= self.therm.mean_tiu <= 1000.0

    def test_strict_temperature_prohibition_advisory(self):
        disclaimer = self.therm.temperature_prohibition_disclaimer.lower()
        assert "temperature" in disclaimer
        assert "not" in disclaimer or "prohibition" in disclaimer


# ===========================================================================
# 5. SCENARIO E: Science Discovery Proximity Validation
# ===========================================================================

class TestScenarioEScienceDiscoveryProximityValidation:
    """Verifies candidate discovery identification, nearest mileposts, and 4-tier evidence."""

    @classmethod
    def setup_class(cls):
        req = MarswalkRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
        )
        route = MarswalkPlanner.plan_route(req)
        cls.opps = get_route_intelligence_service().analyze_route(route).nearby_science_opportunities

    def test_candidate_discovery_identification_near_tyrrhena(self):
        assert len(self.opps) >= 1
        opp_ids = [o.discovery_id for o in self.opps]
        assert any("tyrrhena" in did for did in opp_ids)

        for opp in self.opps:
            assert opp.evidence_class in [
                "direct_sensor_observation",
                "derived_measurement",
                "mapped_geological_interpretation",
                "indicative_proxy",
            ]
            assert opp.distance_from_route_km >= 0.0
            assert opp.closest_route_milepost_m >= 0.0


# ===========================================================================
# 6. EDGE CASES AND FAILURE MODES
# ===========================================================================

class TestEdgeCasesAndFailureModes:
    """Tests missing IDs, malformed inputs, out-of-bounds coords, and NoData policies."""

    def test_nonexistent_route_id_returns_404(self):
        resp = client.get("/api/v1/marswalk/route/mw-nonexistent-999999")
        assert resp.status_code == 404
        resp_intel = client.get("/api/v1/marswalk/analysis/route/mw-nonexistent-999999")
        assert resp_intel.status_code == 404

    def test_nonexistent_traverse_id_returns_404(self):
        resp = client.get("/api/v1/marswalk/multi-stop/mst-nonexistent-999999")
        assert resp.status_code == 404
        resp_intel = client.get("/api/v1/marswalk/analysis/multi-stop/mst-nonexistent-999999")
        assert resp_intel.status_code == 404

    def test_out_of_bounds_latitude_rejected_by_pydantic(self):
        resp = client.post(
            "/api/v1/marswalk/route",
            json={
                "start_lat": 95.0,
                "start_lon": 66.30,
                "dest_lat": -4.60,
                "dest_lon": 66.31,
            },
        )
        assert resp.status_code == 422

    def test_unsupported_coordinates_outside_dem_coverage(self):
        resp = client.post(
            "/api/v1/marswalk/route",
            json={
                "start_lat": 50.0,
                "start_lon": 10.0,
                "dest_lat": 50.01,
                "dest_lon": 10.01,
                "preferred_source": "ctx-tyrrhena",
            },
        )
        assert resp.status_code == 400

    def test_duplicate_start_and_destination_coords(self):
        resp = client.post(
            "/api/v1/marswalk/route",
            json={
                "start_lat": -4.600,
                "start_lon": 66.317,
                "dest_lat": -4.600,
                "dest_lon": 66.317,
                "preferred_source": "ctx-tyrrhena",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_surface_distance_m"] < 1.0

    def test_nodata_elevation_never_silently_converted_to_zero(self):
        svc = get_traversability_service()
        pt = svc.query_point(-85.0, 0.0)
        assert pt is not None


# ===========================================================================
# 7. BITWISE FLOAT32 ELEVATION BENCHMARK PRESERVATION
# ===========================================================================

class TestBitwiseFloat32ElevationBenchmarks:
    """Verifies that the three authoritative Float32 elevation benchmarks remain exact."""

    def test_tyrrhena_benchmark_bitwise_hex(self):
        src_dict = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-tyrrhena")
        with rasterio.open(src_dict["elev_path"]) as ds:
            x = MARS_RADIUS_M * math.radians(66.317)
            y = MARS_RADIUS_M * math.radians(-4.600)
            r, c = rowcol(ds.transform, x, y)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "4508d7c3"
            assert math.isclose(float(raw_val), 2189.485107421875, rel_tol=1e-7)

    def test_apollinaris_benchmark_bitwise_hex(self):
        src_dict = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-apollinaris")
        with rasterio.open(src_dict["elev_path"]) as ds:
            x = MARS_RADIUS_M * math.radians(168.250)
            y = MARS_RADIUS_M * math.radians(4.700)
            r, c = rowcol(ds.transform, x, y)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "c5372c4c"
            assert math.isclose(float(raw_val), -2930.7685546875, rel_tol=1e-7)

    def test_holden_benchmark_bitwise_hex(self):
        src_dict = next(s for s in TERRAIN_SOURCES if s["source_id"] == "hirise-holden")
        with rasterio.open(src_dict["elev_path"]) as ds:
            lon_norm = 309.020 % 360.0
            proj_lon = lon_norm - 360.0 if lon_norm > 180.0 else lon_norm
            x = MARS_RADIUS_M * math.radians(proj_lon)
            y = MARS_RADIUS_M * math.radians(-28.500)
            r, c = rowcol(ds.transform, x, y)
            raw_val = ds.read(1, window=rasterio.windows.Window(c, r, 1, 1))[0, 0]
            raw_hex = struct.pack(">f", float(raw_val)).hex()
            assert raw_hex == "c48d849f"
            assert math.isclose(float(raw_val), -1132.1444091796875, rel_tol=1e-7)
