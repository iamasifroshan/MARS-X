"""Environmental Intelligence Data Models — Phase 8.9.1.

Defines Pydantic data schemas for:
1. Analytical Martian atmospheric reference pressure modeling ($P(z) = P_{ref} * exp(-z / H)$).
2. Ground-truth pressure residual validation against in-situ rover observations (MEDA and REMS).
3. Deterministic Mars solar geometry (solar longitude Ls, declination, hour angle, SZA, flux, and dust attenuation).
4. Historical in-situ rover weather summaries from Mars 2020 Perseverance and MSL Curiosity.
5. Environmental route profile enrichment for Marswalk traverses.
"""

from typing import Dict, List, Optional, Tuple, Any, Literal
from pydantic import BaseModel, Field


# ── Provenance & Scientific Classification ──────────────────────────────────
# Permitted 4-tier classification labels
ProvenanceClassification = Literal[
    "Historical Observation",
    "Analytical Model",
    "Derived Estimate",
    "Unavailable",
]

ENVIRONMENTAL_SAFETY_DISCLAIMER = (
    "ASTRONAUT SAFETY & OPERATIONAL PROHIBITION: Environmental metrics are derived from "
    "analytical barometric approximations, deterministic orbital solar geometry, and localized historical "
    "point observations. They DO NOT constitute a live Martian weather forecast or life-support certification. "
    "Never describe routes or conditions as 'astronaut-safe', 'safe pressure', or 'survivable'."
)


class AtmosphericPressureEstimate(BaseModel):
    """Hydrostatic reference atmospheric pressure estimate at elevation z."""

    elevation_m: float = Field(..., description="Topographic elevation relative to MOLA Areoid datum in metres")
    reference_pressure_p0_pa: float = Field(default=610.0, description="Reference pressure P_ref at z=0 m (datum) in Pa")
    scale_height_h_m: float = Field(default=11100.0, description="Mean atmospheric scale height H in metres")
    reference_atmospheric_pressure_estimate_pa: float = Field(
        ...,
        description="Calculated reference atmospheric pressure in Pascals: P(z) = P_ref * exp(-z / H)",
    )
    vertical_datum: str = Field(
        default="MOLA Areoid (Equipotential Gravitational Surface, R=3,396,190 m)",
        description="Vertical geodetic reference datum",
    )
    classification: ProvenanceClassification = Field(
        default="Analytical Model",
        description="Scientific provenance classification",
    )
    model_formula: str = Field(
        default="P(z) = P_ref * exp(-z / H)",
        description="Underlying analytical mathematical formula",
    )
    scientific_limitations: str = Field(
        default=(
            "Isothermal exponential barometric approximation with constant scale height (11,100 m). "
            "Does not capture the seasonal CO2 condensation/sublimation atmospheric mass cycle (~25% annual amplitude) "
            "or localized diurnal barometric thermal tides (10-30 Pa peak-to-peak)."
        ),
        description="Physical and meteorological limitations of the reference model",
    )
    safety_disclaimer: str = Field(
        default=ENVIRONMENTAL_SAFETY_DISCLAIMER,
        description="Mandatory operational safety advisory",
    )


class PressureResidualBenchmark(BaseModel):
    """Quantitative residual analysis between the analytical pressure model and in-situ rover ground truth."""

    station_id: str = Field(..., description="Unique station identifier (e.g. 'MEDA_JEZERO', 'REMS_GALE')")
    station_name: str = Field(..., description="Rover instrument name and landing site")
    mission: str = Field(..., description="Flight mission identifier")
    landing_site: str = Field(..., description="Named landing location on Mars")
    coordinates: Tuple[float, float] = Field(..., description="(lat, lon) coordinates of the station in degrees")
    elevation_m: float = Field(..., description="MOLA Areoid ground elevation in metres")
    model_pressure_pa: float = Field(..., description="Analytical model estimate P(z) in Pa")
    observed_mean_pressure_pa: float = Field(..., description="Empirical mean observed pressure from PDS4 Sol 1 data in Pa")
    residual_pa: float = Field(..., description="Signed residual: P_model - P_observed in Pa")
    residual_percent: float = Field(..., description="Relative percentage error: ((P_model - P_observed) / P_observed) * 100")
    observation_sol: int = Field(default=1, description="Mission sol of the ground-truth observation")
    instrument_lid: str = Field(..., description="Official PDS4 Product Logical Identifier (LID)")
    classification: ProvenanceClassification = Field(
        default="Derived Estimate",
        description="Scientific provenance classification",
    )
    notes: str = Field(..., description="Scientific commentary explaining the physical origin of the residual")


class MarsTimeConversion(BaseModel):
    """Martian time system transformation between MTC, LMST, and LTST."""

    input_time_hours: float = Field(..., description="Input solar time in decimal hours [0, 24)")
    input_system: Literal["LMST", "LTST", "MTC"] = Field(..., description="Source time system")
    lon_deg: float = Field(..., description="Planetocentric longitude in degrees")
    lon_convention: Literal["east_positive", "west_positive"] = Field(
        default="east_positive",
        description="Longitude sign convention: 'east_positive' [0, 360) / [-180, 180] or 'west_positive' [0, 360)",
    )
    ls_deg: float = Field(..., description="Areocentric solar longitude Ls in degrees [0, 360)")
    equation_of_time_hours: float = Field(..., description="Equation of Time (LTST - LMST) in decimal hours")
    equation_of_time_minutes: float = Field(..., description="Equation of Time in decimal minutes")
    lmst_hours: float = Field(..., description="Local Mean Solar Time in decimal hours [0, 24)")
    ltst_hours: float = Field(..., description="Local True Solar Time in decimal hours [0, 24)")
    mtc_hours: float = Field(..., description="Coordinated Mars Time (MTC) at Prime Meridian in decimal hours [0, 24)")
    classification: ProvenanceClassification = Field(
        default="Analytical Model",
        description="Scientific provenance classification",
    )
    methodology: str = Field(
        default="Allison & McEwen (2000), Planetary and Space Science 48(2-3), pp. 215-235.",
        description="Formal citation for Mars timekeeping equations",
    )


class MarsSolarGeometry(BaseModel):
    """Deterministic Mars orbital and solar geometry parameters."""

    lat: float = Field(..., description="Planetocentric latitude in degrees [-90, +90]")
    lon: float = Field(..., description="Planetocentric East longitude in degrees [0, 360)")
    solar_longitude_ls_deg: float = Field(..., description="Areocentric solar longitude Ls in degrees [0, 360)")
    local_true_solar_time_hours: float = Field(..., description="Local True Solar Time (LTST) in decimal hours [0, 24)")
    local_mean_solar_time_hours: float = Field(..., description="Local Mean Solar Time (LMST) in decimal hours [0, 24)")
    equation_of_time_hours: float = Field(..., description="Equation of Time (LTST - LMST) in decimal hours")
    equation_of_time_minutes: float = Field(..., description="Equation of Time (LTST - LMST) in decimal minutes")
    season_name: str = Field(..., description="Martian astronomical season title")
    mars_sun_distance_au: float = Field(..., description="Instantaneous Mars-Sun orbital radius vector in Astronomical Units")
    solar_declination_deg: float = Field(..., description="Sub-solar planetocentric declination delta in degrees")
    hour_angle_deg: float = Field(..., description="Solar hour angle omega in degrees (0 deg at solar noon)")
    solar_zenith_angle_deg: float = Field(..., description="Solar Zenith Angle (SZA) in degrees [0, 180]")
    solar_elevation_deg: float = Field(..., description="Solar elevation angle above local horizon in degrees (90 - SZA)")
    day_night_status: str = Field(..., description="Diurnal state ('Day', 'Night', 'Polar Day', 'Polar Night', 'Twilight')")
    is_day: bool = Field(..., description="Boolean flag: True if solar elevation > 0 deg (SZA < 90 deg)")
    sunrise_hour: Optional[float] = Field(default=None, description="Local true solar time of sunrise in decimal hours (None during polar night/day)")
    sunset_hour: Optional[float] = Field(default=None, description="Local true solar time of sunset in decimal hours (None during polar night/day)")
    polar_condition: Optional[str] = Field(default=None, description="Polar state: None, 'Polar Day (Midnight Sun)', or 'Polar Night'")
    toa_normal_irradiance_w_m2: float = Field(
        ...,
        description="Top-Of-Atmosphere (TOA) normal-incidence solar irradiance S_Mars = S_0 / r^2 in W/m2",
    )
    toa_horizontal_irradiance_w_m2: float = Field(
        ...,
        description="Top-Of-Atmosphere (TOA) direct horizontal solar irradiance S_Mars * max(0, cos(SZA)) in W/m2 (0.0 when SZA >= 90 deg)",
    )
    surface_direct_normal_irradiance_w_m2: Optional[float] = Field(
        default=None,
        description="Direct beam normal-incidence solar irradiance at surface after dust extinction in W/m2 (0.0 when SZA >= 90 deg)",
    )
    surface_direct_horizontal_irradiance_w_m2: float = Field(
        ...,
        description="Direct beam horizontal solar irradiance at surface in W/m2 after geometric incidence and dust extinction (0.0 when SZA >= 90 deg)",
    )
    top_of_atmosphere_solar_flux_w_m2: float = Field(
        ...,
        description="TOA direct horizontal solar irradiance in W/m2 (legacy alias for toa_horizontal_irradiance_w_m2)",
    )
    optical_depth_tau: Optional[float] = Field(
        default=None,
        description="Optional column dust optical depth tau (tau >= 0) used for Beer-Lambert attenuation",
    )
    surface_solar_flux_w_m2: float = Field(
        ...,
        description="Direct surface horizontal solar flux in W/m2 (legacy alias for surface_direct_horizontal_irradiance_w_m2; does not include diffuse skylight)",
    )
    classification: ProvenanceClassification = Field(
        default="Analytical Model",
        description="Scientific provenance classification",
    )
    methodology_citation: str = Field(
        default="Allison, M., & McEwen, M. (2000). Planetary and Space Science 48(2-3), 215-235.",
        description="Formal scientific citation for the orbital and solar formulations",
    )
    safety_disclaimer: str = Field(
        default=ENVIRONMENTAL_SAFETY_DISCLAIMER,
        description="Mandatory operational safety advisory",
    )


class HistoricalRoverWeatherRecord(BaseModel):
    """Individual sampled time-series observation from in-situ rover sensors."""

    station: str = Field(..., description="Rover instrument abbreviation ('MEDA' or 'REMS')")
    timestamp_or_sclk: str = Field(..., description="Spacecraft Clock (SCLK) or J2000 integer timestamp")
    lmst: str = Field(..., description="Local Mean Solar Time string")
    ltst: str = Field(..., description="Local True Solar Time string")
    pressure_pa: Optional[float] = Field(default=None, description="Atmospheric pressure in Pa")
    ambient_temperature_k: Optional[float] = Field(default=None, description="Ambient air temperature in Kelvin")
    ground_temperature_k: Optional[float] = Field(default=None, description="Ground surface brightness temperature in Kelvin")
    relative_humidity_percent: Optional[float] = Field(default=None, description="Local relative humidity percentage")
    sensor_flags: Optional[Dict[str, Any]] = Field(default=None, description="Sensor health and obstruction flags")


class HistoricalWeatherSummary(BaseModel):
    """Synthesized meteorological summary of PDS4 Sol 1 in-situ rover observations."""

    station_id: str = Field(..., description="Unique station identifier ('MEDA_JEZERO' or 'REMS_GALE')")
    instrument_name: str = Field(..., description="Full scientific instrument name")
    mission: str = Field(..., description="NASA flight mission")
    site_name: str = Field(..., description="Geographical landing site")
    coordinates: Tuple[float, float] = Field(..., description="(lat, lon) coordinates in degrees")
    elevation_m: float = Field(..., description="MOLA Areoid elevation in metres")
    sol: int = Field(default=1, description="Mission sol represented by this record")
    solar_longitude_range_deg: Tuple[float, float] = Field(..., description="(min_Ls, max_Ls) during observation sol")
    total_samples: int = Field(..., description="Total valid sensor rows parsed from PDS4 file")
    pressure_summary_pa: Optional[Dict[str, float]] = Field(default=None, description="Min, max, and mean pressure in Pa")
    ambient_temp_summary_k: Optional[Dict[str, float]] = Field(default=None, description="Min, max, and mean air temperature in K")
    ground_temp_summary_k: Optional[Dict[str, float]] = Field(default=None, description="Min, max, and mean ground temperature in K")
    relative_humidity_summary_pct: Optional[Dict[str, float]] = Field(default=None, description="Min, max, and mean RH %")
    irradiance_summary_w_m2: Optional[Dict[str, float]] = Field(default=None, description="Downward and upward IR / UV flux stats")
    pds4_source_lid: str = Field(..., description="Official PDS4 Product Logical Identifier (LID)")
    classification: ProvenanceClassification = Field(
        default="Historical Observation",
        description="Strict scientific provenance classification",
    )
    temporal_disclaimer: str = Field(
        default=(
            "HISTORICAL IN-SITU POINT OBSERVATION ONLY: These data represent actual sensor measurements "
            "recorded during Sol 1 of the rover's mission at its specific landing site. They DO NOT represent "
            "current, live, or global Martian weather, and cannot be used to extrapolate ambient conditions at "
            "arbitrary traverse locations."
        ),
        description="Mandatory scientific warning against spatial or temporal over-extrapolation",
    )
    sample_records: List[HistoricalRoverWeatherRecord] = Field(
        default_factory=list,
        description="First 5 representative samples from the time series",
    )


class RoutePointEnvironment(BaseModel):
    """Environmental parameters evaluated at an individual waypoint along a Marswalk route."""

    point_index: int = Field(..., description="Sequence index of the waypoint along the route")
    lat: float = Field(..., description="Planetocentric latitude in degrees")
    lon: float = Field(..., description="Planetocentric East longitude in degrees")
    distance_m: float = Field(..., description="Cumulative distance from route start in metres")
    elevation_m: float = Field(..., description="MOLA Areoid elevation in metres")
    reference_pressure_pa: float = Field(..., description="Estimated reference barometric pressure P(z) in Pa")
    solar_zenith_angle_deg: float = Field(..., description="Solar Zenith Angle (SZA) in degrees")
    solar_elevation_deg: float = Field(..., description="Solar elevation angle in degrees")
    is_day: bool = Field(..., description="True if Sun is above the horizon (solar elevation > 0 deg)")
    toa_normal_irradiance_w_m2: float = Field(
        ...,
        description="Top-of-atmosphere normal solar irradiance S_0 / r^2 in W/m2",
    )
    toa_horizontal_irradiance_w_m2: float = Field(
        ...,
        description="Top-of-atmosphere direct horizontal solar irradiance in W/m2 (0.0 when SZA >= 90 deg)",
    )
    surface_direct_horizontal_irradiance_w_m2: float = Field(
        ...,
        description="Attenuated direct beam horizontal solar irradiance in W/m2 (strictly 0.0 when SZA >= 90 deg)",
    )
    toa_solar_flux_w_m2: float = Field(
        ...,
        description="Top-of-atmosphere direct horizontal solar flux in W/m2 (legacy alias for toa_horizontal_irradiance_w_m2)",
    )
    surface_solar_flux_w_m2: float = Field(
        ...,
        description="Attenuated direct surface horizontal solar flux in W/m2 (legacy alias for surface_direct_horizontal_irradiance_w_m2)",
    )


class RouteEnvironmentalSummary(BaseModel):
    """Aggregated environmental profile along a planned Marswalk traverse."""

    solar_longitude_ls_deg: float = Field(..., description="Assumed areocentric solar longitude Ls in degrees")
    local_true_solar_time_hours: float = Field(..., description="Assumed Local True Solar Time (LTST) in decimal hours")
    optical_depth_tau: Optional[float] = Field(default=None, description="Assumed column dust optical depth tau")
    min_pressure_pa: float = Field(..., description="Minimum reference atmospheric pressure along traverse in Pa")
    max_pressure_pa: float = Field(..., description="Maximum reference atmospheric pressure along traverse in Pa")
    mean_pressure_pa: float = Field(..., description="Mean reference atmospheric pressure along traverse in Pa")
    min_surface_flux_w_m2: float = Field(..., description="Minimum direct surface horizontal solar flux along traverse in W/m2")
    max_surface_flux_w_m2: float = Field(..., description="Maximum direct surface horizontal solar flux along traverse in W/m2")
    mean_surface_flux_w_m2: float = Field(..., description="Mean direct surface horizontal solar flux along traverse in W/m2")
    daylight_percentage: float = Field(..., description="Percentage of the traverse bathed in direct sunlight [0, 100]")
    samples: List[RoutePointEnvironment] = Field(..., description="Subsampled route environmental waypoints")
    classification: ProvenanceClassification = Field(
        default="Derived Estimate",
        description="Scientific provenance classification",
    )
    safety_disclaimer: str = Field(
        default=ENVIRONMENTAL_SAFETY_DISCLAIMER,
        description="Mandatory operational safety advisory",
    )


class EnvironmentalMetadataResponse(BaseModel):
    """Catalogue and metadata description of all available environmental services and models."""

    service_name: str = "MARS-X Environmental Intelligence Service"
    version: str = "Phase 8.9.1"
    available_models: List[str] = Field(
        default_factory=lambda: [
            "Analytical Hydrostatic Barometric Pressure: P(z) = P_ref * exp(-z / H)",
            "Deterministic Mars Solar Geometry (Allison & McEwen 2000)",
            "In-Situ Rover Ground Truth: Mars 2020 Perseverance MEDA Sol 1",
            "In-Situ Rover Ground Truth: MSL Curiosity REMS Sol 1",
        ]
    )
    reference_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "p_ref_pa": 610.0,
            "scale_height_m": 11100.0,
            "mola_areoid_radius_m": 3396190.0,
            "mars_axial_tilt_deg": 25.19,
            "mars_semimajor_axis_au": 1.52368,
            "mars_eccentricity": 0.09341,
            "solar_constant_1au_w_m2": 1361.0,
        }
    )
    classification_tiers: List[ProvenanceClassification] = Field(
        default_factory=lambda: [
            "Historical Observation",
            "Analytical Model",
            "Derived Estimate",
            "Unavailable",
        ]
    )
    scientific_limitations: str = Field(
        default=(
            "1. No continuous global dynamic 3D atmospheric model or live sensor network currently exists in the dataset. "
            "2. Pressure calculations use an isothermal exponential approximation and ignore CO2 condensation seasonal cycles. "
            "3. MEDA and REMS data are localized historical single-sol observations. "
            "4. TES thermal inertia indicates regolith physical properties, not kinetic temperature. "
            "5. THEMIS mosaics are qualitative 8-bit radiance proxies."
        )
    )
    safety_disclaimer: str = Field(default=ENVIRONMENTAL_SAFETY_DISCLAIMER)
