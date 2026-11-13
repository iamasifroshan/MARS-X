# MARS-X — Phase 6: Initial Audit & Feasibility Assessment

**Audit Date:** 2026-11-13  
**Auditor:** Senior Planetary Geospatial Engineer, Autonomous Navigation Researcher, Terrain-Analysis Scientist  
**Baseline Commit:** `17a0e6c8658512a4ae75e8b4f603373ba011f142` (Phase 5.1 on branch `master`)

---

## 1. Verified Existing Architecture & Reusable Modules

The MARS-X codebase provides a solid, modular foundation for local terrain-constrained pathfinding:

1. **Planetary Geodesy & CRS Constraints (`backend/app/geospatial.py`):**
   - Mars reference spheroid $R = 3,396,190\text{ m}$, triaxial ellipsoid flattening $f \approx 0.005886$.
   - Positive-East longitude convention ($0^\circ\text{ to }360^\circ$).
   - Planetocentric vs. planetographic latitude conversions.
   - Strict rejection of Earth Web Mercator (`EPSG:3857`).
2. **Dataset Validation & Lifecycle State Machine (`backend/app/terrain/validation.py`):**
   - Progressive validation states: `registered` $\to$ `discovered` $\to$ `downloaded` $\to$ `integrity_verified` $\to$ `metadata_validated` $\to$ `geospatially_validated` $\to$ `scientifically_validated` $\to$ `analysis_ready`.
   - Distinguishes catalog metadata from on-disk raster availability.
3. **MOLA MEG128 Tile Inventory (`backend/app/terrain/inventory.py`):**
   - Separates theoretical coverage ($99.94\%$) from downloaded on-disk coverage ($8.68\%$).
   - Topological boundary adjacency checks.
4. **CRS & Vertical Datum Harmonization (`backend/app/terrain/harmonization.py`):**
   - Validates horizontal and vertical reference compatibility before comparison or fusion.
   - Anti-upsampling protections preventing coarse terrain interpolation from masquerading as high-resolution detail.
5. **Terrain Hazard Intelligence Engine (`backend/app/terrain/hazard_engine.py`):**
   - Horn (1981) $3 \times 3$ gradient with latitude-scaled metric cell spacing ($dx = R \cos\phi\, d\lambda$, $dy = R\, d\phi$).
   - Metric local relief ($\Delta z$) and roughness ($\sigma_z$).
   - Polar geodesy cutoff: $|\phi| > 85^\circ$ rejected from equirectangular approximations.
   - Transparent Boolean terrain complexity classification (`low`, `moderate`, `high`, `extreme`, `insufficient_data`).

---

## 2. Authentic Raster Verification (`megt00n000hb`)

A cryptographic and structural audit of the primary high-resolution numerical raster was conducted:
- **Raw File:** `data/raw/mola/megt00n000hb.img`
- **Label File:** `data/raw/mola/megt00n000hb.lbl`
- **File Size:** $129,761,280\text{ bytes}$ ($123.75\text{ MB}$)
- **Computed SHA-256:** `f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75` (matches PDS manifest identically).
- **Label Dimensions:** 5,632 lines $\times$ 11,520 samples.
- **Data Type:** Big-endian 16-bit signed integer (`MSB_INTEGER`, `>i2`).
- **Native Post-Spacing:** $0.0078125^\circ/\text{px}$ ($\approx 463.08\text{ m/px}$ at Mars equator).
- **Spatial Coverage Footprint:**
  - Latitude: $[-44.0^\circ, 0.0^\circ]$ (Southern Hemisphere, quadrant 00n)
  - Longitude: $[0.0^\circ, 90.0^\circ\text{E}]$
- **Elevation Units & Datum:** Heights in metres relative to the Goddard Mars potential model GMM3 areoid to degree 50.
- **Valid Data Mask:** Verified $100\%$ valid pixels ($64,880,640$ pixels, zero NoData sentinels within the tile).
- **Validation Status:** `scientifically_validated` / `analysis_ready`.

---

## 3. Strict Coverage Footprint for Route Planning

The prototype will **strictly refuse** to plan routes outside:
$$\text{Latitude} \in [-44.0^\circ, 0.0^\circ], \quad \text{Longitude} \in [0.0^\circ, 90.0^\circ\text{E}]$$
Requests with start or destination coordinates outside this bounding box, or path segments traversing unvalidated terrain, will fail with explicit, descriptive error codes.

---

## 4. Planned Phase 6 Implementation

1. **Data Model (`backend/app/routing/route_models.py`):**
   - Pydantic models for mission routing requests and comprehensive route results.
   - Strict validation of coordinates, maximum slope, algorithm choice, and cost weights.
2. **Terrain Grid Builder (`backend/app/routing/grid_builder.py`):**
   - `np.memmap` windowed extraction around requested start/destination bounding box.
   - Metric pixel dimensions ($dx, dy$) calculated per latitude.
   - Start and destination snapping to nearest valid pixel centers (with max snap threshold).
3. **Cost Surface (`backend/app/routing/cost_surface.py`):**
   - Physical distance edge base cost $L$.
   - Multiplicative penalty function: $C = L \cdot (1 + w_s f_s + w_r f_r + w_l f_l + w_c f_c)$.
   - Impassable hard constraints: slope $> \text{max\_slope}$, NoData, exclusion zones.
4. **Pathfinding Algorithms (`backend/app/routing/astar.py` and `dijkstra.py`):**
   - 4-direction and 8-direction movement.
   - Diagonal corner-cutting prevention.
   - Admissible, consistent geodesic lower-bound heuristic for A*.
   - Dijkstra implementation on the identical graph and cost function for ground-truth comparison.
5. **Route Validation & Metrics (`backend/app/routing/route_validator.py`, `route_metrics.py`):**
   - Independent verification of path connectivity, slope bounds, elevation profile, and distance.
   - Detailed explainability notes and scientific disclaimers.
6. **API Endpoints (`backend/app/routers/routing.py`):**
   - `POST /api/v1/routes/plan`
   - `POST /api/v1/routes/compare`
   - `GET /api/v1/routes/metadata`
7. **Frontend Mission Control (`frontend/src/components/panels/RoutePlanning.tsx`):**
   - Interactive Marswalk coordinate selection (with preset geological landmarks inside the footprint: Sinus Meridiani, Mawrth Vallis corridor, Schiaparelli Crater rim).
   - Algorithm selection (A*, Dijkstra, Compare Both).
   - Cost weight sliders and max slope constraints.
   - Comparison metrics table, elevation profile chart, and scientific warning.

---

## 5. Scientific Limitations & Safety Principles

- **No Astronaut Safety Claims:** All generated traverses represent candidate paths on a mathematical terrain-cost surface. They do NOT evaluate spacesuit flexibility, life-support consumable depletion, metabolic energy expenditure, or sub-meter boulder fields.
- **Regional Scale:** $463\text{ m/pixel}$ post-spacing has a Nyquist feature limit of $\sim 1.15\text{ km}$. Features smaller than this threshold are not resolved.
