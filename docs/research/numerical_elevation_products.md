# MARS-X — Numerical Elevation Products Availability Report

**Author:** MARS-X Planetary GIS Architecture Team  
**Date:** 2026-11-13  
**Scope:** Authoritative numerical Digital Terrain Models (DTMs) for Mars exploration and Marswalk traverse planning.

---

## 1. Product Summary Matrix

| Product ID | Mission / Instrument | Pixel Spacing (Resolution) | Coverage Footprint | Native CRS | Vertical Datum | NoData Value | Format | Public Download Source |
|---|---|---|---|---|---|---|---|---|
| `megt_128_areoid` | MGS MOLA | 463 m/px (128 px/deg at equator) | Near-Global ($\pm 88^\circ$ Lat, $0^\circ\text{--}360^\circ$ Lon) | IAU 2000 Mars Sphere ($R=3396190\text{ m}$) | MOLA Areoid (Mars50c) | `-32768` (int16) | PDS3 `.img` / GeoTIFF | [NASA PDS Geosciences](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) |
| `megt_64_areoid` | MGS MOLA | 926 m/px (64 px/deg at equator) | Global ($\pm 88^\circ$ Lat) | IAU 2000 Mars Sphere | MOLA Areoid | `-32768` (int16) | PDS3 `.img` / GeoTIFF | [NASA PDS Geosciences](https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg064/) |
| `hrsc_mc11_dtm` | Mars Express HRSC | 50 m/px | Regional Quadrangle (MC-11 East/West Oxia Planum / Ares Vallis) | Sinusoidal / Equirectangular Mars | MOLA Areoid | `-32768.0` (float32) | GeoTIFF / VICAR | [ESA PSA / DLR HRSC](https://www.cosmos.esa.int/web/psa/mars-express) |
| `hrsc_orbit_strip` | Mars Express HRSC | 50–125 m/px | Individual orbital swaths (variable coverage) | Sinusoidal / Equidistant Cylindrical | MOLA Areoid | `-32768.0` | GeoTIFF / PDS3 | [USGS Astrogeology HRSC Search](https://astrogeology.usgs.gov/search?pmi-target=mars&pmi-instrument=HRSC) |
| `hirise_dtm_jezero` | MRO HiRISE | 1.0 m/px (sampled from 0.25 m images) | Local Targeted ($~20\text{ km} \times 5\text{ km}$ per swath) | Equirectangular Mars (center lat specific) | MOLA Areoid | `-3.40282e+38` (float32) | GeoTIFF / PDS3 IMG | [UA HiRISE DTM Catalog](https://www.uahirise.org/dtm/) |
| `hirise_dtm_gale` | MRO HiRISE | 1.0 m/px | Local Targeted (Mount Sharp & floor) | Equirectangular Mars | MOLA Areoid | `-3.40282e+38` | GeoTIFF | [UA HiRISE DTM Gale](https://www.uahirise.org/dtm/dtm.php?ID=PSP_001752_1750) |
| `ctx_dtm_jezero` | MRO CTX | 18–20 m/px (from 6 m images) | Regional Corridor ($~30\text{ km} \times 100\text{ km}$) | Equirectangular Mars | MOLA Areoid | `-32768.0` or `-3.40282e+38` | GeoTIFF | [USGS Astrogeology CTX DTMs / NASA Ames ASP](https://astrogeology.usgs.gov/) |

---

## 2. Detailed Technical Profiles

### 2.1 MOLA Mission Experiment Gridded Data Records (MEGDR)
- **Product Identifier:** `MEGT90N000CB.IMG` (Topography, 128 px/deg global mosaic or 4-quadrant tiles)
- **Authoritative Source:** NASA Planetary Data System (PDS) Geosciences Node (Washington University in St. Louis).
- **Native CRS:** Simple Cylindrical (Plate Carrée), planetocentric latitude $-88^\circ \text{ to } +88^\circ$, positive East longitude $0^\circ \text{ to } 360^\circ$. Spherical body with radius $R = 3,396,190\text{ m}$.
- **Vertical Datum:** Elevations are heights in metres above the MOLA Areoid. (Formula: $Z_{\text{elev}} = R_{\text{planetary}} - R_{\text{areoid}}$).
- **Pixel Spacing:** 128 pixels per degree ($0.0078125^\circ/\text{px}$). At the equator:
  $$\Delta x = \frac{2\pi \times 3,396,190\text{ m}}{360^\circ \times 128} \approx 463.08\text{ m/pixel}$$
  At latitude $\phi$, the east-west physical spacing is $463.08 \cdot \cos(\phi)\text{ m}$.
- **Storage & Encoding:** 16-bit signed integer (Big-Endian in original PDS3; Little-Endian in GeoTIFF conversions).
- **Elevation Scaling Factor:** $\text{Elevation (metres)} = \text{DN} \times 1.0$.
- **NoData Value:** `-32768`. Any pixel with value $-32768$ indicates unmeasured terrain or polar gaps.
- **Availability:** Immediate direct HTTPS download from PDS Geosciences and USGS Astrogeology.

### 2.2 HRSC High Resolution Stereo Camera DTMs
- **Product Identifier:** e.g., `h5224_0000_dt4.img`, `MC11E_HRSC_DTM_50M.tif`
- **Authoritative Source:** European Space Agency (ESA) Planetary Science Archive (PSA), German Aerospace Center (DLR) Institute of Planetary Research, and NASA PDS Geosciences Node.
- **Native CRS:** IAU 2000 Mars Ellipsoid ($a=3396.19\text{ km}, b=3376.20\text{ km}$), Equirectangular projection with standard parallel at center latitude of the swath.
- **Vertical Datum:** Metres relative to MOLA Areoid.
- **Pixel Spacing:** 50 metres/pixel to 125 metres/pixel depending on orbiter periapsis altitude ($250\text{--}800\text{ km}$).
- **Coverage Footprint:** Strip-based, covering ground tracks of width $\approx 50\text{ km}$ to $300\text{ km}$ and lengths up to $1,000\text{ km}$. Approximately $50\%\text{--}70\%$ of the surface is covered by stereo observations suitable for DTM processing.
- **NoData Value:** `-32768.0` (IEEE 754 single-precision float).
- **Scientific Limitation:** Vertical precision varies from $10\text{ m}$ to $40\text{ m}$ depending on stereo base-to-height ($B/H$) ratio and surface atmospheric dust opacity.

### 2.3 HiRISE Stereo Photogrammetric DTMs
- **Product Identifier:** e.g., `DTEEC_042858_1985_042924_1985_A01.IMG` (Jezero Crater Delta DTM)
- **Authoritative Source:** University of Arizona Lunar and Planetary Laboratory / USGS Astrogeology Science Center / NASA PDS.
- **Native CRS:** Equirectangular projection with center latitude as projection origin, IAU 2000 Mars spheroid.
- **Vertical Datum:** Metres above the MOLA Areoid (tied to MOLA tracks using least-squares surface fitting).
- **Pixel Spacing:** Exactly $1.00\text{ m/pixel}$ (post-spacing).
- **Coverage Footprint:** Local high-priority targets. Typical swath covers $\sim 5\text{ km} \times 15\text{ km}$ to $20\text{ km}$. Total Martian surface coverage is $< 0.1\%$.
- **Format:** 32-bit floating point GeoTIFF or PDS3 `.IMG`.
- **NoData Value:** `-3.4028234663852886e+38` (standard minimum single-precision float).
- **Availability:** Searchable and downloadable directly via the [HiRISE DTM Web Portal](https://www.uahirise.org/dtm/).

### 2.4 CTX Context Camera Stereo DTMs
- **Product Identifier:** e.g., `Jezero_West_CTX_DTM_20m.tif`
- **Authoritative Source:** NASA Ames Stereo Pipeline (ASP) community releases, Murray Lab (Caltech), and USGS Astrogeology Science Center.
- **Native CRS:** Equirectangular Mars 2000.
- **Vertical Datum:** Metres above MOLA Areoid.
- **Pixel Spacing:** 18 to 24 metres/pixel (standard $3\times\text{--}4\times$ optical sampling ratio from 6 m/px raw CTX frames).
- **Coverage Footprint:** Regional landing site corridors ($\approx 30\text{ km} \times 100\text{ km}$).
- **NoData Value:** `-32768.0` or `-3.40282e+38`.
- **Availability:** Available through Caltech Murray Lab CTX portal and USGS Astrogeology data repository.

---

## 3. Product Selection Strategy for MARS-X Ingestion

1. **Global Base Layer:** MOLA MEGDR Topography at 128 px/deg ($\approx 463\text{ m/px}$) or 64 px/deg ($\approx 926\text{ m/px}$) provides complete planet-wide elevation for macro-topography, regional viewsheds, and boundary constraints.
2. **Regional Landing Site Context:** HRSC MC-11 mosaic and CTX stereo DTMs ($20\text{ m/px}$) provide regional traverses in candidate exploration zones (Jezero Crater, Gale Crater, Mawrth Vallis).
3. **Tactical Rover/Marswalk Scale:** HiRISE DTMs ($1.0\text{ m/px}$) provide obstacle-level terrain analysis (boulder fields, sand dunes, steep crater rims) for micro-traverse path planning.

