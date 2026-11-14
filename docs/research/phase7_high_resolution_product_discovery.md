# MARS-X — Phase 7 Research: High-Resolution Product Discovery & Ingestion

## 1. High-Resolution Ingestion Overview

MARS-X bridges regional orbital altimetry (MOLA 463 m/px) with high-resolution numerical Digital Terrain Models (DTMs) produced from stereo photogrammetry by the Mars Reconnaissance Orbiter (MRO) Context Camera (CTX, 20 m/px) and High Resolution Imaging Science Experiment (HiRISE, 1 m/px).

---

## 2. Ingested Regional CTX Numerical DTM

Authentic USGS Astrogeology Controlled CTX DTM data was queried via the USGS Astrogeology STAC API (`https://stac.astrogeology.usgs.gov/api`) and acquired from AWS Open Data storage.

- **Product Name:** `P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W`
- **Region:** Tyrrhena Terra / Northern Hellas rim
- **Spatial Resolution:** **20.01 meters/pixel**
- **Raster Dimensions:** 1,692 samples × 3,472 lines (Single-band 32-bit floating point)
- **Local File:** `data/raw/ctx/P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif`
- **File Size:** 12,734,013 bytes (~12.14 MB Cloud-Optimized GeoTIFF)
- **SHA-256 Checksum:** `a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2`
- **Projection / CRS:** `IAU:49910` (Mars 2000 Equirectangular, standard parallel 0.0°)
- **Vertical Reference Datum:** MOLA Areoid (tied using NASA Ames Stereo Pipeline `pc_align` against MOLA tracks)
- **NoData Sentinel:** `-32767.0` (Preserved and masked; never treated as zero elevation)
- **Elevation Range:** **+797.6 m to +2514.3 m** (Valid pixel count: 4,281,424; 72.88% valid data)
- **Geographic Bounds:**
  - Latitude: **-5.1873° to -4.0028°**
  - Longitude: **66.0357° to 66.6171°E**
  - **CRITICAL GEODESY CONFIRMATION:** This footprint lies **100% geographically inside acquired MOLA tile `megt00n000hb`** (Lat [-44°, 0°], Lon [0°, 90°E]), providing an authentic, overlapping testbed for cross-sensor comparison without artificial synthesis.

---

## 3. Catalogued Local HiRISE Meter-Scale DTM

To establish the local tactical tier, an authentic meter-scale HiRISE DTM was discovered and registered:
- **Product ID:** `hirise-dtm-schiaparelli` (`DTEEC_017118_1790_016406_1790_A01`)
- **Stereo Pair:** `ESP_017118_1790` and `ESP_016406_1790`
- **Location:** Schiaparelli Crater floor dunes & yardangs
- **Resolution:** **1.01 meters/pixel post-spacing**
- **Geographic Footprint:** Lat [-1.11°, -0.77°], Lon [13.80°, 13.92°E]
- **Lifecycle State:** `discovered` (PDS detached label metadata indexed, ready for staging)
- **Vertical Datum:** MOLA Areoid (tied via manual & automated GCPs to MOLA PEDR tracks)
- **NoData Value:** `-3.4028235e+38` (Float32 minimum sentinel)

---

## 4. Controlled Hierarchy Catalog (4 Tiers)

The complete MARS-X multi-resolution elevation hierarchy is now operational across 4 tiers:

1. **Global Coarse (`global_coarse`):** MOLA MEGDR 4 ppd (~14.8 km/px), global planetary reference.
2. **Global Base (`global_base`):** MOLA MEGDR 128 ppd (463.08 m/px), 3 authentic regional tiles on disk covering 26.05% of Mars.
3. **Regional High-Res (`regional`):** USGS Controlled MRO CTX DTM (20.01 m/px), Tyrrhena Terra analysis-ready.
4. **Local Tactical (`local_tactical`):** MRO HiRISE DTM (1.01 m/px), meter-scale microtopography.

