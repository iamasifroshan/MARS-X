# MARS-X — Phase 7 Research: Coverage Report & Spherical Metrics

## 1. Spherical Coverage Methodology

On a spherical planetary body, geographic bounding boxes cannot be measured by simple rectangular degree multiplication ($\Delta \text{lat} \times \Delta \text{lon}$). Because lines of longitude converge toward the poles, the true surface area fraction $f$ of any bounding box $[\phi_{\min}, \phi_{\max}] \times [\lambda_{\min}, \lambda_{\max}]$ is calculated using spherical trigonometry:

$$f = \frac{\sin(\phi_{\max}) - \sin(\phi_{\min})}{2} \times \frac{\lambda_{\max} - \lambda_{\min}}{360^\circ}$$

---

## 2. Spherical Area Breakdown of the 16 MOLA 128 Tiles

The NASA PDS MOLA MEG128 archive is partitioned into 16 tiles across 4 latitude bands and 4 longitude quadrants ($90^\circ$ span each):

| Latitude Band | Latitude Limits | Spherical Fraction per $90^\circ$ Quadrant | Total Band Fraction (4 Quads) |
| :--- | :--- | :--- | :--- |
| **88n** (North Polar) | $+44.0^\circ \text{ to } +88.0^\circ\text{N}$ | **3.8092%** | 15.2368% |
| **44n** (North Equatorial) | $0.0^\circ \text{ to } +44.0^\circ\text{N}$ | **8.6832%** | 34.7328% |
| **00n** (South Equatorial) | $-44.0^\circ \text{ to } 0.0^\circ\text{S}$ | **8.6832%** | 34.7328% |
| **44s** (South Polar) | $-88.0^\circ \text{ to } -44.0^\circ\text{S}$ | **3.8092%** | 15.2368% |
| **Polar Caps** (Excluded from MEGDR) | $|\phi| > 88^\circ$ | **0.0152% per pole** | **0.0609%** |
| **Global Archive Potential** | $|\phi| \le 88^\circ$ | — | **99.9391% (~99.94%)** |

---

## 3. Current Phase 7 Ingestion Status

- **Theoretical Archive Coverage:** **99.94%** of Mars' spherical surface.
- **Acquired & Validated Tiles (3 tiles):**
  - `megt00n000hb`: $8.6832\%$
  - `megt44n000hb`: $8.6832\%$
  - `megt00n090hb`: $8.6832\%$
  - **Sum of Downloaded & Verified Surface:** **26.0496% (~26.05%)**
- **Pending Remote Retrieval (13 tiles):** $73.8895\%$

MARS-X dashboards report both metrics side-by-side with distinct color-coded indicators to guarantee transparent geospatial accounting.

