# MARS-X — Mandatory Original Scientific Resource Policy & Repository Audit

**Document Reference:** `POL-SCI-001`  
**Effective Date:** 2026-11-14  
**Applies to:** All MARS-X Modules, Datasets, Visualizers, and APIs  
**Classification:** Planetary Scientific Data Governance Policy

---

## 1. Executive Summary & Policy Purpose

MARS-X (*Mars Analysis, Research & Site-selection eXplorer*) is designed for authentic mission planning, landing-site hazard assessment, and autonomous EVA traverse navigation on Mars. The validity of planetary engineering decisions depends entirely on the mathematical, physical, and cartographic accuracy of underlying topography.

This policy mandates that **all elevation, slope, roughness, and terrain data utilized by MARS-X must originate from authentic, peer-reviewed, and publicly auditable planetary science missions**.

The incorporation of synthetic elevation maps, procedural heightfields, uncalibrated mirrors, or mock digital elevation models into the runtime platform, data directory, or production visualization pipelines is strictly prohibited.

---

## 2. Approved Planetary Science Repositories

TOPOGRAPHIC and spatial data integrated into MARS-X are restricted to official releases from the following authorized space agency repositories:

1. **NASA Planetary Data System (PDS)**
   - *PDS Geosciences Node* (Washington University in St. Louis): Mars Global Surveyor (MGS) MOLA MEGDR and PEDR archives; MRO CRISM Targeted RDR hyperspectral volumes; Mars Express HRSC DTMs.
   - *PDS Cartography and Imaging Sciences Node* (USGS Astrogeology Science Center / JPL): Mars Reconnaissance Orbiter (MRO) Context Camera (CTX) and High Resolution Imaging Science Experiment (HiRISE) experiment records.
   - *PDS Atmospheres Node* (New Mexico State University): Mars 2020 MEDA derived environmental and meteorological time-series; MSL REMS calibrated atmospheric records.
2. **USGS Astrogeology Science Center (ASC) & USGS Publications Warehouse**
   - Analysis-ready regional and local DTMs processed with the USGS Integrated Software for Imagers and Spectrometers (ISIS) and NASA Ames Stereo Pipeline (ASP) on AWS Open Data (`astrogeo-ard`).
   - USGS Scientific Investigations Maps (e.g., Tanaka et al. 2014 Global Geologic Map of Mars, SIM 3292).
3. **ESA Planetary Science Archive (PSA)**
   - Mars Express (MEX) High Resolution Stereo Camera (HRSC) digital terrain models and ortho-images.
4. **Arizona State University (ASU) Mars Space Flight Facility**
   - Mars Global Surveyor TES Putzig & Mellon (2007) global thermal inertia maps; 2001 Mars Odyssey THEMIS controlled infrared mosaics.
5. **NASA 3D Resources (Science Mission Directorate)**
   - Official spacecraft CAD models and planetary visual representations (`github.com/nasa/NASA-3D-Resources`) for interactive visualization (strictly separated from numerical terrain DTMs).

---

## 3. Strict Prohibitions & Governance Constraints

### 3.1 Prohibition of Synthetic & Procedural Terrain
- **No Procedural Generators:** Algorithmic noise functions (Perlin noise, Simplex noise, fractional Brownian motion, Diamond-Square) must never be used to synthesize elevation, slope, or terrain roughness.
- **No Mock Elevation in Production:** Hand-crafted or synthetic elevation matrices must never be loaded by `TerrainDataEngine`, served by `/api/v1/terrain/*`, or rendered by frontend MapLibre layers.
- **Isolation of Test Fixtures:** If an isolated unit test requires a mock raster (e.g., testing out-of-memory or corrupt file exception handling), the fixture must be created dynamically in memory or stored under `tests/` with the explicit prefix `test_mock_` or `fixture_`. It must never enter `data/raw/` or `data/processed/`.

### 3.2 Prohibition of Resolution Misrepresentation
- **Display Resampling vs. Scientific Resolution:** Display interpolation (e.g., bilinear, bicubic, nearest-neighbor canvas scaling) is a visualization technique and does **not** create real terrain detail.
- **Mandatory Disclaimers:** All map viewports, inspection popups, and profile plots must explicitly distinguish between **Source Resolution** (e.g., 14.8 km/px for MOLA 4, 463 m/px for MOLA 128, 20 m/px for CTX) and **Display Sampling Ratio**.
- **No Fabricated Detail:** Oversampled views must be labeled `oversampled_resampled_visualization` and undersampled overviews labeled `undersampled_decimated_overview`.

### 3.3 Strict NoData & Planetary Boundary Integrity
- **NoData Preservation:** Stored NoData values (e.g., MOLA `32767`, CTX `-32768.0`) must never be clamped to zero or arbitrarily interpolated without explicit NoData flagging.
- **Planetary Latitude Bounds:** Queries outside physical Martian boundaries ($|\phi| > 90.0^\circ$) must immediately return structured `unsupported_out_of_bounds` errors.

---

## 4. Repository Data Provenance Audit

An independent filesystem and cryptographic checksum audit of all active and acquired datasets in `E:\MARS-X` was conducted as part of Phase 8.4 and Phase 8.5:

```
E:\MARS-X\data
├── raw
│   ├── ctx
│   │   ├── P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif (62,990,396 bytes)
│   │   └── P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif.aux.xml (1,061 bytes)
│   └── mola
│       ├── megt00n000hb.img (129,761,280 bytes)
│       ├── megt00n000hb.lbl (2,402 bytes)
│       ├── megt00n090hb.img (129,761,280 bytes)
│       ├── megt00n090hb.lbl (2,402 bytes)
│       ├── megt44n000hb.img (129,761,280 bytes)
│       ├── megt44n000hb.lbl (2,402 bytes)
│       ├── megt90n000cb.img (4,147,200 bytes)
│       └── megt90n000cb.lbl (2,402 bytes)
├── processed
│   └── mola
│       ├── mola_megt90n000cb_elevation.tif (4,152,782 bytes)
│       ├── mola_megt90n000cb_roughness.tif (4,152,782 bytes)
│       └── mola_megt90n000cb_slope.tif (4,152,782 bytes)
├── originals
│   ├── crism (Hyperspectral targeted RDR cubes & PDS labels)
│   ├── ctx (USGS controlled CTX stereo DTMs & MOLA residuals)
│   ├── geology (USGS SIM 3292 maps & XML metadata)
│   ├── hirise (USGS controlled 1m HiRISE DTMs & PDS labels)
│   ├── hrsc (MEX HRSC Level 4 DTMs)
│   ├── meda (Mars 2020 Perseverance Sol 1 pressure, humidity, TIRS)
│   ├── rems (MSL Curiosity Sol 1 ADR & RMD calibrated tables)
│   └── themis (MGS TES Putzig 2007 thermal inertia & THEMIS Night IR)
├── visualization
│   └── nasa_3d (Mars 2020 Perseverance, Ingenuity, Mars Globe texture)
└── manifests
    ├── acquisition_inventory.csv (32 authentic records with URLs & metadata)
    └── checksums.sha256 (32 cryptographic SHA-256 signatures)
```

### 4.1 Cryptographic Checksum Registry

| Product Identifier | File Path | File Size | SHA-256 Checksum | Origin Repository | Audit Result |
|---|---|---:|---|---|---|
| `mola-megdr-4-lbl` | `data/raw/mola/megt90n000cb.lbl` | 2,402 B | `1da984713ea6142129e9bf985e50ce56627be92efcfc9d2f2d91bb3a2b7f300c` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-megdr-4-img` | `data/raw/mola/megt90n000cb.img` | 4,147,200 B | `448f22033bc699cfc1a403ff250ff554c9ea9900c1737be704f47be73087bc97` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-00n000-lbl` | `data/raw/mola/megt00n000hb.lbl` | 2,402 B | `0334812316e6d11b3bc24fcbe00d14b4fb24e6df5b91b9795ff0d9aa2e5359a6` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-00n000-img` | `data/raw/mola/megt00n000hb.img` | 129,761,280 B | `ceabfe1c107bf4a72ad9b08f4cb123e4450bf08e0018a4a58409ee6107eb78ea` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-00n090-lbl` | `data/raw/mola/megt00n090hb.lbl` | 2,402 B | `e3575971168fc59b66bb9aee50b8ebae833a696bc27cbb3e85fa9d1c16cf6179` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-00n090-img` | `data/raw/mola/megt00n090hb.img` | 129,761,280 B | `4322442aeefd1421abefea3b6f2c7a917e82b7cfc8466bba78fb125d02633005` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-44n000-lbl` | `data/raw/mola/megt44n000hb.lbl` | 2,402 B | `32147326841d11ca76b668f182fc6d2e67f70bdf604ba04a9190240a6b5bf08e` | NASA PDS Geosciences | **AUTHENTIC** |
| `mola-128-44n000-img` | `data/raw/mola/megt44n000hb.img` | 129,761,280 B | `e18ffbc74187e14e1a0d8c0767252f9b87df3ee1252d431d10e6eb4d7990ff7a` | NASA PDS Geosciences | **AUTHENTIC** |
| `ctx-dtm-p21-009323` | `data/raw/ctx/P21_009323_..._dtm.tif` | 62,990,396 B | `a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2` | USGS ASC / NASA Ames | **AUTHENTIC** |
| `hrsc-dtm-h0018` | `data/originals/hrsc/h0018_0000_dt4.img` | 86,686,886 B | `32270e0a565624d3c9f8032c7ec616b85cc939be63bce3c2ee7cac1c9937a43e` | NASA PDS Geosciences / ESA | **AUTHENTIC (MD5 matched)** |
| `ctx-dtm-controlled` | `data/originals/ctx/T01_000893_..._adj.tif` | 6,526,946 B | `4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51` | USGS Astrogeology ARD | **AUTHENTIC** |
| `hirise-dtm-1m` | `data/originals/hirise/DTEEC_011635_..._A01.tif` | 65,126,266 B | `a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad` | USGS Astrogeology ARD | **AUTHENTIC** |
| `crism-trdr-cube` | `data/originals/crism/frt000027b2_01_if156l_trr3.img` | 1,682,944 B | `8bc9dda308c3cbfb7a25c65a20d0af7310a4c21192ef8c2733b69bf0a80f5cef` | NASA PDS Geosciences | **AUTHENTIC (MD5 matched)** |
| `tes-thermal-inertia` | `data/originals/themis/DBmap2007.tif` | 77,789,206 B | `0b2ca94b9414cd7c74e73f8df9ccb4a3c104bef24da932c4dc43fb246bc71a4b` | ASU Mars / PDS Geosciences | **AUTHENTIC** |
| `meda-sol0001-press` | `data/originals/meda/WE__0001_..._PS_P02.CSV` | 125,877 B | `600d8d11b26b2127ba66f90889e7ba5621a0b8b788146bf5bf72a02be2e0a16c` | NASA PDS Atmospheres | **AUTHENTIC** |
| `rems-sol0001-adr` | `data/originals/rems/RME_397535244ADR..._P9.TAB` | 114,152 B | `d5edd3d49198992bd36244b4b151b8850befce2d91b9c774cce72a40e254d194` | NASA PDS Atmospheres | **AUTHENTIC** |
| `geology-sim3292` | `data/originals/geology/sim3292_pamphlet.pdf` | 3,415,492 B | `18d3f0547e2f8cd82891f5adc454a8177ab62339c0b4a7f8370d8d2ecbce16ca` | USGS Publications | **AUTHENTIC** |

**Audit Conclusion:** 100% of the elevation, atmospheric, thermal, mineralogical, and geological products in `data/` match their original NASA PDS, USGS, and ESA source checksums. Zero synthetic datasets, mock DEMs, or unverified files exist in the repository.

---

## 7. Mandatory Separation of 3D Visualization Assets from Numerical Terrain Data

1. **Storage Isolation:** All 3D polygonal meshes, CAD objects, and visual texture assets must reside exclusively in `data/visualization/nasa_3d/`.
2. **Functional Boundary:** 3D visual models (e.g., `Mars_2020_Perseverance_Rover.glb`, `Ingenuity_Mars_Helicopter.glb`) are strictly for interactive hardware rendering and contextual astronaut visualization in web viewports.
3. **No Elevation Calculation from Visual Meshes:** The numerical elevation engine (`TerrainDataEngine`), slope calculator, roughness evaluator, and Marswalk pathfinding algorithms must **never** ingest or query polygonal visualization meshes. Numerical analysis is restricted to authentic raster DTMs (MOLA, CTX, HRSC, HiRISE).

---

## 5. Derivative Product Processing Standards

When generating derivative rasters (Cloud-Optimized GeoTIFFs, slope maps, surface roughness grids, or multi-resolution window views), engineers must adhere to the following standards:

1. **Deterministic Lineage:** The transformation script (e.g., `app/terrain/ingestion.py`) must record the source file, source checksum, resampling method, and parameters in the output GeoTIFF metadata tags.
2. **Preservation of Scientific Units:**
   - Elevation must remain in **metres relative to the MOLA Areoid**.
   - Slope must be calculated in **degrees ($0^\circ - 90^\circ$)** using Horn or Zevenbergen-Thorne planetary algorithms.
   - Roughness must represent **root-mean-square deviation (RMSD) or bidirectional relief (m)** over calibrated baseline windows.
3. **Cartographic Precision:**
   - Coordinate Reference Systems must adhere to IAU standards: `IAU:49900` (Planetocentric sphere $R=3,396,190\text{ m}$) or mission-specific local projections (e.g., `IAU:49910` Equirectangular for CTX).
   - Longitude conventions must strictly default to **East Longitudes ($0^\circ \text{ to } 360^\circ$)**.

---

## 6. Scientific Compliance Checklist for Future Releases

Prior to merging any code or updating datasets, the following verification checklist must be passed:

- [x] All raw datasets have accompanying PDS `.lbl` or USGS ISIS/ASP provenance metadata.
- [x] Source file SHA-256 checksums are registered in `TERRAIN_DATASET_PROVENANCE`.
- [x] No procedural noise or synthetic terrain generators exist in backend or frontend code.
- [x] Benchmark coordinates evaluate identically across raw binary data, backend API, and browser UI.
- [x] Tile seams exhibit natural physical continuity with zero artificial gaps or step artifacts.
- [x] Map UI explicitly exposes native dataset resolution vs. viewport display sampling regime.
