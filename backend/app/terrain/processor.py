"""Martian terrain processing engine: slope, roughness, uncertainty, and valid-data masking.

Scientific Constraint:
Missing elevation values (NoData) must NEVER be treated as zero or safe terrain.
Any calculation window containing invalid pixels must mark output as invalid/NaN.
Physical cell width must adjust for latitude: dx = R * cos(lat) * dlon.
"""

import math
import logging
from typing import Tuple, Optional, Dict, Any
import numpy as np

from app.geospatial import MARS_EQUATORIAL_RADIUS_M, MARS_POLAR_RADIUS_M

logger = logging.getLogger("MARS-X.terrain.processor")


def create_valid_data_mask(
    data: np.ndarray,
    nodata_value: Optional[float] = None
) -> np.ndarray:
    """Generate a boolean mask where True indicates scientifically valid elevation data.

    Criteria for True:
    - Finite (not NaN, not +Inf, not -Inf)
    - If nodata_value is defined: absolute difference > tolerance
    - Reasonable Martian topographic limits: -10,000 m (Hellas floor) to +25,000 m (Olympus Mons summit)
    """
    mask = np.isfinite(data)

    if nodata_value is not None:
        if np.isnan(nodata_value):
            mask &= ~np.isnan(data)
        else:
            # Check for approximate equality for floating-point NoData (e.g., -32768.0, -3.40282e+38)
            mask &= ~np.isclose(data, nodata_value, atol=1e-3, rtol=1e-5)
            mask &= (data != nodata_value)

    # Filter out extreme unphysical outliers beyond Martian geoid limits
    mask &= (data >= -12000.0) & (data <= 26000.0)
    return mask


def compute_latitudinal_metric_spacing(
    center_lat_deg: float,
    dlon_deg: float,
    dlat_deg: float
) -> Tuple[float, float]:
    """Compute physical cell dimensions in metres at a specific Martian latitude.

    Accounts for the convergence of meridians in cylindrical projections.
    """
    lat_rad = math.radians(center_lat_deg)
    dx_m = (math.pi * MARS_EQUATORIAL_RADIUS_M / 180.0) * math.cos(lat_rad) * abs(dlon_deg)
    dy_m = (math.pi * MARS_POLAR_RADIUS_M / 180.0) * abs(dlat_deg)
    return max(dx_m, 1e-6), max(dy_m, 1e-6)


def calculate_slope_grid(
    elevation: np.ndarray,
    dx_m: float,
    dy_m: float,
    valid_mask: Optional[np.ndarray] = None,
    algorithm: str = "horn"
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate topographic slope angle in degrees across a 2D elevation grid.

    Scientific safeguards:
    - Never treats missing values as zero.
    - If any neighbor in the 3x3 stencil is invalid, the output slope is set to NaN.
    - Returns (slope_degrees, valid_slope_mask)
    """
    if elevation.ndim != 2:
        raise ValueError(f"Elevation grid must be 2-dimensional; received shape {elevation.shape}")

    rows, cols = elevation.shape
    slope_deg = np.full((rows, cols), np.nan, dtype=np.float32)

    if rows < 3 or cols < 3:
        return slope_deg, np.zeros((rows, cols), dtype=bool)

    if valid_mask is None:
        valid_mask = np.isfinite(elevation)

    # 3x3 neighborhood slices
    z1 = elevation[0:-2, 0:-2]
    z2 = elevation[0:-2, 1:-1]
    z3 = elevation[0:-2, 2:]

    z4 = elevation[1:-1, 0:-2]
    z6 = elevation[1:-1, 2:]

    z7 = elevation[2:, 0:-2]
    z8 = elevation[2:, 1:-1]
    z9 = elevation[2:, 2:]

    # Validity mask across all 8 neighbors plus center
    stencil_valid = (
        valid_mask[0:-2, 0:-2] & valid_mask[0:-2, 1:-1] & valid_mask[0:-2, 2:] &
        valid_mask[1:-1, 0:-2] & valid_mask[1:-1, 1:-1] & valid_mask[1:-1, 2:] &
        valid_mask[2:, 0:-2]   & valid_mask[2:, 1:-1]   & valid_mask[2:, 2:]
    )

    if algorithm.lower() == "horn":
        # Horn's 3x3 weighted finite-difference formulation
        dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx_m)
        dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy_m)
    else:
        # Simple central difference
        dz_dx = (z6 - z4) / (2.0 * dx_m)
        dz_dy = (z8 - z2) / (2.0 * dy_m)

    gradient = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    slope_rad = np.arctan(gradient)
    calculated_deg = np.degrees(slope_rad)

    # Apply only where the full 3x3 neighborhood has valid data
    slope_deg[1:-1, 1:-1] = np.where(stencil_valid, calculated_deg, np.nan)
    valid_slope_mask = stencil_valid & np.isfinite(slope_deg[1:-1, 1:-1])

    full_valid_mask = np.zeros((rows, cols), dtype=bool)
    full_valid_mask[1:-1, 1:-1] = valid_slope_mask

    return slope_deg, full_valid_mask


def calculate_terrain_roughness(
    elevation: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    window_size: int = 3
) -> np.ndarray:
    """Compute terrain roughness (local standard deviation of elevation) in metres.

    Cells with invalid data or incomplete neighborhood are set to NaN.
    """
    if elevation.ndim != 2:
        raise ValueError(f"Elevation grid must be 2D; received {elevation.shape}")

    rows, cols = elevation.shape
    roughness = np.full((rows, cols), np.nan, dtype=np.float32)

    if valid_mask is None:
        valid_mask = np.isfinite(elevation)

    half = window_size // 2
    for r in range(half, rows - half):
        for c in range(half, cols - half):
            patch = elevation[r - half : r + half + 1, c - half : c + half + 1]
            p_mask = valid_mask[r - half : r + half + 1, c - half : c + half + 1]
            if np.all(p_mask):
                roughness[r, c] = float(np.std(patch))

    return roughness


def estimate_instrument_uncertainty(
    dataset_id: str,
    elevation: np.ndarray,
    slope_deg: np.ndarray
) -> Dict[str, Any]:
    """Provide estimated elevation and slope measurement uncertainty for a given dataset."""
    d_id = dataset_id.lower()
    if "mola" in d_id:
        # MOLA vertical precision is ~1 m on flat plains, ~10 m on 15° slopes
        return {
            "dataset_id": dataset_id,
            "nominal_vertical_precision_m": "±1.0 m (smooth plains) to ±10.0 m (rough terrain)",
            "gradient_uncertainty_note": "Degrades on slopes > 5° due to laser pulse broadening within 168m footprint.",
            "interpolation_uncertainty": "Regional gaps up to 2–5 km interpolated between altimeter ground tracks."
        }
    elif "hrsc" in d_id:
        return {
            "dataset_id": dataset_id,
            "nominal_vertical_precision_m": "±10.0 m to ±40.0 m",
            "gradient_uncertainty_note": "Dependent on stereo base-to-height ratio (B/H ~ 0.3) and visual texture contrast.",
            "interpolation_uncertainty": "Stereo correlation dropouts occur over featureless dust blankets."
        }
    elif "hirise" in d_id:
        return {
            "dataset_id": dataset_id,
            "nominal_vertical_precision_m": "±0.2 m to ±0.5 m",
            "gradient_uncertainty_note": "High-precision relative microtopography; absolute tie-in to MOLA Areoid may have systematic ~1–5m vertical shift.",
            "interpolation_uncertainty": "Artifacts present near shadow boundaries and steep escarpments."
        }
    return {
        "dataset_id": dataset_id,
        "nominal_vertical_precision_m": "Unspecified",
        "gradient_uncertainty_note": "Calibration documentation not found.",
        "interpolation_uncertainty": "Unknown."
    }

