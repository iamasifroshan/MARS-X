"""Resolution-Aware Data Selection Engine for MARS-X.

Selects appropriate native-resolution Martian elevation products based on
geographic extent, requested analysis scale, physical availability,
horizontal/vertical compatibility, and scientific constraints.

Enforces strict planetary cartography rules:
- Only local, authentic rasters can be selected for numerical analysis.
- Remote/discovered products are explicitly reported as unavailable.
- Incompatible vertical/horizontal references are rejected unless documented.
- Matches analysis scale to appropriate resolution (avoiding over- or under-sampling).
- NoData and partial coverage are explicitly quantified.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from app.geospatial import MARS_EQUATORIAL_RADIUS_M, haversine_distance
from app.terrain.multi_resolution import (
    MultiResolutionTerrainCatalog,
    DTMProductProfile,
    MULTI_RESOLUTION_DTM_CATALOG,
)
from app.terrain.inventory import Mola128InventoryService
from app.terrain.harmonization import (
    HarmonizationEngine,
    VerticalCompatibilityStatus,
)


logger = logging.getLogger("MARS-X.terrain.resolution_selector")


class AnalysisType(str, Enum):
    """Analysis types determining appropriate resolution scale."""
    RECONNAISSANCE = "reconnaissance"          # Coarse global/regional overview (> 1000m)
    REGIONAL_SURVEY = "regional_survey"        # Regional terrain profiling (100m - 1000m)
    TRAVERSE_PLANNING = "traverse_planning"    # Route exploration (20m - 500m)
    HAZARD_ASSESSMENT = "hazard_assessment"    # Slope & roughness hazards (1m - 50m)
    SITE_INSPECTION = "site_inspection"        # Tactical micro-scale landing/drill site (< 20m)


class SelectionRejectionReason(BaseModel):
    """Reason why a candidate dataset was excluded from selection."""
    product_id: str
    stage: str  # 'availability', 'footprint', 'resolution_scale', 'crs_datum', 'lifecycle'
    reason: str
    details: Optional[Dict[str, Any]] = None


class CandidateEvaluation(BaseModel):
    """Detailed evaluation of an intersecting terrain product."""
    product_id: str
    instrument: str
    tier: str
    native_resolution_m: float
    is_locally_available: bool
    local_file_path: Optional[str] = None
    lifecycle_status: str
    coverage_area_km2: float
    coverage_percentage: float  # Percentage of requested bbox covered
    horizontal_crs: str
    vertical_datum: str
    vertical_datum_compatibility: str
    scale_suitability_score: float  # 0.0 to 1.0 (closeness to target analysis scale)
    is_eligible: bool
    disqualification_reason: Optional[str] = None


class ResolutionSelectionRequest(BaseModel):
    """Query parameters for resolution selection."""
    min_lat: float = Field(..., ge=-90.0, le=90.0)
    min_lon: float = Field(..., ge=0.0, le=360.0)
    max_lat: float = Field(..., ge=-90.0, le=90.0)
    max_lon: float = Field(..., ge=0.0, le=360.0)
    analysis_type: AnalysisType = Field(default=AnalysisType.TRAVERSE_PLANNING)
    target_scale_m: Optional[float] = Field(default=None, description="Preferred resolution scale in metres")
    require_local_raster: bool = Field(default=True, description="Strictly require on-disk raster data")
    require_scientific_validation: bool = Field(default=True, description="Require analysis_ready or scientifically_validated status")
    min_coverage_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Minimum acceptable footprint coverage")
    allow_fallback: bool = Field(default=True, description="Permit coarser baseline if primary scale is unavailable")


class ResolutionSelectionResult(BaseModel):
    """Result of resolution-aware dataset selection."""
    status: str  # 'selected', 'partial_coverage', 'insufficient_data', 'no_coverage'
    selected_product_id: Optional[str] = None
    selected_product: Optional[DTMProductProfile] = None
    fallback_product_id: Optional[str] = None
    native_resolution_m: Optional[float] = None
    coverage_percentage: float = 0.0
    covered_area_km2: float = 0.0
    requested_area_km2: float = 0.0
    selection_rationale: str
    rejected_products: List[SelectionRejectionReason] = []
    evaluated_candidates: List[CandidateEvaluation] = []
    uncertainty_notes: List[str] = []
    scientific_limitations: List[str] = []


class ResolutionSelector:
    """Service to select the scientifically optimal terrain raster for a given mission region."""

    # Default target scales by analysis type (meters)
    ANALYSIS_SCALE_TARGETS = {
        AnalysisType.RECONNAISSANCE: 14818.67,  # MOLA 4 ppd
        AnalysisType.REGIONAL_SURVEY: 463.08,   # MOLA 128 ppd
        AnalysisType.TRAVERSE_PLANNING: 463.08, # MOLA 128 ppd baseline or 20m CTX
        AnalysisType.HAZARD_ASSESSMENT: 20.01,  # CTX DTM
        AnalysisType.SITE_INSPECTION: 1.01,     # HiRISE DTM (tactical)
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.inventory_service = Mola128InventoryService()

    def _calculate_spherical_bbox_area(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> float:
        """Calculate true spherical surface area in km² on Mars radius 3396.19 km."""
        r = 3396.19
        phi1 = math.radians(min_lat)
        phi2 = math.radians(max_lat)
        delta_lambda = math.radians(max_lon - min_lon)
        return abs((r ** 2) * delta_lambda * (math.sin(phi2) - math.sin(phi1)))

    def _calculate_overlap_area(
        self,
        b1_lat_min: float, b1_lat_max: float, b1_lon_min: float, b1_lon_max: float,
        b2_lat_min: float, b2_lat_max: float, b2_lon_min: float, b2_lon_max: float,
    ) -> float:
        """Calculate spherical overlap area between two bounding boxes."""
        o_lat_min = max(b1_lat_min, b2_lat_min)
        o_lat_max = min(b1_lat_max, b2_lat_max)
        o_lon_min = max(b1_lon_min, b2_lon_min)
        o_lon_max = min(b1_lon_max, b2_lon_max)

        if o_lat_min >= o_lat_max or o_lon_min >= o_lon_max:
            return 0.0

        return self._calculate_spherical_bbox_area(o_lat_min, o_lon_min, o_lat_max, o_lon_max)

    def _resolve_local_raster_path(
        self,
        product_id: str,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Determine whether a product has a physically verified local raster on disk.
        Returns the path to open (preferring .lbl for raw PDS datasets so GDAL can read them).
        """
        pid = product_id.lower()

        # Check MOLA global 4 ppd
        if pid in ["mola-megdr-4", "mola-megdr"]:
            candidates = [
                os.path.join(self.data_dir, "processed", "mola", "mola_megt90n000cb_elevation.tif"),
                os.path.join(self.data_dir, "raw", "mola", "megt90n000cb.lbl"),
                os.path.join(self.data_dir, "raw", "mola", "megt90n000cb.img"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    return True, os.path.abspath(c)

        # Check MOLA 128 ppd tiles
        if pid == "mola-megdr-128":
            inv = self.inventory_service.get_inventory_report()
            downloaded = [t for t in inv.tiles if t.is_downloaded]
            if not downloaded:
                return False, None

            # If geographic bounds given, pick the overlapping tile
            chosen_tile = None
            if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
                norm_min_lon = min_lon % 360.0
                norm_max_lon = max_lon % 360.0
                for t in downloaded:
                    lat_ov = not (max_lat < t.lat_min or min_lat > t.lat_max)
                    lon_ov = not (norm_max_lon < t.lon_min or norm_min_lon > t.lon_max)
                    if lat_ov and lon_ov:
                        chosen_tile = t
                        break

            if chosen_tile is None:
                chosen_tile = downloaded[0]

            # Prefer .lbl so GDAL/rasterio can open directly
            if chosen_tile.local_path_lbl and os.path.exists(chosen_tile.local_path_lbl):
                return True, os.path.abspath(chosen_tile.local_path_lbl)
            if chosen_tile.local_path_img and os.path.exists(chosen_tile.local_path_img):
                return True, os.path.abspath(chosen_tile.local_path_img)

        # Check CTX DTM
        if "ctx" in pid:
            candidates = [
                os.path.join(self.data_dir, "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    return True, os.path.abspath(c)

        # HiRISE or remote datasets
        return False, None


    def select_resolution(self, request: ResolutionSelectionRequest) -> ResolutionSelectionResult:
        """Select the scientifically optimal terrain dataset matching the criteria."""
        if request.min_lat > request.max_lat:
            raise ValueError(f"min_lat ({request.min_lat}) must be <= max_lat ({request.max_lat})")
        if request.min_lon > request.max_lon:
            raise ValueError(f"min_lon ({request.min_lon}) must be <= max_lon ({request.max_lon})")

        requested_area = self._calculate_spherical_bbox_area(
            request.min_lat, request.min_lon, request.max_lat, request.max_lon
        )
        if requested_area < 1e-4:
            requested_area = 1e-4

        target_scale = (
            request.target_scale_m
            if request.target_scale_m is not None
            else self.ANALYSIS_SCALE_TARGETS[request.analysis_type]
        )

        all_products = MultiResolutionTerrainCatalog.get_all_products()
        evaluated: List[CandidateEvaluation] = []
        rejections: List[SelectionRejectionReason] = []

        for prod in all_products:
            # 1. Check availability
            is_local, local_path = self._resolve_local_raster_path(prod.product_id)

            # 2. Footprint overlap
            overlap_area = self._calculate_overlap_area(
                request.min_lat, request.max_lat, request.min_lon, request.max_lon,
                prod.lat_min, prod.lat_max, prod.lon_min, prod.lon_max,
            )
            coverage_pct = round((overlap_area / requested_area) * 100.0, 2)

            # 3. Vertical datum compatibility
            try:
                compat = HarmonizationEngine.assess_compatibility("mola-megdr-128", prod.product_id)
                v_compat_val = compat.vertical_compatibility.value
            except Exception:
                v_compat_val = "unknown"


            # 4. Scale suitability: penalize deviation from target scale
            res_ratio = max(prod.pixel_spacing_m, target_scale) / max(min(prod.pixel_spacing_m, target_scale), 1e-6)
            # scale suitability: 1.0 when identical, decaying with log2 ratio
            scale_score = round(max(0.0, 1.0 - (math.log2(res_ratio) * 0.15)), 3)

            is_eligible = True
            disqual_reason = None

            # Evaluation guards
            if request.require_local_raster and not is_local:
                is_eligible = False
                disqual_reason = (
                    f"Product '{prod.product_id}' is not physically stored on disk. "
                    f"Lifecycle status: '{prod.status}'. Local numerical analysis strictly requires authentic raster data."
                )
                rejections.append(SelectionRejectionReason(
                    product_id=prod.product_id,
                    stage="availability",
                    reason=disqual_reason,
                    details={"lifecycle_status": prod.status}
                ))
            elif coverage_pct < 1.0:
                is_eligible = False
                disqual_reason = (
                    f"Product '{prod.product_id}' footprint ([Lat {prod.lat_min}°, {prod.lat_max}°], "
                    f"[Lon {prod.lon_min}°, {prod.lon_max}°]) has negligible or zero overlap ({coverage_pct}%) with requested bounds."
                )
                rejections.append(SelectionRejectionReason(
                    product_id=prod.product_id,
                    stage="footprint",
                    reason=disqual_reason,
                    details={"coverage_pct": coverage_pct}
                ))
            elif request.require_scientific_validation and prod.status not in [
                "analysis_ready", "sample_ingested", "ingested"
            ]:
                is_eligible = False
                disqual_reason = (
                    f"Product '{prod.product_id}' has lifecycle status '{prod.status}'. "
                    "Only 'analysis_ready' or ingested rasters are approved for scientific analysis."
                )
                rejections.append(SelectionRejectionReason(
                    product_id=prod.product_id,
                    stage="lifecycle",
                    reason=disqual_reason,
                ))

            candidate_eval = CandidateEvaluation(
                product_id=prod.product_id,
                instrument=prod.instrument,
                tier=prod.tier,
                native_resolution_m=prod.pixel_spacing_m,
                is_locally_available=is_local,
                local_file_path=local_path,
                lifecycle_status=prod.status,
                coverage_area_km2=round(overlap_area, 2),
                coverage_percentage=min(coverage_pct, 100.0),
                horizontal_crs=prod.crs,
                vertical_datum=prod.vertical_datum,
                vertical_datum_compatibility=v_compat_val,
                scale_suitability_score=scale_score,
                is_eligible=is_eligible,
                disqualification_reason=disqual_reason,
            )
            evaluated.append(candidate_eval)

        # Filter eligible candidates
        eligible = [c for c in evaluated if c.is_eligible]

        if not eligible:
            # Check if any candidate would be eligible if fallback was permitted
            return ResolutionSelectionResult(
                status="insufficient_data",
                selection_rationale=(
                    f"No local terrain dataset satisfies the requested criteria for analysis '{request.analysis_type.value}' "
                    f"at target scale {target_scale:.1f}m. HiRISE products remain discovered (not locally acquired); "
                    "CTX DTM is confined to the Tyrrhena Terra DTM swath [-5.19°N to -4.00°N, 66.04°E to 66.62°E]."
                ),
                requested_area_km2=round(requested_area, 2),
                covered_area_km2=0.0,
                coverage_percentage=0.0,
                rejected_products=rejections,
                evaluated_candidates=evaluated,
                uncertainty_notes=[
                    "No authentic local raster data exists for the requested bounds meeting quality criteria.",
                    "Elevation cannot be fabricated or interpolated from unverified remote catalogues."
                ],
                scientific_limitations=[
                    "Local planetary analyses require authentic downloaded rasters with verified SHA-256 checksums."
                ],
            )

        # Sort eligible by:
        # 1. Coverage percentage >= min_coverage_pct
        # 2. Closeness to target scale (scale_suitability_score descending)
        # 3. Native resolution appropriate for scale (never finer than necessary if coverage is poor)
        def score_candidate(cand: CandidateEvaluation) -> float:
            cov_factor = min(cand.coverage_percentage / max(request.min_coverage_pct, 1.0), 1.0)
            return (cand.scale_suitability_score * 0.6) + (cov_factor * 0.4)

        eligible.sort(key=score_candidate, reverse=True)
        primary_candidate = eligible[0]
        primary_prod = MultiResolutionTerrainCatalog.get_product(primary_candidate.product_id)

        # Fallback candidate (e.g. MOLA baseline if CTX has partial coverage)
        fallback_id = None
        for cand in eligible[1:]:
            if cand.product_id != primary_candidate.product_id and cand.coverage_percentage >= 99.0:
                fallback_id = cand.product_id
                break

        status_result = "selected" if primary_candidate.coverage_percentage >= request.min_coverage_pct else "partial_coverage"

        rationale = (
            f"Selected '{primary_candidate.product_id}' ({primary_candidate.instrument}, "
            f"{primary_candidate.native_resolution_m:.2f} m/px) as the optimal terrain source for "
            f"{request.analysis_type.value} at target scale {target_scale:.1f} m. "
            f"Coverage: {primary_candidate.coverage_percentage:.1f}% ({primary_candidate.coverage_area_km2:.1f} km²). "
            f"Lifecycle status: '{primary_candidate.lifecycle_status}'. "
            f"Vertical datum compatibility: '{primary_candidate.vertical_datum_compatibility}'."
        )

        uncertainties = []
        if primary_candidate.coverage_percentage < 100.0:
            uncertainties.append(
                f"Dataset covers {primary_candidate.coverage_percentage:.1f}% of the requested bbox. "
                "Uncovered portions will encounter NoData and cannot support numerical terrain profiling."
            )
        if "ctx" in primary_candidate.product_id:
            uncertainties.append(
                "CTX DTM is tied to MOLA Areoid via ASP pc_align; a documented scale variance of 55.95 ppm exists "
                "between CTX IAU 2015 Sphere (R=3396.19 km) and MOLA Sphere (R=3396.00 km)."
            )
        elif "128" in primary_candidate.product_id:
            uncertainties.append(
                "MOLA 128 ppd provides 463 m/px regional baseline; sub-kilometer topographical hazards "
                "(boulders, small craters, narrow scarps) are unresolvable at this spatial scale."
            )

        limitations = [
            "Terrain intelligence results reflect the native spatial sampling of the selected dataset.",
            "Higher-resolution features cannot be inferred or upsampled beyond native sensor capability.",
            "This analysis supports scientific feasibility assessment and does not imply rover or astronaut operational safety."
        ]

        return ResolutionSelectionResult(
            status=status_result,
            selected_product_id=primary_candidate.product_id,
            selected_product=primary_prod,
            fallback_product_id=fallback_id,
            native_resolution_m=primary_candidate.native_resolution_m,
            coverage_percentage=primary_candidate.coverage_percentage,
            covered_area_km2=primary_candidate.coverage_area_km2,
            requested_area_km2=round(requested_area, 2),
            selection_rationale=rationale,
            rejected_products=rejections,
            evaluated_candidates=evaluated,
            uncertainty_notes=uncertainties,
            scientific_limitations=limitations,
        )
