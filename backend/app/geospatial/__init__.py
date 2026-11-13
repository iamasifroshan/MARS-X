"""Geospatial package for MARS-X.

Provides planetary coordinate reference system (CRS) constants,
transformation utilities, and planetary projection boundaries for Mars.
"""

from typing import Dict, Any

# Mars ellipsoid constants (IAU 2000 / 2015 recommendations)
MARS_EQUATORIAL_RADIUS_M = 3396190.0
MARS_POLAR_RADIUS_M = 3376200.0
MARS_MEAN_RADIUS_M = 3389500.0

# Mars CRS Identifiers
CRS_IAU_2000_SPHERE = "IAU:49900"
CRS_EPSG_104905 = "EPSG:104905"  # Mars 2000 / Equirectangular Mars (Mars Trek WMTS)
CRS_EARTH_WEB_MERCATOR = "EPSG:3857"  # Strictly Earth-only, NOT compatible with Mars

CRS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "IAU:49900": {
        "name": "Mars (2000) - Sphere",
        "type": "Geographic 2D",
        "datum": "Mars 2000",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "inverse_flattening": 0.0,
        "notes": "Spherical approximation used by MOLA MEGDR and standard global maps."
    },
    "EPSG:104905": {
        "name": "Mars 2000 / Equidistant Cylindrical / Equirectangular",
        "type": "Projected",
        "datum": "Mars 2000",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_POLAR_RADIUS_M,
        "inverse_flattening": 169.8,
        "standard_parallel": 0.0,
        "notes": "Native projection for NASA Mars Trek WMTS tile server. Requires custom projection matrix in web viewers."
    }
}


def is_valid_mars_crs(crs_code: str) -> bool:
    """Validate whether a CRS code belongs to registered planetary Mars systems."""
    return crs_code.upper() in CRS_REGISTRY
