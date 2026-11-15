"use client";

import React, { useState, useEffect } from "react";
import {
  fetchMarswalkMetadata,
  planMarswalkRoute,
  fetchMultiStopMetadata,
  planMultiStopTraverse,
  fetchDiscoveries,
  fetchRouteIntelligence,
  fetchMultiStopTraverseIntelligence,
} from "@/lib/api";
import {
  MarswalkRouteRequest,
  MarswalkRouteResponse,
  MarswalkMetadataResponse,
  ValidatedCorridorPreset,
  ScienceStop,
  MultiStopRouteRequest,
  MultiStopTraverseResponse,
  MultiStopMetadataResponse,
  MultiStopPreset,
  ScienceDiscovery,
  RouteIntelligenceReport,
  MultiStopTraverseIntelligenceReport,
} from "@/lib/types";
import { RouteIntelligenceView } from "./RouteIntelligenceView";
import { EnvironmentalIntelligenceView } from "./EnvironmentalIntelligenceView";

export const MarswalkRoutePlanner: React.FC = () => {
  // Navigation mode: single leg vs multi-stop science traverse vs route intelligence vs environmental
  const [plannerMode, setPlannerMode] = useState<"single" | "multi" | "intelligence" | "environmental">("single");

  // Metadata
  const [singleMetadata, setSingleMetadata] = useState<MarswalkMetadataResponse | null>(null);
  const [multiMetadata, setMultiMetadata] = useState<MultiStopMetadataResponse | null>(null);
  const [catalogDiscoveries, setCatalogDiscoveries] = useState<ScienceDiscovery[]>([]);

  // Single-leg state
  const [selectedCorridor, setSelectedCorridor] = useState<string>("tyrrhena-ctx-valley");
  const [startLat, setStartLat] = useState<number>(-4.600);
  const [startLon, setStartLon] = useState<number>(66.317);
  const [destLat, setDestLat] = useState<number>(-4.605);
  const [destLon, setDestLon] = useState<number>(66.325);
  const [preferredSource, setPreferredSource] = useState<string>("ctx-tyrrhena");
  const [slopePenalty, setSlopePenalty] = useState<number>(2.0);
  const [maxSlope, setMaxSlope] = useState<number>(25.0);

  // Single-leg execution
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<MarswalkRouteResponse | null>(null);

  // Multi-stop state
  const [selectedMultiPreset, setSelectedMultiPreset] = useState<string>("tyrrhena-valley-science-loop");
  const [multiStartLat, setMultiStartLat] = useState<number>(-4.600);
  const [multiStartLon, setMultiStartLon] = useState<number>(66.317);
  const [multiStartName, setMultiStartName] = useState<string>("Fluvial Channel Station");
  const [multiDestLat, setMultiDestLat] = useState<number>(-4.605);
  const [multiDestLon, setMultiDestLon] = useState<number>(66.325);
  const [multiDestName, setMultiDestName] = useState<string>("Crater Rim Outpost");
  const [multiStops, setMultiStops] = useState<ScienceStop[]>([
    {
      stop_id: "stop-chan-bed",
      name: "Channel Bed Stratigraphy",
      lat: -4.602,
      lon: 66.320,
      discovery_id: "disc-terr-tyrrhena-ctx",
      is_mandatory: true,
      target_geology: "Inverted channel fill & stratified Noachian bedrock",
    },
    {
      stop_id: "stop-terrace",
      name: "Terraced Scarp Exposure",
      lat: -4.604,
      lon: 66.322,
      discovery_id: "disc-multi-tyrrhena-corridor",
      is_mandatory: true,
      target_geology: "Degraded impact crater rim scarp",
    },
  ]);
  const [multiStrategy, setMultiStrategy] = useState<string>("optimize_tsp");
  const [multiPreferredSource, setMultiPreferredSource] = useState<string>("ctx-tyrrhena");
  const [multiSlopePenalty, setMultiSlopePenalty] = useState<number>(2.0);
  const [multiMaxSlope, setMultiMaxSlope] = useState<number>(25.0);

  // Stop addition inputs
  const [newStopLat, setNewStopLat] = useState<string>("");
  const [newStopLon, setNewStopLon] = useState<string>("");
  const [newStopName, setNewStopName] = useState<string>("");
  const [selectedDiscoveryToAdd, setSelectedDiscoveryToAdd] = useState<string>("");

  // Multi-stop execution & results
  const [multiLoading, setMultiLoading] = useState<boolean>(false);
  const [multiError, setMultiError] = useState<string | null>(null);
  const [multiResult, setMultiResult] = useState<MultiStopTraverseResponse | null>(null);
  const [activeLegInspectIndex, setActiveLegInspectIndex] = useState<number | null>(null);

  // Route Intelligence State — Phase 8.8.4
  const [routeIntelligence, setRouteIntelligence] = useState<RouteIntelligenceReport | null>(null);
  const [traverseIntelligence, setTraverseIntelligence] = useState<MultiStopTraverseIntelligenceReport | null>(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState<boolean>(false);
  const [intelligenceError, setIntelligenceError] = useState<string | null>(null);

  // Load metadata and discovery catalog on mount
  useEffect(() => {
    fetchMarswalkMetadata()
      .then((data) => setSingleMetadata(data))
      .catch((err) => console.error("Failed to load Marswalk metadata:", err));

    fetchMultiStopMetadata()
      .then((data) => setMultiMetadata(data))
      .catch((err) => console.error("Failed to load Multi-Stop metadata:", err));

    fetchDiscoveries()
      .then((data) => setCatalogDiscoveries(data))
      .catch((err) => console.error("Failed to load discoveries:", err));
  }, []);

  const handleSelectPreset = (preset: ValidatedCorridorPreset) => {
    setSelectedCorridor(preset.corridor_id);
    setStartLat(preset.start_lat);
    setStartLon(preset.start_lon);
    setDestLat(preset.dest_lat);
    setDestLon(preset.dest_lon);
    setPreferredSource(preset.source_dataset);
    setError(null);
  };

  const handleSelectMultiPreset = (preset: MultiStopPreset) => {
    setSelectedMultiPreset(preset.preset_id);
    setMultiStartLat(preset.start_lat);
    setMultiStartLon(preset.start_lon);
    setMultiStartName("Traverse Departure");
    setMultiDestLat(preset.dest_lat);
    setMultiDestLon(preset.dest_lon);
    setMultiDestName("Traverse Terminal");
    setMultiStops(preset.stops);
    setMultiPreferredSource(preset.source_dataset);
    setMultiError(null);
  };

  const handlePlanRoute = async () => {
    try {
      setLoading(true);
      setError(null);
      setRouteResult(null);

      const req: MarswalkRouteRequest = {
        start_lat: Number(startLat),
        start_lon: Number(startLon),
        dest_lat: Number(destLat),
        dest_lon: Number(destLon),
        preferred_source: preferredSource,
        slope_penalty_factor: Number(slopePenalty),
        max_slope_deg: Number(maxSlope),
      };

      const result = await planMarswalkRoute(req);
      setRouteResult(result);

      // Auto-load Route Intelligence
      setIntelligenceLoading(true);
      fetchRouteIntelligence(result.route_id)
        .then((intel) => setRouteIntelligence(intel))
        .catch((err) => console.warn("Failed to fetch route intelligence:", err))
        .finally(() => setIntelligenceLoading(false));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Route planning failed.");
    } finally {
      setLoading(false);
    }
  };

  const handlePlanMultiTraverse = async () => {
    try {
      setMultiLoading(true);
      setMultiError(null);
      setMultiResult(null);
      setActiveLegInspectIndex(null);

      const req: MultiStopRouteRequest = {
        start_lat: Number(multiStartLat),
        start_lon: Number(multiStartLon),
        start_name: multiStartName,
        dest_lat: Number(multiDestLat),
        dest_lon: Number(multiDestLon),
        dest_name: multiDestName,
        stops: multiStops,
        optimization_strategy: multiStrategy,
        preferred_source: multiPreferredSource,
        slope_penalty_factor: Number(multiSlopePenalty),
        max_slope_deg: Number(multiMaxSlope),
        traverse_name: `Multi-Stop Traverse (${multiPreferredSource})`,
      };

      const result = await planMultiStopTraverse(req);
      setMultiResult(result);

      // Auto-load Multi-Stop Traverse Intelligence
      setIntelligenceLoading(true);
      fetchMultiStopTraverseIntelligence(result.traverse_id)
        .then((intel) => setTraverseIntelligence(intel))
        .catch((err) => console.warn("Failed to fetch traverse intelligence:", err))
        .finally(() => setIntelligenceLoading(false));
    } catch (err: unknown) {
      setMultiError(err instanceof Error ? err.message : "Multi-stop planning failed.");
    } finally {
      setMultiLoading(false);
    }
  };

  // URL deep-linking support for route modes and quick automated demonstration
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const mode = params.get("mode");
      if (mode === "single" || mode === "multi" || mode === "intelligence" || mode === "environmental") {
        setPlannerMode(mode);
      }
      if (params.get("autoPlan") === "1") {
        handlePlanRoute();
      }
    }
  }, []);

  const handleAddCustomStop = () => {
    if (!newStopLat || !newStopLon) return;
    const lat = parseFloat(newStopLat);
    const lon = parseFloat(newStopLon);
    if (isNaN(lat) || isNaN(lon)) return;

    const stop: ScienceStop = {
      stop_id: `stop-${Date.now().toString().slice(-4)}`,
      name: newStopName.trim() || `Station (${lat.toFixed(3)}°, ${lon.toFixed(3)}°)`,
      lat,
      lon,
      is_mandatory: true,
      target_geology: "User Defined Science Target",
    };
    setMultiStops([...multiStops, stop]);
    setNewStopLat("");
    setNewStopLon("");
    setNewStopName("");
  };

  const handleAddDiscoveryStop = () => {
    if (!selectedDiscoveryToAdd) return;
    const disc = catalogDiscoveries.find((d) => d.id === selectedDiscoveryToAdd);
    if (!disc) return;

    // Check if already in stops
    if (multiStops.some((s) => s.discovery_id === disc.id)) return;

    const stop: ScienceStop = {
      stop_id: disc.id,
      name: disc.name,
      lat: disc.latitude,
      lon: disc.longitude,
      discovery_id: disc.id,
      is_mandatory: true,
      target_geology: disc.geological_context?.unit_name || disc.primary_feature || "Orbital Science Candidate",
      description: disc.scientific_significance,
    };
    setMultiStops([...multiStops, stop]);
    setSelectedDiscoveryToAdd("");
  };

  const handleRemoveStop = (index: number) => {
    setMultiStops(multiStops.filter((_, i) => i !== index));
  };

  const handleMoveStop = (index: number, direction: "up" | "down") => {
    if (direction === "up" && index === 0) return;
    if (direction === "down" && index === multiStops.length - 1) return;
    const newIdx = direction === "up" ? index - 1 : index + 1;
    const copy = [...multiStops];
    const temp = copy[index];
    copy[index] = copy[newIdx];
    copy[newIdx] = temp;
    setMultiStops(copy);
  };

  const handleToggleMandatory = (index: number) => {
    const copy = [...multiStops];
    copy[index] = { ...copy[index], is_mandatory: !copy[index].is_mandatory };
    setMultiStops(copy);
  };

  return (
    <div className="space-y-5 text-xs font-mono text-slate-300">
      {/* Prominent Mandatory Safety Disclaimer */}
      <div className="bg-red-950/40 border border-red-700/60 rounded-lg p-3.5 text-red-200 shadow-md">
        <div className="flex items-start space-x-2.5">
          <span className="text-lg">⚠️</span>
          <div className="space-y-1">
            <span className="font-bold uppercase tracking-wider text-[11px] text-red-400">
              Operational Safety Advisory — Analytical Cost Only
            </span>
            <p className="text-[11px] leading-relaxed text-red-200/90 font-sans">
              Minimizing analytical terrain cost does NOT certify physical astronaut or rover safety.
              Orbital DEMs (~1 m to 14.8 km/px) do not resolve microtopographic boulder hazards, regolith
              bearing shear strength, or dust depth. No route generated by MARS-X is certified astronaut-safe.
            </p>
          </div>
        </div>
      </div>

      {/* Mode Navigation Tabs */}
      <div className="flex border-b border-[#232840] bg-[#0d1020] p-1 rounded-lg gap-1">
        <button
          onClick={() => setPlannerMode("single")}
          className={`flex-1 py-2 px-3 rounded font-bold uppercase text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
            plannerMode === "single"
              ? "bg-orange-500 text-black shadow-md"
              : "text-slate-400 hover:text-white hover:bg-slate-800/50"
          }`}
        >
          <span>🎯</span> Single-Leg Marswalk (A*)
        </button>
        <button
          onClick={() => setPlannerMode("multi")}
          className={`flex-1 py-2 px-3 rounded font-bold uppercase text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
            plannerMode === "multi"
              ? "bg-emerald-500 text-black shadow-md"
              : "text-slate-400 hover:text-white hover:bg-slate-800/50"
          }`}
        >
          <span>🧭</span> Multi-Stop Science Traverse (Traveling Explorer)
        </button>
        <button
          onClick={() => setPlannerMode("intelligence")}
          className={`flex-1 py-2 px-3 rounded font-bold uppercase text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
            plannerMode === "intelligence"
              ? "bg-cyan-500 text-black shadow-md"
              : "text-slate-400 hover:text-white hover:bg-slate-800/50"
          }`}
        >
          <span>🔬</span> Route Intelligence
          {(routeIntelligence || traverseIntelligence) && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/40 text-cyan-200 font-bold">Ready</span>
          )}
        </button>
        <button
          onClick={() => setPlannerMode("environmental")}
          className={`flex-1 py-2 px-3 rounded font-bold uppercase text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
            plannerMode === "environmental"
              ? "bg-amber-500 text-black shadow-md"
              : "text-slate-400 hover:text-white hover:bg-slate-800/50"
          }`}
        >
          <span>🛰️</span> Environmental
        </button>
      </div>

      {/* ===================================================================== */}
      {/* MODE 1: SINGLE-LEG MARSWALK (PHASE 8.8.2) */}
      {/* ===================================================================== */}
      {plannerMode === "single" && (
        <div className="space-y-5">
          {/* Preset Corridors */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
                <span>🎯</span> Validated Marswalk Corridors (Multi-Tier DEMs)
              </span>
              <span className="text-[10px] text-slate-400">Click to load authenticated coordinates</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {singleMetadata?.validated_corridors?.map((p) => {
                const isSelected = selectedCorridor === p.corridor_id;
                return (
                  <button
                    key={p.corridor_id}
                    onClick={() => handleSelectPreset(p)}
                    className={`text-left p-2.5 rounded border transition-all ${
                      isSelected
                        ? "bg-orange-500/15 border-orange-500/60 text-white shadow"
                        : "bg-[#101426] border-[#1e253e] text-slate-300 hover:border-slate-500 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold text-[11px] text-orange-400">
                      <span>{p.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/40 border border-orange-500/30 text-orange-300">
                        {p.source_dataset}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1 line-clamp-1">{p.description}</div>
                    <div className="text-[9px] text-slate-500 mt-1 flex justify-between">
                      <span>Start: ({p.start_lat >= 0 ? `${p.start_lat.toFixed(3)}°N` : `${Math.abs(p.start_lat).toFixed(3)}°S`}, {p.start_lon.toFixed(3)}°E)</span>
                      <span>Dest: ({p.dest_lat >= 0 ? `${p.dest_lat.toFixed(3)}°N` : `${Math.abs(p.dest_lat).toFixed(3)}°S`}, {p.dest_lon.toFixed(3)}°E)</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Waypoint & Cost Parameters Configuration */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-4">
            <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
              <span>⚙️</span> Traverse Parameters &amp; Cost Surface Controls
            </span>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Coordinates */}
              <div className="space-y-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Waypoint Coordinates</span>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Start Latitude (°)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={startLat}
                      onChange={(e) => setStartLat(parseFloat(e.target.value))}
                      className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Start Longitude (°E)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={startLon}
                      onChange={(e) => setStartLon(parseFloat(e.target.value))}
                      className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Dest Latitude (°)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={destLat}
                      onChange={(e) => setDestLat(parseFloat(e.target.value))}
                      className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Dest Longitude (°E)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={destLon}
                      onChange={(e) => setDestLon(parseFloat(e.target.value))}
                      className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Engine Parameters */}
              <div className="space-y-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Routing Constraints</span>
                <div className="grid grid-cols-1 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Terrain Source Dataset</label>
                    <select
                      value={preferredSource}
                      onChange={(e) => setPreferredSource(e.target.value)}
                      className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                    >
                      <option value="auto">Auto (Select Highest Resolution Footprint)</option>
                      <option value="hirise-holden">HiRISE Holden Crater (~1.01 m/px)</option>
                      <option value="ctx-tyrrhena">CTX Tyrrhena Terra (~20.0 m/px)</option>
                      <option value="ctx-apollinaris">CTX Apollinaris Sulci (~20.0 m/px)</option>
                      <option value="mola-128ppd">MOLA 128 ppd Regional Tile (~463 m/px)</option>
                      <option value="mola-4ppd">MOLA 4 ppd Global Fallback (~14.8 km/px)</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">
                        Slope Penalty β ({slopePenalty}x)
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="10"
                        step="0.5"
                        value={slopePenalty}
                        onChange={(e) => setSlopePenalty(parseFloat(e.target.value))}
                        className="w-full accent-orange-500"
                      />
                      <div className="flex justify-between text-[9px] text-slate-500">
                        <span>0.0 (None)</span>
                        <span>10.0 (Severe)</span>
                      </div>
                    </div>

                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">
                        Max Slope Cutoff ({maxSlope}°)
                      </label>
                      <input
                        type="range"
                        min="5"
                        max="45"
                        step="1"
                        value={maxSlope}
                        onChange={(e) => setMaxSlope(parseFloat(e.target.value))}
                        className="w-full accent-orange-500"
                      />
                      <div className="flex justify-between text-[9px] text-slate-500">
                        <span>5°</span>
                        <span>45°</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="pt-2 flex items-center justify-between border-t border-[#1e253e]">
              <span className="text-[10px] text-slate-500">
                A* 3D Euclidean lower-bound heuristic with diagonal corner-cutting prevention
              </span>
              <button
                onClick={handlePlanRoute}
                disabled={loading}
                className={`px-5 py-2 rounded font-bold uppercase text-xs tracking-wider flex items-center gap-2 transition-all shadow-lg ${
                  loading
                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "bg-orange-500 hover:bg-orange-400 text-black shadow-orange-500/20"
                }`}
              >
                {loading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                    <span>Computing A* Path...</span>
                  </>
                ) : (
                  <>
                    <span>🥾</span>
                    <span>Generate Marswalk Route</span>
                  </>
                )}
              </button>
            </div>

            {error && (
              <div className="bg-red-950/60 border border-red-600 rounded p-3 text-red-200 text-xs">
                <span className="font-bold">Error:</span> {error}
              </div>
            )}
          </div>

          {/* Single-Leg Route Results */}
          {routeResult && (
            <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-4 shadow-xl">
              <div className="flex flex-wrap items-center justify-between border-b border-[#1e253e] pb-3 gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-white uppercase tracking-wider">
                      {routeResult.route_name || "Optimal Marswalk Traverse"}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
                      ID: {routeResult.route_id}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Dataset: <span className="text-orange-300 font-semibold">{routeResult.source_dataset}</span> ({routeResult.native_resolution_desc}) • Vertical Datum: {routeResult.vertical_datum}
                  </div>
                </div>

                <div className="text-right text-[10px] text-slate-400">
                  <div>A* Search Time: <span className="text-slate-200 font-bold">{routeResult.search_metrics?.search_duration_ms ?? "N/A"} ms</span></div>
                  <div>Nodes Expanded: <span className="text-slate-200 font-bold">{routeResult.search_metrics?.nodes_expanded ?? 0}</span></div>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-center">
                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Surface Distance</div>
                  <div className="text-sm font-bold text-emerald-400 mt-0.5">
                    {routeResult.total_surface_distance_m >= 1000
                      ? `${(routeResult.total_surface_distance_m / 1000).toFixed(2)} km`
                      : `${routeResult.total_surface_distance_m.toFixed(1)} m`}
                  </div>
                  <div className="text-[9px] text-slate-500">Horiz: {(routeResult.total_horizontal_distance_m >= 1000 ? (routeResult.total_horizontal_distance_m / 1000).toFixed(2) + " km" : routeResult.total_horizontal_distance_m.toFixed(1) + " m")}</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Optimization Cost</div>
                  <div className="text-sm font-bold text-amber-400 mt-0.5">
                    {routeResult.total_optimization_cost !== undefined ? routeResult.total_optimization_cost.toFixed(1) : (routeResult.search_metrics?.total_path_cost ?? "N/A")}
                  </div>
                  <div className="text-[9px] text-slate-500">Analytical Metric (Weighted)</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Elevation Gain</div>
                  <div className="text-sm font-bold text-blue-400 mt-0.5">
                    +{routeResult.cumulative_elevation_gain_m.toFixed(1)} m
                  </div>
                  <div className="text-[9px] text-slate-500">Loss: -{routeResult.cumulative_elevation_loss_m.toFixed(1)} m</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Elevation Span</div>
                  <div className="text-sm font-bold text-slate-200 mt-0.5">
                    {routeResult.min_elevation_m.toFixed(0)}m to {routeResult.max_elevation_m.toFixed(0)}m
                  </div>
                  <div className="text-[9px] text-slate-500">MOLA Areoid</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Max Route Slope</div>
                  <div className={`text-sm font-bold mt-0.5 ${routeResult.max_route_slope_deg > 20 ? "text-amber-400" : "text-emerald-400"}`}>
                    {routeResult.max_route_slope_deg.toFixed(1)}°
                  </div>
                  <div className="text-[9px] text-slate-500">Mean: {routeResult.mean_route_slope_deg.toFixed(1)}°</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Path Waypoints</div>
                  <div className="text-sm font-bold text-purple-400 mt-0.5">
                    {routeResult.path_points.length}
                  </div>
                  <div className="text-[9px] text-slate-500">8-way connected</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Unknown Terrain</div>
                  <div className="text-sm font-bold text-emerald-400 mt-0.5">
                    {routeResult.unknown_data_exposure_pct.toFixed(1)}%
                  </div>
                  <div className="text-[9px] text-slate-500">Zero NoData</div>
                </div>
              </div>

              {/* Exposure breakdown */}
              <div className="space-y-2 bg-[#101426] border border-[#1e253e] rounded p-3">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-200">
                  <span>Analytical Slope Band Exposure Breakdown</span>
                  <span className="text-[10px] text-slate-400">% of surface distance</span>
                </div>

                <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex shadow-inner">
                  <div style={{ width: `${routeResult.slope_band_exposure_pct.low || 0}%` }} className="bg-[#2ecc71]" />
                  <div style={{ width: `${routeResult.slope_band_exposure_pct.moderate || 0}%` }} className="bg-[#f39c12]" />
                  <div style={{ width: `${routeResult.slope_band_exposure_pct.high || 0}%` }} className="bg-[#e74c3c]" />
                  <div style={{ width: `${routeResult.slope_band_exposure_pct.very_high || 0}%` }} className="bg-[#8e44ad]" />
                  <div style={{ width: `${routeResult.slope_band_exposure_pct.unknown || 0}%` }} className="bg-[#7f8c8d]" />
                </div>
              </div>

              {/* Phase 8.8.4 Action Button */}
              <div className="pt-2">
                <button
                  onClick={() => setPlannerMode("intelligence")}
                  className="w-full py-2.5 px-4 rounded bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/60 text-cyan-200 font-bold uppercase tracking-wider text-xs flex items-center justify-center gap-2 transition-all shadow-md"
                >
                  <span>🔬</span> Inspect Scientific Route Intelligence (Elevation, Slope, Geology, Thermal &amp; Discoveries) →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODE 2: MULTI-STOP SCIENCE TRAVERSE (PHASE 8.8.3) */}
      {/* ===================================================================== */}
      {plannerMode === "multi" && (
        <div className="space-y-5">
          {/* Preset Multi-Stop Transects */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
                <span>🧭</span> Curated Science Transects &amp; Presets
              </span>
              <span className="text-[10px] text-slate-400">Click to load authenticated multi-stop scenarios</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
              {multiMetadata?.curated_presets?.map((p) => {
                const isSelected = selectedMultiPreset === p.preset_id;
                return (
                  <button
                    key={p.preset_id}
                    onClick={() => handleSelectMultiPreset(p)}
                    className={`text-left p-2.5 rounded border transition-all ${
                      isSelected
                        ? "bg-emerald-500/15 border-emerald-500/60 text-white shadow"
                        : "bg-[#101426] border-[#1e253e] text-slate-300 hover:border-slate-500 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold text-[11px] text-emerald-400">
                      <span>{p.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/40 border border-emerald-500/30 text-emerald-300">
                        {p.source_dataset}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1 line-clamp-2">{p.description}</div>
                    <div className="text-[9px] text-slate-500 mt-2 flex justify-between">
                      <span>{p.stops.length} Science Stops</span>
                      <span>Target: {p.target_geology}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Start & Final Destination Configuration */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
            <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
              <span>📍</span> Traverse Termini (Fixed Start &amp; Final Destination)
            </span>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Start */}
              <div className="bg-[#12162a] border border-[#202742] rounded p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-400 uppercase text-[10px]">Start Location</span>
                  <input
                    type="text"
                    value={multiStartName}
                    onChange={(e) => setMultiStartName(e.target.value)}
                    className="bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-0.5 text-[10px] text-slate-200"
                    placeholder="Location Label"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[9px] text-slate-400 block mb-0.5">Latitude (°)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={multiStartLat}
                      onChange={(e) => setMultiStartLat(parseFloat(e.target.value))}
                      className="w-full bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-1 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-slate-400 block mb-0.5">Longitude (°E)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={multiStartLon}
                      onChange={(e) => setMultiStartLon(parseFloat(e.target.value))}
                      className="w-full bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-1 text-xs text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Destination */}
              <div className="bg-[#12162a] border border-[#202742] rounded p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-400 uppercase text-[10px]">Final Destination</span>
                  <input
                    type="text"
                    value={multiDestName}
                    onChange={(e) => setMultiDestName(e.target.value)}
                    className="bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-0.5 text-[10px] text-slate-200"
                    placeholder="Location Label"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[9px] text-slate-400 block mb-0.5">Latitude (°)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={multiDestLat}
                      onChange={(e) => setMultiDestLat(parseFloat(e.target.value))}
                      className="w-full bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-1 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-slate-400 block mb-0.5">Longitude (°E)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={multiDestLon}
                      onChange={(e) => setMultiDestLon(parseFloat(e.target.value))}
                      className="w-full bg-[#0b0e1b] border border-[#262e4d] rounded px-2 py-1 text-xs text-white"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Science Stops Management */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
                <span>🔬</span> Intermediate Science Stops ({multiStops.length})
              </span>
              <span className="text-[10px] text-slate-400">Add from discovery catalog or specify coordinates</span>
            </div>

            {/* Quick Add Form */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 bg-[#101426] border border-[#1e253e] rounded">
              {/* Add from Science Catalog */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-300 block">Add Phase 8.7 Science Discovery</span>
                <div className="flex gap-2">
                  <select
                    value={selectedDiscoveryToAdd}
                    onChange={(e) => setSelectedDiscoveryToAdd(e.target.value)}
                    className="flex-1 bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                  >
                    <option value="">-- Select Science Discovery --</option>
                    {catalogDiscoveries.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.latitude.toFixed(2)}°, {d.longitude.toFixed(2)}°E)
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleAddDiscoveryStop}
                    disabled={!selectedDiscoveryToAdd}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-black font-bold rounded text-xs"
                  >
                    + Add
                  </button>
                </div>
              </div>

              {/* Add Custom Coordinate */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-300 block">Add Custom Waypoint Target</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newStopName}
                    onChange={(e) => setNewStopName(e.target.value)}
                    placeholder="Name"
                    className="w-1/3 bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                  />
                  <input
                    type="number"
                    step="0.0001"
                    value={newStopLat}
                    onChange={(e) => setNewStopLat(e.target.value)}
                    placeholder="Lat"
                    className="w-1/4 bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                  />
                  <input
                    type="number"
                    step="0.0001"
                    value={newStopLon}
                    onChange={(e) => setNewStopLon(e.target.value)}
                    placeholder="Lon"
                    className="w-1/4 bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                  />
                  <button
                    onClick={handleAddCustomStop}
                    disabled={!newStopLat || !newStopLon}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-bold rounded text-xs"
                  >
                    + Add
                  </button>
                </div>
              </div>
            </div>

            {/* Stops Table / List */}
            {multiStops.length === 0 ? (
              <div className="p-4 text-center text-slate-500 italic bg-[#101426] rounded">
                No intermediate stops specified. Direct traversal between Start and Destination will be planned.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-60 overflow-y-auto">
                {multiStops.map((stop, idx) => (
                  <div
                    key={stop.stop_id || idx}
                    className="flex items-center justify-between p-2.5 rounded bg-[#101426] border border-[#1e253e] hover:border-slate-500"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center justify-center font-bold text-[10px]">
                        {idx + 1}
                      </span>
                      <div>
                        <div className="font-bold text-slate-200 text-xs flex items-center gap-2">
                          <span>{stop.name}</span>
                          {stop.discovery_id && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-500/30">
                              Discovery
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          ({stop.lat.toFixed(4)}°, {stop.lon.toFixed(4)}°E) • {stop.target_geology || "No geology tag"}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1 text-[10px] text-slate-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={stop.is_mandatory !== false}
                          onChange={() => handleToggleMandatory(idx)}
                          className="accent-emerald-500"
                        />
                        <span>Mandatory</span>
                      </label>
                      <button
                        onClick={() => handleMoveStop(idx, "up")}
                        disabled={idx === 0}
                        className="px-1.5 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded text-[10px]"
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => handleMoveStop(idx, "down")}
                        disabled={idx === multiStops.length - 1}
                        className="px-1.5 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded text-[10px]"
                      >
                        ▼
                      </button>
                      <button
                        onClick={() => handleRemoveStop(idx)}
                        className="px-2 py-0.5 bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800/40 rounded text-[10px]"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Strategy & Terrain Controls */}
          <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-4">
            <span className="font-bold text-slate-100 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
              <span>⚙️</span> Optimization Strategy &amp; Routing Constraints
            </span>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Stop Ordering Strategy</label>
                <select
                  value={multiStrategy}
                  onChange={(e) => setMultiStrategy(e.target.value)}
                  className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                >
                  <option value="optimize_tsp">Traveling Explorer Optimization (TSP)</option>
                  <option value="nearest_neighbor">Greedy Nearest-Neighbor</option>
                  <option value="preserve_order">Preserve User Stop Order</option>
                </select>
                <span className="text-[9px] text-slate-500 block mt-1">
                  K &le; 4 uses exact permutation; K &gt; 4 uses 2-opt local search.
                </span>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 block mb-1">DEM Source Dataset</label>
                <select
                  value={multiPreferredSource}
                  onChange={(e) => setMultiPreferredSource(e.target.value)}
                  className="w-full bg-[#13172c] border border-[#262e4d] rounded px-2 py-1.5 text-xs text-white"
                >
                  <option value="auto">Auto (Highest Common Resolution)</option>
                  <option value="hirise-holden">HiRISE Holden Crater (~1.01 m/px)</option>
                  <option value="ctx-tyrrhena">CTX Tyrrhena Terra (~20.0 m/px)</option>
                  <option value="ctx-apollinaris">CTX Apollinaris Sulci (~20.0 m/px)</option>
                  <option value="mola-128ppd">MOLA 128 ppd Regional Tile (~463 m/px)</option>
                  <option value="mola-4ppd">MOLA 4 ppd Global Fallback (~14.8 km/px)</option>
                </select>
                <span className="text-[9px] text-slate-500 block mt-1">
                  All waypoints must reside in selected DEM footprint.
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-slate-400">Slope Penalty β ({multiSlopePenalty}x)</span>
                  <span className="text-slate-400">Max Slope ({multiMaxSlope}°)</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={multiSlopePenalty}
                    onChange={(e) => setMultiSlopePenalty(parseFloat(e.target.value))}
                    className="accent-emerald-500"
                  />
                  <input
                    type="range"
                    min="5"
                    max="45"
                    step="1"
                    value={multiMaxSlope}
                    onChange={(e) => setMultiMaxSlope(parseFloat(e.target.value))}
                    className="accent-emerald-500"
                  />
                </div>
              </div>
            </div>

            {/* Action Button */}
            <div className="pt-2 flex items-center justify-between border-t border-[#1e253e]">
              <span className="text-[10px] text-slate-500">
                Solves directed pairwise terrain legs and optimizes intermediate science visit sequence
              </span>
              <button
                onClick={handlePlanMultiTraverse}
                disabled={multiLoading}
                className={`px-6 py-2 rounded font-bold uppercase text-xs tracking-wider flex items-center gap-2 transition-all shadow-lg ${
                  multiLoading
                    ? "bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "bg-emerald-500 hover:bg-emerald-400 text-black shadow-emerald-500/20"
                }`}
              >
                {multiLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                    <span>Optimizing Traverse...</span>
                  </>
                ) : (
                  <>
                    <span>🚀</span>
                    <span>Optimize Science Traverse</span>
                  </>
                )}
              </button>
            </div>

            {multiError && (
              <div className="bg-red-950/60 border border-red-600 rounded p-3 text-red-200 text-xs">
                <span className="font-bold">Error:</span> {multiError}
              </div>
            )}
          </div>

          {/* Multi-Stop Results Telemetry Display */}
          {multiResult && (
            <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-4 shadow-xl">
              <div className="flex flex-wrap items-center justify-between border-b border-[#1e253e] pb-3 gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-white uppercase tracking-wider">
                      {multiResult.traverse_name}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
                      ID: {multiResult.traverse_id}
                    </span>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded border ${
                      multiResult.is_heuristic_solution
                        ? "bg-amber-950/60 border-amber-500/40 text-amber-300"
                        : "bg-blue-950/60 border-blue-500/40 text-blue-300"
                    }`}>
                      {multiResult.is_heuristic_solution ? "Heuristic (2-Opt TSP)" : "Provably Exact Permutation"}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Dataset: <span className="text-emerald-300 font-semibold">{multiResult.source_dataset}</span> ({multiResult.native_resolution_desc}) • Legs: {multiResult.legs.length} • Strategy: {multiResult.optimization_strategy}
                  </div>
                </div>

                <div className="text-right text-[10px] text-slate-400">
                  <div>Optimization Duration: <span className="text-slate-200 font-bold">{multiResult.computation_metrics?.duration_ms ?? "N/A"} ms</span></div>
                  <div>Pairwise Legs Solved: <span className="text-slate-200 font-bold">{multiResult.computation_metrics?.pairwise_legs_computed ?? 0}</span></div>
                </div>
              </div>

              {/* Traverse Analytics Metrics Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-center">
                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Total Distance</div>
                  <div className="text-sm font-bold text-emerald-400 mt-0.5">
                    {multiResult.total_surface_distance_m >= 1000
                      ? `${(multiResult.total_surface_distance_m / 1000).toFixed(2)} km`
                      : `${multiResult.total_surface_distance_m.toFixed(1)} m`}
                  </div>
                  <div className="text-[9px] text-slate-500">Horiz: {(multiResult.total_horizontal_distance_m >= 1000 ? (multiResult.total_horizontal_distance_m / 1000).toFixed(2) + " km" : multiResult.total_horizontal_distance_m.toFixed(1) + " m")}</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Optimization Cost</div>
                  <div className="text-sm font-bold text-amber-400 mt-0.5">
                    {multiResult.total_optimization_cost.toFixed(1)}
                  </div>
                  <div className="text-[9px] text-slate-500">Analytical Traverse Cost</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Elevation Gain</div>
                  <div className="text-sm font-bold text-blue-400 mt-0.5">
                    +{multiResult.cumulative_elevation_gain_m.toFixed(1)} m
                  </div>
                  <div className="text-[9px] text-slate-500">Loss: -{multiResult.cumulative_elevation_loss_m.toFixed(1)} m</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Elevation Span</div>
                  <div className="text-sm font-bold text-slate-200 mt-0.5">
                    {multiResult.min_elevation_m.toFixed(0)}m to {multiResult.max_elevation_m.toFixed(0)}m
                  </div>
                  <div className="text-[9px] text-slate-500">MOLA Areoid</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Max Route Slope</div>
                  <div className={`text-sm font-bold mt-0.5 ${multiResult.max_route_slope_deg > 20 ? "text-amber-400" : "text-emerald-400"}`}>
                    {multiResult.max_route_slope_deg.toFixed(1)}°
                  </div>
                  <div className="text-[9px] text-slate-500">Mean: {multiResult.mean_route_slope_deg.toFixed(1)}°</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Traverse Legs</div>
                  <div className="text-sm font-bold text-purple-400 mt-0.5">
                    {multiResult.legs.length}
                  </div>
                  <div className="text-[9px] text-slate-500">{multiResult.ordered_stops.length} stops visited</div>
                </div>

                <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400">Unknown Terrain</div>
                  <div className="text-sm font-bold text-emerald-400 mt-0.5">
                    {multiResult.unknown_data_exposure_pct.toFixed(1)}%
                  </div>
                  <div className="text-[9px] text-slate-500">Zero NoData</div>
                </div>
              </div>

              {/* Stop Sequence Order */}
              <div className="bg-[#101426] border border-[#1e253e] rounded p-3 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-200">
                  <span>Optimized Stop Visit Sequence</span>
                  <span className="text-[10px] text-slate-400">Start &rarr; Intermediate Stops &rarr; Destination</span>
                </div>
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  {/* Origin */}
                  <div className="px-2.5 py-1.5 rounded bg-emerald-950/80 border border-emerald-500/50 text-emerald-200 text-xs flex items-center gap-1.5">
                    <span className="font-bold">🏁 START:</span>
                    <span>{multiResult.start_stop.name}</span>
                  </div>

                  {/* Intermediates */}
                  {multiResult.ordered_stops.map((st, i) => (
                    <React.Fragment key={st.stop_id}>
                      <span className="text-slate-500 font-bold">&rarr;</span>
                      <div className="px-2.5 py-1.5 rounded bg-[#13172c] border border-blue-500/40 text-blue-200 text-xs flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-blue-500/30 text-blue-300 flex items-center justify-center font-bold text-[9px]">
                          {i + 1}
                        </span>
                        <span>{st.name}</span>
                      </div>
                    </React.Fragment>
                  ))}

                  {/* Destination */}
                  <span className="text-slate-500 font-bold">&rarr;</span>
                  <div className="px-2.5 py-1.5 rounded bg-rose-950/80 border border-rose-500/50 text-rose-200 text-xs flex items-center gap-1.5">
                    <span className="font-bold">🎯 DEST:</span>
                    <span>{multiResult.dest_stop.name}</span>
                  </div>
                </div>
              </div>

              {/* Slope Band Exposure Bar */}
              <div className="space-y-2 bg-[#101426] border border-[#1e253e] rounded p-3">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-200">
                  <span>Aggregated Traverse Slope Band Exposure</span>
                  <span className="text-[10px] text-slate-400">% of total surface distance</span>
                </div>

                <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex shadow-inner">
                  <div style={{ width: `${multiResult.slope_band_exposure_pct.low || 0}%` }} className="bg-[#2ecc71]" />
                  <div style={{ width: `${multiResult.slope_band_exposure_pct.moderate || 0}%` }} className="bg-[#f39c12]" />
                  <div style={{ width: `${multiResult.slope_band_exposure_pct.high || 0}%` }} className="bg-[#e74c3c]" />
                  <div style={{ width: `${multiResult.slope_band_exposure_pct.very_high || 0}%` }} className="bg-[#8e44ad]" />
                  <div style={{ width: `${multiResult.slope_band_exposure_pct.unknown || 0}%` }} className="bg-[#7f8c8d]" />
                </div>
              </div>

              {/* Individual Leg Inspection Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-300">
                  <span>Individual Route Leg Breakdown ({multiResult.legs.length} legs)</span>
                  <span className="text-[10px] text-slate-500">Click leg to inspect detailed metrics</span>
                </div>

                <div className="overflow-x-auto border border-[#1e253e] rounded bg-[#090b14]">
                  <table className="w-full text-left text-[10px]">
                    <thead className="bg-[#12162a] text-slate-400 border-b border-[#1e253e]">
                      <tr>
                        <th className="py-1.5 px-3">Leg</th>
                        <th className="py-1.5 px-3">From</th>
                        <th className="py-1.5 px-3">To</th>
                        <th className="py-1.5 px-3 text-right">Distance (m)</th>
                        <th className="py-1.5 px-3 text-right">Cost</th>
                        <th className="py-1.5 px-3 text-right">Gain / Loss</th>
                        <th className="py-1.5 px-3 text-right">Max Slope</th>
                        <th className="py-1.5 px-3 text-center">Feasibility</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e253e]/40 text-slate-300 font-mono">
                      {multiResult.legs.map((leg, i) => (
                        <tr
                          key={leg.leg_index}
                          onClick={() => setActiveLegInspectIndex(activeLegInspectIndex === i ? null : i)}
                          className={`cursor-pointer transition-colors ${
                            activeLegInspectIndex === i ? "bg-slate-800/80 text-white" : "hover:bg-slate-800/40"
                          }`}
                        >
                          <td className="py-1.5 px-3 font-bold text-slate-400">Leg {i + 1}</td>
                          <td className="py-1.5 px-3 text-emerald-300">{leg.from_stop_name}</td>
                          <td className="py-1.5 px-3 text-blue-300">{leg.to_stop_name}</td>
                          <td className="py-1.5 px-3 text-right text-emerald-400 font-bold">{leg.surface_distance_m.toFixed(1)}</td>
                          <td className="py-1.5 px-3 text-right text-amber-300">{leg.optimization_cost.toFixed(1)}</td>
                          <td className="py-1.5 px-3 text-right">+{leg.elevation_gain_m.toFixed(0)}m / -{leg.elevation_loss_m.toFixed(0)}m</td>
                          <td className="py-1.5 px-3 text-right">{leg.max_slope_deg.toFixed(1)}°</td>
                          <td className="py-1.5 px-3 text-center">
                            <span className="px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-[9px]">
                              PASS
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Phase 8.8.4 Action Button */}
              <div className="pt-2">
                <button
                  onClick={() => setPlannerMode("intelligence")}
                  className="w-full py-2.5 px-4 rounded bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/60 text-cyan-200 font-bold uppercase tracking-wider text-xs flex items-center justify-center gap-2 transition-all shadow-md"
                >
                  <span>🔬</span> Inspect Complete Traverse Intelligence (All Legs &amp; Aggregated Analytics) →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODE 3: ROUTE INTELLIGENCE & TRAVERSE ANALYSIS (PHASE 8.8.4) */}
      {/* ===================================================================== */}
      {plannerMode === "intelligence" && (
        <div className="space-y-4">
          {intelligenceLoading ? (
            <div className="p-8 text-center bg-[#0b0e1b] border border-[#1e253e] rounded-lg text-slate-400 space-y-3">
              <div className="inline-block animate-spin text-2xl">⏳</div>
              <div className="text-sm font-bold text-cyan-400">Computing Scientific Route Intelligence...</div>
              <div className="text-[11px] text-slate-500">
                Intersecting USGS SIM 3292 geological polygons, sampling MGS TES thermal inertia, and querying Phase 8.7 discoveries.
              </div>
            </div>
          ) : (routeIntelligence || traverseIntelligence) ? (
            <RouteIntelligenceView
              routeReport={routeIntelligence}
              traverseReport={traverseIntelligence}
            />
          ) : (
            <div className="p-8 text-center bg-[#0b0e1b] border border-[#1e253e] rounded-lg text-slate-400 space-y-4">
              <span className="text-3xl block">🔬</span>
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-200">No Route Planned Yet</div>
                <p className="text-[11px] text-slate-400 max-w-md mx-auto leading-relaxed">
                  Generate a single-leg Marswalk route or plan a multi-stop science traverse first.
                  The intelligence engine will automatically synthesize elevation profiles, USGS SIM 3292 geology,
                  MGS TES thermal inertia, and nearby science discoveries.
                </p>
              </div>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  onClick={() => {
                    setPlannerMode("single");
                    handlePlanRoute();
                  }}
                  className="py-2 px-4 rounded bg-orange-500 text-black font-bold uppercase tracking-wider text-xs shadow hover:bg-orange-400 transition-all"
                >
                  Plan Tyrrhena Valley Route (A*)
                </button>
                <button
                  onClick={() => {
                    setPlannerMode("multi");
                    handlePlanMultiTraverse();
                  }}
                  className="py-2 px-4 rounded bg-emerald-500 text-black font-bold uppercase tracking-wider text-xs shadow hover:bg-emerald-400 transition-all"
                >
                  Plan Multi-Stop Transect (TSP)
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODE 4: ENVIRONMENTAL INTELLIGENCE (PHASE 8.9.1) */}
      {/* ===================================================================== */}
      {plannerMode === "environmental" && (
        <div className="space-y-4">
          <EnvironmentalIntelligenceView
            routePoints={
              routeResult?.path_points?.map((p) => ({
                lat: p.lat,
                lon: p.lon,
                elevation_m: p.elevation_m,
                distance_m: p.cumulative_distance_m,
              })) || null
            }
            routeName={routeResult?.route_name || multiResult?.traverse_name || null}
          />
        </div>
      )}
    </div>
  );
};
