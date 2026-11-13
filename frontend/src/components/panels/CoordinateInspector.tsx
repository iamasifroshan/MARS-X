"use client";

import React from "react";

interface CoordinateInspectorProps {
  coords: { lat: number; lon: number } | null;
}

export const CoordinateInspector: React.FC<CoordinateInspectorProps> = ({ coords }) => {
  return (
    <div className="bg-[#111320]/90 border border-[#23283f] rounded-lg p-3 text-xs font-mono backdrop-blur-md shadow-xl">
      <div className="flex items-center justify-between border-b border-[#23283f] pb-2 mb-2.5">
        <div className="flex items-center space-x-2">
          <span>🎯</span>
          <span className="font-semibold text-gray-200 uppercase tracking-wider">
            Planetary Coordinate Inspector
          </span>
        </div>
        <span className="text-[10px] text-orange-400 font-bold">MARS 2000</span>
      </div>

      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2 bg-[#0a0c16] p-2.5 rounded border border-[#1b2034]">
          <div>
            <span className="text-[10px] text-gray-500 block uppercase font-bold">Planetocentric Lat</span>
            <span className="text-sm font-semibold text-gray-100">
              {coords ? `${coords.lat.toFixed(4)}°` : "--.----°"}
            </span>
            <span className="text-[9px] text-gray-500 block">
              {coords ? (coords.lat >= 0 ? "North Hemisphere" : "South Hemisphere") : "Awaiting input"}
            </span>
          </div>

          <div>
            <span className="text-[10px] text-gray-500 block uppercase font-bold">Positive East Lon</span>
            <span className="text-sm font-semibold text-gray-100">
              {coords ? `${coords.lon.toFixed(4)}°` : "---.----°"}
            </span>
            <span className="text-[9px] text-gray-500 block">
              {coords ? `[0° to 360° IAU Standard]` : "Awaiting input"}
            </span>
          </div>
        </div>

        <div className="bg-[#0a0c16] p-2.5 rounded border border-[#1b2034] text-[10px] space-y-1">
          <div className="flex justify-between text-gray-400">
            <span>Reference Surface:</span>
            <span className="text-gray-200">MOLA Areoid Datum (0m ref)</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>Local DTM Elevation:</span>
            <span className="text-amber-400 italic">Pending DTM raster query</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>Projection Target:</span>
            <span className="text-gray-200">Equirectangular Mars (EPSG:104905)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
