# MARS-X — Phase 6.1: Scientific Audit & Pre-Calibration Assessment

**Phase:** 6.1  
**Target:** Pathfinding Scientific Verification & Benchmark Calibration  
**Baseline Git Commit:** `adfe630046a10b5f12ccbc8abe135b20ed69e1fa`  
**Date:** 2026-11-13  
**Status:** In Progress — Repository & Mathematical Audit  

---

## 1. Executive Summary

Phase 6 established the initial terrain-constrained local pathfinding engine using authentic Mars elevation data from MGS MOLA MEGDR 128 ppd tile `megt00n000hb`. While the baseline pathfinding implementation and all 94 test cases passed successfully, scientific verification is required to guarantee that mathematical proofs of optimality, heuristic admissibility, and metric geometry strictly adhere to Mars geodesy and IAU2000 conventions.

This audit report records the pre-implementation inspection of:
1. The mathematical definition of the A* heuristic and its relationship to the non-negative terrain cost surface.
2. Mars-specific metric calculations ($dx$, $dy$, spherical projection radius $R_M$).
3. Terrain edge-cost monotonicity and diagonal corner-cutting safeguards.
4. Coordinate snapping round-trip precision and raster registration.
5. Post-generation route validation constraints.
6. Frontend mission presets within the acquired tile footprint.

---

## 2. Ingested Dataset & Geodetic Baseline

The routing engine operates strictly on authentic MOLA MEGDR data. The dataset attributes confirmed from `megt00n000hb.lbl` and `megt00n000hb.img` are:

| Parameter | Authoritative Value (PDS Label) | Verified Implementation | Status |
|:---|:---|:---|:---|
| **Product Identifier** | `MEGT00N000HB.IMG` | `megt00n000hb.img` | Confirmed |
| **Data Format** | Binary 16-bit MSB integer | `>i2` (big-endian signed 16-bit) | Confirmed |
| **Elevation Units** | Meters relative to GMM-3 Areoid | Direct integers in meters | Confirmed |
| **Grid Dimensions** | 5632 lines × 11520 samples | 5632 × 11520 | Confirmed |
| **Map Projection** | Simple Cylindrical | Equirectangular / Plate Carrée | Confirmed |
| **Projection Reference** | Spherical Mars ($R_A = R_B = R_C = 3,396.0\text{ km}$) | $R_M = 3,396,000.0\text{ m}$ | Confirmed |
| **Map Resolution** | 128.0 pixels/degree ($0.0078125^\circ/\text{px}$) | $1.0 / 128.0 = 0.0078125^\circ$ | Confirmed |
| **Nominal Equat. Scale**| $0.463\text{ km/pixel}$ ($463\text{ m/px}$) | $dy = 463.385\text{ m}$ | Confirmed |
| **Latitude Bounds** | $-44.0^\circ\text{N}$ to $0.0^\circ\text{N}$ | $[-44.0^\circ, 0.0^\circ]$ | Confirmed |
| **Longitude Bounds** | $0.0^\circ\text{E}$ to $90.0^\circ\text{E}$ | $[0.0^\circ, 90.0^\circ]$ | Confirmed |
| **File Checksum** | SHA-256 `f57274b5...` (129,761,280 bytes) | Exact match verified | Confirmed |

---

## 3. Mathematical Audit of A* Heuristic

### 3.1 Prior Implementation Analysis
In Phase 6, `AStarPlanner.heuristic(r, c, goal_r, goal_c)` computed:
$$\Delta y = (r_{\text{goal}} - r) \cdot dy$$
$$\Delta x = (c_{\text{goal}} - c) \cdot dx(r)$$
$$\Delta z = z_{\text{goal}} - z(r, c)$$
$$h = \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2}$$
where $dx(r) = R_M \cos(\phi_r) \Delta\lambda$.

### 3.2 Identified Mathematical Risk
In simple cylindrical projections, east-west ground spacing $dx$ scales strictly as $\cos(\phi)$. 
- At latitude $0^\circ$: $dx \approx 463.38\text{ m}$.
- At latitude $-44^\circ$: $dx \approx 333.33\text{ m}$.

If node $u$ is at a lower absolute latitude (e.g., $0^\circ$) than the goal (e.g., $-44^\circ$), evaluating $dx$ using the latitude of node $u$ overestimates the east-west distance compared to paths that traverse south first and then east at a higher latitude where $dx$ is smaller. 

Under specific geometric conditions, this could cause $h(u) > h^*(u)$, violating strict admissibility, or violate the triangle inequality:
$$h(u) \le c(u, v) + h(v)$$

### 3.3 Calibrated Formulation
To guarantee strict mathematical admissibility ($h(u) \le h^*(u)$) and consistency ($h(u) \le c(u, v) + h(v)$) everywhere on Mars, the heuristic must use a guaranteed lower bound on the 3D surface path length.
On a sphere of radius $R_M = 3,396,000.0\text{ m}$, the great-circle surface distance $D_{\text{gc}}$ between $(\phi_u, \lambda_u)$ and $(\phi_G, \lambda_G)$ represents the absolute shortest surface path. 

Combining great-circle geodesic distance with vertical differential via Minkowski's inequality:
$$a = \sin^2\left(\frac{\phi_G - \phi_u}{2}\right) + \cos\phi_u \cos\phi_G \sin^2\left(\frac{\lambda_G - \lambda_u}{2}\right)$$
$$D_{\text{gc}} = 2 R_M \arcsin\left(\min(1.0, \sqrt{\max(0.0, a)})\right)$$
$$h(u, G) = 0.999 \times \sqrt{D_{\text{gc}}^2 + (z_G - z_u)^2}$$

The factor $0.999$ ensures that even with slight tangent-plane discretization effects along diagonal steps, $h(u) \le c(u, v) + h(v)$ holds with guaranteed positive slack for every possible edge, while maintaining $99.9\%$ heuristic tightness.

---

## 4. Terrain Edge Cost & Physical Model Audit

### 4.1 Cost Formulation
The edge traversal cost is defined as:
$$C(u, v) = L(u, v) \times \left(1.0 + w_s f_s + w_r f_r + w_l f_l + w_c f_c\right)$$
Where:
- $L(u, v) = \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2}$ is the physical 3D metric length of the edge.
- All penalty factors $f_s, f_r, f_l, f_c \in [0.0, 1.0]$.
- All weights $w_i \ge 0.0$.

### 4.2 Monotonicity & Conservation
- Since $\sum w_i f_i \ge 0.0$, the penalty multiplier is $\ge 1.0$, guaranteeing $C(u, v) \ge L(u, v) > 0$ for all passable edges.
- Diagonal corner-cutting checks prevent paths from cutting through corners bounded by impassable obstacles.
- Physical elevation conservation holds: $\sum \Delta z = z_{\text{dest}} - z_{\text{start}}$.

---

## 5. Frontend Route Preset Audit

The 3 mission presets in `frontend/src/components/panels/RoutePlanning.tsx` were inspected against the authentic raster:

1. **Preset 1: Sinus Meridiani Plain**
   - Start: $-2.00^\circ\text{N}, 5.00^\circ\text{E}$ (slope $0.85^\circ$, passable).
   - Dest: $-2.15^\circ\text{N}, 5.18^\circ\text{E}$ (slope $1.12^\circ$, passable).
   - Status: **Confirmed valid & fully passable.**

2. **Preset 2: Margaritifer Terra Crater Corridor**
   - Start: $-4.00^\circ\text{N}, 8.00^\circ\text{E}$ (slope $1.20^\circ$, passable).
   - Dest: $-4.12^\circ\text{N}, 8.16^\circ\text{E}$ (slope $25.49^\circ$, **IMPASSABLE** - exceeds $15^\circ$ max slope).
   - Audit Finding: Destination coordinate lands directly on a steep crater rim scarp.
   - Required Correction: Shift destination to $-4.08^\circ\text{N}, 8.08^\circ\text{E}$ along the passable valley floor ($2.83^\circ$ slope), preserving the scientific intent of "navigating valley networks avoiding crater scarps".

3. **Preset 3: Schiaparelli Basin Approach Corridor**
   - Start: $-3.00^\circ\text{N}, 15.00^\circ\text{E}$ (slope $0.64^\circ$, passable).
   - Dest: $-3.10^\circ\text{N}, 15.15^\circ\text{E}$ (slope $0.79^\circ$, passable).
   - Status: **Confirmed valid & fully passable.**

---

## 6. Verification & Implementation Plan

1. **Heuristic Hardening:** Update `AStarPlanner.heuristic` in `backend/app/routing/astar.py` to use precomputed trigonometric row/col tables and spherical great-circle + vertical lower bound with $\alpha = 0.999$.
2. **Validator Enhancement:** Add exact elevation conservation and edge-cost validity assertions to `RouteValidator`.
3. **Preset Calibration:** Update `RoutePlanning.tsx` Preset 2 coordinates to $(-4.08^\circ, 8.08^\circ)$.
4. **Comprehensive Test Suite:** Implement `test_phase6_1_pathfinding.py` covering:
   - Heuristic admissibility and consistency over thousands of random trials.
   - Exact optimality equivalence between A* and Dijkstra.
   - 4-corridor real-MOLA benchmark harness (5 iterations each for median runtimes and expansion ratios).
5. **Research Deliverables:** Produce all 5 formal verification reports in `docs/research/`.
