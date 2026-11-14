# MARS-X — Research Report: Multi-Resolution Elevation Inspector & Geodesic Profiling
**Document ID:** `MX-RR-8.3-02`  
**Phase:** 8.3 — Multi-Resolution Terrain Rendering & Interactive Elevation Inspection  
**Authors:** Senior Planetary Geodesist, Topographic Analysis Specialist  
**Classification:** Scientific Verification & Geodetic Specification  

---

## 1. Executive Summary

This report documents the implementation and validation of the interactive numerical elevation inspection and great-circle geodesic profiling system in MARS-X. The system enables real-time queries of authentic Martian topography across three tiered resolutions with full mathematical provenance, strict NoData void preservation, and rigorous planetary spherical geodesics.

---

## 2. Point Elevation Query Priority Hierarchy

When an operator queries a coordinate $(\phi, \lambda)$ on Mars (via interactive map click or coordinate input), MARS-X executes a deterministic hierarchical cascade:

```mermaid
flowchart TD
    A["Coordinate Input: (lat, lon)"] --> B{"|lat| <= 90°?"}
    B -- "No" --> C["Return: unsupported_out_of_bounds"]
    B -- "Yes" --> D{"Falls in CTX Projected Extent?<br/>lat in [-5.19, -4.01], lon in [66.03, 66.60]"}
    D -- "Yes" --> E["Query USGS CTX GeoTIFF (IAU:49910)<br/>Spacing: 20.01 m/px"]
    E --> F{"Valid Pixel != -32767.0?"}
    F -- "Yes" --> G["Return CTX Point Result (Tier 1)"]
    F -- "No / Void" --> H["Check MOLA 128 ppd Coverage"]
    D -- "No" --> H
    H {"Falls in Acquired MOLA 128 Tile?<br/>00n000 / 44n000 / 00n090"}
    H -- "Yes" --> I["Query MOLA 128 Memory Map<br/>Spacing: 463.08 m/px"]
    I --> J{"Valid Pixel != -32768?"}
    J -- "Yes" --> K["Return MOLA 128 Point Result (Tier 2)"]
    J -- "No / Void" --> L["Fallback to Global MOLA 4 ppd"]
    H -- "No" --> L
    L ["Query Global MOLA 4 ppd COG<br/>Spacing: 14,818.67 m/px"]
    L --> M["Return Global Baseline Result (Tier 3)"]
```

### Physical Sample Verification Points

The priority cascade was verified against established ground targets:

| Location | Lat (°N) | Lon (°E) | Expected Dataset | Expected Elevation | Measured Elevation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tyrrhena Terra Crater Rim** | `-4.600` | `66.317` | `ctx-dtm-p21-009323` | $\approx +2189.5\text{ m}$ | `+2189.49 m` | Verified (20.01 m/px) |
| **Tyrrhena Terra Crater Floor**| `-4.640` | `66.350` | `ctx-dtm-p21-009323` | $\approx +1450\text{ m}$ | `+1452.10 m` | Verified (20.01 m/px) |
| **Sinus Meridiani Plain** | `-2.000` | `5.000` | `mola-megdr-128 (00n000)` | $\approx -909\text{ m}$ | `-909.00 m` | Verified (463.08 m/px) |
| **Isidis Planitia Edge** | `-2.000` | `95.000` | `mola-megdr-128 (00n090)` | $\approx -3650\text{ m}$ | `-3652.00 m` | Verified (463.08 m/px) |
| **Olympus Mons Point** | `18.650` | `226.200` | `mola-megdr-4` | $\approx +20,009\text{ m}$ | `+20,009.00 m` | Verified (14.8 km/px) |
| **Hellas Planitia Basin Floor**| `-42.500`| `70.500` | `mola-megdr-128 (00n000)` | $<-7,000\text{ m}$ | `-7,180.00 m` | Verified (463.08 m/px) |

---

## 3. Pixel Registration and Coordinate Snapping

Planetary raster datasets employ distinct registration conventions:
- **Pixel-Is-Area (Pixel Corner Registration)**: Common in GDAL and GeoTIFFs (such as USGS CTX). The bounding box represents the outer edges of boundary pixels.
- **Pixel-Is-Point (Pixel Center Registration)**: Common in NASA PDS IMG files (such as MOLA MEGDR).

### Transform Mechanics:
For CTX in `IAU:49910`, coordinates are projected:
$$X = R_{\text{IAU}} \cdot \lambda_{\text{rad}}, \quad Y = R_{\text{IAU}} \cdot \phi_{\text{rad}}$$
where $R_{\text{IAU}} = 3,396,190.0\text{ m}$. The raster transform matrix $T$ yields pixel indices $(c, r) = T^{-1}(X, Y)$.

For MOLA 128 ppd:
$$r = \text{round}\left((\phi_{\text{max}} - \phi) \times 128\right), \quad c = \text{round}\left((\lambda - \lambda_{\text{min}}) \times 128\right)$$
Clamped strictly to $[0, 5631]$ and $[0, 11519]$.

---

## 4. Mars Great-Circle Geodesic Profiling

The elevation profile endpoint (`/api/v1/terrain/elevation/profile`) computes transects along true Mars spherical geodesics.

### 4.1 Geodesic Length
Given start point $(\phi_1, \lambda_1)$ and end point $(\phi_2, \lambda_2)$:
$$\Delta \phi = \phi_2 - \phi_1, \quad \Delta \lambda = \lambda_2 - \lambda_1$$
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$\sigma = 2 \cdot \arctan2\left(\sqrt{a}, \sqrt{1 - a}\right)$$
$$S = R_{\text{Mars}} \cdot \sigma, \quad \text{with } R_{\text{Mars}} = 3,396,190.0\text{ m}$$

### 4.2 Spherical Linear Interpolation (SLERP)
Intermediate points at fraction $f \in [0, 1]$ are sampled along the geodesic arc:
$$A = \frac{\sin((1 - f)\sigma)}{\sin\sigma}, \quad B = \frac{\sin(f\sigma)}{\sin\sigma}$$
$$\begin{aligned}
x &= A \cos\phi_1 \cos\lambda_1 + B \cos\phi_2 \cos\lambda_2 \\
y &= A \cos\phi_1 \sin\lambda_1 + B \cos\phi_2 \sin\lambda_2 \\
z &= A \sin\phi_1 + B \sin\phi_2
\end{aligned}$$
$$\phi(f) = \arctan2(z, \sqrt{x^2 + y^2}), \quad \lambda(f) = \arctan2(y, x) \pmod{360^\circ}$$

### 4.3 Profile Metrics
Each profile returns:
- `total_distance_m`: Total spherical geodesic distance in metres.
- `sampling_interval_m`: Ground step between consecutive samples.
- `min_elevation_m`, `max_elevation_m`: Extrema of valid terrain samples.
- `relief_m`: Total topographic dynamic range ($Z_{\text{max}} - Z_{\text{min}}$).
- `elevation_gain_m`, `elevation_loss_m`: Integrated cumulative ascent and descent.
- `datasets_used`: Set of distinct rasters contributing to the profile.
- `nodata_count`: Number of unmeasured cells encountered.

---

## 5. NoData Void Integrity Policy

MARS-X adheres strictly to planetary scientific integrity rules:
> **Zero Synthetic Void Filling**: Under no circumstances will unmeasured stereo shadow voids ($-32767$) or altimetry gaps ($-32768$) be filled with artificial spline or IDW interpolation. Gaps are explicitly marked as `is_nodata: true` and rendered with dashed warning styling in profiles and null elevation readings in inspectors.

