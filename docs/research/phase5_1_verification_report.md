# MARS-X — Scientific Verification & Hazard Engine Calibration Report (Phase 5.1)

## 1. Overview & Verification Scope
Phase 5.1 conducted a rigorous scientific audit of the Phase 5 implementation, addressing:
1. **MOLA Coverage Semantics:** Disentangling theoretical global coverage from locally downloaded, integrity-verified, and scientifically validated tile coverage.
2. **Hazard Classification Logic & Calibration:** Formalizing a Boolean decision table with synthetic edge cases, ensuring that missing/NoData values never default to low risk.
3. **Spatial-Scale Limitations:** Quantifying native pixel spacing, window geometries, and minimum detectable feature scales (Nyquist $\sim 2.5\times$).
4. **Vertical Reference Evidence:** Removing universal $\pm 1\text{--}5\text{ m}$ offset assumptions and cataloguing documented adjustment procedures.
5. **Polar Geodesy Safeguard:** Enforcing a validated latitude envelope ($|\phi| \le 85^\circ$) for equirectangular approximations.
6. **Interface Calibration:** Standardizing the user interface on "terrain complexity" rather than implying astronaut safety.

---

## 2. Issues Found & Corrective Actions

| # | Subsystem | Issue Identified | Correction Implemented |
| :--- | :--- | :--- | :--- |
| **1** | MOLA Inventory | `total_surface_coverage_pct` conflated theoretical archive coverage ($99.94\%$) with on-disk coverage. | Separated into distinct metrics: `theoretical_archive_coverage_pct` ($99.94\%$), `downloaded_tile_coverage_pct` ($8.68\%$), `integrity_verified_coverage_pct` ($8.68\%$), and `scientifically_validated_coverage_pct` ($8.68\%$). |
| **2** | Hazard Engine | Classification lacked explicit spatial scale limits, risking false assumptions that MOLA ($14.8\text{ km/px}$) can resolve rover obstacles. | Added `SpatialScaleMetadata` to all hazard responses exposing pixel spacing ($14.8\text{ km}$), window size ($44.5\text{ km}$), min detectable scale ($\sim 37\text{ km}$), and operational scale tier (`regional_reconnaissance`). |
| **3** | Geodesy | Clamping $\cos\phi$ at high latitudes allowed unrealistic cylindrical metric calculations near poles ($|\phi| > 85^\circ$). | Enforced `MAX_VALID_CYLINDRICAL_LAT_DEG = 85.0^\circ`. Coordinates $|\phi| > 85^\circ$ are rejected from equirectangular approximations and flagged `insufficient_data`. |
| **4** | Harmonization | Stereogrammetric DTMs had hardcoded $\pm 1\text{--}5\text{ m}$ offset notes not derived from individual product headers. | Replaced arbitrary offset text with `VerticalEvidenceRecord` cataloging documented adjustment procedures (bundle-adjustment, ICP `pc_align`, or PEDR tie). Set measured offsets to `None` pending local header parsing. |
| **5** | Frontend | Hazard panel displayed "Terrain Hazard Indicators" which could be misinterpreted as astronaut clearance. | Renamed tab and cards to **Terrain Complexity Indicators** and added a spatial scale transparency card displaying native resolution and undetectable microtopography warnings. |

---

## 3. Evidence Supporting Scientific Assumptions
1. **MOLA 128 ppd Spherical Integration:**
   $$A = R^2 \cdot \Delta\lambda \cdot (\sin\phi_2 - \sin\phi_1)$$
   For tile `megt00n000hb` ($[-44^\circ, 0^\circ]$ latitude, $[0^\circ, 90^\circ]$ longitude), the fraction is exactly $8.6832\%$ of the Martian sphere.
2. **Polar Meridian Convergence:**
   At $85^\circ\text{N}$, $dx = R \cos(85^\circ) \Delta\lambda \approx 14.8\text{ km} \times 0.0872 = 1.29\text{ km/deg}$, creating a $>11\times$ longitudinal compression relative to the equator. Cylindrical projections are mathematically invalid beyond this threshold without conformal/polar stereographic projection.
3. **Nyquist Detectability Limit:**
   In raster altimetry, discrete features must span at least 2 to 3 pixels to avoid aliasing and false morphological interpretation. For MOLA 4 ppd, minimum detectable feature size is $14.818\text{ km} \times 2.5 \approx 37.0\text{ km}$.

---

## 4. Verification Test Results
- **Pytest Suite:** **82 passed, 0 failed** across all test suites in 0.98 seconds:
  - 11 new tests in `backend/tests/test_phase5_1_calibration.py` (decision table cases 1–8, coverage tier separation, spatial scale metadata, vertical evidence auditing).
  - 14 tests in `test_phase5_validation.py`.
  - 12 tests in `test_multi_resolution.py`.
  - 6 tests in `test_mola_ingestion.py`.
  - 39 tests in core geometry, CRS, and datasets.
- **Frontend Production Build:** `npm run build` compiled with Turbopack and strict TypeScript in 1356ms with 0 errors.
