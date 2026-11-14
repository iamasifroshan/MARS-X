# Phase 8: Scientific Limitations & Operational Boundaries

**Author:** Planetary Geodesist & Mission Assurance Lead  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Spatial Resolution Limits

1. **Global MOLA MEGDR ($463.08\text{ m/px}$, $14.8\text{ km/px}$):**
   - Nyquist spatial frequency limit is $\sim 1.15\text{ km}$.
   - Small topographic hazards (boulders, small impact craters $< 1\text{ km}$, crevasses, sand dunes) are completely invisible in MOLA altimetry.
2. **Regional USGS CTX DTM ($20.01\text{ m/px}$):**
   - Minimum resolvable feature size is $\sim 50\text{ m}$.
   - Meter-scale landing hazards (sub-10m boulders, small rover wheel entrapments) cannot be detected.
3. **HiRISE Micro-Topography ($1.01\text{ m/px}$):**
   - High-resolution data is strictly remote/discovered in MARS-X (0 local bytes on disk).
   - The platform never fabricates or interpolates micro-scale features from coarser datasets.

---

## 2. Geodetic & Coordinate Reference System Discrepancies

1. **Sphere Radius Offset:**
   - MOLA MEGDR Simple Cylindrical assumes a spherical body of radius $R = 3,396,000\text{ m}$.
   - Modern USGS CTX GeoTIFF products use the IAU 2015 Mars sphere ($R = 3,396,190\text{ m}$).
   - The resulting scale variance is $55.95\text{ ppm}$ ($3.93\text{ m}$ across the CTX latitude span). Direct sub-pixel raster sampling must account for this discrepancy.
2. **Vertical Reference Model:**
   - MOLA Areoid represents the Martian geoid defined by the Goddard Mars Model 3 (GMM-3) gravity field to degree 50.
   - Stereophotogrammetric DTMs adjusted via Ames Stereo Pipeline (`pc_align`) are tied to MOLA point clouds, but local photogrammetric tilt and ICP residual variances ($\sim 50\text{-}70\text{ m}$) remain.

---

## 3. Strict Operational Non-Claims

- **No Astronaut EVA Clearance:** MARS-X paths represent mathematical graph-cost minimizations across orbital DTMs; they are **not** validated astronaut life-support or walking-energy routes.
- **No Rover Hazard Probabilities:** Complexity classes (`low`, `moderate`, `high`) are morphological descriptions, not certified traversability probabilities.
- **No Artificial Continuous Rasters:** Disjoint products are managed through spatial partitioning rather than uncalibrated continuous mosaics.
