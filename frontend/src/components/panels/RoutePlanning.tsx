"use client";

import React, { useState } from "react";
import { planMarsRoute, compareMarsRouteAlgorithms } from "@/lib/api";
import { 
  RoutePlanRequest, 
  RoutePlanResponse, 
  RouteComparisonResponse,
  PathfindingAlgorithm,
  NeighborConnectivity,
} from "@/lib/types";
import { MarswalkRoutePlanner } from "./MarswalkRoutePlanner";

// Geologically validated mission targets inside MOLA 128 tile megt00n000hb:
// Tile footprint: Lat [-44.0°, 0.0°], Lon [0.0°, 90.0°E]
const PRESET_TARGETS = [
  {
    name: "Sinus Meridiani Plain to Mawrth Vallis Entrance",
    start: { lat: -2.00, lon: 5.00 },
    dest: { lat: -2.15, lon: 5.18 },
    desc: "Traverse from hematite-rich plains toward dissected phyllosilicate channels.",
  },
  {
    name: "Margaritifer Terra Crater Corridor",
    start: { lat: -4.00, lon: 8.00 },
    dest: { lat: -4.08, lon: 8.08 },
    desc: "Route along ancient fluvial valley networks avoiding crater rim scarps.",
  },
  {
    name: "Schiaparelli Basin Approach Corridor",
    start: { lat: -3.00, lon: 15.00 },
    dest: { lat: -3.10, lon: 15.15 },
    desc: "Traverse smooth intercrater plains navigating around localized relief steps.",
  },
];

export const RoutePlanning: React.FC = () => {
  const [routingMode, setRoutingMode] = useState<"marswalk" | "mola128">("marswalk");
  const [startLat, setStartLat] = useState<number>(-2.00);
  const [startLon, setStartLon] = useState<number>(5.00);
  const [destLat, setDestLat] = useState<number>(-2.15);
  const [destLon, setDestLon] = useState<number>(5.18);

  const [algorithm, setAlgorithm] = useState<"astar" | "dijkstra" | "compare">("compare");
  const [connectivity, setConnectivity] = useState<4 | 8>(8);
  const [maxSlope, setMaxSlope] = useState<number>(15.0);
  const [weightSlope, setWeightSlope] = useState<number>(2.0);
  const [weightRoughness, setWeightRoughness] = useState<number>(1.5);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [singleResult, setSingleResult] = useState<RoutePlanResponse | null>(null);
  const [comparisonResult, setComparisonResult] = useState<RouteComparisonResponse | null>(null);

  const handleSelectPreset = (preset: typeof PRESET_TARGETS[0]) => {
    setStartLat(preset.start.lat);
    setStartLon(preset.start.lon);
    setDestLat(preset.dest.lat);
    setDestLon(preset.dest.lon);
    setError(null);
  };

  const handlePlanRoute = async () => {
    try {
      setLoading(true);
      setError(null);
      setSingleResult(null);
      setComparisonResult(null);

      const request: RoutePlanRequest = {
        start_lat: Number(startLat),
        start_lon: Number(startLon),
        dest_lat: Number(destLat),
        dest_lon: Number(destLon),
        dataset_id: "mola-megdr-128",
        algorithm: algorithm === "compare" ? "astar" : algorithm,
        connectivity: connectivity,
        max_slope_deg: Number(maxSlope),
        cost_weights: {
          weight_slope: Number(weightSlope),
          weight_roughness: Number(weightRoughness),
          weight_relief: 1.0,
          weight_complexity: 1.5,
        },
      };

      if (algorithm === "compare") {
        const comp = await compareMarsRouteAlgorithms(request);
        setComparisonResult(comp);
      } else {
        const plan = await planMarsRoute(request);
        setSingleResult(plan);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Route planning failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 text-xs font-mono text-slate-300">
      {/* Engine Mode Tabs */}
      <div className="flex items-center space-x-2 border-b border-[#23293f] pb-3">
        <button
          type="button"
          onClick={() => setRoutingMode("marswalk")}
          className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all ${
            routingMode === "marswalk"
              ? "bg-orange-500 text-black shadow-md shadow-orange-500/20"
              : "bg-[#101426] text-slate-400 hover:text-white border border-[#23293f]"
          }`}
        >
          <span>🥾</span>
          <span>Marswalk Engine (Multi-Tier Terrain — Phase 8.8.2)</span>
        </button>
        <button
          type="button"
          onClick={() => setRoutingMode("mola128")}
          className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all ${
            routingMode === "mola128"
              ? "bg-orange-500 text-black shadow-md shadow-orange-500/20"
              : "bg-[#101426] text-slate-400 hover:text-white border border-[#23293f]"
          }`}
        >
          <span>🛰️</span>
          <span>Regional MOLA 128 Engine (Comparative A* / Dijkstra)</span>
        </button>
      </div>

      {routingMode === "marswalk" ? (
        <MarswalkRoutePlanner />
      ) : (
        <>
          {/* Header and Scope Definition */}
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#23293f] pb-2 gap-2">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base">🛰️</span>
                <span className="font-bold text-white uppercase tracking-wider text-sm">
                  Terrain-Constrained Marswalk Routing (A* & Dijkstra)
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Phase 6 Research Prototype: Geodesic Graph Traversal on Validated MOLA 128 ppd Tile (EPSG:104905)
              </p>
            </div>
            <span className="px-2 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 rounded text-[10px]">
              Footprint: Lat [-44°, 0°], Lon [0°, 90°E]
            </span>
          </div>

      {/* Preset Geological Targets */}
      <div className="space-y-1.5 bg-slate-950/50 p-2.5 rounded border border-slate-800">
        <span className="text-[10px] uppercase font-bold text-cyan-400">
          Geological Target Presets (Inside Validated Footprint):
        </span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {PRESET_TARGETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSelectPreset(preset)}
              className="text-left p-2 rounded bg-slate-900/80 hover:bg-slate-800 border border-slate-800 transition-colors"
            >
              <div className="font-semibold text-slate-200 text-[11px] truncate">{preset.name}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{preset.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Coordinate and Parameter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-slate-900/70 p-3 rounded-lg border border-slate-800">
        {/* Coordinates */}
        <div className="space-y-2 md:col-span-2">
          <span className="text-[11px] text-slate-400 font-bold block uppercase">Mission Coordinates:</span>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-500 block">Start Lat (°)</label>
              <input
                type="number"
                step="0.01"
                value={startLat}
                onChange={(e) => setStartLat(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 block">Start Lon (°E)</label>
              <input
                type="number"
                step="0.01"
                value={startLon}
                onChange={(e) => setStartLon(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 block">Dest Lat (°)</label>
              <input
                type="number"
                step="0.01"
                value={destLat}
                onChange={(e) => setDestLat(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 block">Dest Lon (°E)</label>
              <input
                type="number"
                step="0.01"
                value={destLon}
                onChange={(e) => setDestLon(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
              />
            </div>
          </div>
        </div>

        {/* Algorithm & Connectivity */}
        <div className="space-y-2">
          <span className="text-[11px] text-slate-400 font-bold block uppercase">Algorithm & Mesh:</span>
          <div>
            <label className="text-[10px] text-slate-500 block">Pathfinding Engine</label>
            <select
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
            >
              <option value="compare">Compare A* & Dijkstra</option>
              <option value="astar">A* (Euclidean Lower Bound)</option>
              <option value="dijkstra">Dijkstra (Exact Baseline)</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block">Neighbor Connectivity</label>
            <select
              value={connectivity}
              onChange={(e) => setConnectivity(parseInt(e.target.value) as 4 | 8)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
            >
              <option value={8}>8-Direction (Orthogonal + Diagonal)</option>
              <option value={4}>4-Direction (Orthogonal Only)</option>
            </select>
          </div>
        </div>

        {/* Constraints */}
        <div className="space-y-2">
          <span className="text-[11px] text-slate-400 font-bold block uppercase">Constraints & Weights:</span>
          <div>
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Max Slope Limit</span>
              <span className="text-amber-400 font-bold">{maxSlope}°</span>
            </div>
            <input
              type="range"
              min="5"
              max="30"
              value={maxSlope}
              onChange={(e) => setMaxSlope(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          <div>
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-500">Slope Penalty Weight</span>
              <span className="text-cyan-400 font-bold">{weightSlope}x</span>
            </div>
            <input
              type="range"
              min="0"
              max="5"
              step="0.5"
              value={weightSlope}
              onChange={(e) => setWeightSlope(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {/* Plan Button */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handlePlanRoute}
          disabled={loading}
          className="px-4 py-2 rounded bg-orange-600 hover:bg-orange-500 disabled:bg-slate-800 text-white font-bold text-xs transition-colors flex items-center gap-2"
        >
          {loading ? "Computing Terrain Graph..." : "🚀 Compute Terrain-Constrained Marswalk"}
        </button>
        <span className="text-[10px] text-slate-500">
          Source: MOLA 128 ppd (463.08 m/px) • C = L · (1 + ws·fs + wr·fr + wl·fl + wc·fc)
        </span>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300">
          <strong>Routing Request Rejected:</strong> {error}
        </div>
      )}

      {/* COMPARISON RESULTS TABLE */}
      {comparisonResult && (
        <div className="space-y-3 bg-slate-900/80 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-white uppercase text-xs">
              Algorithm Comparison: A* vs Dijkstra Baseline
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
              Optimal Cost Match: {comparisonResult.cost_difference_pct.toFixed(4)}% Difference
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                  <th className="py-1 px-2">Metric</th>
                  <th className="py-1 px-2 text-cyan-400">A* (Euclidean Lower Bound)</th>
                  <th className="py-1 px-2 text-purple-400">Dijkstra (Exact Baseline)</th>
                  <th className="py-1 px-2 text-emerald-400">Comparison Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                <tr>
                  <td className="py-1 px-2 text-slate-400">Total Path Cost</td>
                  <td className="py-1 px-2 text-slate-200">{comparisonResult.astar_route.metrics.total_cost.toFixed(2)}</td>
                  <td className="py-1 px-2 text-slate-200">{comparisonResult.dijkstra_route.metrics.total_cost.toFixed(2)}</td>
                  <td className="py-1 px-2 text-emerald-400">Identical (within Δ {comparisonResult.cost_difference})</td>
                </tr>
                <tr>
                  <td className="py-1 px-2 text-slate-400">Ground Path Distance</td>
                  <td className="py-1 px-2 text-slate-200">{(comparisonResult.astar_route.metrics.total_distance_m / 1000).toFixed(2)} km</td>
                  <td className="py-1 px-2 text-slate-200">{(comparisonResult.dijkstra_route.metrics.total_distance_m / 1000).toFixed(2)} km</td>
                  <td className="py-1 px-2 text-slate-300">Δ {comparisonResult.distance_difference_m} m</td>
                </tr>
                <tr>
                  <td className="py-1 px-2 text-slate-400">Nodes Expanded</td>
                  <td className="py-1 px-2 text-cyan-300">{comparisonResult.astar_route.metrics.nodes_expanded.toLocaleString()}</td>
                  <td className="py-1 px-2 text-purple-300">{comparisonResult.dijkstra_route.metrics.nodes_expanded.toLocaleString()}</td>
                  <td className="py-1 px-2 text-emerald-400">{comparisonResult.nodes_expanded_ratio.toFixed(1)}x search space reduction</td>
                </tr>
                <tr>
                  <td className="py-1 px-2 text-slate-400">Computation Time</td>
                  <td className="py-1 px-2 text-cyan-300">{comparisonResult.astar_route.metrics.search_duration_ms.toFixed(1)} ms</td>
                  <td className="py-1 px-2 text-purple-300">{comparisonResult.dijkstra_route.metrics.search_duration_ms.toFixed(1)} ms</td>
                  <td className="py-1 px-2 text-emerald-400">{comparisonResult.runtime_speedup_factor.toFixed(1)}x speedup</td>
                </tr>
                <tr>
                  <td className="py-1 px-2 text-slate-400">Max Slope / Elevation Climb</td>
                  <td className="py-1 px-2 text-slate-200">
                    {comparisonResult.astar_route.metrics.max_slope_deg}° / +{comparisonResult.astar_route.metrics.cumulative_elevation_gain_m}m
                  </td>
                  <td className="py-1 px-2 text-slate-200">
                    {comparisonResult.dijkstra_route.metrics.max_slope_deg}° / +{comparisonResult.dijkstra_route.metrics.cumulative_elevation_gain_m}m
                  </td>
                  <td className="py-1 px-2 text-slate-300">Max slope &lt; {maxSlope}° constraint satisfied</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="p-2 bg-slate-950/60 rounded border border-slate-800 text-[11px] text-slate-300">
            {comparisonResult.scientific_synthesis}
          </div>
        </div>
      )}

      {/* SINGLE ROUTE RESULTS CARD */}
      {singleResult && (
        <div className="space-y-3 bg-slate-900/80 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-white uppercase text-xs">
              Candidate Marswalk Traverse ({singleResult.algorithm.toUpperCase()})
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
              Verified: {singleResult.waypoints.length} Waypoints
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Path Distance</span>
              <span className="text-white font-bold text-sm">{(singleResult.metrics.total_distance_m / 1000).toFixed(2)} km</span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Elevation Change</span>
              <span className="text-cyan-300 font-bold text-sm">
                +{singleResult.metrics.cumulative_elevation_gain_m}m / -{singleResult.metrics.cumulative_elevation_loss_m}m
              </span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Max Slope Encountered</span>
              <span className="text-amber-300 font-bold text-sm">{singleResult.metrics.max_slope_deg}°</span>
              <span className="text-[9px] text-slate-500">Threshold: {singleResult.max_slope_threshold_deg}°</span>
            </div>
            <div className="bg-slate-950 p-2 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Computation Time</span>
              <span className="text-emerald-300 font-bold text-sm">{singleResult.metrics.search_duration_ms.toFixed(1)} ms</span>
              <span className="text-[9px] text-slate-500">{singleResult.metrics.nodes_expanded} nodes</span>
            </div>
          </div>

          <div className="p-2 bg-slate-950/60 rounded border border-slate-800 text-[11px] text-slate-300">
            {singleResult.explanation}
          </div>
        </div>
      )}

          {/* Prominent Scientific Disclaimer */}
          <div className="p-2.5 bg-slate-950/90 border border-amber-800/60 rounded text-[11px] text-amber-300/90 italic">
            <strong>Scientific Limitation &amp; Safety Disclaimer:</strong> MARS-X route planning is an experimental terrain-cost simulation based on the selected digital terrain model. It does NOT establish astronaut safety, EVA feasibility, obstacle clearance, or operational navigability. Results are limited by source resolution (463 m/px), coverage, and data uncertainty.
          </div>
        </>
      )}
    </div>
  );
};
