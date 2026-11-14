"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Map, NavigationControl, Marker, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { API_BASE, fetchDiscoveries } from "../../lib/api";
import { MapLayer, ScienceDiscovery } from "../../lib/types";

// Configure MapLibre worker to local public bundle to prevent worker load failure
if (typeof window !== "undefined") {
  setWorkerUrl("/maplibre-gl-worker.mjs");
}

interface MapContainerProps {
  onCoordinateChange?: (coords: { lat: number; lon: number } | null) => void;
  onCoordinateInspect?: (coords: { lat: number; lon: number }) => void;
  inspectedCoord?: { lat: number; lon: number } | null;
  selectedCrater?: string | null;
  layers?: MapLayer[];
}

interface MarsFeature {
  name: string;
  lat: number;
  lon: number;
  zoom?: number;
  type: string;
  description: string;
}

const FAMOUS_MARS_SITES: MarsFeature[] = [
  {
    name: "USGS CTX DTM (Tyrrhena Terra)",
    lat: -4.600,
    lon: 66.317,
    zoom: 8.5,
    type: "High-Resolution Numerical DTM",
    description: "Authentic USGS 20m CTX stereo numerical elevation model coverage (P21_009323_1754)."
  },
  {
    name: "USGS HiRISE 1m DTM (Holden Crater)",
    lat: -28.500,
    lon: 309.020,
    zoom: 11.0,
    type: "Ultra-High-Resolution HiRISE DTM",
    description: "Authentic USGS 1.01m controlled HiRISE numerical elevation model (ESP_011635_1510)."
  },
  {
    name: "USGS CTX Controlled DTM (Apollinaris Sulci)",
    lat: 4.700,
    lon: 168.250,
    zoom: 9.0,
    type: "Controlled CTX Numerical DTM",
    description: "Authentic USGS 20m controlled CTX numerical elevation model (T01_000893_1847)."
  },
  {
    name: "Sinus Meridiani (THEMIS 256 ppd IR / Opportunity)",
    lat: -2.000,
    lon: 5.000,
    zoom: 6.0,
    type: "Regional Visual IR / Hematite Plains",
    description: "Authentic 256 ppd (~231.5 m/px) THEMIS Band 9 visual display mosaic and high thermal inertia plains."
  },
  {
    name: "MOLA 128 Base Tile (00n000)",
    lat: -22.0,
    lon: 45.0,
    zoom: 3.5,
    type: "MOLA Regional Topography",
    description: "Authentic 463 m/px MOLA 128 ppd tile spanning Lat [-44°, 0°], Lon [0°, 90°E]."
  },
  {
    name: "Jezero Crater (Perseverance)",
    lat: 18.38,
    lon: 77.58,
    zoom: 6.0,
    type: "Landing Site / Ancient Lakebed",
    description: "Delta deposit rich in clay minerals, site of Perseverance astrobiology mission."
  },
  {
    name: "Gale Crater (Curiosity)",
    lat: -4.59,
    lon: 137.44,
    zoom: 6.0,
    type: "Landing Site / Mount Sharp",
    description: "Layered sedimentary mound recording transitional aqueous environments."
  },
  {
    name: "Olympus Mons Caldera",
    lat: 18.65,
    lon: 226.2,
    zoom: 4.5,
    type: "Shield Volcano",
    description: "Largest volcano in solar system; summit elevation ~21.3 km above Mars datum."
  },
  {
    name: "Valles Marineris (Melas Chasma)",
    lat: -9.8,
    lon: 283.6,
    zoom: 4.5,
    type: "Tectonic Rift System",
    description: "Grand canyon of Mars spanning over 4,000 km, canyon depth reaches 7 km."
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
            [66.03181, -5.18565],
            [66.60308, -5.18565],
            [66.60308, -4.01340],
            [66.03181, -4.01340],
            [66.03181, -5.18565]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "ctx_t01_000893",
          title: "USGS CTX Controlled DTM: Apollinaris Sulci",
          resolution: "20.0 m/px",
          type: "CTX Numerical DTM"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [168.086, 4.454],
            [168.492, 4.454],
            [168.492, 4.983],
            [168.086, 4.983],
            [168.086, 4.454]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "hirise_esp_011635",
          title: "USGS HiRISE Controlled DTM: Holden Crater",
          resolution: "1.01 m/px",
          type: "HiRISE Ultra-Res DTM"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [-51.013, -28.650],
            [-50.950, -28.650],
            [-50.950, -28.382],
            [-51.013, -28.382],
            [-51.013, -28.650]
          ]]
        }
      },
      {
        type: "Feature",
        properties: {
          id: "themis_ir_n30_000",
          title: "THEMIS 100m Regional IR Mosaic (N-30_000)",
          resolution: "231.5 m/px",
          type: "THEMIS IR Visual Mosaic"
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [0, -30],
            [30, -30],
            [30, 0],
            [0, 0],
            [0, -30]
          ]]
        }
      }
    ]
  };
}

export const MapContainer: React.FC<MapContainerProps> = ({
  onCoordinateChange,
  onCoordinateInspect,
  inspectedCoord,
  layers,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const inspectorMarkerRef = useRef<Marker | null>(null);
  const discoveryMarkersRef = useRef<Marker[]>([]);
  const [activeSite, setActiveSite] = useState<MarsFeature | null>(null);
  const [activeDiscovery, setActiveDiscovery] = useState<ScienceDiscovery | null>(null);
  const [discoveries, setDiscoveries] = useState<ScienceDiscovery[]>([]);
  const [isMapLoaded, setIsMapLoaded] = useState<boolean>(false);
  const [currentZoom, setCurrentZoom] = useState<number>(1.5);
  const [activeElevationMode, setActiveElevationMode] = useState<"global" | "ctx">("global");

  const flyToSite = useCallback((site: MarsFeature) => {
    if (!mapRef.current) return;
    setActiveSite(site);
    const targetLon = site.lon > 180 ? site.lon - 360 : site.lon;
    mapRef.current.flyTo({
      center: [targetLon, site.lat],
      zoom: site.zoom ?? 4.0,
      essential: true,
      duration: 1800,
    });
    if (site.name.includes("CTX")) {
      setActiveElevationMode("ctx");
    } else {
      setActiveElevationMode("global");
    }
  }, []);

  // Update layer visibility when `layers` prop changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoaded || !layers) return;

    // Helper to safely set visibility
    const setVisibility = (layerId: string, visible: boolean) => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
      }
    };

    const globalMola = layers.find((l) => l.id === "mola-elevation-global");
    const molaTiles = layers.find((l) => l.id === "mola-128-tiles");
    const ctxDtm = layers.find((l) => l.id === "ctx-dtm-p21-009323");
    const ctxT01 = layers.find((l) => l.id === "ctx-controlled-t01");
    const hiriseEsp = layers.find((l) => l.id === "hirise-controlled-esp");
    const tesThermal = layers.find((l) => l.id === "tes-thermal-inertia");
    const themisIr = layers.find((l) => l.id === "themis-ir-regional");
    const sim3292 = layers.find((l) => l.id === "sim3292-geology");
    const graticule = layers.find((l) => l.id === "mars-graticule-grid");
    const footprints = layers.find((l) => l.id === "dataset-footprints");

    if (globalMola) {
      setVisibility("layer-mola-east", globalMola.enabled);
      setVisibility("layer-mola-west", globalMola.enabled);
    }
    if (molaTiles) {
      setVisibility("layer-mola-tile-00n000", molaTiles.enabled);
      setVisibility("layer-mola-tile-44n000", molaTiles.enabled);
      setVisibility("layer-mola-tile-00n090", molaTiles.enabled);
    }
    if (ctxDtm) {
      setVisibility("layer-ctx-dtm", ctxDtm.enabled);
    }
    if (ctxT01) {
      setVisibility("layer-ctx-t01", ctxT01.enabled);
    }
    if (hiriseEsp) {
      setVisibility("layer-hirise-esp", hiriseEsp.enabled);
    }
    if (tesThermal) {
      setVisibility("layer-tes-thermal", tesThermal.enabled);
    }
    if (themisIr) {
      setVisibility("layer-themis-ir", themisIr.enabled);
    }
    if (sim3292) {
      setVisibility("layer-sim3292-geology-fill", sim3292.enabled);
      setVisibility("layer-sim3292-geology-line", sim3292.enabled);
    }
    if (graticule) {
      setVisibility("mars-graticule-lines", graticule.enabled);
    }
    if (footprints) {
      setVisibility("mars-footprints-fill", footprints.enabled);
      setVisibility("mars-footprints-border", footprints.enabled);
    }
  }, [layers, isMapLoaded]);

  // Sync inspection marker reticle
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoaded) return;

    if (!inspectedCoord) {
      if (inspectorMarkerRef.current) {
        inspectorMarkerRef.current.remove();
        inspectorMarkerRef.current = null;
      }
      return;
    }

    const displayLon = inspectedCoord.lon > 180 ? inspectedCoord.lon - 360 : inspectedCoord.lon;

    if (!inspectorMarkerRef.current) {
      const el = document.createElement("div");
      el.className = "inspector-target-reticle pointer-events-none";
      el.innerHTML = `
        <div class="relative flex items-center justify-center -translate-x-1/2 -translate-y-1/2">
          <div class="w-8 h-8 rounded-full border-2 border-emerald-400 animate-ping absolute opacity-75"></div>
          <div class="w-6 h-6 rounded-full border border-dashed border-emerald-300 animate-spin absolute"></div>
          <div class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></div>
        </div>
      `;
      inspectorMarkerRef.current = new Marker({ element: el })
        .setLngLat([displayLon, inspectedCoord.lat])
        .addTo(map);
    } else {
      inspectorMarkerRef.current.setLngLat([displayLon, inspectedCoord.lat]);
    }
  }, [inspectedCoord, isMapLoaded]);

  // Load and place interactive Science Discovery markers on the Mars map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapLoaded) return;

    fetchDiscoveries()
      .then((data) => {
        setDiscoveries(data);
        // Clear any previous markers
        discoveryMarkersRef.current.forEach((m) => m.remove());
        discoveryMarkersRef.current = [];

        data.forEach((disc) => {
          const el = document.createElement("div");
          el.className = "group relative cursor-pointer";
          const displayLon = disc.longitude > 180 ? disc.longitude - 360 : disc.longitude;

          let badgeColor = "bg-orange-500 border-amber-300";
          let icon = "📍";
          if (disc.category === "high_res_terrain") {
            badgeColor = "bg-emerald-500 border-emerald-200";
            icon = "🔬";
          } else if (disc.category === "landing_site") {
            badgeColor = "bg-blue-600 border-blue-200";
            icon = "🚀";
          } else if (disc.category === "geological_unit_contact") {
            badgeColor = "bg-amber-600 border-amber-200";
            icon = "🌋";
          } else if (disc.category === "structural_feature") {
            badgeColor = "bg-purple-600 border-purple-200";
            icon = "⚡";
          } else if (disc.category === "thermal_contrast") {
            badgeColor = "bg-cyan-600 border-cyan-200";
            icon = "🌡️";
          } else if (disc.category === "multi_dataset_intersection") {
            badgeColor = "bg-rose-600 border-rose-200";
            icon = "🎯";
          }

          el.innerHTML = `
            <div class="w-5 h-5 rounded-full ${badgeColor} border shadow-lg flex items-center justify-center transform hover:scale-135 transition-transform" title="${disc.name} (${disc.category.replace(/_/g, ' ')})">
              <span class="text-[10px] leading-none">${icon}</span>
            </div>
          `;

          el.addEventListener("click", () => {
            setActiveDiscovery(disc);
            setActiveSite(null);
            if (mapRef.current) {
              mapRef.current.flyTo({
                center: [displayLon, disc.latitude],
                zoom: disc.category === "high_res_terrain" ? 8.5 : 5.5,
                essential: true,
                duration: 1500,
              });
            }
            if (onCoordinateInspect) {
              onCoordinateInspect({
                lat: Number(disc.latitude.toFixed(5)),
                lon: Number(disc.longitude.toFixed(5)),
              });
            }
          });

          const m = new Marker({ element: el })
            .setLngLat([displayLon, disc.latitude])
            .addTo(map);

          discoveryMarkersRef.current.push(m);
        });
      })
      .catch((err) => console.error("Failed to load map discoveries:", err));

    return () => {
      discoveryMarkersRef.current.forEach((m) => m.remove());
      discoveryMarkersRef.current = [];
    };
  }, [isMapLoaded, onCoordinateInspect]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    let initCenter: [number, number] = [45, 0];
    let initZoom = 1.5;
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search);
      const latP = p.get("lat");
      const lonP = p.get("lon");
      const zoomP = p.get("zoom");
      if (latP && lonP) {
        const rawLon = parseFloat(lonP);
        initCenter = [rawLon > 180 ? rawLon - 360 : rawLon, parseFloat(latP)];
      }
      if (zoomP) {
        initZoom = parseFloat(zoomP);
      }
    }

    // Dark Mars coordinate canvas
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
              "background-color": "#06070d"
            }
          }
        ]
      },
      center: initCenter,
      zoom: initZoom,
      minZoom: 1,
      maxZoom: 14,
      pitch: 0,
      bearing: 0,
    });

    mapRef.current = map;

    map.on("load", () => {
      // Add navigation controls
      map.addControl(new NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");

      // ==========================================
      // 1. AUTHENTIC GLOBAL MOLA NUMERICAL RASTERS
      // ==========================================
      // East hemisphere: [0, 180] lon, [-85.05, 85.05] lat
      map.addSource("src-mola-east", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/global-mola?hemisphere=east`,
        coordinates: [
          [0, 85.0511],
          [180, 85.0511],
          [180, -85.0511],
          [0, -85.0511]
        ]
      });
      map.addLayer({
        id: "layer-mola-east",
        type: "raster",
        source: "src-mola-east",
        paint: { "raster-opacity": 0.85 }
      });

      // West hemisphere: [-180, 0] lon (180 to 360E), [-85.05, 85.05] lat
      map.addSource("src-mola-west", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/global-mola?hemisphere=west`,
        coordinates: [
          [-180, 85.0511],
          [0, 85.0511],
          [0, -85.0511],
          [-180, -85.0511]
        ]
      });
      map.addLayer({
        id: "layer-mola-west",
        type: "raster",
        source: "src-mola-west",
        paint: { "raster-opacity": 0.85 }
      });

      // ==========================================
      // 2. AUTHENTIC MOLA 128 PPD REGIONAL TILES
      // ==========================================
      // Tile 00n000: Lat [-44, 0], Lon [0, 90]
      map.addSource("src-mola-tile-00n000", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/mola-128-tile?tile_id=00n000`,
        coordinates: [
          [0, 0],
          [90, 0],
          [90, -44],
          [0, -44]
        ]
      });
      map.addLayer({
        id: "layer-mola-tile-00n000",
        type: "raster",
        source: "src-mola-tile-00n000",
        paint: { "raster-opacity": 0.90 }
      });

      // Tile 44n000: Lat [0, 44], Lon [0, 90]
      map.addSource("src-mola-tile-44n000", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/mola-128-tile?tile_id=44n000`,
        coordinates: [
          [0, 44],
          [90, 44],
          [90, 0],
          [0, 0]
        ]
      });
      map.addLayer({
        id: "layer-mola-tile-44n000",
        type: "raster",
        source: "src-mola-tile-44n000",
        paint: { "raster-opacity": 0.90 }
      });

      // Tile 00n090: Lat [-44, 0], Lon [90, 180]
      map.addSource("src-mola-tile-00n090", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/mola-128-tile?tile_id=00n090`,
        coordinates: [
          [90, 0],
          [180, 0],
          [180, -44],
          [90, -44]
        ]
      });
      map.addLayer({
        id: "layer-mola-tile-00n090",
        type: "raster",
        source: "src-mola-tile-00n090",
        paint: { "raster-opacity": 0.90 }
      });

      // ==========================================
      // 3. AUTHENTIC USGS 20m CTX NUMERICAL DTM
      // ==========================================
      // Lat [-5.18565, -4.01340], Lon [66.03181, 66.60308]
      map.addSource("src-ctx-dtm", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/ctx-dtm`,
        coordinates: [
          [66.03181, -4.01340],
          [66.60308, -4.01340],
          [66.60308, -5.18565],
          [66.03181, -5.18565]
        ]
      });
      map.addLayer({
        id: "layer-ctx-dtm",
        type: "raster",
        source: "src-ctx-dtm",
        paint: { "raster-opacity": 0.95 }
      });

      // 3B. USGS CONTROLLED CTX DTM: Apollinaris Sulci (20m/px)
      map.addSource("src-ctx-t01", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/window?min_lon=168.086&min_lat=4.454&max_lon=168.492&max_lat=4.983&preferred_tier=ctx&width=512&height=512`,
        coordinates: [
          [168.086, 4.983],
          [168.492, 4.983],
          [168.492, 4.454],
          [168.086, 4.454]
        ]
      });
      map.addLayer({
        id: "layer-ctx-t01",
        type: "raster",
        source: "src-ctx-t01",
        layout: { visibility: "visible" },
        paint: { "raster-opacity": 0.95 }
      });

      // 3C. USGS CONTROLLED HiRISE DTM: Holden Crater (1.01m/px)
      map.addSource("src-hirise-esp", {
        type: "image",
        url: `${API_BASE}/api/v1/terrain/render/window?min_lon=308.987&min_lat=-28.650&max_lon=309.050&max_lat=-28.382&preferred_tier=hirise&width=512&height=512`,
        coordinates: [
          [-51.013, -28.382],
          [-50.950, -28.382],
          [-50.950, -28.650],
          [-51.013, -28.650]
        ]
      });
      map.addLayer({
        id: "layer-hirise-esp",
        type: "raster",
        source: "src-hirise-esp",
        layout: { visibility: "visible" },
        paint: { "raster-opacity": 0.98 }
      });

      // 3D. 2001 MARS ODYSSEY THEMIS 100m IR REGIONAL MOSAIC
      map.addSource("src-themis-ir", {
        type: "image",
        url: `${API_BASE}/api/v1/themis/render/window?min_lon=0&min_lat=-30&max_lon=30&max_lat=0&mode=day&width=512&height=512`,
        coordinates: [
          [0, 0],
          [30, 0],
          [30, -30],
          [0, -30]
        ]
      });
      map.addLayer({
        id: "layer-themis-ir",
        type: "raster",
        source: "src-themis-ir",
        layout: { visibility: "none" },
        paint: { "raster-opacity": 0.85 }
      });

      // 3E. MGS TES GLOBAL THERMAL INERTIA (Putzig & Mellon 2007)
      map.addSource("src-tes-thermal", {
        type: "image",
        url: `${API_BASE}/api/v1/thermal/render/window?min_lon=-180&min_lat=-90&max_lon=180&max_lat=90&product=dayside&width=1024&height=512`,
        coordinates: [
          [-180, 90],
          [180, 90],
          [180, -90],
          [-180, -90]
        ]
      });
      map.addLayer({
        id: "layer-tes-thermal",
        type: "raster",
        source: "src-tes-thermal",
        layout: { visibility: "none" },
        paint: { "raster-opacity": 0.70 }
      });

      // 3F. USGS SIM 3292 GLOBAL GEOLOGIC MAP
      map.addSource("src-sim3292-geology", {
        type: "geojson",
        data: `${API_BASE}/api/v1/geology/viewport?min_lon=-180&min_lat=-90&max_lon=180&max_lat=90&layer=geology&limit=1000`
      });
      map.addLayer({
        id: "layer-sim3292-geology-fill",
        type: "fill",
        source: "src-sim3292-geology",
        layout: { visibility: "none" },
        paint: {
          "fill-color": "#e0a96d",
          "fill-opacity": 0.25
        }
      });
      map.addLayer({
        id: "layer-sim3292-geology-line",
        type: "line",
        source: "src-sim3292-geology",
        layout: { visibility: "none" },
        paint: {
          "line-color": "#ffedd5",
          "line-width": 1,
          "line-opacity": 0.6
        }
      });

      // ==========================================
      // 4. VECTOR GRATICULE & FOOTPRINT ENVELOPES
      // ==========================================
      map.addSource("mars-graticule", {
        type: "geojson",
        data: generateMarsGraticule()
      });

      map.addLayer({
        id: "mars-graticule-lines",
        type: "line",
        source: "mars-graticule",
        paint: {
          "line-color": "#384766",
          "line-width": 1,
          "line-dasharray": [2, 3],
          "line-opacity": 0.7
        }
      });

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
            "CTX Numerical DTM", 0.15,
            0.05
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

      // ==========================================
      // 5. MARS SITES & SCIENTIFIC TARGET MARKERS
      // ==========================================
      FAMOUS_MARS_SITES.forEach((site) => {
        const el = document.createElement("div");
        el.className = "group relative cursor-pointer";
        const isCtx = site.name.includes("CTX");
        el.innerHTML = `
          <div class="w-4 h-4 rounded-full ${isCtx ? 'bg-emerald-500 border-emerald-200' : 'bg-orange-600 border-amber-300'} border shadow-md flex items-center justify-center transform hover:scale-125 transition-transform">
            <div class="w-1.5 h-1.5 rounded-full ${isCtx ? 'bg-white animate-ping' : 'bg-amber-100'}"></div>
          </div>
        `;
        el.addEventListener("click", () => {
          flyToSite(site);
        });

        new Marker({ element: el })
          .setLngLat([site.lon > 180 ? site.lon - 360 : site.lon, site.lat])
          .addTo(map);
      });

      setIsMapLoaded(true);
    });

    map.on("zoom", () => {
      setCurrentZoom(map.getZoom());
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

    map.on("click", (e) => {
      if (onCoordinateInspect) {
        const rawLon = e.lngLat.lng;
        const normalizedLon = rawLon < 0 ? rawLon + 360 : rawLon;
        onCoordinateInspect({
          lat: Number(e.lngLat.lat.toFixed(5)),
          lon: Number(normalizedLon.toFixed(5)),
        });
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onCoordinateChange, onCoordinateInspect, flyToSite]);

  return (
    <div className="relative w-full h-full bg-[#06070d] overflow-hidden select-none">
      {/* MapLibre DOM viewport */}
      <div ref={mapContainerRef} className="w-full h-full cursor-crosshair" />

      {/* Top Floating Quick-Navigation Bar */}
      <div className="absolute top-3 left-3 flex flex-wrap items-center gap-1.5 z-10 font-mono text-[11px] max-w-2xl pointer-events-auto">
        <span className="text-[10px] text-gray-400 bg-[#0d0f1c]/90 border border-[#22283e] px-2 py-1 rounded backdrop-blur-md font-semibold">
          TARGET RECON:
        </span>
        {FAMOUS_MARS_SITES.map((site) => (
          <button
            key={site.name}
            onClick={() => flyToSite(site)}
            className={`px-2 py-1 rounded border backdrop-blur-md transition-all flex items-center gap-1 shadow-lg ${
              activeSite?.name === site.name
                ? "bg-orange-500/30 border-orange-400 text-orange-200 font-bold"
                : site.name.includes("CTX")
                ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-300 hover:bg-emerald-900/90 hover:border-emerald-400"
                : "bg-[#0d0f1c]/85 border-[#2b3350] text-gray-300 hover:bg-[#1a1e36] hover:text-white"
            }`}
          >
            <span>{site.name.includes("CTX") ? "🔬" : "📍"}</span>
            <span>{site.name.split(" ")[0]} {site.name.includes("CTX") ? "20m DTM" : ""}</span>
          </button>
        ))}
      </div>

      {/* CRS & Scientific Integrity Banner */}
      <div className="absolute top-12 left-3 max-w-sm bg-[#0d0f1c]/90 border border-amber-500/40 rounded-lg p-2.5 backdrop-blur-md shadow-2xl text-[10px] font-mono pointer-events-auto">
        <div className="flex items-center space-x-2 text-amber-400 font-bold mb-0.5">
          <span>⚠️</span>
          <span className="uppercase tracking-wider">Planetary Topography Engine</span>
        </div>
        <p className="text-gray-300 text-[10px] leading-tight">
          Rendering authentic numerical rasters: <span className="text-orange-400 font-semibold">MOLA MEGDR (463m/px)</span> &amp; <span className="text-emerald-400 font-semibold">USGS CTX DTM (20m/px)</span>.
        </p>
        <div className="mt-1.5 pt-1 border-t border-[#22283e] flex items-center justify-between text-[9px] text-gray-400">
          <span>Datum: Mars 2000 Sphere / Areoid</span>
          <span className="text-emerald-400 font-medium">Turbo Hypsometric Shader</span>
        </div>
      </div>

      {/* Active Resolution Tier HUD */}
      <div className="absolute top-12 right-14 bg-[#0d0f1c]/95 border border-[#262c45] rounded-lg px-3 py-2 backdrop-blur-md shadow-2xl text-[10px] font-mono pointer-events-auto flex items-center space-x-3">
        <div className="flex flex-col">
          <span className="text-[9px] text-gray-400 uppercase tracking-wider font-semibold">Active Resolution Tier</span>
          <div className="flex items-center space-x-1.5 mt-0.5">
            {currentZoom >= 7 ? (
              <span className="px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                LOCAL: CTX Stereo DTM (20.0 m/px)
              </span>
            ) : currentZoom >= 3 ? (
              <span className="px-1.5 py-0.5 rounded bg-orange-950/80 border border-orange-500/60 text-orange-300 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-400"></span>
                REGIONAL: MOLA 128 (463.1 m/px)
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-blue-950/80 border border-blue-500/60 text-blue-300 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                GLOBAL: MOLA MEGDR 4 ppd (14.8 km/px)
              </span>
            )}
            <span className="text-gray-400 font-mono text-[9px]">z: {currentZoom.toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* Click-to-inspect helper */}
      <div className="absolute bottom-3 left-3 bg-[#0d0f1c]/90 border border-[#232840] rounded px-2.5 py-1 text-[10px] font-mono text-gray-400 pointer-events-none flex items-center gap-1.5 z-10">
        <span className="text-emerald-400 font-bold">⊕</span>
        <span>Click anywhere to inspect numerical elevation</span>
      </div>

      {/* Elevation Color Ramp Legend */}
      <div className="absolute bottom-3 right-3 bg-[#0d0f1c]/95 border border-[#2b3350] rounded-lg p-3 backdrop-blur-md shadow-2xl text-[10px] font-mono pointer-events-auto w-72">
        <div className="flex items-center justify-between border-b border-[#1f263d] pb-1.5 mb-2">
          <span className="text-gray-300 uppercase tracking-wider font-bold">Elevation Hypsometry</span>
          <div className="flex gap-1">
            <button
              onClick={() => setActiveElevationMode("global")}
              className={`px-1.5 py-0.5 rounded text-[9px] ${
                activeElevationMode === "global"
                  ? "bg-orange-500 text-white font-bold"
                  : "text-gray-400 hover:text-white bg-[#141727]"
              }`}
            >
              MOLA
            </button>
            <button
              onClick={() => setActiveElevationMode("ctx")}
              className={`px-1.5 py-0.5 rounded text-[9px] ${
                activeElevationMode === "ctx"
                  ? "bg-emerald-500 text-white font-bold"
                  : "text-gray-400 hover:text-white bg-[#141727]"
              }`}
            >
              CTX
            </button>
          </div>
        </div>

        {activeElevationMode === "global" ? (
          <div>
            <div className="text-[9px] text-gray-400 mb-1 flex justify-between">
              <span>MOLA Global Scale</span>
              <span>-8,200m to +21,200m</span>
            </div>
            {/* Turbo Colormap gradient bar */}
            <div
              className="h-3.5 w-full rounded border border-[#3b4566] shadow-inner"
              style={{
                background: "linear-gradient(to right, #30123b, #4662d7, #28bbec, #35f599, #a2fc3c, #fbbe23, #f05c03, #a21201, #7a0403)"
              }}
            />
            <div className="flex justify-between text-[9px] text-gray-300 mt-1 font-semibold">
              <span className="text-purple-400">-8.2 km</span>
              <span className="text-blue-300">-4 km</span>
              <span className="text-emerald-300">0 m (Datum)</span>
              <span className="text-amber-300">+8 km</span>
              <span className="text-red-400">+21.2 km</span>
            </div>
          </div>
        ) : (
          <div>
            <div className="text-[9px] text-emerald-400 mb-1 flex justify-between font-semibold">
              <span>USGS CTX DTM (Tyrrhena Terra)</span>
              <span>+800m to +2,520m</span>
            </div>
            {/* CTX gradient bar */}
            <div
              className="h-3.5 w-full rounded border border-emerald-700/60 shadow-inner"
              style={{
                background: "linear-gradient(to right, #30123b, #4662d7, #28bbec, #35f599, #a2fc3c, #fbbe23, #f05c03)"
              }}
            />
            <div className="flex justify-between text-[9px] text-emerald-200 mt-1 font-semibold">
              <span>+800 m (Basin Floor)</span>
              <span>+1,660 m</span>
              <span>+2,520 m (Rim Plateau)</span>
            </div>
          </div>
        )}

        <div className="mt-2.5 pt-2 border-t border-[#1f263d] space-y-1 text-[9px]">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">MOLA 128 (463 m/px):</span>
            <span className="text-orange-400 font-semibold">Tile Envelopes Active</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">USGS CTX DTM (20 m/px):</span>
            <span className="text-emerald-400 font-semibold">Stereo Raster Active</span>
          </div>
        </div>
      </div>

      {/* Active Crater / Site card */}
      {activeSite && (
        <div className="absolute bottom-3 left-3 max-w-sm bg-[#111322]/95 border border-[#2b3350] rounded-lg p-3 backdrop-blur-md shadow-2xl text-xs font-mono z-10 pointer-events-auto">
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
            <div>Lat: <span className="text-gray-200">{activeSite.lat >= 0 ? `${activeSite.lat.toFixed(3)}°N` : `${Math.abs(activeSite.lat).toFixed(3)}°S`}</span></div>
            <div>Lon: <span className="text-gray-200">{activeSite.lon.toFixed(3)}°E</span></div>
            <div className="col-span-2">Type: <span className="text-amber-400">{activeSite.type}</span></div>
          </div>
        </div>
      )}

      {/* Active Science Discovery Target Card */}
      {activeDiscovery && (
        <div className="absolute bottom-3 left-3 max-w-sm bg-[#0e1122]/95 border border-[#2b3556] rounded-xl p-3.5 backdrop-blur-md shadow-2xl text-xs font-mono z-10 pointer-events-auto">
          <div className="flex items-center justify-between border-b border-[#212942] pb-1.5 mb-2">
            <div className="flex items-center space-x-1.5">
              <span className="text-sm">🔭</span>
              <span className="font-bold text-gray-100">{activeDiscovery.name}</span>
            </div>
            <button
              onClick={() => setActiveDiscovery(null)}
              className="text-gray-400 hover:text-white px-1 text-xs"
            >
              ✕
            </button>
          </div>
          <div className="flex items-center space-x-2 mb-2">
            <span className="px-1.5 py-0.2 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30 text-[9px] font-semibold uppercase">
              {activeDiscovery.category.replace(/_/g, " ")}
            </span>
            <span className="text-[10px] text-gray-400">
              {activeDiscovery.primary_feature}
            </span>
          </div>
          <p className="text-[11px] text-gray-300 mb-2.5 leading-relaxed line-clamp-3">
            {activeDiscovery.scientific_significance}
          </p>
          <div className="text-[10px] grid grid-cols-2 gap-1.5 text-gray-400 bg-[#080a14] p-2 rounded-lg border border-[#1d2338] mb-2.5">
            <div>Lat: <span className="text-amber-300 font-bold">{activeDiscovery.latitude.toFixed(4)}°</span></div>
            <div>Lon: <span className="text-amber-300 font-bold">{activeDiscovery.longitude.toFixed(4)}°E</span></div>
            <div className="col-span-2 text-[9px] text-gray-400 truncate">
              Datasets: <span className="text-gray-300">{activeDiscovery.supporting_datasets.join(", ")}</span>
            </div>
          </div>
          <button
            onClick={() => {
              if (onCoordinateInspect) {
                onCoordinateInspect({
                  lat: Number(activeDiscovery.latitude.toFixed(5)),
                  lon: Number(activeDiscovery.longitude.toFixed(5)),
                });
              }
            }}
            className="w-full py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded font-bold text-[10px] transition-colors uppercase tracking-wider text-center"
          >
            Inspect Geodetic &amp; Geological Profile ➔
          </button>
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
