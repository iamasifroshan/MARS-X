"""Geospatial package for MARS-X.

Provides planetary coordinate reference system (CRS) constants,
transformation utilities, geodetic conversions, and planetary projection boundaries for Mars.
"""

import math
from typing import Dict, Any, Optional, Tuple

# Mars ellipsoid constants (IAU 2000 / 2015 recommendations)
MARS_EQUATORIAL_RADIUS_M = 3396190.0
MARS_POLAR_RADIUS_M = 3376200.0
MARS_MEAN_RADIUS_M = 3389500.0

# Derived parameters
MARS_FLATTENING = (MARS_EQUATORIAL_RADIUS_M - MARS_POLAR_RADIUS_M) / MARS_EQUATORIAL_RADIUS_M  # ~1 / 169.81
MARS_ECCENTRICITY_SQ = 2 * MARS_FLATTENING - MARS_FLATTENING ** 2

# Mars CRS Identifiers & Authorities
CRS_IAU_2000_SPHERE = "IAU:49900"
CRS_IAU_2015_SPHERE = "IAU_2015:49900"
CRS_ESRI_104905 = "ESRI:104905"
CRS_EPSG_104905_ALIAS = "EPSG:104905"  # De facto alias used by NASA Mars Trek WMTS
CRS_EARTH_WEB_MERCATOR = "EPSG:3857"   # Strictly Earth-only, NOT compatible with Mars

CRS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "IAU:49900": {
        "name": "Mars (2000) - Sphere",
        "authority": "IAU",
        "code": "49900",
        "type": "Geographic 2D",
        "datum": "Mars 2000",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "inverse_flattening": 0.0,
        "proj4": "+proj=longlat +a=3396190 +b=3396190 +no_defs",
        "notes": "Spherical approximation used by MOLA MEGDR and standard global maps."
    },
    "IAU_2015:49900": {
        "name": "Mars (2015) - Sphere",
        "authority": "IAU_2015",
        "code": "49900",
        "type": "Geographic 2D",
        "datum": "Mars 2015",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "inverse_flattening": 0.0,
        "proj4": "+proj=longlat +a=3396190 +b=3396190 +no_defs",
        "notes": "Modern IAU 2015 recommended sphere code."
    },
    "ESRI:104905": {
        "name": "Mars 2000 Equidistant Cylindrical",
        "authority": "ESRI",
        "code": "104905",
        "type": "Projected",
        "datum": "Mars 2000",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_POLAR_RADIUS_M,
        "inverse_flattening": 169.81,
        "standard_parallel": 0.0,
        "proj4": "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +a=3396190 +b=3376200 +units=m +no_defs",
        "notes": "Native projection for NASA Mars Trek WMTS tile server. Requires custom projection matrix in web viewers."
    },
    "EPSG:104905": {
        "name": "Mars 2000 Equidistant Cylindrical (NASA Mars Trek WMTS alias)",
        "authority": "EPSG (Alias)",
        "code": "104905",
        "type": "Projected",
        "alias_of": "ESRI:104905",
        "datum": "Mars 2000",
        "semi_major_axis_m": MARS_EQUATORIAL_RADIUS_M,
        "semi_minor_axis_m": MARS_POLAR_RADIUS_M,
        "inverse_flattening": 169.81,
        "notes": "De facto alias adopted in NASA Mars Trek GetCapabilities XML for ESRI:104905."
    }
}


def is_valid_mars_crs(crs_code: str) -> bool:
    """Validate whether a CRS code belongs to registered planetary Mars systems."""
    normalized = crs_code.strip().upper()
    return normalized in CRS_REGISTRY or normalized.replace(" ", "") in CRS_REGISTRY


def get_mars_crs_info(crs_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a registered Mars CRS code."""
    normalized = crs_code.strip().upper()
    return CRS_REGISTRY.get(normalized)


def planetocentric_to_planetographic(lat_c_deg: float) -> float:
    """Convert planetocentric latitude (degrees) to planetographic latitude (degrees).

    Formula: tan(phi_g) = (a / b)^2 * tan(phi_c)
    """
    if abs(lat_c_deg) >= 90.0:
        return lat_c_deg
    rad_c = math.radians(lat_c_deg)
    ratio_sq = (MARS_EQUATORIAL_RADIUS_M / MARS_POLAR_RADIUS_M) ** 2
    tan_g = ratio_sq * math.tan(rad_c)
    return math.degrees(math.atan(tan_g))


def planetographic_to_planetocentric(lat_g_deg: float) -> float:
    """Convert planetographic latitude (degrees) to planetocentric latitude (degrees).

    Formula: tan(phi_c) = (b / a)^2 * tan(phi_g)
    """
    if abs(lat_g_deg) >= 90.0:
        return lat_g_deg
    rad_g = math.radians(lat_g_deg)
    ratio_inv_sq = (MARS_POLAR_RADIUS_M / MARS_EQUATORIAL_RADIUS_M) ** 2
    tan_c = ratio_inv_sq * math.tan(rad_g)
    return math.degrees(math.atan(tan_c))


def normalize_east_longitude(lon_deg: float) -> float:
    """Normalize longitude to positive-East convention [0.0, 360.0)."""
    normalized = lon_deg % 360.0
    if normalized < 0:
        normalized += 360.0
    return normalized


def compute_mars_ground_resolution(lat_deg: float, dlon_deg: float, dlat_deg: float) -> Tuple[float, float]:
    """Calculate ground resolution in physical metres at a given Martian latitude.

    Returns:
        (dx_metres, dy_metres)
    """
    lat_rad = math.radians(lat_deg)
    # Meridional circumference (north-south)
    dy = (math.pi * MARS_POLAR_RADIUS_M / 180.0) * dlat_deg
    # Parallel circumference (east-west), shrinking with cos(lat)
    dx = (math.pi * MARS_EQUATORIAL_RADIUS_M / 180.0) * math.cos(lat_rad) * dlon_deg
    return abs(dx), abs(dy)


def haversine_distance(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
    radius_m: float = MARS_EQUATORIAL_RADIUS_M,
) -> float:
    """Calculate great-circle spherical distance in metres between two points on Mars."""
    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    dphi = math.radians(lat2_deg - lat1_deg)
    dlambda = math.radians(lon2_deg - lon1_deg)
    a = (
        math.sin(dphi * 0.5) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda * 0.5) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(max(0.0, a)), math.sqrt(max(0.0, 1.0 - a)))
    return radius_m * c

