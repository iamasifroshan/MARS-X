"""Multi-Stop Marswalk Planning & Traveling Explorer Optimization Engine — Phase 8.8.3.

Extends the single-destination A* engine into a multi-stop science traverse planner:
- Seamless integration with Phase 8.7 Science Discovery System
- Pairwise directed route-cost matrix generation over authentic Mars DEMs
- Bounded TSP optimization:
    * Exact brute-force permutation optimizer for K <= 4 intermediate stops
    * Nearest-neighbor + 2-opt local search heuristic for K > 4 stops
- Connected GeoJSON LineString geometry assembly with duplicate junction elimination
- Multi-stop terrain analytics (surface distance vs analytical cost, elevation gain/loss, exposure)
- LRU caching with deterministic request hashing
- Mandatory astronaut safety disclaimers
"""

import os
import math
import time
import uuid
import itertools
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.terrain.traversability_service import TERRAIN_SOURCES
from app.science.discovery_service import get_discovery_service
from app.marswalk.marswalk_models import (
    MarswalkRouteRequest,
    MARSWALK_SAFETY_DISCLAIMER,
)
from app.marswalk.marswalk_planner import (
    MarswalkPlanner,
    compute_request_hash,
    MARSWALK_ALGORITHM_VERSION,
    MARSWALK_COST_FUNCTION_VERSION,
    MARSWALK_DERIVATIVE_VERSION,
)
from app.marswalk.multi_stop_models import (
    ScienceStop,
    MultiStopRouteRequest,
    PairwiseRouteLeg,
    MultiStopTraverseResponse,
    MultiStopPreset,
    MultiStopMetadataResponse,
)

logger = logging.getLogger("MARS-X.marswalk.multi_stop")

# Curated multi-stop traverse presets
CURATED_MULTI_STOP_PRESETS: List[MultiStopPreset] = [
    MultiStopPreset(
        preset_id="tyrrhena-valley-science-loop",
        name="Tyrrhena Terra Ancient Fluvial Science Transect",
        region="Tyrrhena Terra",
        source_dataset="ctx-tyrrhena",
        start_lat=-4.600,
        start_lon=66.317,
        dest_lat=-4.605,
        dest_lon=66.325,
        stops=[
            ScienceStop(
                stop_id="stop-tyrrhena-channel-bed",
                name="Fluvial Channel Stratigraphy",
                lat=-4.602,
                lon=66.320,
                discovery_id="disc-terr-tyrrhena-ctx",
                is_mandatory=True,
                target_geology="Inverted channel fill & stratified Noachian bedrock",
                description="Sample layered fluvial deposits along ancient paleochannel axis.",
            ),
            ScienceStop(
                stop_id="stop-tyrrhena-scarp",
                name="Terraced Scarp Exposure",
                lat=-4.604,
                lon=66.322,
                discovery_id="disc-multi-tyrrhena-corridor",
                is_mandatory=True,
                target_geology="Degraded impact crater rim scarp",
                description="Investigate erosional terrace contacts and bedrock fracturing.",
            ),
        ],
        description="Multi-stop science traverse negotiating branching fluvial valley network terrain at ~20 m/px.",
        target_geology="Noachian dissected plateau & ancient cratered terrain",
    ),
    MultiStopPreset(
        preset_id="holden-megabreccia-transect",
        name="Holden Crater Megabreccia Tactical Survey",
        region="Holden Crater (Margaritifer Terra)",
        source_dataset="hirise-holden",
        start_lat=-28.500,
        start_lon=309.020,
        dest_lat=-28.502,
        dest_lon=309.022,
        stops=[
            ScienceStop(
                stop_id="stop-holden-block-alpha",
                name="Megabreccia Block Alpha",
                lat=-28.501,
                lon=309.021,
                discovery_id="disc-terr-holden-hirise",
                is_mandatory=True,
                target_geology="Noachian impact megabreccia clast",
                description="Detailed multispectral inspection of pre-Holden basement ejecta clast.",
            ),
        ],
        description="High-resolution tactical traverse across ejecta megabreccia blocks at ~1.01 m/px.",
        target_geology="Noachian megabreccia & layered lacustrine beds",
    ),
    MultiStopPreset(
        preset_id="apollinaris-yardang-survey",
        name="Apollinaris Sulci Yardang & Basal Scarp Survey",
        region="Apollinaris Sulci",
        source_dataset="ctx-apollinaris",
        start_lat=4.700,
        start_lon=168.250,
        dest_lat=4.706,
        dest_lon=168.258,
        stops=[
            ScienceStop(
                stop_id="stop-apollinaris-flute",
                name="Ignimbrite Flute Outcrop",
                lat=4.703,
                lon=168.254,
                discovery_id="disc-terr-apollinaris-ctx",
                is_mandatory=True,
                target_geology="Medusae Fossae Formation friable volcanic ash",
                description="Measure aeolian abrasion rates on friable pyroclastic flutes.",
            ),
        ],
        description="Navigation through wind-eroded yardang flutes and friable ignimbrite ridges at ~20 m/px.",
        target_geology="Medusae Fossae Formation ignimbrite",
    ),
]

# In-memory LRU multi-stop traverse cache
_MULTI_STOP_CACHE: Dict[str, MultiStopTraverseResponse] = {}
_MULTI_STOP_HASH_TO_ID: Dict[str, str] = {}
_MAX_MULTI_STOP_CACHE_SIZE = 30


def compute_multi_stop_hash(request: MultiStopRouteRequest, resolved_source_id: str) -> str:
    """Compute deterministic cryptographic hash of all multi-stop parameters."""
    norm_start_lon = request.start_lon % 360.0
    norm_dest_lon = request.dest_lon % 360.0

    stops_str = "|".join(
        f"{s.stop_id}:{s.lat:.6f}:{s.lon % 360.0:.6f}:{s.is_mandatory}"
        for s in request.stops
    )
    disc_ids_str = ",".join(request.discovery_ids or [])
    strategy = request.optimization_strategy
    algo_v = MARSWALK_ALGORITHM_VERSION
    cost_v = MARSWALK_COST_FUNCTION_VERSION
    deriv_v = MARSWALK_DERIVATIVE_VERSION
    name = request.traverse_name or ""

    raw = (
        f"{request.start_lat:.6f}:{norm_start_lon:.6f}:"
        f"{request.dest_lat:.6f}:{norm_dest_lon:.6f}:"
        f"{stops_str}:{disc_ids_str}:{strategy}:{resolved_source_id}:"
        f"{request.slope_penalty_factor:.3f}:{request.max_slope_deg:.2f}:"
        f"{request.max_search_nodes}:{algo_v}:{cost_v}:{deriv_v}:{name}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_cached_multi_stop_traverse(traverse_id: str) -> Optional[MultiStopTraverseResponse]:
    """Retrieve previously planned multi-stop traverse by unique traverse_id."""
    return _MULTI_STOP_CACHE.get(traverse_id)


def clear_multi_stop_cache():
    """Clear in-memory multi-stop traverse cache (for testing)."""
    _MULTI_STOP_CACHE.clear()
    _MULTI_STOP_HASH_TO_ID.clear()


class MultiStopPlanner:
    """Coordinator for multi-stop science traverse optimization and analytics."""

    @classmethod
    def resolve_all_stops(cls, request: MultiStopRouteRequest) -> List[ScienceStop]:
        """Combine explicit stops and discovery_ids into a unified list of ScienceStop objects."""
        all_stops: List[ScienceStop] = list(request.stops)

        if request.discovery_ids:
            disc_svc = get_discovery_service()
            existing_ids = {s.stop_id for s in all_stops}
            for d_id in request.discovery_ids:
                if d_id in existing_ids:
                    continue
                d = disc_svc.get_discovery_by_id(d_id)
                if not d:
                    raise ValueError(f"Science discovery ID '{d_id}' not found in discovery catalog.")
                all_stops.append(
                    ScienceStop(
                        stop_id=d["id"],
                        name=d["title"],
                        lat=d["latitude"],
                        lon=d["longitude"],
                        discovery_id=d["id"],
                        is_mandatory=True,
                        target_geology=d.get("primary_geology"),
                        description=d.get("summary"),
                    )
                )

        if request.max_stops is not None and len(all_stops) > request.max_stops:
            # If mandatory stops exceed max_stops, raise error
            mandatory = [s for s in all_stops if s.is_mandatory]
            if len(mandatory) > request.max_stops:
                raise ValueError(
                    f"Number of mandatory science stops ({len(mandatory)}) exceeds the requested "
                    f"maximum stop limit ({request.max_stops}). Mark non-essential stops as optional "
                    "or increase max_stops."
                )
            # Retain all mandatory stops and trim optional stops to fit max_stops
            optional = [s for s in all_stops if not s.is_mandatory]
            slots_for_opt = request.max_stops - len(mandatory)
            all_stops = mandatory + optional[:slots_for_opt]

        return all_stops

    @classmethod
    def select_common_source(
        cls,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        stops: List[ScienceStop],
        preferred_source: Optional[str] = "auto",
    ) -> Dict[str, Any]:
        """Select highest resolution DEM that covers all waypoints (start, destination, and all stops)."""
        all_lats = [start_lat, dest_lat] + [s.lat for s in stops]
        all_lons = [start_lon % 360.0, dest_lon % 360.0] + [s.lon % 360.0 for s in stops]

        min_lat = min(all_lats)
        max_lat = max(all_lats)
        min_lon = min(all_lons)
        max_lon = max(all_lons)

        if preferred_source and preferred_source != "auto":
            src = next((s for s in TERRAIN_SOURCES if s["source_id"] == preferred_source), None)
            if src is None:
                raise ValueError(f"Unknown preferred terrain source: '{preferred_source}'")
            in_lat = (src["lat_min"] <= min_lat) and (max_lat <= src["lat_max"])
            in_lon = (src["lon_min"] <= min_lon) and (max_lon <= src["lon_max"])
            if not (in_lat and in_lon):
                raise ValueError(
                    f"Preferred source '{preferred_source}' does not cover all traverse waypoints: "
                    f"Traverse bounds Lat [{min_lat:.3f}°, {max_lat:.3f}°], Lon [{min_lon:.3f}°, {max_lon:.3f}°E]. "
                    f"Dataset footprint: Lat [{src['lat_min']}°, {src['lat_max']}°], Lon [{src['lon_min']}°, {src['lon_max']}°E]."
                )
            if not (os.path.isfile(src["elev_path"]) and os.path.getsize(src["elev_path"]) > 0):
                raise FileNotFoundError(f"Elevation file for '{preferred_source}' not found on disk.")
            return src

        # Auto selection: highest resolution source covering the bounding box of ALL waypoints
        for sid in ["hirise-holden", "ctx-tyrrhena", "ctx-apollinaris", "mola-128ppd", "mola-4ppd"]:
            src = next((s for s in TERRAIN_SOURCES if s["source_id"] == sid), None)
            if src is None:
                continue
            in_lat = (src["lat_min"] <= min_lat) and (max_lat <= src["lat_max"])
            in_lon = (src["lon_min"] <= min_lon) and (max_lon <= src["lon_max"])
            if in_lat and in_lon and os.path.isfile(src["elev_path"]):
                return src

        # Global MOLA fallback
        return next(s for s in TERRAIN_SOURCES if s["source_id"] == "mola-4ppd")

    @classmethod
    def compute_pairwise_leg(
        cls,
        from_stop: ScienceStop,
        to_stop: ScienceStop,
        source_id: str,
        slope_penalty_factor: float,
        max_slope_deg: float,
        max_search_nodes: int,
        leg_index: int,
    ) -> PairwiseRouteLeg:
        """Compute an authentic A* terrain-aware route leg between two stops."""
        req = MarswalkRouteRequest(
            start_lat=from_stop.lat,
            start_lon=from_stop.lon,
            dest_lat=to_stop.lat,
            dest_lon=to_stop.lon,
            preferred_source=source_id,
            slope_penalty_factor=slope_penalty_factor,
            max_slope_deg=max_slope_deg,
            max_search_nodes=max_search_nodes,
            route_name=f"Leg: {from_stop.name} -> {to_stop.name}",
        )
        try:
            route = MarswalkPlanner.plan_route(req)
            return PairwiseRouteLeg(
                leg_index=leg_index,
                from_stop_id=from_stop.stop_id,
                from_stop_name=from_stop.name,
                to_stop_id=to_stop.stop_id,
                to_stop_name=to_stop.name,
                from_coord=(from_stop.lat, from_stop.lon % 360.0),
                to_coord=(to_stop.lat, to_stop.lon % 360.0),
                route_id=route.route_id,
                is_feasible=True,
                surface_distance_m=route.total_surface_distance_m,
                horizontal_distance_m=route.total_horizontal_distance_m,
                optimization_cost=route.total_optimization_cost,
                elevation_gain_m=route.cumulative_elevation_gain_m,
                elevation_loss_m=route.cumulative_elevation_loss_m,
                min_elevation_m=route.min_elevation_m,
                max_elevation_m=route.max_elevation_m,
                max_slope_deg=route.max_route_slope_deg,
                mean_slope_deg=route.mean_route_slope_deg,
                slope_band_exposure_pct=route.slope_band_exposure_pct,
                source_dataset=route.source_dataset,
                geometry=route.geometry,
                error_message=None,
            )
        except Exception as e:
            logger.warning("Pairwise leg failed: %s -> %s: %s", from_stop.stop_id, to_stop.stop_id, e)
            return PairwiseRouteLeg(
                leg_index=leg_index,
                from_stop_id=from_stop.stop_id,
                from_stop_name=from_stop.name,
                to_stop_id=to_stop.stop_id,
                to_stop_name=to_stop.name,
                from_coord=(from_stop.lat, from_stop.lon % 360.0),
                to_coord=(to_stop.lat, to_stop.lon % 360.0),
                route_id="unreachable",
                is_feasible=False,
                surface_distance_m=0.0,
                horizontal_distance_m=0.0,
                optimization_cost=float("inf"),
                elevation_gain_m=0.0,
                elevation_loss_m=0.0,
                min_elevation_m=0.0,
                max_elevation_m=0.0,
                max_slope_deg=0.0,
                mean_slope_deg=0.0,
                slope_band_exposure_pct={},
                source_dataset=source_id,
                geometry={"type": "LineString", "coordinates": []},
                error_message=str(e),
            )

    @classmethod
    def optimize_stop_sequence(
        cls,
        start_stop: ScienceStop,
        dest_stop: ScienceStop,
        intermediate_stops: List[ScienceStop],
        pairwise_matrix: Dict[Tuple[str, str], PairwiseRouteLeg],
        strategy: str,
    ) -> Tuple[List[ScienceStop], str, bool, Dict[str, Any]]:
        """Determine optimal visit order for intermediate stops using actual A* leg costs.

        Mathematically accounts for directed asymmetric costs where Cost(u, v) != Cost(v, u).
        For K <= 4 intermediate stops, evaluates exact permutations as a reference oracle.
        For K > 4 stops, executes nearest-neighbor greedy initialization followed by
        asymmetric 2-opt local search with full directed path cost re-evaluation.

        Returns: (ordered_stops, effective_strategy, is_heuristic, opt_stats)
        """
        k = len(intermediate_stops)
        if k == 0:
            return [], strategy, False, {"iterations": 0, "optimality_gap_pct": 0.0}

        # Helper to calculate complete directed traverse optimization cost for a candidate ordering
        def eval_sequence_cost(seq: List[ScienceStop]) -> float:
            cost = 0.0
            prev = start_stop
            for st in seq:
                leg = pairwise_matrix.get((prev.stop_id, st.stop_id))
                if not leg or not leg.is_feasible:
                    return float("inf")
                cost += leg.optimization_cost
                prev = st
            final_leg = pairwise_matrix.get((prev.stop_id, dest_stop.stop_id))
            if not final_leg or not final_leg.is_feasible:
                return float("inf")
            cost += final_leg.optimization_cost
            return cost

        if strategy == "preserve_order" or k == 1:
            seq_cost = eval_sequence_cost(intermediate_stops)
            return intermediate_stops, ("preserve_order" if strategy == "preserve_order" else "exact_permutation"), False, {
                "initial_cost": round(seq_cost, 2),
                "final_cost": round(seq_cost, 2),
                "initial_nn_cost": round(seq_cost, 2),
                "two_opt_cost": round(seq_cost, 2),
                "exact_optimum_cost": round(seq_cost, 2),
                "iterations": 0,
                "reversals_accepted": 0,
                "optimality_gap_pct": 0.0,
                "permutations_evaluated": 1,
            }

        # Step 1: Nearest-Neighbor Initial Solution
        unvisited = list(intermediate_stops)
        current = start_stop
        nn_sequence: List[ScienceStop] = []

        while unvisited:
            best_next = None
            best_leg_cost = float("inf")
            for cand in unvisited:
                leg = pairwise_matrix.get((current.stop_id, cand.stop_id))
                if leg and leg.is_feasible and leg.optimization_cost < best_leg_cost:
                    best_leg_cost = leg.optimization_cost
                    best_next = cand

            if best_next is None:
                best_next = unvisited[0]

            nn_sequence.append(best_next)
            unvisited.remove(best_next)
            current = best_next

        nn_cost = eval_sequence_cost(nn_sequence)

        # Step 2: Asymmetric 2-Opt Local Search Improvement
        cur_sequence = list(nn_sequence)
        cur_cost = nn_cost
        two_opt_iters = 0
        reversals_accepted = 0
        improved = True

        while improved and two_opt_iters < 100:
            improved = False
            for i in range(len(cur_sequence) - 1):
                for j in range(i + 1, len(cur_sequence)):
                    # Reverse sub-sequence from index i to j
                    # In an asymmetric matrix, reversing internal vertices reverses directed edges
                    # Therefore, we re-evaluate the full directed sequence cost
                    candidate = cur_sequence[:i] + cur_sequence[i : j + 1][::-1] + cur_sequence[j + 1 :]
                    cand_cost = eval_sequence_cost(candidate)
                    if cand_cost < cur_cost - 1e-4:
                        cur_sequence = candidate
                        cur_cost = cand_cost
                        reversals_accepted += 1
                        improved = True
                        two_opt_iters += 1
                        break
                if improved:
                    break

        two_opt_cost = cur_cost
        two_opt_seq = cur_sequence

        # Step 3: Exact Permutation Reference Oracle for K <= 4
        if k <= 4:
            exact_best_seq = intermediate_stops
            exact_best_cost = eval_sequence_cost(intermediate_stops)
            for perm in itertools.permutations(intermediate_stops):
                cand = list(perm)
                cand_cost = eval_sequence_cost(cand)
                if cand_cost < exact_best_cost:
                    exact_best_cost = cand_cost
                    exact_best_seq = cand

            gap_pct = 0.0
            if exact_best_cost > 0.0 and math.isfinite(two_opt_cost) and math.isfinite(exact_best_cost):
                gap_pct = max(0.0, ((two_opt_cost - exact_best_cost) / exact_best_cost) * 100.0)

            opt_stats = {
                "initial_nn_cost": round(nn_cost, 2),
                "two_opt_cost": round(two_opt_cost, 2),
                "exact_optimum_cost": round(exact_best_cost, 2),
                "optimality_gap_pct": round(gap_pct, 2),
                "reversals_accepted": reversals_accepted,
                "iterations": two_opt_iters,
                "permutations_evaluated": math.factorial(k),
            }

            if strategy == "nearest_neighbor":
                return nn_sequence, "nearest_neighbor", True, opt_stats
            # optimize_tsp selects the provably exact sequence for K <= 4
            return exact_best_seq, "exact_permutation", False, opt_stats

        # For K > 4 stops
        improvement_pct = 0.0
        if nn_cost > 0.0 and math.isfinite(nn_cost) and math.isfinite(two_opt_cost):
            improvement_pct = max(0.0, ((nn_cost - two_opt_cost) / nn_cost) * 100.0)

        opt_stats = {
            "initial_nn_cost": round(nn_cost, 2),
            "final_2opt_cost": round(two_opt_cost, 2),
            "cost_improvement_pct": round(improvement_pct, 2),
            "reversals_accepted": reversals_accepted,
            "iterations": two_opt_iters,
        }

        if strategy == "nearest_neighbor":
            return nn_sequence, "nearest_neighbor", True, opt_stats

        return two_opt_seq, "nearest_neighbor_2opt", True, opt_stats

    @classmethod
    def plan_multi_stop_traverse(cls, request: MultiStopRouteRequest) -> MultiStopTraverseResponse:
        """Plan a fully connected, terrain-optimized multi-stop science traverse."""
        t0 = time.perf_counter()

        # Step 1: Resolve all stops (merging explicit stops and discovery_ids)
        stops = cls.resolve_all_stops(request)

        # Step 2: Select common DEM covering start, destination, and all intermediate stops
        source = cls.select_common_source(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            dest_lat=request.dest_lat,
            dest_lon=request.dest_lon,
            stops=stops,
            preferred_source=request.preferred_source,
        )
        source_id = source["source_id"]

        # Step 3: Check deterministic multi-stop cache
        req_hash = compute_multi_stop_hash(request, source_id)
        cached_id = _MULTI_STOP_HASH_TO_ID.get(req_hash)
        if cached_id and cached_id in _MULTI_STOP_CACHE:
            logger.info("Serving multi-stop traverse from cache: %s", cached_id)
            return _MULTI_STOP_CACHE[cached_id]

        start_stop = ScienceStop(
            stop_id="origin-start",
            name=request.start_name or "Origin / Base Camp",
            lat=request.start_lat,
            lon=request.start_lon,
            is_mandatory=True,
            description="Traverse departure station",
        )
        dest_stop = ScienceStop(
            stop_id="terminal-destination",
            name=request.dest_name or "Final Destination",
            lat=request.dest_lat,
            lon=request.dest_lon,
            is_mandatory=True,
            description="Traverse conclusion point",
        )

        all_nodes = [start_stop] + stops + [dest_stop]
        pairwise_matrix: Dict[Tuple[str, str], PairwiseRouteLeg] = {}
        legs_computed = 0

        # Step 4: Compute all pairwise directed routes needed
        # (Start -> Stops), (Stops -> Stops), (Stops -> Dest), and (Start -> Dest if no stops)
        pairs_to_compute: List[Tuple[ScienceStop, ScienceStop]] = []

        if not stops:
            pairs_to_compute.append((start_stop, dest_stop))
        else:
            for s in stops:
                pairs_to_compute.append((start_stop, s))
                pairs_to_compute.append((s, dest_stop))
            for s1 in stops:
                for s2 in stops:
                    if s1.stop_id != s2.stop_id:
                        pairs_to_compute.append((s1, s2))

        for idx, (u, v) in enumerate(pairs_to_compute):
            leg = cls.compute_pairwise_leg(
                from_stop=u,
                to_stop=v,
                source_id=source_id,
                slope_penalty_factor=request.slope_penalty_factor,
                max_slope_deg=request.max_slope_deg,
                max_search_nodes=request.max_search_nodes,
                leg_index=idx,
            )
            pairwise_matrix[(u.stop_id, v.stop_id)] = leg
            legs_computed += 1

        # Check for unreachable stops and exclude optional ones
        unreachable = []
        reachable_stops = []
        for s in stops:
            # Must be reachable from start or at least one other stop, and must be able to reach dest or another stop
            can_enter = any(
                leg.is_feasible
                for k, leg in pairwise_matrix.items()
                if k[1] == s.stop_id and k[0] != s.stop_id
            )
            can_exit = any(
                leg.is_feasible
                for k, leg in pairwise_matrix.items()
                if k[0] == s.stop_id and k[1] != s.stop_id
            )
            if not (can_enter and can_exit):
                unreachable.append({
                    "stop_id": s.stop_id,
                    "name": s.name,
                    "lat": s.lat,
                    "lon": s.lon,
                    "is_mandatory": s.is_mandatory,
                    "reason": "Impassable terrain (slope > max_slope_deg or NoData) blocks route entrance or exit.",
                })
                if s.is_mandatory:
                    lat_str = f"{abs(s.lat):.4f}°S" if s.lat < 0 else f"{s.lat:.4f}°N"
                    lon_str = f"{s.lon % 360.0:.4f}°E"
                    raise ValueError(
                        f"Mandatory science stop '{s.name}' ({s.stop_id}) at ({lat_str}, {lon_str}) "
                        f"is unreachable within slope threshold {request.max_slope_deg}° or DEM coverage."
                    )
            else:
                reachable_stops.append(s)

        stops = reachable_stops

        # If all stops were filtered out or empty, ensure direct start->dest leg exists in pairwise_matrix
        if not stops and (start_stop.stop_id, dest_stop.stop_id) not in pairwise_matrix:
            direct_leg = cls.compute_pairwise_leg(
                from_stop=start_stop,
                to_stop=dest_stop,
                source_id=source_id,
                slope_penalty_factor=request.slope_penalty_factor,
                max_slope_deg=request.max_slope_deg,
                max_search_nodes=request.max_search_nodes,
                leg_index=legs_computed,
            )
            pairwise_matrix[(start_stop.stop_id, dest_stop.stop_id)] = direct_leg
            legs_computed += 1

        # Step 5: Bounded TSP Optimization of stop ordering
        ordered_intermediate, effective_strategy, is_heuristic, opt_stats = cls.optimize_stop_sequence(
            start_stop=start_stop,
            dest_stop=dest_stop,
            intermediate_stops=stops,
            pairwise_matrix=pairwise_matrix,
            strategy=request.optimization_strategy,
        )

        # Step 6: Construct connected sequence and collect active route legs
        final_sequence = [start_stop] + ordered_intermediate + [dest_stop]
        active_legs: List[PairwiseRouteLeg] = []
        connected_coordinates: List[List[float]] = []

        total_surf_dist = 0.0
        total_horiz_dist = 0.0
        total_opt_cost = 0.0
        total_gain = 0.0
        total_loss = 0.0
        max_slope = 0.0
        weighted_slope_sum = 0.0
        combined_exposure_meters = {"low": 0.0, "moderate": 0.0, "high": 0.0, "very_high": 0.0, "unknown": 0.0}

        for leg_i in range(len(final_sequence) - 1):
            u = final_sequence[leg_i]
            v = final_sequence[leg_i + 1]
            leg = pairwise_matrix.get((u.stop_id, v.stop_id))

            if not leg or not leg.is_feasible:
                raise RuntimeError(
                    f"Optimized traverse failed: Infeasible leg between '{u.name}' and '{v.name}'. "
                    f"Details: {leg.error_message if leg else 'Missing leg'}"
                )

            # Re-index leg to match traverse sequence
            active_leg = leg.model_copy(update={"leg_index": leg_i})
            active_legs.append(active_leg)

            total_surf_dist += active_leg.surface_distance_m
            total_horiz_dist += active_leg.horizontal_distance_m
            total_opt_cost += active_leg.optimization_cost
            total_gain += active_leg.elevation_gain_m
            total_loss += active_leg.elevation_loss_m
            max_slope = max(max_slope, active_leg.max_slope_deg)
            weighted_slope_sum += active_leg.surface_distance_m * active_leg.mean_slope_deg

            # Aggregate exposure
            for cat, pct in active_leg.slope_band_exposure_pct.items():
                if cat in combined_exposure_meters:
                    combined_exposure_meters[cat] += (pct / 100.0) * active_leg.surface_distance_m

            # Connect GeoJSON coordinates without duplicating junction vertices
            leg_coords = active_leg.geometry.get("coordinates", [])
            if leg_coords:
                if not connected_coordinates:
                    connected_coordinates.extend(leg_coords)
                else:
                    # Append coordinates skipping first vertex if identical to last junction vertex
                    if leg_coords[0] == connected_coordinates[-1]:
                        connected_coordinates.extend(leg_coords[1:])
                    else:
                        connected_coordinates.extend(leg_coords)

        # Distance-weighted aggregated mean slope
        mean_slope = (weighted_slope_sum / total_surf_dist) if total_surf_dist > 0.0 else 0.0

        # Exposure percentages
        combined_exposure_pct = {}
        if total_surf_dist > 0.0:
            for cat, dist_m in combined_exposure_meters.items():
                combined_exposure_pct[cat] = round((dist_m / total_surf_dist) * 100.0, 2)
        else:
            combined_exposure_pct = {"low": 100.0, "moderate": 0.0, "high": 0.0, "very_high": 0.0, "unknown": 0.0}

        min_elev = min(leg.min_elevation_m for leg in active_legs) if active_legs else 0.0
        max_elev = max(leg.max_elevation_m for leg in active_legs) if active_legs else 0.0

        total_ms = (time.perf_counter() - t0) * 1000.0
        traverse_id = f"mst-{uuid.uuid4().hex[:12]}"
        title = request.traverse_name or f"Marswalk Multi-Stop Traverse ({source_id})"

        status_str = "partial" if unreachable else "success"

        response = MultiStopTraverseResponse(
            traverse_id=traverse_id,
            status=status_str,
            traverse_name=title,
            start_stop=start_stop,
            dest_stop=dest_stop,
            ordered_stops=ordered_intermediate,
            legs=active_legs,
            total_surface_distance_m=round(total_surf_dist, 2),
            total_horizontal_distance_m=round(total_horiz_dist, 2),
            total_optimization_cost=round(total_opt_cost, 2),
            cumulative_elevation_gain_m=round(total_gain, 2),
            cumulative_elevation_loss_m=round(total_loss, 2),
            min_elevation_m=round(min_elev, 2),
            max_elevation_m=round(max_elev, 2),
            max_route_slope_deg=round(max_slope, 2),
            mean_route_slope_deg=round(mean_slope, 2),
            slope_band_exposure_pct=combined_exposure_pct,
            unknown_data_exposure_pct=combined_exposure_pct.get("unknown", 0.0),
            source_dataset=source_id,
            instrument=source["instrument"],
            tier=source["tier"],
            native_resolution_desc=source["pixel_spacing_desc"],
            connected_geometry={
                "type": "LineString",
                "coordinates": connected_coordinates,
            },
            optimization_strategy=effective_strategy,
            is_heuristic_solution=is_heuristic,
            unreachable_stops=unreachable,
            computation_metrics={
                "duration_ms": round(total_ms, 2),
                "pairwise_legs_computed": legs_computed,
                "two_opt_iterations": opt_stats.get("iterations", 0),
                "total_stops_visited": len(final_sequence),
                "algorithm_version": MARSWALK_ALGORITHM_VERSION,
                "cost_function_version": MARSWALK_COST_FUNCTION_VERSION,
                "derivative_version": MARSWALK_DERIVATIVE_VERSION,
                "optimization_stats": opt_stats,
            },
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
        )

        # Cache in memory
        if len(_MULTI_STOP_CACHE) >= _MAX_MULTI_STOP_CACHE_SIZE:
            oldest_id = next(iter(_MULTI_STOP_CACHE))
            _MULTI_STOP_CACHE.pop(oldest_id, None)
            evict_hashes = [h for h, tid in _MULTI_STOP_HASH_TO_ID.items() if tid == oldest_id]
            for h in evict_hashes:
                _MULTI_STOP_HASH_TO_ID.pop(h, None)

        _MULTI_STOP_CACHE[traverse_id] = response
        _MULTI_STOP_HASH_TO_ID[req_hash] = traverse_id

        return response

    @classmethod
    def get_metadata(cls) -> MultiStopMetadataResponse:
        """Return engine metadata for multi-stop science traverse optimization."""
        return MultiStopMetadataResponse(
            supported_strategies=[
                {
                    "strategy": "optimize_tsp",
                    "description": "Calculates provably exact stop sequence for K <= 4 intermediate stops; runs nearest-neighbor followed by 2-opt local search heuristic for K > 4 stops.",
                },
                {
                    "strategy": "nearest_neighbor",
                    "description": "Greedy sequential traversal selecting the next closest unvisited science stop based on actual A* terrain cost.",
                },
                {
                    "strategy": "preserve_order",
                    "description": "Traverses science stops in the exact user-specified order without TSP reordering.",
                },
            ],
            max_allowed_stops=12,
            cost_function_definition="Cost(u, v) = d_surface * [1.0 + beta * (theta_v / 15.0)^2]",
            optimization_objective="Minimize sum of actual terrain-aware A* leg costs: C_total = Cost(S, W_1) + sum(Cost(W_i, W_{i+1})) + Cost(W_k, D)",
            curated_presets=CURATED_MULTI_STOP_PRESETS,
            engine_versions={
                "algorithm_version": MARSWALK_ALGORITHM_VERSION,
                "cost_function_version": MARSWALK_COST_FUNCTION_VERSION,
                "derivative_version": MARSWALK_DERIVATIVE_VERSION,
            },
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
        )
