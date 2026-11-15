"""FastAPI Router for 2001 Mars Odyssey THEMIS Regional Infrared Mosaics (256 ppd)."""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response

from app.config import API_V1_PREFIX
from app.science.thermal_service import get_themis_service

logger = logging.getLogger("MARS-X.routers.themis")

router = APIRouter(prefix=f"{API_V1_PREFIX}/themis", tags=["themis"])


@router.get("/metadata")
def get_themis_metadata() -> Dict[str, Any]:
    """Retrieve THEMIS 256 ppd regional IR mosaic metadata, footprint, and qualitative semantics."""
    service = get_themis_service()
    return service.get_metadata()


@router.get("/render/window")
def render_themis_window(
    min_lon: float = Query(..., description="West boundary longitude (0° to 360° or -180° to 180°)"),
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="South boundary latitude (-90° to 90°)"),
    max_lon: float = Query(..., description="East boundary longitude (0° to 360° or -180° to 180°)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="North boundary latitude (-90° to 90°)"),
    mode: str = Query(
        default="day",
        pattern="^(day|night)$",
        description="Infrared mosaic mode ('day' or 'night')",
    ),
    width: int = Query(default=256, ge=64, le=1024, description="Output image width in pixels"),
    height: int = Query(default=256, ge=64, le=1024, description="Output image height in pixels"),
):
    """Render a bounding box window of authentic THEMIS 256 ppd regional infrared mosaic as an RGBA PNG."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) cannot exceed max_lat ({max_lat})")

    service = get_themis_service()
    try:
        png_bytes = service.render_window(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            mode=mode,
            width=width,
            height=height,
        )
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        logger.error("THEMIS window rendering failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/point")
@router.get("/temperature")
def query_themis_point_prohibited():
    """Explicitly reject quantitative point temperature queries on THEMIS visual mosaics."""
    raise HTTPException(
        status_code=400,
        detail=(
            "SCIENTIFIC PROHIBITION: Acquired THEMIS 100m infrared mosaics (thm_dir_N-30_000.png / "
            "themis_nightir_N-30_000.png) are qualitative 8-bit visual display mosaics (0-255 DN). "
            "They undergo contrast stretching and track-feathering; conversion to calibrated kinetic temperature (K) "
            "or radiance is scientifically unsupported and invalid. For quantitative thermophysical analysis, "
            "use the MGS TES Thermal Inertia service at /api/v1/thermal/point."
        ),
    )
