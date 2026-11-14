# Phase 8: Resolution-Aware Data Selection Engine

**Author:** Planetary Geospatial Systems Architect & Remote Sensing Specialist  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Objective and Architectural Role

The Resolution Selection Engine (`backend/app/terrain/resolution_selector.py`) serves as the gatekeeper for all analytical and navigation workflows in MARS-X. Planetary terrain exploration faces a stark asymmetry: global coverage is coarse (MOLA 463 m/px, 14.8 km/px), regional photogrammetric coverage is selective (USGS CTX 20 m/px), and high-resolution imaging (HiRISE 1 m/px) is confined to sparse, unacquired targets.

The engine prevents two fatal failure modes:
1. **The Upsampling Fallacy:** Interpolating a coarse DEM (e.g. bicubic resampling of MOLA 463 m) and pretending it resolves micro-craters or boulders.
2. **The Discovered-Data Hallucination:** Selecting discovered or catalogued datasets (e.g. HiRISE Schiaparelli or Jezero Delta) that have zero local raster bytes on disk.

---

## 2. Mathematical Selection Logic

The selector evaluates candidate elevation products from `MULTI_RESOLUTION_DTM_CATALOG` through five sequential filtration and ranking stages:

### Stage 1: Physical Availability Gate
A dataset is immediately disqualified for numerical analysis if its authentic raster file is not present on local storage:
$$\text{is\_eligible} \leftarrow \text{is\_local\_raster\_available}(\text{product\_id})$$
HiRISE products (status `discovered`, 0 bytes on disk) are permanently flagged as unavailable for numerical computation.

### Stage 2: Spherical Footprint Intersection
The intersection between the requested bounding box $B_{\text{req}} = [\phi_1, \phi_2] \times [\lambda_1, \lambda_2]$ and product footprint $B_{\text{prod}}$ is computed on the Mars sphere ($R = 3,396.19\text{ km}$):
$$\text{Area}(B) = R^2 (\lambda_2 - \lambda_1)(\sin\phi_2 - \sin\phi_1)$$
$$\text{Coverage Percentage} = \min\left(100.0, \frac{\text{Area}(B_{\text{req}} \cap B_{\text{prod}})}{\text{Area}(B_{\text{req}})} \times 100\right)$$
Datasets with $< 1\%$ overlap are disqualified with an explicit `footprint` stage rejection reason.

### Stage 3: Lifecycle and Validation Gate
Only datasets in states `analysis_ready`, `sample_ingested`, or `ingested` are approved when scientific validation is requested. Unverified remote entries are rejected with full lifecycle provenance.

### Stage 4: Scale Suitability Scoring
Rather than naively picking the finest resolution available (which might have 5% coverage or be inappropriate for a 50 km regional survey), the engine evaluates suitability relative to the target scale $S_{\text{target}}$:
$$\text{Ratio} = \frac{\max(r_{\text{native}}, S_{\text{target}})}{\min(r_{\text{native}}, S_{\text{target}})}$$
$$\text{Scale Score} = \max\left(0.0, 1.0 - 0.15 \times \log_2(\text{Ratio})\right)$$

### Stage 5: Composite Multi-Criteria Ranking
Eligible products are ranked by composite score combining scale suitability ($60\%$) and footprint coverage ($40\%$):
$$\text{Score}_{\text{composite}} = 0.60 \times \text{Scale Score} + 0.40 \times \min\left(1.0, \frac{\text{Coverage Pct}}{\text{Min Coverage Required}}\right)$$

---

## 3. Empirical Verification Results

1. **Regional Survey Query (Valles Marineris Plain $[-10^\circ, -5^\circ\text{N}], [20^\circ, 25^\circ\text{E}]$):**
   - Candidate: `mola-megdr-128` (463.08 m/px) selected with $100\%$ coverage.
   - Lifecycle: `sample_ingested`. Local presence: `megt00n000hb.lbl`.
2. **Micro-Scale Tactical Query (Schiaparelli Basin $[-1.11^\circ, -0.77^\circ\text{N}], [13.80^\circ, 13.92^\circ\text{E}]$):**
   - Candidate: `hirise-dtm-schiaparelli` (1.01 m/px).
   - Result: Disqualified at `availability` stage (0 local bytes; status `discovered`). Selector fell back to validated MOLA 128 tile.
3. **Hazard Assessment Query (Melas Chasma $[-4.80^\circ, -4.50^\circ\text{N}], [66.10^\circ, 66.40^\circ\text{E}]$):**
   - Candidate: `ctx-dtm-p21-009323` (20.01 m/px).
   - Result: Selected with $100\%$ coverage, `analysis_ready` status, and $55.95\text{ ppm}$ IAU scale drift recorded.
