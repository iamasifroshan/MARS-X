# MARS-X — Live Browser Verification Log (Phase 8.3.2)

**Execution Date:** 2026-11-14  
**Environment:** Next.js 16.4.6 (Port 3005, Task 3141) & FastAPI / Uvicorn (Port 8000, Task 3007)  
**Browser Engine:** Google Chrome Headless (1920x1080, 24-bit color, GPU disabled)  
**Repository Branch:** `master`  
**Baseline Commit:** `c02c677`

---

## 1. Verification Session Inventory

| ID | Timestamp (UTC) | Target URL / Viewport | Feature Verified | Screenshot Artifact | Status |
|---|---|---|---|---|---|
| BV-01 | 2026-11-14T08:08:44Z | `http://localhost:3005/?lat=0.0&lon=0.0&zoom=2` | Full Console & Global MOLA 4 ppd Basemap | `01_global_mars_console.png` | PASS |
| BV-02 | 2026-11-14T08:08:49Z | `http://localhost:3005/?lat=10.0&lon=20.0&zoom=4` | MOLA 128 ppd Regional Coverage & Seams | `02_mola128_regional_coverage.png` | PASS |
| BV-03 | 2026-11-14T08:08:54Z | `http://localhost:3005/?lat=-4.6&lon=66.317&zoom=7` | USGS CTX DTM Local Footprint & Texture | `03_ctx_dtm_local_coverage.png` | PASS |
| BV-04 | 2026-11-14T08:08:58Z | `http://localhost:3005/?drawer=coords&lat=-2.000&lon=5.000&zoom=7` | Elevation Inspector: Sinus Meridiani (-909 m) | `04_inspector_sinus_meridiani.png` | PASS |
| BV-05 | 2026-11-14T08:09:03Z | `http://localhost:3005/?drawer=coords&lat=18.650&lon=226.200&zoom=5` | Elevation Inspector: Olympus Mons (+20,009 m) | `05_inspector_olympus_mons.png` | PASS |
| BV-06 | 2026-11-14T08:09:07Z | `http://localhost:3005/?drawer=coords&lat=-4.600&lon=66.317&zoom=8.5` | Elevation Inspector: Tyrrhena CTX (+2,189.49 m) | `06_inspector_tyrrhena_ctx.png` | PASS |
| BV-07 | 2026-11-14T08:09:12Z | `http://localhost:3005/?tab=profile` | Great-Circle Profile Suite (4 presets + chart) | `07_elevation_profile_suite.png` | PASS |

---

## 2. Detailed Inspection Results

### BV-01: Full Global Mars Console
- **Map Center:** 0.0000°N, 0.0000°E (Zoom 2)
- **Visual Display:** Global shaded-relief elevation map rendered from `mola-megdr-4` (native resolution 4 ppd, 14.8 km/px at equator).
- **Overlays:** MOLA 128 tile boundary footprints rendered in emerald dashed borders (`megt00n000hb`, `megt44n000hb`, `megt00n090hb`). CTX DTM boundary footprint rendered in amber dashed border (`ctx-dtm-p21-009323`).
- **Telemetry Bar:** Displays active CRS `IAU:49900 (Planetocentric, 0–360°E)`, Datum `Mars2000 Sphere (R = 3,396,190 m)`, Backend status `CONNECTED (127.0.0.1:8000)`.

### BV-02: MOLA 128 ppd Regional Coverage & Tile Seams
- **Map Center:** 10.0000°N, 20.0000°E (Zoom 4)
- **Visual Display:** High-resolution multi-tile window rendered seamlessly across the boundary of `megt00n000hb` (0°–44°N, 0°–90°E) and adjacent areas.
- **Seam Continuity:** Verified visual and numerical continuity across the 0° equator seam and 90°E seam without voids, missing pixel lines, or coordinate jumps.

### BV-03: USGS CTX DTM Local Footprint & Texture
- **Map Center:** -4.6000°N, 66.3170°E (Zoom 7)
- **Visual Display:** High-resolution local CTX DTM window rendered from `ctx-dtm-p21-009323` (native resolution 20.01 m/px).
- **Coordinate System:** Native Equirectangular projected raster (IAU:49910, standard parallel -4°). Displayed without distortion or spatial misalignment against regional MOLA base.

### BV-04: Elevation Inspector — Sinus Meridiani
- **Coordinates:** -2.0000°N, 5.0000°E
- **Selected Dataset:** `mola-128-megt00n000hb`
- **Native Resolution:** 128 ppd (~463 m/px)
- **Stored Raw Value:** -909.00 m
- **UI Display Value:** `-909.00 m`
- **Sampling Regime:** `nearest` pixel-center lookup
- **Validation Status:** Verified exact match between raw raster array (`megt00n000hb.img`), live API response (`-909.0`), and browser display.

### BV-05: Elevation Inspector — Olympus Mons
- **Coordinates:** +18.6500°N, 226.2000°E
- **Selected Dataset:** `mola-megdr-4`
- **Native Resolution:** 4 ppd (~14.8 km/px)
- **Stored Raw Value:** +20,009.00 m
- **UI Display Value:** `+20009.00 m`
- **Sampling Regime:** `nearest` pixel-center lookup
- **Validation Status:** Verified exact match between global MOLA raster (`elevation.tif`), live API response (`+20009.0`), and browser display.

### BV-06: Elevation Inspector — Tyrrhena Terra CTX DTM
- **Coordinates:** -4.6000°N, 66.3170°E
- **Selected Dataset:** `ctx-dtm-p21-009323`
- **Native Resolution:** 20.01 m/px
- **Stored Raw Value:** +2,189.485107 m (float32)
- **UI Display Value:** `+2189.49 m`
- **Sampling Regime:** Projected coordinate transform `IAU:49910` $\to$ nearest pixel $(r=1737, c=844)$.
- **Validation Status:** Verified exact match between CTX GeoTIFF, live API response (`+2189.49`), and browser display.

### BV-07: Elevation Profile Suite
- **Tab Activated:** Great-Circle Elevation Profile
- **Presets Tested:**
  1. Valles Marineris Trans-Canyon (2,168 km, 50 samples)
  2. Olympus Mons Caldera-to-Plains (1,012 km, 50 samples)
  3. Gale Crater Rim-to-Mount Sharp (55 km, 50 samples)
  4. Tyrrhena Terra CTX High-Res Transect (25 km, 50 samples)
- **Metrics Displayed:** Total distance (spherical great-circle $R=3,396,190\text{ m}$), Min elevation, Max elevation, Net relief, Max slope gradient, Resolution regime breakdown (MOLA 4 vs MOLA 128 vs CTX).
- **Chart:** Interactive SVG profile chart rendering elevation curve, sampling markers, and terrain gradient fills.

---

## 3. Live API Responses Associated with Browser Tests

All live API queries executed during this verification session were recorded in `docs/research/phase8_3_2_evidence/api_captures.json`.
- `health`: HTTP 200, status: `"healthy"`, version: `"0.1.0"`.
- `catalog`: HTTP 200, 5 datasets registered with authentic metadata, checksums, and resolutions.
- `elevation/point` (Sinus Meridiani): HTTP 200, elevation: `-909.00`, dataset: `"mola-128-megt00n000hb"`.
- `elevation/point` (Olympus Mons): HTTP 200, elevation: `20009.00`, dataset: `"mola-megdr-4"`.
- `elevation/point` (Tyrrhena CTX): HTTP 200, elevation: `2189.49`, dataset: `"ctx-dtm-p21-009323"`.
- `render/window/metadata` (CTX): HTTP 200, native_resolution_m: `20.0128`, sampling_ratio: `0.024`, regime: `"undersampled_decimated_overview"`.
- `elevation/profile` (all 4 presets): HTTP 200 with complete distance, elevation, slope, and dataset attribution arrays.
