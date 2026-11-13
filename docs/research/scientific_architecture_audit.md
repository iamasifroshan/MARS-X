# MARS-X — Scientific Architecture Audit Report

**Date:** 2026-11-13  
**Status:** Completed  
**Subject:** Scientific Data Integrity, Planetary Reference Systems, and Terrain Engine Ingestion Readiness  

---

## 1. Executive Summary

A comprehensive scientific audit of the MARS-X codebase was conducted across metadata repositories, coordinate reference system definitions, and service boundaries. The purpose is to guarantee that subsequent terrain analysis, slope calculation, and EVA Marswalk planning rest upon verifiable planetary geodesy and peer-reviewed NASA/ESA data products rather than ungrounded assumptions.

---

## 2. Confirmed Scientific Facts

| Topic | Confirmed Geodetic & Cartographic Fact | Authoritative Evidence |
|---|---|---|
| **Mars Reference Dimensions** | Equatorial radius $a = 3,396,190\text{ m}$ ($3,396.19\text{ km}$); Polar radius $b = 3,376,200\text{ m}$ ($3,376.20\text{ km}$); Flattening $f = 1/169.8$ ($0.005886$). | IAU/IAG Working Group on Cartographic Coordinates and Rotational Elements (Archinal et al., 2018). |
| **MOLA MEGDR Topography Datum** | Elevation values in MOLA MEGDR (`megt_*.img`) are measured in metres relative to the **MOLA Areoid**, defined by the Mars50c spherical harmonic gravity solution with an average equatorial radius of $3,396.0\text{ km}$ on a reference sphere of radius $R = 3,396.190\text{ km}$. | Smith et al. (2001), Neumann et al. (2001), NASA PDS Geosciences Node. |
| **Latitude Convention** | Modern NASA PDS Mars orbital products (MOLA, HRSC, CTX, HiRISE) standardize on **planetocentric latitude** ($\phi_c$, angle from planetary center to point) rather than planetographic latitude ($\phi_g$, surface normal). | USGS Astrogeology Cartographic Standards; PDS Standards Reference v3.8 / v4.0. |
| **Longitude Convention** | All modern orbital Mars missions standardize on **positive East longitude** ($0^\circ \text{ to } 360^\circ$, or $-180^\circ \text{ to }+180^\circ$ centered on $0^\circ$), with the prime meridian defined by the small crater Airy-0 inside Sinus Meridiani. | IAU 2000 / 2015 recommendations; Davies et al. (1994). |
| **Raster Data Decoupling** | Visual shaded-relief imagery (8-bit RGB/grayscale) encodes simulated solar hillshade irradiance and **cannot be used for quantitative terrain elevation, slope, or rugosity calculations**. Floating-point numerical Digital Terrain Models (DTMs) are strictly mandatory. | Planetary GIS best practices; USGS Open-File Report 2014-1141. |

---

## 3. Uncertain Facts & Clarifications

### 3.1 CRS Identification: `EPSG:104905` vs `ESRI:104905` vs `IAU:49900`
- **Audit Finding:** The EPSG (European Petroleum Survey Group, now IOGP) registry is historically restricted to terrestrial (Earth) reference systems. Neither `EPSG:104905` nor `EPSG:49900` are official IOGP EPSG codes.
- **Clarification:**
  - `104905` is an **ESRI Well-Known ID (WKID)**: `ESRI:104905` corresponds to `Mars_2000_Equidistant_Cylindrical`.
  - NASA Mars Trek WMTS lists `urn:ogc:def:crs:EPSG::104905` or `EPSG:104905` in its `GetCapabilities` XML as a de facto identifier by prepending `EPSG` to the ESRI WKID.
  - In modern PROJ 7+ / GDAL 3+, the official authority code is `IAU_2015:49900` (geographic) or `IAU_2000:49900`.
- **System Correction:** The backend geospatial registry must register `IAU:49900`, `IAU_2015:49900`, `ESRI:104905`, and alias `EPSG:104905` with full WKT2 / PROJ string definitions so that GDAL/Rasterio lookups succeed across all formats.

### 3.2 Planetocentric vs Planetographic Discrepancy
- **Audit Finding:** On an oblate body like Mars ($f \approx 0.005886$), planetocentric ($\phi_c$) and planetographic ($\phi_g$) latitudes differ according to:
  $$\tan \phi_g = \frac{a^2}{b^2} \tan \phi_c \approx 1.0118 \tan \phi_c$$
  The maximum difference occurs at $\phi \approx 45^\circ$, where:
  $$|\phi_g - \phi_c| \approx 0.339^\circ \approx 20.1\text{ km on the Martian surface}$$
- **System Correction:** All coordinate parsing and raster ingestion algorithms must explicitly check coordinate metadata labels. Any dataset reporting planetographic coordinates must be converted before computing distance, slope, or spatial overlay against planetocentric DTMs.

---

## 4. Dataset-Specific Corrections Required

| Dataset ID | Current Representation | Authoritative Correction | Justification |
|---|---|---|---|
| `mola-megdr` | `IAU:49900`, Format: "Binary tables / GeoTIFF" | Format: "PDS3 IMG / GeoTIFF". Datum: IAU 2000 Mars Sphere ($R=3,396,190\text{ m}$), Areoid vertical datum. | MOLA MEGDR native product is 16-bit binary with PDS3 label (`.lbl` + `.img`). GeoTIFF is the standard secondary distribution. |
| `hrsc-dtm` | Coverage: "Significant portions" | Coverage: Regional swaths covering $\approx 50\%\text{--}70\%$ of surface; MC-11 quadrangle mosaics. | HRSC is not global contiguous; individual orbit strips have variable convergence angles and lighting. |
| `hirise-rdr` | Coverage: "~3%" | Coverage: $< 0.1\%$ for stereo DTM products ($3\%$ applies only to monoscopic image footprints). DTM pixel resolution is $1\text{--}2\text{ m/px}$, not $0.25\text{ m/px}$. | Stereopair acquisition requires overlapping passes; photogrammetric DTM generation requires post-processing with ISIS/ASP. |
| `ctx-edr` | Product: "Orbital imagery", DTM not differentiated | Differentiate CTX EDR (imagery, 6 m/px, $>99\%$ coverage) from CTX Stereo DTMs (regional, 18–24 m/px). | Raw CTX images are monoscopic; DTMs require stereo pairs processed with NASA Ames Stereo Pipeline. |

---

## 5. Service Readiness Matrix

| Service | Stated Status | Audited Actual State | Required Status | Action |
|---|---|---|---|---|
| `dataset_catalogue` | `ok` | Fully implemented, 11 real datasets validated against schema. | `ok` | Maintain |
| `geospatial` | `ready` | Basic constants present; needs PROJ/WKT aliases and planetocentric converters. | `active` | Upgrade with PROJ definitions in Stage B |
| `terrain` | `pending_raster_engine` | Initial models present; rasterio installed. | `active_engine` | Implement Rasterio/NumPy raster inspection & processing |
| `routing` | `pending_engine` | Data models defined; pathfinding not yet built. | `pending_engine` | Keep as pending (Phase 3) |
| `science` | `ready` | Target models defined. | `ready` | Maintain |
| `mission` | `ready` | EVA models defined. | `ready` | Maintain |
| `ai` | `foundation_stub` | Stub models defined. | `foundation_stub` | Maintain |

---

## 6. Scientific Constraints for Terrain Engine (Phase 2)

1. **NoData Value Integrity:**
   - NoData values (e.g. $-32768$ in MOLA MEGDR, $-3.40282\times 10^{38}$ in 32-bit float DTMs) must **never** be coerced to $0.0\text{ m}$ or treated as valid Martian elevation.
   - Treating missing data as $0\text{ m}$ elevation creates false datum-level plains with catastrophic false-slope artifacts ($>80^\circ$ vertical cliffs) at data boundaries.
2. **Latitudinal Metric Distortion (Equirectangular):**
   - In equirectangular projections (Plate Carrée), east-west ground distance per degree of longitude shrinks with latitude:
     $$\Delta x = R \cdot \cos(\phi) \cdot \Delta \lambda_{\text{rad}}$$
   - Any gradient, slope, or roughness calculation must compute the local cell width in physical metres using $\cos(\phi)$ at each row, rather than assuming constant Cartesian square pixels.

