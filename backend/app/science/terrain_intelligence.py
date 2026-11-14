"""Planetary Terrain Intelligence and Region Comparison Engine for MARS-X.

Provides multi-region topographic characterization, comparative terrain intelligence,
and explainable scientific metrics using authentic Martian elevation rasters.

Enforces strict planetary cartography rules:
- Compares regions at equivalent physical analysis scales (metres).
- Clearly distinguishes between actual local data and remote catalogued footprints.
- Explains terrain differences using physical geomorphological indicators.
- Employs fully documented, transparent confidence metrics with explicit weights.
- Never fabricates astronaut safety ratings or operational mission approvals.
"""

import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from app.terrain.multiscale_analysis import (
    MultiScaleAnalyzer,
    MultiScaleAnalysisRequest,
    MultiScaleAnalysisResult,
    ScaleMetrics,
)
from app.terrain.resolution_selector import (
    ResolutionSelector,
    ResolutionSelectionRequest,
    AnalysisType,
)
from app.terrain.multi_resolution import MultiResolutionTerrainCatalog

logger = logging.getLogger("MARS-X.science.terrain_intelligence")


class RegionDefinition(BaseModel):
    """Specification of a candidate Martian exploration region."""
    region_id: str
    name: str
    min_lat: float = Field(..., ge=-90.0, le=90.0)
    min_lon: float = Field(..., ge=0.0, le=360.0)
    max_lat: float = Field(..., ge=-90.0, le=90.0)
    max_lon: float = Field(..., ge=0.0, le=360.0)
    geological_context: Optional[str] = None


class RegionTerrainAssessment(BaseModel):
    """In-depth terrain intelligence assessment for a single Martian region."""
    region_id: str
    name: str
    bounds: Dict[str, float]
    area_km2: float
    selected_dataset_id: str
    native_resolution_m: float
    data_availability: str  # 'local_verified', 'local_partial', 'remote_only'
    valid_data_coverage_pct: float
    analysis_scale_m: float
    effective_analysis_scale_x_m: float = Field(default=0.0, description="Effective physical footprint in x/lon direction")
    effective_analysis_scale_y_m: float = Field(default=0.0, description="Effective physical footprint in y/lat direction")
    effective_analysis_area_km2: float = Field(default=0.0, description="Physical kernel ground area")
    scale_suitability: str = Field(default="optimal", description="'optimal', 'sub_pixel_extrapolation_warning', or 'heavily_coarse'")
    mean_slope_deg: float
    max_slope_deg: float
    p50_slope_deg: float
    p90_slope_deg: float
    mean_local_relief_m: float
    max_local_relief_m: float
    mean_roughness_m: float
    max_roughness_m: float
    elevation_min_m: float
    elevation_max_m: float
    elevation_mean_m: float
    elevation_std_m: float
    terrain_complexity_class: str
    complexity_rationale: str
    terrain_data_quality_index: float = Field(
        default=0.0,
        description="Heuristic Data Quality Index (0-100) reflecting coverage, resolution matching, and datum; NOT a probability of safety."
    )
    data_confidence_score: float = Field(
        default=0.0,
        description="Backward-compatible alias for terrain_data_quality_index"
    )
    confidence_breakdown: Dict[str, float]
    scientific_summary: str
    limitations: List[str]


class RegionComparisonRequest(BaseModel):
    """Request to compare two or more candidate Martian exploration regions."""
    regions: List[RegionDefinition]
    target_scale_m: float = Field(default=500.0, description="Equivalent physical scale for comparison")
    prefer_highest_resolution: bool = Field(default=True)


class RegionPairComparison(BaseModel):
    """Pairwise contrast between two candidate exploration regions."""
    region_a_id: str
    region_b_id: str
    slope_contrast: str
    roughness_contrast: str
    coverage_contrast: str
    resolution_contrast: str
    scale_compatibility: str = Field(default="equivalent_scale", description="'equivalent_scale', 'approximately_equivalent', 'non_equivalent'")
    comparative_summary: str


class RegionComparisonResponse(BaseModel):
    """Comprehensive comparison report across multiple candidate regions."""
    comparison_scale_m: float
    regions_evaluated: List[RegionTerrainAssessment]
    pairwise_comparisons: List[RegionPairComparison]
    methodological_notes: List[str]
    scientific_disclaimer: str


# Standard candidate region presets across Mars
PRESET_CANDIDATE_REGIONS = [
    RegionDefinition(
        region_id="tyrrhena-terra-active",
        name="Tyrrhena Terra (CTX DTM Swath)",
        min_lat=-5.10,
        min_lon=66.10,
        max_lat=-4.50,
        max_lon=66.50,
        geological_context="Inter-crater highland plains and dissecting valley networks in Tyrrhena Terra near Hesperia Planum margin, covered by authentic 20m USGS CTX DTM (P21_009323_1754).",
    ),
    RegionDefinition(
        region_id="melas-chasma-valles-marineris",
        name="Melas Chasma Canyon Floor",
        min_lat=-10.50,
        min_lon=282.50,
        max_lat=-9.00,
        max_lon=285.00,
        geological_context="Central deep canyon floor of Valles Marineris (~9.8°S, 283.6°E / 76.4°W), covered by authentic MOLA regional elevation baseline.",
    ),
    RegionDefinition(
        region_id="schiaparelli-impact-basin",
        name="Schiaparelli Basin Floor",
        min_lat=-1.10,
        min_lon=13.80,
        max_lat=-0.80,
        max_lon=13.95,
        geological_context="Ancient degraded impact crater with layered sedimentary floor and MOLA 128 coverage.",
    ),
    RegionDefinition(
        region_id="jezero-delta-scarp",
        name="Jezero Crater Delta Region",
        min_lat=18.30,
        min_lon=77.35,
        max_lat=18.55,
        max_lon=77.60,
        geological_context="Fan-delta river deposits within Jezero impact crater covered by MOLA baseline.",
    ),
    RegionDefinition(
        region_id="coprates-chasma-scarp",
        name="Coprates Chasma Escarpment",
        min_lat=-14.50,
        min_lon=59.00,
        max_lat=-14.00,
        max_lon=59.50,
        geological_context="Steep canyon wall structural scarps within Valles Marineris trough system.",
    ),
]


class TerrainIntelligenceService:
    """Service providing terrain intelligence and multi-region comparisons."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.analyzer = MultiScaleAnalyzer(data_dir=data_dir)
        self.selector = ResolutionSelector(data_dir=data_dir)

    def _calculate_confidence_score(
        self,
        valid_cov_pct: float,
        native_res_m: float,
        target_scale_m: float,
        is_local: bool,
        vert_datum: str,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate fully explainable data confidence score (0-100).
        
        Formula:
          Score = 100 * (0.45 * coverage_factor + 0.35 * scale_factor + 0.20 * datum_factor)
        """
        if not is_local:
            return 0.0, {"coverage": 0.0, "scale_suitability": 0.0, "datum_quality": 0.0}

        # Coverage factor (0.0 to 1.0)
        c_factor = min(max(valid_cov_pct / 100.0, 0.0), 1.0)

        # Scale factor (1.0 when native res matches or exceeds target scale smoothly)
        ratio = max(native_res_m, target_scale_m) / max(min(native_res_m, target_scale_m), 1e-4)
        s_factor = max(0.2, 1.0 - (math.log2(ratio) * 0.12))

        # Datum factor
        d_factor = 1.0 if "Areoid" in vert_datum else 0.8

        total = 100.0 * (0.45 * c_factor + 0.35 * s_factor + 0.20 * d_factor)
        breakdown = {
            "coverage_component": round(0.45 * c_factor * 100.0, 1),
            "scale_suitability_component": round(0.35 * s_factor * 100.0, 1),
            "datum_quality_component": round(0.20 * d_factor * 100.0, 1),
        }
        return round(total, 1), breakdown

    def assess_region(
        self, region: RegionDefinition, target_scale_m: float = 500.0
    ) -> RegionTerrainAssessment:
        """Evaluate a single candidate region with comprehensive terrain intelligence."""
        # 1. Select appropriate resolution
        sel_req = ResolutionSelectionRequest(
            min_lat=region.min_lat,
            min_lon=region.min_lon,
            max_lat=region.max_lat,
            max_lon=region.max_lon,
            analysis_type=AnalysisType.REGIONAL_SURVEY,
            target_scale_m=target_scale_m,
            require_local_raster=True,
        )
        sel_res = self.selector.select_resolution(sel_req)

        area_km2 = sel_res.requested_area_km2

        if not sel_res.selected_product_id:
            # Insufficient local data
            return RegionTerrainAssessment(
                region_id=region.region_id,
                name=region.name,
                bounds={"min_lat": region.min_lat, "min_lon": region.min_lon, "max_lat": region.max_lat, "max_lon": region.max_lon},
                area_km2=area_km2,
                selected_dataset_id="none",
                native_resolution_m=0.0,
                data_availability="remote_only",
                valid_data_coverage_pct=0.0,
                analysis_scale_m=target_scale_m,
                effective_analysis_scale_x_m=0.0,
                effective_analysis_scale_y_m=0.0,
                effective_analysis_area_km2=0.0,
                scale_suitability="insufficient_data",
                mean_slope_deg=0.0,
                max_slope_deg=0.0,
                p50_slope_deg=0.0,
                p90_slope_deg=0.0,
                mean_local_relief_m=0.0,
                max_local_relief_m=0.0,
                mean_roughness_m=0.0,
                max_roughness_m=0.0,
                elevation_min_m=0.0,
                elevation_max_m=0.0,
                elevation_mean_m=0.0,
                elevation_std_m=0.0,
                terrain_complexity_class="insufficient_data",
                complexity_rationale=sel_res.selection_rationale,
                terrain_data_quality_index=0.0,
                data_confidence_score=0.0,
                confidence_breakdown={"coverage": 0.0, "scale_suitability": 0.0, "datum_quality": 0.0},
                scientific_summary=f"Region '{region.name}' lacks authentic local elevation raster coverage.",
                limitations=["No local raster data present on disk for numerical profiling."]
            )

        # 2. Run multi-scale analysis at the target scale
        msa_req = MultiScaleAnalysisRequest(
            min_lat=region.min_lat,
            min_lon=region.min_lon,
            max_lat=region.max_lat,
            max_lon=region.max_lon,
            dataset_id=sel_res.selected_product_id,
            windows_m=[target_scale_m],
        )
        msa_res = self.analyzer.analyze_region(msa_req)
        metrics = msa_res.scales[0] if msa_res.scales else None

        if not metrics:
            raise ValueError(f"Failed to calculate metrics for region {region.region_id}")

        score, breakdown = self._calculate_confidence_score(
            valid_cov_pct=metrics.valid_data_pct,
            native_res_m=metrics.native_resolution_m,
            target_scale_m=target_scale_m,
            is_local=True,
            vert_datum=metrics.vertical_datum,
        )

        summary = (
            f"Region '{region.name}' evaluated at {target_scale_m:.0f}m physical scale using '{metrics.source_product}' "
            f"({metrics.native_resolution_m:.1f}m/px). Mean slope is {metrics.mean_slope_deg:.1f}° (max {metrics.max_slope_deg:.1f}°). "
            f"Mean roughness is {metrics.mean_roughness_m:.1f}m. Classified as '{metrics.complexity_class}'. "
            f"Heuristic Data Quality Index: {score:.1f}/100."
        )

        return RegionTerrainAssessment(
            region_id=region.region_id,
            name=region.name,
            bounds={"min_lat": region.min_lat, "min_lon": region.min_lon, "max_lat": region.max_lat, "max_lon": region.max_lon},
            area_km2=area_km2,
            selected_dataset_id=metrics.source_product,
            native_resolution_m=metrics.native_resolution_m,
            data_availability="local_verified" if metrics.valid_data_pct >= 90.0 else "local_partial",
            valid_data_coverage_pct=metrics.valid_data_pct,
            analysis_scale_m=target_scale_m,
            effective_analysis_scale_x_m=metrics.effective_analysis_scale_x_m,
            effective_analysis_scale_y_m=metrics.effective_analysis_scale_y_m,
            effective_analysis_area_km2=metrics.effective_analysis_area_km2,
            scale_suitability=metrics.scale_suitability,
            mean_slope_deg=metrics.mean_slope_deg,
            max_slope_deg=metrics.max_slope_deg,
            p50_slope_deg=metrics.p50_slope_deg,
            p90_slope_deg=metrics.p90_slope_deg,
            mean_local_relief_m=metrics.mean_local_relief_m,
            max_local_relief_m=metrics.max_local_relief_m,
            mean_roughness_m=metrics.mean_roughness_m,
            max_roughness_m=metrics.max_roughness_m,
            elevation_min_m=metrics.min_elevation_m,
            elevation_max_m=metrics.max_elevation_m,
            elevation_mean_m=metrics.mean_elevation_m,
            elevation_std_m=metrics.elevation_std_m,
            terrain_complexity_class=metrics.complexity_class,
            complexity_rationale=metrics.complexity_rationale,
            terrain_data_quality_index=score,
            data_confidence_score=score,
            confidence_breakdown=breakdown,
            scientific_summary=summary,
            limitations=[
                f"Metrics evaluated at {target_scale_m:.0f}m window (effective: {metrics.effective_analysis_scale_x_m:.0f}m x {metrics.effective_analysis_scale_y_m:.0f}m) using native resolution {metrics.native_resolution_m:.1f}m/px.",
                "Sub-pixel morphologic features cannot be detected.",
                "Heuristic Data Quality Index reflects data completeness and resolution matching, NOT statistical mission success.",
                "Topographic complexity does not imply astronaut or rover operational safety."
            ],
        )

    def compare_regions(self, request: RegionComparisonRequest) -> RegionComparisonResponse:
        """Compare multiple candidate regions at an equivalent physical scale."""
        if len(request.regions) < 2:
            raise ValueError("Region comparison requires at least 2 candidate regions.")

        assessments = [
            self.assess_region(r, target_scale_m=request.target_scale_m)
            for r in request.regions
        ]

        pair_comparisons: List[RegionPairComparison] = []
        for i in range(len(assessments)):
            for j in range(i + 1, len(assessments)):
                ra = assessments[i]
                rb = assessments[j]

                # Slope contrast
                delta_slope = ra.mean_slope_deg - rb.mean_slope_deg
                if abs(delta_slope) < 1.0:
                    slope_c = f"Comparable mean slope (~{ra.mean_slope_deg:.1f}° vs ~{rb.mean_slope_deg:.1f}°)"
                elif delta_slope > 0:
                    slope_c = f"'{ra.name}' has steeper mean slope ({ra.mean_slope_deg:.1f}° vs {rb.mean_slope_deg:.1f}°, Δ=+{delta_slope:.1f}°)"
                else:
                    slope_c = f"'{rb.name}' has steeper mean slope ({rb.mean_slope_deg:.1f}° vs {ra.mean_slope_deg:.1f}°, Δ={delta_slope:.1f}°)"

                # Roughness contrast
                delta_rough = ra.mean_roughness_m - rb.mean_roughness_m
                if abs(delta_rough) < 2.0:
                    rough_c = f"Comparable topographic roughness (~{ra.mean_roughness_m:.1f}m vs ~{rb.mean_roughness_m:.1f}m)"
                elif delta_rough > 0:
                    rough_c = f"'{ra.name}' exhibits higher roughness ({ra.mean_roughness_m:.1f}m vs {rb.mean_roughness_m:.1f}m)"
                else:
                    rough_c = f"'{rb.name}' exhibits higher roughness ({rb.mean_roughness_m:.1f}m vs {ra.mean_roughness_m:.1f}m)"

                # Coverage & resolution contrast
                cov_c = f"Valid coverage: '{ra.name}'={ra.valid_data_coverage_pct:.1f}% vs '{rb.name}'={rb.valid_data_coverage_pct:.1f}%"
                res_c = f"Native resolution: '{ra.selected_dataset_id}' ({ra.native_resolution_m:.1f}m) vs '{rb.selected_dataset_id}' ({rb.native_resolution_m:.1f}m)"

                # Scale compatibility evaluation
                eff_a = max(ra.effective_analysis_scale_x_m, 1e-3)
                eff_b = max(rb.effective_analysis_scale_x_m, 1e-3)
                scale_diff_pct = abs(eff_a - eff_b) / max(eff_a, eff_b) * 100.0

                if scale_diff_pct <= 15.0:
                    compat_str = "equivalent_scale"
                elif scale_diff_pct <= 35.0:
                    compat_str = "approximately_equivalent"
                else:
                    compat_str = "non_equivalent"

                pair_summary = (
                    f"At {request.target_scale_m:.0f}m scale, {slope_c}. {rough_c}. "
                    f"Heuristic Quality Index: {ra.name}={ra.terrain_data_quality_index:.1f}/100 vs {rb.name}={rb.terrain_data_quality_index:.1f}/100. "
                    f"Scale compatibility: {compat_str} (effective footprint Δ={scale_diff_pct:.1f}%)."
                )

                pair_comparisons.append(RegionPairComparison(
                    region_a_id=ra.region_id,
                    region_b_id=rb.region_id,
                    slope_contrast=slope_c,
                    roughness_contrast=rough_c,
                    coverage_contrast=cov_c,
                    resolution_contrast=res_c,
                    scale_compatibility=compat_str,
                    comparative_summary=pair_summary,
                ))

        method_notes = [
            f"All regions evaluated at an identical physical analysis window of {request.target_scale_m:.0f} metres.",
            "Slope metrics derived via Horn 3x3 convolution with latitudinal metric scale correction.",
            "Roughness computed as moving root-mean-square elevation residual.",
            "Confidence score weights: 45% valid coverage, 35% scale suitability, 20% vertical datum alignment."
        ]

        disclaimer = (
            "Terrain intelligence assessments reflect physical morphometry from orbital remote-sensing datasets. "
            "They support landing site feasibility studies and do not provide astronaut safety certifications or operational clearance."
        )

        return RegionComparisonResponse(
            comparison_scale_m=request.target_scale_m,
            regions_evaluated=assessments,
            pairwise_comparisons=pair_comparisons,
            methodological_notes=method_notes,
            scientific_disclaimer=disclaimer,
        )
