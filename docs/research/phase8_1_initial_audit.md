# Phase 8.1: Safe Initial Repository & Runtime Audit

**Author:** Senior Full-Stack Systems Engineer & Planetary Geospatial Scientist  
**Date:** 2026-11-14  
**Project:** MARS-X — Planetary Terrain Intelligence Platform  
**Phase:** 8.1 — Runtime Integration, End-to-End Verification & Scientific Calibration  
**Baseline Commit:** `30e0b1af69a4405fffd86a01ac9bbb5054ffcac6`  
**Git Branch:** `master`  
**Working Tree Status:** Clean  

---

## 1. Executive Summary

An exhaustive runtime and scientific audit of the MARS-X repository was performed prior to executing Stage 1-11 stabilization. While all 152 backend unit tests pass and the Next.js production build succeeds with zero TypeScript errors, critical runtime obstacles and scientific calibrations were identified:

1. **Backend Daemon Status:** The FastAPI backend was not actively running in the background, causing `API OFFLINE`, `Failed to fetch`, and `0 Registered Sources` on the frontend console. Port 8000 is completely unoccupied and available.
2. **MapLibre Web Worker Failure:** MapLibre GL JS v6.18.0 attempted to spawn Web Workers without an explicit worker URL configuration, triggering `Worker failed to load. Check that the worker URL is correct.` when bundled by Next.js Turbopack. Static assets in `frontend/public/` lacked `maplibre-gl-worker.mjs`.
3. **Empty Mars Map Canvas:** `MapContainer.tsx` initialized a dark `#0d0e17` background without raster hillshading, planetary graticule lines, or dataset footprint polygons.
4. **Scale Calibration Discrepancy (Scientific Correction A):** For MOLA 128 ppd ($463.08\text{ m/px}$), requesting a $500\text{ m}$ window produces a $3 \times 3$ pixel kernel, yielding an effective physical spatial window of $1,389.24\text{ m}$ in latitude and $1,389.24 \times \cos(\phi)\text{ m}$ in longitude. Presenting this as an exact $500\text{ m}$ scale violates remote sensing sampling theory.
5. **Geographic Identity Misattribution (Scientific Correction B):** The USGS CTX DTM (`P21_009323_...`) footprint is located at Lat $[-5.19^\circ, -4.00^\circ\text{N}]$, Lon $[66.04^\circ, 66.62^\circ\text{E}]$ ($293.5^\circ\text{W}$). In Phase 8, this was colloquially labeled "Melas Chasma". Real Melas Chasma is located in Valles Marineris at $9.8^\circ\text{S}, 283.6^\circ\text{E}$ ($76.4^\circ\text{W}$). The true geographic feature at $66^\circ\text{E}, 4^\circ\text{S}$ is in **Tyrrhena Terra / Hesperia margin**.
6. **Data Quality Index Semantics (Scientific Correction C):** The score $100 \times (0.45 C + 0.35 S + 0.20 D)$ was presented without clear qualification as a heuristic index, risking misinterpretation as an empirical mission success probability.
7. **Route Corridor Coverage Semantics:** Centerline coverage, buffered corridor envelope, and bounding box coverage were conflated.

---

## 2. Runtime Environment & Startup Configuration Audit

### Backend Runtime
- **Python Version:** 3.12.6
- **Virtual Environment:** `backend\.venv`
- **Application Entry Point:** `app.main:app` (FastAPI)
- **Target Host & Port:** `127.0.0.1:8000` (or `0.0.0.0:8000`)
- **CORS Allowed Origins:** Explicitly permits `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:3005`, `http://127.0.0.1:3005`, `http://localhost:3001`, `http://127.0.0.1:3001`, `http://localhost:4000`. No wildcard `*` with credentials.
- **Port Availability:** Confirmed with `Get-NetTCPConnection` that port 8000 is completely free.

### Frontend Runtime
- **Next.js Version:** 16.4.6 (Turbopack enabled)
- **Framework:** React 19.3.0, TypeScript 5 (strict mode)
- **CSS Framework:** Tailwind CSS 4.3.3
- **Map Library:** `maplibre-gl` 6.18.0
- **API Base URL Configuration:** `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`

---

## 3. Physical Source Dataset & Checksum Verification

All physical raw elevation files in `data/raw/` were verified against authoritative SHA-256 hashes:

| Product File | Dimensions | Spacing | SHA-256 Checksum | Status |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/mola/megt00n000hb.img` | $5632 \times 11520$ | $463.08\text{ m}$ | `f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75` | Verified Intact |
| `data/raw/mola/megt44n000hb.img` | $5632 \times 11520$ | $463.08\text{ m}$ | `14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36` | Verified Intact |
| `data/raw/mola/megt00n090hb.img` | $5632 \times 11520$ | $463.08\text{ m}$ | `764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e` | Verified Intact |
| `data/raw/ctx/P21_009323_..._dtm.tif` | $3472 \times 1692$ | $20.01\text{ m}$ | `a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2` | Verified Intact |
| `data/raw/hirise/` | — | — | 0 bytes on disk | Strictly `discovered` |

---

## 4. Remediation Plan

1. **Stage 1:** Stabilize backend runtime; configure centralized API settings; launch FastAPI daemon on port 8000.
2. **Stage 2:** Copy `maplibre-gl-worker.mjs` to `frontend/public/`; set `setWorkerUrl('/maplibre-gl-worker.mjs')`; add planetary Mars graticule, coordinate grid, and dataset footprint overlays to `MapContainer.tsx`.
3. **Stage 3:** Ensure `DatasetCatalogue` displays 11 registered sources and live local DTM statuses.
4. **Stage 4:** Test all 10 REST endpoints with real HTTP requests.
5. **Stage 5:** Implement requested vs effective analysis scale calculations in `multiscale_analysis.py` and `terrain_intelligence.py`.
6. **Stage 6:** Correct geographic identity of `P21_009323` to **Tyrrhena Terra (East-Hesperia Region)**.
7. **Stage 7:** Refactor score terminology to **Heuristic Data Quality Index** with explicit component weights.
8. **Stage 8:** Implement multi-tier corridor coverage validation (centerline, buffered corridor, bounding box).
9. **Stage 9:** Test and refine the running dashboard UI.
10. **Stage 10 & 11:** Execute automated E2E tests and live browser demonstration.
