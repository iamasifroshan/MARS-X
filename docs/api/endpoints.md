# MARS-X API Documentation

> REST API reference for the MARS-X backend (FastAPI).

**Base URL:** `http://localhost:8000`  
**API Version Prefix:** `/api/v1`

---

## Endpoints

### `GET /` — Welcome

Returns a welcome message with links to API documentation and key endpoints.

**Response** `200 OK`

```json
{
  "message": "Welcome to MARS-X API",
  "version": "0.1.0",
  "docs": "/docs",
  "endpoints": {
    "health": "/health",
    "status": "/api/v1/status",
    "datasets": "/api/v1/datasets"
  }
}
```

---

### `GET /health` — Health Check

Lightweight health check endpoint for monitoring and load balancers.

**Response** `200 OK`

```json
{
  "status": "ok",
  "app": "MARS-X",
  "version": "0.1.0"
}
```

**Pydantic Model:** `HealthResponse`

```python
class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
```

---

### `GET /api/v1/status` — Detailed Status

Returns detailed application status including uptime and service health.

**Response** `200 OK`

```json
{
  "status": "ok",
  "app": "MARS-X",
  "version": "0.1.0",
  "uptime_seconds": 142.7,
  "services": {
    "dataset_catalogue": "operational",
    "geospatial_engine": "not_configured",
    "terrain_analysis": "not_configured"
  }
}
```

**Pydantic Model:** `StatusResponse`

```python
class StatusResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    uptime_seconds: float
    services: Dict[str, str]
```

---

### `GET /api/v1/datasets` — Dataset Catalogue

Returns the full list of registered NASA/USGS Mars dataset metadata entries.

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `mission` | `string` | No | Filter datasets by mission name (case-insensitive substring match) |

**Response** `200 OK`

```json
[
  {
    "dataset_id": "mola-megdr",
    "name": "MOLA Mission Experiment Gridded Data Records",
    "mission": "Mars Global Surveyor",
    "instrument": "Mars Orbiter Laser Altimeter (MOLA)",
    "product_type": "Topographic grid (DTM)",
    "spatial_resolution": "463 m/px (1/128 degree)",
    "acquisition_date_range": "1999-2001",
    "geographic_footprint": "Global",
    "crs": "IAU:49900",
    "source_url": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
    "data_format": "PDS IMG / GeoTIFF",
    "coverage": "Global, 87.5°S to 87.5°N latitude",
    "processing_status": "registered",
    "scientific_limitations": "Accuracy degrades above ~87° latitude due to polar orbit geometry. Vertical accuracy ~1 m, horizontal ~100 m.",
    "description": "Global topographic dataset derived from over 600 million laser altimetry measurements by MOLA aboard Mars Global Surveyor."
  }
]
```

**Example: Filter by mission**

```
GET /api/v1/datasets?mission=reconnaissance
```

Returns only datasets from missions containing "reconnaissance" (e.g., Mars Reconnaissance Orbiter).

**Pydantic Model:** `DatasetMetadata`

```python
class ProcessingStatus(str, Enum):
    registered = "registered"
    available = "available"
    downloaded = "downloaded"
    validated = "validated"
    error = "error"

class DatasetMetadata(BaseModel):
    dataset_id: str
    name: str
    mission: str
    instrument: str
    product_type: str
    spatial_resolution: Optional[str] = None
    acquisition_date_range: Optional[str] = None
    geographic_footprint: Optional[str] = None
    crs: str
    source_url: str
    data_format: str
    coverage: str
    processing_status: ProcessingStatus
    scientific_limitations: Optional[str] = None
    description: str
```

---

## Error Responses

All error responses follow the standard FastAPI format:

**`422 Unprocessable Entity`** — Validation error

```json
{
  "detail": [
    {
      "loc": ["query", "mission"],
      "msg": "value is not a valid string",
      "type": "type_error.str"
    }
  ]
}
```

**`500 Internal Server Error`** — Server-side error

```json
{
  "detail": "Internal server error"
}
```

---

## CORS Configuration

The backend is configured with CORS middleware to allow the frontend development server to make cross-origin requests.

| Setting | Value |
|---|---|
| **Allowed Origins** | `http://localhost:3000` (configurable via `CORS_ORIGINS` env var) |
| **Allowed Methods** | All (`*`) |
| **Allowed Headers** | All (`*`) |

To configure CORS origins, set the environment variable:

```powershell
$env:CORS_ORIGINS = "http://localhost:3000,https://mars-x.example.com"
```

---

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
