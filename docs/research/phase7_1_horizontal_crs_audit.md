# MARS-X — Phase 7.1 Research: Horizontal CRS & Planetary Reference Sphere Audit

## 1. Comparative Reference System Analysis

The cross-resolution pipeline compares elevation products originating from two distinct planetary coordinate frameworks:

1. **MOLA MEGDR 128 ppd Reference System:**
   - Map Projection: Simple Cylindrical (Equirectangular)
   - Planetary Datum: Spherical Mars
   - Reference Radius: $R_{\text{MOLA}} = 3,396,000\text{ meters}$ ($3,396.0\text{ km}$)
   - Standard Parallel: $0.0^\circ$ (Equator)
   - Coordinate System: Areocentric Latitude, Positive-East Longitude ($0^\circ\text{ to }360^\circ\text{E}$)
   - Angular Pixel Spacing: $1/128^\circ \approx 0.0078125^\circ$ ($463.08\text{ m/px}$ at equator)

2. **USGS Controlled CTX DTM Reference System (`IAU:49910`):**
   - Map Projection: Equidistant Cylindrical (Equirectangular)
   - Planetary Datum: Mars (2015) Sphere / Ocentric
   - Reference Radius: $R_{\text{CTX}} = 3,396,190\text{ meters}$ ($3,396.19\text{ km}$)
   - Standard Parallel: $0.0^\circ$ (Equator)
   - Central Meridian: $0.0^\circ$
   - Coordinate Units: Linear meters on projection plane ($x, y$)

---

## 2. Geodetic Discrepancy Quantification ($\Delta R = 190\text{ meters}$)

The difference between the historical MOLA sphere radius ($3,396,000\text{ m}$) and the IAU 2015 sphere radius ($3,396,190\text{ m}$) is exactly:
$$\Delta R = 190\text{ meters}$$

### 2.1 Relative Scale Factor
$$\frac{\Delta R}{R} = \frac{190}{3,396,000} \approx 5.5945 \times 10^{-5} \quad (0.005595\% \text{ or } 55.95\text{ ppm})$$

### 2.2 Linear Ground Distance per Degree of Arc
- **On MOLA Sphere ($R = 3,396,000\text{ m}$):**
  $$1^\circ = \frac{\pi}{180} \times 3,396,000\text{ m} = 59,271.85\text{ meters}$$
- **On IAU:49910 Sphere ($R = 3,396,190\text{ m}$):**
  $$1^\circ = \frac{\pi}{180} \times 3,396,190\text{ m} = 59,275.17\text{ meters}$$
- **Linear Discrepancy per Degree:**
  $$\Delta d = 59,275.17 - 59,271.85 = \mathbf{3.316\text{ meters per degree}}$$

### 2.3 Impact on the CTX Overlap Swath
Over the geographic dimensions of the CTX swath:
- Latitude Span: $\Delta \phi = 1.18425^\circ \implies \Delta y_{\text{scale}} = 1.18425 \times 3.316\text{ m} = \mathbf{3.93\text{ meters}}$
- Longitude Span: $\Delta \lambda = 0.58111^\circ \implies \Delta x_{\text{scale}} = 0.58111 \times 3.316\text{ m} \times \cos(-4.6^\circ) = \mathbf{1.92\text{ meters}}$

### 2.4 Resolution Consequence and Pixel Budget
- Native CTX pixel spacing is $20.0128\text{ meters}$.
- The maximum scaling difference over the entire swath ($3.93\text{ m}$) is **$0.196\times$ (less than one-fifth) of a single CTX pixel**.
- Native MOLA pixel spacing is $463.08\text{ meters}$.
- The maximum scaling difference is **$0.0085\times$ (less than 1%) of a single MOLA pixel**.

### 2.5 Geodetic Safeguard
While sub-pixel at regional scale, MARS-X does not silently ignore this difference.
- Coordinate conversions between angular coordinates and linear projection coordinates explicitly use $R = 3,396,190\text{ m}$ when indexing `IAU:49910` CTX rasters, and $R = 3,396,000\text{ m}$ when computing MOLA angular grid indices.
- This dual-datum handling prevents artificial sub-pixel accumulation across long traverse profiles.
