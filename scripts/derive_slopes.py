"""Derive slope rasters from CTX and HiRISE DTMs.

Produces derived slope GeoTIFFs stored separately from source rasters.
Uses Horn (1981) weighted 3x3 gradient with latitude-corrected metric spacing.

Scientific constraints:
- NoData in any 3x3 neighbourhood → slope = NoData (never zero).
- Pixel spacing computed from actual raster geotransform in projected metres.
- Source DEM files are never modified.
- Output stored in data/processed/{ctx,hirise}/.
"""

import math
import os
import sys
import hashlib
import logging
import numpy as np
import rasterio
from rasterio.transform import Affine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("derive_slopes")

# Mars sphere radius for geographic→metric conversions (IAU2000)
MARS_RADIUS_M = 3_396_190.0
NODATA_OUT = -32767.0


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_slope_horn_projected(elevation: np.ndarray, pixel_x_m: float, pixel_y_m: float,
                                  nodata_val: float) -> np.ndarray:
    """Vectorised Horn 3×3 slope in degrees over a projected-metre raster.

    Both x and y spacings are in physical metres (from IAU:49910 equirectangular
    projection at standard parallel 0°), so no latitude correction is needed
    — the projection already handles it.

    NoData propagation: any NaN or nodata sentinel in the 3×3 stencil → NaN output.
    """
    rows, cols = elevation.shape
    elev = elevation.astype(np.float64)

    # Replace nodata sentinels with NaN
    elev[np.isclose(elev, nodata_val, rtol=1e-5, atol=1.0)] = np.nan
    # Clamp extreme outliers (outside Martian topographic bounds)
    elev[elev < -12_000.0] = np.nan
    elev[elev > 26_000.0] = np.nan

    slope_deg = np.full((rows, cols), np.nan, dtype=np.float32)

    if rows < 3 or cols < 3:
        logger.warning("Raster smaller than 3×3 — cannot compute slope.")
        return slope_deg

    # 3×3 Horn stencil
    z1 = elev[0:-2, 0:-2]; z2 = elev[0:-2, 1:-1]; z3 = elev[0:-2, 2:]
    z4 = elev[1:-1, 0:-2];                          z6 = elev[1:-1, 2:]
    z7 = elev[2:,   0:-2]; z8 = elev[2:,   1:-1];  z9 = elev[2:,   2:]

    # Stencil validity: all 8 neighbours + centre must be finite
    stencil_valid = (
        np.isfinite(z1) & np.isfinite(z2) & np.isfinite(z3) &
        np.isfinite(z4) & np.isfinite(elev[1:-1, 1:-1]) & np.isfinite(z6) &
        np.isfinite(z7) & np.isfinite(z8) & np.isfinite(z9)
    )

    dx = float(pixel_x_m)
    dy = float(pixel_y_m)

    dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx)
    dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy)

    grad = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    calc = np.degrees(np.arctan(grad)).astype(np.float32)

    slope_deg[1:-1, 1:-1] = np.where(stencil_valid, calc, np.nan)
    return slope_deg


def compute_slope_geographic_horn(elevation: np.ndarray, dlon_deg: float, dlat_deg: float,
                                   center_lat_deg: float, nodata_val: float) -> np.ndarray:
    """Horn slope for a geographic (lon/lat degree) raster with latitude-corrected dx.

    Used for MOLA 4ppd global raster which is in geographic CRS (not projected metres).
    dx = R * cos(lat) * dlon_rad  (varies with latitude)
    dy = R * dlat_rad (constant for cylindrical)
    """
    rows, cols = elevation.shape
    elev = elevation.astype(np.float64)
    elev[np.isclose(elev, nodata_val, rtol=1e-5, atol=1.0)] = np.nan
    elev[elev < -12_000.0] = np.nan
    elev[elev > 26_000.0] = np.nan

    slope_deg = np.full((rows, cols), np.nan, dtype=np.float32)
    if rows < 3 or cols < 3:
        return slope_deg

    dy_m = (math.pi / 180.0) * MARS_RADIUS_M * abs(dlat_deg)

    z1 = elev[0:-2, 0:-2]; z2 = elev[0:-2, 1:-1]; z3 = elev[0:-2, 2:]
    z4 = elev[1:-1, 0:-2];                          z6 = elev[1:-1, 2:]
    z7 = elev[2:,   0:-2]; z8 = elev[2:,   1:-1];  z9 = elev[2:,   2:]

    stencil_valid = (
        np.isfinite(z1) & np.isfinite(z2) & np.isfinite(z3) &
        np.isfinite(z4) & np.isfinite(elev[1:-1, 1:-1]) & np.isfinite(z6) &
        np.isfinite(z7) & np.isfinite(z8) & np.isfinite(z9)
    )

    # Latitude for each row's centre (approximate as centre row)
    # We vectorise over latitudes row-by-row via broadcasting
    nrows_inner = rows - 2
    # Latitude of row i (0-indexed from top)
    top_lat = center_lat_deg + ((rows / 2.0) - 1.5) * abs(dlat_deg)
    lats = np.array([top_lat - r * abs(dlat_deg) for r in range(nrows_inner)])  # shape (nrows_inner,)
    cos_lat = np.cos(np.radians(lats))  # shape (nrows_inner,)
    dx_m_per_row = (math.pi / 180.0) * MARS_RADIUS_M * abs(dlon_deg) * cos_lat  # (nrows_inner,)
    dx_m_per_row = np.maximum(dx_m_per_row, 1e-6)

    # Broadcast dx across columns
    dx_m = dx_m_per_row[:, np.newaxis]  # (nrows_inner, 1)

    dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx_m)
    dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy_m)

    grad = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    calc = np.degrees(np.arctan(grad)).astype(np.float32)
    slope_deg[1:-1, 1:-1] = np.where(stencil_valid, calc, np.nan)
    return slope_deg


def write_slope_raster(src_path: str, slope: np.ndarray, out_path: str, nodata: float) -> None:
    slope_out = slope.copy()
    slope_out[np.isnan(slope_out)] = nodata
    with rasterio.open(src_path) as src:
        profile = src.profile.copy()
    profile.update(
        dtype="float32",
        count=1,
        nodata=nodata,
        compress="deflate",
        predictor=2,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(slope_out.astype("float32"), 1)
        dst.update_tags(
            SLOPE_ALGORITHM="Horn (1981) 3x3 weighted gradient",
            SLOPE_UNITS="degrees",
            SLOPE_NODATA=str(nodata),
            SOURCE_RASTER=os.path.basename(src_path),
            SOURCE_CRS=str(profile.get("crs", "unknown")),
            VERTICAL_DATUM="MOLA Areoid (areoid_height)",
            DISCLAIMER="Slope is a derived analytical product. It does NOT assess astronaut safety.",
        )
    logger.info("Written slope raster: %s", out_path)


def derive_ctx_slope(src_path: str, out_path: str) -> dict:
    """Derive slope for a CTX DTM in IAU:49910 equirectangular (metre-projected) CRS."""
    with rasterio.open(src_path) as src:
        elev = src.read(1)
        transform = src.transform
        nodata = src.nodata if src.nodata is not None else -32767.0
        pixel_x_m = abs(transform.a)   # pixel width in metres
        pixel_y_m = abs(transform.e)   # pixel height in metres

    logger.info("Deriving CTX slope: %s (%.4f m/px)", src_path, pixel_x_m)
    slope = compute_slope_horn_projected(elev, pixel_x_m, pixel_y_m, nodata)
    write_slope_raster(src_path, slope, out_path, NODATA_OUT)

    valid = slope[~np.isnan(slope)]
    return {
        "source": src_path,
        "output": out_path,
        "pixel_x_m": round(pixel_x_m, 4),
        "pixel_y_m": round(pixel_y_m, 4),
        "slope_min_deg": round(float(valid.min()), 3) if len(valid) else None,
        "slope_max_deg": round(float(valid.max()), 3) if len(valid) else None,
        "slope_mean_deg": round(float(valid.mean()), 3) if len(valid) else None,
        "valid_cells": int(len(valid)),
        "nodata_cells": int(np.isnan(slope).sum()),
        "source_sha256": sha256_file(src_path),
        "output_sha256": sha256_file(out_path),
    }


def derive_hirise_slope(src_path: str, out_path: str) -> dict:
    """Derive slope for HiRISE DTM in IAU:49910 equirectangular (metre-projected) CRS."""
    with rasterio.open(src_path) as src:
        elev = src.read(1)
        transform = src.transform
        nodata = src.nodata if src.nodata is not None else -3.4028235e+38
        pixel_x_m = abs(transform.a)
        pixel_y_m = abs(transform.e)

    logger.info("Deriving HiRISE slope: %s (%.4f m/px)", src_path, pixel_x_m)
    slope = compute_slope_horn_projected(elev, pixel_x_m, pixel_y_m, nodata)
    write_slope_raster(src_path, slope, out_path, NODATA_OUT)

    valid = slope[~np.isnan(slope)]
    return {
        "source": src_path,
        "output": out_path,
        "pixel_x_m": round(pixel_x_m, 4),
        "pixel_y_m": round(pixel_y_m, 4),
        "slope_min_deg": round(float(valid.min()), 3) if len(valid) else None,
        "slope_max_deg": round(float(valid.max()), 3) if len(valid) else None,
        "slope_mean_deg": round(float(valid.mean()), 3) if len(valid) else None,
        "valid_cells": int(len(valid)),
        "nodata_cells": int(np.isnan(slope).sum()),
        "source_sha256": sha256_file(src_path),
        "output_sha256": sha256_file(out_path),
    }


if __name__ == "__main__":
    results = {}

    # CTX Tyrrhena Terra
    ctx_tyrrhena_src = "data/raw/ctx/P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"
    ctx_tyrrhena_out = "data/derived/traversability/tyrrhena_slope.tif"
    if os.path.exists(ctx_tyrrhena_src):
        results["tyrrhena_ctx"] = derive_ctx_slope(ctx_tyrrhena_src, ctx_tyrrhena_out)
    else:
        logger.error("CTX Tyrrhena source not found: %s", ctx_tyrrhena_src)

    # CTX Apollinaris Sulci
    ctx_apollinaris_src = "data/originals/ctx/T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif"
    ctx_apollinaris_out = "data/derived/traversability/apollinaris_slope.tif"
    if os.path.exists(ctx_apollinaris_src):
        results["apollinaris_ctx"] = derive_ctx_slope(ctx_apollinaris_src, ctx_apollinaris_out)
    else:
        logger.error("CTX Apollinaris source not found: %s", ctx_apollinaris_src)

    # HiRISE Holden Crater
    hirise_src = "data/originals/hirise/DTEEC_011635_1510_029542_1510_A01.tif"
    hirise_out = "data/derived/traversability/holden_slope.tif"
    if os.path.exists(hirise_src):
        results["holden_hirise"] = derive_hirise_slope(hirise_src, hirise_out)
    else:
        logger.error("HiRISE Holden source not found: %s", hirise_src)

    print("\n=== SLOPE DERIVATION RESULTS ===")
    for key, r in results.items():
        print(f"\n{key}:")
        for k, v in r.items():
            print(f"  {k}: {v}")
