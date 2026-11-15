"use client";

import React, { useState } from "react";
import {
  RouteIntelligenceReport,
  MultiStopTraverseIntelligenceReport,
  LegRouteIntelligence,
  RouteElevationProfilePoint,
} from "@/lib/types";

const DEFAULT_SAFETY_DISCLAIMER =
  "OPERATIONAL SAFETY WARNING: Marswalk route intelligence provides analytical and scientific characterization " +
  "of orbital datasets only. Orbital DEMs and 1:20,000,000 geological maps do not resolve sub-metre surface hazards. " +
  "No route generated or analyzed by MARS-X is certified safe for human EVA or robotic traversal.";

interface RouteIntelligenceViewProps {
  routeReport?: RouteIntelligenceReport | null;
  traverseReport?: MultiStopTraverseIntelligenceReport | null;
  onHoverCoord?: (coord: [number, number] | null) => void;
}

export const RouteIntelligenceView: React.FC<RouteIntelligenceViewProps> = ({
  routeReport,
  traverseReport,
  onHoverCoord,
}) => {
  // Active leg selection for multi-stop traverses (null = full traverse)
  const [selectedLegIndex, setSelectedLegIndex] = useState<number | null>(null);
  // Hovered elevation profile sample
  const [hoveredPoint, setHoveredPoint] = useState<RouteElevationProfilePoint | null>(null);

  // Active report data
  const isMultiStop = Boolean(traverseReport);

  const activeLeg: LegRouteIntelligence | null =
    isMultiStop && traverseReport && selectedLegIndex !== null
      ? traverseReport.legs[selectedLegIndex] || null
      : null;

  const title = activeLeg
    ? `Leg ${activeLeg.leg_index + 1}: ${activeLeg.from_stop_name} → ${activeLeg.to_stop_name}`
    : traverseReport?.traverse_name || routeReport?.route_name || "Marswalk Route Intelligence";

  const demSource =
    activeLeg?.dem_source || traverseReport?.dem_source || routeReport?.dem_source || "MOLA DEM";
  const resolutionDesc =
    activeLeg?.native_resolution_desc ||
    traverseReport?.native_resolution_desc ||
    routeReport?.native_resolution_desc ||
    "N/A";

  const elevSummary = activeLeg
    ? activeLeg.elevation_profile
    : traverseReport
    ? traverseReport.aggregated_elevation_profile
    : routeReport?.elevation_profile;

  const terrainSummary = activeLeg
    ? activeLeg.terrain_intelligence
    : traverseReport
    ? traverseReport.aggregated_terrain_intelligence
    : routeReport?.terrain_intelligence;

  const geoContext = activeLeg
    ? activeLeg.geological_context
    : traverseReport
    ? traverseReport.aggregated_geological_context
    : routeReport?.geological_context;

  const thermalContext = activeLeg
    ? activeLeg.thermophysical_context
    : traverseReport
    ? traverseReport.aggregated_thermophysical_context
    : routeReport?.thermophysical_context;

  const scienceOpps = activeLeg
    ? activeLeg.nearby_science_opportunities
    : traverseReport
    ? traverseReport.aggregated_science_opportunities
    : routeReport?.nearby_science_opportunities || [];

  const surfaceDistM = activeLeg
    ? activeLeg.surface_distance_m
    : traverseReport
    ? traverseReport.total_surface_distance_m
    : routeReport?.surface_distance_m || 0;

  const horizDistM = activeLeg
    ? activeLeg.horizontal_distance_m
    : traverseReport
    ? traverseReport.total_horizontal_distance_m
    : routeReport?.horizontal_distance_m || 0;

  const optCost = activeLeg
    ? activeLeg.optimization_cost
    : traverseReport
    ? traverseReport.total_optimization_cost
    : routeReport?.optimization_cost || 0;

  // SVG Chart Dimensions
  const svgWidth = 720;
  const svgHeight = 180;
  const padLeft = 55;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 30;
  const chartW = svgWidth - padLeft - padRight;
  const chartH = svgHeight - padTop - padBottom;

  const points = elevSummary?.points || [];
  const minElev = elevSummary?.min_elevation_m ?? 0;
  const maxElev = elevSummary?.max_elevation_m ?? 100;
  const elevSpan = Math.max(1.0, maxElev - minElev);
  const maxDist = Math.max(1.0, surfaceDistM);

  const getSvgX = (d: number) => padLeft + (d / maxDist) * chartW;
  const getSvgY = (z: number) => padTop + chartH - ((z - minElev) / elevSpan) * chartH;

  // Polyline points
  const polylineCoords = points
    .map((p) => `${getSvgX(p.distance_m)},${getSvgY(p.elevation_m ?? minElev)}`)
    .join(" ");

  // Closed area polygon
  const areaCoords =
    points.length > 0
      ? `${getSvgX(0)},${padTop + chartH} ${polylineCoords} ${getSvgX(
          points[points.length - 1].distance_m
        )},${padTop + chartH}`
      : "";

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!points.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    // Map SVG clickX back to distance
    const normX = (clickX - padLeft) / chartW;
    const targetDist = normX * maxDist;

    // Find nearest sample point
    let closest = points[0];
    let minDiff = Math.abs(closest.distance_m - targetDist);
    for (let i = 1; i < points.length; i++) {
      const diff = Math.abs(points[i].distance_m - targetDist);
      if (diff < minDiff) {
        minDiff = diff;
        closest = points[i];
      }
    }
    setHoveredPoint(closest);
    if (onHoverCoord) {
      onHoverCoord([closest.lon, closest.lat]);
    }
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
    if (onHoverCoord) onHoverCoord(null);
  };

  return (
    <div className="space-y-6 text-xs font-mono text-slate-300">
      {/* Header and Leg Navigation */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1b2238] pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base">🔬</span>
              <span className="font-bold text-sm text-cyan-400 uppercase tracking-wider">
                Route Intelligence &amp; Traverse Analysis
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-700/50 text-cyan-300">
                Phase 8.8.4
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {title} • DEM: <span className="text-orange-400 font-semibold">{demSource}</span> ({resolutionDesc})
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">Vertical Datum:</span>
            <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded">
              MOLA Areoid (R=3,396,190 m)
            </span>
          </div>
        </div>

        {/* Leg Selector for Multi-Stop Traverses */}
        {isMultiStop && traverseReport && traverseReport.legs.length > 1 && (
          <div className="space-y-1.5 pt-1">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
              Select Leg for Detailed Scientific Inspection:
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setSelectedLegIndex(null)}
                className={`py-1 px-3 rounded text-[11px] font-bold transition-all ${
                  selectedLegIndex === null
                    ? "bg-cyan-500 text-black shadow"
                    : "bg-[#141a30] text-slate-300 hover:text-white hover:bg-slate-800"
                }`}
              >
                Full Traverse ({traverseReport.legs.length} Legs)
              </button>
              {traverseReport.legs.map((leg, idx) => (
                <button
                  key={leg.leg_index}
                  onClick={() => setSelectedLegIndex(idx)}
                  className={`py-1 px-2.5 rounded text-[10px] transition-all flex items-center gap-1.5 ${
                    selectedLegIndex === idx
                      ? "bg-emerald-500 text-black font-bold shadow"
                      : "bg-[#141a30] text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <span className="font-mono">#{idx + 1}</span>
                  <span>{leg.from_stop_name} → {leg.to_stop_name}</span>
                  <span className="text-[9px] opacity-75">
                    ({leg.surface_distance_m >= 1000 ? `${(leg.surface_distance_m / 1000).toFixed(1)}km` : `${leg.surface_distance_m.toFixed(0)}m`})
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Key Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 text-center pt-1">
          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Surface Distance</div>
            <div className="text-sm font-bold text-emerald-400 mt-0.5">
              {surfaceDistM >= 1000 ? `${(surfaceDistM / 1000).toFixed(2)} km` : `${surfaceDistM.toFixed(1)} m`}
            </div>
            <div className="text-[9px] text-slate-500">Horiz: {horizDistM >= 1000 ? `${(horizDistM / 1000).toFixed(2)} km` : `${horizDistM.toFixed(1)} m`}</div>
          </div>

          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Optimization Cost</div>
            <div className="text-sm font-bold text-amber-400 mt-0.5">{optCost.toFixed(1)}</div>
            <div className="text-[9px] text-slate-500">Analytical A* Metric</div>
          </div>

          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Elevation Span</div>
            <div className="text-sm font-bold text-cyan-300 mt-0.5">
              {minElev.toFixed(1)}m to {maxElev.toFixed(1)}m
            </div>
            <div className="text-[9px] text-slate-500">Span: {elevSpan.toFixed(1)} m</div>
          </div>

          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Ascent / Descent</div>
            <div className="text-sm font-bold text-blue-400 mt-0.5">
              +{elevSummary?.cumulative_elevation_gain_m.toFixed(1)}m
            </div>
            <div className="text-[9px] text-slate-500">Loss: -{elevSummary?.cumulative_elevation_loss_m.toFixed(1)}m</div>
          </div>

          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Slope &amp; Roughness</div>
            <div className="text-sm font-bold text-orange-400 mt-0.5">
              {terrainSummary?.mean_slope_deg.toFixed(1)}°
            </div>
            <div className="text-[9px] text-slate-500">Max: {terrainSummary?.max_slope_deg.toFixed(1)}° • RMS: {terrainSummary?.roughness_index_m.toFixed(1)}m</div>
          </div>

          <div className="bg-[#12162a] border border-[#202742] rounded p-2.5">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">TES Thermal Inertia</div>
            <div className="text-sm font-bold text-teal-400 mt-0.5">
              {thermalContext?.mean_tiu ? `${thermalContext.mean_tiu} tiu` : "Unmeasured"}
            </div>
            <div className="text-[9px] text-slate-500">MGS TES (Putzig 2007)</div>
          </div>
        </div>
      </div>

      {/* SECTION 1: INTERACTIVE ELEVATION PROFILE */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-[#1e253e] pb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm">📈</span>
            <span className="font-bold text-slate-200 uppercase text-[11px] tracking-wider">
              Interactive Elevation Profile Above MOLA Areoid
            </span>
          </div>
          <div className="text-[10px] text-slate-400">
            {elevSummary?.total_samples ?? 0} samples • Sampling Interval: ~{elevSummary?.sampling_interval_m ?? 0} m
          </div>
        </div>

        {/* Hover telemetry callout */}
        <div className="bg-[#101426] border border-[#232a4a] rounded px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px]">
          {hoveredPoint ? (
            <>
              <div className="flex items-center gap-3">
                <span>Dist: <strong className="text-white">{hoveredPoint.distance_m.toFixed(1)} m</strong></span>
                <span>Elev: <strong className="text-cyan-400">{hoveredPoint.elevation_m != null ? hoveredPoint.elevation_m.toFixed(2) : "N/A"} m</strong></span>
                <span>Slope: <strong className="text-amber-400">{hoveredPoint.slope_deg.toFixed(1)}°</strong></span>
                <span>Gradient: <strong className="text-purple-400">{hoveredPoint.local_gradient_pct.toFixed(2)}%</strong></span>
              </div>
              <div className="text-slate-400 text-[10px]">
                Coord: ({hoveredPoint.lat.toFixed(4)}°, {hoveredPoint.lon.toFixed(4)}°E)
              </div>
            </>
          ) : (
            <div className="text-slate-500 italic text-[10px]">
              Hover or scrub over the elevation profile to inspect local topographic coordinates, slope, and gradient.
            </div>
          )}
        </div>

        {/* Profile SVG */}
        <div className="relative overflow-x-auto bg-[#070914] border border-[#1a2038] rounded-lg p-2 shadow-inner">
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-auto cursor-crosshair select-none"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <defs>
              <linearGradient id="profileGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.02" />
              </linearGradient>
            </defs>

            {/* Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
              const y = padTop + chartH * t;
              const elevVal = maxElev - t * elevSpan;
              return (
                <g key={t}>
                  <line
                    x1={padLeft}
                    y1={y}
                    x2={padLeft + chartW}
                    y2={y}
                    stroke="#1e253e"
                    strokeDasharray="3,3"
                  />
                  <text
                    x={padLeft - 6}
                    y={y + 3}
                    fill="#64748b"
                    fontSize="9"
                    textAnchor="end"
                    fontFamily="monospace"
                  >
                    {elevVal.toFixed(0)}m
                  </text>
                </g>
              );
            })}

            {/* X-axis distance labels */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
              const x = padLeft + chartW * t;
              const distVal = t * maxDist;
              return (
                <text
                  key={t}
                  x={x}
                  y={svgHeight - 8}
                  fill="#64748b"
                  fontSize="9"
                  textAnchor="middle"
                  fontFamily="monospace"
                >
                  {distVal >= 1000 ? `${(distVal / 1000).toFixed(1)}k` : `${distVal.toFixed(0)}m`}
                </text>
              );
            })}

            {/* Filled Area */}
            {areaCoords && <polygon points={areaCoords} fill="url(#profileGradient)" />}

            {/* Profile Line */}
            {polylineCoords && (
              <polyline
                points={polylineCoords}
                fill="none"
                stroke="#22d3ee"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Hovered point marker & crosshair */}
            {hoveredPoint && (
              <>
                <line
                  x1={getSvgX(hoveredPoint.distance_m)}
                  y1={padTop}
                  x2={getSvgX(hoveredPoint.distance_m)}
                  y2={padTop + chartH}
                  stroke="#f59e0b"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <circle
                  cx={getSvgX(hoveredPoint.distance_m)}
                  cy={getSvgY(hoveredPoint.elevation_m ?? minElev)}
                  r="4"
                  fill="#f59e0b"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              </>
            )}
          </svg>
        </div>
      </div>

      {/* SECTION 2: TERRAIN INTELLIGENCE & SLOPE DISTRIBUTION */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-[#1e253e] pb-2">
          <span className="font-bold text-slate-200 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
            <span>⛰️</span> Terrain Intelligence &amp; Slope Distribution
          </span>
          <span className="text-[10px] text-slate-400">
            Roughness Class: <strong className="text-orange-400">{terrainSummary?.roughness_classification}</strong>
          </span>
        </div>

        {/* Stacked exposure bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>Slope Band Exposure Breakdown</span>
            <span>% of Surface Distance</span>
          </div>
          <div className="h-3.5 w-full bg-slate-900 rounded-full overflow-hidden flex shadow-inner border border-slate-800">
            <div style={{ width: `${terrainSummary?.slope_distribution.low || 0}%` }} className="bg-[#2ecc71]" title="Low (0-5°)" />
            <div style={{ width: `${terrainSummary?.slope_distribution.moderate || 0}%` }} className="bg-[#f39c12]" title="Moderate (5-15°)" />
            <div style={{ width: `${terrainSummary?.slope_distribution.high || 0}%` }} className="bg-[#e74c3c]" title="High (15-25°)" />
            <div style={{ width: `${terrainSummary?.slope_distribution.critical || terrainSummary?.slope_distribution.very_high || 0}%` }} className="bg-[#8e44ad]" title="Critical (>25°)" />
            <div style={{ width: `${terrainSummary?.slope_distribution.unknown || 0}%` }} className="bg-[#7f8c8d]" title="Unknown (NoData)" />
          </div>
        </div>

        {/* Table of slope bands */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
          {terrainSummary?.slope_exposure_bands.map((band) => (
            <div key={band.category} className="bg-[#12162a] border border-[#202742] rounded p-2.5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold capitalize text-slate-300">{band.category}</span>
                <span className="font-bold text-cyan-400">{band.percentage.toFixed(1)}%</span>
              </div>
              <div className="text-[10px] text-slate-400">
                {band.distance_m.toFixed(1)} m
              </div>
              <div className="text-[9px] text-slate-500 leading-tight">
                {band.description}
              </div>
            </div>
          ))}
        </div>

        <div className="text-[10px] text-slate-400 leading-relaxed bg-[#101426] border border-[#1e253e] rounded p-2.5">
          <strong className="text-slate-300">DEM Limitations:</strong> {terrainSummary?.terrain_limitations}
        </div>
      </div>

      {/* SECTION 3: GEOLOGICAL ROUTE CONTEXT (USGS SIM 3292) */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-[#1e253e] pb-2">
          <span className="font-bold text-slate-200 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
            <span>🌋</span> USGS SIM 3292 Geological Route Context
          </span>
          <span className="text-[10px] text-slate-400">
            Scale: <strong className="text-slate-200">1:20,000,000</strong> (Tanaka et al. 2014) • Boundary Uncertainty: ~5–10 km
          </span>
        </div>

        {/* Geological units traversed */}
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
            Chronostratigraphic Map Units Intersected:
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {geoContext?.units_traversed.map((u, i) => (
              <div key={i} className="bg-[#12162a] border border-[#202742] rounded p-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded font-bold text-xs bg-amber-950/60 border border-amber-600/50 text-amber-300">
                      {u.unit_code}
                    </span>
                    <span className="font-bold text-slate-200">{u.unit_name}</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-bold">{u.traversed_pct.toFixed(1)}%</span>
                </div>
                <div className="text-[10px] text-slate-400">
                  Era: <strong className="text-amber-400">{u.chronostratigraphic_period}</strong> • Distance: {u.distance_start_m.toFixed(0)}m to {u.distance_end_m.toFixed(0)}m ({u.traversed_length_m.toFixed(1)} m)
                </div>
                <p className="text-[10px] text-slate-400 leading-relaxed font-sans">{u.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Contact Boundaries & Structural Features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Contacts Crossed */}
          <div className="space-y-2">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
              Geological Contacts Crossed ({geoContext?.boundaries_crossed.length ?? 0}):
            </div>
            {geoContext?.boundaries_crossed.length ? (
              <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                {geoContext.boundaries_crossed.map((b, idx) => (
                  <div key={idx} className="bg-[#101426] border border-[#1e253e] rounded p-2 text-[10px] flex items-center justify-between">
                    <div>
                      <span className="text-amber-300 font-bold">{b.from_unit}</span> → <span className="text-amber-300 font-bold">{b.to_unit}</span>
                      <div className="text-slate-500">Coord: ({b.coord[0].toFixed(3)}°, {b.coord[1].toFixed(3)}°E)</div>
                    </div>
                    <div className="text-right text-slate-300 font-bold">
                      at {b.distance_m.toFixed(0)} m
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[10px] text-slate-500 italic bg-[#101426] border border-[#1e253e] rounded p-2.5">
                Traverse lies entirely within a single continuous mapped regional unit polygon.
              </div>
            )}
          </div>

          {/* Nearby Structures */}
          <div className="space-y-2">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
              Nearby Structural &amp; Tectonic Features ({geoContext?.nearby_structures.length ?? 0}):
            </div>
            {geoContext?.nearby_structures.length ? (
              <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                {geoContext.nearby_structures.map((s) => (
                  <div key={s.object_id} className="bg-[#101426] border border-[#1e253e] rounded p-2 text-[10px] flex items-center justify-between">
                    <div>
                      <span className="font-bold text-purple-300">{s.interpretation}</span> ({s.morphology})
                      <div className="text-slate-500">{s.origin} • {s.preservation} preservation</div>
                    </div>
                    <div className="text-right font-bold text-amber-400">
                      {s.distance_from_route_km.toFixed(1)} km
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[10px] text-slate-500 italic bg-[#101426] border border-[#1e253e] rounded p-2.5">
                No major tectonic scarps or wrinkle ridges cataloged within corridor bounds.
              </div>
            )}
          </div>
        </div>

        <div className="text-[10px] text-slate-400 leading-relaxed bg-[#101426] border border-[#1e253e] rounded p-2.5">
          <strong className="text-amber-400">Cartographic Scale Warning:</strong> {geoContext?.limitations_disclaimer}
        </div>
      </div>

      {/* SECTION 4: THERMOPHYSICAL CONTEXT (MGS TES THERMAL INERTIA) */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-[#1e253e] pb-2">
          <span className="font-bold text-slate-200 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
            <span>🌡️</span> MGS TES Thermal Inertia Context
          </span>
          <span className="text-[10px] text-slate-400">
            Native: <strong className="text-slate-200">{thermalContext?.native_resolution_desc}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-[#12162a] border border-[#202742] rounded p-3 text-center space-y-1">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Apparent Thermal Inertia</div>
            <div className="text-base font-bold text-teal-300">
              {thermalContext?.mean_tiu !== null && thermalContext?.mean_tiu !== undefined
                ? `${thermalContext.mean_tiu} tiu`
                : "Unmeasured"}
            </div>
            <div className="text-[9px] text-slate-500">
              Range: {thermalContext?.min_tiu ?? "N/A"} to {thermalContext?.max_tiu ?? "N/A"} tiu
            </div>
          </div>

          <div className="sm:col-span-2 bg-[#12162a] border border-[#202742] rounded p-3 space-y-1">
            <div className="text-[9px] uppercase tracking-wider text-slate-400">Regolith &amp; Surface Interpretation</div>
            <div className="text-[11px] font-bold text-slate-200">
              {thermalContext?.predominant_interpretation}
            </div>
            <div className="text-[9px] text-slate-400">
              {thermalContext?.themis_context}
            </div>
          </div>
        </div>

        <div className="space-y-1 text-[10px] text-slate-400 bg-[#101426] border border-[#1e253e] rounded p-2.5">
          <div><strong className="text-slate-300">Calibration Notes:</strong> {thermalContext?.calibration_notes}</div>
          <div className="text-red-400 font-bold pt-1">{thermalContext?.temperature_prohibition_disclaimer}</div>
        </div>
      </div>

      {/* SECTION 5: NEARBY SCIENCE OPPORTUNITIES (PHASE 8.7) */}
      <div className="bg-[#0b0e1b] border border-[#1e253e] rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-[#1e253e] pb-2">
          <span className="font-bold text-slate-200 uppercase text-[11px] tracking-wider flex items-center gap-1.5">
            <span>🎯</span> Nearby Phase 8.7 Science Opportunities ({scienceOpps.length})
          </span>
          <span className="text-[10px] text-slate-400">Connecting validated Martian discoveries to route</span>
        </div>

        {scienceOpps.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {scienceOpps.map((opp) => (
              <div key={opp.discovery_id} className="bg-[#12162a] border border-[#202742] rounded p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-950/60 border border-blue-600/40 text-blue-300 font-bold">
                      {opp.category_title}
                    </span>
                    <div className="font-bold text-slate-200 text-xs mt-1">{opp.title}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-bold text-emerald-400">{opp.distance_from_route_km.toFixed(1)} km</div>
                    <div className="text-[9px] text-slate-500">from route</div>
                  </div>
                </div>

                <div className="text-[10px] text-slate-400 space-y-1">
                  <div>Evidence Class: <strong className="text-cyan-300 uppercase text-[9px]">{opp.evidence_class}</strong></div>
                  <div>Closest Route Milepost: <strong className="text-slate-200">{opp.closest_route_milepost_m.toFixed(0)} m</strong></div>
                  <div className="pt-1 text-slate-300 italic">{opp.potential_investigation}</div>
                </div>

                <div className="text-[9px] text-slate-500 border-t border-[#1e253e] pt-1">
                  Limitation: {opp.scientific_limitations}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[10px] text-slate-500 italic bg-[#101426] border border-[#1e253e] rounded p-3 text-center">
            No cataloged Phase 8.7 science discoveries situated within the analysis corridor radius.
          </div>
        )}
      </div>

      {/* Mandatory Safety Disclaimer Footer */}
      <div className="bg-red-950/30 border border-red-800/50 rounded-lg p-3 text-red-300/90 text-[10px] leading-relaxed">
        <strong>SAFETY ADVISORY:</strong> {routeReport?.safety_disclaimer || traverseReport?.safety_disclaimer || DEFAULT_SAFETY_DISCLAIMER}
      </div>
    </div>
  );
};
