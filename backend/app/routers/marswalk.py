"""FastAPI Router for Marswalk Route Planning — Phase 8.8.2.

Provides endpoints for terrain-aware route computation, cached route retrieval,
and engine metadata with mandatory safety disclaimers.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Query, status
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
from app.marswalk.multi_stop_models import (
    MultiStopRouteRequest,
    MultiStopTraverseResponse,
    MultiStopMetadataResponse,
)
from app.marswalk.multi_stop_planner import (
    MultiStopPlanner,
    get_cached_multi_stop_traverse,
)
from app.marswalk.route_intelligence_models import (
    RouteIntelligenceReport,
    MultiStopTraverseIntelligenceReport,
    RouteIntelligenceMetadataResponse,
)
from app.marswalk.route_intelligence_service import get_route_intelligence_service

logger = logging.getLogger("MARS-X.routers.marswalk")

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
def generate_route(request: MarswalkRouteRequest) -> MarswalkRouteResponse:
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
def get_route(
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
def get_metadata() -> MarswalkMetadataResponse:
    return MarswalkPlanner.get_metadata()


# =============================================================================
# MULTI-STOP SCIENCE TRAVERSE ENDPOINTS — PHASE 8.8.3
# =============================================================================

@router.post(
    "/multi-stop",
    response_model=MultiStopTraverseResponse,
    summary="Plan multi-stop science traverse with TSP optimization",
    description=(
        "Calculates an optimal connected multi-stop science traverse across authentic Mars DEMs. "
        "Evaluates pairwise directed A* terrain-aware route costs, performs TSP-style stop ordering "
        "(brute-force exact for K <= 4; nearest-neighbor + 2-opt for K > 4), and stitches "
        "connected GeoJSON geometry without duplicate junction vertices. "
        "WARNING: Minimizing terrain cost does NOT certify physical astronaut or rover safety."
    ),
    responses={
        200: {"description": "Multi-stop traverse successfully planned and optimized."},
        400: {"description": "Invalid coordinates, discovery ID not found, or unreachable mandatory stop."},
        404: {"description": "Required DEM or slope raster not found on disk."},
        422: {"description": "Traverse infeasible within slope or elevation limits."},
    },
)
def plan_multi_stop_traverse(request: MultiStopRouteRequest) -> MultiStopTraverseResponse:
    try:
        return MultiStopPlanner.plan_multi_stop_traverse(request)
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
    except (RuntimeError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Multi-stop traverse planning unexpected error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal multi-stop planning engine error: {str(e)}",
        )


@router.get(
    "/multi-stop/metadata",
    response_model=MultiStopMetadataResponse,
    summary="Get multi-stop engine metadata, presets, and capabilities",
    description="Returns supported TSP optimization strategies, max stop limits, presets, and version signatures.",
)
def get_multi_stop_metadata() -> MultiStopMetadataResponse:
    return MultiStopPlanner.get_metadata()


@router.get(
    "/multi-stop/{traverse_id}",
    response_model=MultiStopTraverseResponse,
    summary="Retrieve previously planned multi-stop traverse",
    description="Fetches full connected geometry, leg breakdown, and analytics for a cached multi-stop traverse by ID.",
    responses={
        200: {"description": "Cached multi-stop traverse found and returned."},
        404: {"description": "Traverse ID not found in cache or expired."},
    },
)
def get_multi_stop_traverse(
    traverse_id: str = Path(..., description="Unique multi-stop traverse identifier, e.g. mst-1a2b3c4d"),
) -> MultiStopTraverseResponse:
    traverse = get_cached_multi_stop_traverse(traverse_id)
    if traverse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Multi-stop traverse '{traverse_id}' not found in cache or expired. Please re-run planning.",
        )
    return traverse


# =============================================================================
# ROUTE INTELLIGENCE & SCIENTIFIC TRAVERSE ANALYSIS — PHASE 8.8.4
# =============================================================================

@router.get(
    "/analysis/metadata",
    response_model=RouteIntelligenceMetadataResponse,
    summary="Get Route Intelligence engine metadata and scientific provenance",
    description="Returns data catalog references, native resolutions, vertical datums, evidence classes, and scientific rules.",
)
def get_route_intelligence_metadata() -> RouteIntelligenceMetadataResponse:
    intel_svc = get_route_intelligence_service()
    return intel_svc.get_metadata()


@router.get(
    "/analysis/route/{route_id}",
    response_model=RouteIntelligenceReport,
    summary="Generate scientific route intelligence for a single-destination route",
    description=(
        "Analyzes elevation profile above MOLA Areoid, slope distribution, roughness, "
        "USGS SIM 3292 geological units, contact crossings, structural features, "
        "MGS TES thermal inertia, and nearby Phase 8.7 science opportunities."
    ),
    responses={
        200: {"description": "Route intelligence successfully generated."},
        404: {"description": "Route ID not found in cache or expired."},
    },
)
def analyze_route_by_id(
    route_id: str = Path(..., description="Unique route identifier, e.g. mw-a1b2c3d4e5f6"),
    ls_deg: Optional[float] = Query(default=None, description="Martian solar longitude Ls in degrees [0, 360)"),
    ltst_hours: Optional[float] = Query(default=None, description="Local True Solar Time in decimal hours [0, 24)"),
    tau: Optional[float] = Query(default=None, description="Column dust optical depth tau (tau >= 0)"),
) -> RouteIntelligenceReport:
    route = get_cached_route(route_id)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route '{route_id}' not found in cache or expired. Please plan route first.",
        )
    intel_svc = get_route_intelligence_service()
    return intel_svc.analyze_route(route, ls_deg=ls_deg, ltst_hours=ltst_hours, tau=tau)


@router.get(
    "/analysis/multi-stop/{traverse_id}",
    response_model=MultiStopTraverseIntelligenceReport,
    summary="Generate leg-by-leg and aggregated scientific traverse intelligence",
    description=(
        "Analyzes a multi-stop science traverse: leg-by-leg elevation profiles, slope exposure, "
        "geology, thermal inertia, and nearby discoveries, plus aggregated analytics across all waypoints "
        "without duplicate junction vertices."
    ),
    responses={
        200: {"description": "Traverse intelligence successfully generated."},
        404: {"description": "Traverse ID not found in cache or expired."},
    },
)
def analyze_multi_stop_traverse_by_id(
    traverse_id: str = Path(..., description="Unique multi-stop traverse identifier, e.g. mst-1a2b3c4d"),
    ls_deg: Optional[float] = Query(default=None, description="Martian solar longitude Ls in degrees [0, 360)"),
    ltst_hours: Optional[float] = Query(default=None, description="Local True Solar Time in decimal hours [0, 24)"),
    tau: Optional[float] = Query(default=None, description="Column dust optical depth tau (tau >= 0)"),
) -> MultiStopTraverseIntelligenceReport:
    traverse = get_cached_multi_stop_traverse(traverse_id)
    if traverse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Multi-stop traverse '{traverse_id}' not found in cache or expired. Please plan traverse first.",
        )
    intel_svc = get_route_intelligence_service()
    return intel_svc.analyze_multi_stop_traverse(traverse, ls_deg=ls_deg, ltst_hours=ltst_hours, tau=tau)


