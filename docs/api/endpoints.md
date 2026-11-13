# MARS-X API Documentation

> REST API reference for the MARS-X backend (FastAPI).

**Base URL:** `http://localhost:8000`  
**API Version Prefix:** `/api/v1`

---

## Core System Endpoints

### `GET /` — Welcome
Returns service metadata and navigation endpoints.

### `GET /health` — Health Check
Lightweight liveness probe for orchestration and frontend status monitoring.

```json
{
  "status": "ok",
  "app": "MARS-X",
  "version": "0.1.0"
}
```

### `GET /api/v1/status` — Detailed Status
Returns uptime and subsystem readiness.

```json
{
  "status": "ok",
  "app": "MARS-X",
  "version": "0.1.0",
  "uptime_seconds": 12.4,
  "services": {
    "dataset_catalogue": "ok",
    "geospatial": "active",
    "terrain": "active_engine",
    "routing": "pending_engine",
    "science": "ready",
    "mission": "ready",
    "ai": "foundation_stub"
  }
}
```

---

## Dataset Catalogue Endpoints

### `GET /api/v1/datasets` — Dataset Catalogue
Returns the list of 11 verified NASA/USGS Mars dataset metadata records.

**Query Parameters:**
- `mission` *(optional, string)*: Filter by mission substring (e.g. `MRO`, `MSL`).

---

## Terrain Data Engine Endpoints (Phase 2)

### `GET /api/v1/terrain/datasets` — Numerical Terrain Datasets
Returns summary responses for all registered numerical elevation products (MOLA MEGDR, HRSC DTMs, HiRISE DTMs, CTX DTMs).
Strictly separates numerical DTM elevation grids from visual shaded relief imagery.

**Response `200 OK`:**
```json
[
  {
    "dataset_id": "mola-megdr",
    "name": "MOLA Mission Experiment Gridded Data Records (MEGDR)",
    "mission": "Mars Global Surveyor (MGS)",
    "instrument": "Mars Orbiter Laser Altimeter (MOLA)",
    "product_type": "Numerical Topographic DTM",
    "status": "registered",
    "elevation_unit": "metres relative to MOLA Areoid",
    "native_resolution_desc": "128 pixels/degree (~463 m/px at equator)",
    "is_numerical_dtm": true,
    "coverage": "Near-global (±88° Lat, 0°–360° East Lon)",
    "nodata_value_repr": "-32768 (int16)",
    "scientific_limitations": "Spatial resolution limited to ~463 m; polar gap beyond 88° latitude; microtopography (<100m) not resolved.",
    "provenance_source": "NASA Planetary Data System (PDS) Geosciences Node / Smith et al. (2001)"
  }
]
```

### `GET /api/v1/terrain/coverage` — Spatial Coverage & Footprint
Returns coordinate bounding box and surface percentage coverage.

**Query Parameters:**
- `dataset_id` *(required, string)*: Target dataset ID (e.g., `mola-megdr`, `hrsc-dtm`, `hirise-dtm`, `ctx-dtm`).

**Response `200 OK`:**
```json
{
  "dataset_id": "mola-megdr",
  "is_global": true,
  "lat_min": -88.0,
  "lat_max": 88.0,
  "lon_min": 0.0,
  "lon_max": 360.0,
  "crs": "IAU:49900",
  "total_area_approx_pct": 98.6,
  "notes": "Global cylindrical coverage excluding narrow 2° polar caps covered by polar stereographic megp products."
}
```

### `GET /api/v1/terrain/summary` — Full Terrain Product Profile
Returns comprehensive scientific profile, native resolution, vertical datum, and limitations.

**Query Parameters:**
- `dataset_id` *(required, string)*: Target dataset ID.

### `GET /api/v1/terrain/metadata` — Rasterio Header Inspection
Inspects raster dimensions, transform, CRS, pixel spacing, and NoData value.

**Query Parameters:**
- `dataset_id` *(required, string)*: Target dataset ID.
- `file_path` *(optional, string)*: Path to local raster file on disk.

*Zero-Fabrication Enforcement:* If the file has not yet been downloaded to local storage and `file_path` is not provided, the API returns `404 Not Found` with an explicit notice that un-downloaded raster headers cannot be fabricated.

---

## CORS & Interactive Documentation
- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
