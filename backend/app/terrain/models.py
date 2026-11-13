"""Pydantic data models for MARS-X terrain and raster ingestion."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RasterBounds(BaseModel):
    """Geographic or projected bounding coordinates."""
    min_x: float = Field(..., description="Westernmost longitude or minimum X")
    min_y: float = Field(..., description="Southernmost latitude or minimum Y")
    max_x: float = Field(..., description="Easternmost longitude or maximum X")
    max_y: float = Field(..., description="Northernmost latitude or maximum Y")
    crs: str = Field(..., description="Coordinate reference system identifier")


class RasterResolution(BaseModel):
    """Pixel resolution and physical metric spacing."""
    pixel_width: float = Field(..., description="Pixel dimension along X axis in CRS units")
    pixel_height: float = Field(..., description="Pixel dimension along Y axis in CRS units")
    unit: str = Field("degrees", description="CRS units: degrees or metres")
    metric_spacing_equator_m: Optional[float] = Field(None, description="Equivalent ground spacing at Mars equator in metres")


class RasterMetadataResponse(BaseModel):
    """Inspected raster attributes from GDAL/Rasterio headers."""
    dataset_id: str
    file_path: Optional[str] = None
    driver: str
    width: int
    height: int
    band_count: int
    crs: str
    is_mars_crs: bool
    crs_authority: Optional[str] = None
    bounds: RasterBounds
    resolution: RasterResolution
    nodata_value: Optional[float] = None
    dtype: str
    has_valid_mask: bool = True
    tags: Dict[str, str] = Field(default_factory=dict)


class RasterCoverageResponse(BaseModel):
    """Geographic footprint and coverage extent on Mars."""
    dataset_id: str
    is_global: bool
    lat_min: float = Field(..., ge=-90.0, le=90.0)
    lat_max: float = Field(..., ge=-90.0, le=90.0)
    lon_min: float = Field(..., ge=0.0, le=360.0)
    lon_max: float = Field(..., ge=0.0, le=360.0)
    crs: str
    total_area_approx_pct: float = Field(..., ge=0.0, le=100.0, description="Approximate percentage of Martian surface covered")
    notes: str


class TerrainSummaryResponse(BaseModel):
    """High-level summary of a registered or loaded terrain dataset."""
    dataset_id: str
    name: str
    mission: str
    instrument: str
    product_type: str
    status: str
    elevation_unit: str = "metres relative to MOLA Areoid"
    native_resolution_desc: str
    is_numerical_dtm: bool
    coverage: str
    nodata_value_repr: str
    scientific_limitations: str
    provenance_source: str


class ElevationPointQuery(BaseModel):
    """Single-point elevation query."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Planetocentric latitude in degrees")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="East longitude in degrees")
    dataset_id: str = Field("mola-megdr", description="Target terrain dataset ID")


class ElevationPointResult(BaseModel):
    """Elevation query response with validity verification."""
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    dataset_id: str
    is_valid: bool
    status_note: str


class SlopeMetricResult(BaseModel):
    """Slope analysis metrics over a defined grid or subregion."""
    dataset_id: str
    algorithm: str
    min_slope_deg: Optional[float] = None
    max_slope_deg: Optional[float] = None
    mean_slope_deg: Optional[float] = None
    valid_cells: int
    nodata_cells: int
    scientific_note: str

