"""CRS identification, validation, and projection parsing for Martian terrain datasets."""

import logging
from typing import Dict, Any, Tuple
import rasterio.crs

from app.geospatial import (
    CRS_REGISTRY,
    MARS_EQUATORIAL_RADIUS_M,
    MARS_POLAR_RADIUS_M,
    CRS_EARTH_WEB_MERCATOR,
    is_valid_mars_crs,
)

logger = logging.getLogger("MARS-X.terrain.crs_validator")


class PlanetaryCRSValidationError(Exception):
    """Raised when an invalid, non-Martian, or unsupported coordinate reference system is encountered."""
    pass


def validate_and_identify_crs(crs_input: Any) -> Dict[str, Any]:
    """Inspect and validate a CRS string, dict, or rasterio.crs.CRS object.

    Verifies planetary Mars compatibility and rejects Earth-only systems (e.g., EPSG:3857).
    """
    if crs_input is None:
        return {
            "is_valid_mars": False,
            "crs_string": "UNKNOWN",
            "authority": None,
            "error": "No CRS defined in dataset metadata",
        }

    crs_str = str(crs_input).strip()

    # Reject Earth Web Mercator strictly
    if CRS_EARTH_WEB_MERCATOR in crs_str or "3857" in crs_str:
        raise PlanetaryCRSValidationError(
            f"Detected terrestrial Web Mercator ({CRS_EARTH_WEB_MERCATOR}). "
            "Earth projections cannot be used for Martian terrain without severe scientific distortion."
        )

    # Check direct registry lookup
    upper_crs = crs_str.upper()
    for reg_key, reg_info in CRS_REGISTRY.items():
        if reg_key.upper() in upper_crs or reg_key.replace(":", "").upper() in upper_crs.replace(":", ""):
            return {
                "is_valid_mars": True,
                "crs_string": reg_key,
                "name": reg_info["name"],
                "authority": reg_info.get("authority", "IAU"),
                "semi_major_axis_m": reg_info.get("semi_major_axis_m", MARS_EQUATORIAL_RADIUS_M),
                "semi_minor_axis_m": reg_info.get("semi_minor_axis_m", MARS_POLAR_RADIUS_M),
                "notes": reg_info.get("notes", ""),
            }

    # Inspect rasterio CRS if object provided
    if isinstance(crs_input, rasterio.crs.CRS):
        if crs_input.is_geographic or crs_input.is_projected:
            # Check datum / ellipsoid parameters for Mars radii (~3396 km)
            wkt = crs_input.to_wkt()
            if "Mars" in wkt or "3396190" in wkt or "49900" in wkt:
                return {
                    "is_valid_mars": True,
                    "crs_string": crs_input.to_string(),
                    "name": "Mars Coordinate Reference System",
                    "authority": "IAU/Rasterio",
                    "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
                    "semi_minor_axis_m": MARS_POLAR_RADIUS_M,
                    "notes": "Validated via Rasterio Mars ellipsoid parameters in WKT.",
                }

    # Fallback: check if the string matches valid Mars CRS
    if is_valid_mars_crs(crs_str):
        return {
            "is_valid_mars": True,
            "crs_string": crs_str,
            "authority": "Planetary",
            "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
            "semi_minor_axis_m": MARS_POLAR_RADIUS_M,
            "notes": "Recognized Martian planetary system.",
        }

    return {
        "is_valid_mars": False,
        "crs_string": crs_str,
        "authority": None,
        "error": f"CRS '{crs_str}' is not recognized as an authoritative Mars planetary reference system.",
    }

