"use client";

import React, { useEffect, useState, useCallback } from "react";
import { fetchPointElevation } from "../../lib/api";
import { PointElevationDetail } from "../../lib/types";

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
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const queryCoord = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPointElevation(lat, lon);
      setPointData(data);
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
