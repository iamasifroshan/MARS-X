"use client";

import React from "react";

interface SidebarProps {
  activeSection: string;
  setActiveSection: (sec: string) => void;
  openPanels: {
    layers: boolean;
    datasets: boolean;
    coords: boolean;
    route: boolean;
    terrain: boolean;
    mission: boolean;
  };
  togglePanel: (panel: "layers" | "datasets" | "coords" | "route" | "terrain" | "mission") => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  openPanels,
  togglePanel,
}) => {
  const panelButtons = [
    { id: "layers" as const, label: "Map Layers", icon: "🗺️", active: openPanels.layers },
    { id: "datasets" as const, label: "Catalogue", icon: "📚", active: openPanels.datasets },
    { id: "coords" as const, label: "Coordinates", icon: "🎯", active: openPanels.coords },
    { id: "terrain" as const, label: "Terrain DTM", icon: "⛰️", active: openPanels.terrain },
    { id: "route" as const, label: "Marswalk Path", icon: "🥾", active: openPanels.route },
    { id: "mission" as const, label: "EVA Planning", icon: "🧑‍🚀", active: openPanels.mission },
  ];

  return (
    <aside className="w-14 bg-[#0a0b12] border-r border-[#1e2335] flex flex-col items-center py-3 space-y-3 z-10 select-none">
      {panelButtons.map((btn) => (
        <button
          key={btn.id}
          onClick={() => togglePanel(btn.id)}
          title={btn.label}
          className={`w-10 h-10 rounded-lg flex flex-col items-center justify-center text-xs transition-all relative ${
            btn.active
              ? "bg-[#1f253d] text-orange-400 border border-orange-500/50 shadow-md shadow-orange-950/30"
              : "text-gray-400 hover:text-gray-200 hover:bg-[#141726] border border-transparent"
          }`}
        >
          <span className="text-base">{btn.icon}</span>
          <span className="text-[8px] font-mono mt-0.5 tracking-tighter scale-90">
            {btn.label.split(" ")[0]}
          </span>
          {btn.active && (
            <span className="absolute right-1 top-1 w-1.5 h-1.5 rounded-full bg-orange-500" />
          )}
        </button>
      ))}
    </aside>
  );
};
