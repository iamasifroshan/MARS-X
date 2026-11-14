# Phase 8: Adaptive Route-Planning & Corridor Integration

**Author:** Autonomous Route-Planning Engineer & Navigation Specialist  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Preservation of Phase 6 Baseline Algorithms

The Phase 6 routing architecture—comprising $A^*$ with admissible Minkowski 3D geodesic heuristics and Dijkstra for exact optimality baselines—remains untouched and verified:
- **Heuristic Admissibility:** $h(u, G) = 0.999 \times \sqrt{D_{\text{gc}}(u, G)^2 + (z_G - z_u)^2}$
- **Consistency Guarantee:** $h(u) \le c(u, v) + h(v)$ across latitude-dependent metric grid cells.
- **Cost Formulation:** $C(u, v) = L \times (1 + w_s f_s + w_r f_r + w_l f_l + w_c f_c)$ with hard slope blocking $> 15.0^\circ$.

---

## 2. Adaptive Corridor Terrain Source Selection

Prior to building a cost graph or expanding pathfinding search nodes, the new service method `evaluate_corridor_terrain_source` in `MarsRouteService` interrogates the requested traverse corridor:
1. **Corridor Envelope Derivation:**
   $$\phi_{\min} = \min(\phi_s, \phi_d) - 0.05^\circ, \quad \phi_{\max} = \max(\phi_s, \phi_d) + 0.05^\circ$$
   $$\lambda_{\min} = \min(\lambda_s, \lambda_d) - 0.05^\circ, \quad \lambda_{\max} = \max(\lambda_s, \lambda_d) + 0.05^\circ$$
2. **Great-Circle Distance Computation:**
   $$D = \text{haversine\_distance}(\phi_s, \lambda_s, \phi_d, \lambda_d)$$
3. **Availability & Footprint Containment:**
   - Evaluates whether $\text{Start}$ and $\text{Destination}$ lie fully within the active validated planning footprint (e.g. `megt00n000hb`).
   - If either endpoint or any corridor segment crosses into un-downloaded territory, the route is flagged as `routing_eligible: false` with explicit segment rejection reasons.
4. **Resolution Assignment:**
   - Reports the primary supporting dataset ID, native resolution ($463.08\text{ m/px}$ or $20.01\text{ m/px}$), horizontal CRS, vertical datum, and datum compatibility.

---

## 3. Strict Navigation Safeguards

- **No Gap Bridging:** The planner refuses to connect route nodes across NoData gaps or unsupported resolution boundaries.
- **Scale Normalization:** Costs computed at high resolution ($20\text{ m}$) cannot be aggregated with coarse cells ($463\text{ m}$) without scale normalization.
- **Zero Astronaut Safety Claims:** All generated paths represent algorithmic mathematical terrain-cost optimizations on orbital altimetry, and must never be interpreted as operational EVA or astronaut navigation approvals.
