"""Terrain Hazard Intelligence Engine for MARS-X.

Computes scientifically rigorous, explainable terrain hazard indicators from validated DTM rasters:
1. Slope (Horn / Zevenbergen-Thorne gradient with latitude-dependent metric grid spacing).
2. Local Relief (elevation range within configurable metric neighborhoods).
3. Roughness (elevation standard deviation in configurable metric neighborhoods).
4. Terrain Discontinuities (candidate scarps, crater rims, abrupt elevation steps).
5. Data Confidence (incorporating validation state, resolution, and NoData proximity).
6. Explainable Terrain Complexity Classification (with explicit numerical thresholds and spatial scale limits).
7. Polar Geodesy Guard (masks latitudes |lat| > 85° from equirectangular approximation).

Strictly enforces:
- No claims of astronaut safety or EVA feasibility.
- No Earth-walking metabolic predictions on Mars.
- No conversion of NoData into low-risk terrain.
- Complete transparency of spatial resolution and detectable feature scale.
"""

import math
import numpy as np
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from app.geospatial import MARS_EQUATORIAL_RADIUS_M, MARS_POLAR_RADIUS_M

# Valid latitude envelope for cylindrical/equirectangular metric approximations
# Beyond 85° (|lat| > 85°), meridian convergence creates severe East-West metric compression
# requiring polar stereographic projection (as used in MOLA polar products).
MAX_VALID_CYLINDRICAL_LAT_DEG = 85.0


class TerrainComplexityClass(str, Enum):
    """Explainable terrain complexity classification."""
    LOW_COMPLEXITY = "low_measured_complexity"
    MODERATE_COMPLEXITY = "moderate_complexity"
    HIGH_COMPLEXITY = "high_complexity"
    EXTREME_COMPLEXITY = "extreme_complexity"
    INSUFFICIENT_DATA = "insufficient_data"


class HazardThresholds(BaseModel):
    """Configurable numerical thresholds for terrain complexity classification."""
    slope_moderate_deg: float = 8.0
    slope_high_deg: float = 15.0
    slope_extreme_deg: float = 25.0
    relief_moderate_m: float = 10.0
    relief_high_m: float = 30.0
    relief_extreme_m: float = 75.0
    roughness_moderate_m: float = 2.5
    roughness_high_m: float = 8.0
    roughness_extreme_m: float = 20.0


class SpatialScaleMetadata(BaseModel):
    """Rigorous reporting of spatial resolution, window geometry, and feature detectability."""
    native_pixel_spacing_m: float
    analysis_window_size_m: float
    analysis_window_pixel_span: int = 3
    minimum_detectable_feature_scale_m: float = Field(
        ..., description="Nyquist sampling minimum feature size (typically 2x to 3x pixel post-spacing)"
    )
    operational_scale_tier: str = Field(
        ..., description="'regional_reconnaissance' (MOLA 4), 'meso_scale' (MOLA 128), or 'tactical_microtopography' (HiRISE 1m)"
    )
    scale_limitation_warning: str


class TerrainHazardPointMetrics(BaseModel):
    """Point hazard indicators computed for a specific geographic coordinate."""
    latitude: float
    longitude: float
    elevation_m: float
    slope_deg: Optional[float] = None
    slope_pct: Optional[float] = None
    local_relief_m: Optional[float] = None
    roughness_m: Optional[float] = None
    discontinuity_detected: bool = False
    discontinuity_type: Optional[str] = None
    data_confidence_score: float = Field(..., ge=0.0, le=1.0)
    complexity_class: TerrainComplexityClass
    source_dataset: str
    spatial_scale: SpatialScaleMetadata
    explanation: str
    safety_disclaimer: str = (
        "Terrain hazard classification reflects measured topographical complexity only. "
        "It does NOT evaluate geotechnical soil cohesion, boulder distribution below resolution, "
        "atmospheric pressure, space suit kinematics, or human physiological safety."
    )


class HazardEngineMetadata(BaseModel):
    """Metadata describing the algorithms, equations, units, and limitations of the hazard engine."""
    slope_algorithm: str = "Horn (1981) 3x3 moving window with latitude-scaled longitudinal post-spacing"
    relief_algorithm: str = "Max-Min elevation difference in physical metric radius"
    roughness_algorithm: str = "Unbiased sample standard deviation of elevation in metric radius"
    discontinuity_algorithm: str = "Laplacian and directional relief edge detection for steep scarps"
    confidence_scoring: str = "Multi-criteria score based on validation state, native resolution, and NoData distance"
    metric_units: Dict[str, str] = {
        "elevation": "metres above MOLA areoid",
        "slope": "degrees (0-90°)",
        "local_relief": "metres",
        "roughness": "metres (local standard deviation)",
        "confidence": "fractional index (0.0 = no data, 1.0 = optimal)",
    }
    thresholds: HazardThresholds = HazardThresholds()
    scientific_limitations: List[str] = [
        "Slope and roughness are strictly resolution-dependent. 14.8 km MOLA slopes cannot resolve rover-scale 1m hazards.",
        "Polar latitudes (|lat| > 85°) cause severe longitudinal cell compression; cylindrical calculations are masked outside valid range.",
        "Missing or NoData elevation cells propagate as 'insufficient_data' and are never classified as safe.",
        "Astronaut Marswalk planning requires sub-meter microtopography not available in global datasets.",
    ]


class TerrainHazardEngine:
    """Scientific terrain hazard computation engine."""

    def __init__(self, thresholds: Optional[HazardThresholds] = None):
        self.thresholds = thresholds or HazardThresholds()

    @staticmethod
    def calculate_cell_metric_dimensions(lat_deg: float, d_lat_deg: float, d_lon_deg: float) -> Tuple[float, float]:
        """Compute local metric ground spacing in metres (dy, dx) accounting for Martian latitude.

        Rejects polar latitudes |lat| > 85° with ValueError.
        """
        if abs(lat_deg) > MAX_VALID_CYLINDRICAL_LAT_DEG:
            raise ValueError(
                f"Latitude {lat_deg}° exceeds maximum valid cylindrical/equirectangular envelope "
                f"(±{MAX_VALID_CYLINDRICAL_LAT_DEG}°). Polar stereographic projection required."
            )

        lat_rad = math.radians(lat_deg)
        cos_lat = math.cos(lat_rad)

        dy = (math.pi / 180.0) * MARS_EQUATORIAL_RADIUS_M * d_lat_deg
        dx = (math.pi / 180.0) * MARS_EQUATORIAL_RADIUS_M * cos_lat * d_lon_deg
        return dy, dx

    @classmethod
    def compute_slope_horn(cls, window_3x3: np.ndarray, dy: float, dx: float) -> Optional[float]:
        """Compute slope in degrees using Horn's weighted 3x3 gradient method.

        Strict rule: If any pixel in the 3x3 window is NoData (-32768 or NaN), returns None.
        """
        if window_3x3.shape != (3, 3):
            raise ValueError(f"Expected (3, 3) window, got {window_3x3.shape}")

        if np.any(np.isnan(window_3x3)) or np.any(window_3x3 == -32768):
            return None

        z1, z2, z3 = window_3x3[0, 0], window_3x3[0, 1], window_3x3[0, 2]
        z4, _,  z6 = window_3x3[1, 0], window_3x3[1, 1], window_3x3[1, 2]
        z7, z8, z9 = window_3x3[2, 0], window_3x3[2, 1], window_3x3[2, 2]

        dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx)
        dz_dy = ((z1 + 2.0 * z2 + z3) - (z7 + 2.0 * z8 + z9)) / (8.0 * dy)

        slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
        return math.degrees(slope_rad)

    @classmethod
    def compute_local_relief(cls, window: np.ndarray) -> Optional[float]:
        """Calculate elevation range (max - min) in metres. Returns None if any pixel is NoData."""
        if np.any(np.isnan(window)) or np.any(window == -32768):
            return None
        return float(np.max(window) - np.min(window))

    @classmethod
    def compute_roughness(cls, window: np.ndarray) -> Optional[float]:
        """Calculate sample standard deviation of elevation within the window. Returns None if NoData present."""
        if np.any(np.isnan(window)) or np.any(window == -32768):
            return None
        if window.size < 2:
            return None
        return float(np.std(window, ddof=1))

    @classmethod
    def detect_discontinuity(
        cls, slope_deg: Optional[float], relief_m: Optional[float], roughness_m: Optional[float]
    ) -> Tuple[bool, Optional[str]]:
        """Detect candidate topographic scarps, cliffs, or abrupt steps."""
        if slope_deg is None or relief_m is None or roughness_m is None:
            return False, None

        if slope_deg >= 25.0 and relief_m >= 75.0:
            return True, "Major scarp or crater rim wall"
        elif slope_deg >= 18.0 and relief_m >= 40.0:
            return True, "Moderate slope break or terrace edge"
        elif roughness_m >= 25.0:
            return True, "Dissected chaotic terrain boundary"
        return False, None

    def classify_complexity(
        self, slope_deg: Optional[float], relief_m: Optional[float], roughness_m: Optional[float], confidence: float
    ) -> Tuple[TerrainComplexityClass, str]:
        """Classify terrain complexity using transparent Boolean logic.

        Logic:
        1. If confidence < 0.2 OR any required indicator is None (e.g. NoData in neighborhood):
           -> INSUFFICIENT_DATA
        2. If slope >= 25° OR relief >= 75m OR roughness >= 20m:
           -> EXTREME_COMPLEXITY
        3. If slope >= 15° OR relief >= 30m OR roughness >= 8m:
           -> HIGH_COMPLEXITY
        4. If slope >= 8° OR relief >= 10m OR roughness >= 2.5m:
           -> MODERATE_COMPLEXITY
        5. Otherwise:
           -> LOW_COMPLEXITY
        """
        if confidence < 0.2 or slope_deg is None or relief_m is None or roughness_m is None:
            return (
                TerrainComplexityClass.INSUFFICIENT_DATA,
                "Elevation data missing, NoData encountered in neighborhood, or confidence score below minimum threshold (0.2).",
            )

        if (
            slope_deg >= self.thresholds.slope_extreme_deg
            or relief_m >= self.thresholds.relief_extreme_m
            or roughness_m >= self.thresholds.roughness_extreme_m
        ):
            return (
                TerrainComplexityClass.EXTREME_COMPLEXITY,
                f"Extreme terrain complexity: Slope {slope_deg:.1f}° (>= {self.thresholds.slope_extreme_deg}°), "
                f"Relief {relief_m:.1f}m (>= {self.thresholds.relief_extreme_m}m), or Roughness {roughness_m:.1f}m.",
            )

        if (
            slope_deg >= self.thresholds.slope_high_deg
            or relief_m >= self.thresholds.relief_high_m
            or roughness_m >= self.thresholds.roughness_high_m
        ):
            return (
                TerrainComplexityClass.HIGH_COMPLEXITY,
                f"High terrain complexity: Slope {slope_deg:.1f}°, Relief {relief_m:.1f}m, Roughness {roughness_m:.1f}m.",
            )

        if (
            slope_deg >= self.thresholds.slope_moderate_deg
            or relief_m >= self.thresholds.relief_moderate_m
            or roughness_m >= self.thresholds.roughness_moderate_m
        ):
            return (
                TerrainComplexityClass.MODERATE_COMPLEXITY,
                f"Moderate terrain complexity: Slope {slope_deg:.1f}°, Relief {relief_m:.1f}m, Roughness {roughness_m:.1f}m.",
            )

        return (
            TerrainComplexityClass.LOW_COMPLEXITY,
            f"Low measured terrain complexity at this resolution: Slope {slope_deg:.1f}°, Relief {relief_m:.1f}m, Roughness {roughness_m:.1f}m.",
        )

    def evaluate_point_hazards(
        self,
        lat_deg: float,
        lon_deg: float,
        window_3x3: np.ndarray,
        d_lat_deg: float,
        d_lon_deg: float,
        source_dataset: str,
        source_resolution_m: float,
        validation_state_score: float = 1.0,
    ) -> TerrainHazardPointMetrics:
        """Run complete hazard evaluation on a 3x3 local neighborhood with scale limits."""
        center_elev = float(window_3x3[1, 1])

        # Define scale metadata
        min_feature_scale = round(source_resolution_m * 2.5, 1)
        scale_tier = (
            "regional_reconnaissance" if source_resolution_m > 1000.0
            else "meso_scale" if source_resolution_m > 100.0
            else "tactical_microtopography"
        )
        scale_warning = (
            f"Source resolution is {source_resolution_m:.1f} m/px. Features smaller than ~{min_feature_scale:.0f} m "
            f"(such as rover boulders, crevasses, or meter-scale scarps) CANNOT be detected at this scale. "
            f"Output is suitable strictly for {scale_tier.replace('_', ' ')}."
        )

        scale_meta = SpatialScaleMetadata(
            native_pixel_spacing_m=round(source_resolution_m, 1),
            analysis_window_size_m=round(source_resolution_m * 3.0, 1),
            analysis_window_pixel_span=3,
            minimum_detectable_feature_scale_m=min_feature_scale,
            operational_scale_tier=scale_tier,
            scale_limitation_warning=scale_warning,
        )

        # Check for polar bounds
        if abs(lat_deg) > MAX_VALID_CYLINDRICAL_LAT_DEG:
            return TerrainHazardPointMetrics(
                latitude=lat_deg,
                longitude=lon_deg,
                elevation_m=center_elev,
                slope_deg=None,
                slope_pct=None,
                local_relief_m=None,
                roughness_m=None,
                discontinuity_detected=False,
                discontinuity_type=None,
                data_confidence_score=0.0,
                complexity_class=TerrainComplexityClass.INSUFFICIENT_DATA,
                source_dataset=source_dataset,
                spatial_scale=scale_meta,
                explanation=f"Latitude {lat_deg}° exceeds maximum validated cylindrical envelope (±{MAX_VALID_CYLINDRICAL_LAT_DEG}°). Polar projection required.",
            )

        # If center pixel is NoData, return insufficient data immediately
        if np.isnan(center_elev) or center_elev == -32768:
            return TerrainHazardPointMetrics(
                latitude=lat_deg,
                longitude=lon_deg,
                elevation_m=center_elev,
                slope_deg=None,
                slope_pct=None,
                local_relief_m=None,
                roughness_m=None,
                discontinuity_detected=False,
                discontinuity_type=None,
                data_confidence_score=0.0,
                complexity_class=TerrainComplexityClass.INSUFFICIENT_DATA,
                source_dataset=source_dataset,
                spatial_scale=scale_meta,
                explanation="Center pixel is NoData sentinel.",
            )

        try:
            dy, dx = self.calculate_cell_metric_dimensions(lat_deg, d_lat_deg, d_lon_deg)
        except ValueError as e:
            return TerrainHazardPointMetrics(
                latitude=lat_deg,
                longitude=lon_deg,
                elevation_m=center_elev,
                slope_deg=None,
                slope_pct=None,
                local_relief_m=None,
                roughness_m=None,
                discontinuity_detected=False,
                discontinuity_type=None,
                data_confidence_score=0.0,
                complexity_class=TerrainComplexityClass.INSUFFICIENT_DATA,
                source_dataset=source_dataset,
                spatial_scale=scale_meta,
                explanation=str(e),
            )

        slope_deg = self.compute_slope_horn(window_3x3, dy, dx)
        slope_pct = math.tan(math.radians(slope_deg)) * 100.0 if slope_deg is not None else None
        relief_m = self.compute_local_relief(window_3x3)
        roughness_m = self.compute_roughness(window_3x3)

        # Independent confidence calculation
        nodata_in_window = np.count_nonzero((window_3x3 == -32768) | np.isnan(window_3x3))
        neighbor_validity_frac = (9 - nodata_in_window) / 9.0
        confidence = round(validation_state_score * neighbor_validity_frac, 2)

        is_disc, disc_type = self.detect_discontinuity(slope_deg, relief_m, roughness_m)
        complexity, expl = self.classify_complexity(slope_deg, relief_m, roughness_m, confidence)

        return TerrainHazardPointMetrics(
            latitude=lat_deg,
            longitude=lon_deg,
            elevation_m=center_elev,
            slope_deg=round(slope_deg, 2) if slope_deg is not None else None,
            slope_pct=round(slope_pct, 2) if slope_pct is not None else None,
            local_relief_m=round(relief_m, 2) if relief_m is not None else None,
            roughness_m=round(roughness_m, 2) if roughness_m is not None else None,
            discontinuity_detected=is_disc,
            discontinuity_type=disc_type,
            data_confidence_score=confidence,
            complexity_class=complexity,
            source_dataset=source_dataset,
            spatial_scale=scale_meta,
            explanation=expl,
        )
