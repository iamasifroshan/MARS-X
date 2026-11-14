# MARS-X — Research Report: MapLibre GL JS Worker Architecture & Mars Geospatial Canvas

## 1. Technical Context

MapLibre GL JS is an open-source WebGL/WebGPU mapping library designed primarily for Earth-based Web Mercator projection systems (EPSG:3857). In planetary geospatial science, rendering Mars elevation datasets presents two distinct challenges:
1. **Worker Bundling Conflict:** In modern React 19 / Next.js 16 environments using Turbopack, MapLibre's background worker (`maplibre-gl-worker.js`) cannot be bundled inline as a Blob URL without causing security and CSP initialization exceptions (`Worker failed to load`).
2. **Projection Distortion Safeguard:** Projecting global Mars rasters directly into EPSG:3857 induces extreme polar distortion and false geodesic distance metrics.

---

## 2. Solution: Standalone Worker Pipeline

To ensure 100% deterministic worker instantiation across all browsers:
1. `maplibre-gl-worker.mjs` and its corresponding source map (`maplibre-gl-worker.mjs.map`) were copied directly from `frontend/node_modules/maplibre-gl/dist/` into `frontend/public/maplibre-gl-worker.mjs`.
2. In `frontend/src/components/map/MapContainer.tsx`, the MapLibre worker URL was explicitly declared prior to canvas instantiation:
   ```typescript
   import { setWorkerUrl } from "maplibre-gl";
   if (typeof window !== "undefined") {
     setWorkerUrl("/maplibre-gl-worker.mjs");
   }
   ```
3. Serving tests verified that `http://127.0.0.1:3005/maplibre-gl-worker.mjs` returns HTTP 200 with content length 519,547 bytes.

---

## 3. Vector Graticule & DTM Footprint Envelopes

Rather than rendering an empty dark screen, MARS-X renders an authentic Mars planetary coordinate space:
- **Mars Coordinate Graticule:** Mathematical GeoJSON generation creates 30° parallel lines (-60° to +60° Lat) and 30° meridian lines (-180° to +180° Lon).
- **MOLA 128 ppd Footprint Polygons:** Orange vector polygons denote authentic coverage for:
  - `megt00n000hb` (Lat [-44°, 0°], Lon [0°, 90°E])
  - `megt44n000hb` (Lat [0°, 44°], Lon [0°, 90°E])
  - `megt00n090hb` (Lat [-44°, 0°], Lon [90°, 180°E])
- **USGS CTX DTM Footprint:** Emerald vector polygon highlights the high-resolution numerical stereo DTM swath in Tyrrhena Terra:
  - Lat [-5.187°, -4.003°], Lon [66.036°, 66.617°E] at 20.0 m/px.
- **Interactive Inspection:** Interactive markers denote key exploration sites (Jezero Crater, Gale Crater, Olympus Mons Caldera, Valles Marineris, and Tyrrhena Terra).
