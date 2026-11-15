"""MARS-X API — FastAPI application entry point."""

import sys
import asyncio
import logging

if sys.platform == "win32":
    # Prevent Windows IOCP Proactor socket reset crash (WinError 64 / 10054 on accept)
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS
from app.routers import health as health_router
from app.routers import datasets as datasets_router
from app.routers import terrain as terrain_router
from app.routers import routing as routing_router
from app.routers import science as science_router
from app.routers import geology as geology_router
from app.routers import thermal as thermal_router
from app.routers import themis as themis_router
from app.routers import discovery as discovery_router
from app.routers import traversability as traversability_router
from app.routers import marswalk as marswalk_router
from app.routers import environmental as environmental_router
from app.routers import climatology as climatology_router


# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(APP_NAME)

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MARS-X API",
    description=(
        "Backend API for the MARS-X project — Mars Analysis, Research & "
        "Site-selection eXplorer. Provides dataset catalogue endpoints, "
        "terrain data engine services, and planetary geodesy verification."
    ),
    version=VERSION,
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router.router)
app.include_router(health_router._status_router)
app.include_router(datasets_router.router)
app.include_router(terrain_router.router)
app.include_router(routing_router.router)
app.include_router(routing_router.routing_alias_router)
app.include_router(science_router.router)
app.include_router(geology_router.router)
app.include_router(thermal_router.router)
app.include_router(themis_router.router)
app.include_router(discovery_router.router)
app.include_router(traversability_router.router)
app.include_router(marswalk_router.router)
app.include_router(environmental_router.router)
app.include_router(climatology_router.router)



# ── Root ───────────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    """Welcome endpoint with navigation links."""
    return {
        "message": f"Welcome to {APP_NAME} API v{VERSION}",
        "docs": "/docs",
        "health": "/health",
        "status": f"{API_V1_PREFIX}/status",
        "datasets": f"{API_V1_PREFIX}/datasets",
        "terrain": {
            "datasets": f"{API_V1_PREFIX}/terrain/datasets",
            "metadata": f"{API_V1_PREFIX}/terrain/metadata",
            "coverage": f"{API_V1_PREFIX}/terrain/coverage",
            "summary": f"{API_V1_PREFIX}/terrain/summary",
        },
    }


logger.info("MARS-X API initialised (v%s)", VERSION)
