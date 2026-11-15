"""Environmental Intelligence Router — Phase 8.9.1.

FastAPI endpoints for:
- Atmospheric reference pressure estimation P(z) = P_ref * exp(-z / H)
- Analytical model vs in-situ rover ground-truth residual benchmarking
- Deterministic Mars solar geometry & irradiance
- Historical MEDA & REMS Sol 1 in-situ meteorological observations
- Route environmental profile enrichment
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.science.environmental_models import (
    AtmosphericPressureEstimate,
    PressureResidualBenchmark,
    MarsSolarGeometry,
    HistoricalWeatherSummary,
    RouteEnvironmentalSummary,
    EnvironmentalMetadataResponse,
)
from app.science.environmental_service import get_environmental_service

router = APIRouter(prefix="/api/v1/environmental", tags=["environmental"])


class RouteEnrichmentRequest(BaseModel):
    """Payload for enriching route points with environmental context."""

    route_points: List[Dict[str, Any]] = Field(
        ...,
        description="List of route waypoint dictionaries containing lat, lon, elevation_m, and distance_m",
    )
    ls_deg: float = Field(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)")
    ltst_hours: float = Field(default=12.0, description="Local True Solar Time in decimal hours [0, 24)")
    tau: Optional[float] = Field(default=None, description="Optional atmospheric dust optical depth tau (tau >= 0)")
    max_samples: int = Field(default=50, description="Maximum number of sampled points to return in profile")


@router.get("/metadata", response_model=EnvironmentalMetadataResponse)
async def get_environmental_metadata() -> EnvironmentalMetadataResponse:
    """Return catalogue and metadata describing analytical models, parameters, and limitations."""
    service = get_environmental_service()
    return service.get_metadata()


@router.get("/pressure/estimate", response_model=AtmosphericPressureEstimate)
async def estimate_atmospheric_pressure(
    elevation_m: float = Query(..., description="Topographic elevation in metres relative to MOLA Areoid datum"),
    p_ref_pa: Optional[float] = Query(default=None, description="Reference pressure at datum in Pa (default: 610.0 Pa)"),
    scale_height_m: Optional[float] = Query(default=None, description="Atmospheric scale height in metres (default: 11100.0 m)"),
) -> AtmosphericPressureEstimate:
    """Calculate the reference atmospheric pressure at elevation z relative to MOLA Areoid.

    Formula: P(z) = P_ref * exp(-z / H)
    """
    service = get_environmental_service()
    try:
        return service.estimate_atmospheric_pressure(
            elevation_m=elevation_m,
            p_ref_pa=p_ref_pa,
            scale_height_m=scale_height_m,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pressure/residuals", response_model=Dict[str, PressureResidualBenchmark])
async def get_pressure_residuals() -> Dict[str, PressureResidualBenchmark]:
    """Retrieve quantitative residual benchmarks comparing analytical P(z) to in-situ MEDA and REMS ground truth."""
    service = get_environmental_service()
    try:
        return service.compute_pressure_residuals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute pressure residuals: {str(e)}")


@router.get("/solar-geometry", response_model=MarsSolarGeometry)
async def get_solar_geometry(
    lat: float = Query(..., description="Planetocentric latitude in degrees [-90, +90]"),
    lon: float = Query(..., description="Planetocentric East longitude in degrees [0, 360)"),
    ls_deg: float = Query(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)"),
    ltst_hours: float = Query(default=12.0, description="Local True Solar Time in decimal hours [0, 24)"),
    tau: Optional[float] = Query(default=None, description="Optional column dust optical depth tau (tau >= 0)"),
) -> MarsSolarGeometry:
    """Calculate deterministic Mars solar geometry, declination, SZA, and surface solar flux."""
    service = get_environmental_service()
    try:
        return service.calculate_solar_geometry(
            lat=lat,
            lon=lon,
            ls_deg=ls_deg,
            ltst_hours=ltst_hours,
            tau=tau,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/historical/meda", response_model=HistoricalWeatherSummary)
async def get_historical_meda() -> HistoricalWeatherSummary:
    """Retrieve historical in-situ meteorological summary from Mars 2020 Perseverance MEDA Sol 1."""
    service = get_environmental_service()
    try:
        return service.get_historical_meda_sol1()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load MEDA Sol 1 records: {str(e)}")


@router.get("/historical/rems", response_model=HistoricalWeatherSummary)
async def get_historical_rems() -> HistoricalWeatherSummary:
    """Retrieve historical in-situ meteorological summary from MSL Curiosity REMS Sol 1."""
    service = get_environmental_service()
    try:
        return service.get_historical_rems_sol1()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load REMS Sol 1 records: {str(e)}")


@router.post("/route/enrich", response_model=RouteEnvironmentalSummary)
async def enrich_route_environment(payload: RouteEnrichmentRequest) -> RouteEnvironmentalSummary:
    """Enrich a sequence of route waypoints with reference barometric pressure and solar geometry."""
    service = get_environmental_service()
    try:
        return service.enrich_route_environmental_context(
            route_points=payload.route_points,
            ls_deg=payload.ls_deg,
            ltst_hours=payload.ltst_hours,
            tau=payload.tau,
            max_samples=payload.max_samples,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enrich route environmental context: {str(e)}")
