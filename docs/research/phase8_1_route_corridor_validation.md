# MARS-X — Research Report: Multi-Tier Route Corridor Coverage Validation

## 1. Problem Statement (Correction D)

In autonomous Marswalk planning, determining whether an elevation raster is suitable to support a traverse cannot rely merely on whether the start and destination points fall inside the dataset's rectangular bounding box.

A bounding box may show 95% global data coverage, but:
- The route centerline trajectory could cross an unacquired tile seam or NoData void.
- The pathfinding corridor buffer (e.g. 1,000 m clearance envelope) could extend into unsupported terrain, producing edge clipping and discontinuous cost graphs.

---

## 2. Multi-Tier Corridor Metrics Implementation

In `backend/app/routing/route_service.py`, `evaluate_corridor_terrain_source` was extended with a three-tier coverage evaluation:

### 2.1 Centerline Linear Trajectory Sampling
The direct geodesic path between $(\phi_{\text{start}}, \lambda_{\text{start}})$ and $(\phi_{\text{dest}}, \lambda_{\text{dest}})$ is discretized into 20 equidistant sample coordinates:
$$\phi(t) = \phi_{\text{start}} + t(\phi_{\text{dest}} - \phi_{\text{start}}), \quad t \in [0, 1]$$
$$\lambda(t) = \lambda_{\text{start}} + t(\lambda_{\text{dest}} - \lambda_{\text{start}})$$

Each point is checked against the active validated raster footprint:
$$\text{centerline\_valid\_coverage\_pct} = \frac{N_{\text{valid}}}{N_{\text{samples}}} \times 100\%$$
$$\text{nodata\_intersections} = N_{\text{samples}} - N_{\text{valid}}$$

### 2.2 Buffered Corridor Envelope Coverage
The corridor clearance buffer ($W_{\text{buf}} = 1,000\text{ m}$) defines the operational traverse search space. The corridor envelope coverage is formulated as:
$$\text{corridor\_envelope\_valid\_coverage\_pct} = \min(\text{centerline\_valid\_coverage\_pct}, \text{bounding\_box\_valid\_coverage\_pct})$$

### 2.3 Strict Eligibility Gate
A corridor is designated `routing_eligible = True` and `continuous_traversable_graph_supported = True` if and only if:
1. Start coordinate is inside validated footprint.
2. Destination coordinate is inside validated footprint.
3. Centerline valid coverage $\ge 99.0\%$ ($N_{\text{nodata}} = 0$).
4. Bounding-box coverage $\ge 90.0\%$.

If any criterion fails, unsupported trajectory segments are explicitly listed in `unsupported_segments`, and the corridor is rejected before attempting graph extraction.
