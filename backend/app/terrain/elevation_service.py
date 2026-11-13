"""Elevation data access and sampling service for MARS-X."""

import os
import logging
from typing import Optional, List, Dict, Any
import numpy as np
import rasterio

from app.terrain.models import (
    ElevationPointQuery,
    ElevationPointResult,
    SlopeMetricResult,
)
from app.terrain.provenance import TERRAIN_DATASET_PROVENANCE
from app.terrain.processor import (
    create_valid_data_mask,
    calculate_slope_grid,
    compute_latitudinal_metric_spacing,
)

logger = logging.getLogger("MARS-X.terrain.elevation_service")


class TerrainDataEngine:
    """Core engine for managing on-disk and in-memory Martian elevation rasters."""

    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        self._loaded_rasters: Dict[str, str] = {}
        # Auto-discover known processed rasters
        self._auto_discover_rasters()

    def _auto_discover_rasters(self):
        candidate_paths = [
            "data/processed/mola/mola_megt90n000cb_elevation.tif",
            "../data/processed/mola/mola_megt90n000cb_elevation.tif",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed", "mola", "mola_megt90n000cb_elevation.tif"),
        ]
        for p in candidate_paths:
            abs_p = os.path.abspath(p)
            if os.path.exists(abs_p):
                self._loaded_rasters["mola-megdr"] = abs_p
                logger.info("Auto-discovered MOLA elevation raster: %s", abs_p)
                break

    def register_local_raster(self, dataset_id: str, file_path: str):
        """Register a validated local raster path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot register missing raster file: {file_path}")
        self._loaded_rasters[dataset_id.lower()] = os.path.abspath(file_path)
        logger.info("Registered local raster for %s: %s", dataset_id, file_path)

    def is_raster_available(self, dataset_id: str) -> bool:
        """Check if local raster data has been downloaded and registered."""
        path = self._loaded_rasters.get(dataset_id.lower())
        return path is not None and os.path.exists(path)

    def query_elevation_point(self, query: ElevationPointQuery) -> ElevationPointResult:
        """Query elevation for a single Martian coordinate.

        Strict scientific rule:
        If local raster data has not been downloaded, return an honest status.
        Never fabricate or estimate elevation data.
        """
        d_id = query.dataset_id.lower()
        if not self.is_raster_available(d_id):
            return ElevationPointResult(
                latitude=query.latitude,
                longitude=query.longitude,
                elevation_m=None,
                dataset_id=query.dataset_id,
                is_valid=False,
                status_note=(
                    f"Numerical raster file for '{query.dataset_id}' is not yet downloaded to local storage. "
                    "Dataset is registered in catalogue (Phase 2). Elevation cannot be fabricated."
                ),
            )

        raster_path = self._loaded_rasters[d_id]
        try:
            with rasterio.open(raster_path) as src:
                # Sample coordinate
                coord = [(query.longitude, query.latitude)]
                samples = list(src.sample(coord))
                if not samples or len(samples[0]) == 0:
                    return ElevationPointResult(
                        latitude=query.latitude,
                        longitude=query.longitude,
                        elevation_m=None,
                        dataset_id=query.dataset_id,
                        is_valid=False,
                        status_note="Coordinate falls outside raster spatial extent.",
                    )

                raw_val = float(samples[0][0])
                nodata = src.nodata

                # Validate against NoData
                if nodata is not None and (raw_val == nodata or np.isclose(raw_val, nodata, atol=1e-3)):
                    return ElevationPointResult(
                        latitude=query.latitude,
                        longitude=query.longitude,
                        elevation_m=None,
                        dataset_id=query.dataset_id,
                        is_valid=False,
                        status_note="Coordinate is located in an unmeasured NoData void.",
                    )

                return ElevationPointResult(
                    latitude=query.latitude,
                    longitude=query.longitude,
                    elevation_m=round(raw_val, 2),
                    dataset_id=query.dataset_id,
                    is_valid=True,
                    status_note="Valid numerical elevation sampled from raster.",
                )

        except Exception as e:
            logger.error("Error sampling elevation: %s", str(e))
            return ElevationPointResult(
                latitude=query.latitude,
                longitude=query.longitude,
                elevation_m=None,
                dataset_id=query.dataset_id,
                is_valid=False,
                status_note=f"Raster sampling failed: {str(e)}",
            )

    def calculate_subregion_slope(
        self,
        dataset_id: str,
        elevation_grid: np.ndarray,
        center_lat_deg: float,
        dlon_deg: float,
        dlat_deg: float,
        nodata_val: Optional[float] = -32768.0,
        algorithm: str = "horn",
    ) -> SlopeMetricResult:
        """Perform slope calculations on a verified 2D elevation array."""
        valid_mask = create_valid_data_mask(elevation_grid, nodata_val)
        dx_m, dy_m = compute_latitudinal_metric_spacing(center_lat_deg, dlon_deg, dlat_deg)

        slope_arr, valid_slope_mask = calculate_slope_grid(
            elevation=elevation_grid,
            dx_m=dx_m,
            dy_m=dy_m,
            valid_mask=valid_mask,
            algorithm=algorithm,
        )

        valid_count = int(np.count_nonzero(valid_slope_mask))
        nodata_count = int(elevation_grid.size - valid_count)

        if valid_count == 0:
            return SlopeMetricResult(
                dataset_id=dataset_id,
                algorithm=algorithm,
                min_slope_deg=None,
                max_slope_deg=None,
                mean_slope_deg=None,
                valid_cells=0,
                nodata_cells=nodata_count,
                scientific_note="Entire subregion contains NoData or boundary cells; no valid slope calculable.",
            )

        valid_slopes = slope_arr[valid_slope_mask]
        return SlopeMetricResult(
            dataset_id=dataset_id,
            algorithm=algorithm,
            min_slope_deg=round(float(np.min(valid_slopes)), 2),
            max_slope_deg=round(float(np.max(valid_slopes)), 2),
            mean_slope_deg=round(float(np.mean(valid_slopes)), 2),
            valid_cells=valid_count,
            nodata_cells=nodata_count,
            scientific_note=(
                f"Calculated with {algorithm.capitalize()}'s method using latitudinally scaled metric cell spacing "
                f"(dx={dx_m:.1f}m, dy={dy_m:.1f}m at {center_lat_deg:.2f}° lat)."
            ),
        )


# Global terrain engine instance
engine = TerrainDataEngine()

