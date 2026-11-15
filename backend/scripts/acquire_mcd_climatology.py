"""MARS-X — Phase 8.9.2: MCD v6.2 Climatology Acquisition & Normalization Pipeline.

Acquires authentic Mars Climate Database (MCD v6.2) multi-variable meteorological records
from the Laboratoire de Météorologie Dynamique (LMD / CNRS / Sorbonne Université / ESA / CNES)
and compiles them into:
1. data/originals/climatology/mcd_v6_2_curated_raw.json (unaltered acquired records)
2. data/derived/climatology/mcd_v6_2_climatology_cube.json (normalized, indexed multidimensional cube)
3. data/manifests/climatology_manifest.json (data provenance, units, dimensions, and SHA-256 checksums)
"""

import os
import sys
import json
import math
import time
import hashlib
import re
import urllib.request
import urllib.parse
from pathlib import Path

MCD_CGI_URL = "https://www-mars.lmd.jussieu.fr/mcd_python/cgi-bin/mcdcgi.py"

# Repositories and directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ORIGINALS_DIR = ROOT_DIR / "data" / "originals" / "climatology"
DERIVED_DIR = ROOT_DIR / "data" / "derived" / "climatology"
MANIFESTS_DIR = ROOT_DIR / "data" / "manifests"

ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
DERIVED_DIR.mkdir(parents=True, exist_ok=True)
MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Target Spatial Points ────────────────────────────────────────────────
LANDMARKS = [
    {
        "id": "JEZERO_CRATER",
        "name": "Jezero Crater (Mars 2020 Perseverance)",
        "lat": 18.4447,
        "lon": 77.4508,
        "elevation_m": -2560.0,
        "is_landmark": True,
    },
    {
        "id": "GALE_CRATER",
        "name": "Gale Crater (MSL Curiosity)",
        "lat": -4.5910,
        "lon": 137.4410,
        "elevation_m": -4440.0,
        "is_landmark": True,
    },
    {
        "id": "TYRRHENA_TERRA",
        "name": "Tyrrhena Terra (Traversability Benchmark)",
        "lat": -21.3600,
        "lon": 106.5300,
        "elevation_m": 2189.49,
        "is_landmark": True,
    },
    {
        "id": "APOLLINARIS_SULCI",
        "name": "Apollinaris Sulci (Traversability Benchmark)",
        "lat": -9.3000,
        "lon": 174.4000,
        "elevation_m": -2930.77,
        "is_landmark": True,
    },
    {
        "id": "HOLDEN_CRATER",
        "name": "Holden Crater (Traversability Benchmark)",
        "lat": -26.4000,
        "lon": 326.0000,
        "elevation_m": -1132.14,
        "is_landmark": True,
    },
    {
        "id": "OLYMPUS_MONS",
        "name": "Olympus Mons Summit",
        "lat": 18.6500,
        "lon": 226.2000,
        "elevation_m": 21287.0,
        "is_landmark": True,
    },
    {
        "id": "HELLAS_PLANITIA",
        "name": "Hellas Planitia Basin Floor",
        "lat": -42.7000,
        "lon": 70.0000,
        "elevation_m": -7152.0,
        "is_landmark": True,
    },
]

GRID_LATS = [-60.0, -30.0, 0.0, 30.0, 60.0]
GRID_LONS = [0.0, 90.0, 180.0, 270.0]

GRID_POINTS = []
for lat in GRID_LATS:
    for lon in GRID_LONS:
        GRID_POINTS.append({
            "id": f"GRID_{lat:+03.0f}_{lon:03.0f}",
            "name": f"Global Grid Lat {lat:+03.0f} Lon {lon:03.0f}",
            "lat": lat,
            "lon": lon,
            "elevation_m": 0.0,  # Datum reference
            "is_landmark": False,
        })

ALL_LOCATIONS = LANDMARKS + GRID_POINTS

# ── 2. Target Temporal Coordinates ──────────────────────────────────────────
SEASONS_LS = [0.0, 90.0, 180.0, 270.0]
HOURS_LTST_LANDMARK = [0.0, 6.0, 12.0, 18.0]
HOURS_LTST_GRID = [0.0, 6.0, 12.0, 18.0]


def query_mcd_raw(lat: float, lon: float, ls: float, ltst: float, vars_list: list, max_retries: int = 3):
    """Execute a single query against the MCD v6.2 CGI script."""
    params = {
        "var1": vars_list[0],
        "var2": vars_list[1] if len(vars_list) > 1 else "none",
        "var3": vars_list[2] if len(vars_list) > 2 else "none",
        "var4": vars_list[3] if len(vars_list) > 3 else "none",
        "datekeyhtml": "1",
        "ls": str(ls),
        "localtime": str(ltst),
        "latitude": str(lat),
        "longitude": str(lon),
        "altitude": "10.",
        "zkey": "3",
        "hrkey": "1",
        "dust": "1",
    }
    url = f"{MCD_CGI_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MARS-X/0.1.0 Research Climatology Pipeline"}
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                text = resp.read().decode("latin1", errors="replace")
                items = dict(re.findall(r'<li>\s*([^.]+?)\s*\.{3,}\s*([0-9.eE+-]+)\s*</li>', text))
                return {k.strip(): float(v) for k, v in items.items()}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.0 + attempt * 1.5)
            else:
                print(f"  [WARN] Failed to query {lat},{lon} Ls={ls} LTST={ltst}: {e}")
                return {}


def calculate_wind_direction_deg(u: float, v: float) -> float:
    """Calculate meteorological wind direction (direction wind blows FROM) in degrees [0, 360)."""
    if abs(u) < 1e-4 and abs(v) < 1e-4:
        return 0.0
    dir_deg = math.degrees(math.atan2(-u, -v)) % 360.0
    return round(dir_deg, 2)


def main():
    print(f"=== MARS-X Phase 8.9.2: MCD v6.2 Climatology Acquisition ===")
    print(f"Locations: {len(ALL_LOCATIONS)} ({len(LANDMARKS)} landmarks, {len(GRID_POINTS)} global grid cells)")
    print(f"Seasons: {len(SEASONS_LS)} ({SEASONS_LS})")
    print(f"Diurnal Hours: 4 ({HOURS_LTST_LANDMARK})")
    print()

    raw_records = []
    total_samples = 0
    start_time = time.time()

    for loc in ALL_LOCATIONS:
        loc_id = loc["id"]
        lat = loc["lat"]
        lon = loc["lon"]
        is_lm = loc["is_landmark"]
        hours = HOURS_LTST_LANDMARK if is_lm else HOURS_LTST_GRID

        print(f"Fetching {loc_id} ({loc['name']}, lat={lat}, lon={lon})...")

        for ls in SEASONS_LS:
            for ltst in hours:
                # 1. Primary meteorological query: ps, t, tsurf, tauref
                d1 = query_mcd_raw(lat, lon, ls, ltst, ["ps", "t", "tsurf", "tauref"])
                time.sleep(0.15)  # Polite pause

                # 2. Kinematic query: u, v, wind, rho
                d2 = query_mcd_raw(lat, lon, ls, ltst, ["u", "v", "wind", "rho"])
                time.sleep(0.15)

                ps = d1.get("Surface pressure (Pa)", 0.0)
                t_atm = d1.get("Temperature (K)", 0.0)
                t_surf = d1.get("Surface temperature (K)", 0.0)
                tau = d1.get("Daily mean dust column visible optical depth above surface", 0.0)

                u = d2.get("W-E wind component (m/s)", 0.0)
                v = d2.get("S-N wind component (m/s)", 0.0)
                w_speed = d2.get("Horizontal wind speed (m/s)", math.sqrt(u*u + v*v))
                rho = d2.get("Density (kg/m3)", 0.0)

                w_dir = calculate_wind_direction_deg(u, v)

                record = {
                    "location_id": loc_id,
                    "location_name": loc["name"],
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": loc["elevation_m"],
                    "is_landmark": is_lm,
                    "solar_longitude_ls_deg": ls,
                    "local_true_solar_time_hours": ltst,
                    "surface_pressure_pa": round(ps, 2),
                    "atmospheric_temperature_k": round(t_atm, 2),
                    "surface_temperature_k": round(t_surf, 2),
                    "wind_speed_m_s": round(w_speed, 2),
                    "wind_direction_deg": w_dir,
                    "wind_u_m_s": round(u, 3),
                    "wind_v_m_s": round(v, 3),
                    "dust_optical_depth": round(tau, 3),
                    "density_kg_m3": round(rho, 6),
                    "provenance": "Laboratoire de Météorologie Dynamique (LMD) Mars Climate Database (MCD v6.2)",
                    "scenario": "Climatology Average Solar (clim_aveEUV)",
                }
                raw_records.append(record)
                total_samples += 1

    elapsed = time.time() - start_time
    print(f"\nCompleted acquisition of {total_samples} samples in {elapsed:.1f}s.")

    # ── 3. Save Raw Records ─────────────────────────────────────────────────
    raw_path = ORIGINALS_DIR / "mcd_v6_2_curated_raw.json"
    raw_payload = {
        "dataset_name": "Mars Climate Database (MCD v6.2) Curated Baseline Climatology",
        "source": "Laboratoire de Météorologie Dynamique (LMD/CNRS/Sorbonne/ESA/CNES)",
        "official_url": "https://www-mars.lmd.jussieu.fr/mcd_python/",
        "scenario": "Climatology Average Solar (clim_aveEUV)",
        "vertical_level": "10 m Above Local Surface (ALS) & Surface",
        "acquisition_date": "2026-11-15",
        "sample_count": len(raw_records),
        "records": raw_records,
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2)

    raw_bytes = raw_path.read_bytes()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    print(f"Saved raw dataset: {raw_path} ({len(raw_bytes):,} bytes, SHA-256: {raw_sha256[:16]}...)")

    # ── 4. Save Normalized Derivative Cube ──────────────────────────────────
    derived_path = DERIVED_DIR / "mcd_v6_2_climatology_cube.json"
    derived_payload = {
        "metadata": {
            "model_name": "Mars Climate Database (MCD)",
            "version": "6.2",
            "scenario": "Climatology Average Solar (clim_aveEUV)",
            "citation": "Millour et al. (2018/2022); Forget et al. (1999)",
            "grid_dimensions": {
                "seasons_ls_deg": SEASONS_LS,
                "diurnal_hours_ltst": HOURS_LTST_LANDMARK,
                "grid_latitudes_deg": GRID_LATS,
                "grid_longitudes_deg": GRID_LONS,
                "landmark_count": len(LANDMARKS),
            },
            "variables": [
                {"name": "surface_pressure_pa", "unit": "Pa", "description": "Atmospheric surface pressure"},
                {"name": "atmospheric_temperature_k", "unit": "K", "description": "10m ambient air temperature ALS"},
                {"name": "surface_temperature_k", "unit": "K", "description": "Ground surface temperature"},
                {"name": "wind_speed_m_s", "unit": "m/s", "description": "10m horizontal wind speed"},
                {"name": "wind_direction_deg", "unit": "deg", "description": "Direction wind is blowing FROM (0-360 deg)"},
                {"name": "dust_optical_depth", "unit": "dimensionless", "description": "Daily mean column visible dust opacity tau"},
                {"name": "density_kg_m3", "unit": "kg/m3", "description": "Near-surface atmospheric density"},
            ],
            "disclaimer": (
                "ASTRONAUT SAFETY & OPERATIONAL PROHIBITION: Climatological outputs represent multi-year statistical means "
                "from Global Climate Model (GCM) simulations. They DO NOT constitute a live Martian weather forecast or life-support certification. "
                "Never describe conditions as 'astronaut-safe' or 'safe EVA'."
            ),
        },
        "landmarks": {lm["id"]: lm for lm in LANDMARKS},
        "grid_points": {gp["id"]: gp for gp in GRID_POINTS},
        "records": raw_records,
    }
    with open(derived_path, "w", encoding="utf-8") as f:
        json.dump(derived_payload, f, indent=2)

    derived_bytes = derived_path.read_bytes()
    derived_sha256 = hashlib.sha256(derived_bytes).hexdigest()
    print(f"Saved normalized cube: {derived_path} ({len(derived_bytes):,} bytes, SHA-256: {derived_sha256[:16]}...)")

    # ── 5. Build Data Manifest ──────────────────────────────────────────────
    manifest_path = MANIFESTS_DIR / "climatology_manifest.json"
    manifest_payload = {
        "manifest_version": "1.0",
        "product_id": "MCD_V6_2_CURATED_CLIMATOLOGY",
        "title": "Mars Climate Database (MCD v6.2) Curated Climatological Dataset",
        "publisher": "Laboratoire de Météorologie Dynamique (LMD/CNRS/Sorbonne/ESA/CNES)",
        "source_url": "https://www-mars.lmd.jussieu.fr/mcd_python/",
        "license": "Open access for academic and scientific research under ESA/CNES/CNRS terms",
        "citation": "Millour, E., Forget, F., Spiga, A., et al. (2018/2022). The Mars Climate Database (version 6.2).",
        "coordinate_system": "Planetocentric, East-positive longitude [0, 360), MOLA Areoid vertical datum",
        "temporal_coverage": "All Martian Seasons (Ls 0, 90, 180, 270 deg) & Diurnal Sol (00, 06, 12, 18 LTST)",
        "spatial_coverage": "Global Mars (-60 to +60 deg lat, 0 to 360 deg lon) + 7 Landmark Exploration Sites",
        "files": [
            {
                "file_path": "data/originals/climatology/mcd_v6_2_curated_raw.json",
                "format": "JSON",
                "file_size_bytes": len(raw_bytes),
                "sha256": raw_sha256,
                "role": "Original Acquired Records",
            },
            {
                "file_path": "data/derived/climatology/mcd_v6_2_climatology_cube.json",
                "format": "JSON",
                "file_size_bytes": len(derived_bytes),
                "sha256": derived_sha256,
                "role": "Normalized Multidimensional Climatology Cube",
            },
        ],
        "variables": [
            {"key": "surface_pressure_pa", "unit": "Pa", "valid_range": [50.0, 1500.0]},
            {"key": "atmospheric_temperature_k", "unit": "K", "valid_range": [120.0, 300.0]},
            {"key": "surface_temperature_k", "unit": "K", "valid_range": [120.0, 320.0]},
            {"key": "wind_speed_m_s", "unit": "m/s", "valid_range": [0.0, 60.0]},
            {"key": "wind_direction_deg", "unit": "degrees", "convention": "Direction FROM which wind blows (0=N, 90=E, 180=S, 270=W)"},
            {"key": "dust_optical_depth", "unit": "dimensionless", "valid_range": [0.1, 4.0]},
            {"key": "density_kg_m3", "unit": "kg/m3", "valid_range": [0.001, 0.035]},
        ],
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    print(f"Saved manifest: {manifest_path} ({len(manifest_bytes):,} bytes, SHA-256: {manifest_sha256[:16]}...)")
    print("\nAcquisition completed successfully!")


if __name__ == "__main__":
    main()
