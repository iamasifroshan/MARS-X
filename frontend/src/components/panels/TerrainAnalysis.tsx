"use client";

import { useEffect, useState } from "react";
import { 
  fetchElevationStats, 
  fetchTerrainCoverage, 
  fetchTerrainLayers, 
  fetchValidationReports,
  fetchMolaInventory,
  fetchCompatibilityAssessment,
  fetchTerrainHazards,
  fetchHazardMetadata,
} from "@/lib/api";
import { 
  ElevationStats, 
  TerrainCoverage, 
  TerrainLayerItem, 
  ProductValidationReport,
  Mola128InventoryReport,
  CompatibilityAssessmentResult,
  TerrainHazardPointMetrics,
  HazardEngineMetadata,
} from "@/lib/types";
import { MultiResolutionTerrain } from "./MultiResolutionTerrain";
import { TerrainIntelligencePanel } from "./TerrainIntelligencePanel";
import { TraversabilityPanel } from "./TraversabilityPanel";


interface TerrainAnalysisProps {
  currentCoordinates?: { lat: number; lon: number } | null;
}

export function TerrainAnalysis({ currentCoordinates }: TerrainAnalysisProps) {
  const [stats, setStats] = useState<ElevationStats | null>(null);
  const [coverage, setCoverage] = useState<TerrainCoverage | null>(null);
  const [layers, setLayers] = useState<TerrainLayerItem[]>([]);
  const [validationReports, setValidationReports] = useState<ProductValidationReport[]>([]);
  const [inventory, setInventory] = useState<Mola128InventoryReport | null>(null);
  const [compatibility, setCompatibility] = useState<CompatibilityAssessmentResult | null>(null);
  const [hazards, setHazards] = useState<TerrainHazardPointMetrics | null>(null);
  const [hazardMeta, setHazardMeta] = useState<HazardEngineMetadata | null>(null);
  
  const [selectedTab, setSelectedTab] = useState<"traversability" | "intelligence" | "multires" | "hazards" | "validation" | "inventory" | "compatibility" | "layers">("traversability");

  const [compatPair, setCompatPair] = useState<{ a: string; b: string }>({
    a: "mola-megdr-4",
    b: "hirise-dtm-jezero",
  });
  
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const queryLat = currentCoordinates?.lat ?? 18.65;
  const queryLon = currentCoordinates?.lon ?? 226.20;

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [
          statsData,
          coverageData,
          layersData,
          valData,
          invData,
          compatData,
          hazardData,
          metaData,
        ] = await Promise.all([
          fetchElevationStats(),
          fetchTerrainCoverage(queryLat, queryLon),
          fetchTerrainLayers(),
          fetchValidationReports(),
          fetchMolaInventory(),
          fetchCompatibilityAssessment(compatPair.a, compatPair.b),
          fetchTerrainHazards(queryLat, queryLon, "mola-megdr").catch(() => null),
          fetchHazardMetadata().catch(() => null),
        ]);

        setStats(statsData);
        setCoverage(coverageData);
        setLayers(layersData);
        setValidationReports(valData);
        setInventory(invData);
        setCompatibility(compatData);
        setHazards(hazardData);
        setHazardMeta(metaData);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load terrain intelligence");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [queryLat, queryLon, compatPair.a, compatPair.b]);

  return (
    <div className="space-y-4 text-sm text-slate-300">
      {/* Header and Sub-Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-white tracking-wide flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Mars Terrain Intelligence & Hazard Engine
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Phase 7 Multi-Resolution Planetary Hierarchy & Calibrated Hazard Engine
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center space-x-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs font-mono overflow-x-auto">
          <button
            onClick={() => setSelectedTab("traversability")}
            className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
              selectedTab === "traversability" ? "bg-orange-600 text-white font-bold shadow-md" : "text-slate-400 hover:text-white"
            }`}
          >
            Traversability (P8.8.1)
          </button>
          <button
            onClick={() => setSelectedTab("intelligence")}
            className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
              selectedTab === "intelligence" ? "bg-orange-950/80 text-orange-400 border border-orange-500/60 font-bold" : "text-slate-400 hover:text-white"
            }`}
          >
            Terrain Intelligence (P8)
          </button>
          <button
            onClick={() => setSelectedTab("multires")}
            className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
              selectedTab === "multires" ? "bg-cyan-950/80 text-cyan-300 border border-cyan-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            Multi-Res (4 Tiers)
          </button>

          <button
            onClick={() => setSelectedTab("hazards")}
            className={`px-2.5 py-1 rounded transition-colors ${
              selectedTab === "hazards" ? "bg-red-950/80 text-red-300 border border-red-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            Complexity
          </button>
          <button
            onClick={() => setSelectedTab("validation")}
            className={`px-2.5 py-1 rounded transition-colors ${
              selectedTab === "validation" ? "bg-blue-950/80 text-blue-300 border border-blue-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            Lifecycle ({validationReports.length})
          </button>
          <button
            onClick={() => setSelectedTab("inventory")}
            className={`px-2.5 py-1 rounded transition-colors ${
              selectedTab === "inventory" ? "bg-amber-950/80 text-amber-300 border border-amber-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            MOLA 128 ({inventory?.downloaded_tile_count ?? 0}/16)
          </button>
          <button
            onClick={() => setSelectedTab("compatibility")}
            className={`px-2.5 py-1 rounded transition-colors ${
              selectedTab === "compatibility" ? "bg-purple-950/80 text-purple-300 border border-purple-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            CRS & Datum
          </button>
          <button
            onClick={() => setSelectedTab("layers")}
            className={`px-2.5 py-1 rounded transition-colors ${
              selectedTab === "layers" ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60" : "text-slate-400 hover:text-white"
            }`}
          >
            DTMs
          </button>
        </div>
      </div>

      {loading && (
        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded text-xs text-slate-400 animate-pulse">
          Querying planetary elevation catalog and running geodetic validation...
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* 0. TRAVERSABILITY FOUNDATION (PHASE 8.8.1) */}
      {selectedTab === "traversability" && (
        <TraversabilityPanel currentCoordinates={currentCoordinates} />
      )}

      {/* 0. RESOLUTION-AWARE TERRAIN INTELLIGENCE (PHASE 8) */}
      {selectedTab === "intelligence" && (
        <TerrainIntelligencePanel currentCoordinates={currentCoordinates} />
      )}

      {/* 1. MULTI-RESOLUTION TERRAIN INTELLIGENCE */}
      {selectedTab === "multires" && (
        <MultiResolutionTerrain currentCoordinates={currentCoordinates} />
      )}


      {/* 1. TERRAIN COMPLEXITY & HAZARD INDICATORS */}
      {selectedTab === "hazards" && (
        <div className="space-y-3">
          {hazards ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-xs font-mono uppercase text-red-400 font-bold tracking-wider">
                    Terrain Complexity Indicators ({queryLat >= 0 ? `${queryLat.toFixed(2)}°N` : `${Math.abs(queryLat).toFixed(2)}°S`}, {queryLon.toFixed(2)}°E)
                  </span>
                  <div className="text-[11px] text-slate-400">
                    Source: <code className="text-emerald-300">{hazards.source_dataset}</code> (Window: {hazards.spatial_scale?.analysis_window_size_m?.toLocaleString() ?? "N/A"}m)
                  </div>
                </div>
                <span
                  className={`text-xs px-2.5 py-1 rounded font-mono font-bold uppercase ${
                    hazards.complexity_class === "low_measured_complexity"
                      ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800/50"
                      : hazards.complexity_class === "moderate_complexity"
                      ? "bg-amber-950/60 text-amber-300 border border-amber-800/50"
                      : hazards.complexity_class === "high_complexity"
                      ? "bg-orange-950/60 text-orange-300 border border-orange-800/50"
                      : hazards.complexity_class === "extreme_complexity"
                      ? "bg-red-950/60 text-red-300 border border-red-800/50"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {hazards.complexity_class.replace(/_/g, " ")}
                </span>
              </div>

              {/* Grid of indicators */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Topographic Slope</div>
                  <div className="text-base text-white font-bold mt-0.5">
                    {hazards.slope_deg !== null ? `${hazards.slope_deg}°` : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {hazards.slope_pct !== null ? `${hazards.slope_pct.toFixed(1)}% grade` : "NoData"}
                  </div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Local Relief (Δz)</div>
                  <div className="text-base text-cyan-300 font-bold mt-0.5">
                    {hazards.local_relief_m !== null ? `${hazards.local_relief_m} m` : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-400">Elevation range</div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Roughness (σz)</div>
                  <div className="text-base text-purple-300 font-bold mt-0.5">
                    {hazards.roughness_m !== null ? `${hazards.roughness_m} m` : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-400">Std deviation</div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Data Confidence</div>
                  <div className="text-base text-emerald-300 font-bold mt-0.5">
                    {(hazards.data_confidence_score * 100).toFixed(0)}%
                  </div>
                  <div className="text-[10px] text-slate-400">Authentic MOLA</div>
                </div>
              </div>

              {/* Spatial Scale Transparency Card */}
              {hazards.spatial_scale && (
                <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded text-xs space-y-1 font-mono">
                  <div className="flex items-center justify-between text-slate-400 text-[11px]">
                    <span>Pixel Spacing: <strong className="text-white">{hazards.spatial_scale.native_pixel_spacing_m}m</strong></span>
                    <span>Min Detectable Feature: <strong className="text-amber-400">{hazards.spatial_scale.minimum_detectable_feature_scale_m}m</strong></span>
                    <span>Tier: <strong className="text-cyan-400 uppercase">{hazards.spatial_scale.operational_scale_tier}</strong></span>
                  </div>
                  <div className="text-[10px] text-slate-400 italic">
                    {hazards.spatial_scale.scale_limitation_warning}
                  </div>
                </div>
              )}

              {/* Discontinuity banner if detected */}
              {hazards.discontinuity_detected && (
                <div className="bg-red-950/40 border border-red-700/60 p-2.5 rounded text-xs text-red-200 flex items-center justify-between">
                  <span className="font-semibold">⚠️ Topographic Discontinuity Detected:</span>
                  <span className="font-mono">{hazards.discontinuity_type}</span>
                </div>
              )}

              {/* Explainable Reasoning */}
              <div className="bg-slate-950/40 border border-slate-800/80 p-2.5 rounded text-xs text-slate-300 space-y-1">
                <div className="text-[10px] text-slate-400 uppercase font-mono font-semibold">
                  Classification Rationale:
                </div>
                <p>{hazards.explanation}</p>
              </div>

              {/* Scientific Disclaimer */}
              <div className="p-2 bg-slate-950/80 border border-amber-800/40 rounded text-[10px] text-amber-300/90 italic">
                {hazards.safety_disclaimer}
              </div>
            </div>
          ) : (
            <div className="p-4 bg-slate-900/60 border border-slate-800 rounded text-xs text-slate-400">
              No hazard calculations available for current coordinate. Check dataset ingestion.
            </div>
          )}

          {/* Algorithm Metadata Card */}
          {hazardMeta && (
            <div className="bg-slate-900/50 border border-slate-800 rounded p-3 text-[11px] text-slate-400 space-y-1 font-mono">
              <div className="text-slate-300 font-bold">Algorithms & Mathematical Basis:</div>
              <div>• Slope: {hazardMeta.slope_algorithm}</div>
              <div>• Relief: {hazardMeta.relief_algorithm}</div>
              <div>• Roughness: {hazardMeta.roughness_algorithm}</div>
            </div>
          )}
        </div>
      )}

      {/* 2. DATASET LIFECYCLE & VALIDATION PANEL */}
      {selectedTab === "validation" && (
        <div className="space-y-3">
          <div className="text-xs text-slate-400">
            Planetary datasets undergo formal verification before transitioning from catalogue records to analysis-ready rasters:
          </div>
          <div className="space-y-2">
            {validationReports.map((report) => (
              <div
                key={report.product_id}
                className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-white flex items-center gap-2">
                    <span>{report.product_id}</span>
                    <span className="text-[10px] text-slate-400 font-normal">({report.instrument} • {report.source_archive})</span>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase ${
                      report.is_analysis_ready
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                        : report.lifecycle_state === "discovered"
                        ? "bg-blue-950 text-blue-300 border border-blue-800/60"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {report.lifecycle_state}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono text-slate-400">
                  <div>Res: <span className="text-slate-200">{report.native_resolution_desc}</span></div>
                  <div>CRS: <span className="text-slate-200">{report.horizontal_crs.split(" ")[0]}</span></div>
                  <div>Datum: <span className="text-slate-200">{report.vertical_datum.split(" ")[0]}</span></div>
                  <div>Raster: <span className={report.raster_available_locally ? "text-emerald-400" : "text-amber-400"}>
                    {report.raster_available_locally ? "✓ On Disk" : "✗ Catalog Only"}
                  </span></div>
                </div>

                {report.evidence_checks.length > 0 && (
                  <div className="border-t border-slate-800/80 pt-1.5 space-y-1">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Validation Checks:</div>
                    {report.evidence_checks.map((c, i) => (
                      <div key={i} className="text-[11px] text-slate-300 flex items-center justify-between">
                        <span>• {c.check_name}: {c.details}</span>
                        <span className="text-emerald-400 font-mono">PASS</span>
                      </div>
                    ))}
                  </div>
                )}

                {report.unresolved_limitations.length > 0 && (
                  <div className="text-[10px] text-amber-400/90 italic">
                    ⚠️ {report.unresolved_limitations[0]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. MOLA 128 TILE INVENTORY PANEL */}
      {selectedTab === "inventory" && inventory && (
        <div className="space-y-3">
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-mono uppercase text-amber-400 font-bold">
                MOLA MEG128 Tile Repository (16 Quadrant Tiles)
              </span>
              <span className="text-xs font-mono text-emerald-400 font-bold">
                {inventory.downloaded_tile_coverage_pct.toFixed(2)}% Downloaded on Disk
              </span>
            </div>

            {/* Separated coverage metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono pt-1">
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Theoretical Archive</span>
                <span className="text-slate-300 font-bold">{inventory.theoretical_archive_coverage_pct.toFixed(2)}%</span>
                <span className="text-[9px] text-slate-500 block">Excludes |lat| &gt; 88°</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Downloaded on Disk</span>
                <span className="text-emerald-400 font-bold">{inventory.downloaded_tile_coverage_pct.toFixed(2)}%</span>
                <span className="text-[9px] text-slate-500 block">{inventory.downloaded_tile_count}/16 tiles</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">SHA-256 Verified</span>
                <span className="text-cyan-400 font-bold">{inventory.integrity_verified_coverage_pct.toFixed(2)}%</span>
                <span className="text-[9px] text-slate-500 block">{inventory.integrity_verified_tile_count}/16 tiles</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Scientifically Validated</span>
                <span className="text-purple-400 font-bold">{inventory.scientifically_validated_coverage_pct.toFixed(2)}%</span>
                <span className="text-[9px] text-slate-500 block">{inventory.scientifically_validated_tile_count}/16 tiles</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 pt-1">
              {inventory.coverage_calculation_method}
            </p>
          </div>

          {/* Tile Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {inventory.tiles.map((tile) => (
              <div
                key={tile.tile_id}
                className={`p-2.5 rounded border transition-all ${
                  tile.is_downloaded
                    ? "bg-emerald-950/30 border-emerald-500/50 text-white"
                    : "bg-slate-950/40 border-slate-800/80 text-slate-400"
                }`}
              >
                <div className="font-mono font-bold flex items-center justify-between">
                  <span>{tile.tile_id}</span>
                  <span className={`text-[9px] uppercase px-1 py-0.5 rounded ${tile.is_downloaded ? "bg-emerald-900 text-emerald-300" : "bg-slate-900 text-slate-500"}`}>
                    {tile.is_downloaded ? "INGESTED" : "REMOTE"}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono mt-1">
                  Spherical Area: {tile.spherical_area_fraction_pct.toFixed(2)}%
                </div>
                <div className="text-[10px] text-slate-500 font-mono">
                  Lat: [{tile.lat_min}°, {tile.lat_max}°] • Lon: [{tile.lon_min}°, {tile.lon_max}°E]
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. CRS & VERTICAL DATUM COMPATIBILITY PANEL */}
      {selectedTab === "compatibility" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Compare Pair:</span>
            <select
              value={compatPair.a}
              onChange={(e) => setCompatPair({ ...compatPair, a: e.target.value })}
              className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
            >
              <option value="mola-megdr-4">MOLA MEGDR 4</option>
              <option value="mola-megdr-128">MOLA MEGDR 128</option>
            </select>
            <span className="text-slate-500">vs</span>
            <select
              value={compatPair.b}
              onChange={(e) => setCompatPair({ ...compatPair, b: e.target.value })}
              className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
            >
              <option value="hirise-dtm-jezero">HiRISE Jezero</option>
              <option value="ctx-dtm-jezero">CTX Jezero</option>
              <option value="hrsc-dtm-mc11">HRSC MC-11</option>
              <option value="mola-megdr-128">MOLA MEGDR 128</option>
            </select>
          </div>

          {compatibility && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-mono text-purple-400 uppercase font-bold">
                  Compatibility Assessment
                </span>
                <span
                  className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold ${
                    compatibility.decision === "permitted_direct"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      : "bg-red-950 text-red-300 border border-red-800"
                  }`}
                >
                  {compatibility.decision.replace(/_/g, " ")}
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between border-b border-slate-800/80 pb-1">
                  <span className="text-slate-400">Horizontal CRS:</span>
                  <span className="font-mono text-slate-200">{compatibility.horizontal_status}</span>
                </div>
                <div className="text-[11px] text-slate-400 italic">
                  {compatibility.horizontal_notes}
                </div>

                <div className="flex justify-between border-b border-slate-800/80 pb-1 pt-1">
                  <span className="text-slate-400">Vertical Datum:</span>
                  <span className="font-mono text-slate-200">{compatibility.vertical_status}</span>
                </div>
                <div className="text-[11px] text-slate-400 italic">
                  {compatibility.vertical_notes}
                </div>

                <div className="flex justify-between border-b border-slate-800/80 pb-1 pt-1">
                  <span className="text-slate-400">Resolution Scale Ratio:</span>
                  <span className="font-mono text-emerald-400 font-bold">{compatibility.resolution_ratio.toFixed(1)}x</span>
                </div>
              </div>

              {compatibility.reasons_blocked.length > 0 && (
                <div className="p-2.5 bg-red-950/40 border border-red-800/60 rounded text-[11px] text-red-300 space-y-1">
                  <span className="font-bold block">Comparison / Fusion Blocked:</span>
                  {compatibility.reasons_blocked.map((r, idx) => (
                    <div key={idx}>• {r}</div>
                  ))}
                </div>
              )}

              <div className="p-2 bg-slate-950/60 border border-slate-800/60 rounded text-[10px] text-slate-400 font-mono">
                {compatibility.preservation_guarantee}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. MULTI-RESOLUTION DTM LAYERS PANEL */}
      {selectedTab === "layers" && (
        <div className="space-y-2">
          {layers.map((layer) => (
            <div
              key={layer.layer_id}
              className="p-3 rounded border bg-slate-950/40 border-slate-800 text-xs space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">{layer.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-800 text-slate-300 uppercase">
                  {layer.product_type}
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                <span>Res: {layer.ground_spacing_m.toFixed(1)} m/px</span>
                <span>•</span>
                <span>CRS: {layer.crs}</span>
                <span>•</span>
                <span>Datum: {layer.vertical_datum}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
