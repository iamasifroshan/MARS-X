# MARS-X — MOLA MEG128 Data Inventory & Coverage Report (Phase 5)

## 1. MOLA MEG128 Tile Specification
The MGS MOLA MEGDR 128 pixels/degree (MEG128) product partitions the Martian surface ($88^\circ\text{S}$ to $88^\circ\text{N}$) into 16 regional tiles across 4 latitude bands and 4 longitude quadrants:

- **Latitude Bands ($44^\circ$ span each):**
  - `88n`: $44.0^\circ\text{N}$ to $88.0^\circ\text{N}$
  - `44n`: $0.0^\circ\text{N}$ to $44.0^\circ\text{N}$
  - `00n`: $-44.0^\circ\text{S}$ to $0.0^\circ\text{N}$
  - `44s`: $-88.0^\circ\text{S}$ to $-44.0^\circ\text{S}$
- **Longitude Quadrants ($90^\circ$ span each):**
  - `000`: $0.0^\circ\text{E}$ to $90.0^\circ\text{E}$
  - `090`: $90.0^\circ\text{E}$ to $180.0^\circ\text{E}$
  - `180`: $180.0^\circ\text{E}$ to $270.0^\circ\text{E}$
  - `270`: $270.0^\circ\text{E}$ to $360.0^\circ\text{E}$

## 2. Spherical Coverage Calculation Methodology
The true fraction of Martian spherical surface area covered by a latitude-longitude bounding box is computed via spherical integration:

$$A = R^2 \int_{\lambda_{\min}}^{\lambda_{\max}} d\lambda \int_{\phi_{\min}}^{\phi_{\max}} \cos\phi\, d\phi = R^2 \cdot \Delta\lambda \cdot \left(\sin\phi_{\max} - \sin\phi_{\min}\right)$$

Relative to the full sphere area $4\pi R^2$, the fraction is:

$$\text{Fraction} = \frac{\Delta\lambda}{360^\circ} \cdot \frac{\sin\phi_{\max} - \sin\phi_{\min}}{2}$$

- For equatorial/mid-latitude tiles (e.g. `00n000`, $[-44^\circ, 0^\circ]$):
  $$\Delta\lambda / 360^\circ = 0.25$$
  $$(\sin(0^\circ) - \sin(-44^\circ))/2 = (0 - (-0.69466)) / 2 = 0.34733$$
  $$\text{Fraction} = 0.25 \times 0.34733 = 0.08683 \implies 8.68\% \text{ of Mars}$$
- The 16 tiles collectively cover $99.94\%$ of the Martian sphere ($\sin(88^\circ) \approx 0.99939$). Polar caps ($> 88^\circ\text{N/S}$) represent the remaining $0.06\%$.

## 3. Local Ingestion Status (1/16 Ingested)
- Ingested & Verified: `megt00n000hb` ($8.68\%$ surface area verified).
- Remote Catalog: 15 tiles catalogued with direct NASA PDS URLs and expected dimensions ($5,632 \times 11,520$).
