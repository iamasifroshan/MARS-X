"""Cloud Optimized GeoTIFF (COG) generation pipeline for Martian raster data.

Preserves native source elevation, applies power-of-two overviews, internal tiling,
and embeds planetary coordinate reference system (IAU:49900) without artificial upsampling.
"""

import os
import logging
from typing import Dict, Any, Optional
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling

logger = logging.getLogger("MARS-X.terrain.cog_converter")


def convert_array_to_cog(
    elevation_data: np.ndarray,
    output_tif_path: str,
    west_lon: float,
    max_lat: float,
    pixel_size_x_deg: float,
    pixel_size_y_deg: float,
    nodata_value: float = -32768.0,
    mars_crs_proj4: str = "+proj=longlat +a=3396190 +b=3396190 +no_defs",
    generate_overviews: bool = True,
    block_size: int = 256,
) -> Dict[str, Any]:
    """Write a 2D NumPy elevation array into a Cloud Optimized GeoTIFF (COG).

    Parameters:
        elevation_data: 2D array of heights in metres
        output_tif_path: Destination path on disk
        west_lon: Western boundary in positive-East degrees
        max_lat: Northern boundary in degrees
        pixel_size_x_deg: Pixel width in degrees
        pixel_size_y_deg: Pixel height in degrees
        nodata_value: Missing value sentinel (default -32768.0)
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_tif_path)), exist_ok=True)

    rows, cols = elevation_data.shape
    transform = from_origin(west_lon, max_lat, abs(pixel_size_x_deg), abs(pixel_size_y_deg))
    crs = rasterio.crs.CRS.from_proj4(mars_crs_proj4)

    # Determine optimal block size (cannot exceed image dimensions)
    bx = min(block_size, 1 << (cols.bit_length() - 1)) if cols >= 64 else cols
    by = min(block_size, 1 << (rows.bit_length() - 1)) if rows >= 64 else rows

    # Profile for Cloud-Optimized GeoTIFF layout
    profile = {
        "driver": "GTiff",
        "height": rows,
        "width": cols,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": nodata_value,
        "tiled": True,
        "blockxsize": bx,
        "blockysize": by,
        "compress": "deflate",
        "interleave": "band",
    }

    # Ensure float32 with preserved NoData
    out_arr = elevation_data.astype(np.float32)

    with rasterio.open(output_tif_path, "w", **profile) as dst:
        dst.write(out_arr, 1)

        if generate_overviews and rows >= 128 and cols >= 128:
            factors = [2, 4, 8]
            dst.build_overviews(factors, Resampling.nearest)
            dst.update_tags(ns="rio_overview", resampling="nearest")

    file_size_bytes = os.path.getsize(output_tif_path)
    logger.info("Generated COG: %s (%.2f MB)", output_tif_path, file_size_bytes / (1024 * 1024))

    return {
        "output_path": os.path.abspath(output_tif_path),
        "file_size_bytes": file_size_bytes,
        "width": cols,
        "height": rows,
        "tiled": True,
        "block_size": (bx, by),
        "crs": mars_crs_proj4,
        "nodata_value": nodata_value,
        "compression": "deflate",
    }

