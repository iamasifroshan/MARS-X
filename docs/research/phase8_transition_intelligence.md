# Phase 8: Multi-Resolution Overlap and Transition Intelligence

**Author:** Planetary Geospatial Systems Architect & Photogrammetry Specialist  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Problem Statement: Seamless Mosaic Fallacy

A frequent error in planetary software is the naive stitching or blending of heterogeneous elevation rasters (e.g. merging a $20\text{ m}$ CTX GeoTIFF onto a $463\text{ m}$ MOLA base). Naive stitching creates:
1. **Artificial Seam Steps:** Discontinuities at raster borders caused by vertical datum offsets or localized photogrammetric tilt.
2. **Horizontal Datum Misalignment:** Mismatches between spherical datums ($R = 3,396,000\text{ m}$ for MOLA vs $R = 3,396,190\text{ m}$ for IAU 2015 CTX, generating a $55.95\text{ ppm}$ scale drift).
3. **Resolution Ratio Jumps:** Connecting route nodes directly across a $23.1\times$ resolution boundary causes algorithmic path distortion.

The Transition Intelligence Engine (`backend/app/terrain/resolution_transition.py`) replaces naive merging with rigorous compatibility audits and **Hierarchical Spatial Partitioning**.

---

## 2. Transition Compatibility Classification

When evaluating Product A ($r_A$) and Product B ($r_B$):
1. **`compatible`:** Identical CRS, identical vertical datum, valid overlap, and both present locally.
2. **`compatible_with_documented_transformation`:** Overlapping footprints with documented vertical tie procedures (e.g. CTX DTM tied to MOLA PEDR via ASP `pc_align` and $55.95\text{ ppm}$ IAU scale drift).
3. **`incompatible`:** Irreconcilable vertical datums (e.g. unreferenced stereo models) or unsupported projections.
4. **`insufficient_overlap`:** Footprint intersection area $< 0.1\text{ km}^2$.
5. **`unknown`:** Undocumented vertical or horizontal metadata.

---

## 3. Hierarchical Spatial Partitioning Strategy

Rather than generating an uncalibrated merged raster, the engine outputs an explicit **Region Partitioning Strategy**:
- **High-Resolution Infill:** The finer product (e.g. CTX $20\text{ m/px}$) is designated for core high-interest zones inside its valid data polygon.
- **Regional Context Surround:** The coarser baseline (e.g. MOLA $463\text{ m/px}$) provides contextual framing outside the high-res swath.
- **Boundary Buffer:** A minimum buffer width of $2 \times r_{\text{coarse}} = 926.2\text{ m}$ is enforced along the border to prevent edge artifacts.

---

## 4. Operation Governance Matrix

| Operation | Compatible / Documented | Incompatible / Insufficient |
| :--- | :--- | :--- |
| **Side-by-side comparison** | ✓ Permitted | ✓ Permitted |
| **Region partitioning** | ✓ Permitted | ✗ Forbidden |
| **Multi-scale profiling** | ✓ Permitted | ✗ Forbidden |
| **Residual elevation sampling** | ✓ Permitted | ✗ Forbidden |
| **Cross-resolution pathfinding** | ⚠ Constrained to validated nodes | ✗ Strictly Forbidden |
| **Direct raster mosaic/stitching** | ✗ Strictly Forbidden | ✗ Strictly Forbidden |
| **Upsampling coarse to fine** | ✗ Strictly Forbidden | ✗ Strictly Forbidden |
