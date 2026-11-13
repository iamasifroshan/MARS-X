# MARS-X Dataset Catalogue

> Documentation of all registered NASA/USGS Mars datasets in the MARS-X platform.

---

## Overview

MARS-X maintains a metadata catalogue of **11 Mars datasets** from NASA and USGS missions. These datasets span orbital remote sensing, surface rover measurements, and compiled geologic products.

All datasets currently have `processing_status: "registered"` — their metadata is catalogued but raw data has not yet been downloaded or processed by the platform.

---

## Data Provenance Principles

1. **No fabricated data** — Every dataset entry references a real NASA/USGS data product with verifiable source URLs
2. **Processing status tracking** — Each dataset carries a `processing_status` field that honestly reflects its state in the MARS-X pipeline:
   - `registered` — Metadata catalogued, data not downloaded
   - `available` — Data available for download from source
   - `downloaded` — Raw data fetched to local storage
   - `validated` — Data integrity and schema verified
   - `error` — Processing failed; requires investigation
3. **Scientific limitations documented** — Known caveats, sensor limitations, and coverage gaps are recorded for each dataset
4. **CRS consistency** — All datasets use `IAU:49900` (Mars areocentric coordinates)

---

## Registered Datasets

### 1. MOLA Topography (MEGDR)

| Field | Value |
|---|---|
| **Dataset ID** | `mola-megdr` |
| **Mission** | Mars Global Surveyor |
| **Instrument** | Mars Orbiter Laser Altimeter (MOLA) |
| **Product Type** | Topographic grid (DTM) |
| **Resolution** | 463 m/px (1/128 degree) |
| **Coverage** | Global, 87.5°S to 87.5°N |
| **Date Range** | 1999–2001 |
| **CRS** | IAU:49900 |
| **Format** | PDS IMG / GeoTIFF |
| **Source** | [PDS Geosciences Node](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) |
| **Status** | `registered` |

**Description:** Global topographic dataset derived from over 600 million laser altimetry measurements. Provides the primary global elevation reference for Mars.

**Limitations:** Accuracy degrades above ~87° latitude due to polar orbit geometry. Vertical accuracy ~1 m, horizontal ~100 m.

---

### 2. HRSC Digital Terrain Models

| Field | Value |
|---|---|
| **Dataset ID** | `hrsc-dtm` |
| **Mission** | Mars Express (ESA) |
| **Instrument** | High Resolution Stereo Camera (HRSC) |
| **Product Type** | Stereo-derived DTM |
| **Resolution** | 50–100 m/px |
| **Coverage** | Partial global (orbit strips) |
| **Date Range** | 2004–present |
| **CRS** | IAU:49900 |
| **Format** | PDS IMG / GeoTIFF |
| **Source** | [PDS Geosciences Node](https://pds-geosciences.wustl.edu/missions/mars_express/hrsc.htm) |
| **Status** | `registered` |

**Description:** High-resolution stereo-derived digital terrain models from ESA's Mars Express orbiter, providing regional topography at higher resolution than MOLA.

**Limitations:** Coverage is not global; limited to regions imaged with sufficient stereo convergence angle. Quality varies by orbit.

---

### 3. USGS Geologic Map of Mars (SIM 3292)

| Field | Value |
|---|---|
| **Dataset ID** | `usgs-sim3292` |
| **Mission** | Multi-mission compilation |
| **Instrument** | Multiple (compilation) |
| **Product Type** | Geologic map (vector) |
| **Resolution** | 1:20,000,000 scale |
| **Coverage** | Global geologic units and contacts |
| **Date Range** | N/A (compilation) |
| **CRS** | IAU:49900 |
| **Format** | Shapefile / GeoDatabase |
| **Source** | [USGS Publications](https://pubs.usgs.gov/sim/3292/) |
| **Status** | `registered` |

**Description:** The first global unified geologic map of Mars (Tanaka et al., 2014), defining major geologic units and stratigraphic relationships at 1:20,000,000 scale.

**Limitations:** Not suitable for local-scale geologic analysis. Unit boundaries generalised from multiple source maps.

---

### 4. HiRISE Imagery (RDR)

| Field | Value |
|---|---|
| **Dataset ID** | `hirise-rdr` |
| **Mission** | Mars Reconnaissance Orbiter |
| **Instrument** | High Resolution Imaging Science Experiment (HiRISE) |
| **Product Type** | Orbital imagery |
| **Resolution** | 0.25–0.5 m/px |
| **Coverage** | Targeted sites (~3% of Mars surface) |
| **Date Range** | 2006–present |
| **CRS** | IAU:49900 |
| **Format** | JP2 / PDS IMG |
| **Source** | [HiRISE Catalog](https://www.uahirise.org/catalog/) |
| **Status** | `registered` |

**Description:** The highest-resolution orbital imagery of Mars, enabling detailed study of surface features at sub-metre scale.

**Limitations:** Targeted coverage only; not global. Large file sizes (>1 GB per observation). Colour coverage narrower than red-band.

---

### 5. CTX Context Imagery (EDR)

| Field | Value |
|---|---|
| **Dataset ID** | `ctx-edr` |
| **Mission** | Mars Reconnaissance Orbiter |
| **Instrument** | Context Camera (CTX) |
| **Product Type** | Orbital imagery |
| **Resolution** | ~6 m/px |
| **Coverage** | Over 99% of Mars surface |
| **Date Range** | 2006–present |
| **CRS** | IAU:49900 |
| **Format** | PDS IMG |
| **Source** | [PDS Imaging Node](https://pds-imaging.jpl.nasa.gov/volumes/mro.html) |
| **Status** | `registered` |

**Description:** Grayscale context imagery providing near-global 6 m/px coverage, used for geomorphological mapping and HiRISE targeting context.

**Limitations:** Grayscale only (panchromatic 500–800 nm). Geometric distortions in raw images require map projection.

---

### 6. CRISM Spectroscopy (TRDR)

| Field | Value |
|---|---|
| **Dataset ID** | `crism-trdr` |
| **Mission** | Mars Reconnaissance Orbiter |
| **Instrument** | Compact Reconnaissance Imaging Spectrometer for Mars (CRISM) |
| **Product Type** | Hyperspectral image cube |
| **Resolution** | 15–18 m/px (targeted mode) |
| **Coverage** | Targeted mineralogy at thousands of sites |
| **Date Range** | 2006–present |
| **CRS** | IAU:49900 |
| **Format** | PDS IMG (hyperspectral cubes) |
| **Source** | [CRISM Data Portal](https://crism.jhuapl.edu/) |
| **Status** | `registered` |

**Description:** Visible and infrared reflectance spectroscopy data used to identify and map minerals on the Martian surface including phyllosilicates, sulfates, and iron oxides.

**Limitations:** Detector degradation over mission lifetime reduces spectral quality in later data. Atmospheric correction required for surface mineral identification.

---

### 7. THEMIS Infrared Mosaic

| Field | Value |
|---|---|
| **Dataset ID** | `themis-ir` |
| **Mission** | Mars Odyssey |
| **Instrument** | Thermal Emission Imaging System (THEMIS) |
| **Product Type** | Thermal infrared imagery |
| **Resolution** | 100 m/px (IR), 18 m/px (VIS) |
| **Coverage** | Global daytime and nighttime IR mosaics |
| **Date Range** | 2002–present |
| **CRS** | IAU:49900 |
| **Format** | GeoTIFF / PDS IMG |
| **Source** | [USGS Astrogeology](https://astrogeology.usgs.gov/search/map/Mars/Odyssey/THEMIS-IR-Mosaic-ASU/Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v14) |
| **Status** | `registered` |

**Description:** Global thermal infrared imagery providing daytime and nighttime surface temperature maps used for thermal inertia studies and compositional mapping.

**Limitations:** Thermal inertia derivations depend on atmospheric and surface models. Day/night coverage completeness varies by region.

---

### 8. RAD Radiation Data

| Field | Value |
|---|---|
| **Dataset ID** | `msl-rad` |
| **Mission** | Mars Science Laboratory (Curiosity) |
| **Instrument** | Radiation Assessment Detector (RAD) |
| **Product Type** | In-situ radiation measurements |
| **Resolution** | N/A (point measurements) |
| **Coverage** | Gale Crater (MSL traverse) |
| **Date Range** | 2012–present |
| **CRS** | IAU:49900 |
| **Format** | CSV / PDS TABLE |
| **Source** | [PDS Geosciences Node](https://pds-geosciences.wustl.edu/missions/msl/rad.htm) |
| **Status** | `registered` |

**Description:** Surface-level radiation dose rate and particle flux measurements from RAD on Curiosity, essential for assessing human exploration radiation hazards on Mars.

**Limitations:** Point measurements at a single location; not representative of global radiation environment. Shielding by rover structure affects some channels.

---

### 9. REMS Weather Data

| Field | Value |
|---|---|
| **Dataset ID** | `msl-rems` |
| **Mission** | Mars Science Laboratory (Curiosity) |
| **Instrument** | Rover Environmental Monitoring Station (REMS) |
| **Product Type** | In-situ meteorological data |
| **Resolution** | N/A (point measurements) |
| **Coverage** | Gale Crater (MSL traverse) |
| **Date Range** | 2012–present |
| **CRS** | IAU:49900 |
| **Format** | CSV / PDS TABLE |
| **Source** | [PDS Atmospheres Node](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/MARS/mars_msl.html) |
| **Status** | `registered` |

**Description:** Environmental monitoring data including air/ground temperature, pressure, humidity, UV radiation, and wind speed/direction in Gale Crater.

**Limitations:** Wind speed sensor partially damaged during landing; wind measurements have higher uncertainty. Single-site measurements.

---

### 10. Curiosity Surface Imagery

| Field | Value |
|---|---|
| **Dataset ID** | `msl-imagery` |
| **Mission** | Mars Science Laboratory (Curiosity) |
| **Instrument** | Mastcam / MAHLI / MARDI |
| **Product Type** | Surface imagery |
| **Resolution** | Variable (0.15–7.4 mm/px at 2 m range) |
| **Coverage** | Gale Crater (MSL traverse) |
| **Date Range** | 2012–present |
| **CRS** | IAU:49900 |
| **Format** | JPEG / PNG / PDS IMG |
| **Source** | [PDS Imaging Node](https://pds-imaging.jpl.nasa.gov/volumes/msl.html) |
| **Status** | `registered` |

**Description:** Surface imagery from Curiosity's camera suite including Mastcam (science cameras), MAHLI (hand lens imager), and MARDI (descent imager), documenting Gale Crater geology.

**Limitations:** Mastcam left eye (M-34) lower resolution than right eye (M-100). MAHLI focus distance affects resolution. Colour calibrated but not radiometrically calibrated in all products.

---

### 11. Perseverance Surface Imagery

| Field | Value |
|---|---|
| **Dataset ID** | `m2020-imagery` |
| **Mission** | Mars 2020 (Perseverance) |
| **Instrument** | Mastcam-Z / SuperCam RMI / SHERLOC-WATSON |
| **Product Type** | Surface imagery |
| **Resolution** | Variable (0.15–7.4 mm/px at 2 m range) |
| **Coverage** | Jezero Crater (M2020 traverse) |
| **Date Range** | 2021–present |
| **CRS** | IAU:49900 |
| **Format** | JPEG / PNG / PDS IMG |
| **Source** | [PDS Imaging Node](https://pds-imaging.jpl.nasa.gov/volumes/m2020.html) |
| **Status** | `registered` |

**Description:** Surface imagery from Perseverance's camera suite including Mastcam-Z (zoomable stereo), SuperCam Remote Micro-Imager, and WATSON (close-up imager), documenting Jezero Crater delta and ancient lakebed geology.

**Limitations:** Mastcam-Z zoom optics provide variable resolution. SuperCam RMI has narrower FOV than Mastcam-Z. Ongoing mission; dataset continuously growing.

---

## Summary by Mission

| Mission | Orbit/Surface | Datasets | Primary Science |
|---|---|---|---|
| Mars Global Surveyor | Orbit | MOLA | Global topography |
| Mars Express | Orbit | HRSC | Regional DTMs |
| Mars Odyssey | Orbit | THEMIS | Thermal mapping |
| Mars Reconnaissance Orbiter | Orbit | HiRISE, CTX, CRISM | High-res imagery, mineralogy |
| Multi-mission | — | USGS SIM 3292 | Global geology |
| MSL (Curiosity) | Surface | RAD, REMS, Imagery | Radiation, weather, geology |
| Mars 2020 (Perseverance) | Surface | Imagery | Astrobiology, sample caching |

---

## Future Data Pipeline (planned)

```
Download          Validate           Process            Serve
   │                 │                  │                 │
   ▼                 ▼                  ▼                 ▼
Fetch from       Schema check       CRS reproject    Tile server
PDS/USGS         Checksum verify    Format convert   REST API
archives         CRS validate       Generate tiles   Map layers
```

Each stage updates `processing_status` in the catalogue, providing an honest audit trail from raw data to served product.
