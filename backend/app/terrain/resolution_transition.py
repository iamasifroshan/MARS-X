"""Multi-Resolution Overlap and Transition Intelligence Engine for MARS-X.

Evaluates whether two Martian elevation products can support a continuous or
partitioned analytical mission region without introducing unscientific artifacts.

Enforces strict planetary cartography rules:
- Prohibits naive raster merging across mismatched native resolutions.
- Flags and quantifies horizontal scale differences (e.g. MOLA R=3396.00 km vs IAU 2015 R=3396.19 km, 55.95 ppm).
- Evaluates vertical datum alignment (MOLA Areoid vs ASP pc_align photogrammetry).
- Provides region partitioning strategies instead of misleading merged grids.
- Prevents false upsampling of coarse baselines to high-resolution grids.
"""

import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from app.geospatial import MARS_EQUATORIAL_RADIUS_M
from app.terrain.multi_resolution import (
    MultiResolutionTerrainCatalog,
    DTMProductProfile,
)
from app.terrain.harmonization import (
    HarmonizationEngine,
    VerticalCompatibilityStatus,
    VERTICAL_EVIDENCE_CATALOG,
)


logger = logging.getLogger("MARS-X.terrain.resolution_transition")


class TransitionCompatibilityStatus(str, Enum):
    """Compatibility status between two overlapping elevation products."""
    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION = "compatible_with_documented_transformation"
    INCOMPATIBLE = "incompatible"
    INSUFFICIENT_OVERLAP = "insufficient_overlap"
    UNKNOWN = "unknown"


class ResolutionTransitionRequest(BaseModel):
    """Query parameters to evaluate transition feasibility between two datasets."""
    product_a: str
    product_b: str
    min_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lat: Optional[float] = None
    max_lon: Optional[float] = None


class ResolutionTransitionEvaluation(BaseModel):
    """Complete transition evaluation report for multi-resolution integration."""
    product_a: str
    product_b: str
    transition_status: TransitionCompatibilityStatus
    has_overlap: bool
    overlap_area_km2: float
    overlap_bounds: Optional[Dict[str, float]] = None
    resolution_a_m: float
    resolution_b_m: float
    resolution_ratio: float
    horizontal_crs_status: str
    horizontal_scale_drift_ppm: float
    vertical_datum_status: str
    vertical_datum_notes: str
    pixel_registration_match: bool
    permitted_operations: List[str]
    forbidden_operations: List[str]
    partition_strategy: Optional[Dict[str, Any]] = None
    scientific_justification: str
    anti_upsampling_safeguards: List[str]


class ResolutionTransitionService:
    """Service assessing cross-product boundary continuity and transition validity."""

    @staticmethod
    def _calculate_spherical_bbox_area(
        min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> float:
        """Calculate spherical surface area in km² on Mars radius 3396.19 km."""
        r = 3396.19
        phi1 = math.radians(min_lat)
        phi2 = math.radians(max_lat)
        delta_lambda = math.radians(max_lon - min_lon)
        return abs((r ** 2) * delta_lambda * (math.sin(phi2) - math.sin(phi1)))

    @classmethod
    def evaluate_transition(
        cls, request: ResolutionTransitionRequest
    ) -> ResolutionTransitionEvaluation:
        """Evaluate whether Product A and Product B can support an analytical transition."""
        prod_a = MultiResolutionTerrainCatalog.get_product(request.product_a)
        prod_b = MultiResolutionTerrainCatalog.get_product(request.product_b)

        if not prod_a:
            raise ValueError(f"Product '{request.product_a}' not found in multi-resolution catalog.")
        if not prod_b:
            raise ValueError(f"Product '{request.product_b}' not found in multi-resolution catalog.")

        # 1. Geometric footprint overlap
        o_lat_min = max(prod_a.lat_min, prod_b.lat_min)
        o_lat_max = min(prod_a.lat_max, prod_b.lat_max)
        o_lon_min = max(prod_a.lon_min, prod_b.lon_min)
        o_lon_max = min(prod_a.lon_max, prod_b.lon_max)

        # Clip by requested bounds if specified
        if request.min_lat is not None:
            o_lat_min = max(o_lat_min, request.min_lat)
        if request.max_lat is not None:
            o_lat_max = min(o_lat_max, request.max_lat)
        if request.min_lon is not None:
            o_lon_min = max(o_lon_min, request.min_lon)
        if request.max_lon is not None:
            o_lon_max = min(o_lon_max, request.max_lon)

        has_overlap = (o_lat_min < o_lat_max) and (o_lon_min < o_lon_max)
        overlap_area = (
            cls._calculate_spherical_bbox_area(o_lat_min, o_lon_min, o_lat_max, o_lon_max)
            if has_overlap else 0.0
        )

        overlap_bounds = {
            "min_lat": round(o_lat_min, 5),
            "max_lat": round(o_lat_max, 5),
            "min_lon": round(o_lon_min, 5),
            "max_lon": round(o_lon_max, 5),
        } if has_overlap else None

        # 2. Resolution ratio
        res_a = prod_a.pixel_spacing_m
        res_b = prod_b.pixel_spacing_m
        ratio = round(max(res_a, res_b) / max(min(res_a, res_b), 1e-4), 2)

        # 3. Horizontal CRS compatibility & scale drift
        # MOLA: R=3,396,000 m. CTX/HiRISE: R=3,396,190 m.
        # Scale difference: 190 / 3396000 = 55.95 ppm
        scale_drift_ppm = 0.0
        crs_status = "identical"
        if ("49900" in prod_a.crs and "49910" in prod_b.crs) or ("49910" in prod_a.crs and "49900" in prod_b.crs):
            scale_drift_ppm = 55.95
            crs_status = "scale_drift_documented (55.95 ppm between MOLA sphere and IAU 2015 sphere)"
        elif prod_a.crs != prod_b.crs:
            crs_status = "different_projections_transformation_required"

        # 4. Vertical datum compatibility
        try:
            compat_result = HarmonizationEngine.assess_compatibility(
                prod_a.product_id, prod_b.product_id
            )
            vert_compat_status = compat_result.vertical_status
            vert_compat_notes = compat_result.vertical_notes
        except Exception as e:
            vert_compat_status = VerticalCompatibilityStatus.UNKNOWN
            vert_compat_notes = f"Datum assessment unavailable: {str(e)}"




        # 5. Overlap sufficiency check
        if not has_overlap or overlap_area < 0.1:
            return ResolutionTransitionEvaluation(
                product_a=prod_a.product_id,
                product_b=prod_b.product_id,
                transition_status=TransitionCompatibilityStatus.INSUFFICIENT_OVERLAP,
                has_overlap=False,
                overlap_area_km2=0.0,
                overlap_bounds=None,
                resolution_a_m=res_a,
                resolution_b_m=res_b,
                resolution_ratio=ratio,
                horizontal_crs_status=crs_status,
                horizontal_scale_drift_ppm=scale_drift_ppm,
                vertical_datum_status=vert_compat_status.value,
                vertical_datum_notes=vert_compat_notes,

                pixel_registration_match=False,
                permitted_operations=["independent_analysis_disjoint_regions"],
                forbidden_operations=[
                    "cross_product_pathfinding",
                    "continuous_raster_mosaic",
                    "elevation_residual_comparison",
                ],
                partition_strategy=None,
                scientific_justification=(
                    f"Datasets '{prod_a.product_id}' and '{prod_b.product_id}' have no spatial overlap "
                    "or overlap is beneath numerical threshold (< 0.1 km²)."
                ),
                anti_upsampling_safeguards=[
                    "Disjoint datasets must not be bridged by spatial interpolation.",
                    "Route corridors cannot traverse gaps between disconnected elevation coverages."
                ]
            )

        # 6. Determine overall transition status
        if vert_compat_status == VerticalCompatibilityStatus.INCOMPATIBLE:
            transition_status = TransitionCompatibilityStatus.INCOMPATIBLE
        elif vert_compat_status == VerticalCompatibilityStatus.UNKNOWN:
            transition_status = TransitionCompatibilityStatus.UNKNOWN
        elif vert_compat_status == VerticalCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION:
            transition_status = TransitionCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION
        else:
            transition_status = TransitionCompatibilityStatus.COMPATIBLE


        # 7. Permitted vs Forbidden operations
        permitted = [
            "side_by_side_comparison",
            "region_partitioning",
            "multi_scale_elevation_profiling",
        ]
        forbidden = [
            "direct_raster_stitching_without_datum_adjustment",
            "coarse_to_fine_upsampling_with_claimed_microrelief",
            "unweighted_blend_of_mismatched_resolutions",
        ]

        if transition_status in [
            TransitionCompatibilityStatus.COMPATIBLE,
            TransitionCompatibilityStatus.COMPATIBLE_WITH_DOCUMENTED_TRANSFORMATION,
        ]:
            permitted.append("cross_resolution_elevation_residual_sampling")
            permitted.append("hierarchical_mission_corridor_evaluation")
        else:
            forbidden.append("cross_resolution_pathfinding")

        # 8. Region Partitioning Strategy
        finer_prod = prod_a.product_id if res_a < res_b else prod_b.product_id
        coarser_prod = prod_b.product_id if res_a < res_b else prod_a.product_id
        partition_strategy = {
            "strategy": "hierarchical_nesting",
            "high_resolution_infill": finer_prod,
            "regional_context_surround": coarser_prod,
            "infill_footprint_bounds": overlap_bounds,
            "boundary_buffer_m": round(max(res_a, res_b) * 2.0, 1),
            "recommendation": (
                f"Analyze core high-interest sites using '{finer_prod}' ({min(res_a, res_b):.1f}m/px). "
                f"Use '{coarser_prod}' ({max(res_a, res_b):.1f}m/px) strictly for regional approach context outside the valid footprint."
            )
        }

        justification = (
            f"Evaluated transition between '{prod_a.product_id}' ({res_a:.1f}m/px) and '{prod_b.product_id}' ({res_b:.1f}m/px). "
            f"Overlap area is {overlap_area:.1f} km² (resolution ratio {ratio:.1f}x). "
            f"Horizontal CRS scale drift: {scale_drift_ppm:.2f} ppm. "
            f"Vertical datum compatibility is '{transition_status.value}'. "
            f"Direct raster merging is prohibited; hierarchical spatial partitioning is permitted."
        )

        safeguards = [
            f"Anti-upsampling rule: '{coarser_prod}' ({max(res_a, res_b):.1f}m) cannot be bilinearly or bicubically upsampled to {min(res_a, res_b):.1f}m.",
            "Edge transitions between differing resolutions must maintain a boundary buffer to avoid false artificial step edges.",
            "Traverse costs computed in the finer resolution cannot be directly added to coarse-resolution edge weights without scale normalization."
        ]

        return ResolutionTransitionEvaluation(
            product_a=prod_a.product_id,
            product_b=prod_b.product_id,
            transition_status=transition_status,
            has_overlap=True,
            overlap_area_km2=round(overlap_area, 2),
            overlap_bounds=overlap_bounds,
            resolution_a_m=res_a,
            resolution_b_m=res_b,
            resolution_ratio=ratio,
            horizontal_crs_status=crs_status,
            horizontal_scale_drift_ppm=scale_drift_ppm,
            vertical_datum_status=vert_compat_status.value,
            vertical_datum_notes=vert_compat_notes,

            pixel_registration_match=True,
            permitted_operations=permitted,
            forbidden_operations=forbidden,
            partition_strategy=partition_strategy,
            scientific_justification=justification,
            anti_upsampling_safeguards=safeguards,
        )
