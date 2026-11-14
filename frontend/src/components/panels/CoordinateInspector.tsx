"use client";

import React, { useEffect, useState, useCallback } from "react";
import { fetchPointElevation, fetchGeologyPoint, fetchThermalPoint, fetchTraversabilityPoint } from "../../lib/api";
import { PointElevationDetail, TraversabilityPointResult } from "../../lib/types";

interface CoordinateInspectorProps {
  coords: { lat: number; lon: number } | null;
  onInspectCoord?: (coords: { lat: number; lon: number }) => void;
}

export const CoordinateInspector: React.FC<CoordinateInspectorProps> = ({
  coords,
  onInspectCoord,
}) => {
  const [activeLat, setActiveLat] = useState<number>(-4.600);
  const [activeLon, setActiveLon] = useState<number>(66.317);
  const [inputLat, setInputLat] = useState<string>("-4.600");
  const [inputLon, setInputLon] = useState<string>("66.317");

  const [pointData, setPointData] = useState<PointElevationDetail | null>(null);
  const [geologyData, setGeologyData] = useState<any | null>(null);
  const [thermalData, setThermalData] = useState<any | null>(null);
  const [traversabilityData, setTraversabilityData] = useState<TraversabilityPointResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const queryCoord = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);
    try {
      const [elev, geo, therm, trav] = await Promise.allSettled([
        fetchPointElevation(lat, lon),
        fetchGeologyPoint(lat, lon),
        fetchThermalPoint(lat, lon, "dayside"),
        fetchTraversabilityPoint(lat, lon),
      ]);
      if (elev.status === "fulfilled") setPointData(elev.value);
      if (geo.status === "fulfilled") setGeologyData(geo.value);
      if (therm.status === "fulfilled") setThermalData(therm.value);
      if (trav.status === "fulfilled") setTraversabilityData(trav.value);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Elevation query failed");
      setPointData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // When external coordinates (from map click) change, query immediately
  useEffect(() => {
    if (coords) {
      setActiveLat(coords.lat);
      setActiveLon(coords.lon);
      setInputLat(coords.lat.toFixed(4));
      setInputLon(coords.lon.toFixed(4));
      queryCoord(coords.lat, coords.lon);
    }
  }, [coords, queryCoord]);

  // Initial load query at Tyrrhena Terra CTX location
  useEffect(() => {
    if (!coords) {
      queryCoord(activeLat, activeLon);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const latNum = parseFloat(inputLat);
    const lonNum = parseFloat(inputLon);
    if (!isNaN(latNum) && !isNaN(lonNum)) {
      setActiveLat(latNum);
      setActiveLon(lonNum);
      queryCoord(latNum, lonNum);
      if (onInspectCoord) {
        onInspectCoord({ lat: latNum, lon: lonNum });
      }
    }
  };

  const getTierBadge = (tier?: string) => {
    if (tier === "local_high_resolution") {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-emerald-950 text-emerald-300 border border-emerald-700/60 shadow-sm">
          🔬 High-Res CTX (20m)
        </span>
      );
    }
    if (tier === "regional_high_resolution") {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-orange-950 text-orange-300 border border-orange-700/60 shadow-sm">
          🗺️ Regional MOLA 128 (463m)
        </span>
      );
    }
    if (tier === "global_baseline") {
      return (
        <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-blue-950 text-blue-300 border border-blue-700/60 shadow-sm">
          🌍 Global MOLA 4 ppd
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-red-950 text-red-300 border border-red-700/60">
        ⚠️ Unsupported
      </span>
    );
  };

  return (
    <div className="bg-[#111320]/95 border border-[#23283f] rounded-lg p-3.5 text-xs font-mono backdrop-blur-md shadow-2xl space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#23283f] pb-2">
        <div className="flex items-center space-x-2">
          <span>🎯</span>
          <span className="font-semibold text-gray-100 uppercase tracking-wider text-[11px]">
            Planetary Elevation Inspector
          </span>
        </div>
        {pointData && getTierBadge(pointData.tier)}
      </div>

      {/* Primary Coordinates & Elevation Display */}
      <div className="grid grid-cols-2 gap-2 bg-[#0a0c16] p-3 rounded-lg border border-[#1b2034] shadow-inner">
        <div>
          <span className="text-[9px] text-gray-500 uppercase font-bold block">Planetocentric Lat</span>
          <span className="text-sm font-bold text-gray-100">
            {activeLat >= 0 ? `${activeLat.toFixed(4)}°N` : `${Math.abs(activeLat).toFixed(4)}°S`}
          </span>
          <span className="text-[9px] text-gray-500 block">
            {activeLat >= 0 ? "Northern Hemisphere" : "Southern Hemisphere"}
          </span>
        </div>

        <div>
          <span className="text-[9px] text-gray-500 uppercase font-bold block">Positive East Lon</span>
          <span className="text-sm font-bold text-gray-100">
            {activeLon.toFixed(4)}°E
          </span>
          <span className="text-[9px] text-gray-500 block">
            IAU 2000/2015 Positive East
          </span>
        </div>

        {/* Elevation Readout */}
        <div className="col-span-2 pt-2 border-t border-[#1a1f33] flex items-center justify-between">
          <div>
            <span className="text-[9px] text-gray-400 uppercase font-bold block">Sampled Surface Elevation</span>
            {loading ? (
              <span className="text-xs text-amber-400 animate-pulse">Querying numerical rasters...</span>
            ) : error ? (
              <span className="text-xs text-red-400">{error}</span>
            ) : !pointData || pointData.is_nodata || pointData.elevation_m === null ? (
              <span className="text-sm font-bold text-amber-400">NoData Void / Unmeasured</span>
            ) : (
              <div className="flex items-baseline space-x-1.5">
                <span className="text-lg font-black text-emerald-400 tracking-tight">
                  {pointData.elevation_m >= 0 ? `+${pointData.elevation_m.toFixed(2)}` : pointData.elevation_m.toFixed(2)}
                </span>
                <span className="text-xs font-semibold text-gray-300">metres</span>
              </div>
            )}
          </div>
          <div className="text-right">
            <span className="text-[9px] text-gray-500 block">Vertical Reference</span>
            <span className="text-[10px] text-gray-300 font-semibold">MOLA Areoid Datum</span>
          </div>
        </div>
      </div>

      {/* Multi-Resolution Provenance Details */}
      {pointData && (
        <div className="bg-[#0c0e1a] p-2.5 rounded-lg border border-[#1b2034] text-[10px] space-y-1.5">
          <div className="flex justify-between border-b border-[#181d30] pb-1">
            <span className="text-gray-400">Primary Dataset:</span>
            <span className="text-orange-400 font-semibold">{pointData.dataset_id}</span>
          </div>
          <div className="flex justify-between border-b border-[#181d30] pb-1">
            <span className="text-gray-400">Instrument:</span>
            <span className="text-gray-200">{pointData.instrument}</span>
          </div>
          <div className="flex justify-between border-b border-[#181d30] pb-1">
            <span className="text-gray-400">Native Resolution:</span>
            <span className="text-emerald-300 font-semibold">{pointData.native_resolution_desc}</span>
          </div>
          {pointData.display_resolution_m && (
            <div className="flex justify-between border-b border-[#181d30] pb-1">
              <span className="text-gray-400">Display Resolution:</span>
              <span className="text-gray-300">~{pointData.display_resolution_m.toFixed(1)} m/px</span>
            </div>
          )}
          <div className="flex justify-between border-b border-[#181d30] pb-1">
            <span className="text-gray-400">Horizontal CRS:</span>
            <span className="text-amber-300">{pointData.crs}</span>
          </div>
          <div className="pt-1 text-[9px] text-gray-400 leading-tight">
            <span className="text-gray-500 font-semibold block mb-0.5">Scientific Status:</span>
            {pointData.status_note}
          </div>
          {pointData.source_checksum && (
            <div className="text-[8px] text-gray-500 truncate pt-0.5">
              SHA-256: <span className="font-mono text-gray-400">{pointData.source_checksum.slice(0, 20)}...</span>
            </div>
          )}
        </div>
      )}

      {/* USGS SIM 3292 Geological Unit */}
      {geologyData && (
        <div className="bg-[#0c0e1a] p-2.5 rounded-lg border border-[#1b2034] text-[10px] space-y-1.5">
          <div className="flex items-center justify-between border-b border-[#181d30] pb-1">
            <span className="font-bold text-amber-400 uppercase tracking-wider text-[10px]">
              Geology (USGS SIM 3292)
            </span>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-950/60 text-amber-300 border border-amber-800/40">
              {geologyData.unit}
            </span>
          </div>
          <div className="text-gray-200 text-[10px] leading-tight">
            {geologyData.unit_name || "Unclassified or outside mapped domain"}
          </div>
          <div className="flex justify-between text-[9px] text-gray-400 border-t border-[#181d30] pt-1">
            <span>Period: <span className="text-gray-300 font-semibold">{geologyData.chronostratigraphic_period}</span></span>
            {geologyData.spherical_area_sq_km && (
              <span>Area: <span className="text-gray-300">{Math.round(geologyData.spherical_area_sq_km).toLocaleString()} km²</span></span>
            )}
          </div>
        </div>
      )}

      {/* MGS TES Calibrated Thermal-Inertia Estimate */}
      {thermalData && (
        <div className="bg-[#0c0e1a] p-2.5 rounded-lg border border-[#1b2034] text-[10px] space-y-1.5">
          <div className="flex items-center justify-between border-b border-[#181d30] pb-1">
            <span className="font-bold text-cyan-400 uppercase tracking-wider text-[10px]">
              Calibrated Thermal-Inertia Estimate (TIU)
            </span>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40 font-mono">
              {thermalData.calibrated_thermal_inertia_estimate_tiu !== null && thermalData.calibrated_thermal_inertia_estimate_tiu !== undefined
                ? `${thermalData.calibrated_thermal_inertia_estimate_tiu} TIU`
                : thermalData.thermal_inertia_tiu !== null
                ? `${thermalData.thermal_inertia_tiu} TIU`
                : "NoData"}
            </span>
          </div>
          <div className="text-gray-300 text-[9px] leading-tight">
            <span className="text-gray-500 font-semibold block mb-0.5">Indicative Surface Property:</span>
            {thermalData.physical_interpretation}
          </div>
          <div className="text-[8px] text-cyan-300/80 bg-cyan-950/30 p-1.5 rounded border border-cyan-900/30 leading-snug">
            ⚠️ <span className="font-bold">Not Temperature:</span> Represents regolith thermal resistance (J m⁻² K⁻¹ s⁻¹/²). High values = bedrock/lag; low values = fine dust. Unvalidated proxy estimate.
          </div>
        </div>
      )}

      {/* Phase 8.8.1 Terrain Traversability & Slope Classification */}
      {traversabilityData && (
        <div className="bg-[#0c0e1a] p-2.5 rounded-lg border border-[#1b2034] text-[10px] space-y-1.5">
          <div className="flex items-center justify-between border-b border-[#181d30] pb-1">
            <span className="font-bold text-orange-400 uppercase tracking-wider text-[10px]">
              Terrain Slope (Phase 8.8.1)
            </span>
            {traversabilityData.slope_category && (
              <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase border ${
                traversabilityData.slope_category === "low" ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/40" :
                traversabilityData.slope_category === "moderate" ? "bg-amber-950/60 text-amber-300 border-amber-800/40" :
                traversabilityData.slope_category === "high" ? "bg-orange-950/60 text-orange-300 border-orange-800/40" :
                traversabilityData.slope_category === "very_high" ? "bg-purple-950/60 text-purple-300 border-purple-800/40" :
                "bg-slate-900 text-slate-400 border-slate-700"
              }`}>
                {traversabilityData.slope_category.replace("_", " ")}
              </span>
            )}
          </div>
          <div className="flex justify-between items-center text-gray-200 text-[10px]">
            <span>Calculated Slope:</span>
            <span className="font-bold text-white">
              {traversabilityData.slope_deg !== null ? `${traversabilityData.slope_deg.toFixed(2)}° (${traversabilityData.slope_pct?.toFixed(1)}% grade)` : "NoData Void"}
            </span>
          </div>
          <div className="flex justify-between text-[9px] text-gray-400 border-t border-[#181d30] pt-1">
            <span>Source: <span className="text-orange-300">{traversabilityData.source_id}</span></span>
            <span>Resolution: <span className="text-emerald-300">{traversabilityData.native_pixel_spacing_desc}</span></span>
          </div>
          <div className="text-[8px] text-amber-300/80 bg-amber-950/20 p-1 rounded border border-amber-900/30 leading-snug">
            ⚠️ <span className="font-bold">Analytical Only:</span> Slope bands are orbital DEM derivatives and do NOT establish astronaut safety or EVA mobility.
          </div>
        </div>
      )}

      {/* Manual Coordinate Input & Target Form */}
      <form onSubmit={handleManualSubmit} className="space-y-2 pt-1 border-t border-[#1e2338]">
        <span className="text-[10px] text-gray-400 font-semibold block">Target Coordinate Jump / Query:</span>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Latitude (-90° to +90°):</label>
            <input
              type="number"
              step="0.0001"
              value={inputLat}
              onChange={(e) => setInputLat(e.target.value)}
              className="w-full bg-[#080911] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
            />
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Longitude (0° to 360°):</label>
            <input
              type="number"
              step="0.0001"
              value={inputLon}
              onChange={(e) => setInputLon(e.target.value)}
              className="w-full bg-[#080911] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
            />
          </div>
        </div>
        <button
          type="submit"
          className="w-full py-1.5 bg-[#1b2238] hover:bg-[#252f4e] text-orange-400 hover:text-orange-300 border border-orange-500/40 rounded font-semibold text-[11px] transition-colors"
        >
          Inspect Planetary Coordinates
        </button>
      </form>
    </div>
  );
};

export default CoordinateInspector;
