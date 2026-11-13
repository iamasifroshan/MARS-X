# MARS-X — Terrain Complexity Classification Decision Table (Phase 5.1)

## 1. Boolean Classification Rules & Priority Logic

The terrain complexity engine (`backend/app/terrain/hazard_engine.py`) classifies terrain by evaluating three primary geomorphic indicators:
- **Slope ($S$ in degrees):** Computed via Horn (1981) $3 \times 3$ gradient with latitude-scaled cell dimensions.
- **Local Relief ($\Delta z$ in metres):** Max $-$ min elevation within the local moving window.
- **Roughness ($\sigma_z$ in metres):** Unbiased sample standard deviation within the local moving window.
- **Confidence ($C \in [0.0, 1.0]$):** Derived from product validation state score $\times$ valid neighbor fraction.

### Priority Rules (Evaluated in Strict Order)
1. **Rule 1 (Data Deficiency):** If $C < 0.2$ OR any required indicator ($S, \Delta z, \sigma_z$) is `None` (due to center NoData or neighbor NoData propagation):
   $$\implies \mathbf{INSUFFICIENT\_DATA}$$
2. **Rule 2 (Polar Guard):** If $|\phi| > 85.0^\circ$:
   $$\implies \mathbf{INSUFFICIENT\_DATA}$$
3. **Rule 3 (Extreme Complexity):** If $S \ge 25.0^\circ$ OR $\Delta z \ge 75.0\text{ m}$ OR $\sigma_z \ge 20.0\text{ m}$:
   $$\implies \mathbf{EXTREME\_COMPLEXITY}$$
4. **Rule 4 (High Complexity):** If $S \ge 15.0^\circ$ OR $\Delta z \ge 30.0\text{ m}$ OR $\sigma_z \ge 8.0\text{ m}$:
   $$\implies \mathbf{HIGH\_COMPLEXITY}$$
5. **Rule 5 (Moderate Complexity):** If $S \ge 8.0^\circ$ OR $\Delta z \ge 10.0\text{ m}$ OR $\sigma_z \ge 2.5\text{ m}$:
   $$\implies \mathbf{MODERATE\_COMPLEXITY}$$
6. **Rule 6 (Low Complexity):** If all thresholds are below moderate limits ($S < 8.0^\circ \land \Delta z < 10.0\text{ m} \land \sigma_z < 2.5\text{ m}$):
   $$\implies \mathbf{LOW\_MEASURED\_COMPLEXITY}$$

---

## 2. Synthetic Test Case Decision Table

| Case # | Description | Slope ($S$) | Relief ($\Delta z$) | Roughness ($\sigma_z$) | Confidence ($C$) | Latitude ($\phi$) | Outcome | Scientific Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Low complexity | $3.2^\circ$ | $5.0\text{ m}$ | $1.1\text{ m}$ | $1.00$ | $0.0^\circ$ | `low_measured_complexity` | All values strictly below moderate complexity cutoffs. |
| **Case 2** | High slope alone | $\mathbf{16.5^\circ}$ | $6.0\text{ m}$ | $1.2\text{ m}$ | $1.00$ | $15.0^\circ$ | `high_complexity` | Slope exceeds $15.0^\circ$; triggers high threshold even with low relief. |
| **Case 3** | High relief alone | $4.0^\circ$ | $\mathbf{45.0\text{ m}}$ | $1.5\text{ m}$ | $1.00$ | $-20.0^\circ$ | `high_complexity` | Relief exceeds $30.0\text{ m}$ (regional step or terrace break). |
| **Case 4** | High roughness alone | $5.0^\circ$ | $8.0\text{ m}$ | $\mathbf{11.0\text{ m}}$ | $1.00$ | $45.0^\circ$ | `high_complexity` | Roughness exceeds $8.0\text{ m}$ (dissected surface). |
| **Case 5** | Multiple elevated indicators | $\mathbf{27.0^\circ}$ | $\mathbf{80.0\text{ m}}$ | $\mathbf{22.0\text{ m}}$ | $1.00$ | $-10.0^\circ$ | `extreme_complexity` | Meets multiple extreme triggers; scarp detection flagged. |
| **Case 6** | NoData propagation | `None` | $12.0\text{ m}$ | $2.0\text{ m}$ | $1.00$ | $0.0^\circ$ | `insufficient_data` | Any missing indicator propagates as insufficient data; never safe. |
| **Case 7** | Low confidence | $4.0^\circ$ | $6.0\text{ m}$ | $1.0\text{ m}$ | $\mathbf{0.15}$ | $30.0^\circ$ | `insufficient_data` | Confidence below $0.20$ threshold; data reliability inadequate. |
| **Case 8** | Polar singularity guard | $2.0^\circ$ | $4.0\text{ m}$ | $0.8\text{ m}$ | $1.00$ | $\mathbf{87.5^\circ}$ | `insufficient_data` | $|\phi| > 85.0^\circ$ rejected from equirectangular approximation. |
| **Case 9** | Moderate slope alone | $\mathbf{9.5^\circ}$ | $7.0\text{ m}$ | $1.8\text{ m}$ | $1.00$ | $-44.0^\circ$ | `moderate_complexity` | Slope $\ge 8.0^\circ$ triggers moderate classification. |
