"""FastAPI Router for Mars Route Planning and Traverses."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Path

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
async def get_routing_metadata() -> Dict[str, Any]:
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
async def plan_route(request: RoutePlanRequest) -> RoutePlanResponse:
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
async def compare_route_algorithms(request: RoutePlanRequest) -> RouteComparisonResponse:
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
