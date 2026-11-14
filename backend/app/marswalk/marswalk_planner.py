"""Terrain-Aware Marswalk Route Generation Engine — Phase 8.8.2.

Provides authentic A* pathfinding over multi-tier Mars DEMs:
  1. HiRISE Holden Crater DTM (~1 m/px, local tactical)
  2. CTX Tyrrhena Terra DTM (~20 m/px, regional)
  3. CTX Apollinaris Sulci DTM (~20 m/px, regional)
  4. MOLA 128 ppd Regional Tile (~463 m/px)
  5. MOLA 4 ppd Global COG (~14.8 km/px)

Key scientific and mathematical properties:
  - 8-connected grid transitions with physical 3D Mars-surface Euclidean distance.
  - Strict diagonal corner-cutting prevention (orthogonal neighbors must be passable).
  - Quadratic slope cost penalty: Cost(u, v) = d_surface * [1.0 + beta * (theta_v / 15.0)^2].
  - Hard max slope cutoff (default 25.0°) and NoData impassability.
  - Admissible and consistent 3D Euclidean lower-bound heuristic h(u, G) <= true_cost.
  - Exposure breakdown across standard analytical slope bands (0-5°, 5-15°, 15-25°, >25°, unknown).
  - Prominent astronaut safety disclaimer (never describes routes as astronaut-safe).
"""

import os
import math
import time
import uuid
import heapq
import hashlib
import logging
from typing import Tuple, List, Dict, Any, Optional

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import rowcol, xy

from app.terrain.traversability_service import (
    TERRAIN_SOURCES,
    MARS_RADIUS_M,
    SLOPE_THRESHOLDS,
    classify_slope,
)
from app.marswalk.marswalk_models import (
    MarswalkRouteRequest,
    MarswalkRouteResponse,
    MarswalkRoutePoint,
    MarswalkMetadataResponse,
    ValidatedCorridorPreset,
    MARSWALK_SAFETY_DISCLAIMER,
)

logger = logging.getLogger("MARS-X.marswalk")

# Reference slope angle for quadratic penalty scaling (15° is boundary of high slope)
THETA_REF_DEG = 15.0

# Curated Marswalk corridors for one-click testing and demonstration
VALIDATED_CORRIDORS: List[ValidatedCorridorPreset] = [
    ValidatedCorridorPreset(
        corridor_id="holden-hirise-megabreccia",
        name="Holden Crater Megabreccia Tactical Traverse",
        region="Holden Crater (Margaritifer Terra)",
        source_dataset="hirise-holden",
        start_lat=-28.500,
        start_lon=309.020,
        dest_lat=-28.502,
        dest_lon=309.022,
        description="Tactical traverse across megabreccia ejecta blocks at ~1.01 m/px resolution.",
        target_geology="Noachian impact ejecta & fractured bedrock",
    ),
    ValidatedCorridorPreset(
        corridor_id="tyrrhena-ctx-valley",
        name="Tyrrhena Terra Fluvial Channel Traverse",
        region="Tyrrhena Terra",
        source_dataset="ctx-tyrrhena",
        start_lat=-4.600,
        start_lon=66.317,
        dest_lat=-4.605,
        dest_lon=66.325,
        description="Regional traverse negotiating branching valley network terrain at ~20 m/px.",
        target_geology="Dissected cratered terrain & valley networks",
    ),
    ValidatedCorridorPreset(
        corridor_id="apollinaris-ctx-yardangs",
        name="Apollinaris Sulci Yardang Corridor",
        region="Apollinaris Sulci",
        source_dataset="ctx-apollinaris",
        start_lat=4.700,
        start_lon=168.250,
        dest_lat=4.706,
        dest_lon=168.258,
        description="Navigation through wind-eroded yardang flutes and friable ignimbrite ridges.",
        target_geology="Medusae Fossae Formation yardang fields",
    ),
    ValidatedCorridorPreset(
        corridor_id="tyrrhena-mola-regional",
        name="Tyrrhena Regional Highland Ascent",
        region="Tyrrhena Terra",
        source_dataset="mola-128ppd",
        start_lat=-4.700,
        start_lon=66.100,
        dest_lat=-4.600,
        dest_lon=66.250,
        description="Highland plateau traverse at ~463 m/px base regional resolution.",
        target_geology="Noachian highland crust",
    ),
]

# Engine and algorithmic version definitions for cache identity and invalidation
MARSWALK_ALGORITHM_VERSION = "astar-8way-v1.2"
MARSWALK_COST_FUNCTION_VERSION = "quad-theta15-v1.0"
MARSWALK_DERIVATIVE_VERSION = "horn-slope-3x3-v1.0"

# In-memory LRU route cache with deterministic request hash mapping
_ROUTE_CACHE: Dict[str, MarswalkRouteResponse] = {}
_REQUEST_HASH_TO_ROUTE_ID: Dict[str, str] = {}
_MAX_CACHE_SIZE = 50


def get_source_version_tag(source_id: str) -> str:
    """Compute an immutable version signature for a terrain dataset.

    Includes dataset source ID, product ID, and underlying elevation/slope file
    modification times and sizes on disk. Any modification to DEM or slope rasters
    will automatically alter this tag and invalidate cached routes.
    """
    src = next((s for s in TERRAIN_SOURCES if s["source_id"] == source_id), None)
    if not src:
        return f"{source_id}:unknown"

    elev_path = src.get("elev_path", "")
    slope_path = src.get("slope_path", "")
    product_id = src.get("product_id", "")

    elev_tag = "missing"
    if elev_path and os.path.isfile(elev_path):
        try:
            st = os.stat(elev_path)
            elev_tag = f"{int(st.st_mtime)}:{st.st_size}"
        except OSError:
            elev_tag = "stat_err"

    slope_tag = "none"
    if slope_path and os.path.isfile(slope_path):
        try:
            st = os.stat(slope_path)
            slope_tag = f"{int(st.st_mtime)}:{st.st_size}"
        except OSError:
            slope_tag = "stat_err"

    return f"{source_id}:{product_id}:{elev_tag}:{slope_tag}"


def compute_request_hash(
    request: MarswalkRouteRequest,
    resolved_source_id: Optional[str] = None,
) -> str:
    """Compute deterministic cryptographic hash of all route parameters, datasets, and algorithm versions.

    Hash components:
      1. Start latitude and normalized longitude (6 decimals).
      2. Destination latitude and normalized longitude (6 decimals).
      3. Resolved terrain dataset source ID.
      4. Dataset version signature (mtime + size of elevation and slope rasters).
      5. Quadratic slope penalty factor (beta).
      6. Hard slope cutoff angle (max_slope_deg).
      7. Search node expansion limit (max_search_nodes).
      8. Search algorithm ("astar" vs "dijkstra").
      9. Algorithm implementation version (MARSWALK_ALGORITHM_VERSION).
     10. Cost function definition version (MARSWALK_COST_FUNCTION_VERSION).
     11. Derivative algorithm version (MARSWALK_DERIVATIVE_VERSION).
     12. Optional custom route name.
    """
    norm_start_lon = request.start_lon % 360.0
    norm_dest_lon = request.dest_lon % 360.0
    algo = getattr(request, "algorithm", "astar") or "astar"
    name = getattr(request, "route_name", None) or ""

    if resolved_source_id is None:
        try:
            source = MarswalkPlanner.select_source(
                start_lat=request.start_lat,
                start_lon=request.start_lon,
                dest_lat=request.dest_lat,
                dest_lon=request.dest_lon,
                preferred_source=request.preferred_source,
            )
            resolved_source_id = source["source_id"]
        except Exception:
            resolved_source_id = request.preferred_source or "auto"

    source_tag = get_source_version_tag(resolved_source_id)

    raw = (
        f"{request.start_lat:.6f}:{norm_start_lon:.6f}:"
        f"{request.dest_lat:.6f}:{norm_dest_lon:.6f}:"
        f"{resolved_source_id}:{source_tag}:"
        f"{request.slope_penalty_factor:.3f}:"
        f"{request.max_slope_deg:.2f}:"
        f"{request.max_search_nodes}:"
        f"{algo}:"
        f"{MARSWALK_ALGORITHM_VERSION}:"
        f"{MARSWALK_COST_FUNCTION_VERSION}:"
        f"{MARSWALK_DERIVATIVE_VERSION}:"
        f"{name}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cache_route(route: MarswalkRouteResponse, request_hash: Optional[str] = None):
    """Store route in memory cache, evicting oldest if capacity reached."""
    if len(_ROUTE_CACHE) >= _MAX_CACHE_SIZE:
        oldest_id = next(iter(_ROUTE_CACHE))
        _ROUTE_CACHE.pop(oldest_id, None)
        evict_hashes = [h for h, r_id in _REQUEST_HASH_TO_ROUTE_ID.items() if r_id == oldest_id]
        for h in evict_hashes:
            _REQUEST_HASH_TO_ROUTE_ID.pop(h, None)

    _ROUTE_CACHE[route.route_id] = route
    if request_hash:
        _REQUEST_HASH_TO_ROUTE_ID[request_hash] = route.route_id


def get_cached_route(route_id: str) -> Optional[MarswalkRouteResponse]:
    """Retrieve previously computed route from cache by unique route_id."""
    return _ROUTE_CACHE.get(route_id)


def get_cached_route_by_request(request: MarswalkRouteRequest) -> Optional[MarswalkRouteResponse]:
    """Retrieve cached route if an identical request was already solved."""
    req_hash = compute_request_hash(request)
    route_id = _REQUEST_HASH_TO_ROUTE_ID.get(req_hash)
    if route_id:
        return _ROUTE_CACHE.get(route_id)
    return None


def clear_route_cache():
    """Clear all cached routes and request hashes (for testing and cache invalidation)."""
    _ROUTE_CACHE.clear()
    _REQUEST_HASH_TO_ROUTE_ID.clear()


class BoundedTerrainGrid:
    """Extracted local DEM and slope sub-grid ready for pathfinding."""

    def __init__(
        self,
        source_info: Dict[str, Any],
        elevation: np.ndarray,
        slope: np.ndarray,
        row_offset: int,
        col_offset: int,
        transform: Any,
        is_projected: bool,
        dx_m: float,
        dy_m: float,
        lat_top: Optional[float] = None,
        lon_left: Optional[float] = None,
        d_lat_deg: Optional[float] = None,
        d_lon_deg: Optional[float] = None,
    ):
        self.source_info = source_info
        self.elevation = elevation
        self.slope = slope
        self.rows, self.cols = elevation.shape
        self.row_offset = row_offset
        self.col_offset = col_offset
        self.transform = transform
        self.is_projected = is_projected
        self.dx_m = dx_m
        self.dy_m = dy_m
        self.lat_top = lat_top
        self.lon_left = lon_left
        self.d_lat_deg = d_lat_deg
        self.d_lon_deg = d_lon_deg

        # Boolean passability mask (precomputed)
        self.passable_mask = np.ones((self.rows, self.cols), dtype=bool)

        # Mark NoData in elevation
        nodata_elev = source_info.get("nodata_elev", -32767.0)
        elev_nodata = (
            np.isnan(self.elevation)
            | np.isinf(self.elevation)
            | (self.elevation <= nodata_elev + 1.0)
            | (self.elevation < -30000.0)
        )
        self.passable_mask[elev_nodata] = False

        # Mark NoData in slope
        nodata_slope = source_info.get("nodata_slope", -32767.0)
        slope_nodata = (
            np.isnan(self.slope)
            | np.isinf(self.slope)
            | (self.slope <= nodata_slope + 1.0)
            | (self.slope < 0.0)
            | (self.slope > 90.0)
        )
        self.passable_mask[slope_nodata] = False

    def is_in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_passable(self, r: int, c: int, max_slope_deg: float) -> bool:
        if not self.is_in_bounds(r, c):
            return False
        if not self.passable_mask[r, c]:
            return False
        return float(self.slope[r, c]) <= max_slope_deg

    def get_cell_spacing(self, r: int) -> Tuple[float, float]:
        """Return (dy_m, dx_m) for the given row."""
        if self.is_projected:
            return self.dy_m, self.dx_m
        # Geographic: scale dx by cos(latitude)
        if self.lat_top is not None and self.d_lat_deg is not None and self.d_lon_deg is not None:
            lat = self.lat_top - (r + 0.5) * self.d_lat_deg
            lat_rad = math.radians(lat)
            dy = (math.pi / 180.0) * MARS_RADIUS_M * self.d_lat_deg
            dx = (math.pi / 180.0) * MARS_RADIUS_M * math.cos(lat_rad) * self.d_lon_deg
            return dy, dx
        return self.dy_m, self.dx_m

    def cell_to_lat_lon(self, r: int, c: int) -> Tuple[float, float]:
        """Convert local grid row/col to planetocentric (lat, lon) in degrees."""
        glob_r = self.row_offset + r
        glob_c = self.col_offset + c

        if self.is_projected and self.transform is not None:
            x_m, y_m = xy(self.transform, glob_r, glob_c)
            lat = math.degrees(y_m / MARS_RADIUS_M)
            lon = (math.degrees(x_m / MARS_RADIUS_M)) % 360.0
            return lat, lon
        elif self.transform is not None:
            lon_c, lat_c = xy(self.transform, glob_r, glob_c)
            return float(lat_c), float(lon_c % 360.0)
        else:
            lat_top = self.lat_top if self.lat_top is not None else 0.0
            lon_left = self.lon_left if self.lon_left is not None else 0.0
            d_lat = self.d_lat_deg if self.d_lat_deg is not None else (self.dy_m / MARS_RADIUS_M) * (180.0 / math.pi)
            d_lon = self.d_lon_deg if self.d_lon_deg is not None else (self.dx_m / MARS_RADIUS_M) * (180.0 / math.pi)
            lat = lat_top - (r + 0.5) * d_lat
            lon = (lon_left + (c + 0.5) * d_lon) % 360.0
            return float(lat), float(lon)


class MarswalkPlanner:
    """High-level coordinator for multi-tier Marswalk route generation."""

    @staticmethod
    def select_source(
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        preferred_source: Optional[str] = "auto",
    ) -> Dict[str, Any]:
        """Select best valid terrain dataset covering both endpoints."""
        norm_start_lon = start_lon % 360.0
        norm_dest_lon = dest_lon % 360.0

        if preferred_source and preferred_source != "auto":
            src = next((s for s in TERRAIN_SOURCES if s["source_id"] == preferred_source), None)
            if src is None:
                raise ValueError(f"Unknown preferred terrain source: '{preferred_source}'")
            # Verify coverage of both points
            in_lat = (src["lat_min"] <= start_lat <= src["lat_max"]) and (src["lat_min"] <= dest_lat <= src["lat_max"])
            in_lon = (src["lon_min"] <= norm_start_lon <= src["lon_max"]) and (src["lon_min"] <= norm_dest_lon <= src["lon_max"])
            if not (in_lat and in_lon):
                raise ValueError(
                    f"Selected source '{preferred_source}' does not cover both route coordinates: "
                    f"Start ({start_lat:.3f}°, {norm_start_lon:.3f}°E), Dest ({dest_lat:.3f}°, {norm_dest_lon:.3f}°E). "
                    f"Source footprint: Lat [{src['lat_min']}°, {src['lat_max']}°], Lon [{src['lon_min']}°, {src['lon_max']}°E]."
                )
            if not (os.path.isfile(src["elev_path"]) and os.path.getsize(src["elev_path"]) > 0):
                raise FileNotFoundError(f"Elevation file for '{preferred_source}' not found on disk.")
            return src

        # Auto selection: highest resolution source covering both endpoints
        for sid in ["hirise-holden", "ctx-tyrrhena", "ctx-apollinaris", "mola-128ppd", "mola-4ppd"]:
            src = next((s for s in TERRAIN_SOURCES if s["source_id"] == sid), None)
            if src is None:
                continue
            in_lat = (src["lat_min"] <= start_lat <= src["lat_max"]) and (src["lat_min"] <= dest_lat <= src["lat_max"])
            in_lon = (src["lon_min"] <= norm_start_lon <= src["lon_max"]) and (src["lon_min"] <= norm_dest_lon <= src["lon_max"])
            if in_lat and in_lon and os.path.isfile(src["elev_path"]):
                return src

        # Fallback to global 4ppd
        global_mola = next(s for s in TERRAIN_SOURCES if s["source_id"] == "mola-4ppd")
        return global_mola

    @classmethod
    def extract_grid_window(
        cls,
        source: Dict[str, Any],
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        margin_pct: float = 0.35,
        min_margin_px: int = 25,
        max_window_dim: int = 1200,
    ) -> Tuple[BoundedTerrainGrid, Tuple[int, int], Tuple[int, int]]:
        """Extract bounded sub-grid and map start/dest to local (row, col) coordinates."""
        sid = source["source_id"]
        elev_path = source["elev_path"]
        slope_path = source["slope_path"]

        # -------------------------------------------------------------
        # Case A: MOLA 128 ppd raw binary image
        # -------------------------------------------------------------
        if sid == "mola-128ppd":
            lines, samples = 5632, 11520
            ppd = 128.0
            pixel_deg = 1.0 / 128.0
            lat_max = 0.0
            lon_min = 0.0

            r1 = int(round((lat_max - start_lat) * ppd - 0.5))
            c1 = int(round(((start_lon % 360.0) - lon_min) * ppd - 0.5))
            r2 = int(round((lat_max - dest_lat) * ppd - 0.5))
            c2 = int(round(((dest_lon % 360.0) - lon_min) * ppd - 0.5))

            r1 = max(0, min(r1, lines - 1))
            c1 = max(0, min(c1, samples - 1))
            r2 = max(0, min(r2, lines - 1))
            c2 = max(0, min(c2, samples - 1))

            span_r = abs(r2 - r1)
            span_c = abs(c2 - c1)
            margin = max(min_margin_px, int(max(span_r, span_c) * margin_pct))

            min_r = max(0, min(r1, r2) - margin)
            max_r = min(lines, max(r1, r2) + margin + 1)
            min_c = max(0, min(c1, c2) - margin)
            max_c = min(samples, max(c1, c2) + margin + 1)

            if (max_r - min_r) > max_window_dim or (max_c - min_c) > max_window_dim:
                raise ValueError(
                    f"Route window ({max_r - min_r}x{max_c - min_c} px) exceeds computational safety threshold ({max_window_dim}x{max_window_dim} px). "
                    "Choose waypoints closer together."
                )

            mmap_elev = np.memmap(elev_path, dtype=">i2", mode="r", shape=(lines, samples))
            sub_elev = np.array(mmap_elev[min_r:max_r, min_c:max_c], dtype=np.float32)

            # Compute Horn slope on sub-window
            lat_center = (start_lat + dest_lat) / 2.0
            lat_rad = math.radians(lat_center)
            dy = (math.pi / 180.0) * MARS_RADIUS_M * pixel_deg
            dx = (math.pi / 180.0) * MARS_RADIUS_M * math.cos(lat_rad) * pixel_deg

            # Fast Horn slope calculation with numpy
            sub_slope = cls._compute_horn_slope_grid(sub_elev, dy, dx, nodata_val=-32768.0)

            lat_top = lat_max - min_r * pixel_deg
            lon_left = lon_min + min_c * pixel_deg

            grid = BoundedTerrainGrid(
                source_info=source,
                elevation=sub_elev,
                slope=sub_slope,
                row_offset=min_r,
                col_offset=min_c,
                transform=None,
                is_projected=False,
                dx_m=dx,
                dy_m=dy,
                lat_top=lat_top,
                lon_left=lon_left,
                d_lat_deg=pixel_deg,
                d_lon_deg=pixel_deg,
            )
            return grid, (r1 - min_r, c1 - min_c), (r2 - min_r, c2 - min_c)

        # -------------------------------------------------------------
        # Case B: GeoTIFF products (hirise-holden, ctx-tyrrhena, ctx-apollinaris, mola-4ppd)
        # -------------------------------------------------------------
        with rasterio.open(elev_path) as src_elev, rasterio.open(slope_path) as src_slope:
            transform = src_elev.transform
            bounds = src_elev.bounds
            is_proj = "Equirectangular" in str(src_elev.crs) or "49910" in str(src_elev.crs)

            if is_proj:
                # Projected IAU:49910 Equirectangular
                norm_lon1 = start_lon % 360.0
                norm_lon2 = dest_lon % 360.0
                if bounds.right <= 0 or (bounds.left < 0 and norm_lon1 > 180.0):
                    proj_lon1 = norm_lon1 - 360.0 if norm_lon1 > 180.0 else norm_lon1
                    proj_lon2 = norm_lon2 - 360.0 if norm_lon2 > 180.0 else norm_lon2
                else:
                    proj_lon1 = norm_lon1
                    proj_lon2 = norm_lon2

                x1 = MARS_RADIUS_M * math.radians(proj_lon1)
                y1 = MARS_RADIUS_M * math.radians(start_lat)
                x2 = MARS_RADIUS_M * math.radians(proj_lon2)
                y2 = MARS_RADIUS_M * math.radians(dest_lat)

                r1, c1 = rowcol(transform, x1, y1)
                r2, c2 = rowcol(transform, x2, y2)
                dx_m = abs(transform[0])
                dy_m = abs(transform[4])
            else:
                # Geographic IAU:49900 (e.g. mola-4ppd)
                r1, c1 = rowcol(transform, start_lon % 360.0, start_lat)
                r2, c2 = rowcol(transform, dest_lon % 360.0, dest_lat)
                d_lat_deg = abs(transform[4])
                d_lon_deg = abs(transform[0])
                lat_center = (start_lat + dest_lat) / 2.0
                dy_m = (math.pi / 180.0) * MARS_RADIUS_M * d_lat_deg
                dx_m = (math.pi / 180.0) * MARS_RADIUS_M * math.cos(math.radians(lat_center)) * d_lon_deg

            # Clamp coordinates to raster bounds
            h, w = src_elev.height, src_elev.width
            r1 = max(0, min(r1, h - 1))
            c1 = max(0, min(c1, w - 1))
            r2 = max(0, min(r2, h - 1))
            c2 = max(0, min(c2, w - 1))

            span_r = abs(r2 - r1)
            span_c = abs(c2 - c1)
            margin = max(min_margin_px, int(max(span_r, span_c) * margin_pct))

            min_r = max(0, min(r1, r2) - margin)
            max_r = min(h, max(r1, r2) + margin + 1)
            min_c = max(0, min(c1, c2) - margin)
            max_c = min(w, max(c1, c2) + margin + 1)

            win_h = max_r - min_r
            win_w = max_c - min_c

            if win_h > max_window_dim or win_w > max_window_dim:
                raise ValueError(
                    f"Route window ({win_h}x{win_w} px) exceeds computational limit ({max_window_dim}x{max_window_dim} px). "
                    "Select closer coordinates or use a coarser resolution tier."
                )

            win = Window(min_c, min_r, win_w, win_h)
            sub_elev = src_elev.read(1, window=win).astype(np.float32)
            sub_slope = src_slope.read(1, window=win).astype(np.float32)

            # If slope shape doesn't match elevation shape (e.g. edge cases), recompute Horn slope
            if sub_slope.shape != sub_elev.shape:
                sub_slope = cls._compute_horn_slope_grid(sub_elev, dy_m, dx_m, nodata_val=source.get("nodata_elev", -32767.0))

            grid = BoundedTerrainGrid(
                source_info=source,
                elevation=sub_elev,
                slope=sub_slope,
                row_offset=min_r,
                col_offset=min_c,
                transform=transform,
                is_projected=is_proj,
                dx_m=dx_m,
                dy_m=dy_m,
            )

            return grid, (r1 - min_r, c1 - min_c), (r2 - min_r, c2 - min_c)

    @staticmethod
    def _compute_horn_slope_grid(elev: np.ndarray, dy: float, dx: float, nodata_val: float = -32768.0) -> np.ndarray:
        """Vectorized Horn slope computation over 2D elevation grid in degrees."""
        rows, cols = elev.shape
        slope = np.full((rows, cols), fill_value=nodata_val, dtype=np.float32)

        # Pad elevation to handle edges
        padded = np.pad(elev, ((1, 1), (1, 1)), mode="edge")
        z1 = padded[0:-2, 0:-2]
        z2 = padded[0:-2, 1:-1]
        z3 = padded[0:-2, 2:]
        z4 = padded[1:-1, 0:-2]
        z5 = padded[1:-1, 1:-1]
        z6 = padded[1:-1, 2:]
        z7 = padded[2:, 0:-2]
        z8 = padded[2:, 1:-1]
        z9 = padded[2:, 2:]

        valid_mask = (
            (z1 > nodata_val + 1.0) & (z2 > nodata_val + 1.0) & (z3 > nodata_val + 1.0) &
            (z4 > nodata_val + 1.0) & (z5 > nodata_val + 1.0) & (z6 > nodata_val + 1.0) &
            (z7 > nodata_val + 1.0) & (z8 > nodata_val + 1.0) & (z9 > nodata_val + 1.0) &
            ~np.isnan(z5)
        )

        dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx)
        dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy)

        grad = np.sqrt(dz_dx**2 + dz_dy**2)
        slope_deg = np.degrees(np.arctan(grad))

        slope[valid_mask] = slope_deg[valid_mask]
        return slope

    @staticmethod
    def snap_to_passable(
        grid: BoundedTerrainGrid,
        start_rc: Tuple[int, int],
        max_slope_deg: float,
        search_radius: int = 15,
    ) -> Tuple[int, int]:
        """Snap coordinate to nearest passable pixel if initial cell is NoData or steep."""
        r, c = start_rc
        if grid.is_passable(r, c, max_slope_deg):
            return r, c

        best_cell = None
        best_dist_sq = float("inf")

        for dr in range(-search_radius, search_radius + 1):
            for dc in range(-search_radius, search_radius + 1):
                nr, nc = r + dr, c + dc
                if grid.is_passable(nr, nc, max_slope_deg):
                    d_sq = dr * dr + dc * dc
                    if d_sq < best_dist_sq:
                        best_dist_sq = d_sq
                        best_cell = (nr, nc)

        if best_cell is None:
            raise ValueError(
                f"Waypoint at ({r}, {c}) is inside impassable terrain (slope > {max_slope_deg}° or NoData) "
                f"and no passable pixel exists within {search_radius} pixels."
            )
        return best_cell

    @classmethod
    def plan_route(cls, request: MarswalkRouteRequest) -> MarswalkRouteResponse:
        """Execute full terrain-aware A* or Dijkstra pathfinding and telemetry calculation."""
        # Check deterministic request cache first
        cached = get_cached_route_by_request(request)
        if cached is not None:
            return cached

        t0 = time.perf_counter()

        # Step 1: Source selection
        source = cls.select_source(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            dest_lat=request.dest_lat,
            dest_lon=request.dest_lon,
            preferred_source=request.preferred_source,
        )

        # Step 2: Grid window extraction
        grid, start_rc, goal_rc = cls.extract_grid_window(
            source=source,
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            dest_lat=request.dest_lat,
            dest_lon=request.dest_lon,
        )

        # Step 3: Coordinate snapping to passable cells
        snapped_start_rc = cls.snap_to_passable(grid, start_rc, request.max_slope_deg)
        snapped_goal_rc = cls.snap_to_passable(grid, goal_rc, request.max_slope_deg)

        snapped_start_lat, snapped_start_lon = grid.cell_to_lat_lon(*snapped_start_rc)
        snapped_dest_lat, snapped_dest_lon = grid.cell_to_lat_lon(*snapped_goal_rc)

        # Step 4: Pathfinding (A* or Dijkstra)
        algo = getattr(request, "algorithm", "astar") or "astar"
        path_cells, search_stats = cls._run_astar(
            grid=grid,
            start_rc=snapped_start_rc,
            goal_rc=snapped_goal_rc,
            slope_penalty_factor=request.slope_penalty_factor,
            max_slope_deg=request.max_slope_deg,
            max_nodes=request.max_search_nodes,
            algorithm=algo,
        )

        # Step 5: Metrics & Telemetry calculation
        path_points: List[MarswalkRoutePoint] = []
        cum_dist = 0.0
        elev_gain = 0.0
        elev_loss = 0.0
        max_slope = 0.0
        weighted_slope_sum = 0.0
        total_horiz_dist = 0.0

        # Exposure tracking in metres (distance-weighted)
        exposure_meters = {"low": 0.0, "moderate": 0.0, "high": 0.0, "very_high": 0.0, "unknown": 0.0}

        geojson_coords: List[List[float]] = []

        for i, (r, c) in enumerate(path_cells):
            lat, lon = grid.cell_to_lat_lon(r, c)
            elev = float(grid.elevation[r, c])
            slope_val = float(grid.slope[r, c])
            category = classify_slope(slope_val).value

            if i > 0:
                prev_r, prev_c = path_cells[i - 1]
                prev_elev = float(grid.elevation[prev_r, prev_c])
                dr = r - prev_r
                dc = c - prev_c
                dy, dx = grid.get_cell_spacing(prev_r)
                d_horiz = math.sqrt((dc * dx) ** 2 + (dr * dy) ** 2)
                dz = elev - prev_elev
                d_surf = math.sqrt(d_horiz**2 + dz**2)

                cum_dist += d_surf
                total_horiz_dist += d_horiz
                weighted_slope_sum += d_surf * slope_val

                if dz > 0:
                    elev_gain += dz
                else:
                    elev_loss += abs(dz)

                exposure_meters[category] += d_surf
            else:
                exposure_meters[category] += 0.0

            max_slope = max(max_slope, slope_val)

            path_points.append(
                MarswalkRoutePoint(
                    index=i,
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    elevation_m=round(elev, 2),
                    slope_deg=round(slope_val, 2),
                    slope_category=category,
                    cumulative_distance_m=round(cum_dist, 2),
                )
            )
            geojson_coords.append([round(lon, 6), round(lat, 6)])

        n_pts = len(path_cells)
        # Length-weighted mean slope across traversed segments
        mean_slope = (weighted_slope_sum / cum_dist) if cum_dist > 0.0 else (path_points[0].slope_deg if path_points else 0.0)

        # Distance-weighted percentages across standard analytical slope bands
        exposure_pct = {}
        if cum_dist > 0.0:
            for cat, dist_m in exposure_meters.items():
                exposure_pct[cat] = round((dist_m / cum_dist) * 100.0, 2)
        else:
            first_cat = path_points[0].slope_category if path_points else "low"
            for cat in exposure_meters.keys():
                exposure_pct[cat] = 100.0 if cat == first_cat else 0.0

        total_duration_ms = (time.perf_counter() - t0) * 1000.0
        search_stats["total_duration_ms"] = round(total_duration_ms, 2)
        search_stats["grid_window_shape"] = [grid.rows, grid.cols]
        search_stats["path_length_nodes"] = n_pts
        search_stats["algorithm"] = algo

        elevations = [p.elevation_m for p in path_points]
        min_elev = min(elevations) if elevations else 0.0
        max_elev = max(elevations) if elevations else 0.0

        total_opt_cost = round(float(search_stats.get("total_path_cost", cum_dist)), 2)
        route_id = f"mw-{uuid.uuid4().hex[:12]}"

        response = MarswalkRouteResponse(
            route_id=route_id,
            status="success",
            route_name=request.route_name or f"Marswalk Traverse {source['source_id']}",
            start_coord=(request.start_lat, request.start_lon % 360.0),
            dest_coord=(request.dest_lat, request.dest_lon % 360.0),
            snapped_start_coord=(round(snapped_start_lat, 6), round(snapped_start_lon, 6)),
            snapped_dest_coord=(round(snapped_dest_lat, 6), round(snapped_dest_lon, 6)),
            source_dataset=source["source_id"],
            instrument=source["instrument"],
            tier=source["tier"],
            native_resolution_m=source["pixel_spacing_m"],
            native_resolution_desc=source["pixel_spacing_desc"],
            vertical_datum=source["vertical_datum"],
            vertical_datum_type=source["vertical_datum_type"],
            total_surface_distance_m=round(cum_dist, 2),
            total_horizontal_distance_m=round(total_horiz_dist, 2),
            total_optimization_cost=total_opt_cost,
            cumulative_elevation_gain_m=round(elev_gain, 2),
            cumulative_elevation_loss_m=round(elev_loss, 2),
            min_elevation_m=round(min_elev, 2),
            max_elevation_m=round(max_elev, 2),
            max_route_slope_deg=round(max_slope, 2),
            mean_route_slope_deg=round(mean_slope, 2),
            slope_band_exposure_pct=exposure_pct,
            unknown_data_exposure_pct=exposure_pct.get("unknown", 0.0),
            geometry={
                "type": "LineString",
                "coordinates": geojson_coords,
            },
            path_points=path_points,
            cost_function_parameters={
                "slope_penalty_factor_beta": request.slope_penalty_factor,
                "reference_slope_deg": THETA_REF_DEG,
                "max_slope_cutoff_deg": request.max_slope_deg,
                "algorithm": algo,
                "formula": "Cost(u, v) = d_surface * [1.0 + beta * (theta_v / 15.0)^2]",
            },
            search_metrics=search_stats,
            coverage_limitations=(
                f"Computed over {source['source_id']} ({source['pixel_spacing_desc']}). "
                f"Vertical datum: {source['vertical_datum']}."
            ),
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
        )

        _cache_route(response, request_hash=compute_request_hash(request, resolved_source_id=source["source_id"]))
        return response

    @classmethod
    def _run_astar(
        cls,
        grid: BoundedTerrainGrid,
        start_rc: Tuple[int, int],
        goal_rc: Tuple[int, int],
        slope_penalty_factor: float,
        max_slope_deg: float,
        max_nodes: int,
        algorithm: str = "astar",
    ) -> Tuple[List[Tuple[int, int]], Dict[str, Any]]:
        """Core A* or Dijkstra pathfinding algorithm on 8-connected bounded DEM."""
        t_search_start = time.perf_counter()

        if start_rc == goal_rc:
            return [start_rc], {
                "nodes_expanded": 0,
                "nodes_visited": 1,
                "search_duration_ms": 0.0,
                "total_path_cost": 0.0,
            }

        goal_r, goal_c = goal_rc
        goal_elev = float(grid.elevation[goal_r, goal_c])

        # Precompute destination coordinate for spherical great-circle heuristic (geographic grids only)
        if not grid.is_projected and grid.lat_top is not None:
            goal_lat, goal_lon = grid.cell_to_lat_lon(goal_r, goal_c)
            goal_phi = math.radians(goal_lat)
            goal_lam = math.radians(goal_lon)
        else:
            goal_phi = 0.0
            goal_lam = 0.0

        def heuristic(r: int, c: int) -> float:
            """Admissible and consistent 3D Euclidean distance lower bound.

            Returns 0.0 under Dijkstra mode, guaranteeing uniform-cost search.
            Under A* mode:
            - Projected grids: exact planimetric Euclidean distance.
            - Geographic grids: exact spherical Great-Circle geodesic distance.
            Combined with vertical delta_z via Minkowski lower bound.
            """
            if algorithm == "dijkstra" or (r == goal_r and c == goal_c):
                return 0.0

            if not grid.is_projected and grid.lat_top is not None:
                cur_lat, cur_lon = grid.cell_to_lat_lon(r, c)
                cur_phi = math.radians(cur_lat)
                cur_lam = math.radians(cur_lon)
                dphi = goal_phi - cur_phi
                dlam = goal_lam - cur_lam
                a = (
                    math.sin(dphi * 0.5) ** 2
                    + math.cos(cur_phi) * math.cos(goal_phi) * (math.sin(dlam * 0.5) ** 2)
                )
                d_horiz = 2.0 * MARS_RADIUS_M * math.asin(min(1.0, math.sqrt(max(0.0, a))))
            else:
                dy, dx = grid.get_cell_spacing(r)
                d_horiz = math.sqrt(((goal_c - c) * dx) ** 2 + ((goal_r - r) * dy) ** 2)

            cur_elev = float(grid.elevation[r, c])
            dz = goal_elev - cur_elev
            return 0.999 * math.sqrt(d_horiz**2 + dz**2)

        # Priority queue item: (f_score, g_score, (r, c))
        h_start = heuristic(start_rc[0], start_rc[1])
        open_set = [(h_start, 0.0, start_rc)]

        g_score: Dict[Tuple[int, int], float] = {start_rc: 0.0}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_set = set()

        nodes_expanded = 0

        # 8-connected neighbor deltas
        deltas = [
            (-1, 0), (1, 0), (0, -1), (0, 1),      # orthogonal
            (-1, -1), (-1, 1), (1, -1), (1, 1),    # diagonal
        ]

        while open_set:
            if nodes_expanded >= max_nodes:
                raise TimeoutError(
                    f"A* search exceeded maximum node expansion limit ({max_nodes} nodes). "
                    "The destination is either too distant or completely walled by impassable terrain."
                )

            _, current_g, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == goal_rc:
                # Goal reached! Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                search_ms = (time.perf_counter() - t_search_start) * 1000.0
                return path, {
                    "nodes_expanded": nodes_expanded,
                    "nodes_visited": len(g_score),
                    "search_duration_ms": round(search_ms, 2),
                    "total_path_cost": round(current_g, 2),
                }

            closed_set.add(current)
            nodes_expanded += 1
            cr, cc = current
            cur_elev = float(grid.elevation[cr, cc])
            cur_dy, cur_dx = grid.get_cell_spacing(cr)

            for dr, dc in deltas:
                nr = cr + dr
                nc = cc + dc

                # Hard constraint: target cell passability
                if not grid.is_passable(nr, nc, max_slope_deg):
                    continue

                # Hard constraint: diagonal corner-cutting prevention
                if dr != 0 and dc != 0:
                    if not grid.is_passable(cr + dr, cc, max_slope_deg) or not grid.is_passable(cr, cc + dc, max_slope_deg):
                        continue

                neighbor = (nr, nc)
                if neighbor in closed_set:
                    continue

                # Metric surface step
                step_x = dc * cur_dx
                step_y = dr * cur_dy
                d_horiz = math.sqrt(step_x**2 + step_y**2)
                dz = float(grid.elevation[nr, nc]) - cur_elev
                d_surf = math.sqrt(d_horiz**2 + dz**2)

                # Quadratic slope penalty on destination cell
                theta_v = float(grid.slope[nr, nc])
                slope_penalty = slope_penalty_factor * ((theta_v / THETA_REF_DEG) ** 2)
                edge_cost = d_surf * (1.0 + slope_penalty)

                tentative_g = current_g + edge_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h_val = heuristic(nr, nc)
                    f_val = tentative_g + h_val
                    heapq.heappush(open_set, (f_val, tentative_g, neighbor))

        raise RuntimeError(
            f"No valid path exists between start {start_rc} and destination {goal_rc} "
            f"within slope threshold {max_slope_deg}° and available DEM coverage."
        )

    @classmethod
    def _run_dijkstra(
        cls,
        grid: BoundedTerrainGrid,
        start_rc: Tuple[int, int],
        goal_rc: Tuple[int, int],
        slope_penalty_factor: float,
        max_slope_deg: float,
        max_nodes: int = 150000,
    ) -> Tuple[List[Tuple[int, int]], Dict[str, Any]]:
        """Uniform-cost search benchmark using zero-heuristic Dijkstra."""
        return cls._run_astar(
            grid=grid,
            start_rc=start_rc,
            goal_rc=goal_rc,
            slope_penalty_factor=slope_penalty_factor,
            max_slope_deg=max_slope_deg,
            max_nodes=max_nodes,
            algorithm="dijkstra",
        )

    @classmethod
    def get_metadata(cls) -> MarswalkMetadataResponse:
        """Return engine capabilities, supported tiers, parameters, and presets."""
        supported = []
        for s in TERRAIN_SOURCES:
            supported.append({
                "source_id": s["source_id"],
                "instrument": s["instrument"],
                "tier": s["tier"],
                "pixel_spacing_m": s["pixel_spacing_m"],
                "pixel_spacing_desc": s["pixel_spacing_desc"],
                "crs": s["crs"],
                "vertical_datum": s["vertical_datum"],
                "lat_bounds": [s["lat_min"], s["lat_max"]],
                "lon_bounds": [s["lon_min"], s["lon_max"]],
                "coverage_note": s["coverage_note"],
                "available_on_disk": os.path.isfile(s["elev_path"]),
            })

        tiers = [
            {"tier": "local_tactical", "resolution": "~1 m/px", "dataset": "hirise-holden", "purpose": "Fine boulder/outcrop hazard avoidance"},
            {"tier": "regional", "resolution": "~20 m/px", "dataset": "ctx-tyrrhena, ctx-apollinaris", "purpose": "Valley network and yardang ridge navigation"},
            {"tier": "regional_base", "resolution": "~463 m/px", "dataset": "mola-128ppd", "purpose": "Regional highland terrain traverse"},
            {"tier": "global_coarse", "resolution": "~14.8 km/px", "dataset": "mola-4ppd", "purpose": "Global interplanetary synoptic context"},
        ]

        return MarswalkMetadataResponse(
            supported_datasets=supported,
            resolution_tiers=tiers,
            slope_thresholds_deg=SLOPE_THRESHOLDS,
            default_parameters={
                "slope_penalty_factor": 2.0,
                "reference_slope_deg": THETA_REF_DEG,
                "max_slope_deg": 25.0,
                "max_search_nodes": 150000,
                "preferred_source": "auto",
            },
            cost_function_definition="Cost(u, v) = d_surface * [1.0 + beta * (theta_v / 15.0)^2]",
            heuristic_definition="h(u, G) = 0.999 * sqrt(D_horiz(u, G)^2 + (z_G - z_u)^2)",
            engine_versions={
                "algorithm_version": MARSWALK_ALGORITHM_VERSION,
                "cost_function_version": MARSWALK_COST_FUNCTION_VERSION,
                "derivative_version": MARSWALK_DERIVATIVE_VERSION,
            },
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
            validated_corridors=VALIDATED_CORRIDORS,
        )
