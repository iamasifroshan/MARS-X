"""FastAPI Router for MGS TES Global Thermal Inertia (Putzig & Mellon 2007)."""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response

from app.config import API_V1_PREFIX
from app.science.thermal_service import get_thermal_service

logger = logging.getLogger("MARS-X.routers.thermal")

router = APIRouter(prefix=f"{API_V1_PREFIX}/thermal", tags=["thermal"])


@router.get("/metadata")
def get_thermal_metadata() -> Dict[str, Any]:
    """Retrieve MGS TES Thermal Inertia dataset metadata, coverage, units, and citation."""
    service = get_thermal_service()
    return service.get_metadata()


@router.get("/point")
def query_thermal_inertia_at_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90° to +90°)"),
    lon: float = Query(..., description="Longitude (0° to 360° or -180° to +180°)"),
    product: str = Query(
        default="dayside",
        pattern="^(dayside|nightside)$",
        description="Observation hemisphere ('dayside' or 'nightside')",
    ),
) -> Dict[str, Any]:
    """Query calibrated Martian thermal inertia (in tiu) at a specific latitude and longitude.

    IMPORTANT: Values are legend-calibrated estimates of Apparent Thermal Inertia (J m^-2 K^-1 s^-1/2),
    derived via 790-step reverse lookup of the Putzig & Mellon (2007) published color palette.
    They are NOT temperature or radiant heat.
    """
    service = get_thermal_service()
    try:
        return service.query_point(lat=lat, lon=lon, product=product)
    except Exception as e:
        logger.error("Thermal point query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/render/window")
def render_thermal_window(
    min_lon: float = Query(..., description="West boundary longitude (-180° to 180° or 0° to 360°)"),
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="South boundary latitude (-90° to 90°)"),
    max_lon: float = Query(..., description="East boundary longitude (-180° to 180° or 0° to 360°)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="North boundary latitude (-90° to 90°)"),
    product: str = Query(
        default="dayside",
        pattern="^(dayside|nightside)$",
        description="Observation product ('dayside' or 'nightside')",
    ),
    width: int = Query(default=256, ge=64, le=1024, description="Output image width in pixels"),
    height: int = Query(default=256, ge=64, le=1024, description="Output image height in pixels"),
):
    """Render a bounding box window of authentic MGS TES Thermal Inertia as an RGBA PNG."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) cannot exceed max_lat ({max_lat})")

    service = get_thermal_service()
    try:
        png_bytes = service.render_window(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            product=product,
            width=width,
            height=height,
        )
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        logger.error("Thermal window rendering failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
