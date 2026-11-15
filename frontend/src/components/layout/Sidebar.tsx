"use client";

import React from "react";

interface SidebarProps {
  activeSection: string;
  setActiveSection: (sec: string) => void;
  isDrawerOpen?: boolean;
  onToggleDrawer?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSection,
  setActiveSection,
  isDrawerOpen = true,
  onToggleDrawer,
}) => {
  const navItems = [
    { id: "dashboard", label: "Console", icon: "🗺️", tooltip: "Exploration Console & Map" },
    { id: "discovery", label: "Discovery", icon: "🔭", tooltip: "Evidence-Based Science Discovery System" },
    { id: "catalogue", label: "Catalogue", icon: "📚", tooltip: "NASA PDS Dataset Catalogue" },
    { id: "terrain", label: "Terrain", icon: "⛰️", tooltip: "Multi-Resolution Terrain Intelligence" },
    { id: "profile", label: "Profile", icon: "📈", tooltip: "Mars Great-Circle Elevation Profile" },
    { id: "route", label: "Routing", icon: "🥾", tooltip: "Marswalk Pathfinding (A* & Dijkstra)" },
    { id: "environmental", label: "Environment", icon: "🛰️", tooltip: "Atmospheric Pressure, Solar & MCD Climatology" },
    { id: "mission", label: "Mission", icon: "🧑‍🚀", tooltip: "EVA Traverse Constraints & Logistics" },
    { id: "provenance", label: "Science", icon: "🔬", tooltip: "Planetary CRS & Geodetic Provenance" },
  ];

  return (
    <aside className="w-14 bg-[#0a0b12] border-r border-[#1e2335] flex flex-col items-center py-3 space-y-2.5 z-10 select-none">
      <div className="flex flex-col items-center space-y-2 flex-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveSection(item.id)}
            title={item.tooltip}
            className={`w-10 h-10 rounded-lg flex flex-col items-center justify-center text-xs transition-all relative ${
              activeSection === item.id
                ? "bg-[#1f253d] text-orange-400 border border-orange-500/60 shadow-lg shadow-orange-950/40"
                : "text-gray-400 hover:text-gray-200 hover:bg-[#141726] border border-transparent"
            }`}
          >
            <span className="text-base">{item.icon}</span>
            <span className="text-[8px] font-mono mt-0.5 tracking-tighter scale-90">
              {item.label}
            </span>
            {activeSection === item.id && (
              <span className="absolute right-1 top-1 w-1.5 h-1.5 rounded-full bg-orange-500 ring-2 ring-orange-950" />
            )}
          </button>
        ))}
      </div>

      {activeSection === "dashboard" && onToggleDrawer && (
        <div className="pt-2 border-t border-[#1e2335] w-full flex flex-col items-center">
          <button
            onClick={onToggleDrawer}
            title={isDrawerOpen ? "Collapse Side Drawer" : "Expand Side Drawer"}
            className={`w-9 h-9 rounded flex items-center justify-center text-xs transition-colors ${
              isDrawerOpen
                ? "bg-orange-500/20 text-orange-400 border border-orange-500/30"
                : "text-gray-400 hover:text-white hover:bg-[#141726]"
            }`}
          >
            <span>{isDrawerOpen ? "⮞" : "⮜"}</span>
          </button>
        </div>
      )}
    </aside>
  );
};
