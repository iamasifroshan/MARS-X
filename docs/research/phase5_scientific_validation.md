# MARS-X — Scientific Validation & Verification Report (Phase 5)

## 1. Overview & Verification Summary
MARS-X enforces a strict distinction between catalogue metadata and authentic, verified elevation data. No dataset is labeled `analysis_ready` unless its raw binary array, PDS3 label, coordinate transform, and elevation bounds have been validated through automated verification pipelines.

## 2. Ingested Dataset Verification

### 2.1 MOLA MEGDR 4 ppd (`MEGT90N000CB`)
- **Product ID:** `MEGT90N000CB`
- **Source Archive:** NASA PDS Geosciences Node (`mgsl_300x/meg004/`)
- **File Integrity:**
  - Label: `megt90n000cb.lbl` (4,796 bytes), SHA-256: `5a3fe60256afa1c35fea5d551fe0ab0a9198fb2bcd2c2e161d078aa69627ebac`
  - Image: `megt90n000cb.img` (2,073,600 bytes), SHA-256: `25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c`
- **Array Properties:**
  - Dimensions: 720 lines $\times$ 1440 samples
  - Encoding: 16-bit signed integer (`MSB_INTEGER`), big-endian
  - Valid Pixels: 1,036,800 ($100.0000\%$). Zero NoData (-32768) pixels exist in the interpolated global grid.
  - Elevation Statistics: Min $-8,068\text{ m}$, Max $+21,134\text{ m}$, Mean $-721.74\text{ m}$
  - Physical Landmarks:
    - Olympus Mons Caldera ($18.65^\circ\text{N}, 226.20^\circ\text{E}$): Sampled $20,009\text{ m}$
    - Hellas Planitia Floor ($-42.50^\circ\text{N}, 70.50^\circ\text{E}$): Sampled $-6,151\text{ m}$

### 2.2 MOLA MEGDR 128 ppd Tile (`MEGT00N000HB`)
- **Product ID:** `MEGT00N000HB`
- **Source Archive:** NASA PDS Geosciences Node (`mgsl_300x/meg128/`)
- **File Integrity:**
  - Label: `megt00n000hb.lbl` (4,818 bytes), SHA-256: `d27d0b5635a5024dd5d95845fd83477dc5f723976444d1e5882a675027b0da13`
  - Image: `megt00n000hb.img` (129,761,280 bytes, 123.75 MB), SHA-256: `f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75`
- **Array Properties:**
  - Dimensions: 5,632 lines $\times$ 11,520 samples (64,880,640 pixels)
  - Native Resolution: $0.0078125^\circ/\text{px} \approx 463.08\text{ m/px}$
  - Bounds: Latitude $[-44.0^\circ, 0.0^\circ]$, Longitude $[0.0^\circ, 90.0^\circ\text{E}]$
  - Valid Coverage: $100.0000\%$ ($64,880,640$ valid pixels, 0 NoData)
  - Elevation Range: $-8,208\text{ m}$ to $+4,686\text{ m}$ (Mean $+130.77\text{ m}$)

---

## 3. Dataset Lifecycle & State Machine
MARS-X enforces the following progressive validation states:
1. `registered`: Entry catalogued from NASA documentation.
2. `discovered`: Verified in remote archive (ESA PSA, USGS, PDS).
3. `downloaded`: Raw file saved to local immutable storage.
4. `integrity_verified`: Cryptographic hash matches source manifest.
5. `metadata_validated`: PDS label or raster header parsed.
6. `geospatially_validated`: Coordinate bounds and CRS verified.
7. `scientifically_validated`: Array ranges and physical landmarks verified.
8. `analysis_ready`: Ingested into the engine for hazard calculations.
