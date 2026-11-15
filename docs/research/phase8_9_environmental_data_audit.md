# Phase 8.9.0: Environmental Data Availability & Scientific Source Audit

**Project:** MARS-X — Interplanetary Survival Guide: Martian Map (NASA Space Apps Challenge 2026)  
**Baseline Git Commit:** `a78bb99` (`phase8.8.5: complete independent traverse validation and integrity audit`)  
**Mission Milestone:** Phase 8.9.0 — Environmental Data Availability & Scientific Source Audit  
**Status:** **PASS WITH LIMITATIONS**  

---

## 1. Executive Summary

Phase 8.9.0 executes a rigorous scientific source audit of all Martian environmental, atmospheric, meteorological, and thermophysical data currently resident in the MARS-X repository or cataloged in project metadata. 

Where Phase 8.8 established a mathematically and geodetically validated terrain traversability and route intelligence framework across digital elevation models (HiRISE, CTX, and MOLA), Phase 8.9 investigates the availability, provenance, spatial/temporal scope, and physical validity of environmental data (atmospheric pressure, ambient and surface temperatures, wind velocity, atmospheric opacity/dust attenuation, ultraviolet/solar flux, and local solar time) to support future route contextualization.

### Core Audit Findings
1. **Local In-Situ Rover Meteorological Data Verified:** Authentic PDS4 observational products from Mars 2020 Perseverance (MEDA) and MSL Curiosity (REMS) are resident on disk with verified SHA-256 checksums and PDS4 XML schema definitions.
2. **Spatial and Temporal Confinement:** Local in-situ datasets represent historical single-sol observations (Sol 1) at localized landing sites (Jezero Crater floor for MEDA; Gale Crater floor for REMS). They provide high-precision ground-truth calibration for local diurnal cycles but **cannot** scientifically represent current global Mars weather or conditions along arbitrary exploration traverses (e.g. Tyrrhena Terra, Holden Crater, or Apollinaris Sulci).
3. **Orbital Thermophysical Data Verified:** Global MGS TES 20 ppd dayside and nightside thermal inertia GeoTIFFs (Putzig & Mellon, 2007) are resident and validated. These provide static thermophysical surface property constraints ($I = \sqrt{k \rho c}$ in $\text{TIU}$), but strictly do **not** provide surface kinetic temperatures or atmospheric state variables.
4. **Orbital Infrared Imagery Context:** 2001 Mars Odyssey THEMIS IR regional mosaics (Sinus Meridiani) are confirmed to be 8-bit visual display products (DN 0–255, Band 9 $12.57\,\mu\text{m}$) and must remain qualitative proxies, never treated as calibrated radiance or physical temperature.
5. **Key Environmental Data Gaps:** No continuous global atmospheric fields (such as Mars Climate Sounder vertical soundings or Mars Climate Database/GCM reanalyses) currently reside locally. Arbitrary Marswalk traverses cannot rely on MEDA/REMS point observations without explicit barometric elevation scaling ($P(z) = P_0 e^{-z/H}$) and solar orbital geometry ($L_s$, $LTST$, $SZA$).
6. **Disk Budget:** Host drive `E:` has **23.18 GB free** and `C:` has **26.89 GB free**. Acquisition of gigabyte-scale orbital archives must be avoided in favor of a lightweight, defensible analytical model and climatology lookup table.

---

## 2. Git Baseline Verification

- **Baseline Commit:** `a78bb99152f13fbdce2cac8d8f9ca81b2089b955` (`a78bb99`)
- **Branch:** `master`
- **Working Tree:** Verified clean with 0 uncommitted changes.

---

## 3. Local Environmental Dataset Inventory

The following table documents every environmental data product currently resident on local disk in `E:\MARS-X\data`:

| Discipline / Instrument | Product Logical Identifier (LID) / Filename | File Path | Size (Bytes) | SHA-256 Checksum | Format / Standard | Observation Target / Sol |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **Mars 2020 MEDA** | `urn:nasa:pds:mars2020_meda:data_derived_env:we__0001___________der_ps__________________p` | `data/originals/meda/WE__0001___________DER_PS__________________P02.CSV` | 125,877 | `600d8d11b26b2127ba66f90889e7ba5621a0b8b788146bf5bf72a02be2e0a16c` | PDS4 Delimited Table (CSV) | Jezero Crater ($18.4447^\circ\text{N}, 77.4508^\circ\text{E}$), Sol 1 |
| **Mars 2020 MEDA** | PDS4 XML Label for Derived Pressure | `data/originals/meda/WE__0001___________DER_PS__________________P02.xml` | 9,326 | `bf91828374f61d9267baf2f35b2784e50ffd44ea4b3559e023295ff075068c91` | PDS4 XML Schema (1.16.0.0) | Jezero Crater, Sol 1 |
| **Mars 2020 MEDA** | `urn:nasa:pds:mars2020_meda:data_derived_env:we__0001___________der_rhs_________________p` | `data/originals/meda/WE__0001___________DER_RHS_________________P03.CSV` | 102,060 | `00271c06137f76294541e2c028c1ed76fca85a11829cf7c76c82fb2cd86e35d8` | PDS4 Delimited Table (CSV) | Jezero Crater, Sol 1 |
| **Mars 2020 MEDA** | PDS4 XML Label for Humidity / Temp | `data/originals/meda/WE__0001___________DER_RHS_________________P03.xml` | 10,880 | `29cb6b7cfff3ca88404df1311b58a2e2931f8dfada46b253faa25dd4e7d50a84` | PDS4 XML Schema (1.16.0.0) | Jezero Crater, Sol 1 |
| **Mars 2020 MEDA** | `urn:nasa:pds:mars2020_meda:data_derived_env:we__0001___________der_tirs________________p` | `data/originals/meda/WE__0001___________DER_TIRS________________P04.CSV` | 7,417 | `ded7c255c90ede5fbbfbb66396c562b0ebc4d1682b71e29976e23cbc4cb47815` | PDS4 Delimited Table (CSV) | Jezero Crater, Sol 1 |
| **Mars 2020 MEDA** | PDS4 XML Label for Thermal IR Sensor | `data/originals/meda/WE__0001___________DER_TIRS________________P04.xml` | 13,751 | `970c099fd89a2c01b9e442613d60104c1a76e5f71b7957867fd519c51b5d3673` | PDS4 XML Schema (1.16.0.0) | Jezero Crater, Sol 1 |
| **MSL Curiosity REMS** | `urn:nasa:pds:msl_rems:data_calibrated:rme_397535244adr00010000000_______p9` | `data/originals/rems/RME_397535244ADR00010000000_______P9.TAB` | 114,152 | `d5edd3d49198992bd36244b4b151b8850befce2d91b9c774cce72a40e254d194` | PDS4 Fixed-width Character Table | Gale Crater ($4.59^\circ\text{S}, 137.44^\circ\text{E}$), Sol 1 |
| **MSL Curiosity REMS** | PDS4 XML Label for ADR (Attitude/Dust) | `data/originals/rems/RME_397535244ADR00010000000_______P9.xml` | 17,146 | `c74c1258074918630f716a2dcadf24f272c9501a034ebb06d88d130840f86618` | PDS4 XML Schema (1.18.0.0) | Gale Crater, Sol 1 |
| **MSL Curiosity REMS** | `urn:nasa:pds:msl_rems:data_calibrated:rme_397535244rmd00010000000_______pa` | `data/originals/rems/RME_397535244RMD00010000000_______PA.TAB` | 279,000 | `e38f69846b30e84c13d6bc916b04e2ff27a782172c35bc025faca65740f3669f` | PDS4 Fixed-width Character Table | Gale Crater, Sol 1 |
| **MSL Curiosity REMS** | PDS4 XML Label for RMD (Weather RDR) | `data/originals/rems/RME_397535244RMD00010000000_______PA.xml` | 28,154 | `ce4d63f2be20f8d55d4a2ffaea8a5fedc2338f134243b96396af7af39c123af9` | PDS4 XML Schema (1.18.0.0) | Gale Crater, Sol 1 |
| **MGS TES Thermal Inertia** | Global Dayside Thermal Inertia (Putzig 2007) | `data/originals/themis/DBmap2007.tif` | 77,789,206 | `0b2ca94b9414cd7c74e73f8df9ccb4a3c104bef24da932c4dc43fb246bc71a4b` | GeoTIFF (Equirectangular, 20 ppd) | Global Mars ($90^\circ\text{S}-90^\circ\text{N}$, $0^\circ-360^\circ\text{E}$) |
| **MGS TES Thermal Inertia** | Global Nightside Thermal Inertia (Putzig 2007) | `data/originals/themis/NBmap2007.tif` | 77,789,206 | `ea428e4424f412fc8c94c10e73ed88176f812c2a10fd2e81e9b7d37a5828802e` | GeoTIFF (Equirectangular, 20 ppd) | Global Mars ($90^\circ\text{S}-90^\circ\text{N}$, $0^\circ-360^\circ\text{E}$) |
| **2001 Mars Odyssey THEMIS** | Nighttime IR Regional Mosaic (Sinus Meridiani) | `data/originals/themis/themis_nightir_N-30_000.png` | 49,490,620 | `ebd045a3ca522624ec41c41611415095d07db9452b867cbb205ddba2c2a2f66d` | 8-bit Greyscale PNG (256 ppd) | Sinus Meridiani (Lat $-30^\circ\dots 0^\circ$, Lon $0^\circ\dots 30^\circ\text{E}$) |
| **2001 Mars Odyssey THEMIS** | Daytime IR Regional Mosaic (Sinus Meridiani) | `data/originals/themis/thm_dir_N-30_000.png` | 38,612,248 | `0f80f5cd8a4bdc59d7f9f3b9d1c566bd8f9437cccff68c873d1394b1aa19d7af` | 8-bit Greyscale PNG (256 ppd) | Sinus Meridiani (Lat $-30^\circ\dots 0^\circ$, Lon $0^\circ\dots 30^\circ\text{E}$) |

---

## 4. Detailed Scientific Source Verification & Provenance

### 4.1 Mars 2020 Perseverance — MEDA (Mars Environmental Dynamics Analyzer)
- **Authoritative Provider:** NASA Planetary Data System (PDS) Atmospheres Node (`pds-atmospheres.nmsu.edu`).
- **Instrument Bundle:** `urn:nasa:pds:mars2020_meda`
- **Lead Institution:** Centro de Astrobiología (CAB / CSIC-INTA), Madrid, Spain (Principal Investigator: J. A. Rodriguez-Manfredi).
- **Physical Sensors & Verified Schema Columns:**
  1. **Pressure Sensor (PS):**
     - SCLK (Spacecraft Clock in seconds with millisecond decimals).
     - LMST (Local Mean Solar Time) and LTST (Local True Solar Time).
     - Surface Atmospheric Pressure: Measured in Pascals ($\text{Pa}$). Range in Sol 1 sample: $715.56\text{ Pa}$ to $716.03\text{ Pa}$.
     - Uncertainty: Estimated systematic barocap sensor uncertainty.
     - Transducer ID: 1 or 2 (Vaisala Barocap silicone micromachined capacitive sensors).
  2. **Relative Humidity Sensor (RHS):**
     - Local Relative Humidity: Measured in percentage ($\%$) with respect to ice saturation.
     - Local Humidity Sensor Temperature: Measured in Kelvin ($\text{K}$).
     - Water Vapor Volume Mixing Ratio: Measured in parts-per-million ($\text{ppm}$).
  3. **Thermal Infrared Sensor (TIRS):**
     - Downward Longwave Irradiance: $\text{W}\cdot\text{m}^{-2}$ (Sky brightness temperature).
     - Upward Longwave Irradiance: $\text{W}\cdot\text{m}^{-2}$ (Ground surface brightness temperature).
     - Quality Flags: Rover Remote Sensing Mast (RSM) head obstruction (0/1), front wheel obstruction (0/1), Sun in FOV (0/1), rover tilt $\le \pm 20^\circ$ (0/1), ground footprint shadowed by rover (0/1), and rover motion state (0 = moving, 1 = still).
- **Coordinate System:** Planetocentric surface coordinates at Octavia E. Butler Landing ($18.4447^\circ\text{N}, 77.4508^\circ\text{E}$), Elevation $-2560\text{ m}$ relative to MOLA Areoid.
- **Time Representation:** UTC, SCLK, LMST, LTST, and Solar Longitude ($L_s = 6.149^\circ - 6.168^\circ$).

### 4.2 MSL Curiosity — REMS (Rover Environmental Monitoring Station)
- **Authoritative Provider:** NASA Planetary Data System (PDS) Atmospheres Node (`pds-atmospheres.nmsu.edu`).
- **Instrument Bundle:** `urn:nasa:pds:msl_rems`
- **Lead Institution:** Centro de Astrobiología (CAB / CSIC-INTA), Madrid, Spain (Principal Investigator: J. Gomez-Elvira).
- **Physical Sensors & Verified Schema Columns:**
  1. **Calibrated Environmental Records (RMD / MODRDR):**
     - TIMESTAMP: Integer seconds since epoch J2000 (noon 2000-01-01).
     - Wind Vector: `HORIZONTAL_WIND_SPEED` ($\text{m/s}$), `VERTICAL_WIND_SPEED` ($\text{m/s}$), `WIND_DIRECTION` ($0^\circ - 360^\circ$ clockwise from North).
     - Ground Temperature: `BRIGHTNESS_TEMP` ($\text{K}$) with long-term and short-term systematic uncertainties.
     - Air Temperatures: `BOOM1_LOCAL_AIR_TEMP` ($\text{K}$), `BOOM2_LOCAL_AIR_TEMP` ($\text{K}$), and estimated unperturbed `AMBIENT_TEMP` ($\text{K}$).
     - Ultraviolet Irradiance: `UV_A`, `UV_B`, `UV_C`, `UV_ABC`, `UV_D`, `UV_E` ($\text{W}\cdot\text{m}^{-2}$) with percentage uncertainties.
     - Relative Humidity & Mixing Ratio: `LOCAL_RELATIVE_HUMIDITY` ($\%$), `HS_TEMP` ($\text{K}$), and `VOLUME_MIXING_RATIO` ($\text{ppm}$).
     - Atmospheric Pressure: `PRESSURE` ($\text{Pa}$) with absolute accuracy uncertainty.
  2. **Attitude and Sensor Degradation Records (ADR):**
     - `UV_DUST_ATTENUATION`: Fraction of UV attenuation caused by airfall dust accumulation on photodiode optics ($1.0 = \text{clean}, 0.0 = \text{fully opaque}$).
     - Solar Geometry: `SOLAR_LONGITUDE_ANGLE` and `SOLAR_ZENITHAL_ANGLE` ($SZA$) relative to REMS frame.
     - Rover Kinematics: `ROVER_POSITION_X/Y/Z` relative to Bradbury Landing in meters, pitch, yaw, roll, masthead azimuth/elevation, arm state.
- **Missing Data Conventions:** Real floating-point missing samples are strictly encoded as `-999.00`; missing confidence bitstrings are encoded as `XXXXXX`.
- **Coordinate System:** Gale Crater Bradbury Landing ($4.591^\circ\text{S}, 137.441^\circ\text{E}$), Elevation $-4440\text{ m}$ relative to MOLA Areoid.

### 4.3 MGS TES Thermal Inertia (Putzig & Mellon 2007)
- **Authoritative Provider:** Putzig & Mellon (2007), Arizona State University / Mars Space Flight Facility.
- **Source Product:** MGS Thermal Emission Spectrometer (TES) thermal emission bolometer profiles during mapping orbit.
- **Spatial Grid:** Global Equirectangular grid at $20\text{ ppd}$ ($\sim 2.96\text{ km/pixel}$ at equator), $7200 \times 3600$ pixels.
- **Physical Parameter:** Apparent Thermal Inertia ($I = \sqrt{k \rho c}$), units $\text{J}\cdot\text{m}^{-2}\cdot\text{K}^{-1}\cdot\text{s}^{-1/2}$ ($\text{TIU}$).
- **Calibration:** 790-step logarithmic look-up table relating 8-bit raster values to thermal inertia:
  $$I = 50 \times 50^t, \quad t = \frac{\text{DN} - 1}{789}$$
  Valid range: $50\text{ to }2500\text{ TIU}$.

---

## 5. Spatial and Temporal Coverage Analysis

| Dataset | Type | Spatial Coverage | Spatial Resolution | Observation Interval | Temporal Frequency |
|:---|:---|:---|:---:|:---:|:---:|
| **Mars 2020 MEDA** | In-situ Rover Station | Jezero Crater point ($18.44^\circ\text{N}, 77.45^\circ\text{E}$) | Single Point (rover deck) | Sol 1 ($L_s \approx 6.15^\circ$, Year 36) | 1 Hz (continuous / periodic bursts) |
| **MSL Curiosity REMS** | In-situ Rover Station | Gale Crater point ($4.59^\circ\text{S}, 137.44^\circ\text{E}$) | Single Point (rover mast) | Sol 1 ($L_s \approx 150.7^\circ$, Year 31) | 1 Hz (1 hr continuous + 5 min/hr) |
| **MGS TES Thermal Inertia** | Orbital Synthesis | Global Mars ($90^\circ\text{S}-90^\circ\text{N}$, $0^\circ-360^\circ\text{E}$) | $20\text{ ppd}$ ($\sim 3\text{ km/px}$) | MGS Mapping Phase (1999–2006) | Diurnal Composite (Dayside 14:00, Nightside 02:00) |
| **Odyssey THEMIS IR** | Orbital Thermal Camera | Sinus Meridiani ($30^\circ\text{S}-0^\circ$, $0^\circ-30^\circ\text{E}$) | $256\text{ ppd}$ ($\sim 231.5\text{ m/px}$) | Odyssey Primary / Extended Mission | Composite Daytime & Nighttime Display |

---

## 6. Scientific Suitability Matrix for Marswalk Traversability

| Environmental Parameter | Required for Route Intelligence | Available Locally? | Source Product | Scientific Suitability & Boundary Rules |
|:---|:---:|:---:|:---|:---|
| **Atmospheric Pressure** | Critical (barometric gradient & scale height) | **Partial** | MEDA Sol 1 / REMS Sol 1 | **SUITABLE AS LOCAL BENCHMARK ONLY.** Local point measurements cannot be directly applied to Tyrrhena or Holden traverses. Must use barometric elevation scaling $P(z) = P_0 e^{-z/H}$ tied to elevation models. |
| **Surface Temperature** | Critical (diurnal thermal extremes) | **Missing for routes** | None for arbitrary traverses | **INSUFFICIENT.** TES thermal inertia ($I$) is a material property, NOT temperature. THEMIS is qualitative DN. MEDA/REMS surface temps represent Sol 1 in Jezero/Gale only. |
| **Ambient Air Temperature** | Important (atmospheric boundary layer) | **Partial** | MEDA / REMS Sol 1 | **INSUFFICIENT FOR GENERAL ROUTES.** Gale/Jezero basin boundary layer inversions cannot be transferred to high-altitude volcanic flanks (Tyrrhena) or crater rims. |
| **Wind Speed & Direction** | Important (aerodynamic drag, dust lofting) | **Partial** | REMS Sol 1 | **QUALITATIVE PROXY ONLY.** REMS Boom 1 sensor has known directional damage; Gale wind regimes are dominated by crater katabatic/anabatic slopes. |
| **UV & Solar Flux** | Important (photodegradation, solar power) | **Partial** | REMS Sol 1 (UV A–E), MEDA (LW IR) | **MODELABLE.** Solar irradiance can be deterministically calculated from orbital ephemeris ($L_s$), local hour angle, and atmospheric optical depth $\tau$. |
| **Dust Optical Depth ($\tau$)** | Critical (atmospheric extinction, solar attenuation) | **Missing locally** | None (MCS / MER / THEMIS $\tau$ not on disk) | **DATA GAP.** Dust opacity must either be supplied as a seasonal climatology parameter ($\tau \approx 0.3 - 0.5$ clear, $> 2.0$ dust storm) or acquired from MCS. |
| **Thermophysical Inertia** | Validated (regolith grain size & bearing state) | **YES (Global)** | MGS TES 20 ppd | **FULLY SUITABLE.** Accurately classifies regolith induration and grain size along any traverse. |

---

## 7. Data Gaps and Missing Products

1. **Mars Climate Sounder (MCS) Vertical Atmospheric Soundings:**
   - Measures vertical atmospheric profiles of temperature, dust, and water ice from MRO limb sounding.
   - Status: Not downloaded.
   - Limitation: Limb measurements terminate $5-10\text{ km}$ above the surface due to dust extinction; does not directly sample the planetary boundary layer ($< 2\text{ m}$).
2. **Global Atmospheric Circulation / Climatology Model (LMD MCD):**
   - Provides global gridded hourly predictions of pressure, temperature, wind, and radiative fluxes across Martian seasons ($L_s = 0^\circ - 360^\circ$).
   - Status: Not downloaded.
   - Limitation: Large data footprint ($> 15\text{ GB}$ for full database).
3. **Column Dust Optical Depth ($\tau$) Database:**
   - Historical daily column dust opacities from MGS TES, Odyssey THEMIS, and MRO MCS/MARCI (Montabone et al. climatology).
   - Status: Not resident locally.

---

## 8. Defensible Environmental Architecture & Acquisition Plan

To support Phase 8.9.1 and future environmental intelligence without downloading multi-gigabyte raw PDS archives or violating host disk constraints:

### 8.1 Analytical & Climatological Architecture (Zero-Download Core)
1. **Analytical Barometric Elevation Scaling:**
   Compute atmospheric pressure along any traverse path from the authoritative MOLA Areoid elevation $z$ using the hydrostatic scale height equation:
   $$P(z) = P_0 \exp\left(-\frac{z}{H}\right)$$
   where $P_0 \approx 610\text{ Pa}$ (triple-point reference pressure at $z = 0\text{ m}$) and $H \approx 11.1\text{ km}$ (scale height). Local MEDA ($715\text{ Pa}$ at $-2560\text{ m}$) and REMS ($840\text{ Pa}$ at $-4440\text{ m}$) observations serve as in-situ empirical anchor points confirming scale height validity.
2. **Deterministic Solar Geometry Engine:**
   Calculate exact local solar parameters for any coordinate $(\phi, \lambda)$ at solar longitude $L_s$ and local time $LTST$:
   - Solar Declination: $\delta = \arcsin(\sin \epsilon \sin L_s)$, where Mars obliquity $\epsilon \approx 25.19^\circ$.
   - Hour Angle: $\omega = (LTST - 12) \times 15^\circ$.
   - Solar Zenith Angle: $\cos(SZA) = \sin \phi \sin \delta + \cos \phi \cos \delta \cos \omega$.
   - Direct Solar Flux: $S = \frac{S_0}{r_{\text{Mars}}^2} \max(0, \cos(SZA)) \exp(-\tau / \cos(SZA))$, with $S_0 = 590\text{ W/m}^2$.
3. **Empirical Diurnal Temperature Boundary Layer Climatology:**
   Model surface temperature diurnal bounds using the standard Mars climatology envelope:
   $$T(LTST, z) = T_{\text{mean}}(z) + \Delta T(z) \cos\left(\frac{2\pi (LTST - 14)}{24}\right)$$
   calibrated against MEDA and REMS ground brightness thermistor measurements.

### 8.2 Smallest Defensible Acquisition Recommendation (If Download Required)
- **Target Product:** NASA / ESA Mars Climate Database (MCD) Global Monthly Climatology Summary Table (ASCII / NetCDF, $< 25\text{ MB}$).
- **Disk Budget Impact:** $< 0.1\%$ of available $23.18\text{ GB}$ free disk space.
- **Do NOT acquire:** Raw MCS limb-sounding archives ($> 100\text{ GB}$) or multi-year daily hourly GCM outputs ($> 50\text{ GB}$).

---

## 9. Risks and Scientific Integrity Rules

1. **Prohibition of Extrapolating Historical Local Weather:**
   - Historical MEDA (Sol 1, Feb 2021) and REMS (Sol 1, Aug 2012) records must be explicitly labeled as **historical single-site ground truth**, NEVER as current, active, or global Martian weather conditions.
2. **Prohibition of Temperature Conversion for THEMIS Display DN:**
   - THEMIS 8-bit visual display mosaics (DN 0–255) must remain qualitative proxies and must never be converted into quantitative surface kinetic temperature or physical radiance.
3. **No False Safety Certification:**
   - Environmental intelligence must prominently reiterate that orbital and climatological models do not certify astronaut EVA safety, spacesuit thermal regulation, or rover mechanical survivability. Unmodeled microclimate phenomena (dust devils, thermal boundary layer turbulence, localized katabatic winds) require direct operational margins.

---

## 10. Audit Decision

**DECISION: PASS WITH LIMITATIONS**

- **Justification:** High-precision in-situ meteorological datasets (MEDA, REMS) and global thermophysical datasets (MGS TES) are present, verified, and checksum-matched on disk. However, arbitrary Marswalk exploration corridors (Tyrrhena, Holden, Apollinaris) lack direct local meteorological sensor stations. Environmental route intelligence must proceed using analytical barometric scaling, deterministic solar geometry, and parameterized climatology, with MEDA/REMS serving as validated in-situ benchmark ground-truth anchors.
