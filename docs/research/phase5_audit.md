# MARS-X — Phase 5: Terrain Validation, Harmonization & Hazard Intelligence
## Preliminary Repository & Architecture Audit

**Date:** 2026-11-13  
**Auditor:** Senior Planetary Geospatial Engineer, Mars Remote-Sensing Scientist  
**Commit Baseline:** `c0210cb` on branch `master`

---

### 1. Verified Existing Functionality (Phase 1–4)

1. **Monorepo Foundation & Tests:**
   - FastAPI modular architecture with strict Pydantic schemas.
   - Comprehensive test suite in `backend/tests/`: 49 passing tests across datasets, health, MOLA ingestion, multi-resolution catalog, and terrain geometry.
   - Next.js 16.4.6 with Turbopack, MapLibre GL JS, Tailwind CSS, and strict TypeScript compilation (`npm run build` exits 0).
2. **Authentic Planetary Data Ingestion:**
   - Raw MOLA 4 ppd (`megt90n000cb.img`, 2,073,600 bytes) and label verified with SHA-256 (`25f16fb7...`).
   - Raw MOLA 128 ppd tile (`megt00n000hb.img`, 129,761,280 bytes) and label verified with SHA-256 (`f57274b5...`).
   - PDS3 label parser (`backend/app/terrain/pds_parser.py`) reading dimensions, map projection, byte order, scaling, and NoData.
   - Cloud Optimized GeoTIFF (COG) generation pipeline with internal tiling and overviews (`backend/app/terrain/cog_converter.py`).
   - Derived terrain rasters (`slope.tif`, `roughness.tif`) generated and georeferenced.
3. **Geodesy & Coordinate Systems:**
   - Mars reference spheroid $R = 3,396,190\text{ m}$, triaxial ellipsoid flattening $f \approx 0.005886$.
   - Explicit rejection of Earth Web Mercator (`EPSG:3857`).
   - Strict positive-East longitude ($[0^\circ, 360^\circ]$) and planetocentric latitude conventions.
4. **Multi-Resolution Terrain Catalog:**
   - Multi-tier DTM catalog (`backend/app/terrain/multi_resolution.py`) defining 4 operational tiers: Global Coarse (MOLA 4 ppd), Global Base (MOLA 128 ppd), Regional Medium (HRSC 50m, CTX 20m), and Local Tactical (HiRISE 1m).
   - Point coordinate footprint intersection and resolution comparison endpoints with anti-upsampling guarantees.

---

### 2. Missing Functionality & Gaps Identified for Phase 5

1. **Data Integrity & Valid Pixel Verification:**
   - The reported 100% valid coverage for `MEGT90N000CB` needs deep array-level verification against the raw binary file to confirm whether any `-32768` sentinels or edge artifacts exist.
2. **MOLA 128 ppd Tile Inventory:**
   - The full 16-tile global inventory is currently represented only by tile `megt00n000hb`. There is no formal inventory mechanism that catalogs all 16 tiles, their expected bounding boxes, file sizes, online PDS URLs, local download statuses, and exact spatial coverage percentage.
3. **Dataset Lifecycle & Validation States:**
   - Currently, dataset state transitions are simplistic (`registered`, `available`, `downloaded`, `validated`, `error`).
   - Need granular states: `registered` -> `discovered` -> `downloaded` -> `integrity_verified` -> `metadata_validated` -> `geospatially_validated` -> `scientifically_validated` -> `analysis_ready` (or `failed`, `unavailable`).
   - A registered dataset (such as HiRISE or HRSC) must be clearly distinguished from locally ingested and scientifically validated raster data.
4. **Rigorous CRS & Vertical Datum Harmonization:**
   - Products from different missions use slightly different ellipsoidal or spherical definitions (e.g. IAU 2000 vs IAU 2015 vs ISIS sphere $R=3396.19\text{ km}$).
   - While MOLA, HRSC, CTX, and HiRISE ostensibly reference "MOLA Areoid", HiRISE and CTX stereogrammetry DTMs frequently have residual vertical datum offsets ($\pm 1\text{--}5\text{ m}$) unless tied via iterative closest point (ICP) to MOLA tracks.
   - An explicit compatibility matrix (`compatible`, `compatible_with_documented_transformation`, `incompatible`, `unknown`) must be enforced before combining or comparing datasets.
5. **Terrain Hazard Intelligence Engine:**
   - Phase 3 generated rudimentary slope and roughness GeoTIFFs.
   - Phase 5 requires a configurable terrain hazard service calculating:
     - Slope (Horn / Zevenbergen-Thorne gradient with latitude-dependent metric cell dimensions).
     - Local Relief (elevation range $\Delta z$ within configurable physical neighborhoods in metres).
     - Physical Roughness (standard deviation $\sigma_z$ in metric windows).
     - Terrain Discontinuities (candidate scarp, cliff, and crater rim detection).
     - Data Confidence Layer (tracking source validation, native resolution, and NoData proximity).
     - Explainable Terrain Complexity Classification (without claiming astronaut safety or EVA clearance).
6. **API & Frontend Interface:**
   - Endpoints for validation summaries, tile inventory, compatibility assessments, and hazard metadata/queries.
   - Dashboard extensions: Dataset Validation Panel, MOLA Coverage Inspector, Product Compatibility Inspector, and Hazard Layer Controls.

---

### 3. Scientific Uncertainties & Architectural Risks

1. **HiRISE & CTX Local Offsets:**
   - Non-MOLA DTMs cannot be assumed to have zero vertical offset from the global MOLA areoid. An uncertainty margin must be documented and reported in compatibility assessments.
2. **Polar Singularity in Slope Calculations:**
   - At high latitudes ($\phi \to \pm 90^\circ$), metric distance per degree of longitude approaches 0 ($\Delta x = R \cos\phi \Delta\lambda \to 0$). Slope algorithms must protect against division by zero and extreme metric distortion near the poles.
3. **NoData Propagation:**
   - Boundary NoData must never be filled with 0 elevation or treated as flat safe ground. In hazard calculations, windows overlapping NoData must report `insufficient_data` or propagate NaN/NoData.
4. **Computational Performance:**
   - Hazard calculations on massive 128 ppd tiles ($5632 \times 11520$ = 64.8M pixels) must not be run synchronously on un-cached requests. Windowed sub-array processing or pre-processed multi-resolution hazard rasters must be utilized.

---

### 4. Files Planned for Creation / Modification

#### New Backend Modules:
- `backend/app/terrain/validation.py`: Dataset lifecycle states, state machines, and verification rules.
- `backend/app/terrain/inventory.py`: Reproducible MOLA 128 ppd tile inventory, catalog, and spatial coverage calculator.
- `backend/app/terrain/harmonization.py`: Strict horizontal and vertical CRS compatibility engine.
- `backend/app/terrain/hazard_engine.py`: Terrain hazard metrics (slope, relief, roughness, discontinuities, confidence, complexity classification).
- `backend/tests/test_phase5_validation.py`: Comprehensive test suite for Phase 5.

#### Modified Backend Modules:
- `backend/app/routers/terrain.py`: Adding `/validation`, `/inventory`, `/compatibility`, `/hazards`, `/hazards/metadata`, `/products/{id}/validation`.
- `backend/app/terrain/models.py`: Pydantic models for validation states, tile inventory, compatibility results, and hazard metrics.

#### New Documentation:
- `docs/research/phase5_audit.md` (this file)
- `docs/research/phase5_scientific_validation.md`
- `docs/research/phase5_data_inventory.md`
- `docs/research/phase5_hazard_methodology.md`
- `docs/architecture/phase5_terrain_pipeline.md`

#### Modified Frontend Modules:
- `frontend/src/lib/types.ts`: TypeScript models for validation, inventory, compatibility, and hazard indicators.
- `frontend/src/lib/api.ts`: API clients for Phase 5 endpoints.
- `frontend/src/components/panels/TerrainAnalysis.tsx`: Adding Validation Panel, Tile Inventory Inspector, Compatibility Inspector, and Hazard Controls.
