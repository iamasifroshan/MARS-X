# MARS-X — Phase 7: Initial Scientific & Repository Audit Report

**Phase:** 7  
**Target:** Multi-Resolution Mars Terrain Intelligence & Mission Planning  
**Baseline Git Commit:** `f4f69811f5d6f6e5a6f2cf30a1bf6439e44ef1f8`  
**Date:** 2026-11-13  
**Status:** Initial Audit Completed — Pre-Implementation Baseline Established  

---

## 1. Executive Summary

Phase 6 and 6.1 established a single-tile terrain-constrained route planning prototype on Mars Global Surveyor (MGS) MOLA MEGDR 128 ppd tile `megt00n000hb`. While the single-tile routing engine achieved mathematical optimality (0.0000% difference between A* and Dijkstra) and passed all 107 automated backend tests, the application remains restricted to a single regional quadrant (Lat `[-44°, 0°]`, Lon `[0°, 90°E]`).

Phase 7 expands MARS-X into a true multi-resolution Mars terrain intelligence platform by establishing a scientifically controlled terrain hierarchy:
1. **Tier 1 (Global Coarse):** MOLA 4 ppd (`megt90n000cb.img`, 14.8 km/px) — fully ingested baseline.
2. **Tier 2 (Global/Regional Base):** MOLA 128 ppd (`megt00n000hb.img`, 463 m/px) — acquired, with expansion to neighboring quadrants.
3. **Tier 3 (Regional Controlled DTM):** MRO Context Camera (CTX) numerical stereo DTMs (20 m/px) — acquiring authentic USGS Astrogeology controlled COGs.
4. **Tier 4 (Local Tactical DTM):** MRO High Resolution Imaging Science Experiment (HiRISE) numerical DTMs (1 m/px) — cataloguing authentic stereo DTMs with strict datum traceability.

---

## 2. Baseline Dataset Inventory & Physical Raster Availability

Before initiating Phase 7, the physical files in `data/raw/` were verified:

| Dataset ID | Instrument | Product File | Size (Bytes) | SHA-256 Hash | Physical Raster Available? | Validation State |
|:---|:---|:---|:---:|:---:|:---:|:---|
| `mola-megdr-4` | MGS MOLA | `megt90n000cb.img` | 2,073,600 | `25f16fb7...` | **YES** | Scientifically Validated |
| `mola-megdr-128` | MGS MOLA | `megt00n000hb.img` | 129,761,280 | `f57274b5...` | **YES** | Scientifically Validated |
| `hrsc-dtm-mc11` | MEX HRSC | *(None)* | 0 | None | **NO** | Registered (Metadata only) |
| `ctx-dtm-jezero` | MRO CTX | *(None)* | 0 | None | **NO** | Registered (Metadata only) |
| `hirise-dtm-jezero`| MRO HiRISE | *(None)* | 0 | None | **NO** | Registered (Metadata only) |

### Key Audit Finding on Coverage:
- Jezero Crater (`18.4°N, 77.5°E`) lies north of the equator, entirely outside the currently acquired MOLA tile (`megt00n000hb`, Lat `[-44°, 0°]`). Therefore, earlier catalog entries for Jezero CTX and HiRISE DTMs cannot overlap the currently acquired MOLA tile.
- To demonstrate authentic multi-resolution analysis and route planning, high-resolution DTMs must be acquired within the actual acquired planning area (Lat `[-44°, 0°]`, Lon `[0°, 90°E]`).

---

## 3. Mandatory A* Prerequisite Review

In Phase 6.1, the A* heuristic was rigorously audited and proven:
$$h(u, G) = \alpha \cdot \sqrt{D_{\text{gc}}(u, G)^2 + (z_G - z_u)^2}$$
Where:
- $D_{\text{gc}}(u, G) = 2 R_M \arcsin(\min(1.0, \sqrt{\max(0.0, a)}))$ is the great-circle surface distance on the spherical projection datum ($R_M = 3,396,000.0\text{ m}$).
- $\alpha = 0.999$ is a scaling constant ensuring $h(u) \le c(u, v) + h(v)$ with guaranteed positive slack against grid metric variation ($dx = dy \cos\phi$) and floating-point discretization.
- Admissibility ($h \le h^*$) holds unconditionally because:
  1. $D_{\text{gc}}(u, G) \le \sum L_{\text{horiz}}$ (great-circle is the shortest surface curve).
  2. $|z_G - z_u| \le \sum |\Delta z|$ (absolute vertical sum).
  3. By Minkowski's inequality: $\sqrt{D_{\text{gc}}^2 + (\Delta z)^2} \le \sum \sqrt{L_{\text{horiz}}^2 + \Delta z^2} = \sum L \le \sum C$.

**Operational Constraint for Multi-Resolution Routing:**
The spherical great-circle lower bound $h(u, G)$ is mathematically valid for single-grid uniform simple cylindrical graphs. When routing across heterogeneous multi-resolution grids (e.g. transitioning from 463 m MOLA to 20 m CTX), the graph edge definitions and coordinate frames change. Therefore:
1. Multi-resolution routing must not naively resample coarse data to fine grids.
2. Regional graph partitioning or boundary-stitched hierarchical routing must be used.
3. Unverified heuristics across resolution boundaries must default to Dijkstra ($h = 0$) until explicit admissibility proofs are constructed.

---

## 4. Current CRS & Geodesy Registry

| Product Family | Projection | Horizontal Reference | Vertical Reference | Longitude Direction |
|:---|:---|:---|:---|:---|
| MOLA MEGDR | Simple Cylindrical | Spherical Mars ($R = 3,396.0\text{ km}$) | MOLA GMM-3 Areoid (deg 50) | East ($0^\circ$ to $360^\circ$) |
| USGS Controlled CTX | Equidistant Cylindrical | Spherical Mars ($R = 3,396.19\text{ km}$) | MOLA Areoid (`pc_align` tied) | East ($0^\circ$ to $360^\circ$) |
| HiRISE PDS DTM | Equirectangular | Spherical Mars ($R = 3,396.19\text{ km}$) | MOLA Areoid (`pc_align` tied) | East ($0^\circ$ to $360^\circ$) |

---

## 5. Planned Phase 7 Implementation Steps

1. **Stage 1: MOLA Expansion Analysis:** Document the complete 16-tile inventory, calculate storage requirements, and model cross-tile topological adjacency.
2. **Stage 2: Real CTX DTM Ingestion:** Acquire authentic USGS Astrogeology Controlled MRO CTX DTM (`P21_009323_...`, 20 m/px) overlapping MOLA tile `megt00n000hb` (Lat `[-5.19°, -4.00°]`, Lon `[66.04°, 66.62°]`).
3. **Stage 3: Multi-Resolution Validation Lifecycle:** Implement formal 10-state lifecycle engine (`registered`, `discovered`, `downloaded`, `integrity_verified`, `geospatially_validated`, `scientifically_validated`, `analysis_ready`).
4. **Stage 4: CRS & Vertical Datum Harmonization:** Implement rigorous datum checking, preserving native rasters and prohibiting unjustified datum offsets.
5. **Stage 5: Multi-Resolution Terrain Catalog:** Spatial query engine supporting point, bbox, and polygon intersections, sorting by resolution, and calculating genuine valid-data overlap.
6. **Stage 6: Multi-Resolution Terrain Analysis:** Comparative analysis of overlapping MOLA and CTX terrain (elevation delta, slope, roughness, scale effects).
7. **Stage 7: Resolution-Aware Routing Architecture:** Design dataset selection and graph transition constraints.
8. **Stage 8: REST API Layer:** Expose product availability, coverage queries, and comparison endpoints.
9. **Stage 9: Frontend Mission-Control Dashboard:** Multi-resolution inspection deck, coverage visualizer, and datum compatibility indicators.
10. **Stage 10: Pytest Suite & Production Build:** End-to-end automated verification.

