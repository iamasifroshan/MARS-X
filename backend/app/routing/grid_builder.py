"""Terrain Grid Builder for Mars Route Planning.

Extracts memory-efficient sub-windows using np.memmap on authentic MOLA 128 ppd rasters,
snaps mission start/destination coordinates to valid pixel centers, computes local metric
cell dimensions, and enforces strict coverage boundaries.
"""

import os
import math
import numpy as np
from typing import Tuple, Optional, Dict, Any

from app.geospatial import MARS_EQUATORIAL_RADIUS_M
from app.routing.route_models import ExclusionZone

# Authoritative MOLA 128 tile megt00n000hb constants
MOLA_128_LINES = 5632
MOLA_128_SAMPLES = 11520
MOLA_128_PPD = 128.0
MOLA_128_PIXEL_DEG = 1.0 / 128.0  # 0.0078125 degrees

MOLA_128_LAT_MIN = -44.0
MOLA_128_LAT_MAX = 0.0
MOLA_128_LON_MIN = 0.0
MOLA_128_LON_MAX = 90.0

MOLA_128_RAW_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw", "mola", "megt00n000hb.img")
)
MOLA_128_CHECKSUM = "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"


class TerrainGridWindow:
    """Bounded, locally-extracted 2D terrain elevation grid with georeferencing."""

    def __init__(
        self,
        elevation_grid: np.ndarray,
        row_offset: int,
        col_offset: int,
        lat_top: float,
        lon_left: float,
        d_lat_deg: float = MOLA_128_PIXEL_DEG,
        d_lon_deg: float = MOLA_128_PIXEL_DEG,
    ):
        self.elevation = elevation_grid
        self.rows, self.cols = elevation_grid.shape
        self.row_offset = row_offset
        self.col_offset = col_offset
        self.lat_top = lat_top
        self.lon_left = lon_left
        self.d_lat_deg = d_lat_deg
        self.d_lon_deg = d_lon_deg

        # Precompute 1D coordinate vectors in radians for exact spherical geodesy
        row_indices = np.arange(self.rows)
        col_indices = np.arange(self.cols)
        self.row_lats_rad = np.radians(self.lat_top - (row_indices + 0.5) * self.d_lat_deg)
        self.col_lons_rad = np.radians(self.lon_left + (col_indices + 0.5) * self.d_lon_deg)
        self.row_cos_lat = np.cos(self.row_lats_rad)
        self.row_sin_lat = np.sin(self.row_lats_rad)

    def row_col_to_lat_lon(self, r: int, c: int) -> Tuple[float, float]:
        """Convert local grid row/col to planetocentric lat/lon (pixel center)."""
        lat = self.lat_top - (r + 0.5) * self.d_lat_deg
        lon = self.lon_left + (c + 0.5) * self.d_lon_deg
        return lat, lon

    def lat_lon_to_row_col(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat/lon to nearest local grid row/col."""
        r = int(math.floor((self.lat_top - lat) / self.d_lat_deg))
        c = int(math.floor((lon - self.lon_left) / self.d_lon_deg))
        return r, c

    def is_in_bounds(self, r: int, c: int) -> bool:
        """Check if row/col is inside the local window."""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def get_cell_metric_spacing(self, r: int) -> Tuple[float, float]:
        """Compute metric cell spacing (dy, dx) in metres for a specific row latitude."""
        lat = self.lat_top - (r + 0.5) * self.d_lat_deg
        lat_rad = math.radians(lat)
        dy = (math.pi / 180.0) * MARS_EQUATORIAL_RADIUS_M * self.d_lat_deg
        dx = (math.pi / 180.0) * MARS_EQUATORIAL_RADIUS_M * math.cos(lat_rad) * self.d_lon_deg
        return dy, dx


class TerrainGridBuilder:
    """Manages coordinate validation, snapping, and bounded window extraction from MOLA 128."""

    def __init__(self, raw_path: Optional[str] = None):
        self.raw_path = raw_path or MOLA_128_RAW_PATH
        if not os.path.exists(self.raw_path):
            raise FileNotFoundError(
                f"Authentic MOLA 128 ppd raster not found at: {self.raw_path}. "
                "Route planning requires validated local raster data."
            )
        # Open as memory-mapped array without loading 124MB into memory
        self._memmap = np.memmap(
            self.raw_path,
            dtype=">i2",
            mode="r",
            shape=(MOLA_128_LINES, MOLA_128_SAMPLES),
        )

    @staticmethod
    def is_coordinate_in_footprint(lat: float, lon: float) -> bool:
        """Verify whether coordinate is strictly inside megt00n000hb footprint."""
        norm_lon = lon % 360.0
        return (
            MOLA_128_LAT_MIN <= lat <= MOLA_128_LAT_MAX
            and MOLA_128_LON_MIN <= norm_lon <= MOLA_128_LON_MAX
        )

    def snap_coordinate(
        self, lat: float, lon: float, max_snap_dist_m: float = 2000.0
    ) -> Tuple[float, float, float, int, int]:
        """Snap arbitrary lat/lon to nearest valid pixel center.

        Returns: (snapped_lat, snapped_lon, snap_dist_m, global_row, global_col)
        """
        if not self.is_coordinate_in_footprint(lat, lon):
            raise ValueError(
                f"Requested coordinate ({lat:.4f}°N, {lon:.4f}°E) is outside the validated "
                f"MOLA 128 planning footprint (Lat [{MOLA_128_LAT_MIN}°, {MOLA_128_LAT_MAX}°], "
                f"Lon [{MOLA_128_LON_MIN}°, {MOLA_128_LON_MAX}°E])."
            )

        norm_lon = lon % 360.0
        # Calculate global line and sample
        # Latitude 0.0 is line 0; Latitude -44.0 is line 5632
        line = int(round((MOLA_128_LAT_MAX - lat) * MOLA_128_PPD - 0.5))
        sample = int(round((norm_lon - MOLA_128_LON_MIN) * MOLA_128_PPD - 0.5))

        line = max(0, min(line, MOLA_128_LINES - 1))
        sample = max(0, min(sample, MOLA_128_SAMPLES - 1))

        # Pixel center coordinates
        snapped_lat = MOLA_128_LAT_MAX - (line + 0.5) * MOLA_128_PIXEL_DEG
        snapped_lon = MOLA_128_LON_MIN + (sample + 0.5) * MOLA_128_PIXEL_DEG

        # Metric distance between requested and snapped
        lat_rad = math.radians((lat + snapped_lat) / 2.0)
        d_lat_m = math.radians(lat - snapped_lat) * MARS_EQUATORIAL_RADIUS_M
        d_lon_m = math.radians(norm_lon - snapped_lon) * MARS_EQUATORIAL_RADIUS_M * math.cos(lat_rad)
        dist_m = math.sqrt(d_lat_m**2 + d_lon_m**2)

        if dist_m > max_snap_dist_m:
            raise ValueError(
                f"Coordinate snapping distance ({dist_m:.1f} m) exceeds maximum allowed limit ({max_snap_dist_m:.1f} m)."
            )

        # Check for NoData at pixel
        elev = int(self._memmap[line, sample])
        if elev == -32768:
            raise ValueError(f"Snapped coordinate falls on an impassable NoData pixel ({snapped_lat:.4f}°, {snapped_lon:.4f}°).")

        return snapped_lat, snapped_lon, dist_m, line, sample

    def extract_bounded_window(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        margin_pixels: int = 25,
        max_window_pixels: int = 500,
    ) -> Tuple[TerrainGridWindow, Tuple[int, int], Tuple[int, int]]:
        """Extract a memory-efficient local window encompassing start and destination.

        Returns: (TerrainGridWindow, (start_r, start_c), (dest_r, dest_c))
        """
        _, _, _, r1, c1 = self.snap_coordinate(start_lat, start_lon)
        _, _, _, r2, c2 = self.snap_coordinate(dest_lat, dest_lon)

        min_r = min(r1, r2) - margin_pixels
        max_r = max(r1, r2) + margin_pixels
        min_c = min(c1, c2) - margin_pixels
        max_c = max(c1, c2) + margin_pixels

        # Clip to tile bounds
        min_r = max(0, min_r)
        max_r = min(MOLA_128_LINES, max_r + 1)
        min_c = max(0, min_c)
        max_c = min(MOLA_128_SAMPLES, max_c + 1)

        span_r = max_r - min_r
        span_c = max_c - min_c

        if span_r > max_window_pixels or span_c > max_window_pixels:
            raise ValueError(
                f"Requested route window ({span_r}x{span_c} pixels) exceeds safety limit ({max_window_pixels}x{max_window_pixels} pixels). "
                "Select closer waypoints for local Marswalk traverse planning."
            )

        # Slice sub-array and convert to float32
        sub_grid = np.array(self._memmap[min_r:max_r, min_c:max_c], dtype=np.float32)

        lat_top = MOLA_128_LAT_MAX - min_r * MOLA_128_PIXEL_DEG
        lon_left = MOLA_128_LON_MIN + min_c * MOLA_128_PIXEL_DEG

        window = TerrainGridWindow(
            elevation_grid=sub_grid,
            row_offset=min_r,
            col_offset=min_c,
            lat_top=lat_top,
            lon_left=lon_left,
        )

        start_local = (r1 - min_r, c1 - min_c)
        dest_local = (r2 - min_r, c2 - min_c)

        return window, start_local, dest_local
