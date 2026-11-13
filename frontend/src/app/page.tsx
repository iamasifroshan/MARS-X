"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Header } from "../components/layout/Header";
import { Sidebar } from "../components/layout/Sidebar";
import { StatusBar } from "../components/layout/StatusBar";
import { LayerSelector } from "../components/map/LayerSelector";
import { CoordinateInspector } from "../components/panels/CoordinateInspector";
import { DatasetCatalogue } from "../components/panels/DatasetCatalogue";
import { TerrainAnalysis } from "../components/panels/TerrainAnalysis";
import { RoutePlanning } from "../components/panels/RoutePlanning";
import { MissionInfo } from "../components/panels/MissionInfo";
import { ScienceProvenance } from "../components/panels/ScienceProvenance";
import { useBackendHealth } from "../hooks/useBackendHealth";
import { MapLayer } from "../lib/types";

const MapContainer = dynamic(() => import("../components/map/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0a0b12] flex items-center justify-center font-mono text-xs text-gray-500">
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 rounded-full bg-orange-500 animate-ping" />
        <span>Initializing Planetary Coordinate Canvas...</span>
      </div>
    </div>
  ),
});

const INITIAL_LAYERS: MapLayer[] = [
  {
    id: "mola-shaded-relief",
    name: "MOLA Global Shaded Relief",
    mission: "Mars Global Surveyor",
    type: "shaded_relief",
    crs: "EPSG:104905",
    enabled: false,
    isAvailable: false,
    statusNote: "WMTS tile connection pending EPSG:104905 client reprojection",
  },
  {
    id: "mola-elevation-dtm",
    name: "MOLA MEGDR Topography (128 px/deg)",
    mission: "Mars Global Surveyor",
    type: "elevation_dtm",
    crs: "IAU:49900",
    enabled: false,
    isAvailable: false,
    statusNote: "Numerical raster pending backend GDAL/Rasterio pipeline",
  },
  {
    id: "hrsc-dtm-regional",
    name: "HRSC Regional Stereo DTM (50m)",
    mission: "Mars Express (ESA)",
    type: "elevation_dtm",
    crs: "IAU:49900",
    enabled: false,
    isAvailable: false,
    statusNote: "Regional stereophotogrammetry awaiting download & indexing",
  },
  {
    id: "hirise-rdr-imagery",
    name: "HiRISE RDR High-Resolution Swaths",
    mission: "Mars Reconnaissance Orbiter",
    type: "orbital_imagery",
    crs: "Equirectangular Mars",
    enabled: false,
    isAvailable: false,
    statusNote: "0.25m/px targeting mosaic pending PDS pipeline ingestion",
  },
];

export default function ExplorationDashboard() {
  const healthState = useBackendHealth(15000);
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [layers, setLayers] = useState<MapLayer[]>(INITIAL_LAYERS);

  const [openPanels, setOpenPanels] = useState({
    layers: true,
    datasets: true,
    coords: true,
    route: false,
    terrain: false,
    mission: false,
  });

  const togglePanel = (panel: keyof typeof openPanels) => {
    setOpenPanels((prev) => ({ ...prev, [panel]: !prev[panel] }));
  };

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
          openPanels={openPanels}
          togglePanel={togglePanel}
        />

        {/* Center / Primary Display Area */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activeTab === "catalogue" ? (
            <div className="flex-1 p-4 bg-[#0a0c16] overflow-y-auto">
              <DatasetCatalogue />
            </div>
          ) : activeTab === "provenance" ? (
            <div className="flex-1 p-4 bg-[#0a0c16] overflow-y-auto">
              <ScienceProvenance />
            </div>
          ) : activeTab === "terrain" ? (
            <div className="flex-1 p-4 bg-[#0a0c16] overflow-y-auto">
              <TerrainAnalysis />
            </div>
          ) : activeTab === "mission" ? (
            <div className="flex-1 p-4 bg-[#0a0c16] overflow-y-auto">
              <MissionInfo />
            </div>
          ) : (
            /* Main Exploration Console (Map + Side Panels + Bottom Deck) */
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="flex-1 flex overflow-hidden relative">
                {/* Interactive Mars Map */}
                <div className="flex-1 relative">
                  <MapContainer onCoordinateChange={setCursorCoords} />
                </div>

                {/* Right Floating / Docked Panels */}
                <div className="w-80 md:w-96 border-l border-[#1d2238] bg-[#0c0e1a]/90 backdrop-blur-md flex flex-col p-3 space-y-3 overflow-y-auto z-10 shadow-2xl">
                  {openPanels.coords && (
                    <CoordinateInspector coords={cursorCoords} />
                  )}

                  {openPanels.layers && (
                    <LayerSelector
                      layers={layers}
                      onToggleLayer={handleToggleLayer}
                    />
                  )}

                  {openPanels.datasets && (
                    <div className="flex-1 min-h-[300px]">
                      <DatasetCatalogue />
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom Mission Planning & Terrain Operations Deck */}
              <div className="h-48 border-t border-[#1c2136] bg-[#0b0c16] p-3 grid grid-cols-1 md:grid-cols-3 gap-3 overflow-y-auto select-none z-10">
                <TerrainAnalysis />
                <RoutePlanning />
                <MissionInfo />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Persistent Bottom Bar */}
      <StatusBar healthState={healthState} cursorCoords={cursorCoords} />
    </div>
  );
}
