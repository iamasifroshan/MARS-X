# MARS-X — Route Validation Report (Phase 6)

## 1. Validation Architecture
Every candidate route produced by MARS-X undergoes an automated 8-point post-processing audit via `RouteValidator` before being returned to the client or rendered on the map.

## 2. Mandatory Verification Criteria
1. **Start & Goal Registration:** Traverses must begin and terminate at coordinates matching the accepted snapped pixel centers.
2. **Coverage Footprint Integrity:** All route vertices must lie strictly inside the validated tile boundary ($[-44^\circ, 0^\circ]\text{N}, [0^\circ, 90^\circ]\text{E}$).
3. **NoData Rejection:** Paths crossing NoData sentinels ($-32768$ or NaN) are immediately rejected. No artificial bridging or elevation interpolation is permitted.
4. **Maximum Slope Conformance:** Every step along the traverse must have a local slope $\le S_{\max}$ (default $15.0^\circ$).
5. **Corner-Cutting Guard:** Diagonal moves between $(r_1, c_1)$ and $(r_2, c_2)$ are rejected if either orthogonal neighbor is impassable.
6. **Continuous Mesh Topology:** Waypoints must form an unbroken chain of adjacent 4-way or 8-way grid neighbors.
7. **Distance & Elevation Conservation:** Cumulative ground distance must equal the geodesic sum of metric steps; elevation gain and loss must match endpoint profile differentials.
8. **Cryptographic Traceability:** The output payload records the SHA-256 hash of the input elevation raster (`f57274b5...`).
