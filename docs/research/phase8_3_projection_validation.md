# MARS-X — Research Report: Planetary Projections & Geodetic Coordinate Systems
**Document ID:** `MX-RR-8.3-03`  
**Phase:** 8.3 — Multi-Resolution Terrain Rendering & Interactive Elevation Inspection  
**Authors:** Senior Planetary Geodesist, Cartographic Systems Specialist  
**Classification:** Geodetic & Coordinate Reference System Specification  

---

## 1. Scope & Purpose

Web mapping engines (including MapLibre GL JS and OpenLayers) are built on the terrestrial Web Mercator projection (EPSG:3857) with an assumed Earth radius of $R_{\text{Earth}} = 6,378,137\text{ m}$. Planetary data from NASA PDS, USGS Astrogeology, and ESA PSA use non-terrestrial ellipsoids and spheres.

This document formalizes the mathematical transformations, geodetic radius differences, and projection relationships used in MARS-X.

---

## 2. Coordinate Reference System Inventory

MARS-X manages four distinct coordinate reference systems:

| System / Code | Name / Authority | Ellipsoid / Datum | Semi-Major Axis ($a$) | Inverse Flattening ($1/f$) | Primary Use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`IAU:49900`** | Mars 2000 Sphere | Spherical Mars | $3,396,000.0\text{ m}$ | $\infty$ (Sphere) | Global MOLA 4 ppd & MOLA 128 ppd |
| **`IAU:49910`** | Mars 2000 Sphere (USGS) | Spherical Mars (Revised) | $3,396,190.0\text{ m}$ | $\infty$ (Sphere) | USGS CTX DTM (`P21_009323_1754`) |
| **`EPSG:104905`**| Mars 2000 Equirectangular | Planetocentric Sphere | $3,396,190.0\text{ m}$ | $\infty$ (Sphere) | Vector graticule and footprint overlays |
| **`EPSG:3857`**  | Web Mercator | Pseudo-Mercator (Earth) | $6,378,137.0\text{ m}$ | $\infty$ (Sphere) | MapLibre GL JS browser rendering engine |

---

## 3. Mathematical Radius Discrepancy Analysis

The discrepancy between the standard MOLA spherical radius ($R_1 = 3,396,000\text{ m}$) and the IAU 2000 / USGS CTX spherical radius ($R_2 = 3,396,190\text{ m}$) is:
$$\Delta R = R_2 - R_1 = +190.0\text{ m}$$

### Relative Scale Factor
$$\frac{\Delta R}{R_1} = \frac{190}{3,396,000} \approx 5.5948 \times 10^{-5} \quad (55.95\text{ parts per million})$$

### Horizontal Shift Across Datasets
Across the entire North-South extent of the CTX DTM ($\Delta \phi = 1.17225^\circ \approx 0.02046\text{ radians}$):
$$\Delta s = \Delta R \cdot \Delta \phi = 190.0\text{ m} \cdot 0.02046 \approx 3.89\text{ m}$$

**Crucial Finding**: The $3.89\text{ m}$ maximum horizontal coordinate shift across the entire CTX dataset is **sub-pixel** relative to the $20.0128\text{ m/px}$ CTX ground resolution:
$$\frac{\Delta s}{\text{Resolution}_{\text{CTX}}} = \frac{3.89\text{ m}}{20.0128\text{ m/px}} \approx 0.194\text{ pixels} < 0.2\text{ pixels}$$
Therefore, direct co-registration between MOLA and CTX without non-linear warping introduces an error of less than $0.2$ pixels, which is well below the photogrammetric stereo matching uncertainty ($\pm 0.5$ to $1.0$ pixels).

---

## 4. MapLibre GL Web Mercator Projection Integration

To render planetary rasters on a Web Mercator canvas without geographic distortion:
1. **Latitude Mapping**: Planetocentric latitude $\phi \in [-85.0511^\circ, +85.0511^\circ]$ is passed directly to MapLibre.
2. **Longitude Normalization**: MapLibre spans longitude $\lambda_{\text{web}} \in [-180^\circ, +180^\circ]$. Planetary longitude is convention-defined as positive East $\lambda_{\text{Mars}} \in [0^\circ, 360^\circ]$.
   $$\lambda_{\text{web}} = \begin{cases}
   \lambda_{\text{Mars}} & \text{if } 0 \le \lambda_{\text{Mars}} \le 180^\circ \\
   \lambda_{\text{Mars}} - 360^\circ & \text{if } 180^\circ < \lambda_{\text{Mars}} < 360^\circ
   \end{cases}$$
   $$\lambda_{\text{Mars}} = \begin{cases}
   \lambda_{\text{web}} & \text{if } \lambda_{\text{web}} \ge 0 \\
   \lambda_{\text{web}} + 360^\circ & \text{if } \lambda_{\text{web}} < 0
   \end{cases}$$
3. **Hemispheric Raster Slicing**:
   - East Hemisphere Source: Bounded by $[0^\circ, -85.0511^\circ]$ to $[180^\circ, 85.0511^\circ]$.
   - West Hemisphere Source: Bounded by $[-180^\circ, -85.0511^\circ]$ to $[0^\circ, 85.0511^\circ]$.

---

## 5. Great-Circle Metric Calculations

All surface distance, speed, and slope calculations in MARS-X use the IAU 2000 Mars radius $R_{\text{Mars}} = 3,396,190.0\text{ m}$, never Earth $R_{\text{Earth}} = 6,378,137\text{ m}$.

The distance along the spherical surface between two points is:
$$D = R_{\text{Mars}} \cdot \arccos\left(\sin\phi_1\sin\phi_2 + \cos\phi_1\cos\phi_2\cos(\lambda_2 - \lambda_1)\right)$$
Implemented using the numerically stable Haversine formula for small angular separations.

