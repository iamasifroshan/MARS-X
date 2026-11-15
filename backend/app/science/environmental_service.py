"""Environmental Intelligence Service — Phase 8.9.1.

Implements:
1. Analytical barometric pressure reference model: P(z) = P_ref * exp(-z / H).
2. Deterministic Mars orbital and solar geometry (Allison & McEwen 2000).
3. In-situ rover historical observation parsers (Perseverance MEDA and MSL REMS).
4. Model-to-observation residual benchmarking.
5. Environmental enrichment for single-leg and multi-stop Marswalk traverses.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from app.science.environmental_models import (
    AtmosphericPressureEstimate,
    PressureResidualBenchmark,
    MarsSolarGeometry,
    MarsTimeConversion,
    HistoricalRoverWeatherRecord,
    HistoricalWeatherSummary,
    RoutePointEnvironment,
    RouteEnvironmentalSummary,
    EnvironmentalMetadataResponse,
    ENVIRONMENTAL_SAFETY_DISCLAIMER,
)

logger = logging.getLogger("MARS-X.science.environmental")

# Base data directory relative to repository root
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "originals"
MEDA_DIR = DATA_DIR / "meda"
REMS_DIR = DATA_DIR / "rems"

# Physical and Orbital Constants
P_REF_DEFAULT_PA = 610.0  # Triple point of pure water at z=0 m MOLA datum
SCALE_HEIGHT_DEFAULT_M = 11100.0  # Isothermal mean atmospheric scale height
MOLA_AREOID_RADIUS_M = 3396190.0

MARS_AXIAL_TILT_DEG = 25.19  # Obliquity
MARS_SEMIMAJOR_AXIS_AU = 1.52368
MARS_ECCENTRICITY = 0.09341
MARS_PERIHELION_LS_DEG = 251.0
SOLAR_CONSTANT_1AU_W_M2 = 1361.0


class EnvironmentalIntelligenceService:
    """Core service for planetary environmental calculations and historical observational summaries."""

    def __init__(
        self,
        p_ref_pa: float = P_REF_DEFAULT_PA,
        scale_height_m: float = SCALE_HEIGHT_DEFAULT_M,
    ):
        self.p_ref_pa = p_ref_pa
        self.scale_height_m = scale_height_m
        self._meda_cache: Optional[HistoricalWeatherSummary] = None
        self._rems_cache: Optional[HistoricalWeatherSummary] = None

    # ── 1. Atmospheric Reference Pressure Model ────────────────────────────
    def estimate_atmospheric_pressure(
        self,
        elevation_m: float,
        p_ref_pa: Optional[float] = None,
        scale_height_m: Optional[float] = None,
    ) -> AtmosphericPressureEstimate:
        """Compute the analytical reference atmospheric pressure at elevation z relative to MOLA Areoid.

        P(z) = P_ref * exp(-z / H)
        """
        if elevation_m is None or math.isnan(elevation_m) or math.isinf(elevation_m):
            raise ValueError(f"Invalid elevation value: {elevation_m}. Must be a finite real number.")

        if elevation_m < -15000.0 or elevation_m > 30000.0:
            raise ValueError(
                f"Topographic elevation {elevation_m} m is outside the valid Martian elevation envelope (-15,000 to +30,000 m)."
            )

        p0 = p_ref_pa if p_ref_pa is not None else self.p_ref_pa
        h = scale_height_m if scale_height_m is not None else self.scale_height_m

        if p0 <= 0:
            raise ValueError(f"Reference pressure P_ref must be positive (received {p0} Pa).")
        if h <= 0:
            raise ValueError(f"Atmospheric scale height H must be positive (received {h} m).")

        # Barometric formula
        p_z = p0 * math.exp(-elevation_m / h)

        return AtmosphericPressureEstimate(
            elevation_m=float(elevation_m),
            reference_pressure_p0_pa=float(p0),
            scale_height_h_m=float(h),
            reference_atmospheric_pressure_estimate_pa=round(float(p_z), 2),
        )

    # ── 2. Time Systems & Equation of Time (Allison & McEwen 2000) ─────────
    def calculate_equation_of_time(self, ls_deg: float) -> Tuple[float, float]:
        """Compute the Martian Equation of Time (EOT = LTST - LMST) from areocentric solar longitude Ls.

        Based on Allison & McEwen (2000), Planetary and Space Science 48(2-3), pp. 215-235:
        EOT = 2.861° * sin(2*Ls) - 0.071° * sin(4*Ls) + 0.002° * sin(6*Ls) - (nu - M)
        where (nu - M) is the Keplerian equation of center.

        Returns:
            Tuple of (eot_deg, eot_hours)
        """
        ls_norm = ls_deg % 360.0
        ls_rad = math.radians(ls_norm)

        # 1. Reduction to the equator harmonic series (axial tilt effect)
        term_equator = (
            2.861 * math.sin(2.0 * ls_rad)
            - 0.071 * math.sin(4.0 * ls_rad)
            + 0.002 * math.sin(6.0 * ls_rad)
        )

        # 2. Keplerian Equation of Center (eccentricity effect)
        # True anomaly nu relative to perihelion Ls_p = 250.99°
        nu_deg = (ls_norm - MARS_PERIHELION_LS_DEG) % 360.0
        nu_rad = math.radians(nu_deg)
        e = MARS_ECCENTRICITY

        # Eccentric anomaly E via half-angle relation: tan(E/2) = sqrt((1-e)/(1+e)) * tan(nu/2)
        tan_e_half = math.sqrt((1.0 - e) / (1.0 + e)) * math.tan(nu_rad / 2.0)
        e_rad = 2.0 * math.atan(tan_e_half)
        m_rad = e_rad - e * math.sin(e_rad)
        m_deg = math.degrees(m_rad) % 360.0

        # Equation of center in degrees [-180, +180]
        eq_center = (nu_deg - m_deg + 180.0) % 360.0 - 180.0

        # 3. Net Equation of Time in degrees and hours
        eot_deg = term_equator - eq_center
        eot_hours = eot_deg / 15.0

        return eot_deg, eot_hours

    def convert_mars_time(
        self,
        time_hours: float,
        from_system: str,
        to_system: str,
        lon_deg: float,
        ls_deg: float,
        lon_convention: str = "east_positive",
    ) -> MarsTimeConversion:
        """Convert solar time between MTC, LMST, and LTST according to longitude convention.

        Supported systems: 'LMST', 'LTST', 'MTC'.
        Supported longitude conventions:
        - 'east_positive': Planetocentric East longitude [0, 360) or [-180, +180].
        - 'west_positive': Planetocentric West longitude [0, 360).
        """
        from_sys = from_system.upper().strip()
        to_sys = to_system.upper().strip()
        valid_systems = {"LMST", "LTST", "MTC"}
        if from_sys not in valid_systems or to_sys not in valid_systems:
            raise ValueError(f"Invalid time system: '{from_system}' -> '{to_system}'. Must be LMST, LTST, or MTC.")

        # Standardize longitude to East-positive [0, 360)
        if lon_convention.lower() == "west_positive":
            lon_east = (360.0 - lon_deg) % 360.0
        else:
            lon_east = lon_deg % 360.0

        eot_deg, eot_hours = self.calculate_equation_of_time(ls_deg)
        t_in = time_hours % 24.0

        # Step 1: Resolve to MTC (Coordinated Mars Time at Airy-0 Prime Meridian)
        if from_sys == "MTC":
            mtc = t_in
            lmst = (mtc + lon_east / 15.0) % 24.0
            ltst = (lmst + eot_hours) % 24.0
        elif from_sys == "LMST":
            lmst = t_in
            mtc = (lmst - lon_east / 15.0) % 24.0
            ltst = (lmst + eot_hours) % 24.0
        else:  # LTST
            ltst = t_in
            lmst = (ltst - eot_hours) % 24.0
            mtc = (lmst - lon_east / 15.0) % 24.0

        return MarsTimeConversion(
            input_time_hours=round(t_in, 4),
            input_system=from_sys,  # type: ignore
            lon_deg=round(lon_deg, 4),
            lon_convention="west_positive" if lon_convention.lower() == "west_positive" else "east_positive",
            ls_deg=round(ls_deg, 2),
            equation_of_time_hours=round(eot_hours, 4),
            equation_of_time_minutes=round(eot_hours * 60.0, 2),
            lmst_hours=round(lmst, 4),
            ltst_hours=round(ltst, 4),
            mtc_hours=round(mtc, 4),
        )

    # ── 3. Deterministic Mars Solar Geometry & Irradiance ───────────────────
    def calculate_solar_geometry(
        self,
        lat: float,
        lon: float,
        ls_deg: float = 0.0,
        ltst_hours: float = 12.0,
        tau: Optional[float] = None,
        time_system: str = "LTST",
        lon_convention: str = "east_positive",
    ) -> MarsSolarGeometry:
        """Calculate deterministic Mars solar geometry, declination, SZA, and solar irradiance.

        Distinguishes:
        - Normal-incidence TOA solar irradiance: S_Mars = S_0 / r^2
        - Direct horizontal TOA solar irradiance: S_Mars * max(0, cos(SZA))
        - Direct beam normal-incidence surface irradiance: S_Mars * exp(-tau * airmass)
        - Direct beam horizontal surface irradiance: S_Mars * max(0, cos(SZA)) * exp(-tau * airmass)
        When SZA >= 90 deg, horizontal irradiance evaluates strictly to 0.0 W/m2.
        """
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} must be in range [-90.0, +90.0] degrees.")

        # Standardize longitude to East-positive [0, 360)
        if lon_convention.lower() == "west_positive":
            norm_lon = (360.0 - lon) % 360.0
        else:
            norm_lon = lon % 360.0

        ls_norm = ls_deg % 360.0

        # Calculate Equation of Time (EOT)
        eot_deg, eot_hours = self.calculate_equation_of_time(ls_norm)

        # Handle time system input (LTST vs LMST)
        time_sys = time_system.upper().strip()
        if time_sys == "LMST":
            lmst_val = ltst_hours % 24.0
            actual_ltst = (lmst_val + eot_hours) % 24.0
        else:
            actual_ltst = ltst_hours % 24.0
            lmst_val = (actual_ltst - eot_hours) % 24.0

        if tau is not None and tau < 0.0:
            raise ValueError(f"Dust optical depth tau cannot be negative (received {tau}).")

        # Astronomical season identification
        if 0.0 <= ls_norm < 90.0:
            season_name = "Northern Spring / Southern Autumn"
        elif 90.0 <= ls_norm < 180.0:
            season_name = "Northern Summer / Southern Winter"
        elif 180.0 <= ls_norm < 270.0:
            season_name = "Northern Autumn / Southern Spring"
        else:
            season_name = "Northern Winter / Southern Summer"

        # 1. Mars-Sun Distance r(Ls) in AU
        ls_rad = math.radians(ls_norm)
        perihelion_rad = math.radians(MARS_PERIHELION_LS_DEG)
        true_anomaly = ls_rad - perihelion_rad
        num = MARS_SEMIMAJOR_AXIS_AU * (1.0 - MARS_ECCENTRICITY**2)
        den = 1.0 + MARS_ECCENTRICITY * math.cos(true_anomaly)
        r_au = num / den

        # Normal-incidence solar constant at Mars top of atmosphere (S_Mars = S_0 / r^2)
        s0_mars = SOLAR_CONSTANT_1AU_W_M2 / (r_au**2)

        # 2. Solar Declination delta
        axial_tilt_rad = math.radians(MARS_AXIAL_TILT_DEG)
        sin_declination = math.sin(axial_tilt_rad) * math.sin(ls_rad)
        sin_declination = max(-1.0, min(1.0, sin_declination))
        declination_rad = math.asin(sin_declination)
        declination_deg = math.degrees(declination_rad)

        # 3. Solar Hour Angle omega (0 deg at solar noon LTST=12h, 15 deg per hour)
        hour_angle_deg = (actual_ltst - 12.0) * 15.0
        hour_angle_rad = math.radians(hour_angle_deg)

        # 4. Solar Zenith Angle (SZA)
        lat_rad = math.radians(lat)
        cos_sza = (
            math.sin(lat_rad) * math.sin(declination_rad)
            + math.cos(lat_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad)
        )
        cos_sza = max(-1.0, min(1.0, cos_sza))
        sza_rad = math.acos(cos_sza)
        sza_deg = math.degrees(sza_rad)
        solar_elevation_deg = 90.0 - sza_deg

        # 5. Sunrise / Sunset and Polar Day/Night
        tan_lat_tan_dec = math.tan(lat_rad) * math.tan(declination_rad)
        cos_omega_0 = -tan_lat_tan_dec

        sunrise_hour: Optional[float] = None
        sunset_hour: Optional[float] = None
        polar_condition: Optional[str] = None

        if cos_omega_0 <= -1.0:
            # Sun never sets (Polar Day / Midnight Sun)
            polar_condition = "Polar Day (Midnight Sun)"
            day_night_status = "Polar Day"
            is_day = True
        elif cos_omega_0 >= 1.0:
            # Sun never rises (Polar Night)
            polar_condition = "Polar Night"
            day_night_status = "Polar Night"
            is_day = False
        else:
            omega_0_rad = math.acos(cos_omega_0)
            omega_0_deg = math.degrees(omega_0_rad)
            delta_hours = omega_0_deg / 15.0
            sunrise_hour = round((12.0 - delta_hours) % 24.0, 2)
            sunset_hour = round((12.0 + delta_hours) % 24.0, 2)

            is_day = sza_deg < 90.0
            if is_day:
                day_night_status = "Day"
            elif 90.0 <= sza_deg <= 96.0:
                day_night_status = "Twilight"
            else:
                day_night_status = "Night"

        # 6. Solar Irradiance Separation:
        # F_normal_TOA = S_Mars = S_0 / r^2 (physical normal incidence at TOA)
        # F_horizontal_TOA = S_Mars * max(0, cos(SZA))
        # Surface direct beam normal = S_Mars * exp(-tau * airmass)
        # Surface direct horizontal = S_Mars * max(0, cos(SZA)) * exp(-tau * airmass)
        toa_normal_irradiance = s0_mars

        if sza_deg < 90.0:
            toa_horizontal_irradiance = s0_mars * cos_sza
            if tau is not None and tau >= 0.0:
                airmass = 1.0 / max(cos_sza, 0.05)  # clamp airmass to avoid horizon singularity
                extinction = math.exp(-tau * airmass)
                surface_direct_normal = s0_mars * extinction
                surface_direct_horizontal = toa_horizontal_irradiance * extinction
            else:
                surface_direct_normal = s0_mars
                surface_direct_horizontal = toa_horizontal_irradiance
        else:
            # Strict Rule: When SZA >= 90 deg, all direct horizontal and surface fluxes are strictly 0.0
            toa_horizontal_irradiance = 0.0
            surface_direct_normal = 0.0
            surface_direct_horizontal = 0.0

        return MarsSolarGeometry(
            lat=round(lat, 4),
            lon=round(norm_lon, 4),
            solar_longitude_ls_deg=round(ls_norm, 2),
            local_true_solar_time_hours=round(actual_ltst, 2),
            local_mean_solar_time_hours=round(lmst_val, 2),
            equation_of_time_hours=round(eot_hours, 4),
            equation_of_time_minutes=round(eot_hours * 60.0, 2),
            season_name=season_name,
            mars_sun_distance_au=round(r_au, 5),
            solar_declination_deg=round(declination_deg, 2),
            hour_angle_deg=round(hour_angle_deg, 2),
            solar_zenith_angle_deg=round(sza_deg, 2),
            solar_elevation_deg=round(solar_elevation_deg, 2),
            day_night_status=day_night_status,
            is_day=is_day,
            sunrise_hour=sunrise_hour,
            sunset_hour=sunset_hour,
            polar_condition=polar_condition,
            toa_normal_irradiance_w_m2=round(toa_normal_irradiance, 2),
            toa_horizontal_irradiance_w_m2=round(toa_horizontal_irradiance, 2),
            surface_direct_normal_irradiance_w_m2=round(surface_direct_normal, 2) if surface_direct_normal is not None else None,
            surface_direct_horizontal_irradiance_w_m2=round(surface_direct_horizontal, 2),
            top_of_atmosphere_solar_flux_w_m2=round(toa_horizontal_irradiance, 2),
            optical_depth_tau=round(tau, 3) if tau is not None else None,
            surface_solar_flux_w_m2=round(surface_direct_horizontal, 2),
        )

    # ── 3. Historical In-Situ Rover Observation Parsers ─────────────────────
    def get_historical_meda_sol1(self) -> HistoricalWeatherSummary:
        """Load and summarize Mars 2020 Perseverance MEDA Sol 1 in-situ observations."""
        if self._meda_cache is not None:
            return self._meda_cache

        ps_path = MEDA_DIR / "WE__0001___________DER_PS__________________P02.CSV"
        rhs_path = MEDA_DIR / "WE__0001___________DER_RHS_________________P03.CSV"
        tirs_path = MEDA_DIR / "WE__0001___________DER_TIRS________________P04.CSV"

        if not ps_path.exists():
            raise FileNotFoundError(f"MEDA Sol 1 Pressure file not found at {ps_path}")

        pressures: List[float] = []
        samples: List[HistoricalRoverWeatherRecord] = []

        import csv
        with open(ps_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                p_str = row.get("PRESSURE", "").strip()
                if p_str:
                    try:
                        p_val = float(p_str)
                        if p_val > 0.0:
                            pressures.append(p_val)
                            if len(samples) < 5:
                                samples.append(
                                    HistoricalRoverWeatherRecord(
                                        station="MEDA",
                                        timestamp_or_sclk=row.get("SCLK", ""),
                                        lmst=row.get("LMST", ""),
                                        ltst=row.get("LTST", ""),
                                        pressure_pa=round(p_val, 2),
                                        sensor_flags={"transducer": row.get("TRANSDUCER")},
                                    )
                                )
                    except ValueError:
                        continue

        # Optional RH and TIRS parsing
        rhs_temps: List[float] = []
        if rhs_path.exists():
            with open(rhs_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t_str = row.get("HUMIDITY_LOCAL_TEMP", "").strip()
                    if t_str:
                        try:
                            t_val = float(t_str)
                            if 100.0 < t_val < 350.0:
                                rhs_temps.append(t_val)
                        except ValueError:
                            pass

        tirs_down: List[float] = []
        tirs_up: List[float] = []
        if tirs_path.exists():
            with open(tirs_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    d_str = row.get("DOWNWARD_LW_IRRADIANCE", "").strip()
                    u_str = row.get("UPWARD_LW_IRRADIANCE", "").strip()
                    if d_str:
                        try:
                            d_val = float(d_str)
                            if d_val >= 0.0:
                                tirs_down.append(d_val)
                        except ValueError:
                            pass
                    if u_str:
                        try:
                            u_val = float(u_str)
                            if u_val >= 0.0:
                                tirs_up.append(u_val)
                        except ValueError:
                            pass

        pressure_summary = {
            "min_pa": round(min(pressures), 2) if pressures else 0.0,
            "max_pa": round(max(pressures), 2) if pressures else 0.0,
            "mean_pa": round(sum(pressures) / len(pressures), 2) if pressures else 0.0,
            "count": len(pressures),
        }

        ambient_summary = None
        if rhs_temps:
            ambient_summary = {
                "min_k": round(min(rhs_temps), 2),
                "max_k": round(max(rhs_temps), 2),
                "mean_k": round(sum(rhs_temps) / len(rhs_temps), 2),
                "count": len(rhs_temps),
            }

        irradiance_summary = None
        if tirs_down and tirs_up:
            irradiance_summary = {
                "downward_lw_mean_w_m2": round(sum(tirs_down) / len(tirs_down), 2),
                "upward_lw_mean_w_m2": round(sum(tirs_up) / len(tirs_up), 2),
            }

        summary = HistoricalWeatherSummary(
            station_id="MEDA_JEZERO",
            instrument_name="Mars Environmental Dynamics Analyzer (MEDA)",
            mission="Mars 2020 Perseverance",
            site_name="Jezero Crater (Octavia E. Butler Landing)",
            coordinates=(18.4447, 77.4508),
            elevation_m=-2560.0,
            sol=1,
            solar_longitude_range_deg=(6.15, 6.17),
            total_samples=len(pressures),
            pressure_summary_pa=pressure_summary,
            ambient_temp_summary_k=ambient_summary,
            ground_temp_summary_k=None,
            relative_humidity_summary_pct=None,
            irradiance_summary_w_m2=irradiance_summary,
            pds4_source_lid="urn:nasa:pds:mars2020_meda:data_derived_env:we__0001___________der_ps__________________p",
            sample_records=samples,
        )
        self._meda_cache = summary
        return summary

    def get_historical_rems_sol1(self) -> HistoricalWeatherSummary:
        """Load and summarize MSL Curiosity REMS Sol 1 in-situ observations."""
        if self._rems_cache is not None:
            return self._rems_cache

        rmd_path = REMS_DIR / "RME_397535244RMD00010000000_______PA.TAB"
        if not rmd_path.exists():
            raise FileNotFoundError(f"REMS Sol 1 RMD file not found at {rmd_path}")

        pressures: List[float] = []
        ambient_temps: List[float] = []
        ground_temps: List[float] = []
        samples: List[HistoricalRoverWeatherRecord] = []

        with open(rmd_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = [p.strip().replace('"', "") for p in line.split(",")]
                if len(parts) >= 39:
                    # Column 38 is PRESSURE (0-indexed: parts[37])
                    # Column 16 is AMBIENT_TEMP (0-indexed: parts[15])
                    # Column 8 is BRIGHTNESS_TEMP (0-indexed: parts[7])
                    try:
                        p_val = float(parts[37])
                        if 0 < p_val < 2000 and p_val != -999.0:
                            pressures.append(p_val)
                    except ValueError:
                        p_val = None

                    try:
                        t_val = float(parts[15])
                        if 100 < t_val < 350 and t_val != -999.0:
                            ambient_temps.append(t_val)
                    except ValueError:
                        t_val = None

                    try:
                        gt_val = float(parts[7])
                        if 100 < gt_val < 350 and gt_val != -999.0:
                            ground_temps.append(gt_val)
                    except ValueError:
                        gt_val = None

                    if p_val and len(samples) < 5:
                        samples.append(
                            HistoricalRoverWeatherRecord(
                                station="REMS",
                                timestamp_or_sclk=parts[0],
                                lmst=parts[1],
                                ltst=parts[2],
                                pressure_pa=round(p_val, 2),
                                ambient_temperature_k=round(t_val, 2) if t_val else None,
                                ground_temperature_k=round(gt_val, 2) if gt_val else None,
                            )
                        )

        summary = HistoricalWeatherSummary(
            station_id="REMS_GALE",
            instrument_name="Rover Environmental Monitoring Station (REMS)",
            mission="Mars Science Laboratory Curiosity",
            site_name="Gale Crater (Bradbury Landing)",
            coordinates=(-4.591, 137.441),
            elevation_m=-4440.0,
            sol=1,
            solar_longitude_range_deg=(150.3, 150.6),
            total_samples=len(pressures),
            pressure_summary_pa={
                "min_pa": round(min(pressures), 2) if pressures else 0.0,
                "max_pa": round(max(pressures), 2) if pressures else 0.0,
                "mean_pa": round(sum(pressures) / len(pressures), 2) if pressures else 0.0,
                "count": len(pressures),
            },
            ambient_temp_summary_k={
                "min_k": round(min(ambient_temps), 2) if ambient_temps else 0.0,
                "max_k": round(max(ambient_temps), 2) if ambient_temps else 0.0,
                "mean_k": round(sum(ambient_temps) / len(ambient_temps), 2) if ambient_temps else 0.0,
                "count": len(ambient_temps),
            },
            ground_temp_summary_k={
                "min_k": round(min(ground_temps), 2) if ground_temps else 0.0,
                "max_k": round(max(ground_temps), 2) if ground_temps else 0.0,
                "mean_k": round(sum(ground_temps) / len(ground_temps), 2) if ground_temps else 0.0,
                "count": len(ground_temps),
            },
            pds4_source_lid="urn:nasa:pds:msl_rems:data_calibrated:rme_397535244rmd00010000000_______pa",
            sample_records=samples,
        )
        self._rems_cache = summary
        return summary

    # ── 4. Model-to-Observation Residual Benchmarking ──────────────────────
    def compute_pressure_residuals(self) -> Dict[str, PressureResidualBenchmark]:
        """Compute the signed residual between the analytical barometric model and in-situ ground truth.

        Residual = P_model(z) - P_observed_mean
        """
        meda = self.get_historical_meda_sol1()
        rems = self.get_historical_rems_sol1()

        # Jezero Crater benchmark
        z_jezero = meda.elevation_m
        p_model_jezero = self.estimate_atmospheric_pressure(z_jezero).reference_atmospheric_pressure_estimate_pa
        p_obs_jezero = meda.pressure_summary_pa["mean_pa"] if meda.pressure_summary_pa else 715.00
        res_jezero = round(p_model_jezero - p_obs_jezero, 2)
        res_pct_jezero = round((res_jezero / p_obs_jezero) * 100.0, 2)

        # Gale Crater benchmark
        z_gale = rems.elevation_m
        p_model_gale = self.estimate_atmospheric_pressure(z_gale).reference_atmospheric_pressure_estimate_pa
        p_obs_gale = rems.pressure_summary_pa["mean_pa"] if rems.pressure_summary_pa else 704.41
        res_gale = round(p_model_gale - p_obs_gale, 2)
        res_pct_gale = round((res_gale / p_obs_gale) * 100.0, 2)

        benchmarks = {
            "MEDA_JEZERO": PressureResidualBenchmark(
                station_id="MEDA_JEZERO",
                station_name="Perseverance MEDA (Jezero Crater)",
                mission="Mars 2020",
                landing_site="Jezero Crater floor (Octavia E. Butler Landing)",
                coordinates=meda.coordinates,
                elevation_m=z_jezero,
                model_pressure_pa=p_model_jezero,
                observed_mean_pressure_pa=p_obs_jezero,
                residual_pa=res_jezero,
                residual_percent=res_pct_jezero,
                observation_sol=1,
                instrument_lid=meda.pds4_source_lid,
                notes=(
                    f"Model overestimates observed Sol 1 mean by {res_jezero:+.2f} Pa ({res_pct_jezero:+.2f}%). "
                    "MEDA Sol 1 dataset covers an afternoon interval (15:28–16:20 LTST, 2,330 1-Hz samples) at Ls=6.15 deg. "
                    "The analytical model represents a simplified global isothermal reference profile (P_ref=610 Pa, H=11,100 m), "
                    "which does not capture seasonal polar CO2 condensation cycles or diurnal tidal variations. "
                    "MARS-X preserves this residual explicitly without artificial calibration."
                ),
            ),
            "REMS_GALE": PressureResidualBenchmark(
                station_id="REMS_GALE",
                station_name="Curiosity REMS (Gale Crater)",
                mission="Mars Science Laboratory",
                landing_site="Gale Crater floor (Bradbury Landing)",
                coordinates=rems.coordinates,
                elevation_m=z_gale,
                model_pressure_pa=p_model_gale,
                observed_mean_pressure_pa=p_obs_gale,
                residual_pa=res_gale,
                residual_percent=res_pct_gale,
                observation_sol=1,
                instrument_lid=rems.pds4_source_lid,
                notes=(
                    f"Model overestimates observed Sol 1 mean by {res_gale:+.2f} Pa ({res_pct_gale:+.2f}%). "
                    "REMS Sol 1 dataset covers an afternoon interval (13:47–14:05 LTST, 450 valid samples) at Ls=150.4 deg. "
                    "The analytical model represents a simplified global isothermal reference profile (P_ref=610 Pa, H=11,100 m), "
                    "which does not capture localized basin topography effects or diurnal barometric tides. "
                    "MARS-X preserves this residual explicitly without artificial calibration."
                ),
            ),
        }

        return benchmarks

    # ── 5. Environmental Route Context Enrichment ───────────────────────────
    def enrich_route_environmental_context(
        self,
        route_points: List[Dict[str, Any]],
        ls_deg: float = 0.0,
        ltst_hours: float = 12.0,
        tau: Optional[float] = None,
        max_samples: int = 50,
    ) -> RouteEnvironmentalSummary:
        """Enrich a sequence of route waypoints with reference atmospheric pressure and solar geometry.

        Accepts route points with 'lat', 'lon', 'elevation_m', and 'distance_m'.
        """
        if not route_points:
            raise ValueError("Cannot enrich empty route points list.")

        total_pts = len(route_points)
        step = max(1, total_pts // max_samples)
        sampled_indices = list(range(0, total_pts, step))
        if sampled_indices[-1] != total_pts - 1:
            sampled_indices.append(total_pts - 1)

        enriched_points: List[RoutePointEnvironment] = []
        pressures: List[float] = []
        surface_fluxes: List[float] = []
        daylight_count = 0

        for idx in sampled_indices:
            pt = route_points[idx]
            lat = float(pt.get("lat", 0.0))
            lon = float(pt.get("lon", 0.0))
            elev = float(pt.get("elevation_m", 0.0))
            dist = float(pt.get("distance_m", 0.0))

            # 1. Pressure estimate
            p_est = self.estimate_atmospheric_pressure(elev)
            p_val = p_est.reference_atmospheric_pressure_estimate_pa
            pressures.append(p_val)

            # 2. Solar geometry
            sol_geo = self.calculate_solar_geometry(
                lat=lat,
                lon=lon,
                ls_deg=ls_deg,
                ltst_hours=ltst_hours,
                tau=tau,
            )

            if sol_geo.is_day:
                daylight_count += 1

            surface_fluxes.append(sol_geo.surface_direct_horizontal_irradiance_w_m2)

            enriched_points.append(
                RoutePointEnvironment(
                    point_index=idx,
                    lat=round(lat, 5),
                    lon=round(lon, 5),
                    distance_m=round(dist, 1),
                    elevation_m=round(elev, 2),
                    reference_pressure_pa=p_val,
                    solar_zenith_angle_deg=sol_geo.solar_zenith_angle_deg,
                    solar_elevation_deg=sol_geo.solar_elevation_deg,
                    is_day=sol_geo.is_day,
                    toa_normal_irradiance_w_m2=sol_geo.toa_normal_irradiance_w_m2,
                    toa_horizontal_irradiance_w_m2=sol_geo.toa_horizontal_irradiance_w_m2,
                    surface_direct_horizontal_irradiance_w_m2=sol_geo.surface_direct_horizontal_irradiance_w_m2,
                    toa_solar_flux_w_m2=sol_geo.toa_horizontal_irradiance_w_m2,
                    surface_solar_flux_w_m2=sol_geo.surface_direct_horizontal_irradiance_w_m2,
                )
            )

        daylight_pct = round((daylight_count / len(sampled_indices)) * 100.0, 1)

        return RouteEnvironmentalSummary(
            solar_longitude_ls_deg=round(ls_deg, 2),
            local_true_solar_time_hours=round(ltst_hours, 2),
            optical_depth_tau=round(tau, 3) if tau is not None else None,
            min_pressure_pa=round(min(pressures), 2),
            max_pressure_pa=round(max(pressures), 2),
            mean_pressure_pa=round(sum(pressures) / len(pressures), 2),
            min_surface_flux_w_m2=round(min(surface_fluxes), 2),
            max_surface_flux_w_m2=round(max(surface_fluxes), 2),
            mean_surface_flux_w_m2=round(sum(surface_fluxes) / len(surface_fluxes), 2),
            daylight_percentage=daylight_pct,
            samples=enriched_points,
        )

    # ── 6. Metadata ────────────────────────────────────────────────────────
    def get_metadata(self) -> EnvironmentalMetadataResponse:
        """Return static metadata describing models, datum, and scientific limitations."""
        return EnvironmentalMetadataResponse()


# Singleton service instance
_environmental_service: Optional[EnvironmentalIntelligenceService] = None


def get_environmental_service() -> EnvironmentalIntelligenceService:
    """Obtain or initialize the singleton EnvironmentalIntelligenceService."""
    global _environmental_service
    if _environmental_service is None:
        _environmental_service = EnvironmentalIntelligenceService()
    return _environmental_service
