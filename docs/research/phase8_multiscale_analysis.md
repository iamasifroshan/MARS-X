# Phase 8: Multi-Scale Topographic Analysis Engine

**Author:** Planetary Geomorphologist & Computational Terrain Scientist  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8 — Resolution-Aware Terrain Intelligence  

---

## 1. Principles of Planetary Multi-Scale Geomorphology

Topographic slope, local relief, and roughness are not scale-invariant properties. A single pixel on Mars can appear smooth across a $14.8\text{ km}$ MOLA 4 ppd footprint, moderately rolling across a $463\text{ m}$ MOLA 128 ppd cell, yet rugged and un-traversable with $20\text{ m}$ CTX scarps or $1\text{ m}$ HiRISE boulder fields.

The Multi-Scale Terrain Analysis Engine (`backend/app/terrain/multiscale_analysis.py`) guarantees that every indicator is coupled to an explicit physical metric window diameter ($W\text{ in metres}$), rather than an arbitrary pixel count.

---

## 2. Dynamic Metric-to-Pixel Kernel Translation

For any requested physical window $W_{\text{target}}$ and native raster spacing $r_{\text{native}}$:
$$k_{\text{raw}} = \text{round}\left(\frac{W_{\text{target}}}{r_{\text{native}}}\right)$$
$$k = \max\left(3, k_{\text{raw}} + (1 - k_{\text{raw}} \pmod 2)\right)$$
This guarantees an odd, symmetric kernel size ($k \times k$) with $k \ge 3$, centered precisely on the evaluated cell.

### Actual Window Sizes Evaluated:
| Target Scale ($W$) | CTX DTM ($20.01\text{ m/px}$) | MOLA 128 ppd ($463.08\text{ m/px}$) | MOLA 4 ppd ($14.8\text{ km/px}$) |
| :--- | :--- | :--- | :--- |
| **$100\text{ m}$** | $5 \times 5\text{ pixels}$ ($100.1\text{ m}$) | Sub-pixel (clamps to $3 \times 3$, $1389\text{ m}$) | Sub-pixel |
| **$500\text{ m}$** | $25 \times 25\text{ pixels}$ ($500.3\text{ m}$) | $3 \times 3\text{ pixels}$ ($1389.2\text{ m}$) | Sub-pixel |
| **$1000\text{ m}$** | $51 \times 51\text{ pixels}$ ($1020.6\text{ m}$) | $3 \times 3\text{ pixels}$ ($1389.2\text{ m}$) | Sub-pixel |
| **$2000\text{ m}$** | $101 \times 101\text{ pixels}$ ($2021.3\text{ m}$) | $5 \times 5\text{ pixels}$ ($2315.4\text{ m}$) | Sub-pixel |

---

## 3. Topographic Indicator Formulations

### A. Horn 3x3 Topographic Slope with Latitudinal Spacing
Metric cell dimensions scale with planetary latitude due to meridian convergence:
$$\Delta x = \frac{\pi R_{\text{eq}}}{180} \cos(\phi) \Delta\lambda, \quad \Delta y = \frac{\pi R_{\text{pol}}}{180} \Delta\phi$$
Slope is computed via the Horn 8-neighbor weighted finite-difference gradient:
$$p = \frac{\partial z}{\partial x} = \frac{(z_3 + 2z_6 + z_9) - (z_1 + 2z_4 + z_7)}{8 \Delta x}$$
$$q = \frac{\partial z}{\partial y} = \frac{(z_1 + 2z_2 + z_3) - (z_7 + 2z_8 + z_9)}{8 \Delta y}$$
$$\text{Slope}^\circ = \arctan\left(\sqrt{p^2 + q^2}\right) \times \frac{180}{\pi}$$
Any window containing a NoData dropout is excluded from statistics.

### B. O(1) Integral-Image Uniform Box Filtering for Roughness
To achieve real-time, deterministic moving standard deviation without external scientific packages, a 2D Summed-Area Table (integral image) is constructed:
$$\text{SAT}(r, c) = \sum_{i=1}^r \sum_{j=1}^c z(i, j)$$
Local mean $\mu$ and local squared mean $\mu_2$ across the $k \times k$ neighborhood are computed in $O(1)$ operations per cell:
$$\sigma_{\text{local}} = \sqrt{\max\left(0, \mu_2 - \mu^2\right)}$$
Roughness is quantified as the root-mean-square elevation variability:
$$\text{Roughness} = \sigma_{\text{local}}$$
Local relief is derived as $2\sqrt{2} \times \sigma_{\text{local}}$ for Gaussian surfaces.

### C. Deterministic Complexity Classification
Thresholds are grounded in Martian geomorphological observations:
- **Low Complexity:** $\bar{S} < 5.0^\circ$ and $\text{Roughness} < 15.0\text{ m}$, valid data $\ge 60\%$.
- **Moderate Complexity:** $\bar{S} \in [5.0^\circ, 15.0^\circ]$ or $\text{Roughness} \in [15.0\text{ m}, 40.0\text{ m}]$, valid data $\ge 60\%$.
- **High Complexity:** $\bar{S} > 15.0^\circ$ or $S_{\max} > 25.0^\circ$ or $\text{Roughness} > 40.0\text{ m}$, valid data $\ge 60\%$.
- **Insufficient Data:** Valid data coverage $< 60\%$.
