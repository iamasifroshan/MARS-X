"use client";

import { useEffect, useState } from "react";
import { 
  fetchElevationStats, 
  fetchTerrainCoverage, 
  fetchTerrainLayers, 
  compareTerrainResolutions 
} from "@/lib/api";
import { 
  ElevationStats, 
  TerrainCoverage, 
  TerrainLayerItem, 
  ResolutionComparison 
} from "@/lib/types";

interface TerrainAnalysisProps {
  currentCoordinates?: { lat: number; lon: number } | null;
}

export function TerrainAnalysis({ currentCoordinates }: TerrainAnalysisProps) {
  const [stats, setStats] = useState<ElevationStats | null>(null);
  const [coverage, setCoverage] = useState<TerrainCoverage | null>(null);
  const [layers, setLayers] = useState<TerrainLayerItem[]>([]);
  const [selectedLayerId, setSelectedLayerId] = useState<string>("mola-megdr-128-tile-00n000");
  const [comparison, setComparison] = useState<ResolutionComparison | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const queryLat = currentCoordinates?.lat ?? 18.38;
  const queryLon = currentCoordinates?.lon ?? 77.58;

  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoading(true);
        const [statsData, coverageData, layersData] = await Promise.all([
          fetchElevationStats(),
          fetchTerrainCoverage(queryLat, queryLon),
          fetchTerrainLayers(),
        ]);
        setStats(statsData);
        setCoverage(coverageData);
        setLayers(layersData);

        // Fetch comparison between MOLA 128 and HiRISE
        const cmp = await compareTerrainResolutions("mola-megdr-128", "hirise-dtm-jezero");
        setComparison(cmp);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load terrain intelligence");
      } finally {
        setLoading(false);
      }
    }
    loadInitialData();
  }, [queryLat, queryLon]);

  return (
    <div className="space-y-6 text-sm text-slate-300">
      <div>
        <h3 className="text-base font-semibold text-white tracking-wide flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          Multi-Resolution Terrain Engine
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Authentic planetary DTM hierarchy with anti-upsampling protection and strict Mars CRS bounds.
        </p>
      </div>

      {loading && (
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded animate-pulse text-xs text-slate-400">
          Querying planetary elevation catalog and inspecting footprints...
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Multi-Resolution Layer Hierarchy */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
            Available DTM Layers ({layers.length})
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
            CRS: EPSG:104905
          </span>
        </div>

        <div className="grid grid-cols-1 gap-2">
          {layers.map((layer) => {
            const isSelected = layer.layer_id === selectedLayerId;
            return (
              <div
                key={layer.layer_id}
                onClick={() => setSelectedLayerId(layer.layer_id)}
                className={`cursor-pointer p-2.5 rounded border transition-all text-xs ${
                  isSelected
                    ? "bg-emerald-950/30 border-emerald-500/50 text-white"
                    : "bg-slate-950/40 border-slate-800/80 hover:border-slate-700 text-slate-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{layer.name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                      layer.product_type === "elevation"
                        ? "bg-purple-900/50 text-purple-300 border border-purple-700/50"
                        : layer.product_type === "slope"
                        ? "bg-blue-900/50 text-blue-300 border border-blue-700/50"
                        : "bg-amber-900/50 text-amber-300 border border-amber-700/50"
                    }`}
                  >
                    {layer.product_type.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-400 font-mono">
                  <span>Res: {layer.ground_spacing_m.toFixed(1)} m/px</span>
                  <span>|</span>
                  <span>Datum: {layer.vertical_datum}</span>
                  <span>|</span>
                  <span className={layer.is_available ? "text-emerald-400" : "text-amber-400"}>
                    {layer.is_available ? "✓ Available" : "Catalog Ref"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Coordinate Footprint Inspection */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-2">
        <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
          Point Footprint Intersection
        </span>
        <div className="text-xs text-slate-400">
          Coordinates: <code className="text-cyan-300">{queryLat.toFixed(4)}°N, {queryLon.toFixed(4)}°E</code>
        </div>
        {coverage ? (
          <div className="space-y-2 pt-1">
            <div className="text-xs">
              <span className="text-slate-400">Highest Available Resolution: </span>
              <span className="text-white font-mono font-semibold">
                {coverage.finest_available_resolution_m ? `${coverage.finest_available_resolution_m} m/px` : "N/A"}
              </span>
            </div>
            <div className="text-xs text-slate-400">
              Intersecting Products:
              <ul className="mt-1 space-y-1">
                {coverage.covering_dtms?.map((p) => (
                  <li key={p.id} className="font-mono text-[11px] text-slate-300 flex items-center justify-between bg-slate-950/30 px-2 py-1 rounded">
                    <span>{p.name} ({p.id})</span>
                    <span className="text-emerald-400">{p.pixel_spacing_m} m/px</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500">Checking coverage...</div>
        )}
      </div>

      {/* Anti-Upsampling & Resolution Comparison */}
      {comparison && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-purple-400 uppercase tracking-wider">
              Anti-Upsampling Guard
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/50 font-mono">
              Scientific Integrity
            </span>
          </div>

          <div className="text-xs space-y-2">
            <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
              <span className="text-slate-400">Baseline Product:</span>
              <span className="font-mono text-slate-200">{comparison.product_a}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
              <span className="text-slate-400">Comparison Product:</span>
              <span className="font-mono text-slate-200">{comparison.product_b}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
              <span className="text-slate-400">Resolution Ratio:</span>
              <span className="font-mono text-emerald-400 font-bold">
                {comparison.resolution_ratio.toFixed(1)}x detail disparity
              </span>
            </div>
            <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
              <span className="text-slate-400">Vertical Datum Aligned:</span>
              <span className={`font-mono ${comparison.vertical_datum_compatible ? "text-emerald-400" : "text-red-400"}`}>
                {comparison.vertical_datum_compatible ? "✓ Both GMM-3 Areoid" : "⚠ Datum Mismatch"}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 bg-slate-950/40 p-2 rounded border border-slate-800/50 italic">
            "{comparison.anti_upsampling_notice}"
          </p>
        </div>
      )}

      {/* Physical Elevation Statistics */}
      {stats && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-2">
          <span className="text-xs font-mono text-amber-400 uppercase tracking-wider">
            Verified Physical Elevations ({stats.source_dataset})
          </span>
          <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-xs">
            <div className="bg-slate-950/50 p-2 rounded border border-slate-800/60">
              <div className="text-[10px] text-slate-500 uppercase">Min Elevation</div>
              <div className="text-cyan-300 font-semibold">{stats.min_elevation_m.toLocaleString()} m</div>
              <div className="text-[9px] text-slate-500 mt-0.5">Hellas Basin depth</div>
            </div>
            <div className="bg-slate-950/50 p-2 rounded border border-slate-800/60">
              <div className="text-[10px] text-slate-500 uppercase">Max Elevation</div>
              <div className="text-emerald-300 font-semibold">{stats.max_elevation_m.toLocaleString()} m</div>
              <div className="text-[9px] text-slate-500 mt-0.5">Olympus Mons summit</div>
            </div>
            <div className="bg-slate-950/50 p-2 rounded border border-slate-800/60">
              <div className="text-[10px] text-slate-500 uppercase">Mean Elevation</div>
              <div className="text-slate-200 font-semibold">{stats.mean_elevation_m.toFixed(1)} m</div>
              <div className="text-[9px] text-slate-500 mt-0.5">Global areoid mean</div>
            </div>
            <div className="bg-slate-950/50 p-2 rounded border border-slate-800/60">
              <div className="text-[10px] text-slate-500 uppercase">Valid Pixels</div>
              <div className="text-slate-200 font-semibold">{stats.valid_pixel_count.toLocaleString()}</div>
              <div className="text-[9px] text-slate-500 mt-0.5">100% valid coverage</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
