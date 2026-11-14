"use client";

import { useEffect, useState } from "react";
import {
  fetchTerrainProducts,
  fetchCoverageRegion,
  fetchProductOverlap,
  compareProductsElevation,
  fetchRoutingDataAvailability,
} from "@/lib/api";
import {
  DTMProductProfile,
  ProductOverlapResult,
  RasterElevationComparisonResult,
  RegionCoverageResult,
  RoutingDataAvailability,
} from "@/lib/types";

interface MultiResolutionTerrainProps {
  currentCoordinates?: { lat: number; lon: number } | null;
}

export function MultiResolutionTerrain({ currentCoordinates }: MultiResolutionTerrainProps) {
  const [products, setProducts] = useState<DTMProductProfile[]>([]);
  const [regionCoverage, setRegionCoverage] = useState<RegionCoverageResult | null>(null);
  const [routingAvailability, setRoutingAvailability] = useState<RoutingDataAvailability | null>(null);
  const [overlapResult, setOverlapResult] = useState<ProductOverlapResult | null>(null);
  const [comparisonResult, setComparisonResult] = useState<RasterElevationComparisonResult | null>(null);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [comparing, setComparing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Region inspection bounding box
  const [bbox, setBbox] = useState({
    minLat: -5.5,
    minLon: 65.5,
    maxLat: -3.8,
    maxLon: 67.0,
  });

  // Presets for quick selection
  const presets = [
    {
      name: "USGS CTX Overlap Region (Tyrrhena)",
      minLat: -5.25,
      minLon: 66.0,
      maxLat: -3.95,
      maxLon: 66.7,
    },
    {
      name: "Schiaparelli Crater (HiRISE)",
      minLat: -1.5,
      minLon: 13.5,
      maxLat: -0.5,
      maxLon: 14.5,
    },
    {
      name: "Jezero Crater Delta (MOLA 128 / CTX)",
      minLat: 18.0,
      minLon: 76.5,
      maxLat: 19.5,
      maxLon: 78.5,
    },
    {
      name: "Valles Marineris Regional",
      minLat: -15.0,
      minLon: 60.0,
      maxLat: -5.0,
      maxLon: 80.0,
    },
  ];

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const [prods, cov, rout, ovlp] = await Promise.all([
          fetchTerrainProducts(),
          fetchCoverageRegion(bbox.minLat, bbox.minLon, bbox.maxLat, bbox.maxLon),
          fetchRoutingDataAvailability(bbox.minLat, bbox.minLon, bbox.maxLat, bbox.maxLon),
          fetchProductOverlap("mola-megdr-128", "ctx-dtm-p21-009323"),
        ]);
        setProducts(prods);
        setRegionCoverage(cov);
        setRoutingAvailability(rout);
        setOverlapResult(ovlp);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load multi-resolution data");
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, []);

  const handleQueryRegion = async () => {
    try {
      setLoading(true);
      setError(null);
      const [cov, rout] = await Promise.all([
        fetchCoverageRegion(bbox.minLat, bbox.minLon, bbox.maxLat, bbox.maxLon),
        fetchRoutingDataAvailability(bbox.minLat, bbox.minLon, bbox.maxLat, bbox.maxLon),
      ]);
      setRegionCoverage(cov);
      setRoutingAvailability(rout);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to query region coverage");
    } finally {
      setLoading(false);
    }
  };

  const handleRunRealComparison = async () => {
    try {
      setComparing(true);
      setError(null);
      const res = await compareProductsElevation("mola-megdr-128", "ctx-dtm-p21-009323", 100);
      setComparisonResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Elevation comparison failed");
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="space-y-4 text-sm text-slate-300 font-sans">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-white tracking-wide flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            Multi-Resolution Mars Terrain Intelligence (Phase 7)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Controlled Planetary Elevation Hierarchy: Global MOLA (463m) ➔ USGS CTX DTM (20m) ➔ HiRISE (1m)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 rounded font-bold">
            Anti-Upsampling Enforced
          </span>
          <span className="px-2.5 py-1 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 rounded font-bold">
            Areoid Datum Tied
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300 font-mono">
          {error}
        </div>
      )}

      {/* 1. Controlled Hierarchy 4-Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 text-xs font-mono">
        {/* Tier 1 */}
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg flex flex-col justify-between">
          <div>
            <div className="text-[10px] text-cyan-400 uppercase font-bold tracking-wider">Tier 1: Global Coarse</div>
            <div className="text-sm font-bold text-white mt-1">MOLA MEGDR 4 ppd</div>
            <div className="text-slate-400 text-[11px] mt-0.5">Spacing: 14,818 m/px</div>
            <div className="text-slate-500 text-[10px] mt-1">Global reference baseline (-88° to +88°)</div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 font-bold">
              Available (100%)
            </span>
            <span className="text-[10px] text-slate-500">IAU:49900</span>
          </div>
        </div>

        {/* Tier 2 */}
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg flex flex-col justify-between">
          <div>
            <div className="text-[10px] text-emerald-400 uppercase font-bold tracking-wider">Tier 2: Global Base</div>
            <div className="text-sm font-bold text-white mt-1">MOLA MEGDR 128 ppd</div>
            <div className="text-slate-400 text-[11px] mt-0.5">Spacing: 463.08 m/px</div>
            <div className="text-slate-500 text-[10px] mt-1">Acquired: 3 tiles (26.05% Mars sphere)</div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 font-bold">
              3 Tiles Validated
            </span>
            <span className="text-[10px] text-slate-500">MOLA Areoid</span>
          </div>
        </div>

        {/* Tier 3 */}
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg flex flex-col justify-between">
          <div>
            <div className="text-[10px] text-amber-400 uppercase font-bold tracking-wider">Tier 3: Regional High-Res</div>
            <div className="text-sm font-bold text-white mt-1">USGS Controlled CTX DTM</div>
            <div className="text-slate-400 text-[11px] mt-0.5">Spacing: 20.01 m/px</div>
            <div className="text-slate-500 text-[10px] mt-1">Tyrrhena Terra (3472x1692 float32)</div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/50 text-amber-300 font-bold">
              Analysis Ready
            </span>
            <span className="text-[10px] text-slate-500">ASP Tied</span>
          </div>
        </div>

        {/* Tier 4 */}
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg flex flex-col justify-between">
          <div>
            <div className="text-[10px] text-purple-400 uppercase font-bold tracking-wider">Tier 4: Local Tactical</div>
            <div className="text-sm font-bold text-white mt-1">HiRISE Controlled DTM</div>
            <div className="text-slate-400 text-[11px] mt-0.5">Spacing: 1.01 m/px</div>
            <div className="text-slate-500 text-[10px] mt-1">Schiaparelli / Jezero Delta (Meter-scale)</div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/50 text-blue-300 font-bold">
              Discovered
            </span>
            <span className="text-[10px] text-slate-500">Stereo Tied</span>
          </div>
        </div>
      </div>

      {/* 2. Real Raster Elevation Comparison Tool */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-2">
          <div>
            <span className="text-xs font-mono uppercase text-cyan-400 font-bold tracking-wider flex items-center gap-2">
              🔬 Authentic Raster-to-Raster Elevation Delta Analysis
            </span>
            <div className="text-[11px] text-slate-400">
              Cross-evaluates real overlapping pixels: <code className="text-emerald-300">mola-megdr-128</code> (463m) vs <code className="text-amber-300">ctx-dtm-p21-009323</code> (20m)
            </div>
          </div>
          <button
            onClick={handleRunRealComparison}
            disabled={comparing}
            className="px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 disabled:bg-slate-800 text-white font-mono text-xs font-bold rounded transition-colors flex items-center gap-1.5"
          >
            {comparing ? (
              <>
                <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
                <span>Extracting Rasters...</span>
              </>
            ) : (
              <span>Execute Real Elevation Comparison</span>
            )}
          </button>
        </div>

        {overlapResult && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono bg-slate-950/60 p-2.5 rounded border border-slate-800">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Overlap Status</span>
              <div className="text-white font-bold">{overlapResult.has_overlap ? "Confirmed Overlap" : "No Overlap"}</div>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Overlap Area</span>
              <div className="text-cyan-300 font-bold">{overlapResult.overlap_area_km2.toLocaleString()} km²</div>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Resolution Scale</span>
              <div className="text-amber-300 font-bold">{overlapResult.relative_resolution_ratio}x (20m vs 463m)</div>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Local Rasters</span>
              <div className="text-emerald-300 font-bold">Both Available on Disk</div>
            </div>
          </div>
        )}

        {comparisonResult && (
          <div className="space-y-3 pt-2">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs font-mono">
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-500">Sample Points</div>
                <div className="text-sm font-bold text-white">{comparisonResult.sample_points_count} points</div>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-500">MOLA Mean Elevation</div>
                <div className="text-sm font-bold text-emerald-300">{comparisonResult.mean_elevation_a_m.toFixed(1)} m</div>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-500">CTX DTM Mean Elevation</div>
                <div className="text-sm font-bold text-amber-300">{comparisonResult.mean_elevation_b_m.toFixed(1)} m</div>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-500">Mean Delta (MOLA - CTX)</div>
                <div className="text-sm font-bold text-cyan-300">{comparisonResult.mean_delta_m.toFixed(2)} m</div>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-500">Delta Std Dev (σ)</div>
                <div className="text-sm font-bold text-purple-300">{comparisonResult.std_delta_m.toFixed(2)} m</div>
              </div>
            </div>

            <div className="bg-slate-950/80 border border-slate-800 p-3 rounded text-xs font-mono">
              <div className="text-[10px] text-slate-400 font-bold uppercase mb-1">Scientific Geodesy Interpretation</div>
              <div className="text-slate-300 leading-relaxed">{comparisonResult.scientific_interpretation}</div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Interactive Region Coverage & Routing Eligibility Inspector */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-2">
          <div>
            <span className="text-xs font-mono uppercase text-emerald-400 font-bold tracking-wider">
              🗺️ Regional Terrain Coverage & Route-Planning Eligibility
            </span>
            <div className="text-[11px] text-slate-400">
              Query geographic footprints for elevation data availability across all multi-resolution tiers
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {presets.map((p) => (
              <button
                key={p.name}
                onClick={() => {
                  setBbox({
                    minLat: p.minLat,
                    minLon: p.minLon,
                    maxLat: p.maxLat,
                    maxLon: p.maxLon,
                  });
                }}
                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono rounded transition-colors"
              >
                {p.name.split(" (")[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Bounding box input controls */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs font-mono items-end">
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">Min Lat (°)</label>
            <input
              type="number"
              step="0.1"
              value={bbox.minLat}
              onChange={(e) => setBbox({ ...bbox, minLat: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">Min Lon (°E)</label>
            <input
              type="number"
              step="0.1"
              value={bbox.minLon}
              onChange={(e) => setBbox({ ...bbox, minLon: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">Max Lat (°)</label>
            <input
              type="number"
              step="0.1"
              value={bbox.maxLat}
              onChange={(e) => setBbox({ ...bbox, maxLat: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">Max Lon (°E)</label>
            <input
              type="number"
              step="0.1"
              value={bbox.maxLon}
              onChange={(e) => setBbox({ ...bbox, maxLon: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white"
            />
          </div>
          <div>
            <button
              onClick={handleQueryRegion}
              disabled={loading}
              className="w-full py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:bg-slate-800 text-white font-mono text-xs font-bold rounded transition-colors"
            >
              {loading ? "Inspecting..." : "Inspect Region"}
            </button>
          </div>
        </div>

        {/* Coverage & Eligibility Results */}
        {routingAvailability && (
          <div className="bg-slate-950/60 border border-slate-800 p-3 rounded space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Route-Planning Eligibility:</span>
                <span
                  className={`px-2 py-0.5 rounded font-bold uppercase text-[11px] ${
                    routingAvailability.routing_eligible
                      ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60"
                      : "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                  }`}
                >
                  {routingAvailability.routing_eligible ? "✓ Fully Eligible" : "⚠ Limited Coverage"}
                </span>
              </div>
              <div className="text-slate-400">
                Highest Available: <strong className="text-cyan-300">{routingAvailability.highest_available_resolution_m} m/px</strong>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-slate-500">Available Tiers in Region:</span>
                <div className="flex gap-1.5 mt-1">
                  {routingAvailability.available_tiers.map((t) => (
                    <span key={t} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-slate-500">Recommended Product for Planning:</span>
                <div className="text-white font-bold mt-1">
                  <code className="text-amber-300">{routingAvailability.recommended_product}</code>
                </div>
              </div>
            </div>

            {/* Scientific Notes */}
            <div className="mt-2 pt-2 border-t border-slate-800/80 space-y-1">
              {routingAvailability.scientific_notes.map((note, idx) => (
                <div key={idx} className="text-[10px] text-slate-400 flex items-start gap-1.5">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

