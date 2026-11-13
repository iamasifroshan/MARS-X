"""MOLA MEGDR product ingestion, validation, and terrain processing manager.

Downloads official NASA PDS files, verifies SHA-256 checksums, ingests raw binary data,
generates Cloud Optimized GeoTIFFs (COGs), and produces verified slope and roughness products.
"""

import os
import json
import time
import hashlib
import logging
import urllib.request
from typing import Dict, Any, Tuple, Optional
import numpy as np
import rasterio

from app.terrain.pds_parser import PDS3LabelParser, read_pds3_image_binary
from app.terrain.cog_converter import convert_array_to_cog
from app.terrain.processor import (
    create_valid_data_mask,
    calculate_slope_grid,
    calculate_terrain_roughness,
    compute_latitudinal_metric_spacing,
)
from app.terrain.elevation_service import engine

logger = logging.getLogger("MARS-X.terrain.ingestion")

MOLA_PDS_BASE_URL = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x"


def compute_sha256(file_path: str) -> str:
    """Compute hex SHA-256 checksum of a local file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class MOLAIngestionService:
    """Manages acquisition, verification, and ingestion of MOLA MEGDR elevation data."""

    def __init__(
        self,
        raw_dir: str = "data/raw/mola",
        processed_dir: str = "data/processed/mola"
    ):
        self.raw_dir = os.path.abspath(raw_dir)
        self.processed_dir = os.path.abspath(processed_dir)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def download_product(
        self,
        subfolder: str = "meg004",
        filename_base: str = "megt90n000cb",
        force_redownload: bool = False
    ) -> Dict[str, Any]:
        """Download PDS label (.lbl) and binary image (.img)."""
        lbl_name = f"{filename_base}.lbl"
        img_name = f"{filename_base}.img"

        lbl_url = f"{MOLA_PDS_BASE_URL}/{subfolder}/{lbl_name}"
        img_url = f"{MOLA_PDS_BASE_URL}/{subfolder}/{img_name}"

        lbl_local = os.path.join(self.raw_dir, lbl_name)
        img_local = os.path.join(self.raw_dir, img_name)

        headers = {"User-Agent": "MARS-X-IngestionEngine/1.0 (NASA Space Apps 2026)"}

        # Download LBL
        if force_redownload or not os.path.exists(lbl_local):
            logger.info("Downloading PDS label: %s", lbl_url)
            req = urllib.request.Request(lbl_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(lbl_local, "wb") as f:
                    f.write(resp.read())

        # Download IMG
        if force_redownload or not os.path.exists(img_local):
            logger.info("Downloading PDS binary image: %s", img_url)
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(img_local, "wb") as f:
                    f.write(resp.read())

        # Compute checksums
        lbl_sha256 = compute_sha256(lbl_local)
        img_sha256 = compute_sha256(img_local)

        provenance = {
            "product_id": filename_base.upper(),
            "retrieval_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_urls": {
                "label": lbl_url,
                "image": img_url,
            },
            "files": {
                "label": {
                    "filename": lbl_name,
                    "path": lbl_local,
                    "size_bytes": os.path.getsize(lbl_local),
                    "sha256": lbl_sha256,
                },
                "image": {
                    "filename": img_name,
                    "path": img_local,
                    "size_bytes": os.path.getsize(img_local),
                    "sha256": img_sha256,
                }
            }
        }

        # Save provenance record in raw storage
        prov_path = os.path.join(self.raw_dir, f"{filename_base}_provenance.json")
        with open(prov_path, "w", encoding="utf-8") as f:
            json.dump(provenance, f, indent=2)

        return provenance

    def ingest_and_process(
        self,
        filename_base: str = "megt90n000cb",
    ) -> Dict[str, Any]:
        """Ingest raw PDS file and generate verified elevation, slope, and roughness COGs."""
        lbl_path = os.path.join(self.raw_dir, f"{filename_base}.lbl")
        img_path = os.path.join(self.raw_dir, f"{filename_base}.img")

        if not os.path.exists(lbl_path) or not os.path.exists(img_path):
            raise FileNotFoundError(f"Raw data files missing in {self.raw_dir}")

        # 1. Parse PDS3 Label
        lbl_data = PDS3LabelParser.parse_label_file(lbl_path)
        elevation_arr, pds_meta = read_pds3_image_binary(img_path, lbl_data)

        rows, cols = elevation_arr.shape
        resolution_ppd = pds_meta["map_resolution_ppd"]
        pixel_size_deg = 1.0 / resolution_ppd

        # 2. Elevation Statistics & Valid Mask
        valid_mask = create_valid_data_mask(elevation_arr, nodata_value=-32768.0)
        valid_elevation = elevation_arr[valid_mask]

        elev_min = float(np.min(valid_elevation))
        elev_max = float(np.max(valid_elevation))
        elev_mean = float(np.mean(valid_elevation))
        elev_std = float(np.std(valid_elevation))
        valid_pct = float((np.count_nonzero(valid_mask) / elevation_arr.size) * 100.0)

        # 3. Export Ingested Elevation as Cloud Optimized GeoTIFF (COG)
        elevation_cog_path = os.path.join(self.processed_dir, f"mola_{filename_base}_elevation.tif")
        cog_result = convert_array_to_cog(
            elevation_data=elevation_arr,
            output_tif_path=elevation_cog_path,
            west_lon=pds_meta["west_longitude"],
            max_lat=pds_meta["max_latitude"],
            pixel_size_x_deg=pixel_size_deg,
            pixel_size_y_deg=pixel_size_deg,
            nodata_value=-32768.0,
        )

        # 4. Generate Slope Raster using Horn's algorithm with latitudinal scaling
        dx_m, dy_m = compute_latitudinal_metric_spacing(
            center_lat_deg=0.0,
            dlon_deg=pixel_size_deg,
            dlat_deg=pixel_size_deg
        )
        slope_grid, slope_valid_mask = calculate_slope_grid(
            elevation=elevation_arr,
            dx_m=dx_m,
            dy_m=dy_m,
            valid_mask=valid_mask,
            algorithm="horn",
        )
        # Preserve NoData
        slope_grid_out = np.where(slope_valid_mask, slope_grid, -32768.0)

        slope_cog_path = os.path.join(self.processed_dir, f"mola_{filename_base}_slope.tif")
        convert_array_to_cog(
            elevation_data=slope_grid_out,
            output_tif_path=slope_cog_path,
            west_lon=pds_meta["west_longitude"],
            max_lat=pds_meta["max_latitude"],
            pixel_size_x_deg=pixel_size_deg,
            pixel_size_y_deg=pixel_size_deg,
            nodata_value=-32768.0,
        )

        # 5. Generate Roughness Raster (local std dev)
        roughness_grid = calculate_terrain_roughness(elevation_arr, valid_mask=valid_mask)
        roughness_grid_out = np.where(np.isfinite(roughness_grid), roughness_grid, -32768.0)

        roughness_cog_path = os.path.join(self.processed_dir, f"mola_{filename_base}_roughness.tif")
        convert_array_to_cog(
            elevation_data=roughness_grid_out,
            output_tif_path=roughness_cog_path,
            west_lon=pds_meta["west_longitude"],
            max_lat=pds_meta["max_latitude"],
            pixel_size_x_deg=pixel_size_deg,
            pixel_size_y_deg=pixel_size_deg,
            nodata_value=-32768.0,
        )

        # 6. Register processed elevation raster in global engine
        engine.register_local_raster("mola-megdr", elevation_cog_path)

        processing_summary = {
            "dataset_id": "mola-megdr",
            "product_id": filename_base.upper(),
            "dimensions": {"lines": rows, "samples": cols},
            "resolution": {
                "pixels_per_degree": resolution_ppd,
                "pixel_size_deg": pixel_size_deg,
                "equatorial_ground_resolution_km": round(dx_m / 1000.0, 3),
            },
            "bounds": {
                "lat_min": pds_meta["min_latitude"],
                "lat_max": pds_meta["max_latitude"],
                "lon_min": pds_meta["west_longitude"],
                "lon_max": pds_meta["east_longitude"],
            },
            "elevation_stats_meters": {
                "min": round(elev_min, 1),
                "max": round(elev_max, 1),
                "mean": round(elev_mean, 1),
                "std": round(elev_std, 1),
                "valid_coverage_pct": round(valid_pct, 2),
            },
            "outputs": {
                "elevation_cog": elevation_cog_path,
                "slope_cog": slope_cog_path,
                "roughness_cog": roughness_cog_path,
            },
            "vertical_datum": "GMM3 Goddard Mars gravity model (mgm1025) areoid to degree 50",
            "coordinate_system": "Planetocentric, Positive-East [0, 360]",
        }

        # Write processed manifest
        manifest_path = os.path.join(self.processed_dir, f"mola_{filename_base}_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(processing_summary, f, indent=2)

        return processing_summary

