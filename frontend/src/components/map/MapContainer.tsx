"use client";

import React, { useEffect, useRef, useState } from "react";
import { Map, NavigationControl, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapContainerProps {
  onCoordinateChange?: (coords: { lat: number; lon: number } | null) => void;
  selectedCrater?: string | null;
}

interface MarsFeature {
  name: string;
  lat: number;
  lon: number;
  type: string;
  description: string;
}

const FAMOUS_MARS_SITES: MarsFeature[] = [
  {
    name: "Jezero Crater (Perseverance)",
    lat: 18.38,
    lon: 77.58,
    type: "Landing Site / Ancient Lakebed",
    description: "Delta deposit rich in clay minerals, site of Perseverance astrobiology mission."
  },
  {
    name: "Gale Crater (Curiosity)",
    lat: -4.59,
    lon: 137.44,
    type: "Landing Site / Mount Sharp",
    description: "Layered sedimentary mound recording transitional aqueous environments."
  },
  {
    name: "Olympus Mons Caldera",
    lat: 18.65,
    lon: 226.2,
    type: "Shield Volcano",
    description: "Largest volcano in solar system; summit elevation ~21.3 km above Mars datum."
  },
  {
    name: "Valles Marineris (Melas Chasma)",
    lat: -9.8,
    lon: 283.6,
    type: "Tectonic Rift System",
    description: "Grand canyon of Mars spanning over 4,000 km, canyon depth reaches 7 km."
  }
];

export const MapContainer: React.FC<MapContainerProps> = ({
  onCoordinateChange,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const [activeSite, setActiveSite] = useState<MarsFeature | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Dark Mars coordinate canvas (pure vector background, avoiding EPSG:3857 tile distortion)
    const map = new Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        name: "Mars-Dark-Coordinate-Space",
        sources: {},
        layers: [
          {
            id: "background",
            type: "background",
            paint: {
              "background-color": "#0d0e17"
            }
          }
        ]
      },
      center: [0, 0],
      zoom: 1.5,
      minZoom: 1,
      maxZoom: 14,
      pitch: 0,
      bearing: 0,
    });

    mapRef.current = map;

    map.on("load", () => {
      // Add navigation controls
      map.addControl(new NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");

      // Add Mars feature markers
      FAMOUS_MARS_SITES.forEach((site) => {
        const el = document.createElement("div");
        el.className = "group relative cursor-pointer";
        el.innerHTML = `
          <div class="w-3.5 h-3.5 rounded-full bg-orange-600 border border-amber-300 shadow-md shadow-orange-950 flex items-center justify-center transform hover:scale-125 transition-transform">
            <div class="w-1.5 h-1.5 rounded-full bg-amber-100"></div>
          </div>
        `;
        el.addEventListener("click", () => {
          setActiveSite(site);
          map.flyTo({ center: [site.lon > 180 ? site.lon - 360 : site.lon, site.lat], zoom: 4 });
        });

        new Marker({ element: el })
          .setLngLat([site.lon > 180 ? site.lon - 360 : site.lon, site.lat])
          .addTo(map);
      });
    });

    map.on("mousemove", (e) => {
      if (onCoordinateChange) {
        const rawLon = e.lngLat.lng;
        const normalizedLon = rawLon < 0 ? rawLon + 360 : rawLon;
        onCoordinateChange({
          lat: e.lngLat.lat,
          lon: normalizedLon,
        });
      }
    });

    map.on("mouseout", () => {
      if (onCoordinateChange) {
        onCoordinateChange(null);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onCoordinateChange]);

  return (
    <div className="relative w-full h-full bg-[#0a0b12] overflow-hidden">
      {/* MapLibre DOM viewport */}
      <div ref={mapContainerRef} className="w-full h-full cursor-crosshair" />

      {/* Grid overlay lines to evoke coordinate space */}
      <div className="absolute inset-0 pointer-events-none border border-[#1d2235]/40 grid grid-cols-6 grid-rows-4 opacity-15">
        {Array.from({ length: 24 }).map((_, i) => (
          <div key={i} className="border border-orange-500/10" />
        ))}
      </div>

      {/* Projection Disclaimer & Scientific Integrity Warning */}
      <div className="absolute top-3 left-3 max-w-md bg-[#0d0f1c]/90 border border-amber-500/40 rounded-lg p-3 backdrop-blur-md shadow-2xl text-xs font-mono pointer-events-auto">
        <div className="flex items-center space-x-2 text-amber-400 font-bold mb-1">
          <span>⚠️</span>
          <span className="uppercase tracking-wider">Planetary CRS Notice</span>
        </div>
        <p className="text-gray-300 text-[11px] leading-relaxed">
          NASA Mars Trek MOLA WMTS uses Mars-specific coordinate system <span className="text-amber-300 font-bold">EPSG:104905</span>.
          Standard Web Mercator (<span className="text-red-400 font-bold">EPSG:3857</span>) tile streaming is strictly paused until server-side or client Proj4 projection transforms are validated.
        </p>
        <div className="mt-2 pt-1.5 border-t border-[#22283e] flex items-center justify-between text-[10px] text-gray-400">
          <span>Target Datum: Mars 2000 Sphere</span>
          <span className="text-emerald-400 font-medium">Coordinate Mesh Active</span>
        </div>
      </div>

      {/* Active Crater / Site card */}
      {activeSite && (
        <div className="absolute bottom-3 left-3 max-w-sm bg-[#111322]/95 border border-[#2b3350] rounded-lg p-3 backdrop-blur-md shadow-2xl text-xs font-mono">
          <div className="flex items-center justify-between border-b border-[#252c44] pb-1.5 mb-2">
            <span className="font-bold text-orange-400">{activeSite.name}</span>
            <button
              onClick={() => setActiveSite(null)}
              className="text-gray-400 hover:text-white px-1 text-xs"
            >
              ✕
            </button>
          </div>
          <p className="text-[11px] text-gray-300 mb-2">{activeSite.description}</p>
          <div className="text-[10px] grid grid-cols-2 gap-2 text-gray-400 bg-[#0a0c16] p-2 rounded border border-[#1e2338]">
            <div>Lat: <span className="text-gray-200">{activeSite.lat.toFixed(2)}°N</span></div>
            <div>Lon: <span className="text-gray-200">{activeSite.lon.toFixed(2)}°E</span></div>
            <div className="col-span-2">Type: <span className="text-amber-400">{activeSite.type}</span></div>
          </div>
        </div>
      )}

      {/* Center crosshair */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-40">
        <div className="w-8 h-8 border border-orange-500/50 rounded-full flex items-center justify-center">
          <div className="w-1 h-1 bg-orange-400 rounded-full" />
        </div>
      </div>
    </div>
  );
};

export default MapContainer;
