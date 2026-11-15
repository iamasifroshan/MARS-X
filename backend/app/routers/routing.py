"""FastAPI Router for Mars Route Planning and Traverses."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path

from app.config import API_V1_PREFIX
from app.routing.route_models import (
    RoutePlanRequest,
    RoutePlanResponse,
    RouteComparisonResponse,
)
from app.routing.route_service import MarsRouteService
from app.routing.grid_builder import (
    MOLA_128_LAT_MIN,
    MOLA_128_LAT_MAX,
    MOLA_128_LON_MIN,
    MOLA_128_LON_MAX,
)

router = APIRouter(prefix=f"{API_V1_PREFIX}/routes", tags=["routing"])

# Instantiate service with authentic MOLA 128 raster
try:
    route_service = MarsRouteService()
except Exception:
    route_service = None  # Handled inside endpoints if missing


@router.get("/metadata")
def get_routing_metadata() -> Dict[str, Any]:
    """Retrieve capabilities, constraints, and valid footprints for Mars route planning."""
    return {
        "supported_datasets": [
            {
                "dataset_id": "mola-megdr-128",
                "instrument": "MOLA",
                "pixel_spacing_m": 463.08,
                "coverage_footprint": f"Lat [{MOLA_128_LAT_MIN}°, {MOLA_128_LAT_MAX}°], Lon [{MOLA_128_LON_MIN}°, {MOLA_128_LON_MAX}°E]",
                "validation_status": "scientifically_validated",
                "is_analysis_ready": True,
            }
        ],
        "supported_algorithms": ["astar", "dijkstra"],
        "supported_connectivity": [4, 8],
        "default_constraints": {
            "max_slope_deg": 15.0,
            "max_snapping_distance_m": 2000.0,
            "max_search_nodes": 150000,
        },
        "cost_model": "C = L * (1 + ws*fs + wr*fr + wl*fl + wc*fc)",
        "scientific_limitations": [
            "463 m/px grid resolution cannot detect meter-scale rover boulders or crevasses (Nyquist scale ~1.15 km).",
            "Route planning is strictly limited to the validated MOLA 128 tile footprint (Lat [-44°, 0°], Lon [0°, 90°E]).",
            "Paths represent mathematical terrain-cost optimizations; not an astronaut safety or EVA guarantee.",
        ],
    }


@router.post("/plan", response_model=RoutePlanResponse)
def plan_route(request: RoutePlanRequest) -> RoutePlanResponse:
    """Plan a single terrain-constrained Marswalk traverse using A* or Dijkstra."""
    if route_service is None:
        raise HTTPException(
            status_code=503,
            detail="Mars route service is unavailable. Required MOLA 128 raster file not found.",
        )
    try:
        return route_service.plan_single_route(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))


@router.post("/compare", response_model=RouteComparisonResponse)
def compare_route_algorithms(request: RoutePlanRequest) -> RouteComparisonResponse:
    """Run both A* and Dijkstra on identical mission parameters and return side-by-side metrics."""
    if route_service is None:
        raise HTTPException(
            status_code=503,
            detail="Mars route service is unavailable. Required MOLA 128 raster file not found.",
        )
    try:
        return route_service.compare_algorithms(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))


@router.get("/data-availability")
def check_route_data_availability(
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="Minimum latitude in degrees (-90 to 90)"),
    min_lon: float = Query(..., ge=0.0, le=360.0, description="Minimum longitude in degrees (0 to 360)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="Maximum latitude in degrees (-90 to 90)"),
    max_lon: float = Query(..., ge=0.0, le=360.0, description="Maximum longitude in degrees (0 to 360)"),
) -> Dict[str, Any]:
    """Check availability of multi-resolution elevation datasets for a candidate route bounding box."""
    if route_service is None:
        raise HTTPException(
            status_code=503,
            detail="Mars route service is unavailable. Required MOLA 128 raster file not found.",
        )
    try:
        return route_service.check_data_availability(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/terrain-source")
def get_corridor_terrain_source(
    start_lat: float = Query(..., ge=-90.0, le=90.0, description="Start latitude in degrees"),
    start_lon: float = Query(..., ge=0.0, le=360.0, description="Start longitude in degrees"),
    dest_lat: float = Query(..., ge=-90.0, le=90.0, description="Destination latitude in degrees"),
    dest_lon: float = Query(..., ge=0.0, le=360.0, description="Destination longitude in degrees"),
    target_scale_m: Optional[float] = Query(default=None, ge=1.0, description="Optional target analysis scale in metres"),
) -> Dict[str, Any]:
    """Identify the terrain dataset supporting a proposed route corridor."""
    if route_service is None:
        raise HTTPException(
            status_code=503,
            detail="Mars route service is unavailable. Required MOLA 128 raster file not found.",
        )
    try:
        return route_service.evaluate_corridor_terrain_source(
            start_lat=start_lat,
            start_lon=start_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            target_scale_m=target_scale_m,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Also expose under /api/v1/routing for routing-convention consistency
routing_alias_router = APIRouter(prefix=f"{API_V1_PREFIX}/routing", tags=["routing"])

@routing_alias_router.get("/data-availability")
def check_routing_data_availability_alias(
    min_lat: float = Query(..., ge=-90.0, le=90.0),
    min_lon: float = Query(..., ge=0.0, le=360.0),
    max_lat: float = Query(..., ge=-90.0, le=90.0),
    max_lon: float = Query(..., ge=0.0, le=360.0),
) -> Dict[str, Any]:
    """Alias for /api/v1/routes/data-availability."""
    return check_route_data_availability(min_lat, min_lon, max_lat, max_lon)


@routing_alias_router.get("/terrain-source")
def get_routing_terrain_source_alias(
    start_lat: float = Query(..., ge=-90.0, le=90.0),
    start_lon: float = Query(..., ge=0.0, le=360.0),
    dest_lat: float = Query(..., ge=-90.0, le=90.0),
    dest_lon: float = Query(..., ge=0.0, le=360.0),
    target_scale_m: Optional[float] = Query(default=None, ge=1.0),
) -> Dict[str, Any]:
    """Alias for /api/v1/routes/terrain-source."""
    return get_corridor_terrain_source(start_lat, start_lon, dest_lat, dest_lon, target_scale_m)


