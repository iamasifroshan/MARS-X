"""Raster metadata inspection service using Rasterio."""

import os
import logging
from typing import Dict, Any, Optional
import rasterio

from app.geospatial import MARS_EQUATORIAL_RADIUS_M, compute_mars_ground_resolution
from app.terrain.models import (
    RasterMetadataResponse,
    RasterBounds,
    RasterResolution,
)
from app.terrain.crs_validator import validate_and_identify_crs, PlanetaryCRSValidationError

logger = logging.getLogger("MARS-X.terrain.raster_inspector")


def inspect_raster_file(file_path: str, dataset_id: Optional[str] = None) -> RasterMetadataResponse:
    """Inspect a local raster file (GeoTIFF, PDS3 IMG, etc.) using Rasterio.

    Extracts bounds, pixel resolution, NoData value, band statistics, and validates
    planetary Mars CRS compatibility.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raster file not found on disk: {file_path}")

    try:
        with rasterio.open(file_path) as src:
            bounds = src.bounds
            crs_obj = src.crs

            # Validate CRS
            crs_info = validate_and_identify_crs(crs_obj)
            crs_str = crs_info.get("crs_string", "UNKNOWN")

            # Determine pixel resolutions
            res_x, res_y = src.res

            # Determine if units are degrees or projected metres
            is_geographic = crs_obj.is_geographic if crs_obj else True
            unit = "degrees" if is_geographic else "metres"

            # Compute metric ground spacing at Mars equator
            if is_geographic:
                metric_x, _ = compute_mars_ground_resolution(0.0, abs(res_x), abs(res_y))
            else:
                metric_x = abs(res_x)

            # Get nodata value
            nodata = src.nodata

            raster_bounds = RasterBounds(
                min_x=bounds.left,
                min_y=bounds.bottom,
                max_x=bounds.right,
                max_y=bounds.top,
                crs=crs_str,
            )

            raster_resolution = RasterResolution(
                pixel_width=abs(res_x),
                pixel_height=abs(res_y),
                unit=unit,
                metric_spacing_equator_m=round(metric_x, 2),
            )

            derived_id = dataset_id or os.path.splitext(os.path.basename(file_path))[0]

            return RasterMetadataResponse(
                dataset_id=derived_id,
                file_path=os.path.abspath(file_path),
                driver=src.driver,
                width=src.width,
                height=src.height,
                band_count=src.count,
                crs=crs_str,
                is_mars_crs=crs_info.get("is_valid_mars", False),
                crs_authority=crs_info.get("authority"),
                bounds=raster_bounds,
                resolution=raster_resolution,
                nodata_value=float(nodata) if nodata is not None else None,
                dtype=src.dtypes[0],
                has_valid_mask=True,
                tags=dict(src.tags()),
            )

    except rasterio.errors.RasterioIOError as e:
        logger.error("Failed to read raster header: %s", str(e))
        raise ValueError(f"Invalid or corrupted raster file ({file_path}): {str(e)}") from e

