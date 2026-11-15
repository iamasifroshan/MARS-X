"""MARS-X — Climatology Router — Phase 8.9.2.

FastAPI endpoints for:
- MCD v6.2 Mars climatology metadata and provenance specification
- Point climatological evaluation with spatial, seasonal, and diurnal interpolation
- Diurnal (24-hour) and seasonal (360-degree Ls) atmospheric/surface profile curves
- Climatological coverage boundaries and landmark exploration anchors
- Traverse-level climatological enrichment for single-leg and multi-stop Marswalks
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.science.climatology_models import (
    ClimatologyPoint,
    ClimatologyProfileResponse,
    ClimatologyMetadataResponse,
    ClimatologyCoverageResponse,
    RouteClimatologySummary,
    RouteClimatologyEnrichRequest,
)
from app.science.climatology_service import get_climatology_service

router = APIRouter(prefix="/api/v1/environmental/climatology", tags=["climatology"])


@router.get("/metadata", response_model=ClimatologyMetadataResponse)
async def get_climatology_metadata() -> ClimatologyMetadataResponse:
    """Return catalogue and metadata describing the Mars Climate Database (MCD v6.2) integration."""
    service = get_climatology_service()
    return service.get_climatology_metadata()


@router.get("/point", response_model=ClimatologyPoint)
def get_climatology_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Planetocentric latitude in degrees [-90, +90]"),
    lon: float = Query(..., description="Planetocentric East longitude in degrees [0, 360)"),
    ls_deg: float = Query(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)"),
    ltst_hours: float = Query(default=12.0, description="Local True Solar Time in decimal hours [0, 24)"),
    elevation_m: Optional[float] = Query(
        default=None,
        description="MOLA Areoid elevation in metres for barometric and lapse rate scaling",
    ),
) -> ClimatologyPoint:
    """Evaluate climatological atmospheric and surface parameters at arbitrary location, season, and time."""
    service = get_climatology_service()
    try:
        return service.get_climatology_at_point(
            latitude=lat,
            longitude=lon,
            solar_longitude_ls_deg=ls_deg,
            local_true_solar_time_hours=ltst_hours,
            elevation_m=elevation_m,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute climatology at point: {e}")


@router.get("/profile", response_model=ClimatologyProfileResponse)
def get_climatology_profile(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Planetocentric latitude in degrees"),
    lon: float = Query(..., description="Planetocentric East longitude in degrees"),
    profile_type: str = Query(
        default="diurnal",
        pattern="^(diurnal|seasonal)$",
        description="Type of profile curve to generate: 'diurnal' (24 hours) or 'seasonal' (360 degrees Ls)",
    ),
    fixed_param: float = Query(
        default=0.0,
        description="Value of fixed parameter: Ls in degrees for diurnal profile, LTST in hours for seasonal profile",
    ),
    elevation_m: Optional[float] = Query(
        default=None,
        description="MOLA Areoid elevation in metres for topographic scaling",
    ),
    step_count: int = Query(
        default=24,
        ge=4,
        le=120,
        description="Number of evaluation points along profile",
    ),
) -> ClimatologyProfileResponse:
    """Generate a 24-hour diurnal or 360-degree seasonal climatological profile curve."""
    service = get_climatology_service()
    try:
        return service.get_climatology_profile(
            latitude=lat,
            longitude=lon,
            profile_type=profile_type,
            fixed_param=fixed_param,
            elevation_m=elevation_m,
            step_count=step_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate climatology profile: {e}")


@router.get("/coverage", response_model=ClimatologyCoverageResponse)
def get_climatology_coverage() -> ClimatologyCoverageResponse:
    """Return coverage boundaries, native grid dimensions, and anchor exploration landmarks."""
    service = get_climatology_service()
    return service.get_climatology_coverage()


@router.post("/route/enrich", response_model=RouteClimatologySummary)
def enrich_route_climatology(
    request: RouteClimatologyEnrichRequest,
) -> RouteClimatologySummary:
    """Enrich a planned Marswalk traverse with seasonal and diurnal climatological context."""
    service = get_climatology_service()
    try:
        return service.enrich_route_climatology(
            route_points=request.route_points,
            ls_deg=request.ls_deg,
            ltst_hours=request.ltst_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enrich route with climatology: {e}")
