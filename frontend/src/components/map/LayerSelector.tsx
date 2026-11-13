"use client";

import React from "react";
import { MapLayer } from "../../lib/types";

interface LayerSelectorProps {
  layers: MapLayer[];
  onToggleLayer: (id: string) => void;
}

export const LayerSelector: React.FC<LayerSelectorProps> = ({
  layers,
  onToggleLayer,
}) => {
  return (
    <div className="bg-[#10121d]/90 border border-[#23293f] rounded-lg p-3.5 text-xs font-mono backdrop-blur-md shadow-xl">
      <div className="flex items-center justify-between border-b border-[#23293f] pb-2 mb-3">
        <div className="flex items-center space-x-2">
          <span>🗺️</span>
          <span className="font-semibold text-gray-200 uppercase tracking-wider">
            Planetary Layers
          </span>
        </div>
        <span className="text-[10px] text-gray-400">CRS: EPSG:104905</span>
      </div>

      <div className="space-y-2.5">
        {layers.map((layer) => (
          <div
            key={layer.id}
            className={`p-2.5 rounded border transition-all ${
              layer.enabled
                ? "bg-[#181d30] border-orange-500/50"
                : "bg-[#0c0d15] border-[#1d2235] opacity-75"
            }`}
          >
            <div className="flex items-start justify-between">
              <label className="flex items-start space-x-2 cursor-pointer flex-1 mr-2">
                <input
                  type="checkbox"
                  checked={layer.enabled}
                  disabled={!layer.isAvailable}
                  onChange={() => onToggleLayer(layer.id)}
                  className="mt-0.5 rounded border-[#2e3752] text-orange-600 focus:ring-0 disabled:opacity-40 cursor-pointer"
                />
                <div>
                  <span className="font-semibold text-gray-200 block text-[11px]">
                    {layer.name}
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    {layer.mission} • {layer.crs}
                  </span>
                </div>
              </label>

              <span
                className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold whitespace-nowrap ${
                  layer.type === "elevation_dtm"
                    ? "bg-purple-950/60 text-purple-300 border border-purple-800/40"
                    : layer.type === "shaded_relief"
                    ? "bg-blue-950/60 text-blue-300 border border-blue-800/40"
                    : "bg-amber-950/60 text-amber-300 border border-amber-800/40"
                }`}
              >
                {layer.type === "elevation_dtm" ? "NUMERICAL DTM" : layer.type.replace("_", " ")}
              </span>
            </div>

            <div className="mt-2 text-[10px] text-amber-400/90 flex items-center space-x-1 border-t border-[#1e2336] pt-1.5">
              <span>⚠️</span>
              <span>{layer.statusNote}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 p-2 bg-black/40 rounded border border-[#1f253a] text-[10px] text-gray-400">
        <span className="font-bold text-gray-300 block mb-0.5">Architecture Rule:</span>
        Rendered shaded-relief imagery is strictly decoupled from numerical elevation data.
        Numerical DTM rasters are required for slope and traversability cost calculations.
      </div>
    </div>
  );
};

