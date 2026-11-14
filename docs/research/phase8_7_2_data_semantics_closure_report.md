# MARS-X — PHASE 8.7.2: DISCOVERY DATA SEMANTICS & METADATA CLOSURE REPORT

**Workspace:** `E:\MARS-X`  
**Starting Baseline:** Commit `b014465` (`phase8.7.1: audit scientific discovery evidence and provenance`)  
**Branch:** `master`  
**Project:** MARS-X — Interplanetary Survival Guide: Martian Map (NASA Space Apps Challenge 2026)  
**Status:** Complete & Verified  

---

## 1. Executive Summary

Phase 8.7.2 resolves the scientific classification, source-resolution, and vertical-reference ambiguities identified during the Phase 8.7.1 audit of the Science Discovery System. Prior to this phase, cartographic interpretations (such as USGS SIM 3292 geological unit boundaries and landing-site catalog entries) risked being conflated with direct physical sensor observations, and global MOLA raster pixel spacing (128 ppd / 463.08 m/px) was inadvertently quoted as the native resolution of non-raster geological polygons. Furthermore, vertical datums across CTX, HiRISE, and MOLA required rigorous formal verification to confirm that all numerical elevation queries return areoid heights without conflation with planetary reference-sphere radii.

Through targeted schema refinement, backend service updates, frontend UI modernization, and automated test suite expansion, Phase 8.7.2 delivers:
1. **Strict 5-Class Epistemological Separation**: Discovery evidence across all 18 candidates is partitioned into *Direct sensor observations*, *Derived measurements*, *Mapped geological interpretations*, *Indicative proxies*, and *Potential investigations*.
2. **Accurate Cartographic Scale vs. Raster Resolution**: USGS SIM 3292 features strictly report their published `1:20,000,000` cartographic scale and boundary compilation uncertainty (~5–25 km), completely disentangled from raster grid spacings (CTX 20.0 m/px, HiRISE 1.01 m/px, MOLA 463.08 m/px, TES ~3 km/px, THEMIS ~231.5 m/px).
3. **Rigorous Vertical Reference Audit**: Confirmed that 100% of numerical elevations in MARS-X represent **areoid heights** referenced to the MOLA Areoid (gravitational equipotential surface, Goddard Mars potential model GMM-3 mgm1025 degree 50), with zero mixing of planetary reference-sphere radii ($R = 3,396,190\text{ m}$).
4. **Preserved Numerical Benchmarks**: All three validated Mars elevation benchmarks remain 100% bitwise preserved:
   - Tyrrhena Terra CTX DTM: `+2189.49 m` at `(-4.600°, 66.317°E)`
   - Apollinaris Sulci Controlled CTX DTM: `-2930.77 m` at `(4.700°, 168.250°E)`
   - Holden Crater Controlled HiRISE DTM: `-1132.14 m` at `(-28.500°, 309.020°E)`
5. **Full Regression Verification**: All 266 backend pytest tests passed; Next.js 16 frontend build succeeded with 0 errors; live browser screenshots re-captured and verified.

---

## 2. Evidence Classification Audit & Epistemological Separation

Prior iterations presented evidence under a simplified 4-class structure where historical landing site coordinates or broad geological polygon queries were occasionally grouped with measured physical observations. Phase 8.7.2 establishes a strict 5-class epistemological framework:

| Epistemological Evidence Class | Definition in MARS-X | Permitted Data Sources in MARS-X | Prohibited Conflations |
|---|---|---|---|
| **Direct Sensor Observations** | Uncalibrated or calibrated physical measurements made directly by spacecraft instruments, hosted locally in MARS-X. | MOLA MEGDR gridded radiances/altimeter return counts; locally hosted calibrated frames. | **Never** claim raw pushbroom CCD arrays (CTX EDR or HiRISE EDR/RDR) are hosted locally when only photogrammetric derived DTM GeoTIFFs are present. Point explorer to NASA PDS archive for raw sensor telemetry. |
| **Derived Measurements** | Quantitative parameters calculated from sensor data via validated physical/photogrammetric reduction pipelines. | High-resolution DTM elevation rasters (CTX ASP stereo DTM, HiRISE SOCET SET DTM), MOLA areoid height, calculated terrain slope ($^\circ$), roughness index, geodesic haversine distance. | Do not present cartographic polygons or catalog points as derived measurements. |
| **Mapped Geological Interpretations** | Expert cartographic mappings and stratigraphic interpretations compiled by planetary geologists. | USGS Scientific Investigations Map 3292 (Tanaka et al. 2014): 1,311 geological unit polygons, 3,800 contacts, 3,593 structures, and 9 landing site records. | Do not treat mapped contact lines as mathematical physical boundaries; do not treat landing site point markers as sensor footprints. |
| **Indicative Proxies** | Low-resolution, unvalidated, or qualitative physical proxies representing relative spatial trends. | TES apparent thermal-inertia reconstruction (~0.50% LUT step nominal proxy); THEMIS daytime infrared visual mosaic (8-bit brightness values, 0–255 DN). | **Never** represent TES thermal inertia as kinetic surface temperature; **never** represent THEMIS 8-bit DN as calibrated spectral radiance. |
| **Potential Investigations** | Scientific hypotheses and recommended follow-up observations suggested by multi-dataset context. | Proposed in-situ rover traverse routes, stratigraphic sampling targets, trench excavations, or orbital re-observations. | Must be explicitly flagged as unverified candidate hypotheses. |

### Complete Audit of All 18 Discovery Candidates

| ID | Title | Primary Evidence Class | Primary Source Feature / Product | Native Scale or Spacing | Vertical Reference |
|---|---|---|---|---|---|
| `disc-terr-tyrrhena-ctx` | Tyrrhena Terra Valley Network & Ancient Cratered Uplands | `derived_measurement` | `P21_009323_..._dtm.tif` | 20.0128 m/px raster spacing | MOLA Areoid (`areoid_height`) |
| `disc-terr-apollinaris-ctx` | Apollinaris Sulci Yardang Corridors & Medusae Contact | `derived_measurement` | `T01_000893_...-DEM-geoid-adj.tif` | 20.00 m/px raster spacing | MOLA Areoid (`areoid_height`) |
| `disc-terr-holden-hirise` | Holden Crater Ejecta Megabreccia & Stratified Seds | `derived_measurement` | `DTEEC_011635_1510_029542_1510_A01.tif` | 1.01 m/px raster spacing | MOLA Areoid (`areoid_height`) |
| `disc-land-curiosity` | Bradbury Landing — MSL Curiosity (Aeolis Palus) | `mapped_geological_interpretation` | USGS SIM 3292 Landing Sites (OBJECTID 9) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-land-opportunity` | Meridiani Planum — MER-B Opportunity (Eagle Crater) | `mapped_geological_interpretation` | USGS SIM 3292 Landing Sites (OBJECTID 6) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-land-spirit` | Gusev Crater Floor — MER-A Spirit | `mapped_geological_interpretation` | USGS SIM 3292 Landing Sites (OBJECTID 5) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-land-pathfinder` | Ares Vallis Outflow Plain — Mars Pathfinder | `mapped_geological_interpretation` | USGS SIM 3292 Landing Sites (OBJECTID 4) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-land-viking1` | Chryse Planitia Volcanic Plains — Viking 1 Lander | `mapped_geological_interpretation` | USGS SIM 3292 Landing Sites (OBJECTID 1) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-geol-olympus-mons` | Olympus Mons Volcanic Caldera & Flank Scarp Complex | `mapped_geological_interpretation` | USGS SIM 3292 Global Geology (Unit Ave, ID 1046) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-geol-valles-marineris` | Melas Chasma Interior Floor & Wall Rock Layering | `mapped_geological_interpretation` | USGS SIM 3292 Global Geology (Unit Hpe, ID 922) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-geol-noachis-massifs` | Ancient Noachian Highlands Impact Massifs | `mapped_geological_interpretation` | USGS SIM 3292 Global Geology (Unit mNh, ID 583) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-struct-syrtis-ridges` | Syrtis Major Volcanic Wrinkle Ridge Network | `mapped_geological_interpretation` | USGS SIM 3292 Structural Features (Wrinkle Ridge, ID 1842) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-struct-cerberus-graben` | Cerberus Fossae Extensional Fault Graben System | `mapped_geological_interpretation` | USGS SIM 3292 Structural Features (Fault Graben, ID 3105) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-struct-shalbatana-channel` | Shalbatana Vallis Outflow Channel Scour Margin | `mapped_geological_interpretation` | USGS SIM 3292 Structural Features (Channel Margin, ID 1120) | 1:20,000,000 cartographic scale | MOLA Areoid (`areoid_height`) |
| `disc-therm-sinus-meridiani` | High Thermal Inertia Basaltic Sand Bedforms | `indicative_proxy` | TES Bolometer Thermal Inertia Derivation (Band 10) | ~3,000 m/px nominal grid | MOLA Areoid (`areoid_height`) |
| `disc-therm-tharsis-dust` | Low Thermal Inertia Atmospheric Dust Mantle | `indicative_proxy` | TES Bolometer Thermal Inertia Derivation (Band 10) | ~3,000 m/px nominal grid | MOLA Areoid (`areoid_height`) |
| `disc-multi-tyrrhena-corridor` | Tyrrhena Exploration Corridor: Noachian to Hesperian Transition | `composite_interpretation` | Multi-dataset synthesis (SIM 3292 + CTX DTM + TES + THEMIS) | Multi-scale synthesis | MOLA Areoid (`areoid_height`) |
| `disc-multi-meridiani-gateway` | Meridiani Gateway: Stratigraphic Outcrop to Basalt Sheet Corridor | `composite_interpretation` | Multi-dataset synthesis (SIM 3292 + THEMIS IR + TES TI) | Multi-scale synthesis | MOLA Areoid (`areoid_height`) |

---

## 3. Disentangling Cartographic Scale, Raster Resolution, and Precision

### The Category Error Identified in Previous Milestones
In earlier audit reports, a category error occurred wherein the spatial resolution of a geological unit (such as Noachian Highland unit `mNh` or Olympus Mons unit `Ave`) was reported as `463.08 m/px` or `14,818.67 m/px`. This arose because the point inspection engine queried MOLA elevation grids (128 ppd or 4 ppd) to retrieve topographic context for the geological vector feature, and the user interface naively surfaced the underlying raster's pixel spacing under the label "Native Resolution".

### Resolution and Precision Formal Separation
Phase 8.7.2 formally segregates three distinct spatial attributes across all discovery candidates and API endpoints:
1. **Source Type and Published Scale**:
   - For USGS SIM 3292 vector features (geology, contacts, structures, landing sites), the primary source is documented as `source_type: "cartographic_map"` or `"catalog_record"` with `native_scale_or_spacing: "1:20,000,000 published cartographic map scale"`.
   - Cartographic compilation precision is documented as: *"Boundary line placement uncertainty ~5–25 km depending on Viking/THEMIS base map quality"*.
2. **Raster Pixel Spacing**:
   - Raster products have strictly assigned physical grid spacings:
     - HiRISE Controlled DTM: `1.01 m/px`
     - CTX Ames Stereo Pipeline DTMs: `20.0 m/px` – `20.0128 m/px`
     - MOLA MEGDR 128 ppd: `463.08 m/px` (equatorial)
     - MOLA MEGDR 4 ppd: `14,818.67 m/px` (equatorial)
     - TES Thermal Inertia Grid: `~3,000 m/px` (30 ppd)
     - THEMIS Daytime IR Mosaic: `~231.5 m/px` (approx 8-bit visual preview)
3. **Positional Precision**:
   - Every candidate now provides a `positional_precision` statement in its `primary_source` metadata object. For example, in-situ rover coordinates (e.g. MSL Curiosity) are noted as known to decimeter precision relative to surface features, while orbital base map tie uncertainty is ~50–100 m.

---

## 4. Vertical Reference Audit & Datum Harmonization

### Areoid vs. Geoid vs. Reference-Sphere Radii
Mars geodesy requires precise distinction between three surfaces:
1. **Areoid (Mars Reference Geoid)**: An equipotential gravitational surface of Mars. For MOLA, the areoid is defined by the Goddard Mars potential model GMM-3 (evaluated to spherical harmonic degree and order 50), with a mean equatorial radius of $3,396,000\text{ m}$. Elevation $h$ is defined as the vertical distance of a point above this gravitational equipotential surface:
   $$h = r(\phi, \lambda) - r_{\text{areoid}}(\phi, \lambda)$$
2. **Reference Sphere**: A geometric sphere of fixed radius (typically $R_{\text{IAU}} = 3,396,190\text{ m}$ or $R_0 = 3,396,000\text{ m}$). Radii measured from the planetary center of mass to the surface ($r \approx 3,380,000\text{ to }3,420,000\text{ m}$) are planetary radii, NOT elevations.
3. **Geoid-Adjusted Stereo DTMs**: Stereo photogrammetry software (e.g. USGS ISIS `cam2map`, NASA Ames Stereo Pipeline `pc_align`) initially computes heights above a reference ellipsoid or sphere, then applies a geoid adjustment grid (`dem_geoid --geoid MOLA`) to convert heights into orthometric heights above the MOLA Areoid.

### Formal Datum Audit of Integrated MARS-X Products

| Product Path | Native Header Vertical Tag | Reduction / Alignment Method | Harmonized MARS-X Vertical Datum | Vertical Datum Type |
|---|---|---|---|---|
| `data/raw/ctx/P21_009323_..._dtm.tif` | `GEOID: mola` | Ames Stereo Pipeline `pc_align` tied to MOLA PEDR tracks | MOLA Areoid (ASP pc_align tied) | `areoid_height` |
| `data/originals/ctx/T01_000893_...-DEM-geoid-adj.tif` | `GEOID: mola` | Ames Stereo Pipeline `dem_geoid -DEM.tif -o -DEM-geoid --geoid MOLA` | MOLA Areoid (MOLA Geoid-Adjusted) | `areoid_height` |
| `data/originals/hirise/DTEEC_011635_1510_029542_1510_A01.tif` | `DATA_SET_ID: MRO-M-HIRISE-5-DTM-V1.0` | USGS ISIS SOCET SET bundle adjustment tied to MOLA altimetry | MOLA Areoid (MOLA Geoid-Adjusted) | `areoid_height` |
| `data/derived/mola/mola_megr128_global.tif` | `IAU2000` / GMM-3 degree 50 | PDS MEGDR elevation product (mgm1025) | MOLA Areoid (GMM-3 degree 50) | `areoid_height` |
| `data/derived/mola/mola_megr04_global_cog.tif` | `IAU2000` / GMM-3 degree 50 | PDS MEGDR elevation product (mgm1025) | MOLA Areoid (GMM-3 degree 50) | `areoid_height` |

### Audit Finding
**100% of numerical elevation values returned by MARS-X backend APIs and displayed on frontend panels are areoid heights.** No planetary center radii or uncorrected reference-sphere heights are returned or mixed. The `vertical_reference_audit` block in `/api/v1/discovery/profile` explicitly reports:
```json
{
  "elevation_product": "ctx-dtm-tyrrhena",
  "vertical_datum": "MOLA Areoid (tied via Ames Stereo Pipeline pc_align)",
  "vertical_datum_type": "areoid_height",
  "reference_surface": "MOLA Areoid (Gravitational equipotential surface, GMM-3 degree-50)",
  "datum_harmonization_status": "harmonized_areoid",
  "verification_status": "verified",
  "sphere_mixing_warning": "Elevations are areoid heights, NOT distances from planetary center or reference sphere."
}
```

---

## 5. Bitwise Elevation Benchmark Preservation

All three certified high-resolution DTM elevation benchmarks were verified via direct API test queries against `http://127.0.0.1:8000/api/v1/terrain/elevation/point` and remain 100% bitwise intact:

1. **Tyrrhena Terra CTX DTM Benchmark**:
   - Location: `Lat -4.600°, Lon 66.317°E` (`4.600°S, 66.317°E`)
   - Product: `P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif`
   - Measured Areoid Height: `+2189.49 m` (Bitwise match: `2189.49`)
2. **Apollinaris Sulci Controlled CTX DTM Benchmark**:
   - Location: `Lat 4.700°, Lon 168.250°E` (`4.700°N, 168.250°E`)
   - Product: `T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif`
   - Measured Areoid Height: `-2930.77 m` (Bitwise match: `-2930.77`)
3. **Holden Crater Controlled HiRISE DTM Benchmark**:
   - Location: `Lat -28.500°, Lon 309.020°E` (`28.500°S, 309.020°E`)
   - Product: `DTEEC_011635_1510_029542_1510_A01.tif`
   - Measured Areoid Height: `-1132.14 m` (Bitwise match: `-1132.14`)

---

## 6. Software Architecture & API Changes

### Frontend Implementation
- `frontend/src/lib/types.ts`:
  - Enriched `CandidateDiscovery` with `primary_evidence_class?: string;`, `primary_source?: DiscoveryPrimarySource;`, and expanded `evidence_classes` to include `direct_sensor_observations?: string[];` and `mapped_geological_interpretations?: string[];`.
- `frontend/src/lib/api.ts`:
  - Updated `normalizeDiscovery` to map and preserve `primary_evidence_class`, `primary_source`, and `coordinate_display`.
- `frontend/src/components/panels/ScienceExplorerPanel.tsx`:
  - Updated Left Discovery List to render `1:20M Scale` or native raster spacing pill dynamically.
  - Modernized Top Parameter Tile 4 to display `PRIMARY SOURCE SCALE / RES` (`primary_source.native_scale_or_spacing`) rather than conflating MOLA 463 m raster spacing with geological units.
  - Expanded Evidence Classification Matrix to render the 5 epistemological classes:
    - *Direct Sensor Observations* (with explicit notice that raw pushbroom CCD arrays reside in NASA PDS archives)
    - *Derived Measurements*
    - *Mapped Geological Interpretations (USGS SIM 3292)*
    - *Indicative Proxies (TES & THEMIS)*
    - *Potential Investigations (Candidate Hypotheses)*

### Backend Implementation
- `backend/app/science/discovery_service.py`:
  - Enriched all 18 candidate discoveries with `primary_source` objects documenting `feature_or_product`, `source_type`, `native_scale_or_spacing`, `positional_precision`, `vertical_datum`, `vertical_datum_type: "areoid_height"`, and `coverage_limitations`.
  - Upgraded evidence matrices across all candidates to provide explicit entries for all 5 epistemological classes.
  - Implemented `vertical_reference_audit` block in `get_science_profile` returning datum harmonization metadata.
- `backend/tests/test_phase8_7_2_semantics.py`:
  - Authored a dedicated 7-test suite verifying primary evidence class partitioning, epistemological 5-class matrices, scale vs. pixel resolution segregation, vertical reference areoid semantics, zero double negatives, and benchmark preservation.
- `backend/tests/test_phase8_7_1_audit.py`:
  - Updated `valid_classes` to encompass `mapped_geological_interpretation`, `composite_interpretation`, and `direct_sensor_observation`.

---

## 7. Verification & Test Execution Results

### Backend Automated Test Suite
- **Phase 8.7.2 Semantics Suite**: `backend/tests/test_phase8_7_2_semantics.py`
  - Result: **7 passed in 1.36s**
- **Phase 8.7 & 8.7.1 Suites**: `backend/tests/test_phase8_7_discovery.py` & `backend/tests/test_phase8_7_1_audit.py`
  - Result: **15 passed in 4.84s**
- **Complete Test Suite**: All 27 test files in `backend/tests/`
  - Result: **266 passed, 0 failed in 81.68s**

### Frontend Production Build
- Command: `npm run build --prefix frontend`
- Compiler: Next.js 16.4.6 (Turbopack)
- Result: **Compiled successfully; TypeScript typecheck completed in 3.7s; 0 lint/type errors.**

### Live Visual UI Verification
- Screenshots captured via Puppeteer headless browser:
  - `docs/research/screenshots/08_science_explorer_panel.png`: Displays active discovery candidate with `1:20,000,000 published cartographic map scale` and the 5-tier Evidence Classification Matrix.
  - `docs/research/screenshots/09_discovery_map_markers.png`: Displays global map markers and docked discovery drawer.

---

## 8. Physical Dataset Limitations & Transparency Notice

In keeping with MARS-X data integrity principles:
1. **Raw Sensor Pushbroom Data**: MARS-X does not store the multi-gigabyte raw EDR/RDR pushbroom image cubes for CTX and HiRISE. Instead, it integrates verified photogrammetric DTM products generated via USGS ISIS and Ames Stereo Pipeline. Links and product IDs for the original NASA PDS archives are provided in `dataset_provenance_registry.json`.
2. **Thermal Inertia Proxy Limitations**: TES apparent thermal-inertia values are derived from band-10 brightness temperatures via a lookup table (LUT) stepping at approximately 0.50% resolution. They are indicative thermophysical proxies, not calibrated surface temperatures.
3. **THEMIS 8-bit Visual Preview**: The THEMIS daytime IR mosaic integrated for regional context is an 8-bit visual rendering (0–255 DN) resampled to ~231.5 m/px, not calibrated physical radiance ($W\cdot m^{-2}\cdot sr^{-1}\cdot\mu m^{-1}$).
4. **SIM 3292 Geological Boundary Uncertainty**: Contacts and unit boundaries mapped at 1:20,000,000 scale carry compilation uncertainties of ~5–25 km. They define regional stratigraphic provinces, not meter-scale field boundaries.

---

## 9. Conclusion & Readiness

Phase 8.7.2 has fully closed all scientific classification, scale-versus-resolution, and vertical-reference ambiguities in the Science Discovery System. The codebase is clean, tests are 100% passing, and the repository is ready for Phase 8.8.
