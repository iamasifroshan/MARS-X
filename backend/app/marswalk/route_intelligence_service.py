"""Route Intelligence & Scientific Traverse Analysis Service — Phase 8.8.4.

Analyzes single-destination Marswalk routes and multi-stop science traverses,
generating:
1. High-resolution elevation profile intelligence (MOLA Areoid, local gradient, sampling intervals).
2. Terrain intelligence (slope exposure distribution, roughness index, NoData verification, DEM transitions).
3. Geological route context (USGS SIM 3292 unit intersections, contact boundaries, structural features, 1:20M scale limitations).
4. Thermophysical context (MGS TES thermal inertia, regolith grain-size interpretations, calibration uncertainty, THEMIS display context).
5. Science opportunity analysis (Phase 8.7 candidate discovery proximity, evidence classification, potential investigations).
6. Leg-by-leg and aggregated multi-stop traverse intelligence reports with strict junction deduplication.
"""

import math
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from app.marswalk.marswalk_models import MarswalkRouteResponse, MarswalkRoutePoint
from app.marswalk.marswalk_planner import get_cached_route, TERRAIN_SOURCES, MarswalkPlanner
from app.marswalk.multi_stop_models import MultiStopTraverseResponse, PairwiseRouteLeg
from app.marswalk.multi_stop_planner import get_cached_multi_stop_traverse
from app.marswalk.route_intelligence_models import (
    ElevationProfilePoint,
    ElevationProfileSummary,
    SlopeExposureBand,
    DemSourceSegment,
    TerrainIntelligenceSummary,
    GeologicalContactCrossing,
    GeologicalUnitSegment,
    NearbyGeologicalStructure,
    GeologicalRouteContext,
    ThermalInertiaSample,
    ThermophysicalRouteContext,
    RouteScienceOpportunity,
    LegRouteIntelligence,
    RouteIntelligenceReport,
    MultiStopTraverseIntelligenceReport,
    RouteIntelligenceMetadataResponse,
    MARSWALK_SAFETY_DISCLAIMER,
)
from app.science.geology_service import get_geology_service
from app.science.thermal_service import get_thermal_service
from app.science.environmental_service import get_environmental_service
from app.science.discovery_service import (
    ScienceDiscoveryService,
    mars_haversine_distance_km,
    CANDIDATE_DISCOVERIES,
    DISCOVERY_CATEGORIES,
)

logger = logging.getLogger("MARS-X.marswalk.route_intelligence")

SLOPE_CATEGORY_DESCRIPTIONS = {
    "low": "0°–5° (Gentle, low resistance planar or rolling regolith)",
    "moderate": "5°–15° (Moderate, elevated energy expenditure; within rover & EVA envelope)",
    "high": "15°–25° (Steep scarp / crater wall; near operational traverse limit)",
    "critical": ">25° (Extreme slope; impassable terrain cutoff)",
    "very_high": ">25° (Extreme slope; impassable terrain cutoff)",
    "unknown": "NoData / unmeasured terrain cells",
}


def _calculate_roughness_and_classification(elevations: List[float]) -> Tuple[float, str]:
    """Compute elevation standard deviation / RMSD and morphological classification."""
    if len(elevations) < 2:
        return 0.0, "Smooth planar regolith"

    arr = np.array(elevations, dtype=np.float64)
    # Detrend linear slope across profile to evaluate residual topographic roughness
    x = np.arange(len(arr), dtype=np.float64)
    if len(arr) > 2:
        p = np.polyfit(x, arr, 1)
        detrended = arr - np.polyval(p, x)
        roughness = float(np.std(detrended))
    else:
        roughness = float(np.std(arr))

    roughness = round(roughness, 2)
    if roughness < 0.8:
        classification = "Smooth planar regolith (low relief)"
    elif roughness < 3.5:
        classification = "Undulating terraced terrain (moderate relief)"
    elif roughness < 12.0:
        classification = "Degraded scarp / dissected paleochannel wall (high relief)"
    else:
        classification = "Rugged blocky ejecta / chaotic faulted terrain (extreme relief)"

    return roughness, classification


class RouteIntelligenceService:
    """Singleton service providing deep scientific analysis of Marswalk routes and traverses."""

    _instance: Optional["RouteIntelligenceService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RouteIntelligenceService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.geology_service = get_geology_service()
        self.thermal_service = get_thermal_service()
        self.discovery_service = ScienceDiscoveryService()
        self._initialized = True
        logger.info("RouteIntelligenceService initialized successfully.")

    # =========================================================================
    # ELEVATION PROFILE INTELLIGENCE
    # =========================================================================

    @classmethod
    def build_elevation_profile(
        cls,
        path_points: List[MarswalkRoutePoint],
        dem_source: str,
        native_resolution_m: float,
        start_distance_offset_m: float = 0.0,
    ) -> ElevationProfileSummary:
        """Construct authoritative elevation profile from route sample points."""
        if not path_points:
            return ElevationProfileSummary(
                min_elevation_m=0.0,
                max_elevation_m=0.0,
                cumulative_elevation_gain_m=0.0,
                cumulative_elevation_loss_m=0.0,
                net_elevation_change_m=0.0,
                max_gradient_pct=0.0,
                mean_gradient_pct=0.0,
                sampling_interval_m=0.0,
                total_samples=0,
                points=[],
            )

        profile_points: List[ElevationProfilePoint] = []
        elevations = [p.elevation_m for p in path_points]
        gradients: List[float] = []

        gain = 0.0
        loss = 0.0

        for i, pt in enumerate(path_points):
            cum_dist = pt.cumulative_distance_m + start_distance_offset_m
            local_grad = 0.0
            if i > 0:
                prev = path_points[i - 1]
                dz = pt.elevation_m - prev.elevation_m
                ds = pt.cumulative_distance_m - prev.cumulative_distance_m
                if ds > 1e-4:
                    local_grad = round((dz / ds) * 100.0, 2)
                    gradients.append(abs(local_grad))
                if dz > 0:
                    gain += dz
                else:
                    loss += abs(dz)

            profile_points.append(
                ElevationProfilePoint(
                    sample_index=i,
                    distance_m=round(cum_dist, 2),
                    lat=round(pt.lat, 6),
                    lon=round(pt.lon % 360.0, 6),
                    elevation_m=round(pt.elevation_m, 2),
                    slope_deg=round(pt.slope_deg, 2),
                    local_gradient_pct=local_grad,
                    dem_source=dem_source,
                    resolution_m=native_resolution_m,
                )
            )

        total_dist = path_points[-1].cumulative_distance_m
        num_pts = len(path_points)
        sampling_interval = round(total_dist / (num_pts - 1), 2) if num_pts > 1 else native_resolution_m
        net_change = round(elevations[-1] - elevations[0], 2)
        max_grad = round(max(gradients), 2) if gradients else 0.0
        mean_grad = round(float(np.mean(gradients)), 2) if gradients else 0.0

        return ElevationProfileSummary(
            min_elevation_m=round(min(elevations), 2),
            max_elevation_m=round(max(elevations), 2),
            cumulative_elevation_gain_m=round(gain, 2),
            cumulative_elevation_loss_m=round(loss, 2),
            net_elevation_change_m=net_change,
            max_gradient_pct=max_grad,
            mean_gradient_pct=mean_grad,
            sampling_interval_m=sampling_interval,
            total_samples=num_pts,
            points=profile_points,
        )

    # =========================================================================
    # TERRAIN INTELLIGENCE
    # =========================================================================

    @classmethod
    def build_terrain_intelligence(
        cls,
        elevations: List[float],
        slope_exposure_pct: Dict[str, float],
        mean_slope_deg: float,
        max_slope_deg: float,
        total_surface_distance_m: float,
        unknown_data_exposure_pct: float,
        dem_source: str,
        instrument: str,
        native_resolution_m: float,
        native_resolution_desc: str,
    ) -> TerrainIntelligenceSummary:
        """Analyze route corridor for slope exposure, roughness, and NoData coverage."""
        bands: List[SlopeExposureBand] = []
        for cat in ["low", "moderate", "high", "critical", "unknown"]:
            pct = slope_exposure_pct.get(cat, 0.0)
            if cat == "critical" and "very_high" in slope_exposure_pct:
                pct = max(pct, slope_exposure_pct.get("very_high", 0.0))
            dist_m = round((pct / 100.0) * total_surface_distance_m, 2)
            desc = SLOPE_CATEGORY_DESCRIPTIONS.get(cat, f"Slope category {cat}")
            bands.append(
                SlopeExposureBand(
                    category=cat,
                    description=desc,
                    distance_m=dist_m,
                    percentage=round(pct, 2),
                )
            )

        roughness, rough_class = _calculate_roughness_and_classification(elevations)
        nodata_dist = round((unknown_data_exposure_pct / 100.0) * total_surface_distance_m, 2)
        coverage_status = "complete_verified_coverage" if unknown_data_exposure_pct == 0.0 else "partial_coverage"

        dem_segments = [
            DemSourceSegment(
                source_id=dem_source,
                instrument=instrument,
                native_resolution_m=native_resolution_m,
                start_distance_m=0.0,
                end_distance_m=round(total_surface_distance_m, 2),
            )
        ]

        limitations = (
            f"Elevation and slope derived from {dem_source} ({native_resolution_desc}, {instrument}). "
            f"Physical terrain obstacles smaller than the native sampling resolution ({native_resolution_m} m) "
            "such as meter-scale boulders, fissures, or dust traps cannot be resolved from orbit. "
            "Never infer microtopographic traversability from orbital products."
        )

        return TerrainIntelligenceSummary(
            slope_distribution=slope_exposure_pct,
            slope_exposure_bands=bands,
            mean_slope_deg=round(mean_slope_deg, 2),
            max_slope_deg=round(max_slope_deg, 2),
            roughness_index_m=roughness,
            roughness_classification=rough_class,
            nodata_distance_m=nodata_dist,
            nodata_pct=round(unknown_data_exposure_pct, 2),
            coverage_status=coverage_status,
            dem_source_segments=dem_segments,
            cross_resolution_transition=False,
            terrain_limitations=limitations,
        )

    # =========================================================================
    # GEOLOGICAL ROUTE CONTEXT (USGS SIM 3292)
    # =========================================================================

    def build_geological_context(
        self,
        coords_with_distance: List[Tuple[float, float, float]],
        total_surface_distance_m: float,
        corridor_radius_km: float = 100.0,
    ) -> GeologicalRouteContext:
        """Intersect route points with USGS SIM 3292 geological units, contacts, and structures."""
        if not coords_with_distance:
            return GeologicalRouteContext(
                units_traversed=[],
                boundaries_crossed=[],
                nearby_structures=[],
                limitations_disclaimer="No coordinates provided for geological intersection.",
            )

        # 1. Sample geological units along route
        # Sample up to 60 evenly spaced locations along the route for point-in-polygon queries
        sample_step = max(1, len(coords_with_distance) // 60)
        sampled_coords = coords_with_distance[::sample_step]
        if coords_with_distance[-1] not in sampled_coords:
            sampled_coords.append(coords_with_distance[-1])

        unit_records: List[Tuple[float, str, str, str, str]] = []
        # (distance_m, unit_code, unit_name, period, description)

        for lat, lon, dist_m in sampled_coords:
            u_info = self.geology_service.query_point(lat, lon)
            if u_info:
                unit_code = u_info["unit"]
                unit_name = u_info.get("unit_name", "")
                period = u_info.get("chronostratigraphic_period", "Undivided")
                desc = (
                    f"{unit_name}. Mapped at 1:20,000,000 scale as part of USGS SIM 3292 "
                    f"chronostratigraphic mapping ({period} period)."
                )
                unit_records.append((dist_m, unit_code, unit_name, period, desc))
            else:
                unit_records.append((dist_m, "Undivided", "Unmapped or Undivided Martian Surface", "Undivided", "No formal SIM 3292 polygon mapped at location."))

        # Collapse contiguous identical units into segments
        unit_segments: List[GeologicalUnitSegment] = []
        boundaries: List[GeologicalContactCrossing] = []

        if unit_records:
            cur_start_m, cur_code, cur_name, cur_period, cur_desc = unit_records[0]
            prev_m = cur_start_m

            for i in range(1, len(unit_records)):
                rec_m, rec_code, rec_name, rec_period, rec_desc = unit_records[i]
                if rec_code != cur_code:
                    # Contact boundary crossed!
                    seg_len = max(0.0, rec_m - cur_start_m)
                    pct = round((seg_len / total_surface_distance_m) * 100.0, 2) if total_surface_distance_m > 0 else 100.0
                    unit_segments.append(
                        GeologicalUnitSegment(
                            unit_code=cur_code,
                            unit_name=cur_name,
                            chronostratigraphic_period=cur_period,
                            distance_start_m=round(cur_start_m, 1),
                            distance_end_m=round(rec_m, 1),
                            traversed_length_m=round(seg_len, 1),
                            traversed_pct=pct,
                            description=cur_desc,
                        )
                    )
                    # Find coordinate for this contact crossing
                    contact_coord = (sampled_coords[i][0], sampled_coords[i][1])
                    boundaries.append(
                        GeologicalContactCrossing(
                            distance_m=round(rec_m, 1),
                            coord=contact_coord,
                            from_unit=cur_code,
                            to_unit=rec_code,
                            contact_type="Stratigraphic Contact Boundary",
                        )
                    )
                    cur_start_m = rec_m
                    cur_code = rec_code
                    cur_name = rec_name
                    cur_period = rec_period
                    cur_desc = rec_desc

                prev_m = rec_m

            # Final segment
            seg_len = max(0.0, total_surface_distance_m - cur_start_m)
            pct = round((seg_len / total_surface_distance_m) * 100.0, 2) if total_surface_distance_m > 0 else 100.0
            unit_segments.append(
                GeologicalUnitSegment(
                    unit_code=cur_code,
                    unit_name=cur_name,
                    chronostratigraphic_period=cur_period,
                    distance_start_m=round(cur_start_m, 1),
                    distance_end_m=round(total_surface_distance_m, 1),
                    traversed_length_m=round(seg_len, 1),
                    traversed_pct=pct,
                    description=cur_desc,
                )
            )

        # 2. Query nearby structural features from SIM 3292
        all_lats = [c[0] for c in coords_with_distance]
        all_lons = [c[1] for c in coords_with_distance]
        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)

        # Add margin around bounding box (~1.0 degree ~= 59.3 km)
        margin = 1.0
        v_min_lat = max(-90.0, min_lat - margin)
        v_max_lat = min(90.0, max_lat + margin)
        v_min_lon = ((min_lon - margin + 180.0) % 360.0) - 180.0
        v_max_lon = ((max_lon + margin + 180.0) % 360.0) - 180.0

        nearby_structs: List[NearbyGeologicalStructure] = []
        try:
            struct_res = self.geology_service.query_viewport(
                min_lon=v_min_lon,
                min_lat=v_min_lat,
                max_lon=v_max_lon,
                max_lat=v_max_lat,
                layer="structure",
                limit=30,
            )
            for f in struct_res.get("features", []):
                props = f.get("properties", {})
                geom = f.get("geometry", {})
                g_type = geom.get("type", "")
                coords = geom.get("coordinates", [])

                # Extract points from geometry
                f_points = []
                if g_type == "LineString":
                    f_points = coords
                elif g_type == "MultiLineString":
                    for ring in coords:
                        f_points.extend(ring)

                if not f_points:
                    continue

                # Compute min distance to route
                min_dist_km = float("inf")
                closest_pt = (f_points[0][1], (f_points[0][0] % 360.0))

                # Sample subset of feature points
                for p in f_points[:: max(1, len(f_points) // 10)]:
                    f_lon = p[0] % 360.0
                    f_lat = p[1]
                    for r_lat, r_lon, _ in coords_with_distance[:: max(1, len(coords_with_distance) // 15)]:
                        d_km = mars_haversine_distance_km(r_lat, r_lon, f_lat, f_lon)
                        if d_km < min_dist_km:
                            min_dist_km = d_km
                            closest_pt = (round(f_lat, 4), round(f_lon, 4))

                if min_dist_km <= corridor_radius_km:
                    nearby_structs.append(
                        NearbyGeologicalStructure(
                            object_id=props.get("OBJECTID", f.get("id", 0)),
                            morphology=props.get("Morphology", "Structure"),
                            origin=props.get("Origin", "Geological"),
                            interpretation=props.get("Interpreta", "Structural Lineation"),
                            preservation=props.get("Preservati", "Subdued"),
                            dimension=props.get("Dimension", "Narrow"),
                            distance_from_route_km=round(min_dist_km, 2),
                            closest_coord=closest_pt,
                        )
                    )
        except Exception as e:
            logger.warning("Error querying nearby structures: %s", e)

        nearby_structs.sort(key=lambda s: s.distance_from_route_km)

        disclaimer = (
            "USGS SIM 3292 was mapped at 1:20,000,000 global scale (Tanaka et al. 2014; Skinner et al. 2023). "
            "1 mm on the published map represents 20 km on the Martian surface. Boundary contacts possess nominal "
            "positional uncertainty of ~5–10 km. Local metre-scale traverses may lie entirely within a single mapped "
            "regional polygon. Mapped geological units represent cartographic interpretations and stratigraphy, "
            "NOT direct in-situ sensor measurements."
        )

        return GeologicalRouteContext(
            units_traversed=unit_segments,
            boundaries_crossed=boundaries,
            nearby_structures=nearby_structs[:10],
            published_scale="1:20,000,000",
            cartographic_source="USGS Scientific Investigations Map 3292 (Tanaka et al. 2014; Skinner et al. 2023)",
            positional_uncertainty_km=5.0,
            limitations_disclaimer=disclaimer,
        )

    # =========================================================================
    # THERMOPHYSICAL CONTEXT (MGS TES THERMAL INERTIA)
    # =========================================================================

    def build_thermophysical_context(
        self,
        coords_with_distance: List[Tuple[float, float, float]],
    ) -> ThermophysicalRouteContext:
        """Sample MGS TES thermal inertia and evaluate THEMIS IR regional context."""
        if not coords_with_distance:
            return ThermophysicalRouteContext(
                min_tiu=None,
                max_tiu=None,
                mean_tiu=None,
                predominant_interpretation="No coordinates provided",
                samples=[],
                calibration_notes="No samples",
                themis_context="No samples",
            )

        # Sample up to 30 points along the path for TES queries
        step = max(1, len(coords_with_distance) // 30)
        sampled = coords_with_distance[::step]
        if coords_with_distance[-1] not in sampled:
            sampled.append(coords_with_distance[-1])

        samples: List[ThermalInertiaSample] = []
        ti_vals: List[float] = []

        in_themis_footprint = False

        for lat, lon, dist_m in sampled:
            # Check THEMIS coverage: lat [-30, 0], lon [0, 30]
            norm_lon = lon % 360.0
            if -30.0 <= lat <= 0.0 and 0.0 <= norm_lon <= 30.0:
                in_themis_footprint = True

            try:
                ti_res = self.thermal_service.query_point(lat, lon, product="dayside")
                ti_val = ti_res.get("thermal_inertia_tiu")
                interp = ti_res.get("physical_interpretation", "Unmeasured")
                if ti_val is not None:
                    ti_vals.append(ti_val)
                samples.append(
                    ThermalInertiaSample(
                        distance_m=round(dist_m, 1),
                        lat=round(lat, 5),
                        lon=round(norm_lon, 5),
                        thermal_inertia_tiu=ti_val,
                        physical_interpretation=interp,
                    )
                )
            except Exception as e:
                logger.debug("Failed TES query at (%f, %f): %s", lat, lon, e)
                samples.append(
                    ThermalInertiaSample(
                        distance_m=round(dist_m, 1),
                        lat=round(lat, 5),
                        lon=round(norm_lon, 5),
                        thermal_inertia_tiu=None,
                        physical_interpretation="Unmeasured or query failed",
                    )
                )

        min_ti = round(min(ti_vals), 1) if ti_vals else None
        max_ti = round(max(ti_vals), 1) if ti_vals else None
        mean_ti = round(float(np.mean(ti_vals)), 1) if ti_vals else None

        predominant_interp = "Unmeasured or polar / shadowed region"
        if mean_ti is not None:
            predominant_interp = self.thermal_service._interpret_thermal_inertia(mean_ti)

        themis_note = (
            "THEMIS 100m Infrared Regional Mosaic (thm_dir_N-30_000.png, Band 9 12.57 um) covers this corridor. "
            "Qualitative 8-bit display values only; direct quantitative radiance or temperature conversion is strictly prohibited."
            if in_themis_footprint
            else "Traverse is located outside the 2001 Mars Odyssey THEMIS 100m regional infrared mosaic footprint (lat -30° to 0°, lon 0° to 30°E)."
        )

        cal_notes = (
            "Calibrated from MGS TES Putzig & Mellon (2007) DBmap2007 using a 790-step reverse lookup table "
            "(formula I(t) = 50.0 * 50.0^t tiu across log range 50.0 to 2500.0 tiu). Mathematical step resolution is ~0.50%; "
            "nominal color-matching carries +/-2.5% quantization uncertainty. Values represent legend-calibrated proxy estimates, "
            "not direct spectrometer radiances."
        )

        return ThermophysicalRouteContext(
            min_tiu=min_ti,
            max_tiu=max_ti,
            mean_tiu=mean_ti,
            predominant_interpretation=predominant_interp,
            samples=samples,
            source_product="MGS TES Putzig & Mellon (2007) 20 ppd Global Thermal Inertia",
            native_resolution_desc="20 pixels per degree (~2.96 km/pixel at equator)",
            units="J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
            calibration_notes=cal_notes,
            themis_context=themis_note,
            temperature_prohibition_disclaimer=(
                "PROHIBITION: Thermal inertia (I = sqrt(k * rho * c)) represents resistance to diurnal temperature change, "
                "NOT kinetic temperature or surface heat. Never describe or present thermal inertia values as temperature."
            ),
        )

    # =========================================================================
    # SCIENCE OPPORTUNITY ANALYSIS (PHASE 8.7 DISCOVERIES)
    # =========================================================================

    def find_route_science_opportunities(
        self,
        coords_with_distance: List[Tuple[float, float, float]],
        corridor_radius_km: float = 150.0,
        max_opportunities: int = 6,
    ) -> List[RouteScienceOpportunity]:
        """Identify Phase 8.7 candidate discoveries situated near the traverse corridor."""
        if not coords_with_distance:
            return []

        opportunities: List[RouteScienceOpportunity] = []

        # Subsample route points for proximity testing
        route_sample = coords_with_distance[:: max(1, len(coords_with_distance) // 30)]
        if coords_with_distance[-1] not in route_sample:
            route_sample.append(coords_with_distance[-1])

        for disc in CANDIDATE_DISCOVERIES:
            d_lat = disc["latitude"]
            d_lon = disc["longitude"]

            min_dist_km = float("inf")
            closest_milepost_m = 0.0

            for r_lat, r_lon, r_dist_m in route_sample:
                dist_km = mars_haversine_distance_km(r_lat, r_lon, d_lat, d_lon)
                if dist_km < min_dist_km:
                    min_dist_km = dist_km
                    closest_milepost_m = r_dist_m

            if min_dist_km <= corridor_radius_km:
                cat_info = DISCOVERY_CATEGORIES.get(disc.get("category", "other"), {})
                investigation_text = (
                    disc.get("scientific_significance")
                    or f"Potential field investigation of {disc.get('title', 'target feature')}."
                )
                limits_val = disc.get("scientific_limitations", "")
                if isinstance(limits_val, list):
                    limits_text = " ".join(limits_val)
                else:
                    limits_text = str(limits_val) if limits_val else "Constrained by orbital resolution and lack of in-situ verification."

                opportunities.append(
                    RouteScienceOpportunity(
                        discovery_id=disc["id"],
                        title=disc["title"],
                        category=disc.get("category", "other"),
                        category_title=cat_info.get("title", disc.get("category", "Science Target")),
                        distance_from_route_km=round(min_dist_km, 2),
                        closest_route_milepost_m=round(closest_milepost_m, 1),
                        evidence_class=disc.get("evidence_class", "derived_measurement"),
                        supporting_datasets=disc.get("supporting_datasets", []),
                        primary_feature=disc.get("primary_feature", disc.get("title", "")),
                        potential_investigation=f"Candidate investigation: {investigation_text} (Not a confirmed finding)",
                        scientific_limitations=limits_text,
                    )
                )

        opportunities.sort(key=lambda o: o.distance_from_route_km)
        return opportunities[:max_opportunities]

    # =========================================================================
    # SINGLE ROUTE INTELLIGENCE ANALYSIS
    # =========================================================================

    def analyze_route(
        self,
        route: MarswalkRouteResponse,
        ls_deg: Optional[float] = None,
        ltst_hours: Optional[float] = None,
        tau: Optional[float] = None,
    ) -> RouteIntelligenceReport:
        """Produce exhaustive scientific intelligence report for a single-destination route."""
        # 1. Elevation Profile
        elev_profile = self.build_elevation_profile(
            path_points=route.path_points,
            dem_source=route.source_dataset,
            native_resolution_m=route.native_resolution_m,
        )

        elevations = [p.elevation_m for p in route.path_points]

        # 2. Terrain Intelligence
        terrain_intel = self.build_terrain_intelligence(
            elevations=elevations,
            slope_exposure_pct=route.slope_band_exposure_pct,
            mean_slope_deg=route.mean_route_slope_deg,
            max_slope_deg=route.max_route_slope_deg,
            total_surface_distance_m=route.total_surface_distance_m,
            unknown_data_exposure_pct=route.unknown_data_exposure_pct,
            dem_source=route.source_dataset,
            instrument=route.instrument,
            native_resolution_m=route.native_resolution_m,
            native_resolution_desc=route.native_resolution_desc,
        )

        # Build list of (lat, lon, distance_m) for spatial queries
        coords_with_dist = [(p.lat, p.lon, p.cumulative_distance_m) for p in route.path_points]

        # 3. Geological Context
        geo_context = self.build_geological_context(
            coords_with_distance=coords_with_dist,
            total_surface_distance_m=route.total_surface_distance_m,
        )

        # 4. Thermophysical Context
        thermal_context = self.build_thermophysical_context(
            coords_with_distance=coords_with_dist,
        )

        # 5. Science Opportunities
        science_opps = self.find_route_science_opportunities(
            coords_with_distance=coords_with_dist,
        )

        # 6. Optional Environmental Context
        env_context = None
        if ls_deg is not None and ltst_hours is not None:
            try:
                env_svc = get_environmental_service()
                pts_dicts = [
                    {
                        "lat": p.lat,
                        "lon": p.lon,
                        "elevation_m": p.elevation_m,
                        "distance_m": p.cumulative_distance_m,
                    }
                    for p in route.path_points
                ]
                env_context = env_svc.enrich_route_environmental_context(
                    pts_dicts,
                    ls_deg=ls_deg,
                    ltst_hours=ltst_hours,
                    tau=tau,
                )
            except Exception as e:
                logger.warning("Failed to enrich route with environmental context: %s", e)

        return RouteIntelligenceReport(
            route_id=route.route_id,
            route_name=route.route_name or f"Marswalk Route ({route.source_dataset})",
            surface_distance_m=route.total_surface_distance_m,
            horizontal_distance_m=route.total_horizontal_distance_m,
            optimization_cost=route.total_optimization_cost,
            start_coord=route.start_coord,
            dest_coord=route.dest_coord,
            elevation_profile=elev_profile,
            terrain_intelligence=terrain_intel,
            geological_context=geo_context,
            thermophysical_context=thermal_context,
            nearby_science_opportunities=science_opps,
            environmental_context=env_context,
            dem_source=route.source_dataset,
            instrument=route.instrument,
            tier=route.tier,
            native_resolution_desc=route.native_resolution_desc,
            vertical_datum=route.vertical_datum,
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
        )

    # =========================================================================
    # MULTI-STOP TRAVERSE INTELLIGENCE ANALYSIS
    # =========================================================================

    def analyze_multi_stop_traverse(
        self,
        traverse: MultiStopTraverseResponse,
        ls_deg: Optional[float] = None,
        ltst_hours: Optional[float] = None,
        tau: Optional[float] = None,
    ) -> MultiStopTraverseIntelligenceReport:
        """Produce comprehensive leg-by-leg and aggregated traverse intelligence report."""
        leg_reports: List[LegRouteIntelligence] = []
        aggregated_points: List[ElevationProfilePoint] = []
        all_elevations: List[float] = []

        running_distance_m = 0.0

        for leg in traverse.legs:
            # Try to fetch cached full route to get rich path points
            cached = get_cached_route(leg.route_id)
            if cached and cached.path_points:
                pts = cached.path_points
            else:
                # Reconstruct synthetic path points from leg geometry and metrics
                geom_coords = leg.geometry.get("coordinates", [])
                pts = []
                step_dist = leg.surface_distance_m / max(1, len(geom_coords) - 1)
                for idx, c in enumerate(geom_coords):
                    pts.append(
                        MarswalkRoutePoint(
                            index=idx,
                            lat=c[1],
                            lon=c[0] % 360.0,
                            elevation_m=leg.min_elevation_m + (leg.max_elevation_m - leg.min_elevation_m) * (idx / max(1, len(geom_coords) - 1)),
                            slope_deg=leg.mean_slope_deg,
                            slope_category="moderate",
                            cumulative_distance_m=idx * step_dist,
                        )
                    )

            src_info = next((s for s in TERRAIN_SOURCES if s["source_id"] == leg.source_dataset), None)
            leg_res_m = float(src_info["pixel_spacing_m"]) if src_info else 20.0
            leg_res_desc = src_info["pixel_spacing_desc"] if src_info else traverse.native_resolution_desc

            # Leg Elevation Profile
            leg_elev_profile = self.build_elevation_profile(
                path_points=pts,
                dem_source=leg.source_dataset,
                native_resolution_m=leg_res_m,
                start_distance_offset_m=running_distance_m,
            )

            # Leg Terrain Intelligence
            leg_elevs = [p.elevation_m for p in pts]
            all_elevations.extend(leg_elevs)

            leg_terrain = self.build_terrain_intelligence(
                elevations=leg_elevs,
                slope_exposure_pct=leg.slope_band_exposure_pct,
                mean_slope_deg=leg.mean_slope_deg,
                max_slope_deg=leg.max_slope_deg,
                total_surface_distance_m=leg.surface_distance_m,
                unknown_data_exposure_pct=0.0,
                dem_source=leg.source_dataset,
                instrument=traverse.instrument,
                native_resolution_m=leg_res_m,
                native_resolution_desc=leg_res_desc,
            )

            coords_with_dist = [(p.lat, p.lon, p.cumulative_distance_m + running_distance_m) for p in pts]

            # Leg Geological Context
            leg_geo = self.build_geological_context(
                coords_with_distance=coords_with_dist,
                total_surface_distance_m=leg.surface_distance_m,
            )

            # Leg Thermal Context
            leg_thermal = self.build_thermophysical_context(
                coords_with_distance=coords_with_dist,
            )

            # Leg Science Opportunities
            leg_opps = self.find_route_science_opportunities(
                coords_with_distance=coords_with_dist,
                corridor_radius_km=100.0,
            )

            # Leg Environmental Context
            leg_env = None
            if ls_deg is not None and ltst_hours is not None:
                try:
                    env_svc = get_environmental_service()
                    pts_dicts = [
                        {
                            "lat": p.lat,
                            "lon": p.lon,
                            "elevation_m": p.elevation_m,
                            "distance_m": p.cumulative_distance_m,
                        }
                        for p in pts
                    ]
                    leg_env = env_svc.enrich_route_environmental_context(
                        pts_dicts,
                        ls_deg=ls_deg,
                        ltst_hours=ltst_hours,
                        tau=tau,
                    )
                except Exception as e:
                    logger.debug("Failed to enrich leg %d with environmental context: %s", leg.leg_index, e)

            leg_reports.append(
                LegRouteIntelligence(
                    leg_index=leg.leg_index,
                    from_stop_id=leg.from_stop_id,
                    from_stop_name=leg.from_stop_name,
                    to_stop_id=leg.to_stop_id,
                    to_stop_name=leg.to_stop_name,
                    from_coord=leg.from_coord,
                    to_coord=leg.to_coord,
                    surface_distance_m=leg.surface_distance_m,
                    horizontal_distance_m=leg.horizontal_distance_m,
                    optimization_cost=leg.optimization_cost,
                    elevation_profile=leg_elev_profile,
                    terrain_intelligence=leg_terrain,
                    geological_context=leg_geo,
                    thermophysical_context=leg_thermal,
                    nearby_science_opportunities=leg_opps,
                    environmental_context=leg_env,
                    dem_source=leg.source_dataset,
                    native_resolution_desc=traverse.native_resolution_desc,
                    coverage_limitations=f"Leg evaluated over authentic {leg.source_dataset} DEM raster.",
                )
            )

            # Append to aggregated points with junction deduplication
            for p_idx, pt in enumerate(leg_elev_profile.points):
                if aggregated_points and p_idx == 0:
                    # Skip duplicate junction vertex
                    continue
                aggregated_points.append(
                    pt.model_copy(update={"sample_index": len(aggregated_points)})
                )

            running_distance_m += leg.surface_distance_m

        # Aggregated Elevation Profile
        total_dist = traverse.total_surface_distance_m
        num_agg = len(aggregated_points)
        sampling_interval = round(total_dist / (num_agg - 1), 2) if num_agg > 1 else 10.0
        agg_min_elev = round(min(all_elevations), 2) if all_elevations else traverse.min_elevation_m
        agg_max_elev = round(max(all_elevations), 2) if all_elevations else traverse.max_elevation_m

        agg_elev_summary = ElevationProfileSummary(
            min_elevation_m=agg_min_elev,
            max_elevation_m=agg_max_elev,
            cumulative_elevation_gain_m=traverse.cumulative_elevation_gain_m,
            cumulative_elevation_loss_m=traverse.cumulative_elevation_loss_m,
            net_elevation_change_m=round(all_elevations[-1] - all_elevations[0], 2) if all_elevations else 0.0,
            max_gradient_pct=round(max(p.local_gradient_pct for p in aggregated_points), 2) if aggregated_points else 0.0,
            mean_gradient_pct=round(float(np.mean([abs(p.local_gradient_pct) for p in aggregated_points])), 2) if aggregated_points else 0.0,
            sampling_interval_m=sampling_interval,
            total_samples=num_agg,
            points=aggregated_points,
        )

        # Aggregated Terrain Intelligence
        agg_terrain = self.build_terrain_intelligence(
            elevations=all_elevations,
            slope_exposure_pct=traverse.slope_band_exposure_pct,
            mean_slope_deg=traverse.mean_route_slope_deg,
            max_slope_deg=traverse.max_route_slope_deg,
            total_surface_distance_m=traverse.total_surface_distance_m,
            unknown_data_exposure_pct=traverse.unknown_data_exposure_pct,
            dem_source=traverse.source_dataset,
            instrument=traverse.instrument,
            native_resolution_m=1.0,
            native_resolution_desc=traverse.native_resolution_desc,
        )

        # Full traverse points for context queries
        all_coords_with_dist = [(p.lat, p.lon, p.distance_m) for p in aggregated_points]

        # Aggregated Geological Context
        agg_geo = self.build_geological_context(
            coords_with_distance=all_coords_with_dist,
            total_surface_distance_m=traverse.total_surface_distance_m,
            corridor_radius_km=100.0,
        )

        # Aggregated Thermophysical Context
        agg_thermal = self.build_thermophysical_context(
            coords_with_distance=all_coords_with_dist,
        )

        # Aggregated Science Opportunities
        agg_opps = self.find_route_science_opportunities(
            coords_with_distance=all_coords_with_dist,
            corridor_radius_km=150.0,
            max_opportunities=10,
        )

        # Aggregated Environmental Context
        agg_env = None
        if ls_deg is not None and ltst_hours is not None:
            try:
                env_svc = get_environmental_service()
                agg_pts_dicts = [
                    {
                        "lat": p.lat,
                        "lon": p.lon,
                        "elevation_m": p.elevation_m,
                        "distance_m": p.distance_m,
                    }
                    for p in aggregated_points
                ]
                agg_env = env_svc.enrich_route_environmental_context(
                    agg_pts_dicts,
                    ls_deg=ls_deg,
                    ltst_hours=ltst_hours,
                    tau=tau,
                )
            except Exception as e:
                logger.warning("Failed to enrich aggregated traverse with environmental context: %s", e)

        stop_names = [traverse.start_stop.name] + [s.name for s in traverse.ordered_stops] + [traverse.dest_stop.name]

        return MultiStopTraverseIntelligenceReport(
            traverse_id=traverse.traverse_id,
            traverse_name=traverse.traverse_name,
            total_surface_distance_m=traverse.total_surface_distance_m,
            total_horizontal_distance_m=traverse.total_horizontal_distance_m,
            total_optimization_cost=traverse.total_optimization_cost,
            total_legs=len(leg_reports),
            ordered_stop_names=stop_names,
            legs=leg_reports,
            aggregated_elevation_profile=agg_elev_summary,
            aggregated_terrain_intelligence=agg_terrain,
            aggregated_geological_context=agg_geo,
            aggregated_thermophysical_context=agg_thermal,
            aggregated_science_opportunities=agg_opps,
            aggregated_environmental_context=agg_env,
            dem_source=traverse.source_dataset,
            instrument=traverse.instrument,
            tier=traverse.tier,
            native_resolution_desc=traverse.native_resolution_desc,
            vertical_datum="MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
            safety_disclaimer=MARSWALK_SAFETY_DISCLAIMER,
        )

    # =========================================================================
    # METADATA AND ENGINE SPECIFICATIONS
    # =========================================================================

    @classmethod
    def get_metadata(cls) -> RouteIntelligenceMetadataResponse:
        """Return system metadata, scientific datums, calibration formulas, and analysis limitations."""
        terrain_datasets = [
            {
                "source_id": s["source_id"],
                "instrument": s["instrument"],
                "tier": s["tier"],
                "pixel_spacing": s["pixel_spacing_desc"],
                "bounds": {"lat": [s["lat_min"], s["lat_max"]], "lon": [s["lon_min"], s["lon_max"]]},
                "vertical_datum": "MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
            }
            for s in TERRAIN_SOURCES
        ]

        evidence_classes = [
            {"class": "direct_sensor_observation", "description": "Raw or calibrated original sensor observation products present on disk."},
            {"class": "derived_measurement", "description": "Processed DTM elevation, MOLA gridded height, slope, roughness, or geodesic distance."},
            {"class": "mapped_geological_interpretation", "description": "USGS SIM 3292 cartographic polygons, contacts, and structures (1:20M scale)."},
            {"class": "indicative_proxy", "description": "MGS TES thermal-inertia model estimates and THEMIS 8-bit display mosaics."},
        ]

        rules = [
            "Source elevation rasters and native spatial resolutions are preserved without destructive interpolation.",
            "Vertical reference datum is strictly MOLA Areoid (R=3,396,190 m); never combine incompatible vertical references.",
            "NoData pixels are never treated as zero elevation; gaps in elevation or thermal coverage remain explicitly labeled as unmeasured.",
            "USGS SIM 3292 global geological mapping (1:20,000,000 scale) carries ~5-10 km boundary uncertainty and represents cartographic interpretations, NOT direct in-situ rover measurements.",
            "Thermal inertia (I = sqrt(k * rho * c)) represents resistance to temperature change, NOT kinetic temperature or surface heat.",
            "Orbital terrain analysis does NOT certify human EVA or robotic traversability.",
        ]

        return RouteIntelligenceMetadataResponse(
            geological_map={
                "title": "USGS Scientific Investigations Map 3292 (Geologic Map of Mars)",
                "authors": "Tanaka et al. (2014); Skinner, Fortezzo, Hare (2023)",
                "scale": "1:20,000,000",
                "crs": "GCS_Mars_2000_Sphere (R=3,396,190 m)",
                "layers": ["SIM3292_Global_Geology", "SIM3292_Global_Contacts", "SIM3292_Global_Structure"],
            },
            thermal_dataset={
                "title": "MGS TES Global Thermal Inertia (Putzig & Mellon 2007)",
                "resolution": "20 pixels per degree (~2.96 km/pixel at equator)",
                "units": "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
                "calibration": "790-step logarithmic look-up table (I = 50 * 50^t)",
            },
            terrain_datasets=terrain_datasets,
            evidence_classes=evidence_classes,
            scientific_rules=rules,
        )


def get_route_intelligence_service() -> RouteIntelligenceService:
    """Retrieve singleton RouteIntelligenceService."""
    return RouteIntelligenceService()
