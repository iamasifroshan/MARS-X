"""FastAPI Router for Planetary Terrain Intelligence and Scientific Analysis."""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Body

from app.config import API_V1_PREFIX
from app.terrain.resolution_selector import (
    ResolutionSelector,
    ResolutionSelectionRequest,
    ResolutionSelectionResult,
    AnalysisType,
)
from app.terrain.multiscale_analysis import (
    MultiScaleAnalyzer,
    MultiScaleAnalysisRequest,
    MultiScaleAnalysisResult,
)
from app.terrain.resolution_transition import (
    ResolutionTransitionService,
    ResolutionTransitionRequest,
    ResolutionTransitionEvaluation,
)
from app.science.terrain_intelligence import (
    TerrainIntelligenceService,
    RegionDefinition,
    RegionTerrainAssessment,
    RegionComparisonRequest,
    RegionComparisonResponse,
    PRESET_CANDIDATE_REGIONS,
)

logger = logging.getLogger("MARS-X.routers.science")

router = APIRouter(prefix=f"{API_V1_PREFIX}/science", tags=["science"])

# Services
selector = ResolutionSelector()
analyzer = MultiScaleAnalyzer()
transition_service = ResolutionTransitionService()
intelligence_service = TerrainIntelligenceService()


@router.get("/resolution-selection", response_model=ResolutionSelectionResult)
def select_resolution(
    min_lat: float = Query(..., ge=-90.0, le=90.0, description="Minimum latitude (-90° to 90°)"),
    min_lon: float = Query(..., ge=0.0, le=360.0, description="Minimum longitude (0° to 360°)"),
    max_lat: float = Query(..., ge=-90.0, le=90.0, description="Maximum latitude (-90° to 90°)"),
    max_lon: float = Query(..., ge=0.0, le=360.0, description="Maximum longitude (0° to 360°)"),
    analysis_type: AnalysisType = Query(default=AnalysisType.TRAVERSE_PLANNING, description="Mission analysis intent"),
    target_scale_m: Optional[float] = Query(default=None, ge=0.5, le=50000.0, description="Target analysis scale in metres"),
    require_local_raster: bool = Query(default=True, description="Strictly require on-disk raster availability"),
    min_coverage_pct: float = Query(default=50.0, ge=0.0, le=100.0, description="Minimum acceptable footprint coverage"),
) -> ResolutionSelectionResult:
    """Identify and select the scientifically appropriate Martian elevation product for a requested region."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) cannot exceed max_lat ({max_lat})")
    if min_lon > max_lon:
        raise HTTPException(status_code=400, detail=f"min_lon ({min_lon}) cannot exceed max_lon ({max_lon})")

    req = ResolutionSelectionRequest(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        analysis_type=analysis_type,
        target_scale_m=target_scale_m,
        require_local_raster=require_local_raster,
        min_coverage_pct=min_coverage_pct,
    )
    try:
        return selector.select_resolution(req)
    except Exception as e:
        logger.error("Resolution selection failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/terrain-profile", response_model=MultiScaleAnalysisResult)
def get_terrain_profile(
    min_lat: float = Query(..., ge=-90.0, le=90.0),
    min_lon: float = Query(..., ge=0.0, le=360.0),
    max_lat: float = Query(..., ge=-90.0, le=90.0),
    max_lon: float = Query(..., ge=0.0, le=360.0),
    dataset_id: Optional[str] = Query(default=None, description="Optional dataset ID (e.g. 'mola-megdr-128', 'ctx-dtm-p21-009323')"),
    windows_m: str = Query(default="100,500,1000,2000", description="Comma-separated physical analysis windows in metres"),
) -> MultiScaleAnalysisResult:
    """Compute scale-aware terrain indicators (slope, roughness, relief, complexity) at physical windows in metres."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail="min_lat cannot exceed max_lat")
    if min_lon > max_lon:
        raise HTTPException(status_code=400, detail="min_lon cannot exceed max_lon")

    # Guard bounds dimension to prevent synchronous server stall
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon
    if lat_span > 20.0 or lon_span > 20.0:
        raise HTTPException(status_code=400, detail="Analysis region span exceeds 20° limit. Please query a sub-region.")

    try:
        parsed_windows = [float(w.strip()) for w in windows_m.split(",") if w.strip()]
        if not parsed_windows:
            parsed_windows = [500.0]
    except ValueError:
        raise HTTPException(status_code=400, detail="windows_m must be a comma-separated list of numbers (e.g. '100,500,1000')")

    req = MultiScaleAnalysisRequest(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        dataset_id=dataset_id,
        windows_m=parsed_windows,
    )
    try:
        return analyzer.analyze_region(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Terrain profile analysis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transition-compatibility", response_model=ResolutionTransitionEvaluation)
def evaluate_transition_compatibility(
    product_a: str = Query(..., description="First product ID"),
    product_b: str = Query(..., description="Second product ID"),
    min_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(default=None, ge=0.0, le=360.0),
    max_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(default=None, ge=0.0, le=360.0),
) -> ResolutionTransitionEvaluation:
    """Assess whether two datasets can support a continuous or partitioned analytical region."""
    req = ResolutionTransitionRequest(
        product_a=product_a,
        product_b=product_b,
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
    )
    try:
        return transition_service.evaluate_transition(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Transition evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/region-assessment", response_model=RegionTerrainAssessment)
def get_region_assessment(
    min_lat: float = Query(..., ge=-90.0, le=90.0),
    min_lon: float = Query(..., ge=0.0, le=360.0),
    max_lat: float = Query(..., ge=-90.0, le=90.0),
    max_lon: float = Query(..., ge=0.0, le=360.0),
    name: str = Query(default="Custom Candidate Region"),
    region_id: Optional[str] = Query(default=None),
    target_scale_m: float = Query(default=500.0, ge=1.0, le=20000.0),
) -> RegionTerrainAssessment:
    """Return comprehensive terrain intelligence assessment for a candidate Mars exploration region."""
    if min_lat > max_lat:
        raise HTTPException(status_code=400, detail="min_lat cannot exceed max_lat")
    if min_lon > max_lon:
        raise HTTPException(status_code=400, detail="min_lon cannot exceed max_lon")

    reg = RegionDefinition(
        region_id=region_id or "custom-region",
        name=name,
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
    )
    try:
        return intelligence_service.assess_region(reg, target_scale_m=target_scale_m)
    except Exception as e:
        logger.error("Region assessment failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/region-comparison", response_model=RegionComparisonResponse)
def get_preset_region_comparison(
    target_scale_m: float = Query(default=500.0, ge=1.0, le=20000.0),
) -> RegionComparisonResponse:
    """Compare authoritative preset Martian exploration regions at an equivalent physical scale."""
    req = RegionComparisonRequest(
        regions=PRESET_CANDIDATE_REGIONS[:3],  # Compare first 3 presets
        target_scale_m=target_scale_m,
    )
    try:
        return intelligence_service.compare_regions(req)
    except Exception as e:
        logger.error("Preset region comparison failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/region-comparison", response_model=RegionComparisonResponse)
def post_custom_region_comparison(
    request: RegionComparisonRequest,
) -> RegionComparisonResponse:
    """Compare user-defined candidate Martian regions at an equivalent physical scale."""
    try:
        return intelligence_service.compare_regions(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Custom region comparison failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provenance")
def get_scientific_provenance_registry(
    filter_status: Optional[str] = Query(default=None, description="Optional filter by production_status or provenance_status"),
) -> Dict[str, Any]:
    """Retrieve the authoritative MARS-X Scientific Dataset Provenance Registry."""
    import os
    import json

    registry_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "research", "dataset_provenance_registry.json")
    )
    if not os.path.exists(registry_path):
        raise HTTPException(status_code=404, detail="Provenance registry file not found.")

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        datasets = data.get("datasets", [])
        if filter_status:
            filtered = [
                d for d in datasets
                if d.get("production_status") == filter_status or d.get("provenance_status") == filter_status
            ]
            return {
                "registry_version": data.get("registry_version"),
                "last_audited_utc": data.get("last_audited_utc"),
                "policy_compliance": data.get("policy_compliance"),
                "total_count": len(datasets),
                "filtered_count": len(filtered),
                "filter": filter_status,
                "datasets": filtered,
            }

        return data
    except Exception as e:
        logger.error("Failed to read provenance registry: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provenance/{dataset_id}")
def get_dataset_provenance_by_id(
    dataset_id: str,
) -> Dict[str, Any]:
    """Retrieve detailed scientific provenance, checksums, CRS, and URLs for a specific dataset ID."""
    import os
    import json

    registry_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "research", "dataset_provenance_registry.json")
    )
    if not os.path.exists(registry_path):
        raise HTTPException(status_code=404, detail="Provenance registry file not found.")

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        datasets = data.get("datasets", [])
        for d in datasets:
            if d.get("dataset_id") == dataset_id:
                return d

        raise HTTPException(status_code=404, detail=f"Dataset ID '{dataset_id}' not found in provenance registry.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query dataset provenance: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

