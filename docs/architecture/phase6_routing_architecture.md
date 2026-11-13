# MARS-X — Routing Architecture & Graph Engine (Phase 6)

## 1. System Architecture
The MARS-X pathfinding subsystem evaluates candidate traverses on authentic planetary elevation models through a decoupled, multi-tier pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Route Planning Service                      │
├──────────────────────────────┬──────────────────────────────────┤
│     Terrain Grid Builder     │       Terrain Cost Surface       │
│  - np.memmap Window Access   │  - Metric distance L             │
│  - Geodesic Coordinate Snap  │  - Multiplicative penalties      │
│  - Footprint Boundary Guard  │  - Hard slope / NoData limits    │
├──────────────────────────────┴──────────────────────────────────┤
│                    Pathfinding Algorithms                       │
│  - A* Planner (Admissible 3D Euclidean lower bound heuristic)   │
│  - Dijkstra Baseline (Exact optimality benchmark)               │
├─────────────────────────────────────────────────────────────────┤
│                  Validation & Explainability                    │
│  - Independent Step-by-Step Geodesic Route Validator            │
│  - Elevation Gain/Loss and Roughness Statistics                 │
│  - Feature Detectability & Regional Resolution Disclaimers      │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Terrain Cost Model Formulation
Edge cost between adjacent cells $u$ and $v$ is formulated as:

$$C(u, v) = L(u, v) \cdot \left[1 + w_s f_s(v) + w_r f_r(v) + w_l f_l(v) + w_c f_c(v)\right]$$

Where:
- $L(u, v) = \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2}$ is the physical 3D ground distance in metres.
- $f_s(v) = \min(S_v / S_{\max}, 1.0)$ is the normalized slope penalty.
- $f_r(v) = \min(\sigma_z / 10.0, 1.0)$ is the normalized local roughness penalty.
- $f_l(v) = \min(\Delta z / 40.0, 1.0)$ is the normalized local relief penalty.
- $f_c(v)$ is the discrete complexity category penalty ($1.0$ for high/extreme, $0.3$ for moderate, $0.0$ for low).
- Weights $w_s, w_r, w_l, w_c \ge 0$.

### Hard Impassable Constraints:
- $S_v > S_{\max}$ (slope exceeds threshold, e.g. $15.0^\circ$).
- Cell elevation is NoData ($-32768$ or NaN).
- Cell is outside the validated raster footprint (Lat $[-44^\circ, 0^\circ]$, Lon $[0^\circ, 90^\circ\text{E}]$).
- Cell is within an active exclusion zone.
- Diagonal corner cutting across impassable orthogonal neighbors is strictly blocked.

## 3. A* Heuristic Admissibility & Consistency
Because $L(u, v)$ is the physical metric Euclidean distance and all penalty multipliers satisfy $1 + \sum w_i f_i \ge 1.0$, the cost $C(u, v) \ge L(u, v)$ for all passable edges.

The heuristic $h(u, \text{goal}) = \sqrt{(x_{\text{goal}} - x_u)^2 + (y_{\text{goal}} - y_u)^2 + (z_{\text{goal}} - z_u)^2}$ represents straight-line 3D Euclidean distance. By the triangle inequality on $\mathbb{R}^3$, $h(u) \le L(u, v) + h(v) \le C(u, v) + h(v)$. Thus, $h$ is strictly **admissible** ($h(u) \le h^*(u)$) and **monotonically consistent**, guaranteeing that A* finds the globally optimal path matching Dijkstra's baseline cost.
