"""Terrain package for MARS-X.

Provides modular architectures for:
- Raster metadata inspection (Rasterio)
- CRS identification and validation for Mars
- Raster coverage inspection and boundaries
- NoData and valid-data mask handling (NumPy)
- Pixel resolution reporting and metric spacing conversion
- Elevation data ingestion and sampling
- Raster dataset provenance tracking
- Slope and roughness processing
"""

from app.terrain.models import (
    RasterBounds,
    RasterResolution,
    RasterMetadataResponse,
    RasterCoverageResponse,
    TerrainSummaryResponse,
    ElevationPointQuery,
    ElevationPointResult,
    SlopeMetricResult,
)
from app.terrain.crs_validator import (
    validate_and_identify_crs,
    PlanetaryCRSValidationError,
)
from app.terrain.raster_inspector import inspect_raster_file
from app.terrain.processor import (
    create_valid_data_mask,
    calculate_slope_grid,
    calculate_terrain_roughness,
    compute_latitudinal_metric_spacing,
    estimate_instrument_uncertainty,
)
from app.terrain.provenance import (
    list_terrain_datasets,
    get_terrain_dataset_coverage,
    get_terrain_dataset_summary,
    TERRAIN_DATASET_PROVENANCE,
)
from app.terrain.elevation_service import (
    TerrainDataEngine,
    engine,
)

__all__ = [
    "RasterBounds",
    "RasterResolution",
    "RasterMetadataResponse",
    "RasterCoverageResponse",
    "TerrainSummaryResponse",
    "ElevationPointQuery",
    "ElevationPointResult",
    "SlopeMetricResult",
    "validate_and_identify_crs",
    "PlanetaryCRSValidationError",
    "inspect_raster_file",
    "create_valid_data_mask",
    "calculate_slope_grid",
    "calculate_terrain_roughness",
    "compute_latitudinal_metric_spacing",
    "estimate_instrument_uncertainty",
    "list_terrain_datasets",
    "get_terrain_dataset_coverage",
    "get_terrain_dataset_summary",
    "TERRAIN_DATASET_PROVENANCE",
    "TerrainDataEngine",
    "engine",
]
