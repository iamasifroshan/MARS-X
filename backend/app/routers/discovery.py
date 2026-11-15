"""FastAPI Router for MARS-X Science Discovery Engine.

Endpoints for:
- Discovery categories and candidate catalog
- Viewport and category filtering
- Science opportunity profiles for any Mars coordinate
- Geodesic Mars spherical nearby queries
- Multi-location scientific comparisons
"""

import logging
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import API_V1_PREFIX
from app.science.discovery_service import get_discovery_service

logger = logging.getLogger("MARS-X.routers.discovery")

router = APIRouter(prefix=f"{API_V1_PREFIX}/discovery", tags=["discovery"])


class CompareRequest(BaseModel):
    locations: List[Union[str, Dict[str, Any]]] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of discovery IDs (e.g. 'disc-terr-tyrrhena-ctx'), coordinate strings (e.g. '-4.6,66.317'), or location dicts {'lat': float, 'lon': float, 'label': str}",
    )


@router.get("/categories")
def get_discovery_categories() -> List[Dict[str, Any]]:
    """Retrieve available science discovery categories with metadata and discovery counts."""
    service = get_discovery_service()
    return service.get_categories()


@router.get("/list")
def get_discoveries(
    category: Optional[str] = Query(default=None, description="Optional category filter"),
    min_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="South boundary latitude"),
    max_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="North boundary latitude"),
    min_lon: Optional[float] = Query(default=None, description="West boundary longitude"),
    max_lon: Optional[float] = Query(default=None, description="East boundary longitude"),
    search: Optional[str] = Query(default=None, description="Text search across title and scientific description"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum discoveries to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> Dict[str, Any]:
    """Retrieve candidate science discoveries filtered by category, geographic bounding box, or search query."""
    if min_lat is not None and max_lat is not None and min_lat > max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) cannot exceed max_lat ({max_lat})")

    service = get_discovery_service()
    return service.get_discoveries(
        category=category,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/profile")
def get_science_profile(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (-90° to +90°)"),
    lon: float = Query(..., description="Longitude (0° to 360° or -180° to +180°)"),
    radius_km: float = Query(default=500.0, ge=10.0, le=2500.0, description="Search radius for nearby features in km"),
) -> Dict[str, Any]:
    """Generate a comprehensive science opportunity profile for any coordinate on Mars.

    Combines co-registered elevation, USGS SIM 3292 geology, MGS TES thermal inertia,
    THEMIS 256 ppd IR mosaic availability, nearest structural lines, contacts, and
    dynamically formulated investigation opportunities.
    """
    service = get_discovery_service()
    try:
        return service.get_science_profile(lat=lat, lon=lon, radius_km=radius_km)
    except Exception as e:
        logger.error("Failed to generate science profile for lat=%s, lon=%s: %s", lat, lon, e)
        raise HTTPException(status_code=500, detail=f"Science profile generation failed: {e}")


@router.get("/nearby")
def get_nearby_discoveries(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Origin latitude (-90° to +90°)"),
    lon: float = Query(..., description="Origin longitude (0° to 360° or -180° to +180°)"),
    radius_km: float = Query(default=1500.0, ge=50.0, le=5000.0, description="Search radius in km on Mars sphere"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum discoveries to return"),
) -> List[Dict[str, Any]]:
    """Query science discoveries sorted by geodesic Mars spherical distance from origin coordinate."""
    service = get_discovery_service()
    return service.get_nearby_discoveries(lat=lat, lon=lon, radius_km=radius_km, limit=limit)


@router.get("/{discovery_id}")
def get_discovery_by_id(discovery_id: str) -> Dict[str, Any]:
    """Retrieve details for a specific science discovery enriched with live co-registered measurements."""
    service = get_discovery_service()
    discovery = service.get_discovery_by_id(discovery_id)
    if not discovery:
        raise HTTPException(status_code=404, detail=f"Discovery '{discovery_id}' not found.")
    return discovery


@router.post("/compare")
def compare_science_locations(body: CompareRequest) -> Dict[str, Any]:
    """Compare up to 5 science locations side-by-side using integrated Mars datasets."""
    service = get_discovery_service()
    return service.compare_locations(body.locations)
