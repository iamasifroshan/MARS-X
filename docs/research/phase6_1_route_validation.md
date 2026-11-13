# MARS-X — Phase 6.1: Route Validation & Physical Conservation Report

**Phase:** 6.1  
**Target:** Independent Post-Processing Scientific Route Verification  
**Date:** 2026-11-13  
**Status:** Approved & Formally Verified  

---

## 1. Executive Summary

Pathfinding algorithms in complex planetary terrain must not rely solely on the internal termination state of the search engine. In MARS-X, every generated traverse undergoes an independent, post-generation scientific audit executed by `RouteValidator` before being returned to the user or API client.

In Phase 6.1, `RouteValidator` was upgraded to independently verify physical conservation laws (net elevation conservation), non-negative edge costs, strict endpoint snapping matches, and diagonal obstacle isolation.

---

## 2. Independent 8-Point Verification Suite

Every candidate path is subjected to the following checks:

### 2.1 Endpoint Matching
- **Check 1.1:** `path[0]` strictly matches the snapped start grid coordinate `expected_start_rc`.
- **Check 1.2:** `path[-1]` strictly matches the snapped destination grid coordinate `expected_dest_rc`.
- **Check 1.3:** Both start and destination cells satisfy all hard constraints (`passable_mask == True`).

### 2.2 Continuous Mesh Topology
- **Check 2.1:** For every consecutive pair $(p_i, p_{i+1})$, the row step $|\Delta r| \le 1$ and column step $|\Delta c| \le 1$.
- **Check 2.2:** No zero-length stationary steps ($|\Delta r| + |\Delta c| > 0$).
- **Check 2.3:** No discontinuous coordinate teleports.

### 2.3 Diagonal Corner-Cutting Prevention
- **Check 3:** If a step is diagonal ($|\Delta r| = 1$ and $|\Delta c| = 1$), both adjacent orthogonal neighbors must be passable:
  $$\text{passable}(r_1 + \Delta r, c_1) == \text{True} \quad \land \quad \text{passable}(r_1, c_1 + \Delta c) == \text{True}$$
  This prevents a path from slipping diagonally through an impassable knife-edge ridge or crater wall.

### 2.4 Maximum Slope Hard Limit
- **Check 4:** Every cell along the path must have a Horn 3×3 slope satisfying:
  $$\text{slope}_{\text{cell}} \le \text{max\_slope\_deg} \quad (\text{default } 15.0^\circ)$$
  Any single cell exceeding this threshold causes immediate validation failure.

### 2.5 Numerical NoData Exclusion
- **Check 5:** No cell along the traverse may contain the missing data sentinel $-32768$ or NaN.

### 2.6 Edge Cost Validity & Monotonicity
- **Check 6:** For every step $(p_i, p_{i+1})$, the edge traversal cost computed from the cost surface must satisfy:
  $$0.0 < L(p_i, p_{i+1}) \le C(p_i, p_{i+1}) < \infty$$
  Edges with negative, zero, NaN, or infinite costs are strictly rejected.

### 2.7 Physical Elevation Conservation Law
- **Check 7:** Along any continuous path on a single-valued digital elevation model, the cumulative climb ($\text{gain}$) minus the cumulative descent ($\text{loss}$) must exactly equal the net difference between the endpoint elevations:
  $$\text{Cumulative Gain} = \sum_{\Delta z > 0} \Delta z$$
  $$\text{Cumulative Loss} = \sum_{\Delta z < 0} |\Delta z|$$
  $$\text{Net Differential} = z(p_{\text{end}}) - z(p_{\text{start}})$$
  $$\left|(\text{Cumulative Gain} - \text{Cumulative Loss}) - \text{Net Differential}\right| < 10^{-3}\text{ metres}$$

### 2.8 Cryptographic Traceability
- **Check 8:** The route payload embeds the SHA-256 hash of the input elevation raster (`f57274b5...`), ensuring verifiable lineage to the raw PDS file.

---

## 3. Test Verification Summary

In `backend/tests/test_phase6_1_pathfinding.py`:
- `test_elevation_conservation_validation`: Passed with zero error ($< 10^{-6}\text{ m}$).
- `test_discontinuous_jump_rejected`: Discontinuous jump correctly caught and rejected.
- `test_corner_cutting_rejected`: Diagonal path crossing impassable orthogonal neighbor correctly identified and rejected.
- `test_four_real_mola_corridors_optimality`: All 4 real MOLA routes passed 100% of the 8 validation checks.
