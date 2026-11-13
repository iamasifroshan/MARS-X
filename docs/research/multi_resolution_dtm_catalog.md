# MARS-X — Multi-Resolution Mars Numerical DTM Discovery Report

**Author:** MARS-X Planetary GIS Architecture Team  
**Date:** 2026-11-13  
**Status:** Validated  
**Scope:** Authoritative numerical Digital Terrain Models (DTMs) across MOLA, HRSC, CTX, and HiRISE instruments.

---

## 1. Multi-Resolution Hierarchy Overview

MARS-X categorizes Martian numerical elevation datasets into four operational tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 1: GLOBAL BASELINE (MOLA MEGDR)                                   │
│ Spacing: 463 m/px (128 px/deg) to 14.8 km/px (4 px/deg)               │
│ Coverage: Global (±88° to ±90° Lat) | Vertical Datum: MOLA Areoid      │
└────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 2: REGIONAL CONTEXT (HRSC & CTX DTMs)                             │
│ Spacing: 18 m/px (CTX ASP) to 50–100 m/px (HRSC)                       │
│ Coverage: Swath & Quadrangle (~5%–70%) | Vertical Datum: MOLA Areoid   │
└────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 3: LOCAL EXPLORATION (HiRISE DTMs)                                │
│ Spacing: 1.0 m/px to 2.0 m/px post-spacing                            │
│ Coverage: Targeted (<0.1% planet) | Vertical Datum: MOLA Areoid (tied) │
└────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 4: TACTICAL SURFACE SCALE (In-Situ Rover Navcam/Hazcam Mesh)      │
│ Spacing: Centimeter-scale (1–5 cm/px within 10–20m radius)             │
│ Coverage: In-situ local traverse | Datum: Site-Local Frame             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Product Profiles

### 2.1 MOLA MEGDR 128 px/deg (Global Base Grid)
- **Product ID:** `MEGT00N000HB` (and 15 companion global tiles)
- **Source Archive:** NASA PDS Geosciences Node (Washington University in St. Louis)
- **Download URL:** `https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/`
- **Spatial Footprint:** Latitude $[-44.0^\circ, 0.0^\circ]$, Longitude $[0.0^\circ, 90.0^\circ\text{E}]$ (Tile 00N000)
- **Native CRS:** Simple Cylindrical, IAU 2000 Mars Sphere ($R=3396.0\text{ km}$), Planetocentric, Positive-East
- **Pixel Spacing:** $0.0078125^\circ/\text{pixel}$ ($463.08\text{ m/pixel}$ at equator)
- **Vertical Datum:** Goddard Mars potential model GMM3 areoid evaluated to degree 50
- **NoData Value:** `-32768` (int16)
- **Acquisition Information:** Mars Global Surveyor (1999–2001), 600M laser returns
- **Quality Notes:** Gaps between ground tracks up to 12 km at equator; dense overlapping coverage at higher latitudes; vertical precision $\pm 1\text{ m}$ on flat plains.

### 2.2 HRSC High Resolution Stereo Camera (Regional Swaths & Mosaics)
- **Candidate Product ID:** `MC11E_HRSC_DTM_50M` (Oxia Planum / Ares Vallis MC-11 East)
- **Source Archive:** ESA Planetary Science Archive (PSA) / DLR Institute of Planetary Research / NASA PDS
- **Download URL:** `https://pds-geosciences.wustl.edu/missions/mars_express/hrsc.htm`
- **Spatial Footprint:** Latitude $[0.0^\circ, 30.0^\circ\text{N}]$, Longitude $[315.0^\circ, 360.0^\circ\text{E}]$ (Oxia Planum Rosalind Franklin rover landing site corridor)
- **Native CRS:** Sinusoidal or Equirectangular Mars 2000 Ellipsoid ($a=3396.19\text{ km}, b=3376.20\text{ km}$)
- **Pixel Spacing:** $50.0\text{ m/pixel}$
- **Vertical Datum:** Height above MOLA Areoid
- **NoData Value:** `-32768.0` (float32)
- **Acquisition Information:** Mars Express along-track stereo channels (Nadir, S1, S2, P1, P2)
- **Quality Notes:** Stereophotogrammetric correlation; non-contiguous coverage; vertical precision $10\text{--}25\text{ m}$.

### 2.3 CTX Context Camera Stereo DTMs (Regional Traverse Corridors)
- **Candidate Product ID:** `Jezero_West_CTX_DTM_20m`
- **Source Archive:** USGS Astrogeology Science Center / NASA Ames Stereo Pipeline (Dickson et al., 2018; Murray Lab Caltech)
- **Download URL:** `https://astrogeology.usgs.gov/search/map/Mars/MarsReconnaissanceOrbiter/CTX/`
- **Spatial Footprint:** Latitude $[17.0^\circ, 20.0^\circ\text{N}]$, Longitude $[76.0^\circ, 79.5^\circ\text{E}]$ (Jezero Crater and western rim)
- **Native CRS:** Equirectangular Mars, Planetocentric, Positive-East
- **Pixel Spacing:** $20.0\text{ m/pixel}$
- **Vertical Datum:** MOLA Areoid
- **NoData Value:** `-32768.0` or `-3.40282e+38`
- **Acquisition Information:** MRO CTX stereo pairs (5–6 m/px raw optical resolution)
- **Quality Notes:** Processed using NASA Ames Stereo Pipeline (ASP); tied to MOLA tracks with iterative closest point (ICP) alignment.

### 2.4 HiRISE High Resolution Imaging Science Experiment (Local DTMs)
- **Candidate Product ID:** `DTEEC_042858_1985_042924_1985_A01` (Jezero Crater Western Delta)
- **Source Archive:** University of Arizona Lunar and Planetary Laboratory / NASA PDS
- **Download URL:** `https://www.uahirise.org/dtm/dtm.php?ID=ESP_042858_1985`
- **Spatial Footprint:** Center coordinates $18.42^\circ\text{N}, 77.45^\circ\text{E}$, width $\sim 5\text{ km}$, length $\sim 18\text{ km}$
- **Native CRS:** Equirectangular Mars ($a=3396190\text{ m}, b=3376200\text{ m}$), center latitude $18.5^\circ\text{N}$
- **Pixel Spacing:** $1.00\text{ m/pixel}$ (post-spacing)
- **Vertical Datum:** MOLA Areoid
- **NoData Value:** `-3.4028235e+38` (float32)
- **Acquisition Information:** MRO HiRISE stereo pairs acquired during orbital passes `ESP_042858_1985` and `ESP_042924_1985`
- **Quality Notes:** Ultra-high resolution microtopography resolving meter-scale boulders, crater rims, and delta scarps; total Martian surface coverage is $< 0.1\%$.

---

## 3. Coverage Footprint & Resolution Comparison

| Instrument | Product Level | Native Resolution | Ground Spacing | Planetary Coverage | Vertical Datum |
|---|---|---|---|---|---|
| **MOLA** | MEGDR 4 | $4\text{ px/deg}$ | $14,819\text{ m/px}$ | Global ($100\%$) | MOLA Areoid |
| **MOLA** | MEGDR 64 | $64\text{ px/deg}$ | $926\text{ m/px}$ | Global ($98.6\%$, tiled 4 quads) | MOLA Areoid |
| **MOLA** | MEGDR 128 | $128\text{ px/deg}$ | $463\text{ m/px}$ | Global ($98.6\%$, tiled 16 tiles) | MOLA Areoid |
| **HRSC** | Level 4 DTM | $50\text{--}100\text{ m/px}$ | $50\text{ m/px}$ | Regional swaths ($\sim 50\%\text{--}70\%$) | MOLA Areoid |
| **CTX** | ASP Stereo DTM | $18\text{--}24\text{ m/px}$ | $20\text{ m/px}$ | Regional corridors ($\sim 5\%\text{--}10\%$) | MOLA Areoid |
| **HiRISE** | PDS Stereo DTM | $1.0\text{--}2.0\text{ m/px}$ | $1.0\text{ m/px}$ | Targeted landing sites ($< 0.1\%$) | MOLA Areoid (tied) |

---

## 4. Multi-Resolution Architecture Rules

1. **Strict Anti-Upsampling Constraint:**
   Low-resolution rasters (e.g. MOLA 128 px/deg) must **never** be bilinearly or bicubically upsampled to 1m/px to simulate high-resolution terrain. Any API response or UI view must explicitly report the native source dataset resolution.
2. **Vertical Reference Harmonization:**
   MOLA, HRSC, CTX, and HiRISE all reference the **MOLA Areoid**. However, HiRISE DTMs generated with USGS ISIS may have a localized vertical datum shift of $\pm 1\text{--}5\text{ m}$ relative to raw MOLA tracks if not bundle-adjusted with MOLA PEDR profiles. MARS-X inspects the dataset provenance before computing composite elevation profiles.
