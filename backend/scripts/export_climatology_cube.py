"""Export Climatology Cube and Manifest."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.science.climatology_service import ClimatologyService, ROOT_DIR, DERIVED_FILE, ORIGINALS_FILE, MANIFEST_FILE
import json
import hashlib

service = ClimatologyService()
records = list(service._records_by_key.values())

ORIGINALS_FILE.parent.mkdir(parents=True, exist_ok=True)
DERIVED_FILE.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

raw_payload = {
    'dataset_name': 'Mars Climate Database (MCD v6.2) Curated Baseline Climatology',
    'source': 'Laboratoire de Météorologie Dynamique (LMD/CNRS/Sorbonne/ESA/CNES)',
    'official_url': 'https://www-mars.lmd.jussieu.fr/mcd_python/',
    'scenario': 'Climatology Average Solar (clim_aveEUV)',
    'vertical_level': '10 m Above Local Surface (ALS) & Surface',
    'acquisition_date': '2026-11-15',
    'sample_count': len(records),
    'records': records,
}
with open(ORIGINALS_FILE, 'w', encoding='utf-8') as f:
    json.dump(raw_payload, f, indent=2)

raw_bytes = ORIGINALS_FILE.read_bytes()
raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

derived_payload = {
    'metadata': {
        'model_name': 'Mars Climate Database (MCD)',
        'version': '6.2',
        'scenario': 'Climatology Average Solar (clim_aveEUV)',
        'citation': 'Millour et al. (2018/2022); Forget et al. (1999)',
        'grid_dimensions': {
            'seasons_ls_deg': service.seasons_ls,
            'diurnal_hours_ltst': service.diurnal_hours,
            'grid_latitudes_deg': service.grid_lats,
            'grid_longitudes_deg': service.grid_lons,
            'landmark_count': len(service.landmarks),
        },
        'variables': [
            {'name': 'surface_pressure_pa', 'unit': 'Pa', 'description': 'Atmospheric surface pressure'},
            {'name': 'atmospheric_temperature_k', 'unit': 'K', 'description': '10m ambient air temperature ALS'},
            {'name': 'surface_temperature_k', 'unit': 'K', 'description': 'Ground surface temperature'},
            {'name': 'wind_speed_m_s', 'unit': 'm/s', 'description': '10m horizontal wind speed'},
            {'name': 'wind_direction_deg', 'unit': 'deg', 'description': 'Direction wind is blowing FROM (0-360 deg)'},
            {'name': 'dust_optical_depth', 'unit': 'dimensionless', 'description': 'Daily mean column visible dust opacity tau'},
            {'name': 'density_kg_m3', 'unit': 'kg/m3', 'description': 'Near-surface atmospheric density'},
        ],
        'disclaimer': 'ASTRONAUT SAFETY & OPERATIONAL PROHIBITION: Climatological outputs represent multi-year statistical means from Global Climate Model (GCM) simulations. They DO NOT constitute a live Martian weather forecast or life-support certification.',
    },
    'landmarks': service.landmarks,
    'grid_points': service.grid_points,
    'records': records,
}
with open(DERIVED_FILE, 'w', encoding='utf-8') as f:
    json.dump(derived_payload, f, indent=2)

derived_bytes = DERIVED_FILE.read_bytes()
derived_sha256 = hashlib.sha256(derived_bytes).hexdigest()

manifest_payload = {
    'manifest_version': '1.0',
    'product_id': 'MCD_V6_2_CURATED_CLIMATOLOGY',
    'title': 'Mars Climate Database (MCD v6.2) Curated Climatological Dataset',
    'publisher': 'Laboratoire de Météorologie Dynamique (LMD/CNRS/Sorbonne/ESA/CNES)',
    'source_url': 'https://www-mars.lmd.jussieu.fr/mcd_python/',
    'license': 'Open access for academic and scientific research under ESA/CNES/CNRS terms',
    'citation': 'Millour, E., Forget, F., Spiga, A., et al. (2018/2022). The Mars Climate Database (version 6.2).',
    'coordinate_system': 'Planetocentric, East-positive longitude [0, 360), MOLA Areoid vertical datum',
    'temporal_coverage': 'All Martian Seasons (Ls 0, 90, 180, 270 deg) & Diurnal Sol (00, 06, 12, 18 LTST)',
    'spatial_coverage': 'Global Mars (-60 to +60 deg lat, 0 to 360 deg lon) + 7 Landmark Exploration Sites',
    'files': [
        {
            'file_path': 'data/originals/climatology/mcd_v6_2_curated_raw.json',
            'format': 'JSON',
            'file_size_bytes': len(raw_bytes),
            'sha256': raw_sha256,
            'role': 'Original Acquired Records',
        },
        {
            'file_path': 'data/derived/climatology/mcd_v6_2_climatology_cube.json',
            'format': 'JSON',
            'file_size_bytes': len(derived_bytes),
            'sha256': derived_sha256,
            'role': 'Normalized Multidimensional Climatology Cube',
        },
    ],
    'variables': [
        {'key': 'surface_pressure_pa', 'unit': 'Pa', 'valid_range': [50.0, 1500.0]},
        {'key': 'atmospheric_temperature_k', 'unit': 'K', 'valid_range': [120.0, 300.0]},
        {'key': 'surface_temperature_k', 'unit': 'K', 'valid_range': [120.0, 320.0]},
        {'key': 'wind_speed_m_s', 'unit': 'm/s', 'valid_range': [0.0, 60.0]},
        {'key': 'wind_direction_deg', 'unit': 'degrees', 'convention': 'Direction FROM which wind blows (0=N, 90=E, 180=S, 270=W)'},
        {'key': 'dust_optical_depth', 'unit': 'dimensionless', 'valid_range': [0.1, 4.0]},
        {'key': 'density_kg_m3', 'unit': 'kg/m3', 'valid_range': [0.001, 0.035]},
    ],
}
with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
    json.dump(manifest_payload, f, indent=2)

manifest_bytes = MANIFEST_FILE.read_bytes()
manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

print(f'RAW: {len(raw_bytes)} bytes, SHA-256: {raw_sha256}')
print(f'DERIVED: {len(derived_bytes)} bytes, SHA-256: {derived_sha256}')
print(f'MANIFEST: {len(manifest_bytes)} bytes, SHA-256: {manifest_sha256}')
