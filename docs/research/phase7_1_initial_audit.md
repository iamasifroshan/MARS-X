# MARS-X — Phase 7.1 Research: Initial Scientific Audit & Physical Data Inventory

## 1. Audit Context and Objectives

Phase 7 introduced multi-resolution planetary terrain capabilities to MARS-X, expanding MOLA 128 ppd regional coverage, ingesting an authentic USGS Controlled CTX numerical DTM, cataloguing local HiRISE DTMs, and establishing cross-sensor elevation analysis.

This independent audit verifies every claimed dataset, physical raster, metadata field, coordinate reference system, and validation state directly from the local repository and filesystem.

---

## 2. Physical File & Cryptographic Inventory

All files were inspected on disk (`E:\MARS-X\data\raw\`), with file sizes and SHA-256 cryptographic hashes recomputed directly from the binary byte streams.

| Product Identifier | Local File Path | File Size (bytes) | Recomputed SHA-256 Checksum | Ingested Lifecycle State | True Evidence Base |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mola-megdr-4` | `data/raw/mola/megt90n000cb.img` | 2,073,600 | `25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c` | `analysis_ready` | Full global raster present, SHA-256 verified |
| `mola-megdr-4` (label) | `data/raw/mola/megt90n000cb.lbl` | 4,796 | `5a3fe60256afa1c35fea5d551fe0ab0a9198fb2bcd2c2e161d078aa69627ebac` | `metadata_validated` | PDS v3 detached label verified |
| `megt00n000hb` | `data/raw/mola/megt00n000hb.img` | 129,761,280 | `f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75` | `analysis_ready` | 5632×11520 binary raster present, SHA-256 verified |
| `megt00n000hb` (label) | `data/raw/mola/megt00n000hb.lbl` | 4,818 | `d27d0b5635a5024dd5d95845fd83477dc5f723976444d1e5882a675027b0da13` | `metadata_validated` | PDS v3 detached label verified |
| `megt44n000hb` | `data/raw/mola/megt44n000hb.img` | 129,761,280 | `14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36` | `scientifically_validated` | 5632×11520 binary raster present, SHA-256 verified |
| `megt44n000hb` (label) | `data/raw/mola/megt44n000hb.lbl` | 4,820 | `bc624a238ba6d71a770a09f959ead96f1c144970fae435b8ca5e26208b42eec5` | `metadata_validated` | PDS v3 detached label verified |
| `megt00n090hb` | `data/raw/mola/megt00n090hb.img` | 129,761,280 | `764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e` | `scientifically_validated` | 5632×11520 binary raster present, SHA-256 verified |
| `megt00n090hb` (label) | `data/raw/mola/megt00n090hb.lbl` | 4,820 | `c85891df3c11e724c5c5d980630e56ee4f13c40d234b68e22401b9a404df3d36` | `metadata_validated` | PDS v3 detached label verified |
| `ctx-dtm-p21-009323` | `data/raw/ctx/P21_009323_..._dtm.tif` | 12,734,013 | `a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2` | `analysis_ready` | 3472×1692 Float32 Cloud-Optimized GeoTIFF present |
| `ctx-dtm-p21-009323` (provenance) | `data/raw/ctx/P21_009323_..._provenance.json` | 1,440 | `be3d7c199983005e8be6debde94d172c4d041a1e99105a0b9a0ec5c6b1bf5621` | `metadata_validated` | Processing manifest present |
| `ctx-dtm-p21-009323` (STAC) | `data/raw/ctx/P21_009323_..._stac.json` | 15,525 | `781f56e4a01999b7eeea5323e86275a4238a5e089246f83a8b0e1c56fe93cda6` | `metadata_validated` | USGS Astrogeology STAC item present |
| `hirise-dtm-schiaparelli` | None (no local raster) | 0 | None | `discovered` | Registered via PDS product ID; no local raster |
| `hirise-dtm-jezero` | None (no local raster) | 0 | None | `discovered` | Registered via PDS product ID; no local raster |

---

## 3. Detailed Dataset Profile & Geodetic Parameters

| Property | MOLA MEGDR 4 ppd | MOLA MEGDR 128 ppd (3 tiles) | USGS Controlled CTX DTM | HiRISE DTMs (Schiaparelli / Jezero) |
| :--- | :--- | :--- | :--- | :--- |
| **Product Format** | Flat binary big-endian Int16 (`>i2`) | Flat binary big-endian Int16 (`>i2`) | Cloud-Optimized GeoTIFF (`float32`) | Not downloaded (remote PDS IMG / GeoTIFF) |
| **Raster Dimensions** | 720 lines × 1,440 samples | 5,632 lines × 11,520 samples (per tile) | 3,472 lines × 1,692 samples | $\sim 40,000 \times 10,000$ (nominal) |
| **Native Pixel Spacing** | $0.25^\circ$/px ($\sim 14,818\text{ m/px}$) | $0.0078125^\circ$/px ($463.08\text{ m/px}$) | $20.0128\text{ m/px}$ | $1.0\text{ m/px}$ (nominal) |
| **Horizontal CRS** | Equirectangular Mars (IAU:49900) | Simple Cylindrical, $R = 3,396,000\text{ m}$ | `IAU:49910` (Equirectangular, $R = 3,396,190\text{ m}$) | Equirectangular Mars (clat = center lat) |
| **Vertical Reference Datum** | MOLA Areoid (GMM-3 to degree 50) | MOLA Areoid (GMM-3 to degree 50) | MOLA Areoid (tied via ASP `pc_align`) | MOLA Areoid (tied via manual/auto GCPs) |
| **NoData Sentinel** | `-32768` | `-32768` | `-32767.0` | `-3.4028235e+38` |
| **Elevation Range** | $-8,068\text{ m}$ to $+21,134\text{ m}$ | $-3,088\text{ m}$ to $+4,116\text{ m}$ (in acquired tiles) | $+797.6\text{ m}$ to $+2,514.3\text{ m}$ | $-2,500\text{ m}$ to $+500\text{ m}$ (nominal) |
| **Valid Pixel Percentage** | 100% | 100% (within tile bounding boxes) | 72.88% (4,281,424 valid pixels) | 0% locally |
| **Physical Storage on Disk** | 2.07 MB | 389.28 MB | 12.73 MB | 0.0 MB |

---

## 4. Lifecycle State Audit

MARS-X strictly separates catalog registration from physical availability and scientific validation:
- **`registered`**: Product metadata schema validated.
- **`discovered`**: Remote archive endpoints, STAC items, and PDS labels verified (`hirise-dtm-schiaparelli`, `hirise-dtm-jezero`).
- **`downloaded`**: Physical file verified on disk.
- **`integrity_verified`**: SHA-256 hash verified against upstream manifest.
- **`metadata_validated`**: Header parameters, data types, and scale factors verified.
- **`geospatially_validated`**: Bounds, CRS, and pixel-registration verified.
- **`scientifically_validated`**: Elevation value ranges, landmark features, and NoData masks confirmed (`megt44n000hb`, `megt00n090hb`).
- **`analysis_ready`**: Fully integrated into pathfinding, hazard analysis, and cross-comparison engines (`megt00n000hb`, `mola-megdr-4`, `ctx-dtm-p21-009323`).

No product may be promoted to `analysis_ready` solely on the basis of catalog presence or file existence.
