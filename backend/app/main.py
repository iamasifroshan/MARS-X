"""MARS-X API — FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS
from app.routers import health as health_router
from app.routers import datasets as datasets_router

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
        "Site-selection eXplorer. Provides dataset catalogue endpoints and "
        "health/status checks for the Martian geospatial data pipeline."
    ),
    version=VERSION,
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router.router)
app.include_router(health_router._status_router)
app.include_router(datasets_router.router)


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
    }


logger.info("MARS-X API initialised (v%s)", VERSION)
