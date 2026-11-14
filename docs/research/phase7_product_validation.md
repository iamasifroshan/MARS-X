# MARS-X — Phase 7 Research: Product Validation & Elevation Quality Metrics

## 1. Scope of Validation

To ensure rigorous planetary data standards, all elevation products in MARS-X are subjected to multi-stage verification before being promoted across the 10-state lifecycle:

`registered` ➔ `discovered` ➔ `downloaded` ➔ `integrity_verified` ➔ `metadata_validated` ➔ `geospatially_validated` ➔ `scientifically_validated` ➔ `analysis_ready`.

---

## 2. Validation Evidence Matrix

| Dataset / Product ID | Native Pixel Spacing | Checksum Validation | Geospatial Validation | NoData Sentinel Handling | Scientific Landmark & Range Check | Lifecycle Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mola-megdr-4` | 14,818 m/px | SHA-256 Verified | Equirectangular IAU:49900 bounds `[-88°, +88°]` | `-32768` masked; valid mask enforced | Elevation range: `[-8,068m, +21,134m]` (Olympus Mons verified) | `analysis_ready` |
| `mola-megdr-128` (3 tiles) | 463.08 m/px | SHA-256 Verified for all 3 tiles | Bounds & seamless equatorial/meridional adjacency verified | `-32768` masked; 0 valid NoData in southern highlands | Elevation range: `[-3,088m, +4,116m]` across Tyrrhena Terra | `analysis_ready` |
| `ctx-dtm-p21-009323` | 20.01 m/px | SHA-256 Verified (`a4edb9f4...`) | IAU:49910 bounds verified inside `megt00n000hb` | `-32767.0` masked (27.12% nodata rim borders) | Elevation range: `[+797.6m, +2514.3m]`, 4.28M valid pixels | `analysis_ready` |
| `hirise-dtm-schiaparelli` | 1.01 m/px | PDS Product ID Verified | IAU:49910 projection tied to MOLA tracks | `-3.4028235e+38` masked | Micro-dune morphology and yardangs | `discovered` |

---

## 3. Real Raster Numerical Elevation Comparison

Using the authentic USGS CTX numerical DTM (`P21_009323_1754_XN_04S293W...`) and the overlapping authentic MOLA 128 tile (`megt00n000hb`), MARS-X executed cross-sensor elevation analysis across the confirmed overlap region:

- **Overlap Footprint:** Latitude `[-5.187°, -4.003°]`, Longitude `[66.036°, 66.617°E]`
- **Geographic Overlap Area:** **2,410.10 km²** (Spherical bounding box) / **1,714.77 km²** (Valid stereo data)
- **MOLA 128 ppd Mean Elevation:** **+2,054.16 meters**
- **CTX DTM Mean Elevation:** **+1,996.59 meters**
- **Mean Elevation Difference ($\mu_{\Delta z} = z_{\text{CTX}} - z_{\text{MOLA}}$):** **-57.57 meters**
- **Standard Deviation ($\sigma_{\Delta z}$):** **51.79 meters**
- **Root Mean Square Error (RMSE):** **77.44 meters**
- **Min Delta / Max Delta:** -258.82 m / +184.04 m

### Scientific Interpretation
The systematic elevation difference ($\mu_{\Delta z} = -57.57\text{ m}$) is scientifically expected when comparing regional orbital laser altimetry against high-resolution stereophotogrammetry. MOLA's 463 m post-spacing and ~168 m physical laser footprint spatially averages crater rims and canyon floors, smoothing sharp local depressions. In contrast, 20 m/px CTX stereogrammetry accurately resolves interior crater depth and micro-canyons, resulting in lower local minima and higher crest peaks within the complex cratered terrain of Tyrrhena Terra.

