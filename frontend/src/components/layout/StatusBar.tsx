"use client";

import React, { useEffect, useState } from "react";
import { BackendHealthState } from "../../hooks/useBackendHealth";

interface StatusBarProps {
  healthState: BackendHealthState;
  cursorCoords: { lat: number; lon: number } | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  healthState,
  cursorCoords,
}) => {
  const [utcTime, setUtcTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().replace("T", " ").substring(0, 19) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <footer className="h-7 bg-[#090a10] border-t border-[#1c2030] flex items-center justify-between px-3 text-[11px] font-mono text-gray-400 select-none z-20">
      <div className="flex items-center space-x-4">
        <span className="flex items-center space-x-1.5">
          <span className="text-gray-500">CURSOR POS:</span>
          {cursorCoords ? (
            <span className="text-gray-200">
              {cursorCoords.lat >= 0
                ? `${cursorCoords.lat.toFixed(4)}°N`
                : `${Math.abs(cursorCoords.lat).toFixed(4)}°S`}, {cursorCoords.lon.toFixed(4)}°E
            </span>
          ) : (
            <span className="text-gray-500 italic">Pointer outside viewport</span>
          )}
        </span>

        <span className="hidden sm:inline-block text-gray-700">|</span>

        <span className="hidden sm:flex items-center space-x-1.5">
          <span className="text-gray-500">ELLIPSOID:</span>
          <span className="text-gray-300">Mars 2000 (R_eq=3396.19km, R_pol=3376.20km)</span>
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {healthState.status && (
          <span className="hidden md:flex items-center space-x-1.5">
            <span className="text-gray-500">UPTIME:</span>
            <span className="text-gray-300">{healthState.status.uptime_seconds.toFixed(0)}s</span>
          </span>
        )}

        <span className="hidden md:inline-block text-gray-700">|</span>

        <span className="text-gray-300 font-semibold">{utcTime}</span>
      </div>
    </footer>
  );
};

