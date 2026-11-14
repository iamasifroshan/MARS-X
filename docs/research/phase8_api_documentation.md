# Phase 8: Mission Intelligence API Documentation

**Author:** Full-Stack Planetary Systems Architect  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Overview of Endpoints

Phase 8 introduces 6 versioned REST endpoints under the `/api/v1/science` and `/api/v1/routing` routers. All endpoints enforce Pydantic request/response validation, dimensional bounding-box clamping, and strict planetary cartography rules.

---

## 2. API Reference

### 1. GET `/api/v1/science/resolution-selection`
Selects the scientifically optimal native-resolution dataset for a requested bounding box and mission intent.
- **Parameters:**
  - `min_lat`, `max_lat`: float ([-90.0, 90.0])
  - `min_lon`, `max_lon`: float ([0.0, 360.0])
  - `analysis_type`: string (`traverse_planning`, `regional_survey`, `hazard_assessment`, `reconnaissance`, `site_inspection`)
  - `target_scale_m`: float (optional, e.g. 500.0)
  - `require_local_raster`: bool (default true)
  - `min_coverage_pct`: float (default 50.0)
- **Response Model:** `ResolutionSelectionResult`
  - Returns `status` (`selected`, `partial_coverage`, `insufficient_data`), `selected_product_id`, `native_resolution_m`, `coverage_percentage`, `selection_rationale`, and `evaluated_candidates`.

### 2. GET `/api/v1/science/terrain-profile`
Computes topographic slope, roughness, relief, and complexity classes across documented physical windows in metres.
- **Parameters:**
  - `min_lat`, `max_lat`, `min_lon`, `max_lon`: float
  - `dataset_id`: string (optional)
  - `windows_m`: string (comma-separated, default `"100,500,1000,2000"`)
- **Response Model:** `MultiScaleAnalysisResult`
  - Returns `scales` array containing `window_m`, `neighborhood_pixels`, `mean_slope_deg`, `max_slope_deg`, `mean_roughness_m`, `mean_local_relief_m`, and `complexity_class`.

### 3. GET `/api/v1/science/transition-compatibility`
Evaluates whether two datasets can support a continuous or partitioned analytical region.
- **Parameters:**
  - `product_a`: string (e.g. `"mola-megdr-128"`)
  - `product_b`: string (e.g. `"ctx-dtm-p21-009323"`)
- **Response Model:** `ResolutionTransitionEvaluation`
  - Returns `transition_status` (`compatible`, `compatible_with_documented_transformation`, `incompatible`), `horizontal_scale_drift_ppm`, `permitted_operations`, `forbidden_operations`, and `partition_strategy`.

### 4. GET `/api/v1/science/region-assessment`
Returns a comprehensive terrain intelligence assessment for a single exploration region.
- **Parameters:**
  - `min_lat`, `max_lat`, `min_lon`, `max_lon`: float
  - `name`: string
  - `target_scale_m`: float (default 500.0)
- **Response Model:** `RegionTerrainAssessment`
  - Returns `data_confidence_score` (0-100), `confidence_breakdown`, `mean_slope_deg`, `mean_roughness_m`, `terrain_complexity_class`, and `scientific_summary`.

### 5. GET & POST `/api/v1/science/region-comparison`
Contrasts multiple candidate regions at an equivalent physical scale.
- **Parameters (GET):** `target_scale_m`: float (default 500.0)
- **Payload (POST):** `RegionComparisonRequest`
- **Response Model:** `RegionComparisonResponse`
  - Returns `regions_evaluated`, `pairwise_comparisons` with explainable geomorphological contrasts, and `methodological_notes`.

### 6. GET `/api/v1/routing/terrain-source`
Identifies the supporting elevation dataset, coverage envelope, and unsupported segments for a proposed route corridor.
- **Parameters:**
  - `start_lat`, `start_lon`: float
  - `dest_lat`, `dest_lon`: float
  - `target_scale_m`: float (optional)
- **Response Model:** `RouteTerrainSourceResponse`
  - Returns `routing_eligible`, `primary_terrain_product`, `primary_resolution_m`, `corridor_length_km`, and `unsupported_segments`.
