"""Terrain API router for MARS-X."""

import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path

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
from app.terrain.multi_resolution import (
    MultiResolutionTerrainCatalog,
    DTMProductProfile,
    ResolutionComparisonResult,
)

router = APIRouter(prefix=f"{API_V1_PREFIX}/terrain", tags=["terrain"])


@router.get("/datasets", response_model=List[TerrainSummaryResponse])
async def get_terrain_datasets():
    """Retrieve all registered Martian numerical elevation products.

    Strictly separates numerical DTMs from visual shaded relief imagery.
    """
    return list_terrain_datasets()


@router.get("/layers")
async def get_terrain_layers():
    """Retrieve all active and catalogued terrain visualization layers (Elevation, Slope, Roughness)."""
    processed_mola_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed", "mola"))

    elev_cog = os.path.join(processed_mola_dir, "mola_megt90n000cb_elevation.tif")
    slope_cog = os.path.join(processed_mola_dir, "mola_megt90n000cb_slope.tif")
    rough_cog = os.path.join(processed_mola_dir, "mola_megt90n000cb_roughness.tif")

    layers = [
        {
            "layer_id": "mola-elevation-global",
            "name": "MOLA Global Elevation (4 px/deg)",
            "product_type": "elevation",
            "instrument": "MOLA",
            "resolution_desc": "0.25°/px (~14.8 km/px)",
            "ground_spacing_m": 14818.67,
            "crs": "IAU:49900",
            "vertical_datum": "MOLA Areoid",
            "unit": "metres",
            "value_range": {"min": -8068.0, "max": 21134.0},
            "is_available": os.path.exists(elev_cog),
            "file_format": "COG (Cloud Optimized GeoTIFF)",
            "file_path": elev_cog if os.path.exists(elev_cog) else None,
        },
        {
            "layer_id": "mola-slope-global",
            "name": "MOLA Topographic Slope (Horn)",
            "product_type": "slope",
            "instrument": "MOLA",
            "resolution_desc": "0.25°/px (latitudinally scaled cell spacing)",
            "ground_spacing_m": 14818.67,
            "crs": "IAU:49900",
            "vertical_datum": "Angular Gradient",
            "unit": "degrees",
            "value_range": {"min": 0.0, "max": 16.5},
            "is_available": os.path.exists(slope_cog),
            "file_format": "COG (Cloud Optimized GeoTIFF)",
            "file_path": slope_cog if os.path.exists(slope_cog) else None,
        },
        {
            "layer_id": "mola-roughness-global",
            "name": "MOLA Terrain Roughness (Local Std Dev)",
            "product_type": "roughness",
            "instrument": "MOLA",
            "resolution_desc": "0.25°/px (3x3 moving window)",
            "ground_spacing_m": 14818.67,
            "crs": "IAU:49900",
            "vertical_datum": "Surface Deviation",
            "unit": "metres",
            "value_range": {"min": 0.0, "max": 3523.2},
            "is_available": os.path.exists(rough_cog),
            "file_format": "COG (Cloud Optimized GeoTIFF)",
            "file_path": rough_cog if os.path.exists(rough_cog) else None,
        },
        {
            "layer_id": "mola-megdr-128-tile-00n000",
            "name": "MOLA High-Resolution Base Tile (128 px/deg)",
            "product_type": "elevation",
            "instrument": "MOLA",
            "resolution_desc": "0.0078125°/px (~463 m/px)",
            "ground_spacing_m": 463.08,
            "crs": "IAU:49900",
            "vertical_datum": "MOLA Areoid",
            "unit": "metres",
            "value_range": {"min": -6000.0, "max": 4000.0},
            "is_available": os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "mola", "megt00n000hb.img")),
            "file_format": "PDS3 IMG / Tiled",
            "coverage_footprint": "Lat [-44.0°, 0.0°], Lon [0.0°, 90.0°E]",
        },
        {
            "layer_id": "hirise-dtm-jezero",
            "name": "HiRISE Jezero Crater Delta DTM (1 m/px)",
            "product_type": "elevation",
            "instrument": "HiRISE",
            "resolution_desc": "1.0 m/px post-spacing",
            "ground_spacing_m": 1.0,
            "crs": "Equirectangular Mars",
            "vertical_datum": "MOLA Areoid (tied)",
            "unit": "metres",
            "value_range": {"min": -2700.0, "max": -2300.0},
            "is_available": False,
            "file_format": "GeoTIFF (PDS archive)",
            "coverage_footprint": "Lat [18.30°, 18.55°N], Lon [77.35°, 77.60°E]",
        }
    ]
    return layers


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

    if dataset_id.lower() in TERRAIN_DATASET_PROVENANCE:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Raster data file for '{dataset_id}' has not yet been downloaded to local storage. "
                "Dataset is registered in the catalogue, but raw raster headers cannot be fabricated."
            ),
        )

    raise HTTPException(status_code=404, detail=f"Terrain dataset '{dataset_id}' not found in registry.")


@router.get("/coverage")
async def get_terrain_coverage(
    dataset_id: Optional[str] = Query(None, description="Specific dataset ID"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Query point latitude"),
    lon: Optional[float] = Query(None, ge=0.0, le=360.0, description="Query point positive-East longitude"),
):
    """Retrieve coverage footprint information or query which DTMs intersect a coordinate."""
    if lat is not None and lon is not None:
        intersecting = MultiResolutionTerrainCatalog.find_intersecting_dtms(lat, lon)
        return {
            "query_coordinate": {"latitude": lat, "longitude": lon},
            "matching_dtms_count": len(intersecting),
            "finest_available_resolution_m": intersecting[0].pixel_spacing_m if intersecting else None,
            "covering_dtms": intersecting,
        }

    if dataset_id:
        coverage = get_terrain_dataset_coverage(dataset_id)
        if not coverage:
            raise HTTPException(status_code=404, detail=f"Coverage footprint for '{dataset_id}' not found.")
        return coverage

    # Return full multi-tier catalog coverage
    return {
        "catalog_tiers": [
            {"tier": "global_coarse", "resolution": "14.8 km/px", "coverage": "100% Global"},
            {"tier": "global_base", "resolution": "463 m/px", "coverage": "98.6% Global (tiled)"},
            {"tier": "regional", "resolution": "20–50 m/px", "coverage": "~5%–70% Regional Swaths"},
            {"tier": "local_tactical", "resolution": "1.0 m/px", "coverage": "<0.1% Targeted Landing Sites"}
        ],
        "products": MultiResolutionTerrainCatalog.get_all_products()
    }


@router.get("/compare", response_model=ResolutionComparisonResult)
async def compare_terrain_resolutions(
    product_a: str = Query(..., description="First product ID (e.g., 'mola-megdr-128')"),
    product_b: str = Query(..., description="Second product ID (e.g., 'hirise-dtm-jezero')"),
):
    """Compare resolution ratio, scale factors, and vertical datum compatibility between two DTMs."""
    try:
        return MultiResolutionTerrainCatalog.compare_products(product_a, product_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/products/{product_id}", response_model=DTMProductProfile)
async def get_terrain_product_profile(
    product_id: str = Path(..., description="Product identifier (e.g., 'hirise-dtm-jezero')")
):
    """Retrieve comprehensive profile for a specific multi-resolution DTM product."""
    product = MultiResolutionTerrainCatalog.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found in multi-resolution catalog.")
    return product


@router.get("/summary", response_model=TerrainSummaryResponse)
async def get_terrain_summary(
    dataset_id: str = Query(..., description="Target dataset ID (e.g., 'mola-megdr')")
):
    """Retrieve complete scientific summary and provenance information for a single terrain dataset."""
    summary = get_terrain_dataset_summary(dataset_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Terrain dataset summary for '{dataset_id}' not found.")
    return summary
