"""Georeferencing and topographic feature validation for Phase 3 MOLA products."""

import os
import sys
import json
import numpy as np
import rasterio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.terrain.pds_parser import PDS3LabelParser, read_pds3_image_binary
from app.terrain.raster_inspector import inspect_raster_file
from app.terrain.elevation_service import TerrainDataEngine
from app.terrain.models import ElevationPointQuery

# Known Martian Topographic Reference Features (from IAU / USGS Gazetteer of Planetary Nomenclature)
# Feature name: (lat_deg, lon_east_deg, expected_elev_range_m, feature_type)
KNOWN_MARS_LANDMARKS = {
    "Olympus Mons Caldera": {
        "lat": 18.65,
        "lon": 226.2,
        "expected_min": 18000.0,
        "expected_max": 22000.0,
        "type": "Shield Volcano Summit Peak",
        "description": "Highest volcanic summit in the solar system"
    },
    "Hellas Planitia Floor": {
        "lat": -42.4,
        "lon": 70.5,
        "expected_min": -8200.0,
        "expected_max": -5500.0,
        "type": "Giant Impact Basin Interior",
        "description": "Deepest extensive depression on Mars"
    },
    "Alba Mons Summit": {
        "lat": 40.5,
        "lon": 250.1,
        "expected_min": 4000.0,
        "expected_max": 7500.0,
        "type": "Low-profile Volcanic Construct",
        "description": "Vast volcanic shield with gentle flanks"
    },
    "Argyre Planitia Floor": {
        "lat": -49.7,
        "lon": 316.0,
        "expected_min": -4000.0,
        "expected_max": -1500.0,
        "type": "Impact Basin Floor",
        "description": "Major southern hemisphere impact basin"
    },
    "Valles Marineris (Coprates Chasma)": {
        "lat": -13.5,
        "lon": 298.5,
        "expected_min": -5000.0,
        "expected_max": -1000.0,
        "type": "Rift Canyon Chasma",
        "description": "Deep central trough of Valles Marineris"
    },
    "Elysium Mons Summit": {
        "lat": 25.0,
        "lon": 147.2,
        "expected_min": 10000.0,
        "expected_max": 14500.0,
        "type": "Volcanic Shield Peak",
        "description": "Isolated volcanic construct in Elysium province"
    }
}


def validate_phase3_outputs():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_lbl = os.path.join(base_dir, "data", "raw", "mola", "megt90n000cb.lbl")
    raw_img = os.path.join(base_dir, "data", "raw", "mola", "megt90n000cb.img")
    proc_elev = os.path.join(base_dir, "data", "processed", "mola", "mola_megt90n000cb_elevation.tif")
    proc_slope = os.path.join(base_dir, "data", "processed", "mola", "mola_megt90n000cb_slope.tif")
    proc_rough = os.path.join(base_dir, "data", "processed", "mola", "mola_megt90n000cb_roughness.tif")
    proc_manifest = os.path.join(base_dir, "data", "processed", "mola", "mola_megt90n000cb_manifest.json")

    print("==================================================================")
    print(" STAGE 1: Independent Validation of Phase 3 MOLA Outputs")
    print("==================================================================")

    # 1. Inspect PDS label vs Rasterio
    lbl_data = PDS3LabelParser.parse_label_file(raw_lbl)
    img_obj = lbl_data["IMAGE"]
    proj_obj = lbl_data["IMAGE_MAP_PROJECTION"]

    print("\n1. PDS Label Projection Parameters:")
    print(f"   • MAP_PROJECTION_TYPE: {proj_obj.get('MAP_PROJECTION_TYPE')}")
    print(f"   • MAP_RESOLUTION: {proj_obj.get('MAP_RESOLUTION')} px/deg")
    print(f"   • MAXIMUM_LATITUDE: {proj_obj.get('MAXIMUM_LATITUDE')}°")
    print(f"   • MINIMUM_LATITUDE: {proj_obj.get('MINIMUM_LATITUDE')}°")
    print(f"   • WESTERNMOST_LONGITUDE: {proj_obj.get('WESTERNMOST_LONGITUDE')}°")
    print(f"   • EASTERNMOST_LONGITUDE: {proj_obj.get('EASTERNMOST_LONGITUDE')}°")
    print(f"   • A_AXIS_RADIUS: {proj_obj.get('A_AXIS_RADIUS')} km")
    print(f"   • COORDINATE_SYSTEM_NAME: {proj_obj.get('COORDINATE_SYSTEM_NAME')}")

    # 2. Check GeoTIFF transform and pixel alignment
    with rasterio.open(proc_elev) as src:
        bounds = src.bounds
        transform = src.transform
        res_x, res_y = src.res

        print("\n2. Raster Transform & Pixel Alignment:")
        print(f"   • Transform: {transform}")
        print(f"   • Bounds: Left={bounds.left}°, Bottom={bounds.bottom}°, Right={bounds.right}°, Top={bounds.top}°")
        print(f"   • Pixel Resolution: dx={res_x}°, dy={res_y}° (expected 0.25°)")
        print(f"   • Overviews count: {len(src.overviews(1))} levels {src.overviews(1)}")
        print(f"   • Internal Tiling: Tiled={src.is_tiled}, Block size={src.block_shapes[0]}")
        print(f"   • NoData: {src.nodata}")

        # Pixel center check: Top-left pixel center is at (left + dx/2, top - dy/2)
        tl_center_lon = bounds.left + res_x / 2.0
        tl_center_lat = bounds.top - res_y / 2.0
        print(f"   • Pixel (0,0) Center: Lon={tl_center_lon:.4f}°E, Lat={tl_center_lat:.4f}°N")
        assert bounds.left == 0.0 and bounds.right == 360.0, "Longitude bounds must span [0, 360]"
        assert bounds.bottom == -90.0 and bounds.top == 90.0, "Latitude bounds must span [-90, +90]"
        assert res_x == 0.25 and res_y == 0.25, "Pixel spacing must equal 0.25 deg (4 px/deg)"

    # 3. Test Topographic Georeferencing against Known Landmarks
    print("\n3. Landmark Elevation Sampling Test:")
    engine = TerrainDataEngine()
    engine.register_local_raster("mola-megdr", proc_elev)

    all_landmarks_passed = True
    for name, lm in KNOWN_MARS_LANDMARKS.items():
        q = ElevationPointQuery(latitude=lm["lat"], longitude=lm["lon"], dataset_id="mola-megdr")
        res = engine.query_elevation_point(q)
        elev = res.elevation_m
        in_range = lm["expected_min"] <= elev <= lm["expected_max"]
        status = "PASS" if in_range else "FAIL"
        if not in_range:
            all_landmarks_passed = False
        print(f"   [{status}] {name} ({lm['lat']}°N, {lm['lon']}°E):")
        print(f"          Sampled: {elev:,.1f} m  |  Expected: [{lm['expected_min']:,.0f} m to {lm['expected_max']:,.0f} m]")

    assert all_landmarks_passed, "All landmark elevation tests must pass within physical bounds!"

    # 4. Check Slope and Roughness Rasters
    print("\n4. Slope and Roughness Quality Inspection:")
    with rasterio.open(proc_slope) as s_src:
        s_data = s_src.read(1)
        valid_s = s_data[s_data != -32768.0]
        print(f"   • Slope Grid: {s_src.width} x {s_src.height}, Min={np.min(valid_s):.2f}°, Max={np.max(valid_s):.2f}°, Mean={np.mean(valid_s):.2f}°")
        assert np.min(valid_s) >= 0.0, "Slope cannot be negative"
        assert np.max(valid_s) < 60.0, "Slope at 4 px/deg cannot exceed 60 degrees"

    with rasterio.open(proc_rough) as r_src:
        r_data = r_src.read(1)
        valid_r = r_data[r_data != -32768.0]
        print(f"   • Roughness Grid: {r_src.width} x {r_src.height}, Min={np.min(valid_r):.2f} m, Max={np.max(valid_r):.2f} m, Mean={np.mean(valid_r):.2f} m")
        assert np.min(valid_r) >= 0.0, "Roughness cannot be negative"

    print("\n==================================================================")
    print(" STAGE 1 VALIDATION COMPLETED: ALL GEOREFERENCING TESTS PASSED")
    print("==================================================================")


if __name__ == "__main__":
    validate_phase3_outputs()
