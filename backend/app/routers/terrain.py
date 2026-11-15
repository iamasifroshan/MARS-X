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
import math
import threading
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, HTTPException, Query, Path

from app.config import API_V1_PREFIX
from app.terrain.models import (
    TerrainSummaryResponse,
    RasterCoverageResponse,
    RasterMetadataResponse,
    ElevationPointQuery,
    PointElevationDetailResult,
    ElevationProfilePoint,
    ElevationProfileResult,
    WindowRenderMetadata,
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
    ProductOverlapResult,
    RasterElevationComparisonResult,
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
from fastapi.responses import Response
import rasterio
from rasterio.io import MemoryFile
from rasterio.enums import Resampling

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
            "layer_id": "ctx-dtm-p21-009323",
            "name": "USGS CTX DTM: Tyrrhena Terra (20m/px)",
            "product_type": "elevation",
            "instrument": "CTX",
            "resolution_desc": "20.01 m/px post-spacing",
            "ground_spacing_m": 20.01,
            "crs": "IAU:49910",
            "vertical_datum": "MOLA Areoid (ASP tied)",
            "unit": "metres",
            "value_range": {"min": 800.0, "max": 2520.0},
            "is_available": os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif")),
            "file_format": "GeoTIFF (Stereo numerical DTM)",
            "coverage_footprint": "Lat [-5.19°, -4.01°N], Lon [66.03°, 66.60°E]",
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


# ==============================================================================
# PHASE 7 MULTI-RESOLUTION INTELLIGENCE ENDPOINTS
# ==============================================================================

@router.get("/products")
async def get_all_terrain_products():
    """List all terrain products across all resolution tiers with availability and lifecycle states."""
    products = MultiResolutionTerrainCatalog.get_all_products()
    results = []
    for p in products:
        rep = DatasetValidationRegistry.get_report(p.product_id)
        results.append({
            "product_id": p.product_id,
            "instrument": p.instrument,
            "mission": p.mission,
            "tier": p.tier,
            "pixel_spacing_m": p.pixel_spacing_m,
            "pixel_spacing_desc": p.pixel_spacing_desc,
            "geographic_bounds": {
                "lat_min": p.lat_min,
                "lat_max": p.lat_max,
                "lon_min": p.lon_min,
                "lon_max": p.lon_max,
            },
            "horizontal_crs": p.crs,
            "vertical_datum": p.vertical_datum,
            "lifecycle_state": rep.lifecycle_state if rep else "registered",
            "raster_available_locally": rep.raster_available_locally if rep else False,
            "is_analysis_ready": rep.is_analysis_ready if rep else False,
            "source_archive": p.source_archive,
            "download_url": p.download_url,
            "quality_notes": p.quality_notes,
        })
    return {
        "total_products": len(results),
        "available_locally_count": sum(1 for r in results if r["raster_available_locally"]),
        "analysis_ready_count": sum(1 for r in results if r["is_analysis_ready"]),
        "products": results,
    }


@router.get("/coverage/region")
async def get_terrain_coverage_region(
    min_lat: float = Query(..., ge=-90.0, le=90.0),
    min_lon: float = Query(..., ge=0.0, le=360.0),
    max_lat: float = Query(..., ge=-90.0, le=90.0),
    max_lon: float = Query(..., ge=0.0, le=360.0),
):
    """Query all terrain products intersecting a geographic bounding box."""
    if min_lat >= max_lat or min_lon >= max_lon:
        raise HTTPException(status_code=400, detail="Invalid bounding box: min coordinates must be strictly less than max coordinates.")

    matches = MultiResolutionTerrainCatalog.find_intersecting_dtms_bbox(min_lat, min_lon, max_lat, max_lon)
    return {
        "query_bounds": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        },
        "matching_products_count": len(matches),
        "finest_native_resolution_m": matches[0].pixel_spacing_m if matches else None,
        "available_tiers": list(set(m.tier for m in matches)),
        "products": matches,
    }


@router.get("/resolution-stack")
async def get_terrain_resolution_stack(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=0.0, le=360.0),
):
    """Return available native resolutions intersecting a coordinate, sorted finest to coarsest."""
    intersecting = MultiResolutionTerrainCatalog.find_intersecting_dtms(lat, lon)
    stack = []
    for p in intersecting:
        rep = DatasetValidationRegistry.get_report(p.product_id)
        stack.append({
            "tier": p.tier,
            "product_id": p.product_id,
            "instrument": p.instrument,
            "pixel_spacing_m": p.pixel_spacing_m,
            "pixel_spacing_desc": p.pixel_spacing_desc,
            "is_raster_available": rep.raster_available_locally if rep else False,
            "lifecycle_state": rep.lifecycle_state if rep else "registered",
            "crs": p.crs,
            "vertical_datum": p.vertical_datum,
        })
    return {
        "coordinate": {"latitude": lat, "longitude": lon},
        "tiers_count": len(stack),
        "finest_pixel_spacing_m": stack[0]["pixel_spacing_m"] if stack else None,
        "stack": stack,
    }


@router.get("/overlap", response_model=ProductOverlapResult)
async def get_terrain_product_overlap(
    product_a: str = Query(..., description="First product ID"),
    product_b: str = Query(..., description="Second product ID"),
):
    """Calculate geographic footprint overlap and resolution ratio between two terrain products."""
    try:
        return MultiResolutionTerrainCatalog.calculate_product_overlap(product_a, product_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/compare-products")
async def compare_products_elevation(
    product_a: str = Query(..., description="First product ID (e.g. 'mola-megdr-128')"),
    product_b: str = Query(..., description="Second product ID (e.g. 'ctx-dtm-p21-009323')"),
    run_raster_analysis: bool = Query(False, description="Whether to execute real numerical raster sampling if both are available locally"),
    sample_points: Optional[int] = Query(None, description="Optional sample points count for real raster comparison"),
):
    """Compare two DTM products with compatibility information and optional real raster statistics."""
    try:
        comparison = MultiResolutionTerrainCatalog.compare_products(product_a, product_b)
        overlap = MultiResolutionTerrainCatalog.calculate_product_overlap(product_a, product_b)

        result: Dict[str, Any] = {
            "comparison": comparison,
            "overlap": overlap,
        }

        should_run_raster = run_raster_analysis or (sample_points is not None)
        if should_run_raster and overlap.both_locally_available and overlap.has_overlap:
            try:
                raster_stats = MultiResolutionTerrainCatalog.compare_overlapping_rasters(
                    product_a, product_b, sample_points=sample_points
                )
                result["raster_analysis"] = raster_stats
                # Also expose flat keys for direct access
                result["sample_points_count"] = raster_stats.sample_points_count
                result["mean_delta_m"] = raster_stats.mean_delta_m
                result["std_delta_m"] = raster_stats.std_delta_m
                result["mean_elevation_a_m"] = raster_stats.mean_elevation_a_m
                result["mean_elevation_b_m"] = raster_stats.mean_elevation_b_m
                result["scientific_interpretation"] = raster_stats.scientific_interpretation
            except Exception as e:
                result["raster_analysis_error"] = str(e)

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/quality")
async def get_terrain_quality_metadata(
    product_id: Optional[str] = Query(None, description="Specific product ID to retrieve quality report for"),
):
    """Return scientific validation, uncertainty, and provenance metadata."""
    if product_id:
        report = DatasetValidationRegistry.get_report(product_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Quality report for product '{product_id}' not found.")
        return report

    return {
        "all_reports": DatasetValidationRegistry.get_all_reports()
    }


def _render_turbo_rgba(elev: np.ndarray, nodata_mask: np.ndarray, vmin: float, vmax: float, alpha_val: int = 235) -> bytes:
    """Helper to convert elevation grid to colored RGBA PNG bytes with NoData transparency using Turbo color mapping."""
    norm = np.clip((elev - vmin) / max(vmax - vmin, 1e-4), 0.0, 1.0)
    # Polynomial Turbo approximation
    kR = [0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943]
    kG = [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604]
    kB = [0.10798322, 8.44582113, -34.80584489, 43.16781254, -28.91494539, 5.09355606]
    r = np.polyval(kR[::-1], norm)
    g = np.polyval(kG[::-1], norm)
    b = np.polyval(kB[::-1], norm)

    h, w = elev.shape
    rgba = np.zeros((4, h, w), dtype=np.uint8)
    valid = ~nodata_mask
    rgba[0] = np.where(valid, np.clip(r * 255.0, 0, 255).astype(np.uint8), 0)
    rgba[1] = np.where(valid, np.clip(g * 255.0, 0, 255).astype(np.uint8), 0)
    rgba[2] = np.where(valid, np.clip(b * 255.0, 0, 255).astype(np.uint8), 0)
    rgba[3] = np.where(valid, alpha_val, 0)

    with MemoryFile() as memfile:
        with memfile.open(
            driver="PNG",
            height=h,
            width=w,
            count=4,
            dtype=np.uint8,
        ) as dst:
            dst.write(rgba)
        return memfile.read()


@router.get("/render/global-mola")
def render_global_mola(hemisphere: str = Query(default="east", pattern="^(east|west)$")):
    """Render authentic Global MOLA numerical elevation as colored RGBA PNG with NoData transparency.
    - east: Longitude [0°, 180°E], Latitude [-90°, 90°N]
    - west: Longitude [-180°, 0°E] (180°E to 360°E), Latitude [-90°, 90°N]
    """
    cog_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed", "mola", "mola_megt90n000cb_elevation.tif")
    )
    if not os.path.exists(cog_path):
        raise HTTPException(status_code=404, detail="Processed Global MOLA COG raster not found on disk.")

    with rasterio.open(cog_path) as src:
        elev = src.read(1)
        nodata = src.nodata

    if hemisphere == "east":
        sub_elev = elev[:, :720]
    else:
        sub_elev = elev[:, 720:]

    nodata_mask = (sub_elev == nodata) | ~np.isfinite(sub_elev)
    png_bytes = _render_turbo_rgba(sub_elev, nodata_mask, vmin=-8200.0, vmax=21200.0, alpha_val=230)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/render/mola-128-tile")
def render_mola_128_tile(tile_id: str = Query(default="00n000", pattern="^(00n000|44n000|00n090)$")):
    """Render authentic regional MOLA 128 ppd tile numerical elevation as colored RGBA PNG."""
    filename_map = {
        "00n000": "megt00n000hb.img",
        "44n000": "megt44n000hb.img",
        "00n090": "megt00n090hb.img",
    }
    raw_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "mola", filename_map[tile_id])
    )
    if not os.path.exists(raw_path):
        raise HTTPException(status_code=404, detail=f"MOLA 128 tile '{tile_id}' not found on disk.")

    # 5632 lines x 11520 samples, 16-bit big-endian signed integer
    mm = np.memmap(raw_path, dtype=">i2", mode="r", shape=(5632, 11520))
    # Subsample 16x for responsive rendering (352 lines x 720 samples)
    sub = mm[::16, ::16].astype(np.float32)
    nodata_mask = (sub == -32768)

    # Elevation range for tiles: ~-6000m to +4000m
    png_bytes = _render_turbo_rgba(sub, nodata_mask, vmin=-6000.0, vmax=4000.0, alpha_val=240)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/render/ctx-dtm")
def render_ctx_dtm():
    """Render authentic USGS 20m CTX numerical DTM as colored high-contrast RGBA PNG."""
    ctx_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif")
    )
    if not os.path.exists(ctx_path):
        raise HTTPException(status_code=404, detail="USGS CTX DTM raster not found on disk.")

    with rasterio.open(ctx_path) as src:
        out_shape = (src.height // 4, src.width // 4)
        elev = src.read(1, out_shape=out_shape, resampling=Resampling.bilinear)
        nodata = src.nodata

    nodata_mask = (elev == nodata) | (elev < -30000) | ~np.isfinite(elev)
    # CTX elevation range: ~800m to 2520m
    png_bytes = _render_turbo_rgba(elev, nodata_mask, vmin=800.0, vmax=2520.0, alpha_val=245)
    return Response(content=png_bytes, media_type="image/png")


# -------------------------------------------------------------
# PHASE 8.3: MULTI-RESOLUTION POINT INSPECTOR & ELEVATION PROFILE
# -------------------------------------------------------------

_MEMMAPS_128: Dict[str, np.memmap] = {}
_OPEN_RASTERS: Dict[str, rasterio.DatasetReader] = {}
_RASTER_LOCK = threading.Lock()
_WINDOW_CACHE: Dict[str, Tuple[bytes, Dict[str, str]]] = {}
_MAX_WINDOW_CACHE = 64


def _get_raster_reader(path: str) -> Optional[rasterio.DatasetReader]:
    """Retrieve or lazily open persistent rasterio reader handle in a thread-safe manner."""
    with _RASTER_LOCK:
        if path in _OPEN_RASTERS:
            reader = _OPEN_RASTERS[path]
            if not reader.closed:
                return reader
        if os.path.exists(path):
            try:
                reader = rasterio.open(path)
                _OPEN_RASTERS[path] = reader
                return reader
            except Exception:
                return None
        return None


def _get_mola128_mm(tile_id: str) -> Optional[np.memmap]:
    """Retrieve or initialize memory map for MOLA 128 ppd tile."""
    if tile_id in _MEMMAPS_128:
        return _MEMMAPS_128[tile_id]

    filename_map = {
        "00n000": "megt00n000hb.img",
        "44n000": "megt44n000hb.img",
        "00n090": "megt00n090hb.img",
    }
    fname = filename_map.get(tile_id)
    if not fname:
        return None

    raw_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "mola", fname)
    )
    if not os.path.exists(raw_path):
        return None

    mm = np.memmap(raw_path, dtype=">i2", mode="r", shape=(5632, 11520))
    _MEMMAPS_128[tile_id] = mm
    return mm


def _sample_point_elevation(lat: float, lon: float, preferred_source: Optional[str] = None) -> PointElevationDetailResult:
    """Sample elevation from highest available resolution covering the given coordinates across authentic datasets."""
    norm_lon = lon % 360.0
    if norm_lon < 0.0:
        norm_lon += 360.0

    # 1. Out of physical planetary bounds check
    if abs(lat) > 90.0:
        return PointElevationDetailResult(
            latitude=lat,
            longitude=lon,
            elevation_m=None,
            dataset_id="none",
            instrument="none",
            tier="none",
            native_resolution_m=0.0,
            native_resolution_desc="N/A",
            display_resolution_m=None,
            crs="none",
            vertical_reference="none",
            is_nodata=True,
            is_valid=False,
            query_status="unsupported_out_of_bounds",
            status_note=f"Latitude {lat}° exceeds physical planetary bounds [-90.0°, +90.0°].",
            source_checksum="",
        )

    R_IAU = 3396190.0
    norm_lon_180 = norm_lon - 360.0 if norm_lon > 180.0 else norm_lon

    # 2. Priority 0: HiRISE Controlled DTM (1.01 m/px, Holden Crater, IAU:49910)
    # Fast geographic bounding box pre-check: lat in [-28.9, -28.1], lon in [308.7, 309.3] or lon_180 in [-51.3, -50.7]
    if preferred_source in [None, "auto", "hirise", "hirise-dtm-controlled-esp-011635"]:
        if -28.9 <= lat <= -28.1 and (308.7 <= norm_lon <= 309.3 or -51.3 <= norm_lon_180 <= -50.7):
            hirise_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                    "data",
                    "originals",
                    "hirise",
                    "DTEEC_011635_1510_029542_1510_A01.tif",
                )
            )
            hi_src = _get_raster_reader(hirise_path)
            if hi_src is not None:
                x_hi = math.radians(norm_lon_180) * R_IAU
                y_hi = math.radians(lat) * R_IAU
                if (hi_src.bounds.left <= x_hi <= hi_src.bounds.right) and (
                    hi_src.bounds.bottom <= y_hi <= hi_src.bounds.top
                ):
                    r_hi, c_hi = hi_src.index(x_hi, y_hi)
                    if 0 <= r_hi < hi_src.height and 0 <= c_hi < hi_src.width:
                        with _RASTER_LOCK:
                            val = float(hi_src.read(1, window=((r_hi, r_hi + 1), (c_hi, c_hi + 1)))[0, 0])
                        is_nodata = (val < -30000.0) or not math.isfinite(val)
                        return PointElevationDetailResult(
                            latitude=lat,
                            longitude=norm_lon,
                            elevation_m=None if is_nodata else round(val, 2),
                            dataset_id="hirise-dtm-controlled-esp-011635",
                            instrument="HiRISE (High Resolution Imaging Science Experiment)",
                            tier="ultra_high_resolution",
                            native_resolution_m=1.01,
                            native_resolution_desc="1.01 m/px controlled stereo DTM (Holden Crater)",
                            display_resolution_m=4.04,
                            crs="IAU:49910 (Equirectangular Mars Sphere, R=3396190 m)",
                            vertical_reference="MOLA Geoid Adjusted",
                            is_nodata=is_nodata,
                            is_valid=not is_nodata,
                            query_status="nodata_void" if is_nodata else "success_ultra_resolution_hirise",
                            status_note=(
                                "Unmeasured stereo correlation void"
                                if is_nodata
                                else "Sampled from authentic USGS 1m controlled HiRISE DTM."
                            ),
                            source_checksum="a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad",
                        )

    # 3. Priority 1A: Controlled CTX Numerical DTM (20.0 m/px, Apollinaris Sulci, IAU:49910)
    # Fast geographic bounding box pre-check: lat in [4.3, 5.1], lon in [167.8, 168.7]
    if preferred_source in [None, "auto", "ctx", "ctx-dtm-controlled-t01-000893"]:
        if 4.3 <= lat <= 5.1 and 167.8 <= norm_lon <= 168.7:
            t01_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                    "data",
                    "originals",
                    "ctx",
                    "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif",
                )
            )
            t01_src = _get_raster_reader(t01_path)
            if t01_src is not None:
                x_t01 = math.radians(norm_lon) * R_IAU
                y_t01 = math.radians(lat) * R_IAU
                if (t01_src.bounds.left <= x_t01 <= t01_src.bounds.right) and (
                    t01_src.bounds.bottom <= y_t01 <= t01_src.bounds.top
                ):
                    r_t01, c_t01 = t01_src.index(x_t01, y_t01)
                    if 0 <= r_t01 < t01_src.height and 0 <= c_t01 < t01_src.width:
                        with _RASTER_LOCK:
                            val = float(t01_src.read(1, window=((r_t01, r_t01 + 1), (c_t01, c_t01 + 1)))[0, 0])
                        is_nodata = (val == t01_src.nodata) or (val < -30000.0) or not math.isfinite(val)
                        return PointElevationDetailResult(
                            latitude=lat,
                            longitude=norm_lon,
                            elevation_m=None if is_nodata else round(val, 2),
                            dataset_id="ctx-dtm-controlled-t01-000893",
                            instrument="CTX (Context Camera)",
                            tier="local_high_resolution",
                            native_resolution_m=20.0,
                            native_resolution_desc="20.0 m/px controlled stereo numerical DTM (Apollinaris Sulci)",
                            display_resolution_m=80.0,
                            crs="IAU:49910 (Equirectangular Mars Sphere, R=3396190 m)",
                            vertical_reference="MOLA Geoid Adjusted",
                            is_nodata=is_nodata,
                            is_valid=not is_nodata,
                            query_status="nodata_void" if is_nodata else "success_high_resolution_ctx",
                            status_note=(
                                "Unmeasured stereo correlation void"
                                if is_nodata
                                else "Sampled from authentic USGS 20m controlled CTX DTM."
                            ),
                            source_checksum="4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51",
                        )

    # 4. Priority 1B: Tyrrhena CTX Numerical DTM (20.0128 m/px, IAU:49910)
    # Fast geographic bounding box pre-check: lat in [-5.3, -3.9], lon in [65.9, 66.8]
    if preferred_source in [None, "auto", "ctx", "ctx-dtm-p21-009323"]:
        if -5.3 <= lat <= -3.9 and 65.9 <= norm_lon <= 66.8:
            ctx_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "..",
                    "data",
                    "raw",
                    "ctx",
                    "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
                )
            )
            ctx_src = _get_raster_reader(ctx_path)
            if ctx_src is not None:
                x_ctx = math.radians(norm_lon) * R_IAU
                y_ctx = math.radians(lat) * R_IAU
                if (ctx_src.bounds.left <= x_ctx <= ctx_src.bounds.right) and (
                    ctx_src.bounds.bottom <= y_ctx <= ctx_src.bounds.top
                ):
                    r_ctx, c_ctx = ctx_src.index(x_ctx, y_ctx)
                    if 0 <= r_ctx < ctx_src.height and 0 <= c_ctx < ctx_src.width:
                        with _RASTER_LOCK:
                            val = float(ctx_src.read(1, window=((r_ctx, r_ctx + 1), (c_ctx, c_ctx + 1)))[0, 0])
                        is_nodata = (val == ctx_src.nodata) or (val < -30000.0) or not math.isfinite(val)
                        return PointElevationDetailResult(
                            latitude=lat,
                            longitude=norm_lon,
                            elevation_m=None if is_nodata else round(val, 2),
                            dataset_id="ctx-dtm-p21-009323",
                            instrument="CTX (Context Camera)",
                            tier="local_high_resolution",
                            native_resolution_m=20.0128,
                            native_resolution_desc="20.01 m/px stereo numerical DTM",
                            display_resolution_m=80.05,
                            crs="IAU:49910 (Equirectangular Mars Sphere, R=3396190 m)",
                            vertical_reference="MOLA Areoid (ASP pc_align tied)",
                            is_nodata=is_nodata,
                            is_valid=not is_nodata,
                            query_status="nodata_void" if is_nodata else "success_high_resolution_ctx",
                            status_note=(
                                "Unmeasured stereo correlation void"
                                if is_nodata
                                else "Sampled from authentic USGS 20m numerical CTX DTM."
                            ),
                            source_checksum="a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2",
                        )

    # 3. Priority 2: Regional MOLA 128 ppd Tile (~463.08 m/px, IAU:49900)
    tile_info = None
    if -44.0 <= lat <= 0.0 and 0.0 <= norm_lon <= 90.0:
        tile_info = (
            "00n000",
            "megt00n000hb",
            -lat * 128.0,
            norm_lon * 128.0,
            "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75",
        )
    elif 0.0 < lat <= 44.0 and 0.0 <= norm_lon <= 90.0:
        tile_info = (
            "44n000",
            "megt44n000hb",
            (44.0 - lat) * 128.0,
            norm_lon * 128.0,
            "14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36",
        )
    elif -44.0 <= lat <= 0.0 and 90.0 < norm_lon <= 180.0:
        tile_info = (
            "00n090",
            "megt00n090hb",
            -lat * 128.0,
            (norm_lon - 90.0) * 128.0,
            "764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e",
        )

    if tile_info:
        tile_key, tile_id, raw_r, raw_c, tile_sha = tile_info
        mm = _get_mola128_mm(tile_key)
        if mm is not None:
            r = min(max(int(round(raw_r)), 0), 5631)
            c = min(max(int(round(raw_c)), 0), 11519)
            val = float(mm[r, c])
            is_nodata = val == -32768.0
            return PointElevationDetailResult(
                latitude=lat,
                longitude=norm_lon,
                elevation_m=None if is_nodata else val,
                dataset_id=f"mola-megdr-128 ({tile_id})",
                instrument="MOLA (Mars Orbiter Laser Altimeter)",
                tier="regional_high_resolution",
                native_resolution_m=463.08,
                native_resolution_desc="0.0078125°/px (~463.08 m/px at equator)",
                display_resolution_m=7409.3,
                crs="IAU:49900 (Simple Cylindrical / Mars Sphere R=3396000 m)",
                vertical_reference="MOLA Areoid (GMM3 mgm1025 degree 50)",
                is_nodata=is_nodata,
                is_valid=not is_nodata,
                query_status="nodata_void" if is_nodata else "success_regional_mola_128",
                status_note=(
                    "Altimetry unmeasured void"
                    if is_nodata
                    else f"Sampled from authentic regional MOLA 128 ppd tile {tile_id}."
                ),
                source_checksum=tile_sha,
            )

    # 4. Priority 3: Global MOLA 4 ppd Baseline (~14.8 km/px, IAU:49900)
    cog_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "processed",
            "mola",
            "mola_megt90n000cb_elevation.tif",
        )
    )
    mola4_src = _get_raster_reader(cog_path)
    if mola4_src is not None:
        r, c = mola4_src.index(norm_lon, lat)
        if 0 <= r < mola4_src.height and 0 <= c < mola4_src.width:
            val = float(mola4_src.read(1, window=((r, r + 1), (c, c + 1)))[0, 0])
            is_nodata = not math.isfinite(val) or (val == mola4_src.nodata)
            return PointElevationDetailResult(
                latitude=lat,
                longitude=norm_lon,
                elevation_m=None if is_nodata else round(val, 2),
                dataset_id="mola-megdr-4",
                instrument="MOLA (Mars Orbiter Laser Altimeter)",
                tier="global_baseline",
                native_resolution_m=14818.67,
                native_resolution_desc="0.25°/px (~14.8 km/px at equator)",
                display_resolution_m=14818.67,
                crs="IAU:49900 (Equirectangular Mars Sphere R=3396000 m)",
                vertical_reference="MOLA Areoid (GMM3 mgm1025 degree 50)",
                is_nodata=is_nodata,
                is_valid=not is_nodata,
                query_status="nodata_void" if is_nodata else "success_global_mola_baseline",
                status_note=(
                    "NoData cell"
                    if is_nodata
                    else "Sampled from authentic Global MOLA 4 ppd continuous elevation baseline."
                ),
                source_checksum="25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c",
            )

    return PointElevationDetailResult(
        latitude=lat,
        longitude=norm_lon,
        elevation_m=None,
        dataset_id="none",
        instrument="none",
        tier="none",
        native_resolution_m=0.0,
        native_resolution_desc="N/A",
        display_resolution_m=None,
        crs="none",
        vertical_reference="none",
        is_nodata=True,
        is_valid=False,
        query_status="unsupported_region",
        status_note="No verified numerical elevation raster covers this coordinate.",
        source_checksum="",
    )


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle spherical distance on Mars (radius 3,396,190 m)."""
    R = 3396190.0
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    sigma = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R * sigma


def _slerp_great_circle(lat1: float, lon1: float, lat2: float, lon2: float, f: float) -> Tuple[float, float]:
    """Spherical linear interpolation along great-circle arc."""
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    sigma = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    if sigma < 1e-12:
        return lat1, lon1 % 360.0
    A = math.sin((1.0 - f) * sigma) / math.sin(sigma)
    B = math.sin(f * sigma) / math.sin(sigma)
    x = A * math.cos(phi1) * math.cos(lam1) + B * math.cos(phi2) * math.cos(lam2)
    y = A * math.cos(phi1) * math.sin(lam1) + B * math.cos(phi2) * math.sin(lam2)
    z = A * math.sin(phi1) + B * math.sin(phi2)
    lat_f = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon_f = math.degrees(math.atan2(y, x)) % 360.0
    return lat_f, lon_f


@router.get("/elevation/point", response_model=PointElevationDetailResult)
def get_point_elevation(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Planetocentric latitude in degrees"),
    lon: float = Query(..., description="East longitude in degrees (0 to 360 or -180 to 180)"),
    preferred_source: Optional[str] = Query(default=None, description="Optional preferred product or tier ('auto', 'hirise', 'ctx', 'mola')"),
):
    """Query authentic numerical elevation at a single Martian coordinate across multi-resolution hierarchy."""
    return _sample_point_elevation(lat, lon, preferred_source=preferred_source)


@router.get("/elevation/profile", response_model=ElevationProfileResult)
def get_elevation_profile(
    start_lat: float = Query(..., ge=-90.0, le=90.0),
    start_lon: float = Query(...),
    end_lat: float = Query(..., ge=-90.0, le=90.0),
    end_lon: float = Query(...),
    num_samples: int = Query(default=100, ge=10, le=500),
):
    """Compute great-circle geodesic elevation profile across authentic multi-resolution Martian terrain."""
    total_dist_m = _haversine_distance_m(start_lat, start_lon, end_lat, end_lon)
    sampling_interval_m = total_dist_m / max(num_samples - 1, 1)

    points: List[ElevationProfilePoint] = []
    datasets_used_set = set()
    nodata_count = 0
    valid_elevations: List[float] = []
    elevation_gain_m = 0.0
    elevation_loss_m = 0.0
    prev_elev: Optional[float] = None

    for i in range(num_samples):
        frac = i / float(num_samples - 1) if num_samples > 1 else 0.0
        lat_i, lon_i = _slerp_great_circle(start_lat, start_lon, end_lat, end_lon, frac)
        dist_i = frac * total_dist_m

        pt_res = _sample_point_elevation(lat_i, lon_i)
        datasets_used_set.add(pt_res.dataset_id)

        if pt_res.is_nodata or pt_res.elevation_m is None:
            nodata_count += 1
            elev = None
        else:
            elev = pt_res.elevation_m
            valid_elevations.append(elev)
            if prev_elev is not None:
                diff = elev - prev_elev
                if diff > 0:
                    elevation_gain_m += diff
                else:
                    elevation_loss_m += abs(diff)
            prev_elev = elev

        points.append(
            ElevationProfilePoint(
                point_index=i,
                lat=round(lat_i, 5),
                lon=round(lon_i, 5),
                distance_m=round(dist_i, 1),
                elevation_m=elev,
                dataset_id=pt_res.dataset_id,
                resolution_m=pt_res.native_resolution_m,
                is_nodata=pt_res.is_nodata,
            )
        )

    return ElevationProfileResult(
        start_lat=start_lat,
        start_lon=start_lon % 360.0,
        end_lat=end_lat,
        end_lon=end_lon % 360.0,
        total_distance_m=round(total_dist_m, 2),
        sampling_interval_m=round(sampling_interval_m, 2),
        num_samples=num_samples,
        min_elevation_m=min(valid_elevations) if valid_elevations else None,
        max_elevation_m=max(valid_elevations) if valid_elevations else None,
        elevation_gain_m=round(elevation_gain_m, 2),
        elevation_loss_m=round(elevation_loss_m, 2),
        datasets_used=sorted(list(datasets_used_set)),
        nodata_count=nodata_count,
        points=points,
    )


@router.get("/render/window")
def render_terrain_window(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    width: int = Query(default=512, ge=64, le=1024),
    height: int = Query(default=512, ge=64, le=1024),
    preferred_tier: str = Query(default="auto"),
):
    """Progressive windowed raster rendering endpoint supporting dynamic viewport queries with custom headers."""
    # Check cache
    cache_key = f"{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}_{width}_{height}_{preferred_tier}"
    if cache_key in _WINDOW_CACHE:
        png_bytes, headers = _WINDOW_CACHE[cache_key]
        cached_headers = dict(headers)
        cached_headers["X-Cache-Status"] = "HIT"
        return Response(content=png_bytes, media_type="image/png", headers=cached_headers)

    # Normalize bounds
    lon_min_norm = min_lon % 360.0
    lon_max_norm = max_lon % 360.0
    if lon_max_norm < lon_min_norm:
        lon_max_norm += 360.0

    # 0. Check HiRISE Controlled DTM (Holden Crater, ~1.01 m/px)
    hirise_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "originals",
            "hirise",
            "DTEEC_011635_1510_029542_1510_A01.tif",
        )
    )
    lon_180_min = lon_min_norm - 360.0 if lon_min_norm > 180.0 else lon_min_norm
    lon_180_max = lon_max_norm - 360.0 if lon_max_norm > 180.0 else lon_max_norm
    if lon_180_min > lon_180_max:
        lon_180_min, lon_180_max = lon_180_max, lon_180_min

    has_hirise_overlap = (
        not (max_lat < -28.66 or min_lat > -28.37 or lon_180_max < -51.03 or lon_180_min > -50.94)
        and (max_lat - min_lat <= 1.0)
    )
    if has_hirise_overlap and preferred_tier in ["auto", "hirise"] and os.path.exists(hirise_path):
        with rasterio.open(hirise_path) as hi_src:
            R_IAU = 3396190.0
            x_min = math.radians(lon_180_min) * R_IAU
            x_max = math.radians(lon_180_max) * R_IAU
            y_min = math.radians(min_lat) * R_IAU
            y_max = math.radians(max_lat) * R_IAU

            from rasterio.windows import from_bounds
            win = from_bounds(x_min, y_min, x_max, y_max, hi_src.transform)
            arr = hi_src.read(
                1,
                window=win,
                out_shape=(height, width),
                resampling=Resampling.bilinear,
                boundless=True,
                fill_value=-3.40282e+38,
            )
            nodata_mask = (arr < -30000.0) | ~np.isfinite(arr)
            png_bytes = _render_turbo_rgba(arr, nodata_mask, vmin=-2400.0, vmax=-700.0, alpha_val=245)

            disp_res = (x_max - x_min) / float(width)
            src_res = 1.01
            ratio = disp_res / src_res
            regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")

            headers = {
                "X-Source-Dataset": "hirise-dtm-controlled-esp-011635",
                "X-Source-Resolution": "1.01 m/px",
                "X-Display-Resolution": f"{disp_res:.2f} m/px",
                "X-Sampling-Regime": regime,
                "X-Sampling-Ratio": f"{ratio:.4f}",
                "X-Output-Dimensions": f"{width}x{height}",
                "X-Resampling-Method": "bilinear",
                "X-Source-Checksum": "a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad",
                "X-Geographic-Bounds": f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]",
                "X-Cache-Status": "MISS",
            }
            if len(_WINDOW_CACHE) < _MAX_WINDOW_CACHE:
                _WINDOW_CACHE[cache_key] = (png_bytes, headers)
            return Response(content=png_bytes, media_type="image/png", headers=headers)

    # 0B. Check Apollinaris Sulci Controlled CTX DTM (20.0 m/px)
    t01_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "originals",
            "ctx",
            "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif",
        )
    )
    has_t01_overlap = (
        not (max_lat < 4.44 or min_lat > 4.99 or lon_max_norm < 168.07 or lon_min_norm > 168.50)
        and (max_lat - min_lat <= 2.5)
    )
    if has_t01_overlap and preferred_tier in ["auto", "ctx"] and os.path.exists(t01_path):
        with rasterio.open(t01_path) as t01_src:
            R_IAU = 3396190.0
            x_min = math.radians(lon_min_norm) * R_IAU
            x_max = math.radians(lon_max_norm) * R_IAU
            y_min = math.radians(min_lat) * R_IAU
            y_max = math.radians(max_lat) * R_IAU

            from rasterio.windows import from_bounds
            win = from_bounds(x_min, y_min, x_max, y_max, t01_src.transform)
            arr = t01_src.read(
                1,
                window=win,
                out_shape=(height, width),
                resampling=Resampling.bilinear,
                boundless=True,
                fill_value=-32767.0,
            )
            nodata_mask = (arr == -32767.0) | (arr < -30000.0) | ~np.isfinite(arr)
            png_bytes = _render_turbo_rgba(arr, nodata_mask, vmin=-3500.0, vmax=-2200.0, alpha_val=245)

            disp_res = (x_max - x_min) / float(width)
            src_res = 20.0
            ratio = disp_res / src_res
            regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")

            headers = {
                "X-Source-Dataset": "ctx-dtm-controlled-t01-000893",
                "X-Source-Resolution": "20.0 m/px",
                "X-Display-Resolution": f"{disp_res:.2f} m/px",
                "X-Sampling-Regime": regime,
                "X-Sampling-Ratio": f"{ratio:.4f}",
                "X-Output-Dimensions": f"{width}x{height}",
                "X-Resampling-Method": "bilinear",
                "X-Source-Checksum": "4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51",
                "X-Geographic-Bounds": f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]",
                "X-Cache-Status": "MISS",
            }
            if len(_WINDOW_CACHE) < _MAX_WINDOW_CACHE:
                _WINDOW_CACHE[cache_key] = (png_bytes, headers)
            return Response(content=png_bytes, media_type="image/png", headers=headers)

    # 1. Check Tyrrhena CTX DTM (20.0128 m/px)
    ctx_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "raw",
            "ctx",
            "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
        )
    )
    # CTX extent: Lat [-5.19, -4.01], Lon [66.03, 66.60]
    R_IAU = 3396190.0

    # 0. Check HiRISE Holden Crater overlap
    lon_180_min = lon_min_norm - 360.0 if lon_min_norm > 180.0 else lon_min_norm
    lon_180_max = lon_max_norm - 360.0 if lon_max_norm > 180.0 else lon_max_norm
    if lon_180_min > lon_180_max:
        lon_180_min, lon_180_max = lon_180_max, lon_180_min

    has_hirise_overlap = (
        not (max_lat < -28.66 or min_lat > -28.37 or lon_180_max < -51.03 or lon_180_min > -50.94)
        and (max_lat - min_lat <= 1.0)
    )
    if has_hirise_overlap:
        x_min = math.radians(lon_180_min) * R_IAU
        x_max = math.radians(lon_180_max) * R_IAU
        disp_res = (x_max - x_min) / float(width)
        src_res = 1.01
        ratio = disp_res / src_res
        regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
        return WindowRenderMetadata(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width=width,
            height=height,
            dataset_id="hirise-dtm-controlled-esp-011635",
            source_resolution_m=1.01,
            display_resolution_m=round(disp_res, 2),
            sampling_regime=regime,
            sampling_ratio=round(ratio, 4),
            resampling_method="bilinear",
            source_checksum="a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad",
        )

    # 0B. Check Apollinaris Sulci CTX overlap
    has_t01_overlap = (
        not (max_lat < 4.44 or min_lat > 4.99 or lon_max_norm < 168.07 or lon_min_norm > 168.50)
        and (max_lat - min_lat <= 2.5)
    )
    if has_t01_overlap:
        x_min = math.radians(lon_min_norm) * R_IAU
        x_max = math.radians(lon_max_norm) * R_IAU
        disp_res = (x_max - x_min) / float(width)
        src_res = 20.0
        ratio = disp_res / src_res
        regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
        return WindowRenderMetadata(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width=width,
            height=height,
            dataset_id="ctx-dtm-controlled-t01-000893",
            source_resolution_m=20.0,
            display_resolution_m=round(disp_res, 2),
            sampling_regime=regime,
            sampling_ratio=round(ratio, 4),
            resampling_method="bilinear",
            source_checksum="4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51",
        )

    has_ctx_overlap = (
        not (max_lat < -5.19 or min_lat > -4.01 or lon_max_norm < 66.03 or lon_min_norm > 66.61)
        and (max_lat - min_lat <= 2.5)
    )

    if has_ctx_overlap and preferred_tier in ["auto", "ctx"] and os.path.exists(ctx_path):
        with rasterio.open(ctx_path) as ctx_src:
            R_IAU = 3396190.0
            x_min = math.radians(lon_min_norm) * R_IAU
            x_max = math.radians(lon_max_norm) * R_IAU
            y_min = math.radians(min_lat) * R_IAU
            y_max = math.radians(max_lat) * R_IAU

            from rasterio.windows import from_bounds

            win = from_bounds(x_min, y_min, x_max, y_max, ctx_src.transform)
            arr = ctx_src.read(
                1,
                window=win,
                out_shape=(height, width),
                resampling=Resampling.bilinear,
                boundless=True,
                fill_value=-32767.0,
            )

            nodata_mask = (arr == -32767.0) | (arr < -30000.0) | ~np.isfinite(arr)
            png_bytes = _render_turbo_rgba(arr, nodata_mask, vmin=800.0, vmax=2520.0, alpha_val=245)

            disp_res = (x_max - x_min) / float(width)
            src_res = 20.0128
            sampling_ratio = disp_res / src_res
            if sampling_ratio < 0.95:
                sampling_regime = "oversampled_resampled_visualization"
            elif sampling_ratio > 1.05:
                sampling_regime = "undersampled_decimated_overview"
            else:
                sampling_regime = "native_matched"

            headers = {
                "X-Source-Dataset": "ctx-dtm-p21-009323",
                "X-Source-Resolution": "20.0128 m/px",
                "X-Display-Resolution": f"{disp_res:.2f} m/px",
                "X-Sampling-Regime": sampling_regime,
                "X-Sampling-Ratio": f"{sampling_ratio:.4f}",
                "X-Output-Dimensions": f"{width}x{height}",
                "X-Resampling-Method": "bilinear",
                "X-Source-Checksum": "a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2",
                "X-Geographic-Bounds": f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]",
                "X-Cache-Status": "MISS",
            }
            if len(_WINDOW_CACHE) < _MAX_WINDOW_CACHE:
                _WINDOW_CACHE[cache_key] = (png_bytes, headers)
            return Response(content=png_bytes, media_type="image/png", headers=headers)

    # 2. Check if window intersects any regional MOLA 128 ppd Tile
    mola128_tiles = [
        ("00n000", "megt00n000hb", -44.0, 0.0, 0.0, 90.0, "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"),
        ("44n000", "megt44n000hb", 0.0, 44.0, 0.0, 90.0, "14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36"),
        ("00n090", "megt00n090hb", -44.0, 0.0, 90.0, 180.0, "764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e"),
    ]

    best_tile = None
    best_overlap_area = 0.0

    if preferred_tier in ["auto", "mola_128"]:
        for t_key, t_id, t_min_lat, t_max_lat, t_min_lon, t_max_lon, t_sha in mola128_tiles:
            overlap_lat_min = max(min_lat, t_min_lat)
            overlap_lat_max = min(max_lat, t_max_lat)
            overlap_lon_min = max(lon_min_norm, t_min_lon)
            overlap_lon_max = min(lon_max_norm, t_max_lon)
            if overlap_lat_max > overlap_lat_min and overlap_lon_max > overlap_lon_min:
                area = (overlap_lat_max - overlap_lat_min) * (overlap_lon_max - overlap_lon_min)
                if area > best_overlap_area:
                    best_overlap_area = area
                    best_tile = (t_key, t_id, t_min_lat, t_max_lat, t_min_lon, t_max_lon, t_sha,
                                 overlap_lat_min, overlap_lat_max, overlap_lon_min, overlap_lon_max)

    if best_tile is not None:
        t_key, t_id, t_min_lat, t_max_lat, t_min_lon, t_max_lon, t_sha, o_lat_min, o_lat_max, o_lon_min, o_lon_max = best_tile
        mm = _get_mola128_mm(t_key)
        if mm is not None:
            if t_key == "00n000":
                r_start = min(max(int(round(-o_lat_max * 128.0)), 0), 5631)
                r_end = min(max(int(round(-o_lat_min * 128.0)), 0), 5632)
                c_start = min(max(int(round(o_lon_min * 128.0)), 0), 11519)
                c_end = min(max(int(round(o_lon_max * 128.0)), 0), 11520)
            elif t_key == "44n000":
                r_start = min(max(int(round((44.0 - o_lat_max) * 128.0)), 0), 5631)
                r_end = min(max(int(round((44.0 - o_lat_min) * 128.0)), 0), 5632)
                c_start = min(max(int(round(o_lon_min * 128.0)), 0), 11519)
                c_end = min(max(int(round(o_lon_max * 128.0)), 0), 11520)
            else:  # 00n090
                r_start = min(max(int(round(-o_lat_max * 128.0)), 0), 5631)
                r_end = min(max(int(round(-o_lat_min * 128.0)), 0), 5632)
                c_start = min(max(int(round((o_lon_min - 90.0) * 128.0)), 0), 11519)
                c_end = min(max(int(round((o_lon_max - 90.0) * 128.0)), 0), 11520)

            if r_end > r_start and c_end > c_start:
                sub = mm[r_start:r_end, c_start:c_end]
                r_idx = np.linspace(0, sub.shape[0] - 1, height).astype(np.intp)
                c_idx = np.linspace(0, sub.shape[1] - 1, width).astype(np.intp)
                arr = sub[np.ix_(r_idx, c_idx)].astype(np.float32)

                nodata_mask = arr == -32768.0
                png_bytes = _render_turbo_rgba(arr, nodata_mask, vmin=-6000.0, vmax=4000.0, alpha_val=240)

                disp_res = ((lon_max_norm - lon_min_norm) * (3396190.0 * math.pi / 180.0)) / float(width)
                src_res = 463.08
                sampling_ratio = disp_res / src_res
                if sampling_ratio < 0.95:
                    sampling_regime = "oversampled_resampled_visualization"
                elif sampling_ratio > 1.05:
                    sampling_regime = "undersampled_decimated_overview"
                else:
                    sampling_regime = "native_matched"

                headers = {
                    "X-Source-Dataset": f"mola-megdr-128",
                    "X-Source-Resolution": "463.08 m/px",
                    "X-Display-Resolution": f"{disp_res:.2f} m/px",
                    "X-Sampling-Regime": sampling_regime,
                    "X-Sampling-Ratio": f"{sampling_ratio:.4f}",
                    "X-Output-Dimensions": f"{width}x{height}",
                    "X-Resampling-Method": "stride_subsample",
                    "X-Source-Checksum": t_sha,
                    "X-Geographic-Bounds": f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]",
                    "X-Cache-Status": "MISS",
                }
                if len(_WINDOW_CACHE) < _MAX_WINDOW_CACHE:
                    _WINDOW_CACHE[cache_key] = (png_bytes, headers)
                return Response(content=png_bytes, media_type="image/png", headers=headers)

    # 3. Fallback: Global MOLA 4 ppd windowed read
    cog_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "data",
            "processed",
            "mola",
            "mola_megt90n000cb_elevation.tif",
        )
    )
    with rasterio.open(cog_path) as mola4_src:
        from rasterio.windows import from_bounds

        win = from_bounds(lon_min_norm, min_lat, lon_max_norm, max_lat, mola4_src.transform)
        arr = mola4_src.read(
            1,
            window=win,
            out_shape=(height, width),
            resampling=Resampling.bilinear,
            boundless=True,
            fill_value=mola4_src.nodata,
        )
        nodata_mask = (arr == mola4_src.nodata) | ~np.isfinite(arr)
        png_bytes = _render_turbo_rgba(arr, nodata_mask, vmin=-8200.0, vmax=21200.0, alpha_val=230)

        disp_res = ((lon_max_norm - lon_min_norm) * (3396190.0 * math.pi / 180.0)) / float(width)
        src_res = 14818.67
        sampling_ratio = disp_res / src_res
        if sampling_ratio < 0.95:
            sampling_regime = "oversampled_resampled_visualization"
        elif sampling_ratio > 1.05:
            sampling_regime = "undersampled_decimated_overview"
        else:
            sampling_regime = "native_matched"

        headers = {
            "X-Source-Dataset": "mola-megdr-4",
            "X-Source-Resolution": "14818.67 m/px",
            "X-Display-Resolution": f"{disp_res:.2f} m/px",
            "X-Sampling-Regime": sampling_regime,
            "X-Sampling-Ratio": f"{sampling_ratio:.4f}",
            "X-Output-Dimensions": f"{width}x{height}",
            "X-Resampling-Method": "bilinear",
            "X-Source-Checksum": "25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c",
            "X-Geographic-Bounds": f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]",
            "X-Cache-Status": "MISS",
        }
        if len(_WINDOW_CACHE) < _MAX_WINDOW_CACHE:
            _WINDOW_CACHE[cache_key] = (png_bytes, headers)
        return Response(content=png_bytes, media_type="image/png", headers=headers)


@router.get("/render/window/metadata", response_model=WindowRenderMetadata)
async def get_window_render_metadata(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    width: int = Query(default=512),
    height: int = Query(default=512),
):
    """Retrieve metadata for a requested raster window."""
    lon_min_norm = min_lon % 360.0
    lon_max_norm = max_lon % 360.0
    if lon_max_norm < lon_min_norm:
        lon_max_norm += 360.0

    R_IAU = 3396190.0

    # 0. Check HiRISE Holden Crater overlap
    lon_180_min = lon_min_norm - 360.0 if lon_min_norm > 180.0 else lon_min_norm
    lon_180_max = lon_max_norm - 360.0 if lon_max_norm > 180.0 else lon_max_norm
    if lon_180_min > lon_180_max:
        lon_180_min, lon_180_max = lon_180_max, lon_180_min

    has_hirise_overlap = (
        not (max_lat < -28.66 or min_lat > -28.37 or lon_180_max < -51.03 or lon_180_min > -50.94)
        and (max_lat - min_lat <= 1.0)
    )
    if has_hirise_overlap:
        x_min = math.radians(lon_180_min) * R_IAU
        x_max = math.radians(lon_180_max) * R_IAU
        disp_res = (x_max - x_min) / float(width)
        src_res = 1.01
        ratio = disp_res / src_res
        regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
        return WindowRenderMetadata(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width=width,
            height=height,
            dataset_id="hirise-dtm-controlled-esp-011635",
            source_resolution_m=1.01,
            display_resolution_m=round(disp_res, 2),
            sampling_regime=regime,
            sampling_ratio=round(ratio, 4),
            resampling_method="bilinear",
            source_checksum="a3b3c22912b2b23675c1a91a6287200b2794f1f10cfb878c41aebc954ee655ad",
        )

    # 0B. Check Apollinaris Sulci CTX overlap
    has_t01_overlap = (
        not (max_lat < 4.44 or min_lat > 4.99 or lon_max_norm < 168.07 or lon_min_norm > 168.50)
        and (max_lat - min_lat <= 2.5)
    )
    if has_t01_overlap:
        x_min = math.radians(lon_min_norm) * R_IAU
        x_max = math.radians(lon_max_norm) * R_IAU
        disp_res = (x_max - x_min) / float(width)
        src_res = 20.0
        ratio = disp_res / src_res
        regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
        return WindowRenderMetadata(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width=width,
            height=height,
            dataset_id="ctx-dtm-controlled-t01-000893",
            source_resolution_m=20.0,
            display_resolution_m=round(disp_res, 2),
            sampling_regime=regime,
            sampling_ratio=round(ratio, 4),
            resampling_method="bilinear",
            source_checksum="4888a180ba6e868cb4fc0f33478723587499cf40e780af15983b615ce62f3c51",
        )

    has_ctx_overlap = (
        not (max_lat < -5.19 or min_lat > -4.01 or lon_max_norm < 66.03 or lon_min_norm > 66.61)
        and (max_lat - min_lat <= 2.5)
    )

    if has_ctx_overlap:
        R_IAU = 3396190.0
        x_min = math.radians(lon_min_norm) * R_IAU
        x_max = math.radians(lon_max_norm) * R_IAU
        disp_res = (x_max - x_min) / float(width)
        src_res = 20.0128
        ratio = disp_res / src_res
        regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
        return WindowRenderMetadata(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width=width,
            height=height,
            dataset_id="ctx-dtm-p21-009323",
            source_resolution_m=20.0128,
            display_resolution_m=round(disp_res, 2),
            sampling_regime=regime,
            sampling_ratio=round(ratio, 4),
            resampling_method="bilinear",
            source_checksum="a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2",
        )

    # Check MOLA 128 tiles
    mola128_tiles = [
        ("00n000", "megt00n000hb", -44.0, 0.0, 0.0, 90.0, "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"),
        ("44n000", "megt44n000hb", 0.0, 44.0, 0.0, 90.0, "14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36"),
        ("00n090", "megt00n090hb", -44.0, 0.0, 90.0, 180.0, "764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e"),
    ]
    for t_key, t_id, t_min_lat, t_max_lat, t_min_lon, t_max_lon, t_sha in mola128_tiles:
        overlap_lat_min = max(min_lat, t_min_lat)
        overlap_lat_max = min(max_lat, t_max_lat)
        overlap_lon_min = max(lon_min_norm, t_min_lon)
        overlap_lon_max = min(lon_max_norm, t_max_lon)
        if overlap_lat_max > overlap_lat_min and overlap_lon_max > overlap_lon_min:
            disp_res = ((lon_max_norm - lon_min_norm) * (3396190.0 * math.pi / 180.0)) / float(width)
            src_res = 463.08
            ratio = disp_res / src_res
            regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
            return WindowRenderMetadata(
                bbox=[min_lon, min_lat, max_lon, max_lat],
                width=width,
                height=height,
                dataset_id="mola-megdr-128",
                source_resolution_m=463.08,
                display_resolution_m=round(disp_res, 2),
                sampling_regime=regime,
                sampling_ratio=round(ratio, 4),
                resampling_method="stride_subsample",
                source_checksum=t_sha,
            )

    disp_res = ((lon_max_norm - lon_min_norm) * (3396190.0 * math.pi / 180.0)) / float(width)
    src_res = 14818.67
    ratio = disp_res / src_res
    regime = "oversampled_resampled_visualization" if ratio < 0.95 else ("undersampled_decimated_overview" if ratio > 1.05 else "native_matched")
    return WindowRenderMetadata(
        bbox=[min_lon, min_lat, max_lon, max_lat],
        width=width,
        height=height,
        dataset_id="mola-megdr-4",
        source_resolution_m=14818.67,
        display_resolution_m=round(disp_res, 2),
        sampling_regime=regime,
        sampling_ratio=round(ratio, 4),
        resampling_method="bilinear",
        source_checksum="25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c",
    )


