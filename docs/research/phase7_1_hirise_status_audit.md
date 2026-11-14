# MARS-X — Phase 7.1 Research: HiRISE Product Status & Lifecycle Audit

## 1. HiRISE Ingestion Status

The Phase 7 implementation registered two local tactical microtopography products in the multi-resolution catalog:
1. `hirise-dtm-schiaparelli` (`DTEEC_017118_1790_016406_1790_A01`)
2. `hirise-dtm-jezero` (`ESP_042858_1985` / `ESP_039977_1985`)

---

## 2. Independent File & Directory Verification

- **Local Filesystem Inspection:**
  - Directory `data/raw/hirise/` does **NOT** exist in the workspace.
  - No physical `.IMG`, `.TIF`, or detached label files for HiRISE exist on disk.
- **Physical Availability State:** **`unavailable_locally`** (Zero local bytes).
- **Correct Lifecycle Classification:** **`discovered`**
  - Metadata, PDS product IDs, stereo pair IDs, nominal pixel spacings ($1.01\text{ m/px}$ and $1.0\text{ m/px}$), and bounding boxes are correctly indexed from published NASA PDS / University of Arizona catalog entries.
  - However, neither product is downloaded, integrity-verified, or analysis-ready.

---

## 3. Geographic Footprint and Overlap Analysis

| HiRISE Product ID | Latitude Range | Longitude Range | Overlaps Acquired MOLA Tiles? | Overlaps Acquired CTX DTM? |
| :--- | :--- | :--- | :--- | :--- |
| `hirise-dtm-schiaparelli` | $[-1.11^\circ, -0.77^\circ\text{S}]$ | $[13.80^\circ, 13.92^\circ\text{E}]$ | **YES** (100% inside `megt00n000hb`: Lat $[-44^\circ, 0^\circ]$, Lon $[0^\circ, 90^\circ\text{E}]$) | **NO** (CTX DTM is at Lon $66.0^\circ\text{E}$; Schiaparelli is at $13.8^\circ\text{E}$, separated by $\sim 3,100\text{ km}$) |
| `hirise-dtm-jezero` | $[+18.30^\circ, +18.55^\circ\text{N}]$ | $[77.35^\circ, 77.60^\circ\text{E}]$ | **YES** (100% inside `megt44n000hb`: Lat $[0^\circ, +44^\circ\text{N}]$, Lon $[0^\circ, 90^\circ\text{E}]$) | **NO** (Jezero is at $18.4^\circ\text{N}$; CTX DTM is at $4.6^\circ\text{S}$, separated by $\sim 1,360\text{ km}$) |

### 3.1 Geographic Overlap Findings:
1. **Schiaparelli Crater:** Located geographically inside the acquired southern MOLA tile `megt00n000hb`. When downloaded in a future phase, it can be compared directly against `megt00n000hb`.
2. **Jezero Delta:** With the acquisition of `megt44n000hb` in Phase 7, Jezero Crater ($+18.4^\circ\text{N}$) is now geographically inside acquired MOLA 128 coverage!
3. **CTX Swath Disjointness:** Neither HiRISE product overlaps the acquired CTX swath (`P21_009323_...`, Lat $-4.6^\circ$, Lon $66.3^\circ\text{E}$). The three datasets do not form a co-located 3-way stack at a single geographic point; they provide multi-resolution coverage samples across distinct Martian regions.

---

## 4. UI and API Safeguards

- In `MultiResolutionTerrainCatalog`, both HiRISE entries have `status: "catalogued"` and validation lifecycle state `discovered`.
- The frontend UI displays the HiRISE tier badge as **`Discovered`** (blue badge), never `Available` or `Downloaded`.
- The API endpoints `/compare-products` and `/routing/data-availability` correctly refuse to attempt raster sampling or routing on HiRISE footprints, returning explicit notices that raw rasters are not present locally.
