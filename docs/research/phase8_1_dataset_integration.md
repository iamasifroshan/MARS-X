# MARS-X — Research Report: Multi-Resolution Dataset Lifecycle & Physical Ingestion

## 1. Multi-Resolution Elevation Inventory

MARS-X enforces a strict distinction between **catalogued remote products** and **locally ingested numerical rasters**. Only datasets with verified local file availability and cryptographic SHA-256 integrity checks may be evaluated by numerical terrain processors.

| Product ID | Instrument / Mission | Nominal Resolution | Physical Storage Path | SHA-256 Verified | Lifecycle Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mola-megdr-4` | MOLA / MGS | 14,818.67 m/px (4 ppd) | `data/raw/mola/megt90n000cb.img` | Authenticated | `ingested` |
| `mola-megdr-128-000hb` | MOLA / MGS | 463.08 m/px (128 ppd) | `data/raw/mola/megt00n000hb.img` | Authenticated | `ingested` |
| `mola-megdr-128-44nhb` | MOLA / MGS | 463.08 m/px (128 ppd) | `data/raw/mola/megt44n000hb.img` | Authenticated | `ingested` |
| `mola-megdr-128-090hb` | MOLA / MGS | 463.08 m/px (128 ppd) | `data/raw/mola/megt00n090hb.img` | Authenticated | `ingested` |
| `ctx-dtm-p21-009323` | CTX / MRO | 20.01 m/px post-spacing | `data/raw/ctx/P21_009323_..._dtm.tif` | Authenticated | `analysis_ready` |
| `hirise-dtm-schiaparelli` | HiRISE / MRO | 1.0 m/px | *(Remote NASA PDS archive)* | Remote | `discovered` |
| `hirise-dtm-jezero` | HiRISE / MRO | 1.0 m/px | *(Remote NASA PDS archive)* | Remote | `catalogued` |

---

## 2. Anti-Fabrication Safeguard

The Resolution Selection Engine (`backend/app/terrain/resolution_selector.py`) evaluates candidate datasets across four stages:
1. **Physical Availability Verification:** If `is_locally_available` is False or file path is absent from disk, the product is immediately disqualified with rejection stage `availability`.
2. **Footprint Envelope Intersection:** Overlap area must be positive and non-negligible.
3. **Scale Suitability Scoring:** Logarithmic penalty applied when native resolution deviates significantly from requested analysis scale.
4. **Horizontal / Vertical Datum Alignment:** Rejects incompatible datums unless mathematical transformations are documented.

Under no circumstances does MARS-X synthesize artificial elevation pixels or claim operational clearance for undiscovered products.
