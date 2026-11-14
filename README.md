# 🔴 MARS-X

**Interplanetary Exploration, Mars Terrain Intelligence and Astronaut Marswalk Planning Platform**

> Built for [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/)

MARS-X is an open-source platform for visualising Mars terrain, planning astronaut surface traverses (marswalks), and analysing scientific datasets from NASA and ESA Mars missions. It combines a high-performance web map interface with a catalogue of real planetary science datasets to support exploration planning and research.

---

## 🛰️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15 · TypeScript · Tailwind CSS · MapLibre GL JS |
| **Backend** | FastAPI · Python 3.12 · Pydantic · Uvicorn |
| **Geospatial** | Rasterio · NumPy · COG pipeline · Multi-Resolution DTM Engine |
| **Data** | NASA PDS · MOLA MEGDR 4 & 128 ppd · ESA PSA HRSC · USGS CTX · HiRISE |
| **Hazard Analysis** | Horn Gradient · Metric Relief · Local Roughness · Scarp Detection |
| **Pathfinding** | A* (Euclidean lower bound) · Dijkstra baseline · Mars terrain cost surface |

---

## 📂 Project Structure

```
MARS-X/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── config.py       # Environment-based configuration
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── models/         # Pydantic request/response models
│   │   ├── routers/        # API route handlers
│   │   ├── services/       # Business logic & dataset catalogue
│   │   └── data/           # Static data files (NASA datasets JSON)
│   ├── tests/              # pytest test suite
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/     # React components
│   │   ├── lib/            # Utility functions & API client
│   │   └── types/          # TypeScript type definitions
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── data/                   # Data assets & metadata
│   ├── metadata/           # Dataset schema & reference JSON
│   ├── raw/                # Raw downloaded data (git-ignored)
│   ├── processed/          # Processed data products (git-ignored)
│   └── cache/              # Temporary cache (git-ignored)
├── docs/                   # Project documentation
│   ├── architecture/       # System architecture docs
│   ├── api/                # API endpoint documentation
│   └── research/           # CRS notes, dataset catalogue docs
├── scripts/                # Automation scripts
│   ├── setup.ps1           # Windows PowerShell setup script
│   └── validate_metadata.py
└── .gitignore
```

---

## 🚀 Quick Start (Windows PowerShell)

### Prerequisites

- **Python 3.12+** — install from [python.org](https://www.python.org/) (ensure `py` launcher is available)
- **Node.js 18+** — install from [nodejs.org](https://nodejs.org/)

### Automated Setup

```powershell
.\scripts\setup.ps1
```

### Manual Setup

**Backend** (Terminal 1):

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

**Frontend** (Terminal 2):

```powershell
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:3010`.

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Welcome message with API links |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/status` | Detailed status (version, uptime, services) |
| `GET` | `/api/v1/datasets` | Dataset catalogue (supports `?mission=` filter) |
| `GET` | `/api/v1/science/resolution-selection` | Resolution-aware dataset selector based on scale & availability |
| `GET` | `/api/v1/science/terrain-profile` | Scale-aware topographic profiler (slope, roughness, relief) |
| `GET` | `/api/v1/science/transition-compatibility` | Cross-resolution boundary compatibility & spatial partitioning |
| `GET` | `/api/v1/science/region-assessment` | Single-region terrain intelligence with data confidence scoring |
| `GET` | `/api/v1/science/region-comparison` | Multi-region comparative geomorphological contrast at equal scales |
| `GET` | `/api/v1/routing/terrain-source` | Route corridor elevation source & gap identification |


Full API documentation: [docs/api/endpoints.md](docs/api/endpoints.md)

---

## 🗃️ Dataset Catalogue

MARS-X registers metadata for **11 real NASA/USGS Mars datasets** across orbital and surface missions:

| # | Dataset | Mission | Resolution |
|---|---|---|---|
| 1 | MOLA Topography | Mars Global Surveyor | ~463 m/px |
| 2 | HRSC DTMs | Mars Express | 50–100 m/px |
| 3 | USGS Geologic Map (SIM 3292) | Multi-mission | 1:20M scale |
| 4 | HiRISE Imagery | MRO | 0.25–0.5 m/px |
| 5 | CTX Imagery | MRO | ~6 m/px |
| 6 | CRISM Spectroscopy | MRO | 15–18 m/px |
| 7 | THEMIS IR Mosaic | Mars Odyssey | 100 m/px (IR) |
| 8 | RAD Radiation Data | MSL/Curiosity | In-situ |
| 9 | REMS Weather Data | MSL/Curiosity | In-situ |
| 10 | Curiosity Surface Imagery | MSL | Variable |
| 11 | Perseverance Surface Imagery | Mars 2020 | Variable |

All datasets have `processing_status: "registered"` — metadata is catalogued but raw data has not yet been downloaded or processed. See [docs/research/dataset_catalogue.md](docs/research/dataset_catalogue.md) for details.

---

## 🌐 Coordinate Reference System

> [!IMPORTANT]
> Mars is not Earth. All geospatial data in MARS-X uses **EPSG:104905** (IAU 2000 Mars), not Web Mercator (EPSG:3857).

NASA Mars Trek WMTS tile services use EPSG:104905 (areocentric coordinates on a Mars spheroid). MapLibre GL JS only natively supports EPSG:3857, so Mars-specific CRS handling is required. See [docs/research/crs_projection_notes.md](docs/research/crs_projection_notes.md) for technical details.

---

## 📊 Current Status

**Phase: Phase 8 (Resolution-Aware Terrain Intelligence & Adaptive Mission Planning)** 🧭🔴

- [x] Project scaffolding and directory structure
- [x] Backend API with FastAPI (health, status, dataset catalogue)
- [x] Dataset metadata schema and validation
- [x] 11 NASA/USGS datasets registered with real metadata
- [x] Frontend application with Next.js, Tailwind, and dark theme
- [x] Mars map component with MapLibre GL JS
- [x] Authentic MOLA MEGDR 128 ppd tile ingestion (`megt00n000hb.img`)
- [x] Multi-resolution terrain catalog and hazard intelligence engine
- [x] Terrain-constrained A* and Dijkstra pathfinding engine
- [x] Rigorous A* heuristic admissibility & consistency verification on Mars sphere
- [x] Multi-corridor benchmark calibration and 100% path feasibility validation
- [x] Expanded MOLA 128 ppd regional coverage (3 authentic tiles, 26.05% of Mars sphere)
- [x] Acquired authentic USGS Controlled MRO CTX numerical DTM (20.01 m/px, 100% inside MOLA tile)
- [x] Catalogued local meter-scale HiRISE DTM with strict datum tie
- [x] Independent bit-for-bit SHA-256 verification of all MOLA and CTX source files
- [x] Discrepancy resolution for CTX overlap area ($2,410.1\text{ km}^2$ spherical bbox; $1,714.8\text{ km}^2$ valid data)
- [x] Formal geodetic sign convention ($\Delta z = z_{\text{CTX}} - z_{\text{MOLA}} = -57.57\text{ m}$)
- [x] Dual-support sampling audit: Point sampling ($N = 184$) and MOLA cell aggregation ($N = 1,877$)
- [x] Zero-median boundary continuity verified across MOLA tile seams (0.0 m median)
- [x] Resolution-Aware Data Selection Engine (`resolution_selector.py`) with zero-fabrication lifecycle guards
- [x] Multi-Scale Topographic Profiler (`multiscale_analysis.py`) converting physical windows (metres) to odd pixel kernels
- [x] O(1) Integral-image uniform box filtering for local roughness and relief
- [x] Multi-Resolution Transition Intelligence & Hierarchical Spatial Partitioning (`resolution_transition.py`)
- [x] Planetary Terrain Intelligence & Region Comparison Engine (`terrain_intelligence.py`) with explainable confidence scoring
- [x] Adaptive Route Corridor Source Selection & Gap Detection in `route_service.py`
- [x] Next.js Mission Control Terrain Intelligence Panel with 5 interactive analysis views
- [x] 152 comprehensive backend tests passed with zero regressions


---

## 📄 License

*License to be determined.*

---

<p align="center">
  <em>Built with 🔴 for Mars exploration</em>
</p>
