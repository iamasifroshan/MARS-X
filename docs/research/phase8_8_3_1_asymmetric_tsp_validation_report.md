# Phase 8.8.3.1 Closure Report: Asymmetric TSP Optimization & Multi-Stop Traverse Integrity Audit

**Project:** MARS-X — Interplanetary Survival Guide: Martian Map (NASA Space Apps Challenge 2026)  
**Baseline Git Commit:** `5943b0c` (`phase8.8.3: implement multi-stop science traverse optimization`)  
**Validation Target:** Asymmetric TSP Optimization, Optional/Mandatory Stop Exclusion, Geometric Continuity, and Analytical Telemetry Integrity  
**Status:** VALIDATED & COMPLIANT

---

## 1. Executive Summary & Audit Baseline

Phase 8.8.3 introduced multi-stop science traverse optimization to the MARS-X platform, connecting multiple scientific discoveries and waypoints into traversable routes over bounded digital elevation models (HiRISE, CTX, and MOLA).

Phase 8.8.3.1 conducts a rigorous mathematical and scientific audit of the multi-stop engine, addressing critical requirements in directed graph pathfinding:
1. **Asymmetric 2-Opt Formulation:** Directed terrain cost matrices inherently exhibit asymmetry ($C(u, v) \ne C(v, u)$) because A* edge costs evaluate destination-cell slopes and elevation deltas. Reversing a tour section alters internal directed edge traversal directions. The optimizer is validated to re-evaluate the full directed sequence cost along candidate tours rather than relying on symmetric shortcut deltas.
2. **Exact Reference Oracle ($K \le 4$):** For $K \le 4$ intermediate science stops ($\le 24$ permutations), the system executes an exact brute-force permutation search as a reference oracle, demonstrating an empirical **$0.0\%$ optimality gap** between 2-opt and global optimum solutions.
3. **Optional vs Mandatory Stop Semantics:** If an optional stop is blocked by terrain (slope $> \theta_{\max}$ or NoData), it is safely isolated into `unreachable_stops` with a specific reason, and the active traverse continues across all reachable waypoints with status `partial`. Unreachable mandatory stops strictly reject the request with `ValueError`.
4. **GeoJSON LineString Continuity:** All pairwise legs are assembled into a single continuous GeoJSON `LineString` with strict junction vertex deduplication ($N_{\text{total}} = \sum |L_i| - (M - 1)$), eliminating consecutive duplicate vertices.
5. **Telemetry Disaggregation:** Physical 3D surface ground distance is mathematically disaggregated from graph optimization cost.
6. **Bitwise Elevation Benchmark Preservation:** All three authoritative IEEE 754 Float32 elevation benchmarks (`0x4508d7c3`, `0xc5372c4c`, `0xc48d849f`) remain bitwise identical with zero drift.
7. **Coordinate Notation Standards:** All coordinate outputs strictly follow signed format (`-4.600°`) or cardinal suffix (`4.600°S`), completely avoiding prohibited hybrid notations (`-4.600°S`).

---

## 2. Asymmetric 2-Opt Mathematical Formulation & Proof

### 2.1 The Asymmetric Traveling Explorer Problem (ATSP)

In the standard symmetric Traveling Salesperson Problem (TSP), distance or cost between two locations is invariant under direction: $C(u, v) = C(v, u)$. However, on Martian terrain, the cost function evaluated along an A* edge from cell $u$ to adjacent cell $v$ is directional:

$$\text{cost}(u \to v) = \Delta s_{uv} \times \left(1 + \beta \left(\frac{\theta_v}{\theta_{\text{ref}}}\right)^2\right)$$

Because the slope penalty depends on the destination cell slope $\theta_v$ and uphill vs downhill energy expenditure varies with gradient, the resulting pairwise shortest path cost between science waypoints $W_a$ and $W_b$ is asymmetric:

$$C(W_a, W_b) \ne C(W_b, W_a)$$

### 2.2 Reversal Flaw in Naive 2-Opt

In standard symmetric 2-opt, reversing a tour segment $W_i \to \dots \to W_j$ removes two boundary edges $(W_{i-1}, W_i)$ and $(W_j, W_{j+1})$ and adds $(W_{i-1}, W_j)$ and $(W_i, W_{j+1})$. In symmetric graphs, the cost of all internal edges $W_k \to W_{k+1}$ remains unchanged because $C(u, v) = C(v, u)$.

In an asymmetric cost matrix, reversing the sequence $W_i, W_{i+1}, \dots, W_j$ reverses every single directed edge within the subsequence:

$$C_{\text{reversed internal}} = \sum_{m=i}^{j-1} C(W_{m+1}, W_m) \ne \sum_{m=i}^{j-1} C(W_m, W_{m+1})$$

A naive symmetric 2-opt implementation that only evaluates boundary changes will miscalculate the move value, frequently accepting suboptimal moves or rejecting true improvements.

### 2.3 MARS-X ATSP Evaluation Architecture

In `MultiStopPlanner.optimize_stop_sequence`, whenever a 2-opt reversal is evaluated:
```python
candidate = cur_sequence[:i] + cur_sequence[i : j + 1][::-1] + cur_sequence[j + 1 :]
cand_cost = eval_sequence_cost(candidate)
```
Where `eval_sequence_cost` traverses the complete directed chain from `start_stop` through each stop in sequence to `dest_stop`:
$$C(\text{Tour}) = C(\text{Start}, W_{\pi(1)}) + \sum_{m=1}^{K-1} C(W_{\pi(m)}, W_{\pi(m+1)}) + C(W_{\pi(K)}, \text{Dest})$$

### 2.4 Empirical Verification on Strongly Asymmetric Matrix

A synthetic 4-node problem with extreme directional bias was evaluated:
- $C(S, W_1) = 10, C(W_1, W_2) = 10, C(W_2, D) = 10 \implies C(\text{Forward}) = 30.0$
- $C(S, W_2) = 100, C(W_2, W_1) = 200, C(W_1, D) = 100 \implies C(\text{Reverse}) = 400.0$

When initialized with the suboptimal sequence $[W_2, W_1]$ (cost 400.0), the MARS-X optimizer evaluated the internal reversed edge cost $C(W_1, W_2) = 10.0$ and successfully inverted the sequence to $[W_1, W_2]$, achieving the global minimum cost of $30.0$ with an optimality gap of $0.0\%$.

---

## 3. Exact Permutation Reference Oracle ($K \le 4$)

To guarantee optimal scientific routing for tactical field excursions ($K \le 4$ intermediate stops), the planner evaluates all $K!$ permutations:
- $K = 1$: $1$ permutation
- $K = 2$: $2$ permutations
- $K = 3$: $6$ permutations
- $K = 4$: $24$ permutations

For $K \le 4$, the exact permutation search acts as an in-line oracle. Both the nearest-neighbor greedy path, the 2-opt local search path, and the exact permutation path are computed.

### Benchmark Results ($K \le 4$):

| Intermediate Stops ($K$) | Permutations Evaluated | Initial NN Cost | 2-Opt Cost | Exact Optimum Cost | Optimality Gap (%) | Result Strategy |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | 1 | 240.00 | 240.00 | 240.00 | **0.00%** | `exact_permutation` |
| **2** | 2 | 385.00 | 340.00 | 340.00 | **0.00%** | `exact_permutation` |
| **3** | 6 | 530.00 | 480.00 | 480.00 | **0.00%** | `exact_permutation` |
| **4** | 24 | 695.00 | 620.00 | 620.00 | **0.00%** | `exact_permutation` |

For $K > 4$, the system transitions to `nearest_neighbor_2opt` with explicit documentation in `computation_metrics` stating that the solution is a polynomial-time heuristic approximation.

---

## 4. Optional vs Mandatory Stop Semantics & Exclusion Rules

Science mission planning requires distinguishing non-negotiable mission goals from opportunistic targets.

### Rules Implemented:
1. **Mandatory Stops ($is\_mandatory = True$):**
   - If terrain slope exceeds $\theta_{\max}$ or crosses NoData zones such that no feasible path enters or leaves a mandatory stop, the request is immediately aborted with a descriptive `ValueError`:
     ```
     Mandatory science stop 'Impassable Cliff' (mandatory-cliff) at (4.6020°S, 66.3200°E) is unreachable within slope threshold 5.0° or DEM coverage.
     ```
2. **Optional Stops ($is\_mandatory = False$):**
   - If an optional stop is impassable, it is excluded from `stops` and logged in `unreachable_stops` with the exact terrain reason.
   - The traverse continues planning with all remaining reachable waypoints.
   - The response status is marked as `partial`.
3. **Capacity Constraints ($max\_stops$):**
   - If the requested stops exceed `max_stops`, all mandatory stops are preserved first, and optional stops are trimmed to fit remaining capacity.
   - If mandatory stops alone exceed `max_stops`, a `ValueError` prompts the user to increase capacity or designate non-essential stops as optional.

---

## 5. GeoJSON LineString Continuity & Junction Deduplication

When combining $M$ pairwise A* route legs $L_1, L_2, \dots, L_M$ into a continuous traverse LineString, the terminal coordinate of leg $L_i$ is identical to the initial coordinate of leg $L_{i+1}$:

$$L_i[-1] \equiv L_{i+1}[0]$$

A naive concatenation causes duplicate vertices at every waypoint junction, creating rendering artifacts, double-counted distances in spatial analysis tools, and invalid network topology.

### Deduplication Logic:
```python
if not connected_coordinates:
    connected_coordinates.extend(leg_coords)
else:
    if leg_coords[0] == connected_coordinates[-1]:
        connected_coordinates.extend(leg_coords[1:])
    else:
        connected_coordinates.extend(leg_coords)
```

### Invariant Verified:
$$|C_{\text{connected}}| = \sum_{i=1}^M |L_i| - (M - 1)$$
Unit tests verified zero consecutive duplicate vertices across all multi-stop traverse configurations.

---

## 6. Analytical Telemetry Disaggregation

Telemetry fields provide rigorous separation between physical planetary measurements and optimization parameters:

| Field | Dimension | Physical Meaning |
|---|---|---|
| `total_surface_distance_m` | Metres ($m$) | True 3D physical ground distance $\sum \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2}$ |
| `total_horizontal_distance_m` | Metres ($m$) | 2D planimetric distance $\sum \sqrt{\Delta x^2 + \Delta y^2}$ |
| `total_optimization_cost` | Dimensionless | Total A* graph traversal cost $\sum \text{edge\_cost}$ |
| `mean_route_slope_deg` | Degrees ($^\circ$) | Distance-weighted average slope: $\frac{\sum (d_i \times \bar{\theta}_i)}{\sum d_i}$ |
| `max_route_slope_deg` | Degrees ($^\circ$) | Strict supremum slope: $\max_i \theta_{i,\max}$ |

---

## 7. Bitwise Elevation Benchmark Preservation & Coordinate Standards

### 7.1 Authoritative Elevation Benchmarks (IEEE 754 Float32)

All three Mars elevation benchmark samples were verified bitwise:

| Region | Instrument | Target Coord | Raw Float32 Value | IEEE 754 Hex | Display | Status |
|---|---|---|---|---|---|---|
| **Tyrrhena Terra** | CTX DTM (~20 m/px) | `(-4.600°, 66.317°E)` | `+2189.485107421875` | `0x4508d7c3` | `+2189.49 m` | **BITWISE EXACT** |
| **Apollinaris Sulci** | CTX DTM (~20 m/px) | `(4.700°, 168.250°E)` | `-2930.7685546875` | `0xc5372c4c` | `-2930.77 m` | **BITWISE EXACT** |
| **Holden Crater** | HiRISE DTM (~1.01 m/px) | `(-28.500°, 309.020°E)` | `-1132.1444091796875` | `0xc48d849f` | `-1132.14 m` | **BITWISE EXACT** |

### 7.2 Coordinate Notation Rule Adherence
- Valid forms: `4.600°S` or `-4.600°` (never `-4.600°S`).
- Positive forms: `4.700°N` or `+4.700°` (never `+4.700°N`).
- Longitude: strictly in planetocentric $0^\circ \dots 360^\circ\text{E}$ or signed $\pm 180^\circ$.

---

## 8. Verification & Test Suite Summary

- **Phase 8.8.3.1 Validation Suite (`test_phase8_8_3_1_validation.py`):** 11 passed in 1.35s
- **Phase 8.8.3 Multi-Stop Suite (`test_phase8_8_3_multi_stop.py`):** 17 passed in 2.99s
- **Frontend Production Build (`next build`):** 0 errors, static export ready
- **Total Backend Tests:** 374+ tests passing
