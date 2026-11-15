"""MARS-X — Climatology Models.

Schemas for seasonal and diurnal Martian climatology derived from the
Laboratoire de Météorologie Dynamique (LMD) Mars Climate Database (MCD v6.2)
and Mars Climate Sounder (MCS) atmospheric records.
"""

from typing import List, Dict, Optional, Literal, Any, Tuple
from pydantic import BaseModel, Field

ProvenanceClassification = Literal[
    "Historical Observation",
    "Analytical Model",
    "Climatological Model",
    "Derived Estimate",
    "Unavailable",
]

CLIMATOLOGY_SAFETY_DISCLAIMER = (
    "ASTRONAUT SAFETY & OPERATIONAL PROHIBITION: Climatological outputs represent multi-year statistical means "
    "from Mars Global Climate Model (GCM) simulations (MCD v6.2, LMD/ESA/CNES). They DO NOT constitute a live Martian "
    "weather forecast or life-support certification. Never describe routes or conditions as 'astronaut-safe', "
    "'safe pressure', 'safe temperature', or 'safe EVA'."
)


class ClimatologyPoint(BaseModel):
    """Climatological environmental parameters at a specific planetary location, season, and local time."""

    latitude: float = Field(..., description="Planetocentric latitude in degrees [-90, +90]")
    longitude: float = Field(..., description="Planetocentric East longitude in degrees [0, 360)")
    solar_longitude_ls_deg: float = Field(..., description="Areocentric solar longitude Ls in degrees [0, 360)")
    local_true_solar_time_hours: float = Field(..., description="Local True Solar Time (LTST) in decimal hours [0, 24)")
    elevation_m: float = Field(..., description="MOLA Areoid elevation in metres used for topographic adjustment")
    season_name: str = Field(..., description="Martian astronomical season name")
    surface_pressure_pa: float = Field(..., description="Climatological surface atmospheric pressure in Pa")
    atmospheric_temperature_k: float = Field(..., description="Ambient air temperature at 10m ALS in Kelvin")
    surface_temperature_k: float = Field(..., description="Ground surface kinetic temperature in Kelvin")
    wind_speed_m_s: float = Field(..., description="10m horizontal wind speed in m/s")
    wind_direction_deg: float = Field(
        ...,
        description="Meteorological wind direction (direction wind blows FROM) in degrees clockwise from North [0, 360)",
    )
    wind_cardinal: str = Field(..., description="Cardinal wind direction compass label (e.g. 'NNE', 'SSW')")
    dust_optical_depth: float = Field(..., description="Daily mean column visible dust optical depth tau (dimensionless)")
    density_kg_m3: float = Field(..., description="Near-surface atmospheric density in kg/m3")
    interpolation_method: str = Field(..., description="Multidimensional interpolation method applied")
    is_landmark: bool = Field(default=False, description="Whether location matches an exact ground-truth anchor landmark")
    nearest_landmark: Optional[str] = Field(default=None, description="Name of closest exploration landmark anchor")
    distance_to_landmark_km: Optional[float] = Field(default=None, description="Distance to closest landmark in km")
    classification: ProvenanceClassification = Field(
        default="Climatological Model",
        description="Scientific provenance classification",
    )
    model_version: str = Field(
        default="MCD v6.2 (LMD/ESA/CNES)",
        description="Model identifier and version",
    )
    safety_disclaimer: str = Field(
        default=CLIMATOLOGY_SAFETY_DISCLAIMER,
        description="Mandatory operational safety proscription",
    )


class ClimatologyProfilePoint(BaseModel):
    """Single point along a seasonal or diurnal climatology profile."""

    step_value: float = Field(..., description="Profile independent axis value (hours for diurnal, degrees Ls for seasonal)")
    surface_pressure_pa: float = Field(..., description="Surface atmospheric pressure in Pa")
    atmospheric_temperature_k: float = Field(..., description="Air temperature at 10m ALS in Kelvin")
    surface_temperature_k: float = Field(..., description="Ground surface temperature in Kelvin")
    wind_speed_m_s: float = Field(..., description="Horizontal wind speed in m/s")
    dust_optical_depth: float = Field(..., description="Column visible dust optical depth tau")


class ClimatologyProfileResponse(BaseModel):
    """Diurnal or seasonal climatological profile curve for a given planetary location."""

    latitude: float = Field(..., description="Planetocentric latitude in degrees")
    longitude: float = Field(..., description="Planetocentric East longitude in degrees")
    elevation_m: float = Field(..., description="MOLA elevation in metres")
    profile_type: Literal["diurnal", "seasonal"] = Field(..., description="Type of profile curve")
    fixed_parameter: str = Field(..., description="Fixed parameter description (e.g. 'Ls=0.0 deg' or 'LTST=12.0h')")
    independent_variable: str = Field(..., description="X-axis variable name ('LTST (hours)' or 'Solar Longitude Ls (degrees)')")
    points: List[ClimatologyProfilePoint] = Field(..., description="Array of profile points")
    min_temperature_k: float = Field(..., description="Minimum atmospheric temperature along profile in Kelvin")
    max_temperature_k: float = Field(..., description="Maximum atmospheric temperature along profile in Kelvin")
    mean_temperature_k: float = Field(..., description="Mean atmospheric temperature along profile in Kelvin")
    min_pressure_pa: float = Field(..., description="Minimum surface pressure along profile in Pa")
    max_pressure_pa: float = Field(..., description="Maximum surface pressure along profile in Pa")
    mean_pressure_pa: float = Field(..., description="Mean surface pressure along profile in Pa")
    classification: ProvenanceClassification = Field(
        default="Climatological Model",
        description="Scientific provenance classification",
    )
    model_version: str = Field(
        default="MCD v6.2 (LMD/ESA/CNES)",
        description="Model identifier and version",
    )
    safety_disclaimer: str = Field(
        default=CLIMATOLOGY_SAFETY_DISCLAIMER,
        description="Mandatory operational safety proscription",
    )


class ClimatologyVariableMetadata(BaseModel):
    """Metadata specification for an individual climatological variable."""

    name: str = Field(..., description="Variable programmatic key")
    label: str = Field(..., description="Human-readable display name")
    unit: str = Field(..., description="SI physical unit")
    valid_range: Tuple[float, float] = Field(..., description="Physical valid bounds [min, max]")
    description: str = Field(..., description="Scientific description and physical significance")


class ClimatologyMetadataResponse(BaseModel):
    """Metadata detailing the climatological dataset provenance, parameters, and limitations."""

    service_name: str = Field(..., description="Name of climatology service")
    version: str = Field(..., description="Dataset and service version")
    model_name: str = Field(..., description="Underlying planetary climate model")
    scenario: str = Field(..., description="Baseline atmospheric scenario")
    authoritative_source: str = Field(..., description="Institutional source")
    citation: str = Field(..., description="Academic citation")
    native_spatial_resolution: str = Field(..., description="GCM grid and HR topography resolution")
    vertical_level: str = Field(..., description="Boundary layer vertical level")
    temporal_coverage: str = Field(..., description="Seasonal and diurnal span")
    available_variables: List[ClimatologyVariableMetadata] = Field(..., description="List of supported variables")
    classification_tiers: List[ProvenanceClassification] = Field(..., description="Supported classification tiers")
    scientific_limitations: str = Field(..., description="Formal scientific limitations")
    safety_disclaimer: str = Field(default=CLIMATOLOGY_SAFETY_DISCLAIMER, description="Safety disclaimer")


class ClimatologyCoverageResponse(BaseModel):
    """Coverage boundaries, grid dimensions, and landmark anchors."""

    lat_min: float = Field(-90.0, description="Minimum latitude")
    lat_max: float = Field(90.0, description="Maximum latitude")
    lon_min: float = Field(0.0, description="Minimum East longitude")
    lon_max: float = Field(360.0, description="Maximum East longitude")
    seasonal_coverage: str = Field("0 to 360 deg Ls (All Martian Seasons)", description="Seasonal coverage")
    diurnal_coverage: str = Field("00:00 to 24:00 LTST (Complete Diurnal Cycle)", description="Diurnal coverage")
    grid_latitudes_deg: List[float] = Field(..., description="Native grid latitude bands")
    grid_longitudes_deg: List[float] = Field(..., description="Native grid longitude bands")
    landmarks: Dict[str, Dict[str, Any]] = Field(..., description="Anchor landmark stations")
    classification: ProvenanceClassification = Field(default="Climatological Model", description="Provenance")


class RoutePointClimatology(BaseModel):
    """Climatological environmental context for a single route waypoint."""

    point_index: int = Field(..., description="Zero-based waypoint index")
    lat: float = Field(..., description="Planetocentric latitude in degrees")
    lon: float = Field(..., description="Planetocentric East longitude in degrees")
    distance_m: float = Field(..., description="Cumulative distance from route start in metres")
    elevation_m: float = Field(..., description="MOLA Areoid elevation in metres")
    climatological_pressure_pa: float = Field(..., description="Estimated climatological surface pressure in Pa")
    climatological_temperature_k: float = Field(..., description="Estimated ambient air temperature at 10m ALS in Kelvin")
    climatological_surface_temperature_k: float = Field(..., description="Estimated ground surface temperature in Kelvin")
    climatological_wind_speed_m_s: float = Field(..., description="Estimated horizontal wind speed in m/s")
    climatological_wind_direction_deg: float = Field(..., description="Estimated wind direction in degrees [0, 360)")
    climatological_dust_optical_depth: float = Field(..., description="Estimated dust optical depth tau")


class RouteClimatologySummary(BaseModel):
    """Traverse-level aggregated climatological environmental summary."""

    solar_longitude_ls_deg: float = Field(..., description="Target solar longitude Ls in degrees")
    local_true_solar_time_hours: float = Field(..., description="Target local true solar time in hours")
    min_climatology_pressure_pa: float = Field(..., description="Minimum climatological pressure along traverse in Pa")
    max_climatology_pressure_pa: float = Field(..., description="Maximum climatological pressure along traverse in Pa")
    mean_climatology_pressure_pa: float = Field(..., description="Mean climatological pressure along traverse in Pa")
    min_climatology_temp_k: float = Field(..., description="Minimum ambient air temperature along traverse in Kelvin")
    max_climatology_temp_k: float = Field(..., description="Maximum ambient air temperature along traverse in Kelvin")
    mean_climatology_temp_k: float = Field(..., description="Mean ambient air temperature along traverse in Kelvin")
    min_surface_temp_k: float = Field(..., description="Minimum ground surface temperature along traverse in Kelvin")
    max_surface_temp_k: float = Field(..., description="Maximum ground surface temperature along traverse in Kelvin")
    mean_surface_temp_k: float = Field(..., description="Mean ground surface temperature along traverse in Kelvin")
    mean_wind_speed_m_s: float = Field(..., description="Mean wind speed along traverse in m/s")
    max_wind_speed_m_s: float = Field(..., description="Maximum wind speed along traverse in m/s")
    mean_dust_tau: float = Field(..., description="Mean dust optical depth tau along traverse")
    samples: List[RoutePointClimatology] = Field(..., description="Subsampled route climatological waypoints")
    classification: ProvenanceClassification = Field(
        default="Derived Estimate",
        description="Scientific provenance classification",
    )
    safety_disclaimer: str = Field(
        default=CLIMATOLOGY_SAFETY_DISCLAIMER,
        description="Mandatory operational safety proscription",
    )


class RouteClimatologyEnrichRequest(BaseModel):
    """Request payload for route climatological enrichment."""

    route_points: List[Dict[str, float]] = Field(
        ...,
        description="List of route points with 'lat', 'lon', 'elevation_m', and 'distance_m'",
    )
    ls_deg: float = Field(default=0.0, description="Martian solar longitude Ls [0, 360)")
    ltst_hours: float = Field(default=12.0, description="Local True Solar Time [0, 24)")
