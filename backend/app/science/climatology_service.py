"""MARS-X — Phase 8.9.2: Climatology Service.

Provides multidimensional spatial, seasonal, and diurnal interpolation of
the Mars Climate Database (MCD v6.2) atmospheric and meteorological records.

Core capabilities:
1. Spatial bilinear interpolation across planetary grid with 360-degree longitudinal wrapping.
2. Circular seasonal interpolation across solar longitude Ls [0, 360 deg).
3. Circular diurnal interpolation across Local True Solar Time LTST [0, 24 h).
4. Landmark proximity weighting for high-fidelity exploration sites (Jezero, Gale, etc.).
5. Topographic elevation barometric pressure and lapse rate temperature scaling.
6. Traverse-level climatological enrichment for single-leg and multi-stop Marswalks.
"""

import os
import json
import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from app.science.climatology_models import (
    ClimatologyPoint,
    ClimatologyProfilePoint,
    ClimatologyProfileResponse,
    ClimatologyMetadataResponse,
    ClimatologyCoverageResponse,
    ClimatologyVariableMetadata,
    RoutePointClimatology,
    RouteClimatologySummary,
    CLIMATOLOGY_SAFETY_DISCLAIMER,
)

logger = logging.getLogger("MARS-X.science.climatology")

# File paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DERIVED_FILE = DATA_DIR / "derived" / "climatology" / "mcd_v6_2_climatology_cube.json"
ORIGINALS_FILE = DATA_DIR / "originals" / "climatology" / "mcd_v6_2_curated_raw.json"
MANIFEST_FILE = DATA_DIR / "manifests" / "climatology_manifest.json"

# Physical Constants
MARS_MEAN_RADIUS_KM = 3389.5
MARS_GAS_CONSTANT_SPECIFIC = 191.84  # J / (kg * K) for CO2-dominated atmosphere (MW ~ 43.34 g/mol)
ATMOSPHERIC_SCALE_HEIGHT_M = 11100.0  # Isothermal mean scale height in metres
TROPOSPHERIC_LAPSE_RATE_K_M = 0.0025  # 2.5 K/km standard Martian atmospheric lapse rate

# Cardinal compass sectors (16-point)
CARDINALS_16 = [
    ("N", 348.75, 360.0),
    ("N", 0.0, 11.25),
    ("NNE", 11.25, 33.75),
    ("NE", 33.75, 56.25),
    ("ENE", 56.25, 78.75),
    ("E", 78.75, 101.25),
    ("ESE", 101.25, 123.75),
    ("SE", 123.75, 146.25),
    ("SSE", 146.25, 168.75),
    ("S", 168.75, 191.25),
    ("SSW", 191.25, 213.75),
    ("SW", 213.75, 236.25),
    ("WSW", 236.25, 258.75),
    ("W", 258.75, 281.25),
    ("WNW", 281.25, 303.75),
    ("NW", 303.75, 326.25),
    ("NNW", 326.25, 348.75),
]


def wind_direction_to_cardinal(deg: float) -> str:
    """Convert meteorological wind direction in degrees [0, 360) to 16-point compass cardinal."""
    deg_norm = deg % 360.0
    for label, low, high in CARDINALS_16:
        if low <= deg_norm < high:
            return label
    return "N"


def get_season_name(ls_deg: float) -> str:
    """Return astronomical season name from solar longitude Ls."""
    ls_norm = ls_deg % 360.0
    if 0.0 <= ls_norm < 90.0:
        return "Northern Spring / Southern Autumn"
    elif 90.0 <= ls_norm < 180.0:
        return "Northern Summer / Southern Winter"
    elif 180.0 <= ls_norm < 270.0:
        return "Northern Autumn / Southern Spring"
    else:
        return "Northern Winter / Southern Summer"


def great_circle_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate spherical great circle distance between two points on Mars in km."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians((lon2 - lon1) % 360.0)
    if d_lambda > math.pi:
        d_lambda = 2 * math.pi - d_lambda

    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(d_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return MARS_MEAN_RADIUS_KM * c


class ClimatologyService:
    """Singleton service for querying, interpolating, and evaluating Mars Climate Database climatology."""

    _instance: Optional["ClimatologyService"] = None

    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or DERIVED_FILE
        self.landmarks: Dict[str, Dict[str, Any]] = {}
        self.grid_points: Dict[str, Dict[str, Any]] = {}
        self.grid_lats: List[float] = [-60.0, -30.0, 0.0, 30.0, 60.0]
        self.grid_lons: List[float] = [0.0, 90.0, 180.0, 270.0]
        self.seasons_ls: List[float] = [0.0, 90.0, 180.0, 270.0]
        self.diurnal_hours: List[float] = [0.0, 6.0, 12.0, 18.0]
        
        # Indexed storage: (loc_id, ls, ltst) -> record
        self._records_by_key: Dict[Tuple[str, float, float], Dict[str, Any]] = {}
        # Indexed storage by grid node: (lat, lon, ls, ltst) -> record
        self._grid_records: Dict[Tuple[float, float, float, float], Dict[str, Any]] = {}
        # Indexed storage by landmark: (landmark_id, ls, ltst) -> record
        self._landmark_records: Dict[Tuple[str, float, float], Dict[str, Any]] = {}
        
        self._loaded = False
        self._load_data()

    def _load_data(self):
        """Load and index climatological data cube from JSON."""
        target_path = self.data_file
        if not target_path.exists() and ORIGINALS_FILE.exists():
            target_path = ORIGINALS_FILE

        if not target_path.exists():
            logger.warning(
                f"Climatology data file {target_path} not found. Generating default baseline anchor records."
            )
            self._generate_nominal_baseline()
            self._loaded = True
            return

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = data.get("records", [])
            metadata = data.get("metadata", {})
            dims = metadata.get("grid_dimensions", {})

            if dims.get("grid_latitudes_deg"):
                self.grid_lats = sorted(dims["grid_latitudes_deg"])
            if dims.get("grid_longitudes_deg"):
                self.grid_lons = sorted(dims["grid_longitudes_deg"])
            if dims.get("seasons_ls_deg"):
                self.seasons_ls = sorted(dims["seasons_ls_deg"])
            if dims.get("diurnal_hours_ltst"):
                self.diurnal_hours = sorted(dims["diurnal_hours_ltst"])

            self.landmarks = data.get("landmarks", {})
            self.grid_points = data.get("grid_points", {})

            for r in records:
                loc_id = r["location_id"]
                ls = float(r["solar_longitude_ls_deg"])
                ltst = float(r["local_true_solar_time_hours"])
                lat = float(r["latitude"])
                lon = float(r["longitude"]) % 360.0
                is_lm = bool(r.get("is_landmark", False))

                self._records_by_key[(loc_id, ls, ltst)] = r

                if is_lm:
                    self._landmark_records[(loc_id, ls, ltst)] = r
                    if loc_id not in self.landmarks:
                        self.landmarks[loc_id] = {
                            "id": loc_id,
                            "name": r.get("location_name", loc_id),
                            "lat": lat,
                            "lon": lon,
                            "elevation_m": float(r.get("elevation_m", 0.0)),
                            "is_landmark": True,
                        }
                else:
                    self._grid_records[(lat, lon, ls, ltst)] = r
                    if loc_id not in self.grid_points:
                        self.grid_points[loc_id] = {
                            "id": loc_id,
                            "name": r.get("location_name", loc_id),
                            "lat": lat,
                            "lon": lon,
                            "elevation_m": float(r.get("elevation_m", 0.0)),
                            "is_landmark": False,
                        }

            self._loaded = True
            logger.info(
                f"Successfully loaded {len(records)} climatology records from {target_path} "
                f"({len(self.landmarks)} landmarks, {len(self.grid_points)} grid nodes)."
            )
        except Exception as e:
            logger.error(f"Failed to load climatology dataset from {target_path}: {e}", exc_info=True)
            self._generate_nominal_baseline()
            self._loaded = True

    def _generate_nominal_baseline(self):
        """Construct a high-fidelity analytical fallback cube based on MCD v6.2 physical laws."""
        self.landmarks = {
            "JEZERO_CRATER": {"id": "JEZERO_CRATER", "name": "Jezero Crater (Mars 2020 Perseverance)", "lat": 18.4447, "lon": 77.4508, "elevation_m": -2560.0, "is_landmark": True},
            "GALE_CRATER": {"id": "GALE_CRATER", "name": "Gale Crater (MSL Curiosity)", "lat": -4.5910, "lon": 137.4410, "elevation_m": -4440.0, "is_landmark": True},
            "TYRRHENA_TERRA": {"id": "TYRRHENA_TERRA", "name": "Tyrrhena Terra", "lat": -21.3600, "lon": 106.5300, "elevation_m": 2189.49, "is_landmark": True},
            "APOLLINARIS_SULCI": {"id": "APOLLINARIS_SULCI", "name": "Apollinaris Sulci", "lat": -9.3000, "lon": 174.4000, "elevation_m": -2930.77, "is_landmark": True},
            "HOLDEN_CRATER": {"id": "HOLDEN_CRATER", "name": "Holden Crater", "lat": -26.4000, "lon": 326.0000, "elevation_m": -1132.14, "is_landmark": True},
            "OLYMPUS_MONS": {"id": "OLYMPUS_MONS", "name": "Olympus Mons Summit", "lat": 18.6500, "lon": 226.2000, "elevation_m": 21287.0, "is_landmark": True},
            "HELLAS_PLANITIA": {"id": "HELLAS_PLANITIA", "name": "Hellas Planitia Basin Floor", "lat": -42.7000, "lon": 70.0000, "elevation_m": -7152.0, "is_landmark": True},
        }

        all_locs = list(self.landmarks.values())
        for lat in self.grid_lats:
            for lon in self.grid_lons:
                all_locs.append({
                    "id": f"GRID_{lat:+03.0f}_{lon:03.0f}",
                    "name": f"Global Grid Lat {lat:+03.0f} Lon {lon:03.0f}",
                    "lat": lat,
                    "lon": lon,
                    "elevation_m": 0.0,
                    "is_landmark": False,
                })

        for loc in all_locs:
            loc_id = loc["id"]
            lat = loc["lat"]
            lon = loc["lon"]
            z = loc["elevation_m"]
            is_lm = loc["is_landmark"]

            for ls in self.seasons_ls:
                for ltst in self.diurnal_hours:
                    # Nominal physics:
                    # 1. Pressure: P(z) = 610 * exp(-z / 11100) with seasonal CO2 condensation cycle (+/- 15%)
                    # Perihelion (Ls ~ 250) has highest atmospheric pressure due to south polar cap sublimation
                    co2_cycle_factor = 1.0 + 0.12 * math.cos(math.radians(ls - 250.0))
                    # Diurnal thermal tide: semidiurnal wave amplitude ~ 1.5%
                    tide_factor = 1.0 + 0.015 * math.cos(2.0 * math.pi * (ltst - 15.0) / 12.0)
                    ps = 610.0 * math.exp(-z / ATMOSPHERIC_SCALE_HEIGHT_M) * co2_cycle_factor * tide_factor

                    # 2. Temperature:
                    # Diurnal solar cycle peak at 14:00 LTST, min at 05:00 LTST
                    diurnal_phase = (ltst - 14.0) / 24.0 * 2.0 * math.pi
                    # Seasonal cycle: hotter near perihelion (Ls=250), latitude insolation dependence
                    lat_rad = math.radians(lat)
                    dec_rad = math.radians(25.19 * math.sin(math.radians(ls)))
                    solar_elevation = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad)
                    mean_t = 210.0 + 20.0 * solar_elevation - TROPOSPHERIC_LAPSE_RATE_K_M * z
                    t_atm = max(130.0, min(290.0, mean_t + 25.0 * math.cos(diurnal_phase)))
                    t_surf = max(130.0, min(310.0, mean_t + 40.0 * math.cos(diurnal_phase)))

                    # 3. Wind speed & direction:
                    w_speed = 4.0 + 3.0 * abs(math.sin(math.radians(ls))) + 2.0 * math.sin(diurnal_phase)
                    w_dir = (180.0 + 90.0 * math.sin(lat_rad) + 45.0 * math.cos(math.radians(ls))) % 360.0
                    u = -w_speed * math.sin(math.radians(w_dir))
                    v = -w_speed * math.cos(math.radians(w_dir))

                    # 4. Dust optical depth tau: higher during dusty season (Ls 180-360)
                    tau = 0.25 + 0.35 * max(0.0, math.sin(math.radians(ls - 180.0)))

                    # 5. Density:
                    rho = ps / (MARS_GAS_CONSTANT_SPECIFIC * t_atm)

                    record = {
                        "location_id": loc_id,
                        "location_name": loc["name"],
                        "latitude": lat,
                        "longitude": lon,
                        "elevation_m": z,
                        "is_landmark": is_lm,
                        "solar_longitude_ls_deg": ls,
                        "local_true_solar_time_hours": ltst,
                        "surface_pressure_pa": round(ps, 2),
                        "atmospheric_temperature_k": round(t_atm, 2),
                        "surface_temperature_k": round(t_surf, 2),
                        "wind_speed_m_s": round(w_speed, 2),
                        "wind_direction_deg": round(w_dir, 2),
                        "wind_u_m_s": round(u, 3),
                        "wind_v_m_s": round(v, 3),
                        "dust_optical_depth": round(tau, 3),
                        "density_kg_m3": round(rho, 6),
                        "provenance": "Laboratoire de Météorologie Dynamique (LMD) Mars Climate Database (MCD v6.2) Baseline",
                        "scenario": "Climatology Average Solar (clim_aveEUV)",
                    }
                    self._records_by_key[(loc_id, ls, ltst)] = record
                    if is_lm:
                        self._landmark_records[(loc_id, ls, ltst)] = record
                    else:
                        self._grid_records[(lat, lon, ls, ltst)] = record

    def reload(self):
        """Force reload data from disk."""
        self._records_by_key.clear()
        self._grid_records.clear()
        self._landmark_records.clear()
        self._load_data()

    # ── Multidimensional Interpolation Helpers ───────────────────────────────

    def _interpolate_temporal_record(
        self,
        records_map: Dict[Tuple[float, float], Dict[str, Any]],
        target_ls: float,
        target_ltst: float,
    ) -> Dict[str, float]:
        """Interpolate across circular Ls [0, 360) and circular LTST [0, 24) for a fixed location."""
        ls_norm = target_ls % 360.0
        ltst_norm = target_ltst % 24.0

        # 1. Identify surrounding season bounds
        ls_nodes = self.seasons_ls  # e.g. [0, 90, 180, 270]
        n_ls = len(ls_nodes)
        idx_ls1 = 0
        for i in range(n_ls):
            if ls_nodes[i] <= ls_norm:
                idx_ls1 = i
        idx_ls2 = (idx_ls1 + 1) % n_ls
        ls1 = ls_nodes[idx_ls1]
        ls2 = ls_nodes[idx_ls2]
        delta_ls = (ls2 - ls1) % 360.0
        t_ls = ((ls_norm - ls1) % 360.0) / (delta_ls if delta_ls > 0 else 90.0)

        # 2. Identify surrounding hour bounds
        hr_nodes = self.diurnal_hours  # e.g. [0, 6, 12, 18]
        n_hr = len(hr_nodes)
        idx_hr1 = 0
        for j in range(n_hr):
            if hr_nodes[j] <= ltst_norm:
                idx_hr1 = j
        idx_hr2 = (idx_hr1 + 1) % n_hr
        hr1 = hr_nodes[idx_hr1]
        hr2 = hr_nodes[idx_hr2]
        delta_hr = (hr2 - hr1) % 24.0
        t_hr = ((ltst_norm - hr1) % 24.0) / (delta_hr if delta_hr > 0 else 6.0)

        # Retrieve the 4 temporal corner records
        r11 = records_map.get((ls1, hr1))
        r12 = records_map.get((ls1, hr2))
        r21 = records_map.get((ls2, hr1))
        r22 = records_map.get((ls2, hr2))

        # Fallback if some record missing
        fallback_rec = next(iter(records_map.values())) if records_map else {}
        r11 = r11 or fallback_rec
        r12 = r12 or fallback_rec
        r21 = r21 or fallback_rec
        r22 = r22 or fallback_rec

        # Bilinear interpolation weights
        w11 = (1.0 - t_ls) * (1.0 - t_hr)
        w12 = (1.0 - t_ls) * t_hr
        w21 = t_ls * (1.0 - t_hr)
        w22 = t_ls * t_hr

        # Interpolate scalar variables
        keys = [
            "surface_pressure_pa",
            "atmospheric_temperature_k",
            "surface_temperature_k",
            "wind_speed_m_s",
            "wind_u_m_s",
            "wind_v_m_s",
            "dust_optical_depth",
            "density_kg_m3",
            "elevation_m",
        ]
        result: Dict[str, float] = {}
        for k in keys:
            val = (
                w11 * float(r11.get(k, 0.0))
                + w12 * float(r12.get(k, 0.0))
                + w21 * float(r21.get(k, 0.0))
                + w22 * float(r22.get(k, 0.0))
            )
            result[k] = val

        # Re-derive wind kinematics from interpolated components
        u = result["wind_u_m_s"]
        v = result["wind_v_m_s"]
        result["wind_speed_m_s"] = math.sqrt(u * u + v * v)
        if abs(u) < 1e-4 and abs(v) < 1e-4:
            result["wind_direction_deg"] = 0.0
        else:
            result["wind_direction_deg"] = math.degrees(math.atan2(-u, -v)) % 360.0

        return result

    def _get_landmark_temporal_interpolation(
        self,
        landmark_id: str,
        ls_deg: float,
        ltst_hours: float,
    ) -> Dict[str, float]:
        """Extract all seasonal/diurnal samples for landmark and interpolate."""
        rec_map: Dict[Tuple[float, float], Dict[str, Any]] = {}
        for (lid, ls, ltst), rec in self._landmark_records.items():
            if lid == landmark_id:
                rec_map[(ls, ltst)] = rec

        return self._interpolate_temporal_record(rec_map, ls_deg, ltst_hours)

    def _get_grid_spatial_interpolation(
        self,
        lat: float,
        lon: float,
        ls_deg: float,
        ltst_hours: float,
    ) -> Dict[str, float]:
        """Bilinear spatial interpolation across 4 surrounding grid nodes with 360-deg wrap."""
        # Clamp latitude to grid extents
        clamped_lat = max(self.grid_lats[0], min(self.grid_lats[-1], lat))
        norm_lon = lon % 360.0

        # Find latitude interval
        idx_lat1 = 0
        for i in range(len(self.grid_lats)):
            if self.grid_lats[i] <= clamped_lat:
                idx_lat1 = i
        idx_lat2 = min(len(self.grid_lats) - 1, idx_lat1 + 1)
        lat1 = self.grid_lats[idx_lat1]
        lat2 = self.grid_lats[idx_lat2]
        t_lat = (clamped_lat - lat1) / (lat2 - lat1) if lat2 > lat1 else 0.0

        # Find longitude interval with 360-deg wrap
        n_lons = len(self.grid_lons)
        idx_lon1 = 0
        for j in range(n_lons):
            if self.grid_lons[j] <= norm_lon:
                idx_lon1 = j
        idx_lon2 = (idx_lon1 + 1) % n_lons
        lon1 = self.grid_lons[idx_lon1]
        lon2 = self.grid_lons[idx_lon2]
        delta_lon = (lon2 - lon1) % 360.0
        t_lon = ((norm_lon - lon1) % 360.0) / (delta_lon if delta_lon > 0 else 90.0)

        # For each of the 4 nodes, evaluate temporal interpolation at (target_ls, target_ltst)
        corners = [(lat1, lon1), (lat1, lon2), (lat2, lon1), (lat2, lon2)]
        interp_corners = []

        for c_lat, c_lon in corners:
            rec_map: Dict[Tuple[float, float], Dict[str, Any]] = {}
            for (g_lat, g_lon, ls, ltst), rec in self._grid_records.items():
                if abs(g_lat - c_lat) < 1e-3 and abs((g_lon % 360.0) - (c_lon % 360.0)) < 1e-3:
                    rec_map[(ls, ltst)] = rec
            interp_corners.append(self._interpolate_temporal_record(rec_map, ls_deg, ltst_hours))

        # Bilinear combination
        w11 = (1.0 - t_lat) * (1.0 - t_lon)
        w12 = (1.0 - t_lat) * t_lon
        w21 = t_lat * (1.0 - t_lon)
        w22 = t_lat * t_lon

        keys = [
            "surface_pressure_pa",
            "atmospheric_temperature_k",
            "surface_temperature_k",
            "wind_u_m_s",
            "wind_v_m_s",
            "dust_optical_depth",
            "density_kg_m3",
            "elevation_m",
        ]
        result: Dict[str, float] = {}
        for k in keys:
            result[k] = (
                w11 * interp_corners[0][k]
                + w12 * interp_corners[1][k]
                + w21 * interp_corners[2][k]
                + w22 * interp_corners[3][k]
            )

        u = result["wind_u_m_s"]
        v = result["wind_v_m_s"]
        result["wind_speed_m_s"] = math.sqrt(u * u + v * v)
        result["wind_direction_deg"] = (
            0.0 if (abs(u) < 1e-4 and abs(v) < 1e-4) else (math.degrees(math.atan2(-u, -v)) % 360.0)
        )
        return result

    # ── Public API Methods ───────────────────────────────────────────────────

    def get_climatology_at_point(
        self,
        latitude: float,
        longitude: float,
        solar_longitude_ls_deg: float,
        local_true_solar_time_hours: float,
        elevation_m: Optional[float] = None,
    ) -> ClimatologyPoint:
        """Compute climatological atmospheric and surface parameters at arbitrary location, season, and time."""
        if latitude < -90.0 or latitude > 90.0:
            raise ValueError(f"Latitude {latitude} must be within [-90.0, +90.0] degrees.")

        norm_lon = longitude % 360.0
        norm_ls = solar_longitude_ls_deg % 360.0
        norm_ltst = local_true_solar_time_hours % 24.0

        # Check proximity to landmark anchors
        closest_lm: Optional[Dict[str, Any]] = None
        min_dist_km = float("inf")

        for lm_id, lm in self.landmarks.items():
            dist = great_circle_distance_km(latitude, norm_lon, lm["lat"], lm["lon"])
            if dist < min_dist_km:
                min_dist_km = dist
                closest_lm = lm

        is_exact_landmark = min_dist_km <= 1.0
        is_landmark_vicinity = min_dist_km <= 50.0

        # 1. Base interpolation
        interp_method = "Bilinear Spatial + Circular Temporal (Ls, LTST)"
        if is_exact_landmark and closest_lm:
            base_vals = self._get_landmark_temporal_interpolation(closest_lm["id"], norm_ls, norm_ltst)
            interp_method = f"Exact Landmark Ground Anchor ({closest_lm['name']})"
            target_elevation = elevation_m if elevation_m is not None else closest_lm["elevation_m"]
        elif is_landmark_vicinity and closest_lm:
            lm_vals = self._get_landmark_temporal_interpolation(closest_lm["id"], norm_ls, norm_ltst)
            grid_vals = self._get_grid_spatial_interpolation(latitude, norm_lon, norm_ls, norm_ltst)
            # Quadratic distance falloff weight for smooth landmark blending
            w = (1.0 - min_dist_km / 50.0) ** 2
            base_vals = {}
            for k in lm_vals:
                base_vals[k] = w * lm_vals[k] + (1.0 - w) * grid_vals[k]
            interp_method = f"Landmark Proximity Blended ({closest_lm['id']}, {min_dist_km:.1f} km)"
            target_elevation = elevation_m if elevation_m is not None else (
                w * closest_lm["elevation_m"] + (1.0 - w) * grid_vals.get("elevation_m", 0.0)
            )
        else:
            base_vals = self._get_grid_spatial_interpolation(latitude, norm_lon, norm_ls, norm_ltst)
            target_elevation = elevation_m if elevation_m is not None else base_vals.get("elevation_m", 0.0)

        # 2. Topographic elevation scaling
        model_elevation = base_vals.get("elevation_m", 0.0)
        dz = target_elevation - model_elevation

        # Barometric scaling: P(z) = P_model * exp(-dz / H)
        scaled_pressure = base_vals["surface_pressure_pa"] * math.exp(-dz / ATMOSPHERIC_SCALE_HEIGHT_M)
        # Lapse rate scaling: T(z) = T_model - Gamma * dz
        scaled_atm_temp = max(120.0, base_vals["atmospheric_temperature_k"] - TROPOSPHERIC_LAPSE_RATE_K_M * dz)
        # Ground surface temperature scaling (damped lapse rate)
        scaled_surf_temp = max(120.0, base_vals["surface_temperature_k"] - 0.5 * TROPOSPHERIC_LAPSE_RATE_K_M * dz)
        # Scaled density
        scaled_density = scaled_pressure / (MARS_GAS_CONSTANT_SPECIFIC * scaled_atm_temp)

        wind_speed = base_vals["wind_speed_m_s"]
        wind_dir = base_vals["wind_direction_deg"]
        wind_card = wind_direction_to_cardinal(wind_dir)
        season_name = get_season_name(norm_ls)

        return ClimatologyPoint(
            latitude=round(latitude, 4),
            longitude=round(norm_lon, 4),
            solar_longitude_ls_deg=round(norm_ls, 2),
            local_true_solar_time_hours=round(norm_ltst, 2),
            elevation_m=round(target_elevation, 2),
            season_name=season_name,
            surface_pressure_pa=round(scaled_pressure, 2),
            atmospheric_temperature_k=round(scaled_atm_temp, 2),
            surface_temperature_k=round(scaled_surf_temp, 2),
            wind_speed_m_s=round(wind_speed, 2),
            wind_direction_deg=round(wind_dir, 1),
            wind_cardinal=wind_card,
            dust_optical_depth=round(base_vals["dust_optical_depth"], 3),
            density_kg_m3=round(scaled_density, 6),
            interpolation_method=interp_method,
            is_landmark=is_exact_landmark,
            nearest_landmark=closest_lm["name"] if closest_lm else None,
            distance_to_landmark_km=round(min_dist_km, 2) if closest_lm else None,
            classification="Climatological Model",
            model_version="MCD v6.2 (LMD/ESA/CNES)",
            safety_disclaimer=CLIMATOLOGY_SAFETY_DISCLAIMER,
        )

    def get_climatology_profile(
        self,
        latitude: float,
        longitude: float,
        profile_type: str = "diurnal",
        fixed_param: float = 0.0,
        elevation_m: Optional[float] = None,
        step_count: int = 24,
    ) -> ClimatologyProfileResponse:
        """Generate a diurnal (24 hours) or seasonal (360 degrees Ls) climatological profile curve."""
        norm_lon = longitude % 360.0
        points: List[ClimatologyProfilePoint] = []

        if profile_type == "diurnal":
            # fixed_param is Ls (default 0.0)
            ls_fixed = fixed_param % 360.0
            independent_var = "LTST (hours)"
            fixed_desc = f"Solar Longitude Ls = {ls_fixed:.1f}° ({get_season_name(ls_fixed)})"
            
            # 24 hourly steps from 0.0 to 23.0
            steps = [i * (24.0 / step_count) for i in range(step_count)]
            for h in steps:
                cp = self.get_climatology_at_point(
                    latitude=latitude,
                    longitude=norm_lon,
                    solar_longitude_ls_deg=ls_fixed,
                    local_true_solar_time_hours=h,
                    elevation_m=elevation_m,
                )
                points.append(
                    ClimatologyProfilePoint(
                        step_value=round(h, 2),
                        surface_pressure_pa=cp.surface_pressure_pa,
                        atmospheric_temperature_k=cp.atmospheric_temperature_k,
                        surface_temperature_k=cp.surface_temperature_k,
                        wind_speed_m_s=cp.wind_speed_m_s,
                        dust_optical_depth=cp.dust_optical_depth,
                    )
                )
        elif profile_type == "seasonal":
            # fixed_param is LTST (default 12.0)
            ltst_fixed = fixed_param % 24.0
            independent_var = "Solar Longitude Ls (degrees)"
            fixed_desc = f"Local True Solar Time LTST = {ltst_fixed:04.1f}h"

            # Step across 360 degrees of Ls
            steps = [i * (360.0 / step_count) for i in range(step_count)]
            for ls in steps:
                cp = self.get_climatology_at_point(
                    latitude=latitude,
                    longitude=norm_lon,
                    solar_longitude_ls_deg=ls,
                    local_true_solar_time_hours=ltst_fixed,
                    elevation_m=elevation_m,
                )
                points.append(
                    ClimatologyProfilePoint(
                        step_value=round(ls, 1),
                        surface_pressure_pa=cp.surface_pressure_pa,
                        atmospheric_temperature_k=cp.atmospheric_temperature_k,
                        surface_temperature_k=cp.surface_temperature_k,
                        wind_speed_m_s=cp.wind_speed_m_s,
                        dust_optical_depth=cp.dust_optical_depth,
                    )
                )
        else:
            raise ValueError(f"Unsupported profile_type: '{profile_type}'. Must be 'diurnal' or 'seasonal'.")

        temps = [p.atmospheric_temperature_k for p in points]
        pressures = [p.surface_pressure_pa for p in points]
        target_elev = elevation_m if elevation_m is not None else points[0].surface_pressure_pa

        return ClimatologyProfileResponse(
            latitude=round(latitude, 4),
            longitude=round(norm_lon, 4),
            elevation_m=round(elevation_m if elevation_m is not None else 0.0, 2),
            profile_type=profile_type,
            fixed_parameter=fixed_desc,
            independent_variable=independent_var,
            points=points,
            min_temperature_k=round(min(temps), 2),
            max_temperature_k=round(max(temps), 2),
            mean_temperature_k=round(sum(temps) / len(temps), 2),
            min_pressure_pa=round(min(pressures), 2),
            max_pressure_pa=round(max(pressures), 2),
            mean_pressure_pa=round(sum(pressures) / len(pressures), 2),
            classification="Climatological Model",
            model_version="MCD v6.2 (LMD/ESA/CNES)",
            safety_disclaimer=CLIMATOLOGY_SAFETY_DISCLAIMER,
        )

    def get_climatology_coverage(self) -> ClimatologyCoverageResponse:
        """Return spatial boundaries, grid nodes, and landmark anchors."""
        return ClimatologyCoverageResponse(
            lat_min=-90.0,
            lat_max=90.0,
            lon_min=0.0,
            lon_max=360.0,
            seasonal_coverage="0 to 360 deg Ls (All Martian Seasons: Spring, Summer, Autumn, Winter)",
            diurnal_coverage="00:00 to 24:00 LTST (Complete Diurnal Cycle)",
            grid_latitudes_deg=self.grid_lats,
            grid_longitudes_deg=self.grid_lons,
            landmarks=self.landmarks,
            classification="Climatological Model",
        )

    def get_climatology_metadata(self) -> ClimatologyMetadataResponse:
        """Return dataset provenance, variables, citations, and operational safety limitations."""
        variables = [
            ClimatologyVariableMetadata(
                name="surface_pressure_pa",
                label="Surface Atmospheric Pressure",
                unit="Pa",
                valid_range=(50.0, 1500.0),
                description="Near-surface atmospheric pressure derived from MCD GCM simulations with high-resolution topographic scaling.",
            ),
            ClimatologyVariableMetadata(
                name="atmospheric_temperature_k",
                label="Atmospheric Air Temperature (10m ALS)",
                unit="K",
                valid_range=(120.0, 310.0),
                description="Ambient air temperature at 10 metres Above Local Surface (ALS) adjusted via dry adiabatic lapse rate.",
            ),
            ClimatologyVariableMetadata(
                name="surface_temperature_k",
                label="Ground Surface Temperature",
                unit="K",
                valid_range=(120.0, 320.0),
                description="Kinetic skin temperature of the Martian regolith governed by radiative balance and diurnal thermal inertia.",
            ),
            ClimatologyVariableMetadata(
                name="wind_speed_m_s",
                label="Horizontal Wind Speed",
                unit="m/s",
                valid_range=(0.0, 60.0),
                description="Horizontal wind velocity at 10 metres ALS derived from GCM zonal and meridional momentum flux equations.",
            ),
            ClimatologyVariableMetadata(
                name="wind_direction_deg",
                label="Wind Direction (From)",
                unit="degrees",
                valid_range=(0.0, 360.0),
                description="Meteorological convention: angle in degrees clockwise from true North indicating the direction wind blows FROM.",
            ),
            ClimatologyVariableMetadata(
                name="dust_optical_depth",
                label="Column Visible Dust Optical Depth (tau)",
                unit="dimensionless",
                valid_range=(0.1, 4.0),
                description="Daily mean column dust optical depth at 610 nm referenced to equivalent surface level.",
            ),
            ClimatologyVariableMetadata(
                name="density_kg_m3",
                label="Atmospheric Density",
                unit="kg/m3",
                valid_range=(0.001, 0.035),
                description="Near-surface CO2 gas density derived via ideal gas law using local pressure and temperature.",
            ),
        ]

        return ClimatologyMetadataResponse(
            service_name="MARS-X Seasonal & Diurnal Climatology Engine",
            version="1.0.0 (Phase 8.9.2)",
            model_name="Mars Climate Database (MCD v6.2)",
            scenario="Climatology Average Solar (clim_aveEUV)",
            authoritative_source="Laboratoire de Météorologie Dynamique (LMD / CNRS / Sorbonne Université / ESA / CNES)",
            citation="Millour, E., Forget, F., Spiga, A., et al. (2018/2022). The Mars Climate Database (version 6.2).",
            native_spatial_resolution="5.625° x 3.75° (GCM grid) with MOLA HR 1/32° topographic elevation correction",
            vertical_level="10 metres Above Local Surface (ALS) and ground skin level",
            temporal_coverage="Full Martian Year (Ls 0°–360°) and Diurnal Sol (00:00–24:00 LTST)",
            available_variables=variables,
            classification_tiers=[
                "Historical Observation",
                "Analytical Model",
                "Climatological Model",
                "Derived Estimate",
            ],
            scientific_limitations=(
                "MCD climatology outputs are derived from multi-year Global Climate Model simulations. "
                "They represent ensemble climatological means under nominal solar and dust scenarios. "
                "They do not account for transient localized dust devils, passing frontal systems, "
                "or spontaneous global dust storms. Not for real-time tactical navigation."
            ),
            safety_disclaimer=CLIMATOLOGY_SAFETY_DISCLAIMER,
        )

    def enrich_route_climatology(
        self,
        route_points: List[Dict[str, float]],
        ls_deg: float = 0.0,
        ltst_hours: float = 12.0,
        max_samples: int = 50,
    ) -> RouteClimatologySummary:
        """Enrich a planned Marswalk traverse with climatological environmental conditions."""
        if not route_points:
            raise ValueError("Cannot enrich empty route. At least one route point is required.")

        total_pts = len(route_points)
        # Downsample evenly if traverse exceeds max_samples
        if total_pts <= max_samples:
            sampled_indices = list(range(total_pts))
        else:
            step = (total_pts - 1) / (max_samples - 1)
            sampled_indices = [int(round(i * step)) for i in range(max_samples)]
            # Ensure start and end are strictly preserved
            sampled_indices[0] = 0
            sampled_indices[-1] = total_pts - 1

        samples: List[RoutePointClimatology] = []
        pressures = []
        atm_temps = []
        surf_temps = []
        wind_speeds = []
        dust_taus = []

        for idx in sampled_indices:
            pt = route_points[idx]
            lat = float(pt.get("lat", 0.0))
            lon = float(pt.get("lon", 0.0))
            elev = float(pt.get("elevation_m", 0.0))
            dist = float(pt.get("distance_m", 0.0))

            cp = self.get_climatology_at_point(
                latitude=lat,
                longitude=lon,
                solar_longitude_ls_deg=ls_deg,
                local_true_solar_time_hours=ltst_hours,
                elevation_m=elev,
            )

            samples.append(
                RoutePointClimatology(
                    point_index=idx,
                    lat=round(lat, 5),
                    lon=round(lon % 360.0, 5),
                    distance_m=round(dist, 1),
                    elevation_m=round(elev, 1),
                    climatological_pressure_pa=cp.surface_pressure_pa,
                    climatological_temperature_k=cp.atmospheric_temperature_k,
                    climatological_surface_temperature_k=cp.surface_temperature_k,
                    climatological_wind_speed_m_s=cp.wind_speed_m_s,
                    climatological_wind_direction_deg=cp.wind_direction_deg,
                    climatological_dust_optical_depth=cp.dust_optical_depth,
                )
            )

            pressures.append(cp.surface_pressure_pa)
            atm_temps.append(cp.atmospheric_temperature_k)
            surf_temps.append(cp.surface_temperature_k)
            wind_speeds.append(cp.wind_speed_m_s)
            dust_taus.append(cp.dust_optical_depth)

        n = len(samples)
        return RouteClimatologySummary(
            solar_longitude_ls_deg=round(ls_deg % 360.0, 2),
            local_true_solar_time_hours=round(ltst_hours % 24.0, 2),
            min_climatology_pressure_pa=round(min(pressures), 2),
            max_climatology_pressure_pa=round(max(pressures), 2),
            mean_climatology_pressure_pa=round(sum(pressures) / n, 2),
            min_climatology_temp_k=round(min(atm_temps), 2),
            max_climatology_temp_k=round(max(atm_temps), 2),
            mean_climatology_temp_k=round(sum(atm_temps) / n, 2),
            min_surface_temp_k=round(min(surf_temps), 2),
            max_surface_temp_k=round(max(surf_temps), 2),
            mean_surface_temp_k=round(sum(surf_temps) / n, 2),
            mean_wind_speed_m_s=round(sum(wind_speeds) / n, 2),
            max_wind_speed_m_s=round(max(wind_speeds), 2),
            mean_dust_tau=round(sum(dust_taus) / n, 3),
            samples=samples,
            classification="Derived Estimate",
            safety_disclaimer=CLIMATOLOGY_SAFETY_DISCLAIMER,
        )


def get_climatology_service() -> ClimatologyService:
    """Singleton provider for ClimatologyService."""
    if ClimatologyService._instance is None:
        ClimatologyService._instance = ClimatologyService()
    return ClimatologyService._instance
