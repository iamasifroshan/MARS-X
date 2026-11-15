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
    MarsTimeConversion,
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
def estimate_atmospheric_pressure(
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
def get_pressure_residuals() -> Dict[str, PressureResidualBenchmark]:
    """Retrieve quantitative residual benchmarks comparing analytical P(z) to in-situ MEDA and REMS ground truth."""
    service = get_environmental_service()
    try:
        return service.compute_pressure_residuals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute pressure residuals: {str(e)}")


@router.get("/solar-geometry", response_model=MarsSolarGeometry)
def get_solar_geometry(
    lat: float = Query(..., description="Planetocentric latitude in degrees [-90, +90]"),
    lon: float = Query(..., description="Planetocentric longitude in degrees"),
    ls_deg: float = Query(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)"),
    ltst_hours: float = Query(default=12.0, description="Local solar time in decimal hours [0, 24)"),
    tau: Optional[float] = Query(default=None, description="Optional column dust optical depth tau (tau >= 0)"),
    time_system: str = Query(default="LTST", description="Time system: 'LTST' (Local True Solar Time) or 'LMST' (Local Mean Solar Time)"),
    lon_convention: str = Query(default="east_positive", description="Longitude convention: 'east_positive' [0, 360) / [-180, +180] or 'west_positive' [0, 360)"),
) -> MarsSolarGeometry:
    """Calculate deterministic Mars solar geometry, declination, SZA, and solar irradiance."""
    service = get_environmental_service()
    try:
        return service.calculate_solar_geometry(
            lat=lat,
            lon=lon,
            ls_deg=ls_deg,
            ltst_hours=ltst_hours,
            tau=tau,
            time_system=time_system,
            lon_convention=lon_convention,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/time/eot")
def get_equation_of_time(
    ls_deg: float = Query(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)"),
) -> Dict[str, Any]:
    """Calculate the Martian Equation of Time (EOT = LTST - LMST) from areocentric solar longitude Ls."""
    service = get_environmental_service()
    eot_deg, eot_hours = service.calculate_equation_of_time(ls_deg)
    return {
        "solar_longitude_ls_deg": round(ls_deg % 360.0, 2),
        "equation_of_time_deg": round(eot_deg, 4),
        "equation_of_time_hours": round(eot_hours, 4),
        "equation_of_time_minutes": round(eot_hours * 60.0, 2),
        "classification": "Analytical Model",
        "citation": "Allison & McEwen (2000), Planetary and Space Science 48(2-3), pp. 215-235",
    }


@router.get("/time/convert", response_model=MarsTimeConversion)
def convert_time(
    time_hours: float = Query(..., description="Solar time in decimal hours [0, 24)"),
    from_system: str = Query(..., description="Input time system: 'LMST', 'LTST', or 'MTC'"),
    to_system: str = Query(..., description="Target time system: 'LMST', 'LTST', or 'MTC'"),
    lon_deg: float = Query(..., description="Planetocentric longitude in degrees"),
    ls_deg: float = Query(default=0.0, description="Martian solar longitude Ls in degrees [0, 360)"),
    lon_convention: str = Query(default="east_positive", description="Longitude convention: 'east_positive' or 'west_positive'"),
) -> MarsTimeConversion:
    """Convert solar time between MTC, LMST, and LTST according to longitude convention."""
    service = get_environmental_service()
    try:
        return service.convert_mars_time(
            time_hours=time_hours,
            from_system=from_system,
            to_system=to_system,
            lon_deg=lon_deg,
            ls_deg=ls_deg,
            lon_convention=lon_convention,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/historical/meda", response_model=HistoricalWeatherSummary)
def get_historical_meda() -> HistoricalWeatherSummary:
    """Retrieve historical in-situ meteorological summary from Mars 2020 Perseverance MEDA Sol 1."""
    service = get_environmental_service()
    try:
        return service.get_historical_meda_sol1()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load MEDA Sol 1 records: {str(e)}")


@router.get("/historical/rems", response_model=HistoricalWeatherSummary)
def get_historical_rems() -> HistoricalWeatherSummary:
    """Retrieve historical in-situ meteorological summary from MSL Curiosity REMS Sol 1."""
    service = get_environmental_service()
    try:
        return service.get_historical_rems_sol1()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load REMS Sol 1 records: {str(e)}")


@router.post("/route/enrich", response_model=RouteEnvironmentalSummary)
def enrich_route_environment(payload: RouteEnrichmentRequest) -> RouteEnvironmentalSummary:
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
