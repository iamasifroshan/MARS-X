"use client";

import React, { useState } from "react";
import { fetchElevationProfile } from "../../lib/api";
import { ElevationProfileResponse, ElevationProfilePoint } from "../../lib/types";

const PRESET_TRANSECTS = [
  {
    name: "USGS CTX 20m Crater Rim-to-Floor",
    startLat: -4.600,
    startLon: 66.317,
    endLat: -4.640,
    endLon: 66.350,
    tier: "High-Res CTX 20m",
    desc: "Stereo DTM transect through dissected impact crater in Tyrrhena Terra.",
  },
  {
    name: "Sinus Meridiani to Mawrth Vallis",
    startLat: -2.000,
    startLon: 5.000,
    endLat: -2.150,
    endLon: 5.180,
    tier: "Regional MOLA 128",
    desc: "Regional traverse across layered phyllosilicate clay channels.",
  },
  {
    name: "Olympus Mons Flank to Caldera Summit",
    startLat: 18.000,
    startLon: 224.000,
    endLat: 18.650,
    endLon: 226.200,
    tier: "Global MOLA 4 ppd",
    desc: "Massive volcanic ascent onto the summit caldera rim at +21.2 km altitude.",
  },
  {
    name: "Valles Marineris (Melas Chasma)",
    startLat: -9.000,
    startLon: 283.000,
    endLat: -10.500,
    endLon: 284.000,
    tier: "Global MOLA 4 ppd",
    desc: "Deep canyon cross-section dropping over 7 km into the Martian chasma floor.",
  },
];

export const ElevationProfilePanel: React.FC = () => {
  const [startLat, setStartLat] = useState<number>(-4.600);
  const [startLon, setStartLon] = useState<number>(66.317);
  const [endLat, setEndLat] = useState<number>(-4.640);
  const [endLon, setEndLon] = useState<number>(66.350);
  const [numSamples, setNumSamples] = useState<number>(80);

  const [profileData, setProfileData] = useState<ElevationProfileResponse | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<ElevationProfilePoint | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectPreset = (p: typeof PRESET_TRANSECTS[0]) => {
    setStartLat(p.startLat);
    setStartLon(p.startLon);
    setEndLat(p.endLat);
    setEndLon(p.endLon);
    setError(null);
  };

  const handleGenerateProfile = async () => {
    setLoading(true);
    setError(null);
    setHoveredPoint(null);
    try {
      const res = await fetchElevationProfile(startLat, startLon, endLat, endLon, numSamples);
      setProfileData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Elevation profile generation failed");
    } finally {
      setLoading(false);
    }
  };

  // Compute SVG dimensions and path
  const renderSvgChart = () => {
    if (!profileData || profileData.points.length === 0) return null;

    const width = 640;
    const height = 180;
    const padX = 45;
    const padY = 25;

    const validPoints = profileData.points.filter((p) => p.elevation_m !== null);
    if (validPoints.length === 0) {
      return (
        <div className="h-44 flex items-center justify-center text-amber-400 font-mono text-xs">
          Entire profile trajectory falls in unmeasured NoData or unsupported coverage.
        </div>
      );
    }

    const minElev = profileData.min_elevation_m ?? 0;
    const maxElev = profileData.max_elevation_m ?? 1000;
    const elevRange = Math.max(maxElev - minElev, 1.0);
    const totalDist = profileData.total_distance_m;

    // Coordinate mapping
    const getX = (distM: number) => padX + (distM / totalDist) * (width - 2 * padX);
    const getY = (elevM: number) => height - padY - ((elevM - minElev) / elevRange) * (height - 2 * padY);

    // Build SVG Path
    let pathD = "";
    let fillD = "";

    profileData.points.forEach((pt, idx) => {
      if (pt.elevation_m !== null) {
        const x = getX(pt.distance_m);
        const y = getY(pt.elevation_m);
        if (pathD === "") {
          pathD = `M ${x.toFixed(1)} ${y.toFixed(1)}`;
          fillD = `M ${x.toFixed(1)} ${(height - padY).toFixed(1)} L ${x.toFixed(1)} ${y.toFixed(1)}`;
        } else {
          pathD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
          fillD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
        }
      }
    });

    if (fillD !== "") {
      const lastValid = validPoints[validPoints.length - 1];
      const lastX = getX(lastValid.distance_m);
      fillD += ` L ${lastX.toFixed(1)} ${(height - padY).toFixed(1)} Z`;
    }

    return (
      <div className="relative w-full overflow-hidden bg-[#0a0c16] rounded-lg border border-[#1d2238] p-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-44 select-none">
          <defs>
            <linearGradient id="profileGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f97316" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#f97316" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="#1f263d" strokeDasharray="3 3" />
          <line x1={padX} y1={height / 2} x2={width - padX} y2={height / 2} stroke="#1f263d" strokeDasharray="3 3" />
          <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="#2b3452" />

          {/* Y Axis labels */}
          <text x={padX - 6} y={padY + 4} textAnchor="end" fill="#94a3b8" fontSize="9" fontFamily="monospace">
            {maxElev.toFixed(0)}m
          </text>
          <text x={padX - 6} y={height / 2 + 3} textAnchor="end" fill="#64748b" fontSize="8" fontFamily="monospace">
            {((maxElev + minElev) / 2).toFixed(0)}m
          </text>
          <text x={padX - 6} y={height - padY} textAnchor="end" fill="#94a3b8" fontSize="9" fontFamily="monospace">
            {minElev.toFixed(0)}m
          </text>

          {/* X Axis labels */}
          <text x={padX} y={height - 8} textAnchor="start" fill="#94a3b8" fontSize="8" fontFamily="monospace">
            0 km
          </text>
          <text x={width - padX} y={height - 8} textAnchor="end" fill="#94a3b8" fontSize="8" fontFamily="monospace">
            {(totalDist / 1000).toFixed(2)} km
          </text>

          {/* Filled Area */}
          <path d={fillD} fill="url(#profileGradient)" />

          {/* Elevation Profile Curve */}
          <path d={pathD} fill="none" stroke="#fb923c" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data Points */}
          {profileData.points.map((pt) => {
            if (pt.elevation_m === null) return null;
            const cx = getX(pt.distance_m);
            const cy = getY(pt.elevation_m);
            const isCtx = pt.dataset_id.includes("ctx");
            const isMola128 = pt.dataset_id.includes("128");

            return (
              <circle
                key={pt.point_index}
                cx={cx}
                cy={cy}
                r={hoveredPoint?.point_index === pt.point_index ? 5 : 2.5}
                fill={isCtx ? "#10b981" : isMola128 ? "#f97316" : "#38bdf8"}
                stroke="#0f172a"
                strokeWidth="1"
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredPoint(pt)}
              />
            );
          })}
        </svg>

        {/* Hover Point Tooltip */}
        {hoveredPoint && (
          <div className="absolute top-3 right-3 bg-[#0d0f1c]/95 border border-[#2e3752] rounded p-2 text-[10px] font-mono shadow-2xl backdrop-blur-md">
            <div className="text-gray-400">
              Dist: <span className="text-white font-bold">{(hoveredPoint.distance_m / 1000).toFixed(2)} km</span>
            </div>
            <div className="text-gray-400">
              Elev: <span className="text-emerald-400 font-bold">{hoveredPoint.elevation_m?.toFixed(1)} m</span>
            </div>
            <div className="text-gray-400">
              Source: <span className="text-orange-300">{hoveredPoint.dataset_id}</span>
            </div>
            <div className="text-[9px] text-gray-500">
              Lat: {hoveredPoint.lat.toFixed(3)}°, Lon: {hoveredPoint.lon.toFixed(3)}°
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-[#101322]/90 border border-[#232840] rounded-lg p-5 text-xs font-mono backdrop-blur-md shadow-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-[#232840] pb-3 gap-2">
        <div className="flex items-center space-x-2.5">
          <span className="text-xl">📈</span>
          <div>
            <h2 className="font-bold text-sm text-gray-100 uppercase tracking-wider">
              Multi-Resolution Elevation Profile Generator
            </h2>
            <p className="text-[11px] text-gray-400">
              Great-circle spherical geodesic transect sampling across authentic NASA/USGS elevation rasters.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
            Mars Great-Circle Geodesic (R = 3,396.19 km)
          </span>
        </div>
      </div>

      {/* Preset Transect Selector */}
      <div>
        <span className="text-[10px] text-gray-400 uppercase font-bold block mb-1.5">
          Planetary Mission Transect Presets:
        </span>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {PRESET_TRANSECTS.map((p) => (
            <button
              key={p.name}
              onClick={() => handleSelectPreset(p)}
              className={`p-2 rounded text-left border transition-all ${
                startLat === p.startLat && endLat === p.endLat
                  ? "bg-[#1c2238] border-orange-500/80 shadow-md"
                  : "bg-[#0b0d18] border-[#1d2338] hover:border-gray-600 hover:bg-[#121524]"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-gray-200 text-xs">{p.name}</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-orange-500/10 text-orange-400 font-bold border border-orange-500/20">
                  {p.tier}
                </span>
              </div>
              <p className="text-[10px] text-gray-400 leading-tight">{p.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Coordinates Inputs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 bg-[#090b14] p-3 rounded-lg border border-[#1c2238]">
        <div>
          <label className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Start Lat (°N)</label>
          <input
            type="number"
            step="0.001"
            value={startLat}
            onChange={(e) => setStartLat(parseFloat(e.target.value) || 0)}
            className="w-full bg-[#06070d] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
          />
        </div>
        <div>
          <label className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Start Lon (°E)</label>
          <input
            type="number"
            step="0.001"
            value={startLon}
            onChange={(e) => setStartLon(parseFloat(e.target.value) || 0)}
            className="w-full bg-[#06070d] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
          />
        </div>
        <div>
          <label className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">End Lat (°N)</label>
          <input
            type="number"
            step="0.001"
            value={endLat}
            onChange={(e) => setEndLat(parseFloat(e.target.value) || 0)}
            className="w-full bg-[#06070d] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
          />
        </div>
        <div>
          <label className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">End Lon (°E)</label>
          <input
            type="number"
            step="0.001"
            value={endLon}
            onChange={(e) => setEndLon(parseFloat(e.target.value) || 0)}
            className="w-full bg-[#06070d] border border-[#232840] rounded px-2 py-1 text-gray-200 text-xs focus:border-orange-500 outline-none"
          />
        </div>
        <div className="col-span-2 md:col-span-1 flex flex-col justify-end">
          <label className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Samples ({numSamples})</label>
          <input
            type="range"
            min="20"
            max="200"
            step="10"
            value={numSamples}
            onChange={(e) => setNumSamples(parseInt(e.target.value))}
            className="accent-orange-500 w-full"
          />
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={handleGenerateProfile}
        disabled={loading}
        className="w-full py-2 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 disabled:opacity-50 text-white font-bold rounded shadow-lg transition-all text-xs tracking-wider uppercase flex items-center justify-center space-x-2"
      >
        <span>{loading ? "Sampling Numerical Rasters..." : "Generate Geodesic Elevation Profile"}</span>
        <span>⮞</span>
      </button>

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-red-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* SVG Profile Chart */}
      {profileData && (
        <div className="space-y-3">
          {renderSvgChart()}

          {/* Profile Metrics Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
            <div className="bg-[#0c0e1a] p-2 rounded border border-[#1c2238]">
              <span className="text-gray-500 uppercase font-bold block">Transect Distance</span>
              <span className="text-xs font-semibold text-gray-200">
                {(profileData.total_distance_m / 1000).toFixed(2)} km
              </span>
              <span className="text-[9px] text-gray-500 block">
                Interval: {profileData.sampling_interval_m.toFixed(1)} m
              </span>
            </div>

            <div className="bg-[#0c0e1a] p-2 rounded border border-[#1c2238]">
              <span className="text-gray-500 uppercase font-bold block">Elevation Range</span>
              <span className="text-xs font-semibold text-emerald-400">
                {profileData.min_elevation_m?.toFixed(0)}m to {profileData.max_elevation_m?.toFixed(0)}m
              </span>
              <span className="text-[9px] text-gray-500 block">
                ΔH: {((profileData.max_elevation_m ?? 0) - (profileData.min_elevation_m ?? 0)).toFixed(0)} m
              </span>
            </div>

            <div className="bg-[#0c0e1a] p-2 rounded border border-[#1c2238]">
              <span className="text-gray-500 uppercase font-bold block">Accumulated Relief</span>
              <span className="text-xs font-semibold text-amber-300">
                +{profileData.elevation_gain_m.toFixed(0)}m / -{profileData.elevation_loss_m.toFixed(0)}m
              </span>
              <span className="text-[9px] text-gray-500 block">Ascent / Descent</span>
            </div>

            <div className="bg-[#0c0e1a] p-2 rounded border border-[#1c2238]">
              <span className="text-gray-500 uppercase font-bold block">Datasets Contributing</span>
              <div className="flex flex-wrap gap-1 mt-0.5">
                {profileData.datasets_used.map((ds) => (
                  <span key={ds} className="text-[8px] px-1.5 py-0.2 rounded bg-orange-950 text-orange-300 border border-orange-800/40">
                    {ds.split(" ")[0]}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Scientific Disclaimer */}
      <div className="p-2.5 bg-black/30 rounded border border-[#1a1f33] text-[9px] text-gray-400 leading-relaxed">
        <span className="text-amber-400 font-bold block mb-0.5">Scientific Geodetic Notice:</span>
        Distances are computed along the Martian spherical geodesic (R = 3,396,190 m). Elevation samples are directly extracted from authentic MOLA and CTX numerical rasters. Unmeasured segments or NoData voids are never filled with synthetic interpolation. This tool provides topographical terrain visualization, not an astronaut life-support prediction.
      </div>
    </div>
  );
};

export default ElevationProfilePanel;

