# MARS-X — Research Report: End-to-End Verification & Real Runtime Demonstration

## 1. Test Suite Execution & Metric Audit

Phase 8.1 implemented an end-to-end automated verification suite (`backend/tests/test_phase8_1_e2e.py`) validating both live HTTP endpoint operations and scientific correctness.

### 1.1 Full Test Suite Results
```bash
pytest backend/tests/ -v
====================== 166 passed, 2 warnings in 40.86s =======================
```
- Total test count expanded from 152 to **166 passing tests** with 100% test pass rate.
- Verified test modules:
  - `test_phase8_1_e2e.py` (14 new integration & calibration tests)
  - `test_phase8_intelligence.py` (Resolution selection, multiscale profiling, region comparison)
  - `test_phase7_1_audit.py` (PDS labels, raw checksums, CTX DTM geodetic properties)
  - `test_phase6_1_pathfinding.py` (A* vs Dijkstra optimality, benchmarks, corner cutting)
  - `test_phase5_1_calibration.py` (Hazard calibration decision table, separated coverage)
  - `test_mola_ingestion.py` (Real MOLA 128 ppd binary ingestion, COG conversion)
  - `test_terrain.py` & `test_terrain_api.py` (Geodesy, Horn slope, CRS rejection)

---

## 2. Live Runtime Daemon Verification

Both backend and frontend services run as stable background daemons:

### 2.1 Backend Daemon (`127.0.0.1:8000`)
- **Process:** `backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`
- **Health Verification:**
  ```json
  GET http://127.0.0.1:8000/health
  {"status": "ok", "app": "MARS-X", "version": "0.1.0"}
  ```
- **Service Verification:**
  ```json
  GET http://127.0.0.1:8000/api/v1/status
  {
    "status": "ok",
    "services": {
      "dataset_catalogue": "ok",
      "geospatial": "active",
      "terrain": "active_engine",
      "science": "ready"
    }
  }
  ```

### 2.2 Frontend Server (`127.0.0.1:3005`)
- **Process:** `next start -p 3005`
- **Asset Serving:** `http://127.0.0.1:3005/maplibre-gl-worker.mjs` returns HTTP 200 (519,547 bytes).
- **MapLibre Engine:** Initialized with standalone worker URL, rendering graticule lines and DTM footprint polygons.
- **Client Fetching:** Uses centralized `API_BASE = "http://127.0.0.1:8000"` with 8-second timeout protection.
