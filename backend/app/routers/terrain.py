"""Terrain API router for MARS-X.

Exposes endpoints for:
- Datasets, metadata, coverage, layers, and product profiles
- Multi-resolution comparisons and tile adjacency
- Scientific validation registry and reports (/validation, /products/{id}/validation)
- MOLA MEG128 tile inventory and coverage calculations (/inventory)
- Strict CRS and vertical datum compatibility assessment (/compatibility)
- Terrain hazard metrics and metadata (/hazards, /hazards/metadata)
"""

import os
import numpy as np
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path

from app.config import API_V1_PREFIX
from app.terrain.models import (
    TerrainSummaryResponse,
    RasterCoverageResponse,
    RasterMetadataResponse,
    ElevationPointQuery,
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
from app.terrain.validation import (
    DatasetValidationRegistry,
    ProductValidationReport,
)
from app.terrain.inventory import (
    Mola128InventoryService,
    Mola128InventoryReport,
    TileAdjacencyCheckResult,
)
from app.terrain.harmonization import (
    HarmonizationEngine,
    CompatibilityAssessmentResult,
)
from app.terrain.hazard_engine import (
    TerrainHazardEngine,
    TerrainHazardPointMetrics,
    HazardEngineMetadata,
    HazardThresholds,
)

router = APIRouter(prefix=f"{API_V1_PREFIX}/terrain", tags=["terrain"])

inventory_service = Mola128InventoryService()
hazard_engine = TerrainHazardEngine()


@router.get("/datasets", response_model=List[TerrainSummaryResponse])
async def get_terrain_datasets():
    """Retrieve all registered Martian numerical elevation products."""
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
            "resolution_desc": "0.25°/px (~14.8 km/px)",
            "ground_spacing_m": 14818.67,
            "crs": "IAU:49900",
            "vertical_datum": "Gradient (Horn 3x3)",
            "unit": "degrees",
            "value_range": {"min": 0.0, "max": 18.2},
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


@router.get("/validation", response_model=List[ProductValidationReport])
async def get_validation_summary():
    """Retrieve lifecycle states and scientific verification summaries for all terrain products."""
    return DatasetValidationRegistry.get_all_reports()


@router.get("/products/{product_id}/validation", response_model=ProductValidationReport)
async def get_product_validation(
    product_id: str = Path(..., description="Target product identifier (e.g., 'mola-megdr-4')")
):
    """Retrieve detailed scientific validation report and check history for a single product."""
    report = DatasetValidationRegistry.get_report(product_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Validation report for '{product_id}' not found.")
    return report


@router.get("/inventory", response_model=Mola128InventoryReport)
async def get_mola_128_inventory():
    """Retrieve MOLA 128 ppd tile inventory, download statuses, and computed spherical coverage."""
    return inventory_service.get_inventory_report()


@router.get("/inventory/adjacency", response_model=TileAdjacencyCheckResult)
async def check_tile_adjacency(
    tile_a: str = Query(..., description="First tile identifier (e.g., 'megt00n000hb')"),
    tile_b: str = Query(..., description="Second tile identifier (e.g., 'megt44n000hb')"),
):
    """Inspect topological boundary adjacency and seam alignment between two MOLA 128 tiles."""
    try:
        return Mola128InventoryService.check_adjacency(tile_a, tile_b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/compatibility", response_model=CompatibilityAssessmentResult)
async def assess_product_compatibility(
    product_a: str = Query(..., description="First product ID (e.g., 'mola-megdr-128')"),
    product_b: str = Query(..., description="Second product ID (e.g., 'hirise-dtm-jezero')"),
):
    """Assess horizontal CRS, vertical datum, and resolution compatibility before combining or comparing."""
    try:
        return HarmonizationEngine.assess_compatibility(product_a, product_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/hazards/metadata", response_model=HazardEngineMetadata)
async def get_hazard_metadata():
    """Retrieve mathematical algorithms, thresholds, and limitations of the terrain hazard engine."""
    return HazardEngineMetadata()


@router.get("/hazards", response_model=TerrainHazardPointMetrics)
async def evaluate_terrain_hazards(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Target Martian latitude"),
    lon: float = Query(..., ge=0.0, le=360.0, description="Target Martian positive-East longitude"),
    dataset_id: str = Query("mola-megdr", description="Source DTM product ID (e.g., 'mola-megdr')"),
):
    """Evaluate point terrain hazard indicators (slope, relief, roughness, discontinuities, and complexity).

    Uses authentic locally ingested raster data.
    """
    if not engine.is_raster_available(dataset_id):
        raise HTTPException(
            status_code=404,
            detail=f"Numerical raster for '{dataset_id}' not loaded or unavailable locally. Cannot compute hazards."
        )

    # Sample local 3x3 window around the requested point
    # Global MOLA 4 ppd has pixel size d_lat = 0.25, d_lon = 0.25
    d_lat = 0.25
    d_lon = 0.25

    # Extract 3x3 elevations
    elev_grid = np.zeros((3, 3), dtype=np.float32)
    offsets = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),  (0, 0),  (0, 1),
               (1, -1),  (1, 0),  (1, 1)]

    for row_idx, d_row in enumerate([-1, 0, 1]):
        for col_idx, d_col in enumerate([-1, 0, 1]):
            sample_lat = max(min(lat - d_row * d_lat, 90.0), -90.0)
            sample_lon = (lon + d_col * d_lon) % 360.0
            pt = engine.query_elevation_point(
                ElevationPointQuery(
                    latitude=sample_lat,
                    longitude=sample_lon,
                    dataset_id=dataset_id,
                )
            )
            elev_grid[row_idx, col_idx] = pt.elevation_m if pt.elevation_m is not None else -32768.0

    metrics = hazard_engine.evaluate_point_hazards(
        lat_deg=lat,
        lon_deg=lon,
        window_3x3=elev_grid,
        d_lat_deg=d_lat,
        d_lon_deg=d_lon,
        source_dataset=dataset_id,
        source_resolution_m=14818.67,
        validation_state_score=1.0,
    )
    return metrics


@router.get("/metadata", response_model=RasterMetadataResponse)
async def get_terrain_metadata(
    dataset_id: str = Query(..., description="Target dataset ID (e.g., 'mola-megdr')"),
    file_path: Optional[str] = Query(None, description="Optional path to local raster file to inspect via Rasterio"),
):
    """Inspect and return raster metadata and CRS parameters."""
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
