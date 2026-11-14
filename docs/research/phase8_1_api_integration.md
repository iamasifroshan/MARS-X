# MARS-X — Research Report: API Integration, Serialization & Endpoint Architecture

## 1. Overview

MARS-X exposes a comprehensive set of RESTful endpoints powering planetary cartographic queries, resolution selection, multi-scale terrain profiling, transition compatibility checks, region comparisons, and route corridor source validations.

---

## 2. Documented Endpoints

### 2.1 Core System & Health
- `GET /health`: Basic daemon health and application version (`{"status": "ok", "app": "MARS-X", "version": "0.1.0"}`).
- `GET /api/v1/status`: Comprehensive status report detailing uptime and operational state across the dataset catalogue, geospatial engine, terrain processor, and routing services.

### 2.2 Planetary Terrain Intelligence (`/api/v1/science/*`)
- `GET /api/v1/science/resolution-selection`:
  - Parameters: `min_lat`, `min_lon`, `max_lat`, `max_lon`, `analysis_type`, `target_scale_m`, `require_local_raster`.
  - Evaluates all catalogued elevation products, rejects unacquired remote footprints, and returns the mathematically optimal local DTM profile.
- `GET /api/v1/science/terrain-profile`:
  - Parameters: `min_lat`, `min_lon`, `max_lat`, `max_lon`, `windows_m`.
  - Calculates moving-window slopes (Horn 3x3), roughness, and local relief across explicit physical diameters.
- `GET /api/v1/science/transition-compatibility`:
  - Parameters: `product_a`, `product_b`.
  - Evaluates spatial overlap, datum alignment, horizontal scale drift in parts-per-million (ppm), and specifies permitted vs forbidden operations.
- `GET /api/v1/science/region-assessment`:
  - Parameters: `min_lat`, `min_lon`, `max_lat`, `max_lon`, `name`, `region_id`, `target_scale_m`.
  - Generates comprehensive topographic characterization including effective scale metrics and Heuristic Data Quality Index.
- `GET /api/v1/science/region-comparison`:
  - Parameters: `target_scale_m`.
  - Compares candidate Martian regions at controlled physical analysis scales, rendering pairwise contrasts and scale compatibility classifications.

### 2.3 Traverse Corridor Intelligence (`/api/v1/routes/*`)
- `GET /api/v1/routes/terrain-source`:
  - Parameters: `start_lat`, `start_lon`, `dest_lat`, `dest_lon`, `target_scale_m`.
  - Evaluates route centerline valid coverage, buffered corridor coverage, and bounding-box coverage before approving terrain cost graph generation.
