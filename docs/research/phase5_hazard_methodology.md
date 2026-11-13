# MARS-X — Terrain Hazard Intelligence Methodology (Phase 5)

## 1. Principles & Strict Constraints
1. **Explainability Over Black-Box Models:** All hazard indicators are computed using transparent geodetic equations and documented mathematical algorithms.
2. **No Astronaut Safety Claims:** Topographical complexity indicators evaluate ground shape only. They do NOT evaluate geotechnical soil shear strength, subsurface ice stability, space suit kinematics, or metabolic energy limits.
3. **Strict NoData Propagation:** NoData cells (-32768 or NaN) propagate through neighborhood calculations and yield `insufficient_data`, never a false low-risk score.

## 2. Mathematical Formulations

### 2.1 Metric Ground Spacing & Latitude Scaling
Because Martian meridians converge toward the poles, the East-West cell dimension ($dx$) shrinks with the cosine of latitude:

$$dy = \frac{\pi}{180} R_M \Delta\phi$$
$$dx = \frac{\pi}{180} R_M \cos(\phi) \Delta\lambda$$

Where $R_M = 3,396,190\text{ m}$ (Mars mean equatorial radius). To avoid polar division-by-zero singularities, $\cos\phi$ is capped at a minimum value ($10^{-6}$).

### 2.2 Horn (1981) Gradient & Slope
Using a $3 \times 3$ moving elevation window:

$$\begin{bmatrix} z_1 & z_2 & z_3 \\ z_4 & z_5 & z_6 \\ z_7 & z_8 & z_9 \end{bmatrix}$$

The orthogonal elevation partial derivatives are computed via Horn's weighted kernel:

$$\frac{\partial z}{\partial x} = \frac{(z_3 + 2z_6 + z_9) - (z_1 + 2z_4 + z_7)}{8 \cdot dx}$$

$$\frac{\partial z}{\partial y} = \frac{(z_1 + 2z_2 + z_3) - (z_7 + 2z_8 + z_9)}{8 \cdot dy}$$

$$\text{Slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$

### 2.3 Local Relief & Roughness
- **Local Relief ($\Delta z$):** $\max(z_i) - \min(z_i)$ in metres within the analysis window.
- **Roughness ($\sigma_z$):** Unbiased sample standard deviation:

$$\sigma_z = \sqrt{\frac{1}{N - 1} \sum_{i=1}^N (z_i - \bar{z})^2}$$

### 2.4 Topographical Discontinuity Detection
Candidate scarps, crater rims, and structural terrace breaks are flagged when:
- $\text{Slope} \ge 25.0^\circ$ and $\Delta z \ge 75.0\text{ m}$ (Major scarp or crater rim wall)
- $\text{Slope} \ge 18.0^\circ$ and $\Delta z \ge 40.0\text{ m}$ (Moderate slope break)
- $\sigma_z \ge 25.0\text{ m}$ (Chaotic terrain boundary)

### 2.5 Explainable Complexity Classification
- **Low Measured Complexity:** $\text{Slope} < 8.0^\circ$, $\Delta z < 10.0\text{ m}$, $\sigma_z < 2.5\text{ m}$
- **Moderate Complexity:** $\text{Slope} \ge 8.0^\circ$ or $\Delta z \ge 10.0\text{ m}$ or $\sigma_z \ge 2.5\text{ m}$
- **High Complexity:** $\text{Slope} \ge 15.0^\circ$ or $\Delta z \ge 30.0\text{ m}$ or $\sigma_z \ge 8.0\text{ m}$
- **Extreme Complexity:** $\text{Slope} \ge 25.0^\circ$ or $\Delta z \ge 75.0\text{ m}$ or $\sigma_z \ge 20.0\text{ m}$
- **Insufficient Data:** Assigned whenever confidence score $< 0.2$ or center/neighboring pixels contain NoData.
