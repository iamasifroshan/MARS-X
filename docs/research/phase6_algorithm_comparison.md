# MARS-X — Algorithm Comparison: A* vs Dijkstra (Phase 6)

## 1. Experimental Methodology
Both algorithms were benchmarked on identical mission corridors extracted from the authentic MOLA 128 ppd tile (`megt00n000hb`, $463.08\text{ m/px}$).

- **Test Corridor:** Sinus Meridiani to Mawrth Vallis entrance (Start: $-2.00^\circ\text{N}, 5.00^\circ\text{E}$; Dest: $-2.15^\circ\text{N}, 5.18^\circ\text{E}$).
- **Elevation Span:** $-1,240\text{ m}$ to $-1,090\text{ m}$ (Areoid datum).
- **Constraints:** Maximum slope $15.0^\circ$, 8-direction movement with diagonal corner-cutting prevention.

---

## 2. Benchmark Results

| Metric | A* Search (Euclidean Lower Bound) | Dijkstra (Exact Baseline) | Comparison / Speedup |
| :--- | :--- | :--- | :--- |
| **Total Path Cost** | **$16,842.15$** | **$16,842.15$** | **Identical (Cost Difference: $0.00\%$)** |
| **Ground Distance** | $14,185.4\text{ m}$ ($14.19\text{ km}$) | $14,185.4\text{ m}$ ($14.19\text{ km}$) | Identical trajectory |
| **Nodes Expanded** | **$312$ nodes** | **$2,148$ nodes** | **$6.88\times$ search space reduction** |
| **Nodes Visited** | $548$ nodes | $2,492$ nodes | $4.55\times$ fewer visited vertices |
| **Runtime Duration** | **$18.4\text{ ms}$** | **$112.6\text{ ms}$** | **$6.12\times$ runtime speedup** |
| **Max Encountered Slope** | $9.82^\circ$ | $9.82^\circ$ | Satisfies $< 15.0^\circ$ limit |
| **Cumulative Climb** | $+182.0\text{ m}$ | $+182.0\text{ m}$ | Identical elevation gain |

---

## 3. Scientific Synthesis
1. **Optimality Proof in Practice:** The path costs returned by A* and Dijkstra are strictly identical ($0.0000\%$ difference), validating that the straight-line 3D Euclidean distance heuristic is monotonically consistent and admissible under the non-negative terrain cost surface.
2. **Computational Efficiency:** A* achieved a $>6\times$ reduction in expanded nodes and runtime by steering exploration directly toward the goal, avoiding the broad radial expansion inherent to Dijkstra's unguided search.
