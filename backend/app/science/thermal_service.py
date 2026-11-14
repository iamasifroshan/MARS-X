"""Thermal Inertia and THEMIS Infrared Services for MARS-X.

Authoritative Scientific Integration:
1. MGS TES Global Thermal Inertia (Putzig & Mellon 2007)
   - Dayside: DBmap2007.tif (20 ppd, Simple Cylindrical Mars)
   - Nightside: NBmap2007.tif (20 ppd, Simple Cylindrical Mars)
   - Physical unit: Thermal Inertia Units (tiu = J m^-2 K^-1 s^-1/2)
   - Prohibits labeling as temperature.

2. 2001 Mars Odyssey THEMIS 100m Infrared Regional Mosaics
   - Daytime IR: thm_dir_N-30_000.png (256 ppd, lat -30° to 0°, lon 0° to 30°E)
   - Nighttime IR: themis_nightir_N-30_000.png (256 ppd, lat -30° to 0°, lon 0° to 30°E)
   - Qualitative 8-bit visual display mosaic only (Band 9 12.57 um).
   - Direct quantitative temperature / radiance conversion is prohibited.
"""

import os
import math
import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window
from rasterio.enums import Resampling

logger = logging.getLogger("MARS-X.science.thermal_service")


class TESThermalInertiaService:
    """Service for querying and rendering MGS TES Global Thermal Inertia (Putzig & Mellon 2007).
    
    Calibration Methodology:
    - Data sources: DBmap2007.tif (dayside) and NBmap2007.tif (nightside), 7200x3600 pixels (20 ppd).
    - Image format: 3-band uint8 RGB color-mapped using the IDL rainbow palette.
    - Calibration reverse-lookup: Extracted 790 distinct RGB colors from tes_putzigti_dayside2007_label.jpg.
    - Mathematical formula: I = 50.0 * (50.0 ** t) tiu, where t in [0.0, 1.0] across the 790 steps.
    - Range: 50.0 to 2500.0 tiu (Thermal Inertia Units = J m^-2 K^-1 s^-1/2).
    - Measurement status: Legend-calibrated estimates (not directly measured spectrometer radiances).
    - Quantization uncertainty: ~2.5% step-to-step color quantization and nearest-neighbor uncertainty.
    """

    _instance: Optional["TESThermalInertiaService"] = None

    def __init__(self, data_root: Optional[str] = None):
        if data_root is None:
            self.data_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "originals", "themis")
            )
        else:
            self.data_root = data_root

        self.dayside_path = os.path.join(self.data_root, "DBmap2007.tif")
        self.nightside_path = os.path.join(self.data_root, "NBmap2007.tif")
        self.label_path = os.path.join(self.data_root, "tes_putzigti_dayside2007_label.jpg")

        self.width = 7200
        self.height = 3600
        self.ppd = 20.0
        self.min_lon = -180.0
        self.max_lon = 180.0
        self.min_lat = -90.0
        self.max_lat = 90.0

        # Build calibration color table from label image
        self._init_calibration_lut()

    def _init_calibration_lut(self):
        """Extract the 790 calibrated color steps and construct the log-tiu lookup table."""
        try:
            if os.path.exists(self.label_path):
                with rasterio.open(self.label_path) as src:
                    # Colorbar at y=2000, x=1050..1839 (790 pixels)
                    bar = src.read(window=Window(1050, 2000, 790, 1)) # shape (3, 1, 790)
                    self.bar_colors = bar[:, 0, :].T.astype(np.float32) # shape (790, 3)
            else:
                self.bar_colors = None
        except Exception as e:
            logger.warning("Failed to extract color table from label jpg: %s", e)
            self.bar_colors = None

        if self.bar_colors is not None and len(self.bar_colors) > 0:
            n_steps = len(self.bar_colors)
            t_vals = np.linspace(0.0, 1.0, n_steps)
            # Logarithmic range from 50.0 to 2500.0 tiu: I = 50.0 * 50.0^t
            self.ti_values = 50.0 * (50.0 ** t_vals)
        else:
            self.bar_colors = None
            self.ti_values = None

    def get_metadata(self) -> Dict[str, Any]:
        """Return dataset metadata, calibration formula, and scientific context."""
        return {
            "dataset_id": "tes-thermal-inertia-putzig-2007",
            "product_id": "TES_PUTZIG_TI_2007",
            "instrument": "Thermal Emission Spectrometer (TES)",
            "mission": "Mars Global Surveyor (MGS)",
            "citation": "Putzig, N. E., & Mellon, M. T. (2007). Apparent thermal inertia and the surface heterogeneity of Mars. Icarus, 191(1), 68-94.",
            "physical_property": "Apparent Thermal Inertia (I = sqrt(k * rho * c))",
            "units": "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
            "raster_dimensions": {"width": self.width, "height": self.height, "pixels_per_degree": self.ppd},
            "spatial_coverage": {"min_lon": -180.0, "max_lon": 180.0, "min_lat": -90.0, "max_lat": 90.0},
            "raster_format": "3-band 8-bit RGB color image (IDL rainbow palette representation)",
            "calibration": {
                "method": "790-step reverse lookup table extracted from published label colorbar (x=1050..1839, y=2000)",
                "formula": "I(t) = 50.0 * (50.0 ** t) [tiu], where t = i / 789 for step index i in [0, 789]",
                "endpoints_tiu": {"i_0": 50.0, "i_789": 2500.0},
                "mathematical_step_resolution_pct": 0.50,
                "quantization_uncertainty_pct": 2.5,
                "uncertainty_status": "unvalidated_nominal_estimate",
                "uncertainty_statement": (
                    "Unvalidated nominal proxy estimate. Mathematical step resolution of the 790-step log LUT is ~0.50%; "
                    "the nominal +/-2.5% color-matching quantization window is an uncalibrated proxy. Radiometric accuracy "
                    "cannot be established without direct comparison to calibrated TES spectral radiances."
                ),
                "range_tiu": {"min": 50.0, "max": 2500.0, "scale": "logarithmic"},
                "measurement_status": "legend_calibrated_estimate (not direct spectrometer radiance)",
            },
            "products": {
                "dayside": {"file": "DBmap2007.tif", "exists": os.path.exists(self.dayside_path)},
                "nightside": {"file": "NBmap2007.tif", "exists": os.path.exists(self.nightside_path)},
            },
            "prohibition_disclaimer": (
                "Thermal inertia is a thermophysical property representing resistance to temperature change, "
                "NOT temperature. Never label or treat these values as kinetic temperature or surface heat."
            ),
        }

    def _coord_to_pixel(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat, lon (in planetary degrees) to pixel row and column."""
        # Normalize lon to [-180, 180]
        norm_lon = lon % 360.0
        if norm_lon > 180.0:
            norm_lon -= 360.0

        col = int(math.floor((norm_lon - self.min_lon) * self.ppd))
        row = int(math.floor((self.max_lat - lat) * self.ppd))

        col = max(0, min(col, self.width - 1))
        row = max(0, min(row, self.height - 1))
        return row, col

    def _interpret_thermal_inertia(self, ti: float) -> str:
        """Provide indicative surface-property interpretation based on Putzig & Mellon (2007)."""
        if ti < 90.0:
            return "Indicative: Fine, unindurated aeolian dust mantle (> several mm thick); high atmospheric insulation"
        elif ti < 180.0:
            return "Indicative: Fine to medium aeolian sand with incipient thin duricrust"
        elif ti < 350.0:
            return "Indicative: Medium to coarse sand, cemented soil, or duricrust layers"
        elif ti < 600.0:
            return "Indicative: Coarse sand, granule lag, fragmented rocks, or eroded duricrust surfaces"
        elif ti < 1200.0:
            return "Indicative: Rocky plains, high boulder abundance, cemented duricrust, or partially exposed bedrock"
        else:
            return "Indicative: Dense boulder fields, massive rock exposures, or cohesive solid bedrock"

    def query_point(self, lat: float, lon: float, product: str = "dayside") -> Dict[str, Any]:
        """Query calibrated thermal inertia at a Martian coordinate."""
        file_path = self.dayside_path if product.lower() == "dayside" else self.nightside_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Thermal raster file not found: {file_path}")

        row, col = self._coord_to_pixel(lat, lon)

        with rasterio.open(file_path) as src:
            # Read 1x1 window
            rgb = src.read(window=Window(col, row, 1, 1)) # shape (3, 1, 1)
            r = int(rgb[0, 0, 0])
            g = int(rgb[1, 0, 0])
            b = int(rgb[2, 0, 0])

        # Check NoData (0, 0, 0)
        is_nodata = (r == 0 and g == 0 and b == 0)

        if is_nodata or self.bar_colors is None:
            return {
                "latitude": lat,
                "longitude": lon,
                "product": product,
                "thermal_inertia_tiu": None,
                "calibrated_thermal_inertia_estimate_tiu": None,
                "units": "J m^-2 K^-1 s^-1/2 (Thermal Inertia)",
                "is_nodata": True,
                "physical_interpretation": "Unmeasured or masked polar / shadowed region",
                "pixel_row": row,
                "pixel_col": col,
                "raw_rgb": [r, g, b],
                "calibration_status": "nodata",
                "quantization_uncertainty_pct": None,
            }

        # Find nearest calibrated color
        target_color = np.array([r, g, b], dtype=np.float32)
        diffs = np.sum((self.bar_colors - target_color) ** 2, axis=1)
        best_idx = int(np.argmin(diffs))
        ti_val = float(round(self.ti_values[best_idx], 1))
        interpretation = self._interpret_thermal_inertia(ti_val)

        return {
            "latitude": lat,
            "longitude": lon,
            "product": product,
            "thermal_inertia_tiu": ti_val,
            "calibrated_thermal_inertia_estimate_tiu": ti_val,
            "units": "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
            "is_nodata": False,
            "physical_interpretation": interpretation,
            "pixel_row": row,
            "pixel_col": col,
            "raw_rgb": [r, g, b],
            "citation": "Putzig & Mellon (2007), Icarus 191, 68-94",
            "calibration_status": "legend_calibrated_estimate",
            "mathematical_step_resolution_pct": 0.50,
            "quantization_uncertainty_pct": 2.5,
            "uncertainty_status": "unvalidated_nominal_estimate",
            "uncertainty_statement": (
                "Unvalidated nominal proxy estimate. Mathematical step resolution of the 790-step log LUT is ~0.50%; "
                "the +/-2.5% color-matching window is an uncalibrated proxy. Radiometric accuracy cannot be established "
                "without direct comparison to calibrated TES spectral radiances."
            ),
            "estimation_method": "Putzig 2007 790-step logarithmic colorbar reverse lookup",
        }

    def render_window(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        product: str = "dayside",
        width: int = 256,
        height: int = 256,
    ) -> bytes:
        """Render a viewport window from the authentic Putzig 2007 raster as RGBA PNG."""
        file_path = self.dayside_path if product.lower() == "dayside" else self.nightside_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Thermal raster file not found: {file_path}")

        # Normalize coordinates
        def _norm(x: float) -> float:
            x = x % 360.0
            return x - 360.0 if x > 180.0 else x

        n_min_lon = _norm(min_lon)
        n_max_lon = _norm(max_lon)
        if n_min_lon > n_max_lon:
            n_min_lon, n_max_lon = n_max_lon, n_min_lon

        row_top, col_left = self._coord_to_pixel(max_lat, n_min_lon)
        row_bot, col_right = self._coord_to_pixel(min_lat, n_max_lon)

        window_w = max(1, col_right - col_left + 1)
        window_h = max(1, row_bot - row_top + 1)

        with rasterio.open(file_path) as src:
            window = Window(col_left, row_top, window_w, window_h)
            # Read and resample
            rgb_data = src.read(
                window=window,
                out_shape=(3, height, width),
                resampling=Resampling.bilinear,
            )

        r = rgb_data[0]
        g = rgb_data[1]
        b = rgb_data[2]

        rgba = np.zeros((4, height, width), dtype=np.uint8)
        rgba[0] = r
        rgba[1] = g
        rgba[2] = b
        # Alpha is 0 for pure black (NoData), 240 otherwise
        is_valid = (r > 0) | (g > 0) | (b > 0)
        rgba[3] = np.where(is_valid, 240, 0).astype(np.uint8)

        with MemoryFile() as memfile:
            with memfile.open(
                driver="PNG",
                height=height,
                width=width,
                count=4,
                dtype=np.uint8,
            ) as dst:
                dst.write(rgba)
            return memfile.read()


class THEMISInfraredService:
    """Service for rendering 2001 Mars Odyssey THEMIS 100m Infrared Regional Mosaics."""

    _instance: Optional["THEMISInfraredService"] = None

    def __init__(self, data_root: Optional[str] = None):
        if data_root is None:
            self.data_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "originals", "themis")
            )
        else:
            self.data_root = data_root

        self.day_path = os.path.join(self.data_root, "thm_dir_N-30_000.png")
        self.night_path = os.path.join(self.data_root, "themis_nightir_N-30_000.png")

        # Regional tile N-30_000 footprint
        self.footprint_min_lat = -30.0
        self.footprint_max_lat = 0.0
        self.footprint_min_lon = 0.0
        self.footprint_max_lon = 30.0
        self.tile_pixels = 7680
        self.ppd = 256.0

    def get_metadata(self) -> Dict[str, Any]:
        """Return THEMIS IR mosaic metadata, resolution audit, and strict qualitative usage instructions."""
        return {
            "dataset_id": "themis-ir-mosaics-regional",
            "product_id": "THEMIS_IR_MOSAICS_256PPD_REGIONAL",
            "title": "2001 Mars Odyssey THEMIS Regional Infrared Mosaic (256 ppd, ~231.5 m/px)",
            "instrument": "Thermal Emission Imaging System (THEMIS)",
            "mission": "2001 Mars Odyssey",
            "archive": "ASU Mars Space Flight Facility / THEMIS Science Team",
            "regional_tile": "N-30_000 (Sinus Meridiani / Tyrrhena corridor)",
            "footprint": {
                "min_lat": self.footprint_min_lat,
                "max_lat": self.footprint_max_lat,
                "min_lon": self.footprint_min_lon,
                "max_lon": self.footprint_max_lon,
            },
            "nominal_instrument_nadir_resolution_m": 100.0,
            "delivered_mosaic_grid_resolution_ppd": 256.0,
            "delivered_pixel_width_equator_m": 231.55,
            "delivered_pixel_width_min_lat_m": 200.52,
            "is_raw_100m_raster": False,
            "native_camera_resolution": "100 m/px at 430 km circular orbit (nadir pointing)",
            "mosaic_grid_resolution": "256 ppd (equatorial pixel width ~231.55 m/px, reducing to ~200.5 m/px at -30° latitude due to cosine convergence)",
            "resolution": "256 ppd (~231.55 m/px equatorial)",
            "resolution_qualification": (
                "The 100 m/px descriptor refers exclusively to the THEMIS instrument's native nadir camera optics. "
                "The actual downloaded regional product (thm_dir_N-30_000.png) is gridded at 256 ppd (~231.55 m/px equatorial). "
                "It is NOT a 100 m/px raster."
            ),
            "pixel_format": "8-bit grayscale display DN (0-255)",
            "products": {
                "day_ir": {"file": "thm_dir_N-30_000.png", "exists": os.path.exists(self.day_path)},
                "night_ir": {"file": "themis_nightir_N-30_000.png", "exists": os.path.exists(self.night_path)},
            },
            "measurement_semantics": {
                "type": "Qualitative 8-bit visual display mosaic (Band 9, 12.57 um)",
                "quantitative_analysis_supported": False,
                "temperature_prohibition_note": (
                    "Pixel values represent non-linearly tone-mapped visual display values (0-255 DN). "
                    "Conversion to brightness temperature (K) or radiance is scientifically invalid and prohibited. "
                    "For physical thermophysical properties, query the calibrated TES Thermal Inertia service."
                ),
            },
        }

    def render_window(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        mode: str = "day",
        width: int = 256,
        height: int = 256,
    ) -> bytes:
        """Render a viewport window from the authentic THEMIS 100m IR mosaic as RGBA PNG."""
        file_path = self.day_path if mode.lower() == "day" else self.night_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"THEMIS mosaic file not found: {file_path}")

        # Check footprint overlap
        if (
            max_lat < self.footprint_min_lat
            or min_lat > self.footprint_max_lat
            or max_lon < self.footprint_min_lon
            or min_lon > self.footprint_max_lon
        ):
            # Outside regional tile: return transparent image
            rgba = np.zeros((4, height, width), dtype=np.uint8)
            with MemoryFile() as memfile:
                with memfile.open(driver="PNG", height=height, width=width, count=4, dtype=np.uint8) as dst:
                    dst.write(rgba)
                return memfile.read()

        # Clamp query to regional footprint
        q_min_lat = max(min_lat, self.footprint_min_lat)
        q_max_lat = min(max_lat, self.footprint_max_lat)
        q_min_lon = max(min_lon, self.footprint_min_lon)
        q_max_lon = min(max_lon, self.footprint_max_lon)

        col_left = int(round((q_min_lon - self.footprint_min_lon) * self.ppd))
        col_right = int(round((q_max_lon - self.footprint_min_lon) * self.ppd))
        row_top = int(round((self.footprint_max_lat - q_max_lat) * self.ppd))
        row_bot = int(round((self.footprint_max_lat - q_min_lat) * self.ppd))

        col_left = max(0, min(col_left, self.tile_pixels - 1))
        col_right = max(0, min(col_right, self.tile_pixels - 1))
        row_top = max(0, min(row_top, self.tile_pixels - 1))
        row_bot = max(0, min(row_bot, self.tile_pixels - 1))

        w = max(1, col_right - col_left)
        h = max(1, row_bot - row_top)

        with rasterio.open(file_path) as src:
            window = Window(col_left, row_top, w, h)
            # Read band 1 (grayscale display)
            data = src.read(1, window=window, out_shape=(height, width), resampling=Resampling.bilinear)

        rgba = np.zeros((4, height, width), dtype=np.uint8)
        rgba[0] = data
        rgba[1] = data
        rgba[2] = data
        # Alpha is 240 where DN > 0
        rgba[3] = np.where(data > 0, 240, 0).astype(np.uint8)

        with MemoryFile() as memfile:
            with memfile.open(
                driver="PNG",
                height=height,
                width=width,
                count=4,
                dtype=np.uint8,
            ) as dst:
                dst.write(rgba)
            return memfile.read()


def get_thermal_service() -> TESThermalInertiaService:
    """Retrieve singleton TESThermalInertiaService."""
    if TESThermalInertiaService._instance is None:
        TESThermalInertiaService._instance = TESThermalInertiaService()
    return TESThermalInertiaService._instance


def get_themis_service() -> THEMISInfraredService:
    """Retrieve singleton THEMISInfraredService."""
    if THEMISInfraredService._instance is None:
        THEMISInfraredService._instance = THEMISInfraredService()
    return THEMISInfraredService._instance
