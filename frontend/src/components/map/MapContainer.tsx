"use client";

import React, { useEffect, useRef, useState } from "react";
import { Map, NavigationControl, Marker, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Configure MapLibre worker to local public bundle to prevent worker load failure
if (typeof window !== "undefined") {
  setWorkerUrl("/maplibre-gl-worker.mjs");
}

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
  },
  {
    name: "Tyrrhena Terra (CTX DTM Swath)",
    lat: -4.6,
    lon: 66.3,
    type: "High-Resolution Numerical DTM",
    description: "Authentic USGS 20m CTX stereo numerical elevation model coverage (P21_009323_1754)."
  }
];

// Generate GeoJSON graticule lines (30 deg parallels and meridians)
function generateMarsGraticule(): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];

  // Parallels (-60 to +60 in steps of 30)
  for (let lat = -60; lat <= 60; lat += 30) {
    const coords: [number, number][] = [];
    for (let lon = -180; lon <= 180; lon += 5) {
      coords.push([lon, lat]);
    }
    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates: coords },
      properties: { label: `${lat >= 0 ? lat + "°N" : Math.abs(lat) + "°S"}` }
    });
  }

  // Meridians (-180 to 180 in steps of 30)
  for (let lon = -180; lon <= 180; lon += 30) {
    const coords: [number, number][] = [];
    for (let lat = -80; lat <= 80; lat += 5) {
      coords.push([lon, lat]);
    }
    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates: coords },
      properties: { label: `${lon >= 0 ? lon + "°E" : lon + 360 + "°E"}` }
    });
  }

  return { type: "FeatureCollection", features };
}

// Generate Footprint Polygons for acquired DTMs in Web Map coordinates [-180, 180]
function generateAcquiredFootprints(): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {
          id: "megt00n000hb",
          title: "MOLA 128 ppd: megt00n000hb",
          resolution: "463 m/px",
          type: "MOLA MEGDR"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [0, -44],
            [90, -44],
            [90, 0],
            [0, 0],
            [0, -44]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "megt44n000hb",
          title: "MOLA 128 ppd: megt44n000hb",
          resolution: "463 m/px",
          type: "MOLA MEGDR"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [0, 0],
            [90, 0],
            [90, 44],
            [0, 44],
            [0, 0]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "megt00n090hb",
          title: "MOLA 128 ppd: megt00n090hb",
          resolution: "463 m/px",
          type: "MOLA MEGDR"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [90, -44],
            [180, -44],
            [180, 0],
            [90, 0],
            [90, -44]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "ctx_p21_009323",
          title: "USGS CTX DTM: Tyrrhena Terra",
          resolution: "20.0 m/px",
          type: "CTX Numerical DTM"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [66.036, -5.187],
            [66.617, -5.187],
            [66.617, -4.003],
            [66.036, -4.003],
            [66.036, -5.187]
          ]]
        }
      }
    ]
  };
}

export const MapContainer: React.FC<MapContainerProps> = ({
  onCoordinateChange,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const [activeSite, setActiveSite] = useState<MarsFeature | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Dark Mars coordinate canvas (vector space avoiding web mercator tile distortion)
    const map = new Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        name: "Mars-Planetary-Coordinate-Space",
        sources: {},
        layers: [
          {
            id: "background",
            type: "background",
            paint: {
              "background-color": "#090a10"
            }
          }
        ]
      },
      center: [45, 0],
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

      // Add Graticule Source and Layer
      map.addSource("mars-graticule", {
        type: "geojson",
        data: generateMarsGraticule()
      });

      map.addLayer({
        id: "mars-graticule-lines",
        type: "line",
        source: "mars-graticule",
        paint: {
          "line-color": "#2a3656",
          "line-width": 1,
          "line-dasharray": [2, 3],
          "line-opacity": 0.6
        }
      });

      // Add Acquired Footprints
      map.addSource("mars-footprints", {
        type: "geojson",
        data: generateAcquiredFootprints()
      });

      map.addLayer({
        id: "mars-footprints-fill",
        type: "fill",
        source: "mars-footprints",
        paint: {
          "fill-color": [
            "match",
            ["get", "type"],
            "CTX Numerical DTM", "#10b981",
            "#f97316"
          ],
          "fill-opacity": [
            "match",
            ["get", "type"],
            "CTX Numerical DTM", 0.35,
            0.12
          ]
        }
      });

      map.addLayer({
        id: "mars-footprints-border",
        type: "line",
        source: "mars-footprints",
        paint: {
          "line-color": [
            "match",
            ["get", "type"],
            "CTX Numerical DTM", "#34d399",
            "#fb923c"
          ],
          "line-width": [
            "match",
            ["get", "type"],
            "CTX Numerical DTM", 2.5,
            1.5
          ],
          "line-opacity": 0.85
        }
      });

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

      {/* Projection Disclaimer & Scientific Integrity Warning */}
      <div className="absolute top-3 left-3 max-w-md bg-[#0d0f1c]/90 border border-amber-500/40 rounded-lg p-3 backdrop-blur-md shadow-2xl text-xs font-mono pointer-events-auto">
        <div className="flex items-center space-x-2 text-amber-400 font-bold mb-1">
          <span>⚠️</span>
          <span className="uppercase tracking-wider">Planetary CRS Notice</span>
        </div>
        <p className="text-gray-300 text-[11px] leading-relaxed">
          NASA Mars Trek MOLA WMTS uses Mars-specific coordinate system <span className="text-amber-300 font-bold">EPSG:104905</span>.
          Active vector canvas renders authentic MOLA 128 ppd and CTX footprint envelopes directly in Mars coordinate space.
        </p>
        <div className="mt-2 pt-1.5 border-t border-[#22283e] flex items-center justify-between text-[10px] text-gray-400">
          <span>Target Datum: Mars 2000 Sphere</span>
          <span className="text-emerald-400 font-medium">Coordinate Mesh Active</span>
        </div>
      </div>

      {/* Footprint Legend */}
      <div className="absolute bottom-3 right-3 bg-[#0d0f1c]/90 border border-[#2b3350] rounded-lg p-2.5 backdrop-blur-md shadow-xl text-[10px] font-mono pointer-events-auto flex flex-col gap-1.5">
        <div className="text-gray-400 uppercase tracking-wider font-semibold border-b border-[#1f263d] pb-1">Verified Elevation Footprints</div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-2 rounded bg-orange-500/40 border border-orange-400 inline-block"></span>
          <span className="text-gray-200">MOLA 128 ppd (~463 m/px)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-2 rounded bg-emerald-500/50 border border-emerald-400 inline-block"></span>
          <span className="text-gray-200">USGS CTX DTM (20.0 m/px)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-0.5 border-b border-dashed border-[#475569] inline-block"></span>
          <span className="text-gray-400">Mars Graticule (30° mesh)</span>
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
