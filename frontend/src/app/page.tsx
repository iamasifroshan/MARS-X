"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Header } from "../components/layout/Header";
import { Sidebar } from "../components/layout/Sidebar";
import { StatusBar } from "../components/layout/StatusBar";
import { LayerSelector } from "../components/map/LayerSelector";
import { CoordinateInspector } from "../components/panels/CoordinateInspector";
import { ElevationProfilePanel } from "../components/panels/ElevationProfilePanel";
import { DatasetCatalogue } from "../components/panels/DatasetCatalogue";
import { TerrainAnalysis } from "../components/panels/TerrainAnalysis";
import { RoutePlanning } from "../components/panels/RoutePlanning";
import { MissionInfo } from "../components/panels/MissionInfo";
import { ScienceProvenance } from "../components/panels/ScienceProvenance";
import { ScienceExplorerPanel } from "../components/panels/ScienceExplorerPanel";
import { EnvironmentalIntelligenceView } from "../components/panels/EnvironmentalIntelligenceView";
import { useBackendHealth } from "../hooks/useBackendHealth";
import { MapLayer, ScienceDiscovery } from "../lib/types";
import { fetchDiscoveries } from "../lib/api";

const MapContainer = dynamic(() => import("../components/map/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#06070d] flex items-center justify-center font-mono text-xs text-gray-500">
      <div className="flex items-center space-x-2">
        <div className="w-2.5 h-2.5 rounded-full bg-orange-500 animate-ping" />
        <span>Initializing Authentic Planetary Raster Canvas...</span>
      </div>
    </div>
  ),
});

const INITIAL_LAYERS: MapLayer[] = [
  {
    id: "mola-elevation-global",
    name: "MOLA Global Topography (4 px/deg)",
    mission: "Mars Global Surveyor (MGS)",
    type: "elevation_dtm",
    crs: "IAU:49900",
    enabled: true,
    isAvailable: true,
    statusNote: "Authentic global numerical elevation COG with Turbo hypsometry",
  },
  {
    id: "mola-128-tiles",
    name: "MOLA High-Res Regional Tiles (128 px/deg)",
    mission: "Mars Global Surveyor (MGS)",
    type: "elevation_dtm",
    crs: "IAU:49900",
    enabled: true,
    isAvailable: true,
    statusNote: "Authentic 463 m/px numerical tiles (00n000, 44n000, 00n090)",
  },
  {
    id: "ctx-dtm-p21-009323",
    name: "USGS CTX DTM: Tyrrhena Terra (20m/px)",
    mission: "Mars Reconnaissance Orbiter (MRO)",
    type: "elevation_dtm",
    crs: "IAU:49910",
    enabled: true,
    isAvailable: true,
    statusNote: "Authentic 20m numerical stereo elevation model",
  },
  {
    id: "ctx-controlled-t01",
    name: "USGS CTX DTM: Apollinaris Sulci (20m/px)",
    mission: "Mars Reconnaissance Orbiter (MRO)",
    type: "elevation_dtm",
    crs: "IAU:49910",
    enabled: true,
    isAvailable: true,
    statusNote: "Authentic 20m controlled stereo DTM (MOLA geoid adjusted)",
  },
  {
    id: "hirise-controlled-esp",
    name: "USGS HiRISE DTM: Holden Crater (1.0m/px)",
    mission: "Mars Reconnaissance Orbiter (MRO)",
    type: "elevation_dtm",
    crs: "IAU:49910",
    enabled: true,
    isAvailable: true,
    statusNote: "Authentic 1.01m ultra-high-resolution controlled stereo DTM",
  },
  {
    id: "tes-thermal-inertia",
    name: "MGS TES Global Thermal Inertia (20 ppd, Putzig 2007)",
    mission: "Mars Global Surveyor (MGS)",
    type: "multispectral",
    crs: "IAU:49900",
    enabled: false,
    isAvailable: true,
    statusNote: "Calibrated thermal-inertia estimate (50-2500 tiu). Qualitative thermophysical proxy, NOT temperature.",
  },
  {
    id: "themis-ir-regional",
    name: "THEMIS Regional IR Mosaic (256 ppd, ~231.5 m/px — Sinus Meridiani)",
    mission: "2001 Mars Odyssey",
    type: "orbital_imagery",
    crs: "IAU:49900",
    enabled: false,
    isAvailable: true,
    statusNote: "256 ppd (~231.5 m/px) Band 9 visual display DN (lat -30°..0°, lon 0°..30°E). Qualitative only (resampled from 100m camera).",
  },
  {
    id: "sim3292-geology",
    name: "USGS Mars Global Geologic Map (SIM 3292)",
    mission: "USGS Astrogeology (Tanaka et al. 2014)",
    type: "geology",
    crs: "GCS_Mars_2000_Sphere",
    enabled: false,
    isAvailable: true,
    statusNote: "Authentic 1:20M global chronostratigraphic units, contacts, and structures",
  },
  {
    id: "mars-graticule-grid",
    name: "Mars Coordinate Graticule (30° mesh)",
    mission: "MARS-X Cartography",
    type: "geology",
    crs: "EPSG:104905",
    enabled: true,
    isAvailable: true,
    statusNote: "Mars 2000 Sphere coordinate reference graticule",
  },
  {
    id: "dataset-footprints",
    name: "Coverage Footprints & Boundaries",
    mission: "Multi-Mission Envelopes",
    type: "geology",
    crs: "EPSG:104905",
    enabled: true,
    isAvailable: true,
    statusNote: "Polygons marking acquired CTX & MOLA 128 coverage boundaries",
  },
  {
    id: "hirise-rdr-imagery",
    name: "HiRISE Jezero Crater DTM (1.0m/px)",
    mission: "Mars Reconnaissance Orbiter (MRO)",
    type: "elevation_dtm",
    crs: "IAU:49900",
    enabled: false,
    isAvailable: false,
    statusNote: "Discovered PDS product metadata (Awaiting local acquisition)",
  },
];

export default function ExplorationDashboard() {
  const healthState = useBackendHealth(15000);
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [inspectedCoords, setInspectedCoords] = useState<{ lat: number; lon: number } | null>({
    lat: -4.600,
    lon: 66.317,
  });
  const [layers, setLayers] = useState<MapLayer[]>(INITIAL_LAYERS);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);
  const [drawerSubTab, setDrawerSubTab] = useState<"layers" | "coords" | "profile" | "presets" | "discovery">("layers");
  const [activeDiscoveryId, setActiveDiscoveryId] = useState<string | null>(null);
  const [quickDiscoveries, setQuickDiscoveries] = useState<ScienceDiscovery[]>([]);

  // Load candidate discoveries for quick reconnaissance
  React.useEffect(() => {
    fetchDiscoveries()
      .then((data) => setQuickDiscoveries(data))
      .catch((err) => console.error("Failed to load discoveries:", err));
  }, []);

  // Read URL search parameters on initial mount for deep-linking
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      const drawer = params.get("drawer");
      const lat = params.get("lat");
      const lon = params.get("lon");
      if (tab) setActiveTab(tab);
      if (drawer) {
        setIsDrawerOpen(true);
        setDrawerSubTab(drawer as any);
      }
      if (lat && lon) {
        setInspectedCoords({ lat: parseFloat(lat), lon: parseFloat(lon) });
      }
    }
  }, []);

  const handleToggleLayer = (layerId: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, enabled: !l.enabled } : l))
    );
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#07080f] text-gray-200 overflow-hidden font-sans">
      {/* Top Navigation & Status */}
      <Header
        healthState={healthState}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Icon Sidebar */}
        <Sidebar
          activeSection={activeTab}
          setActiveSection={setActiveTab}
          isDrawerOpen={isDrawerOpen}
          onToggleDrawer={() => setIsDrawerOpen(!isDrawerOpen)}
        />

        {/* Center / Primary Display Area */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activeTab === "discovery" ? (
            <div className="flex-1 overflow-hidden">
              <ScienceExplorerPanel
                initialDiscoveryId={activeDiscoveryId}
                onFlyToLocation={(coords) => {
                  setInspectedCoords({ lat: coords.lat, lon: coords.lon });
                  setActiveTab("dashboard");
                }}
                onInspectCoordinates={(coords) => {
                  setInspectedCoords(coords);
                  setActiveTab("dashboard");
                  setIsDrawerOpen(true);
                  setDrawerSubTab("coords");
                }}
              />
            </div>
          ) : activeTab === "catalogue" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto h-full">
                <DatasetCatalogue />
              </div>
            </div>
          ) : activeTab === "provenance" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <ScienceProvenance />
              </div>
            </div>
          ) : activeTab === "terrain" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <TerrainAnalysis currentCoordinates={cursorCoords} />
              </div>
            </div>
          ) : activeTab === "profile" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <div className="bg-[#101322]/90 border border-[#232840] rounded-lg p-5 backdrop-blur-md shadow-2xl">
                  <ElevationProfilePanel />
                </div>
              </div>
            </div>
          ) : activeTab === "route" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <div className="bg-[#101322]/90 border border-[#232840] rounded-lg p-5 backdrop-blur-md shadow-2xl">
                  <div className="flex items-center justify-between border-b border-[#232840] pb-3 mb-4">
                    <div className="flex items-center space-x-2">
                      <span className="text-xl">🥾</span>
                      <div>
                        <h2 className="font-bold text-sm text-gray-100 uppercase tracking-wider font-mono">
                          Marswalk Route Intelligence &amp; Autonomous Pathfinding
                        </h2>
                        <p className="text-[11px] text-gray-400 font-mono">
                          Terrain-constrained A* and Dijkstra path optimization on authentic MOLA 128 ppd elevation data.
                        </p>
                      </div>
                    </div>
                  </div>
                  <RoutePlanning />
                </div>
              </div>
            </div>
          ) : activeTab === "environmental" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <EnvironmentalIntelligenceView />
              </div>
            </div>
          ) : activeTab === "mission" ? (
            <div className="flex-1 p-6 bg-[#0a0c16] overflow-y-auto">
              <div className="max-w-7xl mx-auto">
                <MissionInfo />
              </div>
            </div>
          ) : (
            /* Main Exploration Console (Full Map with Docked/Collapsible Side Drawer) */
            <div className="flex-1 flex overflow-hidden relative">
              {/* Interactive Mars Map */}
              <div className="flex-1 relative h-full">
                <MapContainer
                  onCoordinateChange={setCursorCoords}
                  onCoordinateInspect={(coords) => {
                    setInspectedCoords(coords);
                    setIsDrawerOpen(true);
                    setDrawerSubTab("coords");
                  }}
                  inspectedCoord={inspectedCoords}
                  layers={layers}
                />
              </div>

              {/* Collapsible Right Docked Drawer */}
              {isDrawerOpen ? (
                <div className="w-84 md:w-96 border-l border-[#1d2238] bg-[#0c0e1a]/95 backdrop-blur-md flex flex-col z-10 shadow-2xl overflow-hidden transition-all duration-200">
                  {/* Drawer Tab Header */}
                  <div className="flex items-center justify-between border-b border-[#1f253d] px-3 py-2 bg-[#090b14] text-xs font-mono">
                    <div className="flex space-x-1">
                      <button
                        onClick={() => setDrawerSubTab("layers")}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          drawerSubTab === "layers"
                            ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Layers ({layers.filter((l) => l.enabled).length})
                      </button>
                      <button
                        onClick={() => setDrawerSubTab("coords")}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          drawerSubTab === "coords"
                            ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Inspector
                      </button>
                      <button
                        onClick={() => setDrawerSubTab("profile")}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          drawerSubTab === "profile"
                            ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Profile
                      </button>
                      <button
                        onClick={() => setDrawerSubTab("discovery")}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          drawerSubTab === "discovery"
                            ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Discovery
                      </button>
                      <button
                        onClick={() => setDrawerSubTab("presets")}
                        className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                          drawerSubTab === "presets"
                            ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Quick Route
                      </button>
                    </div>

                    <button
                      onClick={() => setIsDrawerOpen(false)}
                      title="Collapse Drawer"
                      className="text-gray-400 hover:text-white px-1.5 py-0.5 rounded hover:bg-[#181d30]"
                    >
                      ✕
                    </button>
                  </div>

                  {/* Drawer Content */}
                  <div className="flex-1 p-3 overflow-y-auto space-y-3 font-mono text-xs">
                    {drawerSubTab === "layers" && (
                      <LayerSelector
                        layers={layers}
                        onToggleLayer={handleToggleLayer}
                      />
                    )}

                    {drawerSubTab === "coords" && (
                      <CoordinateInspector
                        coords={inspectedCoords || cursorCoords}
                        onInspectCoord={setInspectedCoords}
                      />
                    )}

                    {drawerSubTab === "profile" && (
                      <ElevationProfilePanel />
                    )}

                    {drawerSubTab === "discovery" && (
                      <div className="space-y-3 font-mono text-xs">
                        <div className="p-3 bg-[#111322] border border-[#23293f] rounded-lg">
                          <div className="font-bold text-orange-400 mb-1 flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <span>🔭</span>
                              <span>Candidate Discoveries</span>
                            </span>
                            <button
                              onClick={() => setActiveTab("discovery")}
                              className="text-[10px] text-orange-400 hover:underline font-normal"
                            >
                              Full Suite ↗
                            </button>
                          </div>
                          <p className="text-[11px] text-gray-300 leading-relaxed">
                            Evidence-backed science discoveries across terrain, geology, and thermophysics.
                          </p>
                        </div>

                        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                          {quickDiscoveries.map((disc) => (
                            <div
                              key={disc.id}
                              onClick={() => {
                                setInspectedCoords({ lat: disc.latitude, lon: disc.longitude });
                                setActiveDiscoveryId(disc.id);
                              }}
                              className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                                inspectedCoords?.lat === disc.latitude && inspectedCoords?.lon === disc.longitude
                                  ? "bg-[#181d36] border-orange-500 shadow-md"
                                  : "bg-[#0f1224] border-[#222942] hover:border-gray-500"
                              }`}
                            >
                              <div className="flex justify-between items-start gap-1">
                                <span className="font-bold text-gray-200 text-[11px] leading-tight">
                                  {disc.name}
                                </span>
                                <span className="text-[9px] px-1 py-0.2 rounded bg-[#181d33] border border-[#273050] text-gray-400 shrink-0">
                                  {disc.category.split("_")[0]}
                                </span>
                              </div>
                              <p className="text-[10px] text-gray-400 mt-1 line-clamp-2">
                                {disc.scientific_significance}
                              </p>
                              <div className="flex justify-between items-center mt-2 pt-1 border-t border-[#1b2138] text-[9px]">
                                <span className="text-amber-400 font-mono">
                                  {disc.latitude.toFixed(2)}°, {disc.longitude.toFixed(2)}°E
                                </span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveDiscoveryId(disc.id);
                                    setActiveTab("discovery");
                                  }}
                                  className="text-orange-400 hover:text-orange-300 font-semibold"
                                >
                                  View Profile ➔
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {drawerSubTab === "presets" && (
                      <div className="space-y-3">
                        <div className="p-3 bg-[#111322] border border-[#23293f] rounded-lg">
                          <div className="font-bold text-orange-400 mb-1 flex items-center gap-1.5">
                            <span>🥾</span>
                            <span>Marswalk Quick Traverse</span>
                          </div>
                          <p className="text-[11px] text-gray-300 mb-3 leading-relaxed">
                            Select a target to run terrain-constrained routing in MOLA tile megt00n000hb.
                          </p>
                          <button
                            onClick={() => setActiveTab("route")}
                            className="w-full py-2 bg-gradient-to-r from-orange-600 to-red-600 text-white font-bold rounded shadow-lg hover:from-orange-500 hover:to-red-500 transition-all text-xs tracking-wider uppercase"
                          >
                            Open Full Routing Suite ⮞
                          </button>
                        </div>
                        <CoordinateInspector
                          coords={inspectedCoords || cursorCoords}
                          onInspectCoord={setInspectedCoords}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Collapsed Drawer Open Button */
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  title="Expand Layer & Coordinate Drawer"
                  className="absolute right-3 top-3 z-10 bg-[#0c0e1a]/90 border border-orange-500/40 text-orange-400 px-3 py-1.5 rounded-lg text-xs font-mono shadow-2xl backdrop-blur-md hover:bg-orange-600 hover:text-white transition-all flex items-center gap-1.5"
                >
                  <span>🗺️</span>
                  <span>Open Layers Panel</span>
                  <span>⮜</span>
                </button>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Persistent Bottom Bar */}
      <StatusBar healthState={healthState} cursorCoords={cursorCoords} />
    </div>
  );
}
