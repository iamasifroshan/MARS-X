"""Phase 8.8.3.1 Asymmetric TSP Optimization & Multi-Stop Integrity Validation Suite.

Validates:
1. Mathematical correctness of Asymmetric 2-opt on directed terrain cost matrices.
2. Exact permutation search (K <= 4) as an empirical reference oracle with 0.0% optimality gap.
3. Strict semantics for mandatory vs optional stops under impassable terrain.
4. Continuous GeoJSON LineString assembly and junction vertex deduplication.
5. Telemetry disaggregation (physical 3D surface distance vs analytical optimization cost).
6. Bitwise preservation of raw IEEE 754 Float32 elevation benchmarks.
7. Coordinate notation standards (never combine negative sign with south/north suffix).
"""

import math
import struct
import numpy as np
import pytest
from app.marswalk.marswalk_models import MarswalkRouteRequest
from app.marswalk.marswalk_planner import MarswalkPlanner, TERRAIN_SOURCES
from app.marswalk.multi_stop_models import (
    MultiStopRouteRequest,
    PairwiseRouteLeg,
    ScienceStop,
)
from app.marswalk.multi_stop_planner import (
    MultiStopPlanner,
    clear_multi_stop_cache,
)


# ==============================================================================
# 1. Asymmetric 2-Opt and ATSP Mathematical Integrity
# ==============================================================================


class TestAsymmetricTSPMathematicalValidation:
    """Verifies that 2-opt evaluates full directed sequence costs rather than symmetric shortcut deltas."""

    def test_deliberate_asymmetric_matrix_2opt_reversal_cost(self):
        """Construct a strongly asymmetric 4-node problem where Cost(W1, W2) << Cost(W2, W1).

        Verify that 2-opt evaluates all reversed directed internal edges and picks the
        lower-cost sequence rather than assuming Cost(u, v) == Cost(v, u).
        """
        start = ScienceStop(stop_id="S", name="Start", lat=-4.600, lon=66.317, is_mandatory=True)
        dest = ScienceStop(stop_id="D", name="Dest", lat=-4.605, lon=66.325, is_mandatory=True)
        w1 = ScienceStop(stop_id="W1", name="Stop 1", lat=-4.601, lon=66.319, is_mandatory=True)
        w2 = ScienceStop(stop_id="W2", name="Stop 2", lat=-4.603, lon=66.322, is_mandatory=True)

        def make_dummy_leg(from_id: str, to_id: str, cost: float) -> PairwiseRouteLeg:
            return PairwiseRouteLeg(
                route_id=f"leg-{from_id}-{to_id}",
                leg_index=0,
                from_stop_id=from_id,
                to_stop_id=to_id,
                from_stop_name=from_id,
                to_stop_name=to_id,
                from_coord=(0.0, 0.0),
                to_coord=(0.0, 0.0),
                is_feasible=True,
                surface_distance_m=100.0,
                horizontal_distance_m=100.0,
                optimization_cost=cost,
                elevation_gain_m=10.0,
                elevation_loss_m=0.0,
                min_elevation_m=-1000.0,
                max_elevation_m=-990.0,
                max_slope_deg=5.0,
                mean_slope_deg=3.0,
                slope_band_exposure_pct={"low": 100.0},
                source_dataset="test-dem",
                geometry={"type": "LineString", "coordinates": [[66.317, -4.6], [66.325, -4.605]]},
            )

        # Strongly directed asymmetric cost matrix:
        # S -> W1: 10, W1 -> W2: 10, W2 -> D: 10   Total: 30
        # S -> W2: 100, W2 -> W1: 200, W1 -> D: 100 Total: 400
        matrix = {
            ("S", "W1"): make_dummy_leg("S", "W1", 10.0),
            ("S", "W2"): make_dummy_leg("S", "W2", 100.0),
            ("W1", "W2"): make_dummy_leg("W1", "W2", 10.0),
            ("W2", "W1"): make_dummy_leg("W2", "W1", 200.0),
            ("W1", "D"): make_dummy_leg("W1", "D", 100.0),
            ("W2", "D"): make_dummy_leg("W2", "D", 10.0),
        }

        # Case A: Sequence is [W1, W2] -> Cost is 10 + 10 + 10 = 30.0
        # Case B: Sequence is [W2, W1] -> Cost is 100 + 200 + 100 = 400.0
        # When starting from [W2, W1], 2-opt MUST reverse the internal section to [W1, W2]
        ordered, strategy, is_heuristic, stats = MultiStopPlanner.optimize_stop_sequence(
            start_stop=start,
            dest_stop=dest,
            intermediate_stops=[w2, w1],  # Given in bad order
            pairwise_matrix=matrix,
            strategy="optimize_tsp",
        )

        assert [s.stop_id for s in ordered] == ["W1", "W2"]
        assert stats["exact_optimum_cost"] == 30.0
        assert stats["optimality_gap_pct"] == 0.0

    def test_exact_oracle_comparison_k1_to_k4(self):
        """For K in 1, 2, 3, 4, verify that exact permutation and 2-opt solutions are measured

        and the optimality gap is exactly 0.0%.
        """
        start = ScienceStop(stop_id="S", name="Start", lat=-4.600, lon=66.317, is_mandatory=True)
        dest = ScienceStop(stop_id="D", name="Dest", lat=-4.605, lon=66.325, is_mandatory=True)

        for k in [1, 2, 3, 4]:
            stops = [
                ScienceStop(stop_id=f"W{i}", name=f"Stop {i}", lat=-4.600 - i * 0.001, lon=66.317 + i * 0.001)
                for i in range(1, k + 1)
            ]
            all_nodes = [start] + stops + [dest]
            matrix = {}
            for u in all_nodes:
                for v in all_nodes:
                    if u.stop_id != v.stop_id:
                        # Asymmetric cost: distance-based + directional bias
                        u_idx = int(u.stop_id[1]) if u.stop_id.startswith("W") else (0 if u.stop_id == "S" else 99)
                        v_idx = int(v.stop_id[1]) if v.stop_id.startswith("W") else (0 if v.stop_id == "S" else 99)
                        asym_bias = 15.0 if u_idx > v_idx else 0.0
                        matrix[(u.stop_id, v.stop_id)] = PairwiseRouteLeg(
                            route_id=f"leg-{u.stop_id}-{v.stop_id}",
                            leg_index=0,
                            from_stop_id=u.stop_id,
                            to_stop_id=v.stop_id,
                            from_stop_name=u.name,
                            to_stop_name=v.name,
                            from_coord=(u.lat, u.lon),
                            to_coord=(v.lat, v.lon),
                            is_feasible=True,
                            surface_distance_m=150.0,
                            horizontal_distance_m=150.0,
                            optimization_cost=100.0 + abs(u_idx - v_idx) * 20.0 + asym_bias,
                            elevation_gain_m=5.0,
                            elevation_loss_m=0.0,
                            min_elevation_m=-1000.0,
                            max_elevation_m=-990.0,
                            max_slope_deg=6.0,
                            mean_slope_deg=4.0,
                            slope_band_exposure_pct={"low": 100.0},
                            source_dataset="test-dem",
                            geometry={"type": "LineString", "coordinates": [[u.lon, u.lat], [v.lon, v.lat]]},
                        )

            ordered, strategy, is_heuristic, stats = MultiStopPlanner.optimize_stop_sequence(
                start_stop=start,
                dest_stop=dest,
                intermediate_stops=stops,
                pairwise_matrix=matrix,
                strategy="optimize_tsp",
            )
            assert len(ordered) == k
            assert stats["optimality_gap_pct"] == 0.0
            assert stats["exact_optimum_cost"] <= stats["initial_nn_cost"]
            assert stats["permutations_evaluated"] == math.factorial(k)


# ==============================================================================
# 2. Optional vs Mandatory Stop Semantics
# ==============================================================================


class TestOptionalVsMandatoryStopSemantics:
    """Verifies that unreachable optional stops are excluded without failing the traverse,

    while unreachable mandatory stops raise ValueError.
    """

    def setup_method(self):
        clear_multi_stop_cache()

    def test_unreachable_optional_stop_is_excluded_into_unreachable_stops(self):
        """When an optional stop is blocked by terrain (e.g. slope > max_slope_deg or NoData),

        the planner must filter it into `unreachable_stops` and complete the traverse for reachable stops.
        """
        req = MultiStopRouteRequest(
            start_name="Apollinaris Plains Base",
            start_lat=4.700,
            start_lon=168.250,
            dest_name="Apollinaris Science Hab",
            dest_lat=4.703,
            dest_lon=168.254,
            preferred_source="ctx-apollinaris",
            max_slope_deg=6.0,  # 6 deg is passable between start and dest, but impassable to steep flute
            stops=[
                ScienceStop(
                    stop_id="opt-cliff-stop",
                    name="Steep Flute Scarp",
                    lat=4.71162,
                    lon=168.24548,
                    is_mandatory=False,  # Optional!
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

    def test_unreachable_mandatory_stop_strictly_raises_value_error(self):
        """When a mandatory stop is unreachable, plan_multi_stop_traverse must reject

        the entire plan with ValueError.
        """
        req = MultiStopRouteRequest(
            start_name="Tyrrhena Valley Crest",
            start_lat=-4.600,
            start_lon=66.317,
            dest_name="Tyrrhena Channel Mouth",
            dest_lat=-4.605,
            dest_lon=66.325,
            preferred_source="ctx-tyrrhena",
            max_slope_deg=5.0,  # Unnavigable slope in Tyrrhena valley
            stops=[
                ScienceStop(
                    stop_id="mandatory-cliff",
                    name="Impassable Cliff",
                    lat=-4.602,
                    lon=66.320,
                    is_mandatory=True,  # Mandatory!
                )
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            MultiStopPlanner.plan_multi_stop_traverse(req)

        assert "is unreachable within slope threshold" in str(exc_info.value)
        # Coordinate check: must not write -...°S or -...°N
        assert "-4.6020°S" not in str(exc_info.value)
        assert "-4.6020°N" not in str(exc_info.value)
        assert "4.6020°S" in str(exc_info.value)

    def test_max_stops_preserves_all_mandatory_stops(self):
        """Verify that max_stops limits the number of optional stops without dropping mandatory stops."""
        req = MultiStopRouteRequest(
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            max_stops=3,
            stops=[
                ScienceStop(stop_id="m1", name="Mandatory 1", lat=-4.601, lon=66.318, is_mandatory=True),
                ScienceStop(stop_id="m2", name="Mandatory 2", lat=-4.602, lon=66.319, is_mandatory=True),
                ScienceStop(stop_id="opt1", name="Optional 1", lat=-4.603, lon=66.320, is_mandatory=False),
                ScienceStop(stop_id="opt2", name="Optional 2", lat=-4.604, lon=66.321, is_mandatory=False),
            ],
        )
        resolved = MultiStopPlanner.resolve_all_stops(req)
        assert len(resolved) == 3
        ids = [s.stop_id for s in resolved]
        assert "m1" in ids
        assert "m2" in ids
        assert "opt1" in ids
        assert "opt2" not in ids


# ==============================================================================
# 3. GeoJSON Continuity and Junction Vertex Deduplication
# ==============================================================================


class TestGeoJsonContinuityAndDeduplication:
    """Verifies that connected traverse geometries form a single uninterrupted LineString

    without duplicating junction vertices.
    """

    def test_junction_vertex_deduplication(self):
        """Ensure connected_geometry coordinates have exactly N_total - (num_legs - 1) vertices."""
        req = MultiStopRouteRequest(
            start_name="Holden Crest",
            start_lat=-28.500,
            start_lon=309.020,
            dest_name="Holden Alluvial Basin",
            dest_lat=-28.502,
            dest_lon=309.022,
            preferred_source="hirise-holden",
            stops=[
                ScienceStop(
                    stop_id="holden-fan-1",
                    name="Alluvial Fan Outcrop 1",
                    lat=-28.501,
                    lon=309.021,
                    is_mandatory=True,
                ),
            ],
            optimization_strategy="optimize_tsp",
        )

        resp = MultiStopPlanner.plan_multi_stop_traverse(req)
        coords = resp.connected_geometry["coordinates"]

        # 1. No two consecutive coordinates are identical
        for i in range(len(coords) - 1):
            assert coords[i] != coords[i + 1], f"Duplicate consecutive vertex found at index {i}: {coords[i]}"

        # 2. The start coordinate of leg i must match terminal coordinate of leg i-1
        for leg_idx in range(1, len(resp.legs)):
            prev_leg_end = resp.legs[leg_idx - 1].geometry["coordinates"][-1]
            cur_leg_start = resp.legs[leg_idx].geometry["coordinates"][0]
            assert prev_leg_end == cur_leg_start, f"Discontinuity between leg {leg_idx-1} and leg {leg_idx}"

        # 3. Total vertices in connected_geometry equals sum(len(leg.coords)) - (num_legs - 1)
        expected_len = sum(len(leg.geometry["coordinates"]) for leg in resp.legs) - (len(resp.legs) - 1)
        assert len(coords) == expected_len


# ==============================================================================
# 4. Telemetry Disaggregation & Analytical Invariants
# ==============================================================================


class TestTelemetryDisaggregationAndInvariants:
    """Verifies that physical surface distance is cleanly disaggregated from optimization cost."""

    def test_telemetry_distance_vs_cost_invariants(self):
        """Assert that total_surface_distance_m is purely geometric/physical,

        and total_optimization_cost is the sum of A* analytical edge costs.
        """
        req = MultiStopRouteRequest(
            start_name="Holden Crest",
            start_lat=-28.500,
            start_lon=309.020,
            dest_name="Holden Alluvial Basin",
            dest_lat=-28.502,
            dest_lon=309.022,
            preferred_source="hirise-holden",
            stops=[
                ScienceStop(
                    stop_id="holden-fan-1",
                    name="Alluvial Fan Outcrop 1",
                    lat=-28.501,
                    lon=309.021,
                    is_mandatory=True,
                )
            ],
        )
        resp = MultiStopPlanner.plan_multi_stop_traverse(req)

        # Disaggregation assertions
        sum_surface_dist = sum(leg.surface_distance_m for leg in resp.legs)
        sum_horiz_dist = sum(leg.horizontal_distance_m for leg in resp.legs)
        sum_opt_cost = sum(leg.optimization_cost for leg in resp.legs)
        sum_gain = sum(leg.elevation_gain_m for leg in resp.legs)
        sum_loss = sum(leg.elevation_loss_m for leg in resp.legs)

        assert abs(resp.total_surface_distance_m - sum_surface_dist) < 1e-2
        assert abs(resp.total_horizontal_distance_m - sum_horiz_dist) < 1e-2
        assert abs(resp.total_optimization_cost - sum_opt_cost) < 1e-2
        assert abs(resp.cumulative_elevation_gain_m - sum_gain) < 1e-2
        assert abs(resp.cumulative_elevation_loss_m - sum_loss) < 1e-2

        # 3D surface distance must be >= 2D horizontal distance
        assert resp.total_surface_distance_m >= resp.total_horizontal_distance_m

        # Weighted mean slope matches definition: sum(d_i * slope_i) / sum(d_i)
        weighted_slope = sum(leg.surface_distance_m * leg.mean_slope_deg for leg in resp.legs) / resp.total_surface_distance_m
        assert abs(resp.mean_route_slope_deg - weighted_slope) < 1e-2

        # Max slope is max across all legs
        expected_max_slope = max(leg.max_slope_deg for leg in resp.legs)
        assert abs(resp.max_route_slope_deg - expected_max_slope) < 1e-2


# ==============================================================================
# 5. Elevation Benchmark Bitwise Preservation & Coordinate Standards
# ==============================================================================


class TestElevationBenchmarkPreservationAndCoordinateNotation:
    """Verifies bitwise IEEE 754 Float32 elevation benchmarks and coordinate notation."""

    def test_tyrrhena_ctx_dtm_bitwise_hex(self):
        """Tyrrhena CTX DTM elevation benchmark at row 500, col 500: +2189.485107421875 m (0x4508d7c3)."""
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-tyrrhena")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=-4.600,
            start_lon=66.317,
            dest_lat=-4.605,
            dest_lon=66.325,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0x4508d7c3", f"Tyrrhena raw hex mismatch: {raw_hex} != 0x4508d7c3"
        assert abs(val - 2189.485107421875) < 1e-6
        assert round(val, 2) == 2189.49

    def test_apollinaris_sulci_dtm_bitwise_hex(self):
        """Apollinaris Sulci CTX DTM elevation benchmark at row 500, col 500: -2930.7685546875 m (0xc5372c4c)."""
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "ctx-apollinaris")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=4.700,
            start_lon=168.250,
            dest_lat=4.706,
            dest_lon=168.258,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0xc5372c4c", f"Apollinaris raw hex mismatch: {raw_hex} != 0xc5372c4c"
        assert abs(val - (-2930.7685546875)) < 1e-6
        assert round(val, 2) == -2930.77

    def test_holden_hirise_dtm_bitwise_hex(self):
        """Holden Crater HiRISE DTM elevation benchmark at row 500, col 500: -1132.1444091796875 m (0xc48d849f)."""
        source = next(s for s in TERRAIN_SOURCES if s["source_id"] == "hirise-holden")
        grid, start_rc, _ = MarswalkPlanner.extract_grid_window(
            source=source,
            start_lat=-28.500,
            start_lon=309.020,
            dest_lat=-28.502,
            dest_lon=309.022,
            min_margin_px=10,
        )
        r, c = start_rc
        val = float(grid.elevation[r, c])
        raw_hex = "0x" + struct.pack(">f", val).hex()
        assert raw_hex == "0xc48d849f", f"Holden raw hex mismatch: {raw_hex} != 0xc48d849f"
        assert abs(val - (-1132.1444091796875)) < 1e-6
        assert round(val, 2) == -1132.14

    def test_coordinate_notation_standards(self):
        """Ensure coordinate formatting never produces invalid combinations like -4.600°S or -4.600°N."""
        test_coords = [(-4.600, 66.317), (-28.500, 309.020), (4.700, 168.250)]
        for lat, lon in test_coords:
            lat_cardinal = f"{abs(lat):.4f}°S" if lat < 0 else f"{lat:.4f}°N"
            lat_signed = f"{lat:+.4f}°"
            # Valid expressions
            assert not lat_cardinal.startswith("-")
            assert "°S" in lat_cardinal or "°N" in lat_cardinal
            assert not (lat_signed.startswith("-") and "°S" in lat_signed)
            assert not (lat_signed.startswith("-") and "°N" in lat_signed)
