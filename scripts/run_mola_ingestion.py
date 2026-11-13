"""Script to execute MOLA MEGDR sample acquisition, ingestion, and terrain processing."""

import sys
import os

# Add backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.terrain.ingestion import MOLAIngestionService
from app.terrain.raster_inspector import inspect_raster_file


def main():
    print("============================================================")
    print(" MARS-X Phase 3: Real MOLA MEGDR Acquisition & Ingestion")
    print("============================================================")

    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mola"))
    proc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "mola"))

    service = MOLAIngestionService(raw_dir=raw_dir, processed_dir=proc_dir)

    print(f"\n1. Downloading MOLA sample (megt90n000cb) to {raw_dir}...")
    provenance = service.download_product(subfolder="meg004", filename_base="megt90n000cb")

    print("\n   Provenance Recorded:")
    print("   - Product ID:", provenance["product_id"])
    print("   - Retrieval Timestamp:", provenance["retrieval_timestamp"])
    for ftype, finfo in provenance["files"].items():
        print(f"   - {ftype.capitalize()}: {finfo['filename']} ({finfo['size_bytes']} bytes)")
        print(f"     SHA-256: {finfo['sha256']}")

    print("\n2. Ingesting raw binary, parsing PDS label, and generating COG products...")
    summary = service.ingest_and_process(filename_base="megt90n000cb")

    print("\n   Processing Summary:")
    print("   - Dimensions:", summary["dimensions"])
    print("   - Resolution:", summary["resolution"])
    print("   - Lat/Lon Bounds:", summary["bounds"])
    print("   - Elevation Stats (m):", summary["elevation_stats_meters"])
    print("   - Vertical Datum:", summary["vertical_datum"])
    print("   - Output COGs:")
    for name, path in summary["outputs"].items():
        print(f"     • {name}: {path} ({os.path.getsize(path):,} bytes)")

    print("\n3. Validating Ingested Elevation COG with Rasterio Engine...")
    elev_cog_path = summary["outputs"]["elevation_cog"]
    meta = inspect_raster_file(elev_cog_path, dataset_id="mola-megdr-sample")

    print("   - Driver:", meta.driver)
    print("   - Width x Height:", meta.width, "x", meta.height)
    print("   - Band Count:", meta.band_count)
    print("   - CRS:", meta.crs, "(Valid Mars CRS:", meta.is_mars_crs, ")")
    print("   - Bounds:", meta.bounds)
    print("   - Resolution (deg):", meta.resolution.pixel_width, "x", meta.resolution.pixel_height)
    print("   - Equator Spacing:", meta.resolution.metric_spacing_equator_m, "meters")
    print("   - NoData Value:", meta.nodata_value)

    print("\n============================================================")
    print(" Real MOLA Ingestion and Verification Complete: SUCCESS")
    print("============================================================")


if __name__ == "__main__":
    main()

