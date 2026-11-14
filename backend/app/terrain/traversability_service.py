"""Terrain Traversability Service for MARS-X — Phase 8.8.1.

Provides scientifically rigorous slope classification and terrain coverage
intelligence for Mars exploration traversability assessment.

STRICT SCOPE RULES:
- This service does NOT plan routes, generate paths, or simulate A* traversal.
- Slope bands are ANALYTICAL ONLY — they do NOT assess astronaut safety.
- NoData terrain is always classified 'unknown', never 'low_slope'.
- Source dataset, resolution and vertical reference are always exposed.
- Multiple resolutions are never presented as equivalent precision.

Terrain Source Selection Policy (highest confidence first):
  1. HiRISE DTM        (~1 m/px)   — if coordinate within swath footprint
  2. CTX DTM           (~20 m/px)  — if coordinate within swath footprint
  3. MOLA 128ppd       (~463 m/px) — regional tiles where available
  4. MOLA 4ppd         (~14.8 km)  — global fallback

Each level explicitly reports why a higher-resolution source was not used.
"""

import os
import math
import logging
import hashlib
import functools
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import rasterio
from rasterio.transform import rowcol
from pydantic import BaseModel, Field

logger = logging.getLogger("MARS-X.traversability")

# ---------------------------------------------------------------------------
# Mars geodetic constants
# ---------------------------------------------------------------------------
MARS_RADIUS_M = 3_396_190.0

# ---------------------------------------------------------------------------
# Slope classification thresholds (configurable, analytical only)
# ---------------------------------------------------------------------------
SLOPE_THRESHOLDS = {
    "low":          (0.0,  5.0),
    "moderate":     (5.0,  15.0),
    "high":         (15.0, 25.0),
    "very_high":    (25.0, 90.0),
}

SLOPE_DISCLAIMER = (
    "Slope bands are analytical terrain classifications derived from orbital DEM data only. "
    "They do NOT constitute astronaut safety assessments, EVA feasibility evaluations, "
    "or mobility predictions. No terrain in this system has been certified safe for human traversal."
)


class SlopeCategory(str, Enum):
    LOW       = "low"
    MODERATE  = "moderate"
    HIGH      = "high"
    VERY_HIGH = "very_high"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# Terrain source registry
# ---------------------------------------------------------------------------
# Each entry describes an integrated terrain product, its coverage footprint,
# pixel spacing, and local file paths for elevation and slope.
_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))


TERRAIN_SOURCES: List[Dict[str, Any]] = [
    {
        "source_id":        "hirise-holden",
        "instrument":       "HiRISE",
        "mission":          "MRO",
        "tier":             "local_tactical",
        "pixel_spacing_m":  1.0125,
        "pixel_spacing_desc": "~1 m/px (1.0125 m/px native)",
        "crs":              "IAU:49910 (Equirectangular, Mars sphere, standard parallel 0°)",
        "vertical_datum":   "MOLA Areoid (MOLA Geoid-Adjusted, SOCET SET bundle adjustment)",
        "vertical_datum_type": "areoid_height",
        # Geographic bounding box in planetocentric lon/lat (0–360E)
        "lat_min":          -29.0,
        "lat_max":          -27.5,
        "lon_min":          308.0,
        "lon_max":          310.5,
        "elev_path":        os.path.join(_DATA_ROOT, "originals", "hirise", "DTEEC_011635_1510_029542_1510_A01.tif"),
        "slope_path":       os.path.join(_DATA_ROOT, "derived", "traversability", "holden_slope.tif"),
        "nodata_elev":      -3.4028235e+38,
        "nodata_slope":     -32767.0,
        "product_id":       "DTEEC_011635_1510_029542_1510_A01",
        "coverage_note":    "Single stereo pair swath ~3.7 km × 15.9 km covering Holden Crater ejecta megabreccia",
    },
    {
        "source_id":        "ctx-tyrrhena",
        "instrument":       "CTX",
        "mission":          "MRO",
        "tier":             "regional",
        "pixel_spacing_m":  20.0128,
        "pixel_spacing_desc": "~20 m/px (20.0128 m/px native)",
        "crs":              "IAU:49910 (Equirectangular, Mars sphere, standard parallel 0°)",
        "vertical_datum":   "MOLA Areoid (ASP pc_align tied)",
        "vertical_datum_type": "areoid_height",
        "lat_min":          -5.5,
        "lat_max":          -3.8,
        "lon_min":          65.8,
        "lon_max":          67.0,
        "elev_path":        os.path.join(_DATA_ROOT, "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"),
        "slope_path":       os.path.join(_DATA_ROOT, "derived", "traversability", "tyrrhena_slope.tif"),
        "nodata_elev":      -32767.0,
        "nodata_slope":     -32767.0,
        "product_id":       "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm",
        "coverage_note":    "Stereo pair swath ~40 km wide covering Tyrrhena Terra valley network",
    },
    {
        "source_id":        "ctx-apollinaris",
        "instrument":       "CTX",
        "mission":          "MRO",
        "tier":             "regional",
        "pixel_spacing_m":  20.0,
        "pixel_spacing_desc": "~20 m/px (20.0 m/px native)",
        "crs":              "IAU:49910 (Equirectangular, Mars sphere, standard parallel 0°)",
        "vertical_datum":   "MOLA Areoid (MOLA Geoid-Adjusted via ASP dem_geoid)",
        "vertical_datum_type": "areoid_height",
        "lat_min":          4.4,
        "lat_max":          5.0,
        "lon_min":          167.8,
        "lon_max":          168.9,
        "elev_path":        os.path.join(_DATA_ROOT, "originals", "ctx", "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif"),
        "slope_path":       os.path.join(_DATA_ROOT, "derived", "traversability", "apollinaris_slope.tif"),
        "nodata_elev":      -32767.0,
        "nodata_slope":     -32767.0,
        "product_id":       "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj",
        "coverage_note":    "Controlled stereo pair covering Apollinaris Sulci yardang corridors",
    },
    {
        "source_id":        "mola-128ppd",
        "instrument":       "MOLA",
        "mission":          "MGS",
        "tier":             "regional_base",
        "pixel_spacing_m":  463.08,
        "pixel_spacing_desc": "~463 m/px (128 ppd, equatorial)",
        "crs":              "IAU:49900 (Geographic, Mars sphere)",
        "vertical_datum":   "MOLA Areoid (GMM3 mgm1025 degree 50)",
        "vertical_datum_type": "areoid_height",
        "lat_min":          -44.0,
        "lat_max":           44.0,
        "lon_min":            0.0,
        "lon_max":           90.0,  # Only tiles ingested so far; global coverage via 4ppd fallback
        "elev_path":        os.path.join(_DATA_ROOT, "raw", "mola", "megt00n000hb.img"),
        "slope_path":       os.path.join(_DATA_ROOT, "processed", "mola", "mola_megt90n000cb_slope.tif"),
        "nodata_elev":      -32768.0,
        "nodata_slope":     -32768.0,
        "product_id":       "MEGT00N000HB",
        "coverage_note":    "MOLA MEGDR 128 ppd tile covering lat -44°–0°, lon 0°–90°",
    },
    {
        "source_id":        "mola-4ppd",
        "instrument":       "MOLA",
        "mission":          "MGS",
        "tier":             "global_coarse",
        "pixel_spacing_m":  14818.67,
        "pixel_spacing_desc": "~14,818 m/px (4 ppd, equatorial)",
        "crs":              "IAU:49900 (Geographic, Mars sphere)",
        "vertical_datum":   "MOLA Areoid (GMM3 mgm1025 degree 50)",
        "vertical_datum_type": "areoid_height",
        "lat_min":          -90.0,
        "lat_max":           90.0,
        "lon_min":            0.0,
        "lon_max":           360.0,
        "elev_path":        os.path.join(_DATA_ROOT, "processed", "mola", "mola_megt90n000cb_elevation.tif"),
        "slope_path":       os.path.join(_DATA_ROOT, "processed", "mola", "mola_megt90n000cb_slope.tif"),
        "nodata_elev":      -32768.0,
        "nodata_slope":     -32768.0,
        "product_id":       "MEGT90N000CB (4ppd COG)",
        "coverage_note":    "MOLA MEGDR 4 ppd global-coverage COG elevation raster; near-global (±90°)",
    },
]

# Priority ordering for source selection (highest-resolution first)
SOURCE_PRIORITY_ORDER = ["hirise-holden", "ctx-tyrrhena", "ctx-apollinaris", "mola-128ppd", "mola-4ppd"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TerrainSourceInfo(BaseModel):
    source_id: str
    instrument: str
    mission: str
    tier: str
    pixel_spacing_m: float
    pixel_spacing_desc: str
    crs: str
    vertical_datum: str
    vertical_datum_type: str
    product_id: str
    coverage_note: str
    elevation_file_available: bool
    slope_file_available: bool


class TraversabilityPointResult(BaseModel):
    latitude: float
    longitude: float
    elevation_m: Optional[float]
    slope_deg: Optional[float]
    slope_pct: Optional[float]
    slope_category: SlopeCategory
    source_id: str
    instrument: str
    native_pixel_spacing_m: float
    native_pixel_spacing_desc: str
    vertical_datum: str
    vertical_datum_type: str
    is_elevation_nodata: bool
    is_slope_nodata: bool
    source_selection_reason: str
    fallback_chain: List[str]
    slope_disclaimer: str = SLOPE_DISCLAIMER
    slope_thresholds_deg: Dict[str, Any] = Field(default_factory=lambda: SLOPE_THRESHOLDS)


class TraversabilityWindowResult(BaseModel):
    bbox: List[float]            # [min_lon, min_lat, max_lon, max_lat]
    width_px: int
    height_px: int
    source_id: str
    native_pixel_spacing_m: float
    display_pixel_spacing_m: float
    sampling_regime: str
    slope_values: List[List[Optional[float]]]   # 2-D array [row][col], None = nodata
    slope_categories: List[List[str]]           # 2-D array [row][col]
    nodata_fraction: float
    coverage_within_bbox_fraction: float
    slope_disclaimer: str = SLOPE_DISCLAIMER


class TraversabilityCoverageEntry(BaseModel):
    source_id: str
    instrument: str
    tier: str
    pixel_spacing_m: float
    pixel_spacing_desc: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    elevation_file_available: bool
    slope_file_available: bool
    coverage_note: str
    vertical_datum: str


class TraversabilityLegendEntry(BaseModel):
    category: str
    label: str
    slope_range_deg: str
    color_hex: str
    description: str


TRAVERSABILITY_LEGEND: List[TraversabilityLegendEntry] = [
    TraversabilityLegendEntry(
        category="low",
        label="Low Slope (0–5°)",
        slope_range_deg="0–5°",
        color_hex="#2ecc71",
        description="Relatively flat terrain at this orbital resolution. Microtopography (boulders, crevasses) below resolution limit is NOT assessed.",
    ),
    TraversabilityLegendEntry(
        category="moderate",
        label="Moderate Slope (5–15°)",
        slope_range_deg="5–15°",
        color_hex="#f39c12",
        description="Measurable slope gradient. Terrain features at this scale require additional investigation.",
    ),
    TraversabilityLegendEntry(
        category="high",
        label="High Slope (15–25°)",
        slope_range_deg="15–25°",
        color_hex="#e74c3c",
        description="Steep terrain at this scale. Likely crater walls, escarpments, or fault scarps.",
    ),
    TraversabilityLegendEntry(
        category="very_high",
        label="Very High Slope (>25°)",
        slope_range_deg=">25°",
        color_hex="#8e44ad",
        description="Extreme slope gradient. Likely cliff faces, caldera walls, or canyon rims.",
    ),
    TraversabilityLegendEntry(
        category="unknown",
        label="Unknown / NoData",
        slope_range_deg="N/A",
        color_hex="#7f8c8d",
        description="No valid slope data available. This terrain must NEVER be assumed safe or low-slope.",
    ),
]


# ---------------------------------------------------------------------------
# Helper: file availability check
# ---------------------------------------------------------------------------
def _file_ok(path: str) -> bool:
    return bool(path and os.path.isfile(path) and os.path.getsize(path) > 0)


# ---------------------------------------------------------------------------
# Source selection
# ---------------------------------------------------------------------------
def select_source_for_point(lat: float, lon: float) -> Tuple[Optional[Dict], List[str]]:
    """Return (best_source_dict, fallback_chain) for a given coordinate.

    Applies priority: HiRISE → CTX → MOLA 128ppd → MOLA 4ppd.
    Returns None if no valid source is available.
    """
    lon_norm = lon % 360.0
    fallback_chain: List[str] = []

    for sid in SOURCE_PRIORITY_ORDER:
        src = next((s for s in TERRAIN_SOURCES if s["source_id"] == sid), None)
        if src is None:
            continue

        # Check geographic coverage
        if not (src["lat_min"] <= lat <= src["lat_max"]):
            fallback_chain.append(f"{sid}: outside latitude coverage ({src['lat_min']}° – {src['lat_max']}°)")
            continue
        # Longitude coverage (handle 0–360 wrap)
        lon_in = src["lon_min"] <= lon_norm <= src["lon_max"]
        if not lon_in:
            fallback_chain.append(f"{sid}: outside longitude coverage ({src['lon_min']}° – {src['lon_max']}°)")
            continue

        # Check file availability
        if not _file_ok(src["elev_path"]):
            fallback_chain.append(f"{sid}: elevation file not on disk")
            continue

        fallback_chain.append(f"{sid}: SELECTED")
        return src, fallback_chain

    fallback_chain.append("No terrain source covers this coordinate.")
    return None, fallback_chain


# ---------------------------------------------------------------------------
# Raster sampling utilities
# ---------------------------------------------------------------------------
def _sample_raster_point(raster_path: str, lon: float, lat: float,
                          nodata_val: float, projected: bool = True) -> Optional[float]:
    """Sample a single value from a raster at (lon, lat).

    For projected IAU:49910 rasters, the coordinate is re-projected from
    geographic lon/lat using the equirectangular forward formula:
        x = R * lon_rad   (clon=0°, standard_parallel=0°)
        y = R * lat_rad
    For geographic IAU:49900 rasters, lon/lat are used directly.
    """
    with rasterio.open(raster_path) as src:
        transform = src.transform
        bounds = src.bounds

        if projected:
            # Equirectangular: x = R * lon_rad, y = R * lat_rad
            lon_norm = lon % 360.0
            # If bounds use [-180, 180] domain (e.g. HiRISE left < 0)
            if bounds.right <= 0 or (bounds.left < 0 and lon_norm > 180.0):
                lon_proj = lon_norm - 360.0 if lon_norm > 180.0 else lon_norm
            else:
                lon_proj = lon_norm
            x = MARS_RADIUS_M * math.radians(lon_proj)
            y = MARS_RADIUS_M * math.radians(lat)
        else:
            # Geographic: col = lon, row = lat
            lon_norm = lon % 360.0
            x = lon_norm
            y = lat

        if not (bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top):
            return None

        try:
            row, col = rowcol(transform, x, y)
            if row < 0 or col < 0 or row >= src.height or col >= src.width:
                return None
            value = src.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0]
        except Exception as exc:
            logger.debug("Raster sampling error at (%.4f, %.4f): %s", lat, lon, exc)
            return None

    value = float(value)
    # Check for NoData
    if math.isnan(value) or math.isinf(value):
        return None
    if nodata_val is not None and abs(value - nodata_val) < abs(nodata_val) * 1e-5 + 1.0:
        return None
    # Sanity check for MOLA areoid range
    if value < -12_000.0 or value > 26_000.0:
        return None
    return round(value, 3)


# ---------------------------------------------------------------------------
# Slope classification
# ---------------------------------------------------------------------------
def classify_slope(slope_deg: Optional[float]) -> SlopeCategory:
    if slope_deg is None:
        return SlopeCategory.UNKNOWN
    if math.isnan(slope_deg):
        return SlopeCategory.UNKNOWN
    if slope_deg < 0.0:
        return SlopeCategory.UNKNOWN
    if slope_deg <= SLOPE_THRESHOLDS["low"][1]:
        return SlopeCategory.LOW
    if slope_deg <= SLOPE_THRESHOLDS["moderate"][1]:
        return SlopeCategory.MODERATE
    if slope_deg <= SLOPE_THRESHOLDS["high"][1]:
        return SlopeCategory.HIGH
    return SlopeCategory.VERY_HIGH


# ---------------------------------------------------------------------------
# Traversability Service class
# ---------------------------------------------------------------------------
class TraversabilityService:
    """Point and window traversability assessment from validated Mars DTMs."""

    def get_sources(self) -> List[TerrainSourceInfo]:
        return [
            TerrainSourceInfo(
                source_id=s["source_id"],
                instrument=s["instrument"],
                mission=s["mission"],
                tier=s["tier"],
                pixel_spacing_m=s["pixel_spacing_m"],
                pixel_spacing_desc=s["pixel_spacing_desc"],
                crs=s["crs"],
                vertical_datum=s["vertical_datum"],
                vertical_datum_type=s["vertical_datum_type"],
                product_id=s["product_id"],
                coverage_note=s["coverage_note"],
                elevation_file_available=_file_ok(s["elev_path"]),
                slope_file_available=_file_ok(s["slope_path"]),
            )
            for s in TERRAIN_SOURCES
        ]

    def get_coverage(self) -> List[TraversabilityCoverageEntry]:
        return [
            TraversabilityCoverageEntry(
                source_id=s["source_id"],
                instrument=s["instrument"],
                tier=s["tier"],
                pixel_spacing_m=s["pixel_spacing_m"],
                pixel_spacing_desc=s["pixel_spacing_desc"],
                lat_min=s["lat_min"],
                lat_max=s["lat_max"],
                lon_min=s["lon_min"],
                lon_max=s["lon_max"],
                elevation_file_available=_file_ok(s["elev_path"]),
                slope_file_available=_file_ok(s["slope_path"]),
                coverage_note=s["coverage_note"],
                vertical_datum=s["vertical_datum"],
            )
            for s in TERRAIN_SOURCES
        ]

    def query_point(self, lat: float, lon: float) -> TraversabilityPointResult:
        """Return elevation, slope, slope category and provenance for a single coordinate."""
        src, fallback_chain = select_source_for_point(lat, lon)

        if src is None:
            return TraversabilityPointResult(
                latitude=lat,
                longitude=lon,
                elevation_m=None,
                slope_deg=None,
                slope_pct=None,
                slope_category=SlopeCategory.UNKNOWN,
                source_id="none",
                instrument="none",
                native_pixel_spacing_m=0.0,
                native_pixel_spacing_desc="n/a",
                vertical_datum="n/a",
                vertical_datum_type="n/a",
                is_elevation_nodata=True,
                is_slope_nodata=True,
                source_selection_reason="No terrain dataset covers this coordinate.",
                fallback_chain=fallback_chain,
            )

        # Determine whether to use projected or geographic sampling
        is_projected = "49910" in src.get("crs", "") or src["tier"] in ("local_tactical", "regional")

        elev = _sample_raster_point(
            src["elev_path"], lon, lat, src["nodata_elev"], projected=is_projected
        )
        slope = None
        if _file_ok(src["slope_path"]):
            slope = _sample_raster_point(
                src["slope_path"], lon, lat, src["nodata_slope"], projected=is_projected
            )

        slope_pct = round(math.tan(math.radians(slope)) * 100.0, 3) if slope is not None else None
        category = classify_slope(slope)

        selection_reason = next((r for r in fallback_chain if "SELECTED" in r), fallback_chain[-1])

        return TraversabilityPointResult(
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
            slope_deg=round(slope, 3) if slope is not None else None,
            slope_pct=slope_pct,
            slope_category=category,
            source_id=src["source_id"],
            instrument=src["instrument"],
            native_pixel_spacing_m=src["pixel_spacing_m"],
            native_pixel_spacing_desc=src["pixel_spacing_desc"],
            vertical_datum=src["vertical_datum"],
            vertical_datum_type=src["vertical_datum_type"],
            is_elevation_nodata=(elev is None),
            is_slope_nodata=(slope is None),
            source_selection_reason=selection_reason,
            fallback_chain=fallback_chain,
        )

    def query_window(
        self,
        min_lat: float, max_lat: float,
        min_lon: float, max_lon: float,
        width: int = 64, height: int = 32,
    ) -> TraversabilityWindowResult:
        """Return a gridded slope classification over a bounding box.

        Resolution is capped at 128×64 to avoid massive payloads.
        The best available source for the window centre is used.
        """
        width = min(width, 128)
        height = min(height, 64)

        centre_lat = (min_lat + max_lat) / 2.0
        centre_lon = (min_lon + max_lon) / 2.0
        src, fallback_chain = select_source_for_point(centre_lat, centre_lon)

        if src is None:
            return TraversabilityWindowResult(
                bbox=[min_lon, min_lat, max_lon, max_lat],
                width_px=width,
                height_px=height,
                source_id="none",
                native_pixel_spacing_m=0.0,
                display_pixel_spacing_m=0.0,
                sampling_regime="no_data",
                slope_values=[[None] * width for _ in range(height)],
                slope_categories=[["unknown"] * width for _ in range(height)],
                nodata_fraction=1.0,
                coverage_within_bbox_fraction=0.0,
            )

        is_projected = "49910" in src.get("crs", "") or src["tier"] in ("local_tactical", "regional")

        # Compute display pixel spacing in metres
        lon_span_deg = (max_lon - min_lon) % 360.0 or 360.0
        lat_mid_rad = math.radians(centre_lat)
        display_m_per_px = (MARS_RADIUS_M * math.radians(lon_span_deg)) / max(width, 1)
        source_m_per_px = src["pixel_spacing_m"]

        ratio = display_m_per_px / source_m_per_px
        if ratio < 0.95:
            regime = "oversampled_resampled"
        elif ratio > 1.05:
            regime = "undersampled_decimated"
        else:
            regime = "native_matched"

        # Sample on the grid
        lats = [min_lat + (max_lat - min_lat) * (r + 0.5) / height for r in range(height)]
        lons = [min_lon + lon_span_deg * (c + 0.5) / width for c in range(width)]

        slope_values: List[List[Optional[float]]] = []
        slope_categories: List[List[str]] = []
        nodata_count = 0
        in_coverage_count = 0

        slope_path = src["slope_path"] if _file_ok(src["slope_path"]) else None

        if slope_path:
            with rasterio.open(slope_path) as rst:
                transform = rst.transform
                bounds = rst.bounds

                for lat in lats:
                    row_vals: List[Optional[float]] = []
                    row_cats: List[str] = []
                    for lon in lons:
                        if is_projected:
                            lon_norm = lon % 360.0
                            if bounds.right <= 0 or (bounds.left < 0 and lon_norm > 180.0):
                                lon_proj = lon_norm - 360.0 if lon_norm > 180.0 else lon_norm
                            else:
                                lon_proj = lon_norm
                            x = MARS_RADIUS_M * math.radians(lon_proj)
                            y = MARS_RADIUS_M * math.radians(lat)
                        else:
                            x = lon % 360.0
                            y = lat

                        if not (bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top):
                            row_vals.append(None)
                            row_cats.append("unknown")
                            nodata_count += 1
                            continue

                        in_coverage_count += 1
                        try:
                            r_px, c_px = rowcol(transform, x, y)
                            if 0 <= r_px < rst.height and 0 <= c_px < rst.width:
                                v = float(rst.read(1, window=rasterio.windows.Window(c_px, r_px, 1, 1))[0, 0])
                                nd = src["nodata_slope"]
                                if math.isnan(v) or math.isinf(v) or (nd is not None and abs(v - nd) < abs(nd) * 1e-5 + 1.0):
                                    row_vals.append(None)
                                    row_cats.append("unknown")
                                    nodata_count += 1
                                else:
                                    slope_v = round(v, 2)
                                    row_vals.append(slope_v)
                                    row_cats.append(classify_slope(slope_v).value)
                            else:
                                row_vals.append(None)
                                row_cats.append("unknown")
                                nodata_count += 1
                        except Exception:
                            row_vals.append(None)
                            row_cats.append("unknown")
                            nodata_count += 1

                    slope_values.append(row_vals)
                    slope_categories.append(row_cats)
        else:
            # No slope file — all unknown
            for _ in range(height):
                slope_values.append([None] * width)
                slope_categories.append(["unknown"] * width)
            nodata_count = width * height

        total = width * height
        nodata_frac = nodata_count / total
        cov_frac = in_coverage_count / total

        return TraversabilityWindowResult(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            width_px=width,
            height_px=height,
            source_id=src["source_id"],
            native_pixel_spacing_m=source_m_per_px,
            display_pixel_spacing_m=round(display_m_per_px, 1),
            sampling_regime=regime,
            slope_values=slope_values,
            slope_categories=slope_categories,
            nodata_fraction=round(nodata_frac, 4),
            coverage_within_bbox_fraction=round(cov_frac, 4),
        )

    @staticmethod
    def get_legend() -> List[TraversabilityLegendEntry]:
        return TRAVERSABILITY_LEGEND

    @staticmethod
    def get_slope_thresholds() -> Dict[str, Any]:
        return {
            "thresholds_deg": SLOPE_THRESHOLDS,
            "disclaimer": SLOPE_DISCLAIMER,
            "algorithm": "Horn (1981) weighted 3×3 gradient in degrees",
            "units": "degrees (0–90°)",
            "configurable": True,
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_service: Optional[TraversabilityService] = None


def get_traversability_service() -> TraversabilityService:
    global _service
    if _service is None:
        _service = TraversabilityService()
        logger.info("TraversabilityService initialised.")
    return _service
