"""FastAPI Router for MARS-X Terrain Traversability — Phase 8.8.1.

Endpoints:
  GET /api/v1/traversability/metadata   — Source inventory, algorithm docs, slope thresholds
  GET /api/v1/traversability/point      — Single-point elevation, slope, category, provenance
  GET /api/v1/traversability/window     — Bounded slope-category grid for map display
  GET /api/v1/traversability/coverage   — All terrain source coverage footprints
  GET /api/v1/traversability/legend     — Slope-category legend with colours and disclaimers

STRICT SCOPE:
  This router does NOT plan routes or generate traversal paths.
  Slope bands are analytical terrain classifications ONLY.
  No terrain in this system has been certified astronaut-safe.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import API_V1_PREFIX
from app.terrain.traversability_service import (
    get_traversability_service,
    TraversabilityPointResult,
    TraversabilityWindowResult,
    TraversabilityCoverageEntry,
    TraversabilityLegendEntry,
    TerrainSourceInfo,
    SLOPE_DISCLAIMER,
    SLOPE_THRESHOLDS,
)

logger = logging.getLogger("MARS-X.routers.traversability")

router = APIRouter(prefix=f"{API_V1_PREFIX}/traversability", tags=["traversability"])


@router.get("/metadata")
async def get_traversability_metadata():
    """Return terrain source inventory, slope algorithm documentation, and threshold configuration.

    Clients should read this endpoint to understand what DEM products underpin
    slope values and how slope categories are defined.
    """
    svc = get_traversability_service()
    sources = svc.get_sources()
    return {
        "description": (
            "Terrain Traversability Foundation — Phase 8.8.1. "
            "Provides scientifically traceable slope, elevation and terrain coverage from "
            "validated Mars DTM datasets. Does NOT implement route generation or pathfinding."
        ),
        "slope_algorithm": "Horn (1981) weighted 3×3 gradient in degrees (arctan of gradient magnitude)",
        "slope_units": "degrees (0–90°)",
        "slope_thresholds_deg": SLOPE_THRESHOLDS,
        "slope_disclaimer": SLOPE_DISCLAIMER,
        "vertical_datum_policy": (
            "All elevation values are MOLA Areoid heights (gravitational equipotential surface, "
            "GMM3 mgm1025 degree 50). No reference-sphere radii are mixed with areoid heights."
        ),
        "source_selection_policy": [
            "1. HiRISE DTM (~1 m/px)   — if coordinate within swath footprint AND file on disk",
            "2. CTX DTM   (~20 m/px)   — if coordinate within swath footprint AND file on disk",
            "3. MOLA 128ppd (~463 m/px) — regional tiles where available AND file on disk",
            "4. MOLA 4ppd  (~14.8 km)   — global fallback",
        ],
        "anti_upsampling_guarantee": (
            "Coarser sources are NEVER upsampled and presented as higher-resolution detail. "
            "Each response reports native pixel spacing. Resolution mismatches are explicitly stated."
        ),
        "nodata_policy": (
            "Any coordinate with missing or NoData elevation or slope is classified 'unknown'. "
            "Unknown terrain is NEVER re-classified as low or safe terrain."
        ),
        "terrain_sources": [s.model_dump() for s in sources],
    }


@router.get("/point", response_model=TraversabilityPointResult)
def get_traversability_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Planetocentric latitude in degrees"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="East longitude in degrees (0–360 or -180–180)"),
):
    """Query elevation, slope angle, slope category and full provenance for a single Mars coordinate.

    The response always reports:
    - Which DEM product was selected and why.
    - Native pixel spacing of the selected product.
    - Whether elevation and/or slope are NoData.
    - Vertical datum of elevation values.
    - Slope disclaimer confirming this is an analytical terrain metric, NOT a safety assessment.

    If no terrain data covers the coordinate, all values are null and slope_category is 'unknown'.
    """
    svc = get_traversability_service()
    try:
        return svc.query_point(lat, lon)
    except Exception as exc:
        logger.exception("Error querying traversability point (%.4f, %.4f): %s", lat, lon, exc)
        raise HTTPException(status_code=500, detail=f"Traversability point query failed: {exc}")


@router.get("/window", response_model=TraversabilityWindowResult)
def get_traversability_window(
    min_lat: float = Query(..., ge=-90.0, le=90.0,  description="South boundary latitude"),
    max_lat: float = Query(..., ge=-90.0, le=90.0,  description="North boundary latitude"),
    min_lon: float = Query(..., ge=-180.0, le=360.0, description="West boundary longitude"),
    max_lon: float = Query(..., ge=-180.0, le=360.0, description="East boundary longitude"),
    width:   int   = Query(64, ge=4, le=128,         description="Output grid width (columns), max 128"),
    height:  int   = Query(32, ge=4, le=64,          description="Output grid height (rows), max 64"),
):
    """Return a gridded slope classification over a bounding box.

    Returns a 2-D grid of slope values (degrees) and slope category strings
    suitable for client-side map rendering. Grid resolution is capped at 128×64
    to avoid large payloads.

    The response reports:
    - Source dataset ID and native pixel spacing.
    - Display pixel spacing (ground distance per output pixel).
    - Sampling regime (native_matched / oversampled / undersampled).
    - Per-cell slope_values (float, or null for NoData) and slope_categories (string).
    - nodata_fraction: fraction of grid cells with no valid slope data.
    - coverage_within_bbox_fraction: fraction of grid cells within any source footprint.
    """
    if min_lat >= max_lat:
        raise HTTPException(status_code=400, detail=f"min_lat ({min_lat}) must be less than max_lat ({max_lat})")
    svc = get_traversability_service()
    try:
        return svc.query_window(min_lat, max_lat, min_lon, max_lon, width, height)
    except Exception as exc:
        logger.exception("Error querying traversability window: %s", exc)
        raise HTTPException(status_code=500, detail=f"Traversability window query failed: {exc}")


@router.get("/coverage", response_model=List[TraversabilityCoverageEntry])
async def get_traversability_coverage():
    """Return coverage footprints for all terrain sources used by the traversability system.

    Each entry describes geographic bounds, pixel spacing, file availability, and
    vertical datum for one terrain product. Clients can use this to build layer
    boundary overlays and resolution legends.
    """
    svc = get_traversability_service()
    return svc.get_coverage()


@router.get("/legend", response_model=List[TraversabilityLegendEntry])
async def get_traversability_legend():
    """Return the slope classification legend with color codes and descriptions.

    IMPORTANT: Slope categories are analytical terrain bands derived from orbital DEM data.
    They do NOT assess astronaut mobility, EVA safety, or geotechnical bearing capacity.
    """
    return get_traversability_service().get_legend()
