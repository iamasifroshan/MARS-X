"""Audit raw floating-point elevation benchmark samples."""
import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

import struct
import rasterio
from rasterio.transform import rowcol, xy
import math

from app.terrain.traversability_service import (
    get_traversability_service,
    TERRAIN_SOURCES,
    MARS_RADIUS_M,
)

svc = get_traversability_service()

benchmarks = [
    ("Tyrrhena CTX DTM", "ctx-tyrrhena", -4.600, 66.317, 2189.49),
    ("Apollinaris Sulci Controlled CTX DTM", "ctx-apollinaris", 4.700, 168.250, -2930.77),
    ("Holden Crater Controlled HiRISE DTM", "hirise-holden", -28.500, 309.020, -1132.14),
]

print("=== ELEVATION BENCHMARK NUMERICAL AUDIT ===")

for name, src_id, lat, lon, nominal in benchmarks:
    pt = svc.query_point(lat, lon)
    src_dict = next(s for s in TERRAIN_SOURCES if s["source_id"] == src_id)
    
    with rasterio.open(src_dict["elev_path"]) as ds:
        bounds = ds.bounds
        transform = ds.transform
        dtype = ds.dtypes[0]
        nodata = ds.nodata
        
        # Determine projection coordinates
        lon_norm = lon % 360.0
        if bounds.right <= 0 or (bounds.left < 0 and lon_norm > 180.0):
            proj_lon = lon_norm - 360.0 if lon_norm > 180.0 else lon_norm
        else:
            proj_lon = lon_norm
        x = MARS_RADIUS_M * math.radians(proj_lon)
        y = MARS_RADIUS_M * math.radians(lat)
        
        r, c = rowcol(transform, x, y)
        window = rasterio.windows.Window(c, r, 1, 1)
        raw_val = ds.read(1, window=window)[0, 0]
        raw_bytes = struct.pack(">f", float(raw_val)).hex()
        
    print(f"\nTarget: {name}")
    print(f"  Source ID: {src_id}")
    print(f"  Coordinates: lat={lat:.4f}, lon={lon:.4f} (projected x={x:.2f}, y={y:.2f})")
    print(f"  Raster Pixel Index: row={r}, col={c} (within shape {ds.shape})")
    print(f"  Raster Dtype: {dtype}, NoData={nodata}")
    print(f"  Raw Direct Array Value: {raw_val!r} (type: {type(raw_val).__name__})")
    print(f"  QueryPoint Elevation: {pt.elevation_m!r} (type: {type(pt.elevation_m).__name__})")
    print(f"  Exact Hex (IEEE 754 float32): {raw_bytes}")
    print(f"  Nominal Benchmark: {nominal}")
    print(f"  Rounded (2 decimals): {round(pt.elevation_m, 2)}")
    print(f"  Difference from Nominal: {pt.elevation_m - nominal:+.6f} m")
    print(f"  Bitwise Identical (Direct == QueryPoint): {float(raw_val) == float(pt.elevation_m)}")
