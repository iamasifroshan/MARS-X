"use client";

import { useEffect, useState } from "react";
import {
  fetchResolutionSelection,
  fetchTerrainProfile,
  fetchTransitionCompatibility,
  fetchRegionAssessment,
  fetchPresetRegionComparison,
  fetchRouteTerrainSource,
} from "@/lib/api";
import {
  ResolutionSelectionResult,
  MultiScaleAnalysisResult,
  ResolutionTransitionEvaluation,
  RegionTerrainAssessment,
  RegionComparisonResponse,
  RouteTerrainSourceResponse,
} from "@/lib/types";

interface TerrainIntelligencePanelProps {
  currentCoordinates?: { lat: number; lon: number } | null;
}

export function TerrainIntelligencePanel({ currentCoordinates }: TerrainIntelligencePanelProps) {
  const [subTab, setSubTab] = useState<"selector" | "multiscale" | "comparison" | "transition" | "route">("selector");
  
  // Region Coordinates for Analysis
  const [bbox, setBbox] = useState({
    minLat: -5.1,
    minLon: 66.1,
    maxLat: -4.5,
    maxLon: 66.5,
  });

  // State
  const [analysisType, setAnalysisType] = useState<string>("traverse_planning");
  const [targetScaleM, setTargetScaleM] = useState<number>(500);
  const [selectorResult, setSelectorResult] = useState<ResolutionSelectionResult | null>(null);
  const [profileResult, setProfileResult] = useState<MultiScaleAnalysisResult | null>(null);
  const [comparisonResult, setComparisonResult] = useState<RegionComparisonResponse | null>(null);
  const [transitionResult, setTransitionResult] = useState<ResolutionTransitionEvaluation | null>(null);
  const [routeSourceResult, setRouteSourceResult] = useState<RouteTerrainSourceResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Initial load
  useEffect(() => {
    handleRunResolutionSelection();
  }, []);

  const handleRunResolutionSelection = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchResolutionSelection(
        bbox.minLat,
        bbox.minLon,
        bbox.maxLat,
        bbox.maxLon,
        analysisType,
        targetScaleM
      );
      setSelectorResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Resolution selection query failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRunMultiScaleProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchTerrainProfile(
        bbox.minLat,
        bbox.minLon,
        bbox.maxLat,
        bbox.maxLon,
        undefined,
        "100,500,1000,2000"
      );
      setProfileResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Multi-scale profiling failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRunRegionComparison = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchPresetRegionComparison(targetScaleM);
      setComparisonResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Region comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRunTransitionEvaluation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchTransitionCompatibility("mola-megdr-128", "ctx-dtm-p21-009323");
      setTransitionResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transition compatibility check failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRunRouteSourceEval = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchRouteTerrainSource(-14.2, 59.1, -14.0, 59.3, targetScaleM);
      setRouteSourceResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Route source evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 text-sm text-slate-300 font-sans">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-white tracking-wide flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-pulse"></span>
            Resolution-Aware Terrain Intelligence (Phase 8)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Scientifically Constrained Multi-Resolution Mars Analysis & Mission Site Characterization
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 bg-orange-950/60 border border-orange-800/60 text-orange-400 rounded font-bold">
            Physical Scale Aware
          </span>
          <span className="px-2.5 py-1 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 rounded font-bold">
            Zero Discovered Fabrication
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300 font-mono">
          {error}
        </div>
      )}

      {/* Sub-Tabs */}
      <div className="flex border-b border-slate-800 space-x-1 font-mono text-xs overflow-x-auto pb-1">
        <button
          onClick={() => { setSubTab("selector"); handleRunResolutionSelection(); }}
          className={`px-3 py-1.5 rounded transition-colors ${
            subTab === "selector"
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 font-bold"
              : "text-slate-400 hover:text-white"
          }`}
        >
          1. Resolution Selector
        </button>
        <button
          onClick={() => { setSubTab("multiscale"); handleRunMultiScaleProfile(); }}
          className={`px-3 py-1.5 rounded transition-colors ${
            subTab === "multiscale"
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 font-bold"
              : "text-slate-400 hover:text-white"
          }`}
        >
          2. Multi-Scale Profiler
        </button>
        <button
          onClick={() => { setSubTab("comparison"); handleRunRegionComparison(); }}
          className={`px-3 py-1.5 rounded transition-colors ${
            subTab === "comparison"
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 font-bold"
              : "text-slate-400 hover:text-white"
          }`}
        >
          3. Region Comparison
        </button>
        <button
          onClick={() => { setSubTab("transition"); handleRunTransitionEvaluation(); }}
          className={`px-3 py-1.5 rounded transition-colors ${
            subTab === "transition"
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 font-bold"
              : "text-slate-400 hover:text-white"
          }`}
        >
          4. Transition Intelligence
        </button>
        <button
          onClick={() => { setSubTab("route"); handleRunRouteSourceEval(); }}
          className={`px-3 py-1.5 rounded transition-colors ${
            subTab === "route"
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 font-bold"
              : "text-slate-400 hover:text-white"
          }`}
        >
          5. Route Terrain Source
        </button>
      </div>

      {/* ── Sub-Tab 1: Resolution Selector ─────────────────────────────────── */}
      {subTab === "selector" && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-lg space-y-3 font-mono text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold text-white">Target Envelope & Mission Intent:</span>
              <div className="flex items-center gap-2">
                <select
                  value={analysisType}
                  onChange={(e) => setAnalysisType(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-200"
                >
                  <option value="traverse_planning">Traverse Planning (20-500m)</option>
                  <option value="regional_survey">Regional Survey (100-1000m)</option>
                  <option value="hazard_assessment">Hazard Assessment (20-50m)</option>
                  <option value="reconnaissance">Reconnaissance (&gt;1000m)</option>
                  <option value="site_inspection">Site Inspection (1m tactical)</option>
                </select>
                <button
                  onClick={handleRunResolutionSelection}
                  disabled={loading}
                  className="px-3 py-1 bg-orange-600 hover:bg-orange-500 text-white font-bold rounded"
                >
                  {loading ? "Selecting..." : "Evaluate Selection"}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div>
                <span className="text-slate-500">Min Lat:</span>
                <input
                  type="number"
                  step="0.1"
                  value={bbox.minLat}
                  onChange={(e) => setBbox({ ...bbox, minLat: parseFloat(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-0.5 mt-0.5 text-white"
                />
              </div>
              <div>
                <span className="text-slate-500">Max Lat:</span>
                <input
                  type="number"
                  step="0.1"
                  value={bbox.maxLat}
                  onChange={(e) => setBbox({ ...bbox, maxLat: parseFloat(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-0.5 mt-0.5 text-white"
                />
              </div>
              <div>
                <span className="text-slate-500">Min Lon:</span>
                <input
                  type="number"
                  step="0.1"
                  value={bbox.minLon}
                  onChange={(e) => setBbox({ ...bbox, minLon: parseFloat(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-0.5 mt-0.5 text-white"
                />
              </div>
              <div>
                <span className="text-slate-500">Max Lon:</span>
                <input
                  type="number"
                  step="0.1"
                  value={bbox.maxLon}
                  onChange={(e) => setBbox({ ...bbox, maxLon: parseFloat(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-0.5 mt-0.5 text-white"
                />
              </div>
            </div>
          </div>

          {selectorResult && (
            <div className="space-y-3 font-mono text-xs">
              {/* Primary Selection Banner */}
              <div className="bg-slate-950/80 border border-orange-500/40 p-3 rounded-lg space-y-2">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">Selected Product:</span>
                    <span className="text-sm font-bold text-orange-400">
                      {selectorResult.selected_product_id || "None (Insufficient Data)"}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Status: {selectorResult.status}
                    </span>
                  </div>
                  <div className="text-slate-400">
                    Native Res: <strong className="text-white">{selectorResult.native_resolution_m?.toFixed(2)} m/px</strong>
                  </div>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  {selectorResult.selection_rationale}
                </p>
                <div className="flex flex-wrap gap-4 pt-1 text-[11px] text-slate-400">
                  <span>Coverage: <strong className="text-emerald-400">{selectorResult.coverage_percentage}%</strong></span>
                  <span>Covered Area: <strong className="text-white">{selectorResult.covered_area_km2.toFixed(1)} km²</strong></span>
                  <span>Requested Area: <strong className="text-white">{selectorResult.requested_area_km2.toFixed(1)} km²</strong></span>
                </div>
              </div>

              {/* Candidate Evaluations Grid */}
              <div className="space-y-1.5">
                <div className="text-slate-400 font-bold">Evaluated Datasets & Lifecycle Gates:</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {selectorResult.evaluated_candidates.map((cand) => (
                    <div
                      key={cand.product_id}
                      className={`p-2.5 rounded border text-[11px] flex flex-col justify-between ${
                        cand.is_eligible
                          ? "bg-slate-900/80 border-emerald-800/60"
                          : "bg-slate-950/80 border-slate-800 opacity-75"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">{cand.product_id}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            cand.is_eligible
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                              : "bg-red-950 text-red-300 border border-red-700"
                          }`}
                        >
                          {cand.is_eligible ? "✓ Eligible" : "✗ Excluded"}
                        </span>
                      </div>
                      <div className="mt-1 text-slate-400 space-y-0.5">
                        <div>Resolution: {cand.native_resolution_m.toFixed(1)} m/px ({cand.tier})</div>
                        <div>Local Raster: {cand.is_locally_available ? "Yes (on disk)" : "No (0 local bytes)"}</div>
                        <div>Lifecycle: {cand.lifecycle_status} | Coverage: {cand.coverage_percentage}%</div>
                      </div>
                      {cand.disqualification_reason && (
                        <div className="mt-2 pt-1 border-t border-slate-800/80 text-[10px] text-amber-400">
                          {cand.disqualification_reason}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Sub-Tab 2: Multi-Scale Profiler ─────────────────────────────────── */}
      {subTab === "multiscale" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-3 rounded-lg font-mono text-xs">
            <div>
              <span className="font-bold text-white">Physical Analysis Windows:</span>
              <span className="text-slate-400 ml-2">100m, 500m, 1000m, 2000m</span>
            </div>
            <button
              onClick={handleRunMultiScaleProfile}
              disabled={loading}
              className="px-3 py-1 bg-cyan-700 hover:bg-cyan-600 text-white font-bold rounded"
            >
              {loading ? "Computing..." : "Run Multi-Scale Analysis"}
            </button>
          </div>

          {profileResult && (
            <div className="space-y-3 font-mono text-xs">
              <div className="bg-slate-950 p-3 rounded border border-slate-800 text-[11px] text-slate-300">
                {profileResult.cross_scale_summary}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {profileResult.scales.map((s) => (
                  <div key={s.window_m} className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg space-y-2">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                      <span className="text-sm font-bold text-cyan-300">
                        Window: {s.window_m.toFixed(0)}m ({s.neighborhood_pixels}x{s.neighborhood_pixels} px)
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          s.complexity_class === "low_complexity"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : s.complexity_class === "moderate_complexity"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-red-950 text-red-300 border border-red-800"
                        }`}
                      >
                        {s.complexity_class.replace("_", " ")}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div>Mean Slope: <strong className="text-white">{s.mean_slope_deg}°</strong></div>
                      <div>Max Slope: <strong className="text-white">{s.max_slope_deg}°</strong></div>
                      <div>Mean Roughness: <strong className="text-white">{s.mean_roughness_m}m</strong></div>
                      <div>Max Roughness: <strong className="text-white">{s.max_roughness_m}m</strong></div>
                      <div>Local Relief: <strong className="text-white">{s.mean_local_relief_m}m</strong></div>
                      <div>Elev Span: <strong className="text-white">[{s.min_elevation_m}m, {s.max_elevation_m}m]</strong></div>
                      {s.effective_analysis_scale_x_m && (
                        <div className="col-span-2 text-cyan-300">
                          Effective Footprint: <strong>{s.effective_analysis_scale_x_m.toFixed(0)}m × {s.effective_analysis_scale_y_m?.toFixed(0)}m</strong> ({s.effective_analysis_area_km2?.toFixed(2)} km²)
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
                      {s.scale_limitation && (
                        <div className="text-amber-400/90 mb-1">
                          ⚠️ {s.scale_limitation}
                        </div>
                      )}
                      {s.complexity_rationale}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Sub-Tab 3: Mission Region Comparison ───────────────────────────── */}
      {subTab === "comparison" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-3 rounded-lg font-mono text-xs">
            <div>
              <span className="font-bold text-white">Controlled Comparison Scale:</span>
              <span className="text-orange-400 font-bold ml-2">{targetScaleM} metres</span>
            </div>
            <button
              onClick={handleRunRegionComparison}
              disabled={loading}
              className="px-3 py-1 bg-purple-700 hover:bg-purple-600 text-white font-bold rounded"
            >
              {loading ? "Comparing..." : "Compare Candidate Regions"}
            </button>
          </div>

          {comparisonResult && (
            <div className="space-y-3 font-mono text-xs">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                {comparisonResult.regions_evaluated.map((r) => (
                  <div key={r.region_id} className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg space-y-2">
                    <div className="font-bold text-white text-sm">{r.name}</div>
                    <div className="text-[10px] text-slate-400">Source: {r.selected_dataset_id} ({r.native_resolution_m}m/px)</div>
                    <div className="space-y-1 text-[11px] pt-1 border-t border-slate-800">
                      <div>Mean Slope: <strong className="text-white">{r.mean_slope_deg}°</strong></div>
                      <div>Mean Roughness: <strong className="text-white">{r.mean_roughness_m}m</strong></div>
                      <div>Local Relief: <strong className="text-white">{r.mean_local_relief_m}m</strong></div>
                      <div>Valid Coverage: <strong className="text-emerald-400">{r.valid_data_coverage_pct}%</strong></div>
                      <div>Heuristic Quality Index: <strong className="text-orange-400">{r.terrain_data_quality_index ?? r.data_confidence_score}/100</strong></div>
                      {r.effective_analysis_scale_x_m && (
                        <div className="text-[10px] text-cyan-300">
                          Effective Scale: {r.effective_analysis_scale_x_m.toFixed(0)}m × {r.effective_analysis_scale_y_m?.toFixed(0)}m
                        </div>
                      )}
                    </div>
                    <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
                      {r.scientific_summary}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pairwise Contrasts */}
              <div className="space-y-2">
                <div className="font-bold text-slate-300">Pairwise Scientific Contrasts:</div>
                {comparisonResult.pairwise_comparisons.map((p, idx) => (
                  <div key={idx} className="bg-slate-950 p-2.5 rounded border border-slate-800 text-[11px] space-y-1">
                    <div className="text-cyan-400 font-bold">{p.comparative_summary}</div>
                    <div className="text-slate-400 flex flex-wrap gap-4 text-[10px]">
                      <span>{p.slope_contrast}</span>
                      <span>{p.roughness_contrast}</span>
                      <span>{p.resolution_contrast}</span>
                      {p.scale_compatibility && (
                        <span className="text-amber-400">Scale: {p.scale_compatibility.replace(/_/g, " ")}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Sub-Tab 4: Transition Intelligence ─────────────────────────────── */}
      {subTab === "transition" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-3 rounded-lg font-mono text-xs">
            <div>
              <span className="font-bold text-white">Transition Pair:</span>
              <span className="text-slate-400 ml-2">MOLA 128 ppd (463m) ⟷ USGS CTX DTM (20m)</span>
            </div>
            <button
              onClick={handleRunTransitionEvaluation}
              disabled={loading}
              className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 text-white font-bold rounded"
            >
              {loading ? "Evaluating..." : "Check Transition Compatibility"}
            </button>
          </div>

          {transitionResult && (
            <div className="space-y-3 font-mono text-xs bg-slate-900/80 border border-slate-800 p-3.5 rounded-lg">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Transition Status:</span>
                  <span className="px-2 py-0.5 rounded font-bold uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                    {transitionResult.transition_status}
                  </span>
                </div>
                <div className="text-slate-400">
                  Scale Drift: <strong className="text-amber-400">{transitionResult.horizontal_scale_drift_ppm} ppm</strong>
                </div>
              </div>

              <p className="text-[11px] text-slate-300 leading-relaxed">
                {transitionResult.scientific_justification}
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800 text-[11px]">
                <div>
                  <span className="text-emerald-400 font-bold">✓ Permitted Operations:</span>
                  <ul className="list-disc list-inside text-slate-400 mt-1 space-y-0.5">
                    {transitionResult.permitted_operations.map((op, i) => (
                      <li key={i}>{op.replace(/_/g, " ")}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="text-red-400 font-bold">✗ Strictly Forbidden:</span>
                  <ul className="list-disc list-inside text-slate-400 mt-1 space-y-0.5">
                    {transitionResult.forbidden_operations.map((op, i) => (
                      <li key={i}>{op.replace(/_/g, " ")}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {transitionResult.partition_strategy && (
                <div className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] bg-slate-950/60 p-2 rounded">
                  <span className="text-amber-300 font-bold">Region Partitioning Strategy:</span>
                  <p className="text-slate-300 mt-0.5">{transitionResult.partition_strategy.recommendation}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Sub-Tab 5: Route Terrain Source ─────────────────────────────────── */}
      {subTab === "route" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-3 rounded-lg font-mono text-xs">
            <div>
              <span className="font-bold text-white">Corridor Coordinates:</span>
              <span className="text-slate-400 ml-2">(14.2°S, 59.1°E) ➔ (14.0°S, 59.3°E)</span>
            </div>
            <button
              onClick={handleRunRouteSourceEval}
              disabled={loading}
              className="px-3 py-1 bg-orange-700 hover:bg-orange-600 text-white font-bold rounded"
            >
              {loading ? "Inspecting..." : "Inspect Route Terrain Source"}
            </button>
          </div>

          {routeSourceResult && (
            <div className="space-y-3 font-mono text-xs bg-slate-900/80 border border-slate-800 p-3.5 rounded-lg">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Routing Eligibility:</span>
                  <span
                    className={`px-2 py-0.5 rounded font-bold uppercase ${
                      routeSourceResult.routing_eligible
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : "bg-red-950 text-red-300 border border-red-800"
                    }`}
                  >
                    {routeSourceResult.routing_eligible ? "✓ Route Eligible" : "✗ Unsupported Corridor"}
                  </span>
                </div>
                <div className="text-slate-400">
                  Corridor Length: <strong className="text-white">{routeSourceResult.corridor_length_km} km</strong>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                <div>Primary Terrain Source: <strong className="text-orange-400">{routeSourceResult.primary_terrain_product}</strong></div>
                <div>Source Resolution: <strong className="text-white">{routeSourceResult.primary_resolution_m} m/px</strong></div>
                <div>Centerline Coverage: <strong className="text-emerald-400">{routeSourceResult.centerline_valid_coverage_pct ?? routeSourceResult.valid_data_coverage_pct}%</strong></div>
                <div>Corridor Envelope: <strong className="text-emerald-400">{routeSourceResult.corridor_envelope_valid_coverage_pct ?? routeSourceResult.valid_data_coverage_pct}%</strong></div>
                <div>Horizontal CRS: <strong className="text-white">{routeSourceResult.horizontal_crs}</strong></div>
                <div>Vertical Datum: <strong className="text-white">{routeSourceResult.vertical_datum}</strong></div>
                {routeSourceResult.nodata_intersections !== undefined && (
                  <div className="col-span-2 text-slate-400">
                    NoData Trajectory Gaps: <strong className={routeSourceResult.nodata_intersections > 0 ? "text-red-400" : "text-emerald-400"}>{routeSourceResult.nodata_intersections} points</strong>
                  </div>
                )}
              </div>

              <p className="text-[11px] text-slate-300 pt-1 border-t border-slate-800 leading-relaxed">
                {routeSourceResult.selection_rationale}
              </p>

              {routeSourceResult.unsupported_segments.length > 0 && (
                <div className="bg-red-950/40 border border-red-800/60 p-2 rounded text-[11px] text-red-300 space-y-0.5">
                  <span className="font-bold">Gaps / Unsupported Segments:</span>
                  {routeSourceResult.unsupported_segments.map((seg, i) => (
                    <div key={i}>• {seg}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
