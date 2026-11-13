# MARS-X — Terrain Validation & Hazard Pipeline Architecture (Phase 5)

## 1. Subsystem Architecture
Phase 5 introduces a three-tiered scientific processing architecture:

```
┌────────────────────────────────────────────────────────┐
│                   MARS-X Backend                       │
├──────────────────────────┬─────────────────────────────┤
│   Validation Subsystem   │    Harmonization Engine     │
│  - DatasetLifecycleState │   - Horizontal CRS checks   │
│  - Evidence Verification │   - Vertical Datum checks   │
│  - Inventory Tracking    │   - Anti-Upsampling Guard   │
├──────────────────────────┴─────────────────────────────┤
│                Hazard Intelligence Engine              │
│  - Horn Gradient (3x3 with latitude-scaled cell dx/dy) │
│  - Local Relief (Elevation Range Δz)                   │
│  - Metric Roughness (Sample Standard Deviation σz)     │
│  - Discontinuity & Scarp Detection                     │
│  - Explainable Complexity Classification               │
└────────────────────────────────────────────────────────┘
```

## 2. API Endpoint Suite
- `GET /api/v1/terrain/validation`: Catalog-wide lifecycle verification statuses.
- `GET /api/v1/terrain/products/{id}/validation`: Individual product validation report with verification checks.
- `GET /api/v1/terrain/inventory`: MOLA 128 ppd tile repository inventory and spherical coverage.
- `GET /api/v1/terrain/inventory/adjacency`: Topological seam verification between adjacent tiles.
- `GET /api/v1/terrain/compatibility`: Pairwise CRS and vertical datum compatibility assessment.
- `GET /api/v1/terrain/hazards`: Point hazard evaluation from authentic ingested rasters.
- `GET /api/v1/terrain/hazards/metadata`: Algorithms, thresholds, and scientific limitations.
