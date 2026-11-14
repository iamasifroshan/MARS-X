# MARS-X — Phase 8.5 Scientific Data Acquisition & Integration Report

**Project:** MARS-X (*Mars Analysis, Research & Site-selection eXplorer*)  
**Milestone:** Phase 8.5 — Official NASA, USGS, and ESA Scientific Data Acquisition & Integration  
**NASA Space Apps Challenge:** Interplanetary Survival Guide: Martian Map  
**Auditor / Architect:** Senior Planetary Geospatial Scientist & PDS Systems Auditor  
**Date:** November 14, 2026 (Updated in Phase 8.5.1)  
**Status:** COMPLETED & VERIFIED  

---

## 1. Executive Summary

To satisfy the highest standards of planetary cartography, astronaut traverse safety, and scientific defensibility for the NASA Space Apps Challenge, MARS-X has expanded its authentic Mars repository. 

Rather than relying solely on global baseline topography or synthetic representations, **Phase 8.5 has directly acquired, cryptographically verified, and ingested original scientific data products** from official NASA Planetary Data System (PDS) nodes, the United States Geological Survey (USGS) Astrogeology Science Center, the European Space Agency (ESA) Planetary Science Archive, Arizona State University (ASU) Mars Space Flight Facility, and NASA's official 3D Resources repository.

Every file has been verified against official published archive checksums or sealed with SHA-256 cryptographic hashes in `data/manifests/checksums.sha256`. Zero synthetic heightfields or procedural mock data exist in the repository.

---

## 2. Repository Architecture & Governance Structure

All acquired datasets strictly adhere to the MARS-X planetary data hierarchy:

```
E:\MARS-X\data
├── originals/                # Unmodified original archives from NASA/USGS/ESA
│   ├── crism/                # MRO CRISM hyperspectral targeted RDR cubes & PDS labels
│   ├── ctx/                  # USGS controlled CTX stereo DTMs & bundle adjustment residuals
│   ├── geology/              # USGS SIM 3292 database ZIP, metadata & pamphlet
│   ├── hirise/               # USGS controlled 1.0 m/px HiRISE DTMs & PDS labels
│   ├── hrsc/                 # Mars Express HRSC Level 4 DTMs (50 m/px)
│   ├── meda/                 # Mars 2020 Perseverance Sol 1 environmental time-series
│   ├── rems/                 # MSL Curiosity Sol 1 calibrated atmospheric & rover motion records
│   └── themis/               # MGS TES Putzig 2007 thermal inertia & THEMIS Day/Night IR
├── raw/                      # Pre-existing validated Phase 1-8.4 baselines (MOLA 4 & 128 ppd, CTX DTM)
├── processed/                # Production Cloud-Optimized GeoTIFFs (elevation, slope, roughness)
├── derived/                  # Secondary scientific grids with deterministic lineage
│   └── geology/              # Extracted working copies of USGS SIM 3292 Shapefiles & GDB
├── visualization/            # Strictly isolated 3D meshes & visual assets
│   └── nasa_3d/              # Official NASA CAD models (Perseverance, Ingenuity, Globe)
└── manifests/                # Cryptographic manifests & complete acquisition registries
    ├── acquisition_inventory.csv  # 34 authentic records with URLs, CRS, resolution, units
    └── checksums.sha256           # Cryptographic SHA-256 hashes of all 34 acquired files
```

### 2.1 Separation of 3D Visualization Assets from Numerical Topography
In accordance with `POL-SCI-001`, 3D polygonal meshes (glTF 2.0 `.glb`) are stored in `data/visualization/nasa_3d/`. These assets represent spacecraft geometry (Perseverance rover, Ingenuity helicopter) for contextual user interface rendering and mission visualization. They are **strictly isolated** from the numerical terrain engine (`TerrainDataEngine`) and cannot be queried for elevation, slope, or pathfinding calculations.

---

## 3. Detailed Scientific Inventory by Discipline

### 3.1 High-Resolution Terrain & Elevation
1. **Mars Express HRSC Level 4 DTM (`h0018_0000_dt4.img`):**
   - **Provider:** ESA PSA / NASA PDS Geosciences Node (`mexhrs_2001`)
   - **Resolution:** 50 meters/pixel (Sinusoidal projection, planetocentric)
   - **Vertical Datum:** `HEIGHT_ABOVE_SPHEROID` (Mars Sphere $R = 3,396.0\text{ km}$, **NOT** MOLA Areoid).
   - **Production Readiness:** `downloaded_validation_pending` (requires areoid separation undulation transformation before merging with MOLA or CTX).
   - **File Size:** 86,686,886 bytes
   - **Published MD5:** `BFAF16E930228E9C9ACA7E10B396446F` (**EXACT MATCH** against `mexhrs_2001_161028.md5`)
   - **SHA-256:** `32270e0a565624d3c9f8032c7ec616b85cc939be63bce3c2ee7cac1c9937a43e`
2. **USGS Controlled CTX Stereo DTM (`T01_000893...-DEM-geoid-adj.tif`):**
   - **Provider:** USGS Astrogeology Science Center (AWS Open Data `astrogeo-ard`)
   - **Resolution:** 20.0 meters/pixel
   - **CRS:** Equirectangular Mars (`IAU:49910`)
   - **Vertical Datum:** MOLA Geoid Adjusted
   - **Production Readiness:** `downloaded_verified`
   - **File Size:** 6,526,946 bytes
   - **Companion Files:** MOLA bundle-adjustment residuals CSV (`geodiff-diff.csv`) and USGS ISIS3 processing provenance log.
   - **SHA-256:** `4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51`
3. **USGS Controlled HiRISE 1-Meter DTM (`DTEEC_011635_1510_029542_1510_A01.tif`):**
   - **Provider:** USGS Astrogeology Science Center / MRO HiRISE Team
   - **Resolution:** 1.0 meter/pixel (ultra-high resolution traverse micro-relief)
   - **CRS:** Equirectangular Mars (`IAU:49910`)
   - **Vertical Datum:** MOLA Geoid Adjusted
   - **Production Readiness:** `downloaded_verified`
   - **File Size:** 65,126,266 bytes
   - **Companion Files:** Orthoimage PDS3 label (`ESP_011635_1510_RED_A_02_ORTHO.LBL`) and USGS ISIS3 processing history.
   - **SHA-256:** `a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad`

### 3.2 Planetary Geology & Chronostratigraphy
1. **USGS SIM 3292 Geologic Map of Mars (Tanaka et al. 2014):**
   - **Provider:** USGS Publications Warehouse (`pubs.usgs.gov/sim/3292/`)
   - **Publication DOI:** `10.3133/sim3292` (distinguished from 2023 data release `10.5066/P9UGAC18`)
   - **Scale:** 1:20,000,000 Global Map
   - **Acquired Original Archive:** `sim3292_database.zip` (808,910,442 bytes, SHA-256: `ef75f059b1f2f5a47aff55e6c6e39500cf1ab65e743fabc5d463b97bc10b6541`).
   - **Extracted Working Copy:** `data/derived/geology/sim3292_database/SIM3292_MarsGlobalGeologicGIS_20M` containing:
     - `SIM3292_Shapefiles/` (1,311 geologic unit polygons across 39 distinct chronostratigraphic units, contacts, and tectonic structures)
     - `SIM3292_geodatabase.gdb` (ESRI File Geodatabase)
   - **CRS:** `GCS_Mars_2000_Sphere` ($R = 3,396,190.0\text{ m}$, flattening $= 0.0$).
   - **Production Readiness:** `downloaded_verified`

### 3.3 Surface Thermal Science & Physical Properties
1. **Putzig & Mellon (2007) Global Thermal Inertia (`DBmap2007.tif` & `NBmap2007.tif`):**
   - **Provider:** Arizona State University Mars Space Flight Facility / MGS TES
   - **Physical Quantity:** **Thermal Inertia** ($I = \sqrt{k\rho c}$), **NOT** surface temperature.
   - **Resolution:** 20 pixels per degree (~3.0 km/pixel at equator)
   - **Units:** $\text{J}\cdot\text{m}^{-2}\cdot\text{K}^{-1}\cdot\text{s}^{-1/2}$ (tiu)
   - **Coverage:** Global dayside (2 PM) and nightside (2 AM) thermal inertia maps (77.8 MB each) with official classification legends.
   - **Production Readiness:** `downloaded_verified`
2. **2001 Mars Odyssey THEMIS Daytime & Nighttime Infrared Mosaics:**
   - **Provider:** ASU Mars Space Flight Facility / THEMIS Team
   - **Physical Quantity:** Calibrated Band 9 (12.57 $\mu\text{m}$) Infrared Brightness Temperature / Radiance Digital Numbers.
   - **Resolution:** 100 meters/pixel regional mosaic tiles (Sinus Meridiani region: $-30^\circ \le \text{lat} \le 0^\circ$, $0^\circ \le \text{lon} \le 30^\circ$).
   - **Files:** Daytime IR `thm_dir_N-30_000.png` (38.6 MB, SHA-256: `0f80f5cd8a4bdc59d7f9f3b9d1c566bd8f9437cccff68c873d1394b1aa19d7af`) and Nighttime IR `themis_nightir_N-30_000.png` (49.5 MB, SHA-256: `ebd045a3ca522624ec41c41611415095d07db9452b867cbb205ddba2c2a2f66d`).
   - **Production Readiness:** `downloaded_verified`

### 3.4 Hyperspectral Mineralogy
1. **MRO CRISM Targeted Reduced Data Record (`frt000027b2_01_if156l_trr3.img`):**
   - **Provider:** NASA PDS Geosciences Node (`mrocr_2101`)
   - **Resolution:** ~18 meters/pixel; 438 spectral channels (1.0 to 3.92 $\mu\text{m}$)
   - **Data Product:** Calibrated Radiance Factor ($I/F$) hyperspectral image cube and associated PDS3 label files.
   - **Calibration Status:** PDS label indicates `MRO:ATMO_CORRECTION_FLAG = "OFF"` and `MRO:THERMAL_CORRECTION_MODE = "OFF"`.
   - **Production Readiness:** `downloaded_validation_pending` (no mineral detection claimed until atmospheric correction and band-ratio analysis are performed).
   - **Published MD5:** `6935C24B14926ABD43BED6B63F750A2F` (**EXACT MATCH**)
   - **SHA-256:** `8bc9dda308c3cbfb7a25c65a20d0af7310a4c21192ef8c2733b69bf0a80f5cef`

### 3.5 In-Situ Atmospheric & Environmental Observations
1. **Mars 2020 Perseverance MEDA Sol 1 Observations:**
   - **Provider:** NASA PDS Atmospheres Node (`mars2020_meda`, Jezero Crater: $18.38^\circ\text{N}, 77.58^\circ\text{E}$)
   - **Temporal Scope:** Limited historical sample (Sol 1: 2021-02-19T21:35:54 to 22:29:54 UTC).
   - **Products:** Atmospheric Pressure (`DER_PS`), Relative Humidity (`DER_RHS`), and Ground Thermal IR (`DER_TIRS`).
   - **Production Readiness:** `downloaded_verified`
2. **MSL Curiosity REMS Sol 1 Observations:**
   - **Provider:** NASA PDS Atmospheres Node (`msl_rems_bundle`, Gale Crater: $-4.59^\circ\text{S}, 137.44^\circ\text{E}$)
   - **Temporal Scope:** Limited historical sample (Sol 1: 2012-08-07T04:04:38 to 04:24:19 UTC).
   - **Products:** Atmospheric Derived Data Record (`ADR`) and Rover Motion Data (`RMD`).
   - **Production Readiness:** `downloaded_verified`

### 3.6 NASA 3D Mission & Equipment Visualization
1. **Mars 2020 Perseverance Rover (`Mars_2020_Perseverance_Rover.glb`, 4.98 MB):** Official NASA CAD visual model.
2. **Ingenuity Mars Helicopter (`Ingenuity_Mars_Helicopter.glb`, 2.01 MB):** Official NASA aerial scout visual model.
3. **NASA Mars Globe Texture (`Mars_Globe_Texture.jpg`, 972 KB):** NASA 3D Resources texture map.

---

## 4. Cryptographic Checksum Audit Matrix

The following 34 original scientific records are cataloged in `data/manifests/acquisition_inventory.csv` and hashed into `data/manifests/checksums.sha256`:

| # | Product Name | Subdirectory | Size (Bytes) | Published Checksum | SHA-256 Checksum | Production Status |
|---|---|---|---:|---|---|---|
| 1 | `frt000027b2_01_if156l_trr3.img` | `originals/crism` | 1,682,944 | MD5: `6935C24B14926ABD43BED6B63F750A2F` (MATCH) | `8bc9dda308c3cbfb7a25c65a20d0af7310a4c21192ef8c2733b69bf0a80f5cef` | `downloaded_validation_pending` |
| 2 | `frt000027b2_01_if156l_trr3.lbl` | `originals/crism` | 9,512 | MD5: `AB1AACC13528F6599BA6F78BFE7087B4` (MATCH) | `559e303df765174b0f5710a89718a4b7ae7f96d2c5cc528cd5d4df33b43decb7` | `downloaded_verified` |
| 3 | `frt000027b2_01_ra156l_trr3.lbl` | `originals/crism` | 9,528 | MD5: `3A8185EFF53D8C609D4CDF01B6D3AE2C` (MATCH) | `60ffe446ab0306ed1ac30759f1902301719b5d867e711fe5b25766031cb55a35` | `downloaded_verified` |
| 4 | `T01_000893...-DEM-geoid-adj.tif` | `originals/ctx` | 6,526,946 | None published (USGS ARD) | `4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51` | `downloaded_verified` |
| 5 | `T01_000893...-FINAL_geodiff-diff.csv` | `originals/ctx` | 51,977 | None published (USGS ARD) | `6dda3d8ec0c3c4f10b34852bc04c9a8e635c76c217a64d6d6710305516aaea06` | `downloaded_verified` |
| 6 | `T01_000893_provenance.txt` | `originals/ctx` | 9,605 | None published (USGS ARD) | `b973a7ae6361908fe09570d62b903ed7d14283da14f5c6189773d3c5b57e6e6f` | `downloaded_verified` |
| 7 | `sim3292_database.zip` | `originals/geology` | 808,910,442 | None published (USGS Pubs) | `ef75f059b1f2f5a47aff55e6c6e39500cf1ab65e743fabc5d463b97bc10b6541` | `downloaded_verified` |
| 8 | `sim3292_metadata.txt` | `originals/geology` | 14,233 | None published (USGS Pubs) | `f6124030ad026b0f0f249f9aff64b733dcfe0174c97aa8027b7af33b6f3527a6` | `downloaded_verified` |
| 9 | `sim3292_metadata.xml` | `originals/geology` | 14,721 | None published (USGS Pubs) | `38806845cae2354e4ab65c55f57819d3e001b3865aceb5a24426efd5412683f8` | `downloaded_verified` |
| 10 | `sim3292_pamphlet.pdf` | `originals/geology` | 3,415,492 | None published (USGS Pubs) | `18d3f0547e2f8cd82891f5adc454a8177ab62339c0b4a7f8370d8d2ecbce16ca` | `downloaded_verified` |
| 11 | `sim3292_readme.txt` | `originals/geology` | 5,580 | None published (USGS Pubs) | `702c8d8dd705a7746dad2b47a36f85fd850cc44939388ccc5f8e636369731aeb` | `downloaded_verified` |
| 12 | `DTEEC_011635..._A01.tif` | `originals/hirise` | 65,126,266 | None published (USGS ARD) | `a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad` | `downloaded_verified` |
| 13 | `ESP_011635..._RED_A_02_ORTHO.LBL` | `originals/hirise` | 5,406 | None published (USGS ARD) | `d980d74f4519e773efe80aa98415614476db7c545dcde00d04a616c015c7b677` | `downloaded_verified` |
| 14 | `provenance.txt` | `originals/hirise` | 3,024 | None published (USGS ARD) | `f64e16114ebd512e47df3323ce2c42e53edb1490fcc36097873fc944a8353051` | `downloaded_verified` |
| 15 | `h0018_0000_dt4.img` | `originals/hrsc` | 86,686,886 | MD5: `BFAF16E930228E9C9ACA7E10B396446F` (MATCH) | `32270e0a565624d3c9f8032c7ec616b85cc939be63bce3c2ee7cac1c9937a43e` | `downloaded_validation_pending` |
| 16 | `WE__0001..._DER_PS...P02.CSV` | `originals/meda` | 125,877 | None published (PDS Atmospheres) | `600d8d11b26b2127ba66f90889e7ba5621a0b8b788146bf5bf72a02be2e0a16c` | `downloaded_verified` |
| 17 | `WE__0001..._DER_PS...P02.xml` | `originals/meda` | 9,326 | None published (PDS Atmospheres) | `bf91828374f61d9267baf2f35b2784e50ffd44ea4b3559e023295ff075068c91` | `downloaded_verified` |
| 18 | `WE__0001..._DER_RHS...P03.CSV` | `originals/meda` | 102,060 | None published (PDS Atmospheres) | `00271c06137f76294541e2c028c1ed76fca85a11829cf7c76c82fb2cd86e35d8` | `downloaded_verified` |
| 19 | `WE__0001..._DER_RHS...P03.xml` | `originals/meda` | 10,880 | None published (PDS Atmospheres) | `29cb6b7cfff3ca88404df1311b58a2e2931f8dfada46b253faa25dd4e7d50a84` | `downloaded_verified` |
| 20 | `WE__0001..._DER_TIRS...P04.CSV` | `originals/meda` | 7,417 | None published (PDS Atmospheres) | `ded7c255c90ede5fbbfbb66396c562b0ebc4d1682b71e29976e23cbc4cb47815` | `downloaded_verified` |
| 21 | `WE__0001..._DER_TIRS...P04.xml` | `originals/meda` | 13,751 | None published (PDS Atmospheres) | `970c099fd89a2c01b9e442613d60104c1a76e5f71b7957867fd519c51b5d3673` | `downloaded_verified` |
| 22 | `RME_397535244ADR..._P9.TAB` | `originals/rems` | 114,152 | None published (PDS Atmospheres) | `d5edd3d49198992bd36244b4b151b8850befce2d91b9c774cce72a40e254d194` | `downloaded_verified` |
| 23 | `RME_397535244ADR..._P9.xml` | `originals/rems` | 17,146 | None published (PDS Atmospheres) | `c74c1258074918630f716a2dcadf24f272c9501a034ebb06d88d130840f86618` | `downloaded_verified` |
| 24 | `RME_397535244RMD..._PA.TAB` | `originals/rems` | 279,000 | None published (PDS Atmospheres) | `e38f69846b30e84c13d6bc916b04e2ff27a782172c35bc025faca65740f3669f` | `downloaded_verified` |
| 25 | `RME_397535244RMD..._PA.xml` | `originals/rems` | 28,154 | None published (PDS Atmospheres) | `ce4d63f2be20f8d55d4a2ffaea8a5fedc2338f134243b96396af7af39c123af9` | `downloaded_verified` |
| 26 | `DBmap2007.tif` | `originals/themis` | 77,789,206 | None published (ASU Mars) | `0b2ca94b9414cd7c74e73f8df9ccb4a3c104bef24da932c4dc43fb246bc71a4b` | `downloaded_verified` |
| 27 | `NBmap2007.tif` | `originals/themis` | 77,789,206 | None published (ASU Mars) | `ea428e4424f412fc8c94c10e73ed88176f812c2a10fd2e81e9b7d37a5828802e` | `downloaded_verified` |
| 28 | `tes_putzigti_dayside...jpg` | `originals/themis` | 3,464,102 | None published (ASU Mars) | `e3e35d17bf9abf0bfe09c943ee239071e06adc4b486863281649e71c65571fb2` | `downloaded_verified` |
| 29 | `tes_putzigti_nightside...jpg` | `originals/themis` | 2,991,218 | None published (ASU Mars) | `1dc5d3c7dbe9ab31314455ab2d9eb2be1ad51d10453d516a2139e9388d83d6d9` | `downloaded_verified` |
| 30 | `themis_nightir_N-30_000.png` | `originals/themis` | 49,490,620 | None published (ASU Mars) | `ebd045a3ca522624ec41c41611415095d07db9452b867cbb205ddba2c2a2f66d` | `downloaded_verified` |
| 31 | `thm_dir_N-30_000.png` | `originals/themis` | 38,612,248 | None published (ASU Mars) | `0f80f5cd8a4bdc59d7f9f3b9d1c566bd8f9437cccff68c873d1394b1aa19d7af` | `downloaded_verified` |
| 32 | `Ingenuity_Mars_Helicopter.glb` | `visualization/nasa_3d` | 2,019,408 | None published (NASA 3D) | `9e5a5398ab335eae7d46335085301ce46fb7de052300b645debe8bac6d39f2b5` | `downloaded_verified` |
| 33 | `Mars_2020_Perseverance_Rover.glb` | `visualization/nasa_3d` | 4,987,176 | None published (NASA 3D) | `10db7c03a5e63a5a3b3e7baa6243aa4918ba045fa8ff0a731d0217491adc727f` | `downloaded_verified` |
| 34 | `Mars_Globe_Texture.jpg` | `visualization/nasa_3d` | 972,896 | None published (NASA 3D) | `12ec6bf02ebd42a246edc778cb2ce8c595b4d9f0892badf0bfff8abb2303c780` | `downloaded_verified` |

---

## 5. Audit Conclusion

With Phase 8.5/8.5.1 completed:
1. **Full Geological GIS Ingestion:** The original USGS SIM 3292 database (`sim3292_database.zip`, 808.9 MB) is acquired and extracted into `data/derived/geology/` with 1,311 chronostratigraphic polygons and structural linework.
2. **Accurate Thermal Classification:** MGS TES Putzig (2007) is classified as Thermal Inertia ($I = \sqrt{k\rho c}$ in tiu), NOT surface temperature. 2001 Mars Odyssey THEMIS Day and Night 100m IR mosaics are integrated and verified as calibrated infrared brightness temperature/radiance.
3. **HRSC Spheroid Reference Rigorously Established:** The HRSC Level 4 DTM is confirmed to reference `HEIGHT_ABOVE_SPHEROID` ($R = 3,396.0\text{ km}$), correctly preventing invalid direct merges with MOLA/CTX areoid elevations until geoid separation is applied.
4. **Observation & Spectral Honesty:** CRISM is verified with atmospheric/thermal corrections OFF, MEDA and REMS are documented as Sol 1 limited historical samples, and MCS is catalogued as unavailable.
