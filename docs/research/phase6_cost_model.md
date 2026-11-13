# MARS-X — Terrain Cost Model & Hazard Penalties (Phase 6)

## 1. Mathematical Formulation
Edge traversal cost between nodes $u$ and $v$ is formulated as:

$$C(u, v) = L(u, v) \cdot \left[1 + \sum_{k} w_k f_k(v)\right]$$

### 1.1 Physical Ground Distance ($L$)
Mars terrain distance incorporates the 3D surface topography:

$$L(u, v) = \sqrt{(\Delta x)^2 + (\Delta y)^2 + (\Delta z)^2}$$

Where:
$$\Delta y = (r_2 - r_1) \cdot \frac{\pi}{180} R_M \cdot \Delta\phi$$
$$\Delta x = (c_2 - c_1) \cdot \frac{\pi}{180} R_M \cos(\phi) \cdot \Delta\lambda$$
$$\Delta z = z(r_2, c_2) - z(r_1, c_1)$$

### 1.2 Soft Hazard Penalties
- **Normalized Slope Penalty ($f_s$):**
  $$f_s = \min\left(\frac{S_v}{S_{\max}}, 1.0\right)$$
  Smoothly penalizes steep climbs while remaining strictly bounded below $S_{\max}$.
- **Normalized Roughness Penalty ($f_r$):**
  $$f_r = \min\left(\frac{\sigma_{z, v}}{10.0\text{ m}}, 1.0\right)$$
  Penalizes terrain with high local elevation variance (blocky or dissected ground).
- **Normalized Local Relief Penalty ($f_l$):**
  $$f_l = \min\left(\frac{\Delta z_v}{40.0\text{ m}}, 1.0\right)$$
  Penalizes cells located near abrupt elevation terraces or scarp breaks.
- **Terrain Complexity Category Penalty ($f_c$):**
  $$f_c = \begin{cases} 1.0 & \text{if } \text{complexity is high or extreme} \\ 0.3 & \text{if } \text{complexity is moderate} \\ 0.0 & \text{if } \text{complexity is low} \end{cases}$$

---

## 2. Default Mission Weights
- Slope Weight ($w_s = 2.0$): Primary weight prioritizing traversable valley floors over ridge crests.
- Roughness Weight ($w_r = 1.5$): Steers traverses away from heavily cratered or chaotic surfaces.
- Relief Weight ($w_l = 1.0$): Discourages paths near cliff edges.
- Complexity Weight ($w_c = 1.5$): Penalizes cells flagged with multi-criteria complexity triggers.
