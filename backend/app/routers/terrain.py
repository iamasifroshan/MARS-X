"""Terrain API router for MARS-X."""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.config import API_V1_PREFIX
from app.terrain.models import (
    TerrainSummaryResponse,
    RasterCoverageResponse,
    RasterMetadataResponse,
)
from app.terrain.provenance import (
    list_terrain_datasets,
    get_terrain_dataset_coverage,
    get_terrain_dataset_summary,
    TERRAIN_DATASET_PROVENANCE,
)
from app.terrain.raster_inspector import inspect_raster_file
from app.terrain.elevation_service import engine

router = APIRouter(prefix=f"{API_V1_PREFIX}/terrain", tags=["terrain"])


@router.get("/datasets", response_model=List[TerrainSummaryResponse])
async def get_terrain_datasets():
    """Retrieve all registered Martian numerical elevation products.

    Strictly separates numerical DTMs from visual shaded relief imagery.
    """
    return list_terrain_datasets()


@router.get("/metadata", response_model=RasterMetadataResponse)
async def get_terrain_metadata(
    dataset_id: str = Query(..., description="Target dataset ID (e.g., 'mola-megdr')"),
    file_path: Optional[str] = Query(None, description="Optional path to local raster file to inspect via Rasterio"),
):
    """Inspect and return raster metadata and CRS parameters.

    If file_path is specified, runs live Rasterio inspection on the file.
    If only dataset_id is provided, checks if a local raster is registered with the engine,
    or returns 404 if local raster has not been ingested.
    """
    target_path = file_path
    if not target_path and engine.is_raster_available(dataset_id):
        target_path = engine._loaded_rasters.get(dataset_id.lower())

    if target_path:
        if not os.path.exists(target_path):
            raise HTTPException(status_code=404, detail=f"Raster file not found: {target_path}")
        try:
            return inspect_raster_file(target_path, dataset_id=dataset_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to inspect raster: {str(e)}")

    # If dataset exists in provenance registry but file is not on disk:
    if dataset_id.lower() in TERRAIN_DATASET_PROVENANCE:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Raster data file for '{dataset_id}' has not yet been downloaded to local storage. "
                "Dataset is registered in the catalogue, but raw raster headers cannot be fabricated."
            ),
        )

    raise HTTPException(status_code=404, detail=f"Terrain dataset '{dataset_id}' not found in registry.")


@router.get("/coverage", response_model=RasterCoverageResponse)
async def get_terrain_coverage(
    dataset_id: str = Query(..., description="Target dataset ID (e.g., 'mola-megdr', 'hrsc-dtm', 'hirise-dtm', 'ctx-dtm')")
):
    """Retrieve verified geographic footprint, coordinate bounds, and surface coverage percentage."""
    coverage = get_terrain_dataset_coverage(dataset_id)
    if not coverage:
        raise HTTPException(status_code=404, detail=f"Coverage footprint for '{dataset_id}' not found.")
    return coverage


@router.get("/summary", response_model=TerrainSummaryResponse)
async def get_terrain_summary(
    dataset_id: str = Query(..., description="Target dataset ID (e.g., 'mola-megdr')")
):
    """Retrieve complete scientific summary and provenance information for a single terrain dataset."""
    summary = get_terrain_dataset_summary(dataset_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Terrain dataset summary for '{dataset_id}' not found.")
    return summary
