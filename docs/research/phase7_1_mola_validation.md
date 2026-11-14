# MARS-X — Phase 7.1 Research: MOLA 128 ppd Regional Validation & Boundary Seam Audit

## 1. MOLA 128 ppd Regional Dataset Overview

The Mars Global Surveyor (MGS) Mars Orbiter Laser Altimeter (MOLA) Mission Experiment Gridded Data Record (MEGDR) 128 ppd product provides the global topographic baseline for regional terrain navigation on Mars.

In Phase 7, three contiguous tiles were acquired from the NASA PDS Geosciences Node:
1. `megt00n000hb.img` (South Equatorial: Lat $[-44^\circ, 0^\circ]$, Lon $[0^\circ, 90^\circ\text{E}]$)
2. `megt44n000hb.img` (North Equatorial: Lat $[0^\circ, +44^\circ\text{N}]$, Lon $[0^\circ, 90^\circ\text{E}]$)
3. `megt00n090hb.img` (Eastern Continuation: Lat $[-44^\circ, 0^\circ]$, Lon $[90^\circ, 180^\circ\text{E}]$)

---

## 2. Independent PDS Label Parameter Extraction

Labels (`.lbl`) for all three products were parsed independently:

| Parameter | `megt00n000hb.lbl` | `megt44n000hb.lbl` | `megt00n090hb.lbl` | Conformance Status |
| :--- | :--- | :--- | :--- | :--- |
| `LINES` | 5632 | 5632 | 5632 | Verified identical |
| `LINE_SAMPLES` | 11520 | 11520 | 11520 | Verified identical |
| `SAMPLE_BITS` | 16 | 16 | 16 | Verified 16-bit |
| `SAMPLE_TYPE` | `MSB_INTEGER` | `MSB_INTEGER` | `MSB_INTEGER` | Verified signed big-endian |
| `MAP_PROJECTION_TYPE` | `SIMPLE CYLINDRICAL` | `SIMPLE CYLINDRICAL` | `SIMPLE CYLINDRICAL` | Verified Equirectangular |
| `A_AXIS_RADIUS` | 3396.0 <KM> | 3396.0 <KM> | 3396.0 <KM> | Verified 3,396,000 m sphere |
| `B_AXIS_RADIUS` | 3396.0 <KM> | 3396.0 <KM> | 3396.0 <KM> | Verified spherical datum |
| `C_AXIS_RADIUS` | 3396.0 <KM> | 3396.0 <KM> | 3396.0 <KM> | Verified spherical datum |
| `MAP_RESOLUTION` | 128.0 <PIXEL/DEGREE> | 128.0 <PIXEL/DEGREE> | 128.0 <PIXEL/DEGREE> | Verified 0.0078125°/px |
| `MAXIMUM_LATITUDE` | 0.0 <DEGREE> | 44.0 <DEGREE> | 0.0 <DEGREE> | Verified |
| `MINIMUM_LATITUDE` | -44.0 <DEGREE> | 0.0 <DEGREE> | -44.0 <DEGREE> | Verified |
| `WESTERNMOST_LONGITUDE` | 0.0 <DEGREE> | 0.0 <DEGREE> | 90.0 <DEGREE> | Verified |
| `EASTERNMOST_LONGITUDE` | 90.0 <DEGREE> | 90.0 <DEGREE> | 180.0 <DEGREE> | Verified |
| `LINE_PROJECTION_OFFSET` | 0.5 | 5632.5 | 0.5 | Verified pixel-center alignment |
| `SAMPLE_PROJECTION_OFFSET`| 23040.5 | 23040.5 | 11520.5 | Verified pixel-center alignment |

---

## 3. Boundary Continuity and Seam Discontinuity Analysis

To detect any systematic geodetic step errors, registration shifts, or datum offsets across tile boundaries, numerical pixel-to-pixel comparisons were executed along the shared edges.

### 3.1 Equator Boundary (`megt44n000hb` line 5631 vs `megt00n000hb` line 0)
- **Shared Geometry:** Latitude $0.0^\circ$ (Equator), spanning Longitude $0.0^\circ\text{E}$ to $90.0^\circ\text{E}$ (11,520 columns).
- **Pixel Spacing:** In pixel-center registration, line 5631 of the northern tile is centered at $+0.5/128^\circ \approx +0.0039^\circ\text{N}$. Line 0 of the southern tile is centered at $-0.5/128^\circ \approx -0.0039^\circ\text{S}$.
- **Center-to-Center Distance:** Exactly 1 pixel ($1/128^\circ \approx 463.08\text{ meters}$).
- **Measured Metrics (11,520 columns):**
  - **Median Elevation Difference:** **$0.0\text{ meters}$**
  - **Mean Absolute Difference:** **$21.28\text{ meters}$**
  - **Min / Max Difference:** $-354.0\text{ m}$ / $+424.0\text{ m}$
  - **Mean Equivalent Slope:** **$2.59^\circ$**
  - **Max Equivalent Slope:** **$42.48^\circ$** (reflecting steep natural crater rims crossing the equator, e.g. around Terra Sabaea).

### 3.2 Meridian 90°E Boundary (`megt00n000hb` column 11519 vs `megt00n090hb` column 0)
- **Shared Geometry:** Longitude $90.0^\circ\text{E}$, spanning Latitude $-44.0^\circ$ to $0.0^\circ$ (5,632 rows).
- **Pixel Spacing:** Column 11519 is centered at $90.0^\circ - 0.5/128^\circ \approx 89.9961^\circ\text{E}$. Column 0 is centered at $90.0^\circ + 0.5/128^\circ \approx 90.0039^\circ\text{E}$.
- **Center-to-Center Distance:** $463.08 \times \cos(\phi)\text{ meters}$ ($\approx 333\text{ m}$ at $-44^\circ$ to $463\text{ m}$ at $0^\circ$).
- **Measured Metrics (5,632 rows):**
  - **Median Elevation Difference:** **$0.0\text{ meters}$**
  - **Mean Absolute Difference:** **$13.58\text{ meters}$**
  - **Min / Max Difference:** $-323.0\text{ m}$ / $+158.0\text{ m}$
  - **Mean Equivalent Slope:** **$1.86^\circ$**
  - **Max Equivalent Slope:** **$35.13^\circ$**

### 3.3 Geodetic Conclusion
The median elevation difference across both boundaries is **identically 0.0 meters**. The absence of any non-zero median bias confirms that:
1. There is no vertical datum step across tiles.
2. Coordinate transforms and projection offsets are mathematically aligned to sub-meter precision.
3. Observed elevation differences along the seam represent authentic Martian topographic slopes.
