"use client";

import React, { useState, useEffect } from "react";
import {
  AtmosphericPressureEstimate,
  PressureResidualBenchmark,
  MarsSolarGeometry,
  HistoricalWeatherSummary,
  RouteEnvironmentalSummary,
  RoutePointEnvironment,
  ProvenanceClassification,
  ClimatologyPoint,
  ClimatologyProfileResponse,
  RouteClimatologySummary,
} from "@/lib/types";
import {
  fetchAtmosphericPressureEstimate,
  fetchPressureResiduals,
  fetchSolarGeometry,
  fetchHistoricalMeda,
  fetchHistoricalRems,
  enrichRouteEnvironment,
  fetchClimatologyPoint,
  fetchClimatologyProfile,
  enrichRouteClimatology,
} from "@/lib/api";

const ENVIRONMENTAL_SAFETY_DISCLAIMER =
  "ASTRONAUT SAFETY & OPERATIONAL PROHIBITION: Environmental metrics are derived from analytical barometric approximations " +
  "(P(z) = P_ref * exp(-z / H)), deterministic orbital solar geometry (Allison & McEwen 2000), and localized historical point observations " +
  "(MEDA/REMS Sol 1). They DO NOT constitute a live Martian weather forecast or life-support certification. " +
  "Never describe routes or conditions as 'astronaut-safe', 'safe pressure', or 'survivable'.";

interface EnvironmentalIntelligenceViewProps {
  routePoints?: Array<{ lat: number; lon: number; elevation_m: number; distance_m: number }> | null;
  routeName?: string | null;
}

export const EnvironmentalIntelligenceView: React.FC<EnvironmentalIntelligenceViewProps> = ({
  routePoints,
  routeName,
}) => {
  const [activeTab, setActiveTab] = useState<"pressure" | "solar" | "rovers" | "climatology" | "route">("pressure");

  // ── 1. Pressure Model State ──────────────────────────────────────────────
  const [elevationInput, setElevationInput] = useState<number>(-2560); // Default to Jezero floor
  const [pressureEstimate, setPressureEstimate] = useState<AtmosphericPressureEstimate | null>(null);
  const [pressureLoading, setPressureLoading] = useState<boolean>(false);
  const [residuals, setResiduals] = useState<Record<string, PressureResidualBenchmark> | null>(null);

  // ── 2. Solar Geometry State ──────────────────────────────────────────────
  const [solarLat, setSolarLat] = useState<number>(18.4447); // Jezero lat
  const [solarLon, setSolarLon] = useState<number>(77.4508);
  const [lsDeg, setLsDeg] = useState<number>(6.15); // Perseverance Sol 1 Ls
  const [ltstHours, setLtstHours] = useState<number>(13.5); // Midday
  const [timeSystem, setTimeSystem] = useState<"LTST" | "LMST">("LTST");
  const [dustTau, setDustTau] = useState<number>(0.3);
  const [solarGeometry, setSolarGeometry] = useState<MarsSolarGeometry | null>(null);
  const [solarLoading, setSolarLoading] = useState<boolean>(false);

  // ── 3. Rover Observations State ──────────────────────────────────────────
  const [activeRover, setActiveRover] = useState<"meda" | "rems">("meda");
  const [medaSummary, setMedaSummary] = useState<HistoricalWeatherSummary | null>(null);
  const [remsSummary, setRemsSummary] = useState<HistoricalWeatherSummary | null>(null);
  const [roverLoading, setRoverLoading] = useState<boolean>(false);

  // ── 4. Climatology (MCD v6.2) State ──────────────────────────────────────
  const [climLat, setClimLat] = useState<number>(18.4447);
  const [climLon, setClimLon] = useState<number>(77.4508);
  const [climLs, setClimLs] = useState<number>(0.0);
  const [climLtst, setClimLtst] = useState<number>(12.0);
  const [climElev, setClimElev] = useState<number>(-2560.0);
  const [climPoint, setClimPoint] = useState<ClimatologyPoint | null>(null);
  const [climProfile, setClimProfile] = useState<ClimatologyProfileResponse | null>(null);
  const [climProfileType, setClimProfileType] = useState<"diurnal" | "seasonal">("diurnal");
  const [climRouteSummary, setClimRouteSummary] = useState<RouteClimatologySummary | null>(null);
  const [climLoading, setClimLoading] = useState<boolean>(false);

  // ── 5. Route Environmental Enrichment State ──────────────────────────────
  const [routeSummary, setRouteSummary] = useState<RouteEnvironmentalSummary | null>(null);
  const [routeLoading, setRouteLoading] = useState<boolean>(false);

  // Fetch initial pressure estimate and residuals on mount
  useEffect(() => {
    updatePressureEstimate(elevationInput);
    fetchPressureResiduals()
      .then((data) => setResiduals(data))
      .catch((err) => console.error("Failed to load pressure residuals:", err));
  }, []);

  // Fetch initial solar geometry on mount or parameter change
  useEffect(() => {
    updateSolarGeometry(solarLat, solarLon, lsDeg, ltstHours, dustTau, timeSystem);
  }, [solarLat, solarLon, lsDeg, ltstHours, dustTau, timeSystem]);

  // Fetch historical rover data when tab opened
  useEffect(() => {
    if (activeTab === "rovers") {
      setRoverLoading(true);
      Promise.all([
        fetchHistoricalMeda().catch((e) => {
          console.error(e);
          return null;
        }),
        fetchHistoricalRems().catch((e) => {
          console.error(e);
          return null;
        }),
      ]).then(([meda, rems]) => {
        if (meda) setMedaSummary(meda);
        if (rems) setRemsSummary(rems);
        setRoverLoading(false);
      });
    }
  }, [activeTab]);

  // Enrich route when routePoints change or route tab selected
  useEffect(() => {
    if (routePoints && routePoints.length > 0) {
      setRouteLoading(true);
      enrichRouteEnvironment(routePoints, lsDeg, ltstHours, dustTau)
        .then((summary) => {
          setRouteSummary(summary);
          setRouteLoading(false);
        })
        .catch((err) => {
          console.error("Failed to enrich route environment:", err);
          setRouteLoading(false);
        });
    }
  }, [routePoints, lsDeg, ltstHours, dustTau]);

  // Fetch climatology point and profile when climatology tab active or parameters change
  useEffect(() => {
    if (activeTab === "climatology") {
      updateClimatology(climLat, climLon, climLs, climLtst, climElev, climProfileType);
    }
  }, [activeTab, climLat, climLon, climLs, climLtst, climElev, climProfileType]);

  // Enrich route with climatology if routePoints available
  useEffect(() => {
    if (routePoints && routePoints.length > 0 && activeTab === "climatology") {
      enrichRouteClimatology(routePoints, climLs, climLtst)
        .then((res) => setClimRouteSummary(res))
        .catch((err) => console.error("Failed to enrich route climatology:", err));
    }
  }, [routePoints, climLs, climLtst, activeTab]);

  const CLIMATOLOGY_LANDMARKS = [
    { id: "JEZERO", name: "Jezero Crater", lat: 18.4447, lon: 77.4508, elev: -2560.0 },
    { id: "GALE", name: "Gale Crater", lat: -4.5910, lon: 137.4410, elev: -4440.0 },
    { id: "TYRRHENA", name: "Tyrrhena Terra", lat: -21.3600, lon: 106.5300, elev: 2189.49 },
    { id: "APOLLINARIS", name: "Apollinaris Sulci", lat: -9.3000, lon: 174.4000, elev: -2930.77 },
    { id: "HOLDEN", name: "Holden Crater", lat: -26.4000, lon: 326.0000, elev: -1132.14 },
    { id: "OLYMPUS", name: "Olympus Mons", lat: 18.6500, lon: 226.2000, elev: 21287.0 },
    { id: "HELLAS", name: "Hellas Planitia", lat: -42.7000, lon: 70.0000, elev: -7152.0 },
  ];

  const updateClimatology = (
    lat: number,
    lon: number,
    ls: number,
    ltst: number,
    elev?: number,
    profType: "diurnal" | "seasonal" = "diurnal"
  ) => {
    setClimLoading(true);
    Promise.all([
      fetchClimatologyPoint(lat, lon, ls, ltst, elev).catch((e) => {
        console.error("Climatology point fetch error:", e);
        return null;
      }),
      fetchClimatologyProfile(lat, lon, profType, profType === "diurnal" ? ls : ltst, elev, 24).catch((e) => {
        console.error("Climatology profile fetch error:", e);
        return null;
      }),
    ]).then(([pt, prof]) => {
      if (pt) setClimPoint(pt);
      if (prof) setClimProfile(prof);
      setClimLoading(false);
    });
  };

  const updatePressureEstimate = (elev: number) => {
    setPressureLoading(true);
    fetchAtmosphericPressureEstimate(elev)
      .then((res) => {
        setPressureEstimate(res);
        setPressureLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch pressure estimate:", err);
        setPressureLoading(false);
      });
  };

  const updateSolarGeometry = (
    lat: number,
    lon: number,
    ls: number,
    tHours: number,
    tau: number,
    tSystem: "LTST" | "LMST" = "LTST"
  ) => {
    setSolarLoading(true);
    fetchSolarGeometry(lat, lon, ls, tHours, tau, tSystem)
      .then((res) => {
        setSolarGeometry(res);
        setSolarLoading(false);
      })
      .catch((err) => {
        console.error("Failed to calculate solar geometry:", err);
        setSolarLoading(false);
      });
  };

  const renderClassificationBadge = (classification: ProvenanceClassification) => {
    switch (classification) {
      case "Historical Observation":
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-blue-950/80 text-blue-300 border border-blue-700/60 font-semibold">
            ● Historical Observation
          </span>
        );
      case "Analytical Model":
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 font-semibold">
            ▲ Analytical Model
          </span>
        );
      case "Climatological Model":
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-purple-950/80 text-purple-300 border border-purple-700/60 font-semibold">
            ● Climatological Model
          </span>
        );
      case "Derived Estimate":
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950/80 text-amber-300 border border-amber-700/60 font-semibold">
            ◆ Derived Estimate
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-900 text-slate-400 border border-slate-700 font-semibold">
            Unavailable
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col space-y-4 text-slate-200">
      {/* ── Header & Disclaimer ── */}
      <div className="p-3.5 bg-[#0e1222] border border-[#232b48] rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-orange-400 font-bold text-sm tracking-wider uppercase">
              MARS-X Environmental Intelligence
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
              Phase 8.9.1
            </span>
          </div>
          <div className="flex space-x-1.5 text-[10px]">
            {renderClassificationBadge("Analytical Model")}
            {renderClassificationBadge("Historical Observation")}
          </div>
        </div>

        <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
          Scientifically constrained atmospheric reference modeling, deterministic solar geometry, and
          in-situ PDS4 rover meteorological records.
        </p>

        {/* Mandatory Safety Box */}
        <div className="p-2.5 bg-red-950/30 border border-red-800/60 rounded text-[11px] text-red-300/90 leading-tight">
          <span className="font-bold tracking-wide text-red-400 uppercase mr-1.5">
            Operational Warning:
          </span>
          {ENVIRONMENTAL_SAFETY_DISCLAIMER}
        </div>
      </div>

      {/* ── Sub-navigation Tabs ── */}
      <div className="flex border-b border-[#232b48] text-xs">
        <button
          onClick={() => setActiveTab("pressure")}
          className={`flex-1 py-2 font-medium border-b-2 transition-colors ${
            activeTab === "pressure"
              ? "border-orange-500 text-orange-400 bg-[#141933]/50"
              : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#141933]/20"
          }`}
        >
          Atmospheric Pressure
        </button>
        <button
          onClick={() => setActiveTab("solar")}
          className={`flex-1 py-2 font-medium border-b-2 transition-colors ${
            activeTab === "solar"
              ? "border-orange-500 text-orange-400 bg-[#141933]/50"
              : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#141933]/20"
          }`}
        >
          Solar Geometry
        </button>
        <button
          onClick={() => setActiveTab("rovers")}
          className={`flex-1 py-2 font-medium border-b-2 transition-colors ${
            activeTab === "rovers"
              ? "border-orange-500 text-orange-400 bg-[#141933]/50"
              : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#141933]/20"
          }`}
        >
          Rover In-Situ Data
        </button>
        <button
          onClick={() => setActiveTab("climatology")}
          className={`flex-1 py-2 font-medium border-b-2 transition-colors ${
            activeTab === "climatology"
              ? "border-orange-500 text-orange-400 bg-[#141933]/50"
              : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#141933]/20"
          }`}
        >
          Climatology (MCD)
        </button>
        {routePoints && routePoints.length > 0 && (
          <button
            onClick={() => setActiveTab("route")}
            className={`flex-1 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "route"
                ? "border-orange-500 text-orange-400 bg-[#141933]/50"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#141933]/20"
            }`}
          >
            Route Profile
          </button>
        )}
      </div>

      {/* ── TAB 1: Atmospheric Pressure Reference Model ── */}
      {activeTab === "pressure" && (
        <div className="space-y-4">
          {/* Formula & Calculator Card */}
          <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200">
                Hydrostatic Barometric Approximation
              </span>
              {renderClassificationBadge("Analytical Model")}
            </div>

            <div className="p-2.5 bg-[#12162a] border border-[#232b48] rounded font-mono text-xs text-orange-300">
              P(z) = P_ref × exp(-z / H)
              <span className="block text-[10px] text-slate-400 font-sans mt-0.5">
                Reference pressure P_ref = 610.0 Pa (datum z = 0 m), scale height H = 11,100 m. Datum: MOLA Areoid.
              </span>
            </div>

            {/* Elevation Slider / Input */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="text-slate-300 font-medium">Elevation relative to MOLA Areoid:</label>
                <span className="font-mono text-orange-400 font-bold">
                  {elevationInput >= 0 ? `+${elevationInput}` : elevationInput} m
                </span>
              </div>
              <input
                type="range"
                min="-8000"
                max="25000"
                step="50"
                value={elevationInput}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setElevationInput(val);
                  updatePressureEstimate(val);
                }}
                className="w-full h-1.5 bg-[#1e253e] rounded-lg appearance-none cursor-pointer accent-orange-500"
              />

              {/* Quick Preset Buttons */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                <button
                  onClick={() => {
                    setElevationInput(-4440);
                    updatePressureEstimate(-4440);
                  }}
                  className="px-2 py-0.5 text-[10px] bg-[#141933] hover:bg-[#1f2648] text-slate-300 rounded border border-[#273256]"
                >
                  Gale Floor (-4440m)
                </button>
                <button
                  onClick={() => {
                    setElevationInput(-2560);
                    updatePressureEstimate(-2560);
                  }}
                  className="px-2 py-0.5 text-[10px] bg-[#141933] hover:bg-[#1f2648] text-slate-300 rounded border border-[#273256]"
                >
                  Jezero Floor (-2560m)
                </button>
                <button
                  onClick={() => {
                    setElevationInput(0);
                    updatePressureEstimate(0);
                  }}
                  className="px-2 py-0.5 text-[10px] bg-[#141933] hover:bg-[#1f2648] text-slate-300 rounded border border-[#273256]"
                >
                  Datum (0m)
                </button>
                <button
                  onClick={() => {
                    setElevationInput(2189);
                    updatePressureEstimate(2189);
                  }}
                  className="px-2 py-0.5 text-[10px] bg-[#141933] hover:bg-[#1f2648] text-slate-300 rounded border border-[#273256]"
                >
                  Tyrrhena (+2189m)
                </button>
                <button
                  onClick={() => {
                    setElevationInput(21287);
                    updatePressureEstimate(21287);
                  }}
                  className="px-2 py-0.5 text-[10px] bg-[#141933] hover:bg-[#1f2648] text-slate-300 rounded border border-[#273256]"
                >
                  Olympus Mons (+21287m)
                </button>
              </div>
            </div>

            {/* Computed Pressure Result */}
            {pressureEstimate && (
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1e253e]">
                <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                  <span className="text-[10px] text-slate-400 block uppercase">Reference Pressure</span>
                  <span className="text-base font-mono font-bold text-orange-400">
                    {pressureEstimate.reference_atmospheric_pressure_estimate_pa.toFixed(2)} Pa
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    {(pressureEstimate.reference_atmospheric_pressure_estimate_pa / 100.0).toFixed(2)} mbar
                  </span>
                </div>
                <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                  <span className="text-[10px] text-slate-400 block uppercase">Earth Sea-Level Comparison</span>
                  <span className="text-base font-mono font-bold text-slate-300">
                    {((pressureEstimate.reference_atmospheric_pressure_estimate_pa / 101325.0) * 100).toFixed(2)}%
                  </span>
                  <span className="text-[10px] text-slate-500 block">Relative to 101,325 Pa</span>
                </div>
              </div>
            )}
          </div>

          {/* Ground-Truth Residual Analysis Card */}
          {residuals && (
            <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">
                    Rover Ground-Truth Residual Benchmarks
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    Analytical model P(z) evaluated against authentic Sol 1 in-situ rover observations.
                  </span>
                </div>
                {renderClassificationBadge("Derived Estimate")}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {/* MEDA Jezero */}
                <div className="p-2.5 bg-[#12162a] border border-[#232b48] rounded space-y-1.5 text-xs">
                  <div className="flex justify-between items-center font-medium text-slate-200">
                    <span>{residuals.MEDA_JEZERO?.station_name}</span>
                    <span className="text-blue-400 font-mono text-[10px]">Sol 1</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-300">
                    <div>Elevation: <span className="font-mono">{residuals.MEDA_JEZERO?.elevation_m}m</span></div>
                    <div>Model P: <span className="font-mono text-orange-300">{residuals.MEDA_JEZERO?.model_pressure_pa} Pa</span></div>
                    <div>Observed Mean: <span className="font-mono text-blue-300">{residuals.MEDA_JEZERO?.observed_mean_pressure_pa} Pa</span></div>
                    <div>Residual: <span className="font-mono text-red-400 font-bold">{residuals.MEDA_JEZERO?.residual_pa > 0 ? `+${residuals.MEDA_JEZERO?.residual_pa}` : residuals.MEDA_JEZERO?.residual_pa} Pa ({residuals.MEDA_JEZERO?.residual_percent}%)</span></div>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-tight pt-1 border-t border-[#1e253e]">
                    {residuals.MEDA_JEZERO?.notes}
                  </p>
                </div>

                {/* REMS Gale */}
                <div className="p-2.5 bg-[#12162a] border border-[#232b48] rounded space-y-1.5 text-xs">
                  <div className="flex justify-between items-center font-medium text-slate-200">
                    <span>{residuals.REMS_GALE?.station_name}</span>
                    <span className="text-blue-400 font-mono text-[10px]">Sol 1</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-300">
                    <div>Elevation: <span className="font-mono">{residuals.REMS_GALE?.elevation_m}m</span></div>
                    <div>Model P: <span className="font-mono text-orange-300">{residuals.REMS_GALE?.model_pressure_pa} Pa</span></div>
                    <div>Observed Mean: <span className="font-mono text-blue-300">{residuals.REMS_GALE?.observed_mean_pressure_pa} Pa</span></div>
                    <div>Residual: <span className="font-mono text-red-400 font-bold">{residuals.REMS_GALE?.residual_pa > 0 ? `+${residuals.REMS_GALE?.residual_pa}` : residuals.REMS_GALE?.residual_pa} Pa ({residuals.REMS_GALE?.residual_percent}%)</span></div>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-tight pt-1 border-t border-[#1e253e]">
                    {residuals.REMS_GALE?.notes}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: Deterministic Mars Solar Geometry ── */}
      {activeTab === "solar" && (
        <div className="space-y-4">
          <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200">
                Mars Solar Geometry & Insolation (Allison & McEwen 2000)
              </span>
              {renderClassificationBadge("Analytical Model")}
            </div>

            {/* Sliders Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {/* Solar Longitude Ls */}
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-300 font-medium">Solar Longitude (Ls):</span>
                  <span className="font-mono text-orange-400 font-bold">{lsDeg.toFixed(1)}°</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="359.9"
                  step="1"
                  value={lsDeg}
                  onChange={(e) => setLsDeg(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#1e253e] rounded appearance-none cursor-pointer accent-orange-500"
                />
                <span className="text-[10px] text-slate-400 block">
                  {solarGeometry?.season_name}
                </span>
              </div>

              {/* Local Solar Time (LTST / LMST) */}
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-slate-300 font-medium">Local Time:</span>
                    <button
                      type="button"
                      onClick={() => setTimeSystem(timeSystem === "LTST" ? "LMST" : "LTST")}
                      className="px-1.5 py-0.5 text-[9px] font-mono bg-[#161c36] hover:bg-[#1f284d] border border-[#2e3b68] rounded text-cyan-300"
                      title="Toggle time system between Local True Solar Time (LTST) and Local Mean Solar Time (LMST)"
                    >
                      {timeSystem}
                    </button>
                  </div>
                  <span className="font-mono text-orange-400 font-bold">{ltstHours.toFixed(1)} h</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="23.9"
                  step="0.1"
                  value={ltstHours}
                  onChange={(e) => setLtstHours(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#1e253e] rounded appearance-none cursor-pointer accent-orange-500"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>{Math.floor(ltstHours)}:{String(Math.floor((ltstHours % 1) * 60)).padStart(2, "0")} {timeSystem}</span>
                  {solarGeometry && (
                    <span className="text-cyan-400">
                      {timeSystem === "LTST" ? `LMST ${solarGeometry.local_mean_solar_time_hours}h` : `LTST ${solarGeometry.local_true_solar_time_hours}h`} (EOT {solarGeometry.equation_of_time_minutes > 0 ? `+` : ``}{solarGeometry.equation_of_time_minutes}m)
                    </span>
                  )}
                </div>
              </div>

              {/* Dust Optical Depth (Tau) */}
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-300 font-medium">Dust Optical Depth (τ):</span>
                  <span className="font-mono text-orange-400 font-bold">{dustTau.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.05"
                  value={dustTau}
                  onChange={(e) => setDustTau(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#1e253e] rounded appearance-none cursor-pointer accent-orange-500"
                />
                <span className="text-[10px] text-slate-400 block">
                  {dustTau < 0.3 ? "Clear atmosphere" : dustTau < 1.0 ? "Moderate dust haze" : "Dust storm conditions"}
                </span>
              </div>

              {/* Latitude */}
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-300 font-medium">Latitude:</span>
                  <span className="font-mono text-orange-400 font-bold">{solarLat.toFixed(2)}°</span>
                </div>
                <input
                  type="range"
                  min="-89"
                  max="89"
                  step="1"
                  value={solarLat}
                  onChange={(e) => setSolarLat(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#1e253e] rounded appearance-none cursor-pointer accent-orange-500"
                />
                <span className="text-[10px] text-slate-400 block">
                  {solarLat >= 0 ? "Northern Hemisphere" : "Southern Hemisphere"}
                </span>
              </div>
            </div>

            {/* Results Grid */}
            {solarGeometry && (
              <div className="space-y-3 pt-3 border-t border-[#1e253e]">
                {/* Orbital & Celestial Parameters */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Solar Zenith Angle</span>
                    <span className="text-sm font-mono font-bold text-orange-300">
                      {solarGeometry.solar_zenith_angle_deg}°
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Elev: {solarGeometry.solar_elevation_deg}°
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Diurnal State</span>
                    <span
                      className={`text-sm font-mono font-bold ${
                        solarGeometry.is_day ? "text-emerald-400" : "text-blue-400"
                      }`}
                    >
                      {solarGeometry.day_night_status}
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {solarGeometry.polar_condition ||
                        (solarGeometry.sunrise_hour && solarGeometry.sunset_hour
                          ? `Rise ${solarGeometry.sunrise_hour}h / Set ${solarGeometry.sunset_hour}h`
                          : "Diurnal")}
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Mars-Sun Distance</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {solarGeometry.mars_sun_distance_au} AU
                    </span>
                    <span className="text-[10px] text-slate-500 block font-mono">
                      Dec: {solarGeometry.solar_declination_deg}°
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Equation of Time</span>
                    <span className="text-sm font-mono font-bold text-cyan-300">
                      {solarGeometry.equation_of_time_minutes > 0 ? `+` : ``}{solarGeometry.equation_of_time_minutes} min
                    </span>
                    <span className="text-[10px] text-slate-500 block font-mono">
                      LMST: {solarGeometry.local_mean_solar_time_hours}h
                    </span>
                  </div>
                </div>

                {/* Irradiance Breakdown: TOA Normal vs TOA Horizontal vs Surface Horizontal */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">TOA Normal Irradiance (S_Mars)</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {solarGeometry.toa_normal_irradiance_w_m2} W/m²
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      S_0 / r² (normal incidence at top of atmosphere)
                    </span>
                  </div>

                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">TOA Direct Horizontal Flux</span>
                    <span className="text-sm font-mono font-bold text-amber-200">
                      {solarGeometry.toa_horizontal_irradiance_w_m2} W/m²
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      S_Mars × max(0, cos(SZA))
                    </span>
                  </div>

                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase font-medium">Direct Beam Surface Horizontal</span>
                    <span className="text-sm font-mono font-bold text-amber-400">
                      {solarGeometry.surface_direct_horizontal_irradiance_w_m2} W/m²
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Extinguished direct beam (excludes diffuse skylight)
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 3: Historical Rover Observations (PDS4) ── */}
      {activeTab === "rovers" && (
        <div className="space-y-4">
          <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200">
                Historical In-Situ Rover Meteorological Ground Truth
              </span>
              {renderClassificationBadge("Historical Observation")}
            </div>

            {/* Rover Selector */}
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveRover("meda")}
                className={`px-3 py-1.5 text-xs font-medium rounded border transition-colors ${
                  activeRover === "meda"
                    ? "bg-blue-900/60 border-blue-500 text-blue-200"
                    : "bg-[#141933] border-[#273256] text-slate-400 hover:text-slate-200"
                }`}
              >
                Mars 2020 Perseverance — MEDA (Jezero Crater)
              </button>
              <button
                onClick={() => setActiveRover("rems")}
                className={`px-3 py-1.5 text-xs font-medium rounded border transition-colors ${
                  activeRover === "rems"
                    ? "bg-blue-900/60 border-blue-500 text-blue-200"
                    : "bg-[#141933] border-[#273256] text-slate-400 hover:text-slate-200"
                }`}
              >
                MSL Curiosity — REMS (Gale Crater)
              </button>
            </div>

            {/* Warning Banner */}
            <div className="p-2 bg-blue-950/40 border border-blue-800/50 rounded text-[10px] text-blue-300 leading-tight">
              {activeRover === "meda"
                ? medaSummary?.temporal_disclaimer
                : remsSummary?.temporal_disclaimer}
            </div>

            {/* Rover Statistics Cards */}
            {activeRover === "meda" && medaSummary && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Atmospheric Pressure</span>
                    <span className="text-sm font-mono font-bold text-blue-300">
                      {medaSummary.pressure_summary_pa?.mean_pa} Pa
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Min: {medaSummary.pressure_summary_pa?.min_pa} / Max: {medaSummary.pressure_summary_pa?.max_pa}
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Sensor Temperature</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {medaSummary.ambient_temp_summary_k?.mean_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {((medaSummary.ambient_temp_summary_k?.mean_k || 0) - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">PDS4 Sample Count</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {medaSummary.total_samples}
                    </span>
                    <span className="text-[10px] text-slate-500 block">Sol 1 Calibrated Rows</span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Thermal IR Irradiance</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {medaSummary.irradiance_summary_w_m2?.downward_lw_mean_w_m2 || "33.5"} W/m²
                    </span>
                    <span className="text-[10px] text-slate-500 block">Downward Sky IR Flux</span>
                  </div>
                </div>

                {/* Sample Records Table */}
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-300">
                    PDS4 Time Series Samples (Sol 1)
                  </span>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[10px] font-mono border border-[#1e253e]">
                      <thead className="bg-[#141933] text-slate-400">
                        <tr>
                          <th className="p-1.5">SCLK</th>
                          <th className="p-1.5">LMST</th>
                          <th className="p-1.5">LTST</th>
                          <th className="p-1.5">Pressure (Pa)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e253e] text-slate-300">
                        {medaSummary.sample_records.map((r, i) => (
                          <tr key={i} className="hover:bg-[#141933]/40">
                            <td className="p-1.5">{r.timestamp_or_sclk}</td>
                            <td className="p-1.5">{r.lmst}</td>
                            <td className="p-1.5">{r.ltst}</td>
                            <td className="p-1.5 text-blue-300 font-bold">{r.pressure_pa}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* REMS Statistics Cards */}
            {activeRover === "rems" && remsSummary && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Atmospheric Pressure</span>
                    <span className="text-sm font-mono font-bold text-blue-300">
                      {remsSummary.pressure_summary_pa?.mean_pa} Pa
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Min: {remsSummary.pressure_summary_pa?.min_pa} / Max: {remsSummary.pressure_summary_pa?.max_pa}
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Ambient Air Temp</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {remsSummary.ambient_temp_summary_k?.mean_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {((remsSummary.ambient_temp_summary_k?.mean_k || 0) - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Ground Temp (GTS)</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {remsSummary.ground_temp_summary_k?.mean_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {((remsSummary.ground_temp_summary_k?.mean_k || 0) - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">PDS4 Sample Count</span>
                    <span className="text-sm font-mono font-bold text-slate-200">
                      {remsSummary.total_samples}
                    </span>
                    <span className="text-[10px] text-slate-500 block">Sol 1 Valid Records</span>
                  </div>
                </div>

                {/* Sample Records Table */}
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-300">
                    PDS4 Time Series Samples (Sol 1)
                  </span>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[10px] font-mono border border-[#1e253e]">
                      <thead className="bg-[#141933] text-slate-400">
                        <tr>
                          <th className="p-1.5">SCLK/TS</th>
                          <th className="p-1.5">LMST</th>
                          <th className="p-1.5">LTST</th>
                          <th className="p-1.5">Pressure (Pa)</th>
                          <th className="p-1.5">Air Temp (K)</th>
                          <th className="p-1.5">Ground Temp (K)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e253e] text-slate-300">
                        {remsSummary.sample_records.map((r, i) => (
                          <tr key={i} className="hover:bg-[#141933]/40">
                            <td className="p-1.5">{r.timestamp_or_sclk}</td>
                            <td className="p-1.5">{r.lmst}</td>
                            <td className="p-1.5">{r.ltst}</td>
                            <td className="p-1.5 text-blue-300 font-bold">{r.pressure_pa}</td>
                            <td className="p-1.5">{r.ambient_temperature_k}</td>
                            <td className="p-1.5">{r.ground_temperature_k}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 4: Seasonal and Diurnal Climatology (MCD v6.2) ── */}
      {activeTab === "climatology" && (
        <div className="space-y-4">
          <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold text-slate-200">
                  Mars Climate Database (MCD v6.2) Climatology
                </h4>
                <span className="text-[10px] text-slate-400">
                  Laboratoire de Météorologie Dynamique (LMD/CNRS/Sorbonne/ESA/CNES) • Forget et al. (1999)
                </span>
              </div>
              {renderClassificationBadge("Climatological Model")}
            </div>

            {/* Landmark Quick Selectors */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Exploration Landmark Anchors
              </span>
              <div className="flex flex-wrap gap-1.5">
                {CLIMATOLOGY_LANDMARKS.map((lm) => {
                  const isSelected =
                    Math.abs(climLat - lm.lat) < 0.01 && Math.abs(climLon - lm.lon) < 0.01;
                  return (
                    <button
                      key={lm.id}
                      onClick={() => {
                        setClimLat(lm.lat);
                        setClimLon(lm.lon);
                        setClimElev(lm.elev);
                      }}
                      className={`px-2.5 py-1 text-[11px] rounded border transition-colors ${
                        isSelected
                          ? "bg-purple-900/60 border-purple-500 text-purple-200 font-semibold"
                          : "bg-[#141933] border-[#273256] text-slate-400 hover:text-slate-200 hover:border-slate-500"
                      }`}
                    >
                      {lm.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Input Parameter Sliders & Boxes */}
            <div className="p-3 bg-[#12162a] border border-[#232b48] rounded space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">Latitude (°N/S)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="-90"
                    max="90"
                    value={climLat}
                    onChange={(e) => setClimLat(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-[#0b0e1b] border border-[#273256] rounded text-slate-200 font-mono text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">East Longitude (°E)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0"
                    max="360"
                    value={climLon}
                    onChange={(e) => setClimLon(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-[#0b0e1b] border border-[#273256] rounded text-slate-200 font-mono text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">MOLA Elevation (m)</label>
                  <input
                    type="number"
                    step="10"
                    value={climElev ?? 0}
                    onChange={(e) => setClimElev(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-[#0b0e1b] border border-[#273256] rounded text-slate-200 font-mono text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              {/* Solar Longitude Ls Slider */}
              <div className="space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[11px] text-slate-300">
                    Solar Longitude Ls: <strong className="font-mono text-purple-400">{climLs.toFixed(1)}°</strong>
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950/60 border border-purple-800/50 text-purple-300">
                    {climPoint ? climPoint.season_name : (
                      climLs < 90 ? "N. Spring / S. Autumn" :
                      climLs < 180 ? "N. Summer / S. Winter (Aphelion Ls=71°)" :
                      climLs < 270 ? "N. Autumn / S. Spring (Perihelion Ls=251°)" :
                      "N. Winter / S. Summer"
                    )}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="359"
                  step="1"
                  value={climLs}
                  onChange={(e) => setClimLs(parseFloat(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer h-1.5 bg-[#0b0e1b] rounded"
                />
              </div>

              {/* Local True Solar Time LTST Slider */}
              <div className="space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[11px] text-slate-300">
                    Local True Solar Time: <strong className="font-mono text-purple-400">{climLtst.toFixed(1)}h</strong>
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {climLtst >= 6 && climLtst < 18 ? "☀️ Daytime Insolation" : "🌙 Nighttime Radiative Cooling"}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="23.9"
                  step="0.1"
                  value={climLtst}
                  onChange={(e) => setClimLtst(parseFloat(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer h-1.5 bg-[#0b0e1b] rounded"
                />
              </div>
            </div>

            {/* Current Climatological Metrics Grid */}
            {climLoading ? (
              <div className="p-6 text-center text-xs text-slate-400">
                Evaluating multidimensional climatology interpolation...
              </div>
            ) : climPoint ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Surface Pressure</span>
                    <span className="text-base font-mono font-bold text-orange-400">
                      {climPoint.surface_pressure_pa} Pa
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Scaled to z={climPoint.elevation_m}m
                    </span>
                  </div>

                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">10m Air Temp (ALS)</span>
                    <span className="text-base font-mono font-bold text-sky-400">
                      {climPoint.atmospheric_temperature_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {(climPoint.atmospheric_temperature_k - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Ground Skin Temp</span>
                    <span className="text-base font-mono font-bold text-amber-400">
                      {climPoint.surface_temperature_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {(climPoint.surface_temperature_k - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2.5 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Wind Speed & Dir</span>
                    <span className="text-base font-mono font-bold text-emerald-400">
                      {climPoint.wind_speed_m_s} m/s
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono block">
                      {climPoint.wind_cardinal} ({climPoint.wind_direction_deg}°)
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Dust Optical Depth (τ)</span>
                    <span className="text-sm font-mono font-bold text-yellow-500">
                      {climPoint.dust_optical_depth}
                    </span>
                    <span className="text-[10px] text-slate-500 block">Daily column visible tau</span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Atmospheric Density</span>
                    <span className="text-sm font-mono font-bold text-slate-300">
                      {climPoint.density_kg_m3} kg/m³
                    </span>
                    <span className="text-[10px] text-slate-500 block">Near-surface CO₂</span>
                  </div>

                  <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                    <span className="text-[10px] text-slate-400 block uppercase">Spatial Method</span>
                    <span className="text-xs font-semibold text-purple-300 truncate block">
                      {climPoint.is_landmark ? "● Landmark Anchor" : "▲ Spatial Grid Interp"}
                    </span>
                    <span className="text-[10px] text-slate-500 block truncate">
                      {climPoint.nearest_landmark ? `${climPoint.nearest_landmark} (${climPoint.distance_to_landmark_km} km)` : "Global node"}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Profile Curve Section */}
            {climProfile && (
              <div className="p-3 bg-[#12162a] border border-[#232b48] rounded space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-300">
                      Climatological Profile Evolution
                    </span>
                    <span className="text-[10px] text-slate-500">
                      ({climProfile.fixed_parameter})
                    </span>
                  </div>
                  <div className="flex space-x-1.5">
                    <button
                      onClick={() => setClimProfileType("diurnal")}
                      className={`px-2 py-0.5 text-[10px] rounded border ${
                        climProfileType === "diurnal"
                          ? "bg-purple-900/60 border-purple-500 text-purple-200"
                          : "bg-[#0b0e1b] border-[#273256] text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      24h Diurnal
                    </button>
                    <button
                      onClick={() => setClimProfileType("seasonal")}
                      className={`px-2 py-0.5 text-[10px] rounded border ${
                        climProfileType === "seasonal"
                          ? "bg-purple-900/60 border-purple-500 text-purple-200"
                          : "bg-[#0b0e1b] border-[#273256] text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      360° Seasonal
                    </button>
                  </div>
                </div>

                {/* Profile Extrema Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] font-mono">
                  <div className="p-1.5 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-slate-500 block">Min Air Temp</span>
                    <span className="text-sky-400 font-bold">{climProfile.min_temperature_k} K</span>
                  </div>
                  <div className="p-1.5 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-slate-500 block">Max Air Temp</span>
                    <span className="text-sky-400 font-bold">{climProfile.max_temperature_k} K</span>
                  </div>
                  <div className="p-1.5 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-slate-500 block">Thermal Swing (ΔT)</span>
                    <span className="text-amber-400 font-bold">
                      {(climProfile.max_temperature_k - climProfile.min_temperature_k).toFixed(1)} K
                    </span>
                  </div>
                  <div className="p-1.5 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-slate-500 block">Mean Pressure</span>
                    <span className="text-orange-400 font-bold">{climProfile.mean_pressure_pa} Pa</span>
                  </div>
                </div>

                {/* Subsampled Profile Table */}
                <div className="overflow-x-auto max-h-40">
                  <table className="w-full text-left text-[10px] font-mono border border-[#1e253e]">
                    <thead className="bg-[#141933] text-slate-400 sticky top-0">
                      <tr>
                        <th className="p-1.5">{climProfile.independent_variable}</th>
                        <th className="p-1.5">Surface Pressure (Pa)</th>
                        <th className="p-1.5">Air Temp (K)</th>
                        <th className="p-1.5">Ground Temp (K)</th>
                        <th className="p-1.5">Wind (m/s)</th>
                        <th className="p-1.5">Dust (τ)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e253e] text-slate-300">
                      {climProfile.points.filter((_, idx) => idx % 2 === 0).map((pt, i) => (
                        <tr key={i} className="hover:bg-[#141933]/40">
                          <td className="p-1.5 font-bold text-purple-300">
                            {climProfileType === "diurnal" ? `${pt.step_value.toFixed(1)}h` : `${pt.step_value.toFixed(0)}°`}
                          </td>
                          <td className="p-1.5 text-orange-400">{pt.surface_pressure_pa}</td>
                          <td className="p-1.5 text-sky-400">{pt.atmospheric_temperature_k}</td>
                          <td className="p-1.5 text-amber-400">{pt.surface_temperature_k}</td>
                          <td className="p-1.5 text-emerald-400">{pt.wind_speed_m_s}</td>
                          <td className="p-1.5 text-yellow-500">{pt.dust_optical_depth}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Route Climatology Enrichment (if route active) */}
            {climRouteSummary && (
              <div className="p-3 bg-[#12162a] border border-[#232b48] rounded space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">
                    Traverse Climatological Conditions ({routeName || "Active Marswalk"})
                  </span>
                  {renderClassificationBadge("Derived Estimate")}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-[10px] text-slate-400 block uppercase">Mean Traverse P</span>
                    <span className="text-sm font-mono font-bold text-orange-400">
                      {climRouteSummary.mean_climatology_pressure_pa} Pa
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {climRouteSummary.min_climatology_pressure_pa} – {climRouteSummary.max_climatology_pressure_pa} Pa
                    </span>
                  </div>

                  <div className="p-2 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-[10px] text-slate-400 block uppercase">Mean Air Temp</span>
                    <span className="text-sm font-mono font-bold text-sky-400">
                      {climRouteSummary.mean_climatology_temp_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {(climRouteSummary.mean_climatology_temp_k - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-[10px] text-slate-400 block uppercase">Mean Ground Temp</span>
                    <span className="text-sm font-mono font-bold text-amber-400">
                      {climRouteSummary.mean_surface_temp_k} K
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      {(climRouteSummary.mean_surface_temp_k - 273.15).toFixed(1)} °C
                    </span>
                  </div>

                  <div className="p-2 bg-[#0b0e1b] rounded border border-[#1e253e]">
                    <span className="text-[10px] text-slate-400 block uppercase">Mean Wind</span>
                    <span className="text-sm font-mono font-bold text-emerald-400">
                      {climRouteSummary.mean_wind_speed_m_s} m/s
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Max: {climRouteSummary.max_wind_speed_m_s} m/s
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 5: Route Environmental Profile ── */}
      {activeTab === "route" && routeSummary && (
        <div className="space-y-4">
          <div className="p-3.5 bg-[#0b0e1b] border border-[#1e253e] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold text-slate-200">
                  Route Environmental Profile: {routeName || "Active Marswalk Route"}
                </h4>
                <span className="text-[10px] text-slate-400">
                  Evaluated at Ls={routeSummary.solar_longitude_ls_deg}°, LTST={routeSummary.local_true_solar_time_hours}h, τ={routeSummary.optical_depth_tau || "0.0"}
                </span>
              </div>
              {renderClassificationBadge("Derived Estimate")}
            </div>

            {/* Profile Statistics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                <span className="text-[10px] text-slate-400 block uppercase">Mean Pressure</span>
                <span className="text-sm font-mono font-bold text-orange-400">
                  {routeSummary.mean_pressure_pa} Pa
                </span>
                <span className="text-[10px] text-slate-500 block">
                  Range: {routeSummary.min_pressure_pa} – {routeSummary.max_pressure_pa} Pa
                </span>
              </div>

              <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                <span className="text-[10px] text-slate-400 block uppercase">Mean Surface Flux</span>
                <span className="text-sm font-mono font-bold text-amber-300">
                  {routeSummary.mean_surface_flux_w_m2} W/m²
                </span>
                <span className="text-[10px] text-slate-500 block">
                  Direct beam (max {routeSummary.max_surface_flux_w_m2} W/m²)
                </span>
              </div>

              <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                <span className="text-[10px] text-slate-400 block uppercase">Daylight Exposure</span>
                <span className="text-sm font-mono font-bold text-emerald-400">
                  {routeSummary.daylight_percentage}%
                </span>
                <span className="text-[10px] text-slate-500 block">
                  Direct sunlight along path
                </span>
              </div>

              <div className="p-2 bg-[#12162a] rounded border border-[#232b48]">
                <span className="text-[10px] text-slate-400 block uppercase">Subsampled Points</span>
                <span className="text-sm font-mono font-bold text-slate-200">
                  {routeSummary.samples.length}
                </span>
                <span className="text-[10px] text-slate-500 block">Along route distance</span>
              </div>
            </div>

            {/* Subsampled Points Preview */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-slate-300">
                Waypoint Environmental Breakdown
              </span>
              <div className="overflow-x-auto max-h-48">
                <table className="w-full text-left text-[10px] font-mono border border-[#1e253e]">
                  <thead className="bg-[#141933] text-slate-400 sticky top-0">
                    <tr>
                      <th className="p-1.5">Dist (m)</th>
                      <th className="p-1.5">Elev (m)</th>
                      <th className="p-1.5">Ref Pressure (Pa)</th>
                      <th className="p-1.5">SZA (°)</th>
                      <th className="p-1.5">Surface Beam (W/m²)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e253e] text-slate-300">
                    {routeSummary.samples.map((pt, i) => (
                      <tr key={i} className="hover:bg-[#141933]/40">
                        <td className="p-1.5">{pt.distance_m}</td>
                        <td className="p-1.5">{pt.elevation_m}</td>
                        <td className="p-1.5 text-orange-400 font-bold">{pt.reference_pressure_pa}</td>
                        <td className="p-1.5">{pt.solar_zenith_angle_deg}°</td>
                        <td className="p-1.5 text-amber-300 font-bold">{pt.surface_solar_flux_w_m2}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
