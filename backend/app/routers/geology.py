"""FastAPI Router for USGS Mars Global Geologic Map (SIM 3292)."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path

from app.config import API_V1_PREFIX
from app.science.geology_service import get_geology_service, SIM3292GeologyService

logger = logging.getLogger("MARS-X.routers.geology")

router = APIRouter(prefix=f"{API_V1_PREFIX}/geology", tags=["geology"])


@router.get("/metadata")
def get_geology_metadata() -> Dict[str, Any]:
    """Retrieve official USGS SIM 3292 Geological Map metadata, feature counts, and CRS."""
    service = get_geology_service()
    return service.get_metadata()


@router.get("/legend")
def get_geology_legend() -> List[Dict[str, Any]]:
    """Retrieve chronostratigraphic legend and color designations for all 44 recognized Martian geological units."""
    service = get_geology_service()
    return service.get_legend()


@router.get("/units/{unit_code}")
def get_geology_unit_details(
    unit_code: str = Path(..., description="USGS unit code (e.g., 'mAl', 'lNl', 'AHv', 'lNh')")
) -> Dict[str, Any]:
    """Retrieve detailed scientific description, epoch, and dominant lithology for a specific unit code."""
    service = get_geology_service()
    unit = service.get_unit_details(unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail=f"Geological unit '{unit_code}' not found in SIM 3292 database.")
    return unit


@router.get("/point")
def query_geology_at_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90° to +90°)"),
    lon: float = Query(..., description="Longitude (0° to 360° or -180° to +180°)"),
) -> Dict[str, Any]:
    """Query the USGS SIM 3292 geological unit and stratigraphy at a specific Martian latitude/longitude."""
    service = get_geology_service()
    res = service.query_point(lat, lon)
    if not res:
        return {
            "latitude": lat,
            "longitude": lon,
            "unit": "None",
            "unit_name": "Unclassified or outside mapped geological domain",
            "chronostratigraphic_period": "Undivided",
            "source_product": "USGS SIM 3292 (Tanaka et al. 2014)",
            "crs": "GCS_Mars_2000_Sphere (R=3,396,190 m)",
        }
    return res


@router.get("/viewport")
def query_geology_viewport(
    min_lon: float = Query(..., description="Minimum longitude (-180° to 180° or 0° to 360°)"),
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="Minimum latitude (-90° to 90°)"),
    max_lon: float = Query(..., description="Maximum longitude (-180° to 180° or 0° to 360°)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="Maximum latitude (-90° to 90°)"),
    layer: str = Query(
        default="geology",
        pattern="^(geology|polygons|contacts|structure|landing_sites)$",
        description="Geological layer ('geology'/'polygons', 'contacts', 'structure', 'landing_sites')",
    ),
    limit: int = Query(default=200, ge=1, le=1000, description="Maximum number of features to return"),
) -> Dict[str, Any]:
    """Query USGS SIM 3292 geological features intersecting a bounding box as a GeoJSON FeatureCollection."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) cannot exceed max_lat ({max_lat})")

    # Map alias 'polygons' -> 'geology'
    internal_layer = "geology" if layer == "polygons" else layer

    service = get_geology_service()
    return service.query_viewport(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        layer=internal_layer,
        limit=limit,
    )
