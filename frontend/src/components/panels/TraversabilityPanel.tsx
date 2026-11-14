"use client";

import React, { useEffect, useState } from "react";
import {
  fetchTraversabilityMetadata,
  fetchTraversabilityPoint,
  fetchTraversabilityWindow,
  fetchTraversabilityCoverage,
  fetchTraversabilityLegend,
} from "../../lib/api";
import {
  TraversabilityMetadata,
  TraversabilityPointResult,
  TraversabilityWindowResult,
  TraversabilityCoverageEntry,
  TraversabilityLegendEntry,
} from "../../lib/types";

interface TraversabilityPanelProps {
  currentCoordinates?: { lat: number; lon: number } | null;
}

export const TraversabilityPanel: React.FC<TraversabilityPanelProps> = ({
  currentCoordinates,
}) => {
  const [activeLat, setActiveLat] = useState<number>(currentCoordinates?.lat ?? -4.600);
  const [activeLon, setActiveLon] = useState<number>(currentCoordinates?.lon ?? 66.317);
  const [inputLat, setInputLat] = useState<string>(activeLat.toFixed(4));
  const [inputLon, setInputLon] = useState<string>(activeLon.toFixed(4));

  const [pointData, setPointData] = useState<TraversabilityPointResult | null>(null);
  const [metadata, setMetadata] = useState<TraversabilityMetadata | null>(null);
  const [coverageList, setCoverageList] = useState<TraversabilityCoverageEntry[]>([]);
  const [legendList, setLegendList] = useState<TraversabilityLegendEntry[]>([]);
  const [windowData, setWindowData] = useState<TraversabilityWindowResult | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [pointLoading, setPointLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Sync external coordinates
  useEffect(() => {
    if (currentCoordinates) {
      setActiveLat(currentCoordinates.lat);
      setActiveLon(currentCoordinates.lon);
      setInputLat(currentCoordinates.lat.toFixed(4));
      setInputLon(currentCoordinates.lon.toFixed(4));
    }
  }, [currentCoordinates]);

  // Initial load
  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        const [meta, cov, leg] = await Promise.all([
          fetchTraversabilityMetadata(),
          fetchTraversabilityCoverage(),
          fetchTraversabilityLegend(),
        ]);
        setMetadata(meta);
        setCoverageList(cov);
        setLegendList(leg);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load traversability metadata");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  // Query point whenever activeLat / activeLon change
  useEffect(() => {
    async function query() {
      setPointLoading(true);
      try {
        const pt = await fetchTraversabilityPoint(activeLat, activeLon);
        setPointData(pt);

        // Also query small window around point (±0.5° lat/lon)
        const dSpan = 0.4;
        const win = await fetchTraversabilityWindow(
          activeLat - dSpan,
          activeLat + dSpan,
          (activeLon - dSpan + 360) % 360,
          (activeLon + dSpan + 360) % 360,
          24,
          12
        ).catch(() => null);
        setWindowData(win);
      } catch (err: unknown) {
        console.error("Traversability point query error:", err);
      } finally {
        setPointLoading(false);
      }
    }
    query();
  }, [activeLat, activeLon]);

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const latNum = parseFloat(inputLat);
    const lonNum = parseFloat(inputLon);
    if (!isNaN(latNum) && !isNaN(lonNum)) {
      setActiveLat(latNum);
      setActiveLon(lonNum);
    }
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "low":
        return { bg: "bg-emerald-950/70", text: "text-emerald-300", border: "border-emerald-700/60", badge: "bg-emerald-500" };
      case "moderate":
        return { bg: "bg-amber-950/70", text: "text-amber-300", border: "border-amber-700/60", badge: "bg-amber-500" };
      case "high":
        return { bg: "bg-orange-950/70", text: "text-orange-300", border: "border-orange-700/60", badge: "bg-orange-500" };
      case "very_high":
        return { bg: "bg-purple-950/70", text: "text-purple-300", border: "border-purple-700/60", badge: "bg-purple-600" };
      default:
        return { bg: "bg-slate-900/80", text: "text-slate-400", border: "border-slate-700/60", badge: "bg-slate-500" };
    }
  };

  const quickJumpSites = [
    { name: "Tyrrhena Terra CTX (20m)", lat: -4.600, lon: 66.317 },
    { name: "Apollinaris Sulci CTX (20m)", lat: 4.700, lon: 168.250 },
    { name: "Holden Crater HiRISE (1m)", lat: -28.500, lon: 309.020 },
    { name: "Olympus Mons Caldera", lat: 18.650, lon: 226.200 },
    { name: "Gale Crater (Curiosity)", lat: -4.589, lon: 137.441 },
  ];

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* 1. Mandatory Scientific Safety Warning Banner */}
      <div className="bg-amber-950/40 border border-amber-500/60 rounded-lg p-3 text-amber-200">
        <div className="flex items-center space-x-2 font-bold uppercase text-[11px] mb-1">
          <span className="text-amber-400 text-sm">⚠️</span>
          <span>Scientific Traversability & Safety Notice</span>
        </div>
        <p className="text-[10px] text-amber-200/90 leading-relaxed">
          Slope bands are <strong>analytical terrain classifications</strong> derived from orbital DEM models.
          They do <strong>NOT</strong> establish astronaut safety, EVA feasibility, spacesuit biomechanical clearance,
          or soil bearing strength. Microtopographical hazards below sensor post-spacing (boulders, fissures, dust pockets)
          cannot be resolved. Unknown and NoData terrain is strictly classified as <strong>unknown</strong> and must never be presumed safe.
        </p>
      </div>

      {/* 2. Interactive Coordinate & Target Selector */}
      <div className="bg-[#10121d] border border-[#23293f] rounded-lg p-3 space-y-2.5 shadow-lg">
        <div className="flex items-center justify-between border-b border-[#23293f] pb-2">
          <span className="font-bold text-gray-200 uppercase tracking-wider text-[11px]">
            Target Location & Slope Analysis
          </span>
          <div className="flex items-center space-x-1">
            {quickJumpSites.map((site) => (
              <button
                key={site.name}
                onClick={() => {
                  setActiveLat(site.lat);
                  setActiveLon(site.lon);
                  setInputLat(site.lat.toFixed(4));
                  setInputLon(site.lon.toFixed(4));
                }}
                className="px-2 py-0.5 rounded bg-slate-800/80 hover:bg-orange-950/60 hover:text-orange-300 text-[9px] text-slate-300 border border-slate-700 transition-colors"
                title={`${site.lat >= 0 ? `${site.lat}°N` : `${Math.abs(site.lat)}°S`}, ${site.lon}°E`}
              >
                {site.name.split(" ")[0]}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleManualSubmit} className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 flex-1">
            <label className="text-[10px] text-gray-400">Lat:</label>
            <input
              type="text"
              value={inputLat}
              onChange={(e) => setInputLat(e.target.value)}
              className="bg-[#0a0c16] border border-[#2e3752] rounded px-2 py-1 text-[11px] text-white w-24 focus:outline-none focus:border-orange-500"
              placeholder="-4.600"
            />
            <label className="text-[10px] text-gray-400 ml-2">Lon (°E):</label>
            <input
              type="text"
              value={inputLon}
              onChange={(e) => setInputLon(e.target.value)}
              className="bg-[#0a0c16] border border-[#2e3752] rounded px-2 py-1 text-[11px] text-white w-24 focus:outline-none focus:border-orange-500"
              placeholder="66.317"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1 bg-orange-600 hover:bg-orange-500 text-white font-bold rounded text-[11px] transition-colors"
          >
            Inspect Slope
          </button>
        </form>
      </div>

      {/* 3. Point Analysis Summary Cards */}
      {pointData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
          {/* Card 1: Slope Readout */}
          <div className="bg-[#0c0e1a] border border-[#23293f] rounded-lg p-3 space-y-1">
            <span className="text-[9px] text-gray-400 uppercase font-bold block">Topographic Slope</span>
            {pointLoading ? (
              <span className="text-amber-400 text-xs animate-pulse">Calculating...</span>
            ) : pointData.slope_deg !== null ? (
              <div>
                <div className="flex items-baseline space-x-1">
                  <span className="text-xl font-black text-white">{pointData.slope_deg.toFixed(2)}°</span>
                  <span className="text-[10px] text-gray-400">
                    ({pointData.slope_pct !== null ? `${pointData.slope_pct.toFixed(1)}%` : "N/A"})
                  </span>
                </div>
                <div className="mt-1">
                  {(() => {
                    const c = getCategoryColor(pointData.slope_category);
                    return (
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${c.bg} ${c.text} ${c.border}`}>
                        {pointData.slope_category.replace("_", " ")}
                      </span>
                    );
                  })()}
                </div>
              </div>
            ) : (
              <div>
                <span className="text-sm font-bold text-slate-400">NoData / Void</span>
                <span className="block text-[9px] text-slate-500 mt-0.5">Classified: UNKNOWN</span>
              </div>
            )}
          </div>

          {/* Card 2: Surface Elevation */}
          <div className="bg-[#0c0e1a] border border-[#23293f] rounded-lg p-3 space-y-1">
            <span className="text-[9px] text-gray-400 uppercase font-bold block">MOLA Areoid Elevation</span>
            {pointLoading ? (
              <span className="text-amber-400 text-xs animate-pulse">Sampling...</span>
            ) : pointData.elevation_m !== null ? (
              <div>
                <div className="text-xl font-black text-emerald-400">
                  {pointData.elevation_m >= 0 ? `+${pointData.elevation_m.toFixed(2)}` : pointData.elevation_m.toFixed(2)} m
                </div>
                <span className="text-[9px] text-gray-500 block mt-1 truncate">
                  Datum: {pointData.vertical_datum_type}
                </span>
              </div>
            ) : (
              <span className="text-sm font-bold text-amber-400">NoData Void</span>
            )}
          </div>

          {/* Card 3: Source Dataset & Resolution */}
          <div className="bg-[#0c0e1a] border border-[#23293f] rounded-lg p-3 space-y-1">
            <span className="text-[9px] text-gray-400 uppercase font-bold block">Selected DTM Product</span>
            <div className="text-sm font-bold text-orange-300 truncate">
              {pointData.source_id}
            </div>
            <div className="text-[10px] text-emerald-300 font-semibold">
              {pointData.native_pixel_spacing_desc}
            </div>
            <span className="text-[9px] text-gray-500 block truncate">
              Instrument: {pointData.instrument}
            </span>
          </div>

          {/* Card 4: Selection Reason */}
          <div className="bg-[#0c0e1a] border border-[#23293f] rounded-lg p-3 space-y-1">
            <span className="text-[9px] text-gray-400 uppercase font-bold block">Selection Rationale</span>
            <div className="text-[10px] text-gray-300 leading-tight">
              {pointData.source_selection_reason}
            </div>
            <div className="text-[8px] text-gray-500 pt-1">
              {pointData.fallback_chain.length} tier(s) evaluated
            </div>
          </div>
        </div>
      )}

      {/* 4. Slope Classification Legend */}
      <div className="bg-[#10121d] border border-[#23293f] rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between border-b border-[#23293f] pb-1.5">
          <span className="font-bold text-gray-200 uppercase tracking-wider text-[11px]">
            Analytical Slope Bands (Configurable)
          </span>
          <span className="text-[9px] text-gray-400">Horn 3×3 Gradient • Degrees</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          {legendList.map((entry) => {
            const c = getCategoryColor(entry.category);
            return (
              <div key={entry.category} className={`p-2 rounded border ${c.bg} ${c.border} space-y-1`}>
                <div className="flex items-center space-x-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${c.badge}`} />
                  <span className={`font-bold ${c.text} text-[10px]`}>{entry.label}</span>
                </div>
                <div className="text-[9px] text-gray-300 leading-tight">
                  {entry.description}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Window Slope Preview / Overlay Visualizer */}
      {windowData && windowData.slope_categories && (
        <div className="bg-[#10121d] border border-[#23293f] rounded-lg p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-[#23293f] pb-1.5">
            <div>
              <span className="font-bold text-gray-200 uppercase tracking-wider text-[11px]">
                Localized Terrain Window Slope Grid ({windowData.width_px} × {windowData.height_px})
              </span>
              <span className="block text-[9px] text-gray-400">
                Source: {windowData.source_id} • Native: {windowData.native_pixel_spacing_m.toFixed(1)}m • Display: ~{windowData.display_pixel_spacing_m.toFixed(0)}m/px
              </span>
            </div>
            <div className="text-right text-[9px] text-gray-400">
              NoData: {(windowData.nodata_fraction * 100).toFixed(1)}%
            </div>
          </div>

          {/* Gridded representation */}
          <div className="overflow-x-auto p-1 bg-[#07080f] rounded border border-[#1b2034]">
            <div
              className="grid gap-[1px]"
              style={{
                gridTemplateColumns: `repeat(${windowData.width_px}, minmax(8px, 1fr))`,
              }}
            >
              {windowData.slope_categories.flat().map((cat, idx) => {
                const c = getCategoryColor(cat);
                return (
                  <div
                    key={idx}
                    className={`h-3 rounded-none ${c.badge} transition-opacity hover:opacity-100 opacity-80`}
                    title={`Cell #${idx}: ${cat}`}
                  />
                );
              })}
            </div>
          </div>
          <div className="flex items-center justify-between text-[9px] text-gray-500 pt-1">
            <span>South: {windowData.bbox[1].toFixed(2)}° | North: {windowData.bbox[3].toFixed(2)}°</span>
            <span>West: {windowData.bbox[0].toFixed(2)}°E | East: {windowData.bbox[2].toFixed(2)}°E</span>
          </div>
        </div>
      )}

      {/* 6. Terrain Source Inventory & Coverage Footprints */}
      <div className="bg-[#10121d] border border-[#23293f] rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between border-b border-[#23293f] pb-1.5">
          <span className="font-bold text-gray-200 uppercase tracking-wider text-[11px]">
            Integrated Terrain Coverage & Resolution Hierarchy
          </span>
          <span className="text-[9px] text-emerald-400 font-semibold">
            {coverageList.filter((c) => c.elevation_file_available).length}/{coverageList.length} Products Verified On Disk
          </span>
        </div>

        <div className="space-y-1.5">
          {coverageList.map((src, i) => (
            <div
              key={src.source_id}
              className="p-2 bg-[#0c0e1a] rounded border border-[#1b2034] flex items-center justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-800 text-orange-400">
                    Tier {i + 1}
                  </span>
                  <span className="font-bold text-gray-200 text-[11px]">{src.source_id}</span>
                  <span className="text-[9px] text-gray-400">({src.instrument})</span>
                </div>
                <div className="text-[10px] text-gray-400">
                  {src.coverage_note}
                </div>
                <div className="text-[9px] text-slate-500">
                  Extent: [{src.lat_min}° to {src.lat_max}° Lat, {src.lon_min}° to {src.lon_max}° Lon] • Datum: {src.vertical_datum}
                </div>
              </div>

              <div className="text-right space-y-1">
                <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60 block">
                  {src.pixel_spacing_desc}
                </span>
                <span className="text-[8px] text-slate-400 block">
                  {src.slope_file_available ? "✓ Slope COG Active" : "Elevation Only"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
