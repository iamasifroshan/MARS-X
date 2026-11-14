# MARS-X — Research Report: Scale Calibration & Effective Analysis Window Geodesy

## 1. Problem Statement (Correction A)

In raster terrain analysis, requesting an arbitrary physical window diameter (e.g. $W_{\text{target}} = 500\text{ m}$) across datasets with disparate spatial resolutions (e.g. MOLA $128\text{ ppd} \approx 463.08\text{ m/px}$ vs CTX $\approx 20.01\text{ m/px}$) leads to severe discretization discrepancies if effective dimensions are not explicitly tracked.

For MOLA $128\text{ ppd}$:
- A requested scale of $500\text{ m}$ translates to raw pixel count:
  $$\text{raw\_k} = \text{round}\left(\frac{500}{463.08}\right) = 1 \implies k = 3 \text{ pixels}$$
- A $3 \times 3$ kernel at Mars equator ($R = 3,396,190\text{ m}$, $\Delta\phi = 1/128^\circ$) spans:
  $$W_{\text{eff}} = 3 \times 463.08\text{ m} = 1,389.24\text{ m}$$
- Ground footprint area per kernel:
  $$A_{\text{eff}} = (1,389.24\text{ m})^2 \approx 1.93\text{ km}^2$$

Treating a $1,389\text{ m}$ kernel ($1.93\text{ km}^2$) as a $500\text{ m}$ analysis without disclosure constitutes scientific misrepresentation.

---

## 2. Geodetic Metric Formulation

To preserve scientific rigor, MARS-X computes latitudinally dependent metric spacings:
$$\Delta y = R_{\text{polar}} \times \Delta\phi_{\text{rad}}$$
$$\Delta x = R_{\text{eq}} \cos(\phi) \times \Delta\lambda_{\text{rad}}$$

The effective physical analysis properties are formulated as:
1. **Effective Footprint:**
   $$W_{\text{eff}, x} = k \times \Delta x, \quad W_{\text{eff}, y} = k \times \Delta y$$
2. **Effective Ground Area:**
   $$A_{\text{eff}} = \frac{W_{\text{eff}, x} \times W_{\text{eff}, y}}{1,000,000} \text{ km}^2$$
3. **Scale Suitability Classification:**
   - $W_{\text{target}} < \text{resolution}$: `sub_pixel_extrapolation_warning` (kernel clamped to minimum $3 \times 3$; sub-pixel features cannot be resolved).
   - $W_{\text{eff}} / \text{resolution} > 100$: `heavily_coarse` (large spatial aggregation).
   - Otherwise: `optimal`.

---

## 3. Scale Compatibility in Cross-Region Comparisons

When comparing candidate Martian exploration sites (e.g. Region A and Region B), MARS-X evaluates the scale discrepancy between effective footprints:
$$\Delta_{\text{scale}} = \frac{|W_{\text{eff}, A} - W_{\text{eff}, B}|}{\max(W_{\text{eff}, A}, W_{\text{eff}, B})} \times 100\%$$

- **Equivalent Scale:** $\Delta_{\text{scale}} \le 15\%$
- **Approximately Equivalent:** $15\% < \Delta_{\text{scale}} \le 35\%$
- **Non-Equivalent:** $\Delta_{\text{scale}} > 35\%$

This guarantees that scientists comparing topographic slopes and roughness indicators are fully informed of kernel footprint parity.
