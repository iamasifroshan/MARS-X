# MARS-X — Phase 7.1 Research: API Endpoints & Frontend Presentation Audit

## 1. Audit Scope

This audit evaluates every multi-resolution API endpoint in FastAPI and every user-facing presentation element in the Next.js frontend to ensure that data availability, coverage statistics, resolution ratios, and error behaviors conform to verified ground-truth raster availability.

---

## 2. API Endpoint Verification Matrix

| Endpoint | Method | Input Parameters Tested | Returned Output Structure | Verified Correctness |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/terrain/products` | `GET` | None | `{ total_products, available_locally_count, analysis_ready_count, products: [...] }` | Correctly reports 3 products available locally on disk (`mola-megdr-4`, `mola-megdr-128`, `ctx-dtm-p21-009323`). |
| `/api/v1/terrain/coverage/region` | `GET` | `min_lat=-5.5, min_lon=65.5, max_lat=-3.8, max_lon=67.0` | `{ query_bounds, matching_products_count, finest_native_resolution_m, available_tiers, products }` | Correctly returns CTX (20.01m), MOLA 128 (463.08m), and MOLA 4 (14.8km). |
| `/api/v1/terrain/resolution-stack` | `GET` | `lat=-4.5, lon=66.3` | `{ coordinate, tiers_count, finest_pixel_spacing_m, stack: [...] }` | Correctly orders tiers finest to coarsest: CTX ➔ MOLA 128 ➔ MOLA 4. |
| `/api/v1/terrain/overlap` | `GET` | `product_a=mola-megdr-128, product_b=ctx-dtm-p21-009323` | `ProductOverlapResult` | Correctly returns `has_overlap=True`, `overlap_area_km2=2410.1`, `both_locally_available=True`. |
| `/api/v1/terrain/compare-products` | `GET` | `product_a=mola-megdr-128, product_b=ctx-dtm-p21-009323, sample_points=100` | Flat & nested comparative metrics | Correctly extracts real pixels and returns mean elevation, mean delta, std dev, and scientific explanation. |
| `/api/v1/terrain/quality` | `GET` | `product_id=ctx-dtm-p21-009323` | `ProductValidationReport` | Correctly returns lifecycle state `analysis_ready`, checksum, and validation checks. |
| `/api/v1/routing/data-availability` | `GET` | `min_lat=-5.0, min_lon=65.0, max_lat=-4.0, max_lon=67.0` | `{ bounding_box, routing_eligible, available_tiers, highest_available_resolution_m, ... }` | Correctly reports `routing_eligible=True` inside validated MOLA footprint, with CTX high-res advisory. |

---

## 3. Discovered Defects & Implemented Corrections

1. **Defect 1: Area Label Ambiguity in UI/Docs:**
   - *Finding:* Previous documentation stated `~3,889.3 km²` for CTX overlap, whereas the API returned `2,410.1 km²` and the valid pixel grid covered `1,714.8 km²`.
   - *Correction:* Updated frontend and research documentation to explicitly distinguish between the **Spherical Bounding Box Overlap ($2,410.1\text{ km}^2$)** and the **Valid Stereo DTM Area ($1,714.8\text{ km}^2$)**.

2. **Defect 2: Delta Sign Inversion in Documentation:**
   - *Finding:* Text previously stated $\mu_{\Delta z} = \text{MOLA} - \text{CTX} = -45.58\text{ m}$, whereas the underlying calculation is $z_{\text{CTX}} - z_{\text{MOLA}} = -57.57\text{ m}$.
   - *Correction:* Formally established standard geodetic convention $\Delta z = z_{\text{CTX}} - z_{\text{MOLA}}$ across all documentation, API responses, and UI tooltips.

3. **Defect 3: HiRISE Availability Labeling:**
   - *Finding:* In some earlier mockups, HiRISE was colloquially marked as "available".
   - *Correction:* Verified that the frontend strictly displays HiRISE as **`Discovered`** (blue badge), reflecting that only PDS metadata is registered, with zero local raster bytes.

4. **Defect 4: CORS Configuration for Alternative Ports:**
   - *Finding:* Default CORS in `backend/app/config.py` was hardcoded to `http://localhost:3000`, blocking API calls when the frontend was hosted on custom ports (e.g. 3005, 3001, 4000).
   - *Correction:* Expanded `CORS_ORIGINS` to permit common alternative ports (`http://localhost:3005`, `http://127.0.0.1:3005`, etc.).
