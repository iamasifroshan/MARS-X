"""FastAPI Router for Marswalk Route Planning — Phase 8.8.2.

Provides endpoints for terrain-aware route computation, cached route retrieval,
and engine metadata with mandatory safety disclaimers.
"""

from fastapi import APIRouter, HTTPException, Path, status
from app.config import API_V1_PREFIX
from app.marswalk.marswalk_models import (
    MarswalkRouteRequest,
    MarswalkRouteResponse,
    MarswalkMetadataResponse,
)
from app.marswalk.marswalk_planner import (
    MarswalkPlanner,
    get_cached_route,
)

router = APIRouter(
    prefix=f"{API_V1_PREFIX}/marswalk",
    tags=["marswalk"],
)


@router.post(
    "/route",
    response_model=MarswalkRouteResponse,
    summary="Generate terrain-aware Marswalk route",
    description=(
        "Computes an optimal path between start and destination coordinates using A* pathfinding "
        "over authentic Mars DEMs. Evaluates 3D surface metric distance, Horn slope gradients, "
        "quadratic slope penalties, and enforces diagonal corner-cutting prevention. "
        "WARNING: Minimizing terrain cost does NOT certify astronaut or rover safety."
    ),
    responses={
        200: {"description": "Route successfully planned."},
        400: {"description": "Invalid coordinates or requested source does not cover waypoints."},
        404: {"description": "Required elevation or slope raster not found on disk."},
        422: {"description": "No traversable path exists within max slope threshold or bounds."},
        504: {"description": "Search exceeded maximum node expansion limit."},
    },
)
async def generate_route(request: MarswalkRouteRequest) -> MarswalkRouteResponse:
    try:
        return MarswalkPlanner.plan_route(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal routing engine error: {str(e)}",
        )


@router.get(
    "/route/{route_id}",
    response_model=MarswalkRouteResponse,
    summary="Retrieve previously planned Marswalk route",
    description="Fetches full geometry, profile telemetry, and exposure metrics for a cached route by ID.",
    responses={
        200: {"description": "Cached route found and returned."},
        404: {"description": "Route ID not found in cache or expired."},
    },
)
async def get_route(
    route_id: str = Path(..., description="Unique route identifier, e.g. mw-a1b2c3d4e5f6"),
) -> MarswalkRouteResponse:
    route = get_cached_route(route_id)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found in cache or expired. Please re-run pathfinding.",
        )
    return route


@router.get(
    "/metadata",
    response_model=MarswalkMetadataResponse,
    summary="Get Marswalk engine metadata and capabilities",
    description=(
        "Returns supported DEM datasets, native resolutions, vertical datums, "
        "cost function formulation, analytical slope thresholds, and curated corridor presets."
    ),
)
async def get_metadata() -> MarswalkMetadataResponse:
    return MarswalkPlanner.get_metadata()
