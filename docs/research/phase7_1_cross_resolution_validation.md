# MARS-X — Phase 7.1 Research: Cross-Resolution Elevation Validation & Multi-Support Sampling

## 1. Objectives

This study independently reproduces and evaluates the cross-resolution elevation comparison between the authentic MOLA 128 ppd regional altimetry tile (`megt00n000hb`) and the authentic USGS Controlled CTX numerical DTM (`P21_009323_1754_XN_04S293W...`).

Two distinct sampling methodologies were implemented and compared:
- **Method A:** Point Sampling with coordinate snapping.
- **Method B:** Common-Support / Cell Aggregation (spatial pooling of high-resolution cells into MOLA footprints).

---

## 2. Sign Convention Declaration

All elevation differences are formally defined using the following standard geodetic convention:
$$\Delta z = z_{\text{CTX}} - z_{\text{MOLA}}$$

- A **negative difference ($\Delta z < 0$)** indicates that the high-resolution CTX elevation is **lower** than the regional MOLA elevation.
- A **positive difference ($\Delta z > 0$)** indicates that CTX is **higher** than MOLA.

*(Note: Previous Phase 7 documentation contained an inadvertent sign inversion in the narrative text label $\mu_{\Delta z} = \text{MOLA} - \text{CTX} = -45.58\text{ m}$. The underlying code and true numerical result have always been $z_{\text{CTX}} - z_{\text{MOLA}} < 0$).*

---

## 3. Comparison Results

### 3.1 Method A — Point Sampling
Points were sampled across the confirmed overlap footprint with spatial bounds $[-5.137^\circ, -4.053^\circ]$ Latitude and $[66.086^\circ, 66.567^\circ\text{E}]$ Longitude.
- In a $15 \times 15$ candidate grid ($225$ points), invalid pixels outside the valid stereo swath were filtered, leaving **$184$ valid, spatially distributed evaluation points**:

| Metric | Measured Value |
| :--- | :--- |
| **Sample Points Count** | 184 |
| **Mean CTX Elevation ($z_{\text{CTX}}$)** | $+1,996.59\text{ meters}$ |
| **Mean MOLA Elevation ($z_{\text{MOLA}}$)** | $+2,054.16\text{ meters}$ |
| **Mean Difference ($\mu_{\Delta z} = z_{\text{CTX}} - z_{\text{MOLA}}$)** | **$-57.57\text{ meters}$** |
| **Median Difference** | **$-54.98\text{ meters}$** |
| **Standard Deviation ($\sigma_{\Delta z}$)** | **$51.79\text{ meters}$** |
| **Root Mean Square Error (RMSE)** | **$77.44\text{ meters}$** |
| **Mean Absolute Error (MAE)** | **$65.48\text{ meters}$** |
| **25th Percentile** | $-71.64\text{ meters}$ |
| **75th Percentile** | $-41.96\text{ meters}$ |
| **Min Difference / Max Difference** | $-258.82\text{ meters}$ / $+184.04\text{ meters}$ |

### 3.2 Method B — Common-Support / MOLA Pixel Aggregation
To address spatial support disparity ($20\text{ m/px}$ vs $463\text{ m/px}$), all valid CTX pixels falling within each MOLA $1/128^\circ \times 1/128^\circ$ footprint ($\sim 530\text{ CTX pixels per cell}$) were aggregated by mean and median.
- Evaluated across **$1,877$ full MOLA grid cells** each containing $\ge 100$ valid CTX returns:

| Metric | Measured Value |
| :--- | :--- |
| **MOLA Cells Evaluated** | 1,877 |
| **Mean Cell-Aggregated CTX Elevation** | $+1,996.71\text{ meters}$ |
| **Mean Regional MOLA Elevation** | $+2,052.47\text{ meters}$ |
| **Mean Difference ($\mu_{\Delta z} = \bar{z}_{\text{CTX, agg}} - z_{\text{MOLA}}$)** | **$-55.76\text{ meters}$** |
| **Median Difference** | **$-55.68\text{ meters}$** |
| **Standard Deviation ($\sigma_{\Delta z}$)** | **$46.49\text{ meters}$** |
| **Root Mean Square Error (RMSE)** | **$72.60\text{ meters}$** |
| **Mean Absolute Error (MAE)** | **$63.46\text{ meters}$** |
| **Min Difference / Max Difference** | $-282.44\text{ meters}$ / $+403.25\text{ meters}$ |

---

## 4. Key Scientific Findings

1. **Robust Convergence Across Methodologies:**
   Both point sampling ($-57.57\text{ m}$) and common-support area aggregation ($-55.76\text{ m}$) demonstrate that the mean elevation delta is consistent to within $1.8\text{ meters}$ regardless of sampling geometry.
2. **Standard Deviation Reduction Under Aggregation:**
   Spatial aggregation reduces variance ($\sigma$ drops from $51.79\text{ m}$ to $46.49\text{ m}$), confirming that a portion of the point-sampling variance represents high-frequency sub-pixel terrain relief resolved by CTX that averages out over the $463\text{ m}$ MOLA cell.
3. **Physical Morphological Drivers:**
   In Tyrrhena Terra, deep impact craters and dendritic dissection channels drop up to $250\text{ meters}$ below the regional plateau, explaining the negative minimum delta ($-282.4\text{ m}$). Conversely, narrow crater rim crests and central peaks rise up to $400\text{ meters}$ above the smoothed MOLA baseline, explaining the positive maximum delta ($+403.2\text{ m}$).
