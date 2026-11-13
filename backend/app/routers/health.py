"""Health and status router."""

import time

from fastapi import APIRouter

from app.config import APP_NAME, VERSION, API_V1_PREFIX
from app.models.health import HealthResponse, StatusResponse

router = APIRouter()

_start_time = time.time()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    """Basic liveness check."""
    return HealthResponse(app=APP_NAME, version=VERSION)


_status_router = APIRouter(prefix=API_V1_PREFIX)


@_status_router.get("/status", response_model=StatusResponse, tags=["health"])
async def status():
    """Detailed status including uptime and service readiness."""
    return StatusResponse(
        app=APP_NAME,
        version=VERSION,
        uptime_seconds=round(time.time() - _start_time, 2),
        services={
            "dataset_catalogue": "ok",
            "geospatial": "active",
            "terrain": "active_engine",
            "routing": "pending_engine",
            "science": "ready",
            "mission": "ready",
            "ai": "foundation_stub",
        },
    )
