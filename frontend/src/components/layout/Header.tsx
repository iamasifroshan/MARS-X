"use client";

import React from "react";
import { BackendHealthState } from "../../hooks/useBackendHealth";

interface HeaderProps {
  healthState: BackendHealthState;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  healthState,
  activeTab,
  setActiveTab,
}) => {
  const tabs = [
    { id: "dashboard", label: "EXPLORATION CONSOLE" },
    { id: "discovery", label: "SCIENCE DISCOVERY" },
    { id: "catalogue", label: "DATASET CATALOGUE" },
    { id: "terrain", label: "TERRAIN INTELLIGENCE" },
    { id: "profile", label: "ELEVATION PROFILE" },
    { id: "route", label: "MARSWALK ROUTING" },
    { id: "environmental", label: "ENVIRONMENT & CLIMATOLOGY" },
    { id: "mission", label: "MISSION & EVA" },
    { id: "provenance", label: "SCIENCE & CRS" },
  ];

  return (
    <header className="h-14 bg-[#0c0d16] border-b border-[#202538] flex items-center justify-between px-4 z-20 select-none">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-orange-600 to-red-500 flex items-center justify-center font-black text-white text-xs tracking-tighter shadow-lg shadow-orange-950/50">
            MX
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold tracking-widest text-sm text-gray-100 font-mono">
                MARS-X
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-orange-500/20 text-orange-400 font-mono border border-orange-500/30">
                NASA SPACE APPS 2026
              </span>
            </div>
            <p className="text-[10px] text-gray-400 font-mono -mt-0.5">
              Planetary Terrain Intelligence & Marswalk Navigation
            </p>
          </div>
        </div>

        <nav className="hidden md:flex space-x-1 font-mono text-xs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded transition-colors ${
                activeTab === tab.id
                  ? "bg-[#1c2237] text-orange-400 border border-orange-500/40 font-semibold"
                  : "text-gray-400 hover:text-gray-200 hover:bg-[#141724]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex items-center space-x-4 font-mono text-xs">
        <div className="hidden sm:flex items-center space-x-2 bg-[#121422] border border-[#23273e] px-2.5 py-1 rounded">
          <span className="text-[10px] text-gray-400">PLANETARY CRS:</span>
          <span className="text-[10px] text-amber-300 font-bold">EPSG:104905 / IAU:49900</span>
        </div>

        <div className="flex items-center space-x-2 bg-[#121422] border border-[#23273e] px-2.5 py-1 rounded">
          <div
            className={`w-2 h-2 rounded-full ${
              healthState.isConnected
                ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-pulse"
            }`}
          />
          <span className="text-[11px] text-gray-300">
            {healthState.isConnected ? "API ONLINE" : "API OFFLINE"}
          </span>
        </div>
      </div>
    </header>
  );
};

