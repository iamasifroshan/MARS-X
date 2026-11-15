"""Pydantic Models for Route Intelligence & Scientific Traverse Analysis — Phase 8.8.4.

Provides formal schemas for:
- Elevation profile intelligence (MOLA Areoid, sampling intervals, local gradient, net change).
- Terrain intelligence (slope exposure distribution, roughness index, NoData verification, DEM transitions).
- Geological route context (SIM 3292 unit intersections, contact boundaries, structural features, 1:20M scale limitations).
- Thermophysical context (MGS TES thermal inertia, regolith interpretation, calibration uncertainty, THEMIS display context).
- Science opportunity analysis (Phase 8.7 candidate discovery proximity, evidence classification, potential investigations).
- Leg-by-leg and aggregated multi-stop traverse intelligence reports.
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from app.science.environmental_models import RouteEnvironmentalSummary


MARSWALK_SAFETY_DISCLAIMER = (
    "OPERATIONAL SAFETY WARNING: Marswalk route intelligence provides analytical and scientific "
    "characterization of orbital datasets only. Orbital DEMs and 1:20,000,000 geological maps do not "
    "resolve sub-metre surface hazards, boulder distributions, dust mantle thickness, or soil mechanical "
    "bearing capacity. No route generated or analyzed by MARS-X is certified safe for human EVA or robotic traversal."
)


class ElevationProfilePoint(BaseModel):
    """Single sampled elevation profile point along a traverse."""

    sample_index: int = Field(..., description="0-based sequential index along the profile")
    distance_m: float = Field(..., description="Cumulative surface ground distance from route start in metres")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in planetocentric degrees")
    lon: float = Field(..., description="Longitude in planetocentric degrees (0° to 360°E)")
    elevation_m: float = Field(..., description="Topographic elevation relative to MOLA Areoid datum in metres")
    slope_deg: float = Field(..., ge=0.0, le=90.0, description="Local terrain slope in degrees")
    local_gradient_pct: float = Field(..., description="Local vertical gradient (dz / ds * 100) in percent")
    dem_source: str = Field(..., description="Identifier of the underlying DEM raster used for sampling")
    resolution_m: float = Field(..., description="Native spatial pixel resolution of the DEM in metres")


class ElevationProfileSummary(BaseModel):
    """Authoritative elevation profile analytics along route geometry."""

    min_elevation_m: float = Field(..., description="Minimum elevation along profile relative to MOLA Areoid")
    max_elevation_m: float = Field(..., description="Maximum elevation along profile relative to MOLA Areoid")
    cumulative_elevation_gain_m: float = Field(..., description="Total cumulative ascent in metres")
    cumulative_elevation_loss_m: float = Field(..., description="Total cumulative descent in metres")
    net_elevation_change_m: float = Field(..., description="Net elevation difference (dest - start) in metres")
    max_gradient_pct: float = Field(..., description="Steepest local gradient encountered along the profile in percent")
    mean_gradient_pct: float = Field(..., description="Average absolute gradient along the profile in percent")
    sampling_interval_m: float = Field(..., description="Average physical ground distance between sample points in metres")
    total_samples: int = Field(..., description="Total number of discrete elevation profile samples")
    vertical_datum: str = Field(
        default="MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
        description="Authoritative vertical reference datum",
    )
    points: List[ElevationProfilePoint] = Field(..., description="Chronological sequence of profile samples")


class SlopeExposureBand(BaseModel):
    """Exposure details for a single slope categorization band."""

    category: str = Field(..., description="'low' (0-5°), 'moderate' (5-15°), 'high' (15-25°), 'critical' (>25°), 'unknown'")
    description: str = Field(..., description="Human-readable slope category interpretation")
    distance_m: float = Field(..., description="Total route distance spent within this slope band in metres")
    percentage: float = Field(..., description="Percentage of total route surface distance in this slope band")


class DemSourceSegment(BaseModel):
    """Segment of the traverse covered by a specific DEM source."""

    source_id: str = Field(..., description="Identifier of the DEM dataset")
    instrument: str = Field(..., description="Sensor / instrument (HiRISE, CTX, MOLA)")
    native_resolution_m: float = Field(..., description="Native ground pixel spacing in metres")
    start_distance_m: float = Field(..., description="Cumulative distance where this DEM source begins")
    end_distance_m: float = Field(..., description="Cumulative distance where this DEM source ends")


class TerrainIntelligenceSummary(BaseModel):
    """Comprehensive terrain analysis and geomorphological characterization of the route corridor."""

    slope_distribution: Dict[str, float] = Field(..., description="Exposure percentages across analytical slope bands")
    slope_exposure_bands: List[SlopeExposureBand] = Field(..., description="Detailed metre and percentage breakdown per slope band")
    mean_slope_deg: float = Field(..., description="Distance-weighted average slope across the traverse in degrees")
    max_slope_deg: float = Field(..., description="Steepest slope encountered along the entire route in degrees")
    roughness_index_m: float = Field(
        ...,
        description="Root-mean-square elevation deviation (RMSD) or standard deviation along the profile in metres",
    )
    roughness_classification: str = Field(
        ...,
        description="Derived morphological roughness indicator (e.g., 'Smooth planar', 'Undulating scarp', 'Rough blocky ejecta')",
    )
    nodata_distance_m: float = Field(default=0.0, description="Total distance traversing unmapped or NoData cells in metres")
    nodata_pct: float = Field(default=0.0, description="Percentage of route traversing NoData cells (must be 0.0 for valid routes)")
    coverage_status: str = Field(default="complete_verified_coverage", description="'complete_verified_coverage' or 'partial_coverage'")
    dem_source_segments: List[DemSourceSegment] = Field(..., description="DEM sources and resolution transitions along route")
    cross_resolution_transition: bool = Field(default=False, description="True if route transitions across distinct DEM products")
    terrain_limitations: str = Field(..., description="Explicit scientific caveats regarding DEM spatial resolution and sub-pixel obstacles")


class GeologicalContactCrossing(BaseModel):
    """Point along the traverse where the route crosses a geological unit boundary."""

    distance_m: float = Field(..., description="Cumulative distance from route start where the contact boundary is crossed in metres")
    coord: Tuple[float, float] = Field(..., description="(lat, lon) coordinates of the contact crossing")
    from_unit: str = Field(..., description="Unit code of the departing geological formation")
    to_unit: str = Field(..., description="Unit code of the entering geological formation")
    contact_type: str = Field(default="Stratigraphic Contact", description="Type of contact boundary from SIM 3292")


class GeologicalUnitSegment(BaseModel):
    """Section of the traverse passing through a specific USGS SIM 3292 geological unit."""

    unit_code: str = Field(..., description="Formal USGS SIM 3292 unit code (e.g. 'eNh', 'lNv', 'Achu')")
    unit_name: str = Field(..., description="Full formal chronostratigraphic unit name (Tanaka et al. 2014)")
    chronostratigraphic_period: str = Field(..., description="'Noachian', 'Hesperian', 'Amazonian', or 'Undivided'")
    distance_start_m: float = Field(..., description="Cumulative distance where the route enters this unit in metres")
    distance_end_m: float = Field(..., description="Cumulative distance where the route exits this unit in metres")
    traversed_length_m: float = Field(..., description="Total ground distance traversed within this unit in metres")
    traversed_pct: float = Field(..., description="Percentage of total route distance within this geological unit")
    description: str = Field(..., description="Formal geological and depositional/erosional description from Tanaka et al. (2014)")


class NearbyGeologicalStructure(BaseModel):
    """Tectonic, erosional, or volcanic structural feature from USGS SIM 3292 near the route corridor."""

    object_id: int = Field(..., description="Unique OBJECTID in USGS SIM 3292 Global Structure layer")
    morphology: str = Field(..., description="Structure morphology (e.g. 'Ridge', 'Trough', 'Scarp', 'Graben')")
    origin: str = Field(..., description="Geological origin (e.g. 'Tectonic', 'Fluvial', 'Volcanic', 'Erosional')")
    interpretation: str = Field(..., description="Geological interpretation (e.g. 'Wrinkle ridge', 'Channel axis', 'Fault scarp')")
    preservation: str = Field(..., description="Preservation state (e.g. 'Subdued', 'Crisp', 'Partly Buried')")
    dimension: str = Field(..., description="Dimension classification ('Narrow', 'Broad')")
    distance_from_route_km: float = Field(..., description="Shortest Great-Circle distance from the route to this feature in km")
    closest_coord: Tuple[float, float] = Field(..., description="(lat, lon) coordinates of the closest point on the feature")


class GeologicalRouteContext(BaseModel):
    """USGS SIM 3292 global chronostratigraphic geological context along the route corridor."""

    units_traversed: List[GeologicalUnitSegment] = Field(..., description="Chronological list of geological units crossed by route")
    boundaries_crossed: List[GeologicalContactCrossing] = Field(..., description="List of geological contacts crossed along the route")
    nearby_structures: List[NearbyGeologicalStructure] = Field(..., description="Structural and tectonic features within corridor")
    published_scale: str = Field(default="1:20,000,000", description="Published cartographic scale of USGS SIM 3292")
    cartographic_source: str = Field(
        default="USGS Scientific Investigations Map 3292 (Tanaka et al. 2014; Skinner et al. 2023)",
        description="Formal citation of the source map",
    )
    positional_uncertainty_km: float = Field(
        default=5.0,
        description="Nominal boundary positional uncertainty associated with 1:20M global mapping",
    )
    limitations_disclaimer: str = Field(
        ...,
        description="Essential scientific warning: 1:20M mapped units are interpretive regional polygons, NOT direct rover sensor measurements.",
    )


class ThermalInertiaSample(BaseModel):
    """Calibrated MGS TES thermal inertia sample at a point along the route."""

    distance_m: float = Field(..., description="Cumulative distance from route start in metres")
    lat: float = Field(..., description="Latitude of sample point")
    lon: float = Field(..., description="Longitude of sample point")
    thermal_inertia_tiu: Optional[float] = Field(
        ...,
        description="Calibrated Apparent Thermal Inertia in tiu (J m^-2 K^-1 s^-1/2). None if NoData.",
    )
    physical_interpretation: str = Field(..., description="Indicative regolith grain-size and surface type interpretation")


class ThermophysicalRouteContext(BaseModel):
    """MGS TES global thermal inertia characterization and THEMIS infrared context along route."""

    min_tiu: Optional[float] = Field(..., description="Lowest thermal inertia encountered along route in tiu")
    max_tiu: Optional[float] = Field(..., description="Highest thermal inertia encountered along route in tiu")
    mean_tiu: Optional[float] = Field(..., description="Average thermal inertia along route in tiu")
    predominant_interpretation: str = Field(
        ...,
        description="Overall surface regolith classification (e.g. dust mantle, sand/duricrust, rocky plains)",
    )
    samples: List[ThermalInertiaSample] = Field(..., description="Spatial thermal inertia samples along the route")
    source_product: str = Field(
        default="MGS TES Putzig & Mellon (2007) 20 ppd Global Thermal Inertia",
        description="Source dataset citation",
    )
    native_resolution_desc: str = Field(
        default="20 pixels per degree (~2.96 km/pixel at equator)",
        description="Native spatial resolution of TES raster",
    )
    units: str = Field(
        default="J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
        description="Authoritative physical units of thermal inertia",
    )
    calibration_notes: str = Field(
        ...,
        description="Documentation of 790-step logarithmic LUT calibration from Putzig & Mellon (2007) and nominal +/-2.5% uncertainty",
    )
    themis_context: str = Field(
        ...,
        description="Contextual note on 2001 Mars Odyssey THEMIS 100m IR mosaic availability (qualitative 8-bit DN only)",
    )
    temperature_prohibition_disclaimer: str = Field(
        default="PROHIBITION: Thermal inertia measures resistance to temperature change (I = sqrt(k * rho * c)), NOT kinetic temperature or heat. Never treat TIU values as surface temperature.",
        description="Mandatory scientific warning against confusing thermal inertia with temperature",
    )


class RouteScienceOpportunity(BaseModel):
    """Phase 8.7 Science Discovery situated near the planned traverse corridor."""

    discovery_id: str = Field(..., description="Unique Phase 8.7 discovery catalog ID")
    title: str = Field(..., description="Formal discovery title")
    category: str = Field(..., description="Scientific category ID")
    category_title: str = Field(..., description="Human-readable category title")
    distance_from_route_km: float = Field(..., description="Closest Great-Circle distance from the traverse to this discovery in km")
    closest_route_milepost_m: float = Field(..., description="Distance along the traverse where the discovery is closest in metres")
    evidence_class: str = Field(
        ...,
        description="'direct_sensor_observation', 'derived_measurement', 'mapped_geological_interpretation', or 'indicative_proxy'",
    )
    supporting_datasets: List[str] = Field(..., description="Cataloged datasets supporting this discovery")
    primary_feature: str = Field(..., description="Primary geomorphological feature")
    potential_investigation: str = Field(
        ...,
        description="Candidate scientific investigation hypothesis (clearly distinguished from confirmed findings)",
    )
    scientific_limitations: str = Field(..., description="Observational and instrument constraints on this investigation")


class LegRouteIntelligence(BaseModel):
    """Exhaustive scientific route intelligence report for a single pairwise route leg."""

    leg_index: int = Field(..., description="0-based sequence index of this leg in the traverse")
    from_stop_id: str = Field(..., description="Departure stop identifier")
    from_stop_name: str = Field(..., description="Departure stop name")
    to_stop_id: str = Field(..., description="Arrival stop identifier")
    to_stop_name: str = Field(..., description="Arrival stop name")
    from_coord: Tuple[float, float] = Field(..., description="(lat, lon) coordinates of departure")
    to_coord: Tuple[float, float] = Field(..., description="(lat, lon) coordinates of arrival")
    surface_distance_m: float = Field(..., description="Physical 3D surface traversal distance in metres")
    horizontal_distance_m: float = Field(..., description="Planimetric 2D traversal distance in metres")
    optimization_cost: float = Field(..., description="Analytical graph traversal cost minimized by A*")
    elevation_profile: ElevationProfileSummary = Field(..., description="High-resolution elevation profile along this leg")
    terrain_intelligence: TerrainIntelligenceSummary = Field(..., description="Terrain slope, roughness, and exposure analytics")
    geological_context: GeologicalRouteContext = Field(..., description="SIM 3292 geological units and structures along this leg")
    thermophysical_context: ThermophysicalRouteContext = Field(..., description="MGS TES thermal inertia and surface regolith context")
    nearby_science_opportunities: List[RouteScienceOpportunity] = Field(..., description="Nearby Phase 8.7 science discoveries")
    dem_source: str = Field(..., description="Primary DEM dataset used for this leg")
    native_resolution_desc: str = Field(..., description="Human-readable pixel spacing description")
    coverage_limitations: str = Field(..., description="Specific coverage and terrain resolution caveats")
    environmental_context: Optional[RouteEnvironmentalSummary] = Field(
        default=None,
        description="Analytical barometric pressure and solar geometry along this leg",
    )


class RouteIntelligenceReport(BaseModel):
    """Complete scientific intelligence report for a single-destination Marswalk route."""

    route_id: str = Field(..., description="Unique Marswalk route identifier (e.g. mw-a1b2c3d4)")
    route_name: Optional[str] = Field(default=None, description="Title of the route")
    surface_distance_m: float = Field(..., description="Physical 3D ground distance in metres")
    horizontal_distance_m: float = Field(..., description="Planimetric 2D distance in metres")
    optimization_cost: float = Field(..., description="Total graph traversal cost minimized by A*")
    start_coord: Tuple[float, float] = Field(..., description="(lat, lon) of route departure point")
    dest_coord: Tuple[float, float] = Field(..., description="(lat, lon) of route destination point")
    elevation_profile: ElevationProfileSummary = Field(..., description="MOLA Areoid elevation profile intelligence")
    terrain_intelligence: TerrainIntelligenceSummary = Field(..., description="Slope distribution, roughness, and exposure")
    geological_context: GeologicalRouteContext = Field(..., description="USGS SIM 3292 chronostratigraphic context")
    thermophysical_context: ThermophysicalRouteContext = Field(..., description="MGS TES thermal inertia context")
    nearby_science_opportunities: List[RouteScienceOpportunity] = Field(..., description="Nearby Phase 8.7 science discoveries")
    dem_source: str = Field(..., description="DEM dataset identifier")
    instrument: str = Field(..., description="Instrument name (HiRISE, CTX, MOLA)")
    tier: str = Field(..., description="Resolution tier")
    native_resolution_desc: str = Field(..., description="Native pixel spacing description")
    vertical_datum: str = Field(
        default="MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
        description="Vertical reference datum",
    )
    environmental_context: Optional[RouteEnvironmentalSummary] = Field(
        default=None,
        description="Analytical barometric pressure and solar geometry along the route",
    )
    safety_disclaimer: str = Field(default=MARSWALK_SAFETY_DISCLAIMER, description="Mandatory astronaut safety advisory")


class MultiStopTraverseIntelligenceReport(BaseModel):
    """Aggregated scientific intelligence report for a multi-stop science traverse."""

    traverse_id: str = Field(..., description="Unique multi-stop traverse identifier (e.g. mst-1a2b3c4d)")
    traverse_name: str = Field(..., description="Title of the planned multi-stop traverse")
    total_surface_distance_m: float = Field(..., description="Total physical 3D ground distance across all legs in metres")
    total_horizontal_distance_m: float = Field(..., description="Total 2D planimetric distance in metres")
    total_optimization_cost: float = Field(..., description="Total analytical cost minimized across the traverse")
    total_legs: int = Field(..., description="Number of constituent route legs")
    ordered_stop_names: List[str] = Field(..., description="Ordered list of visited stop names")
    legs: List[LegRouteIntelligence] = Field(..., description="Individual intelligence report for each constituent leg")
    aggregated_elevation_profile: ElevationProfileSummary = Field(
        ...,
        description="Unified continuous elevation profile across the entire traverse without duplicate junction vertices",
    )
    aggregated_terrain_intelligence: TerrainIntelligenceSummary = Field(
        ...,
        description="Overall terrain slope distribution, roughness index, and exposure across the full traverse",
    )
    aggregated_geological_context: GeologicalRouteContext = Field(
        ...,
        description="Consolidated geological units traversed, contact crossings, and nearby structures",
    )
    aggregated_thermophysical_context: ThermophysicalRouteContext = Field(
        ...,
        description="Consolidated MGS TES thermal inertia profile and regolith assessment",
    )
    aggregated_science_opportunities: List[RouteScienceOpportunity] = Field(
        ...,
        description="Deduplicated list of nearby science opportunities along the traverse",
    )
    aggregated_environmental_context: Optional[RouteEnvironmentalSummary] = Field(
        default=None,
        description="Analytical barometric pressure and solar geometry along the full traverse",
    )
    dem_source: str = Field(..., description="Primary DEM dataset resolving all traverse waypoints")
    instrument: str = Field(..., description="Instrument name (HiRISE, CTX, MOLA)")
    tier: str = Field(..., description="Resolution tier")
    native_resolution_desc: str = Field(..., description="Native resolution description")
    vertical_datum: str = Field(
        default="MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
        description="Vertical reference datum",
    )
    safety_disclaimer: str = Field(default=MARSWALK_SAFETY_DISCLAIMER, description="Mandatory astronaut safety advisory")


class RouteIntelligenceMetadataResponse(BaseModel):
    """Metadata describing the Route Intelligence analysis capabilities, datums, and scientific rules."""

    system_name: str = "MARS-X Route Intelligence & Scientific Traverse Analysis"
    version: str = "8.8.4"
    vertical_datum: str = "MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)"
    geological_map: Dict[str, Any]
    thermal_dataset: Dict[str, Any]
    terrain_datasets: List[Dict[str, Any]]
    evidence_classes: List[Dict[str, str]]
    scientific_rules: List[str]
    safety_disclaimer: str = MARSWALK_SAFETY_DISCLAIMER
