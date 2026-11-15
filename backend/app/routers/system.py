"""System and Storage Diagnostics Router for MARS-X.

NASA Space Apps Challenge: Interplanetary Survival Guide: Martian Map.

Provides endpoints to:
1. Inspect host filesystem mount status and storage capacity (/system/storage)
2. Determine whether the runtime environment uses a persistent volume or an ephemeral container
3. Audit authentic scientific dataset availability on disk
4. Trigger on-demand authentic dataset synchronization (/system/sync)
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Header
from pydantic import BaseModel, Field

from app.config import API_V1_PREFIX, DATA_ROOT

logger = logging.getLogger("MARS-X.routers.system")

router = APIRouter(prefix=f"{API_V1_PREFIX}/system", tags=["system"])


class DiskSpaceInfo(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class StorageInspectionResponse(BaseModel):
    data_root: str
    exists: bool
    is_mount: bool
    storage_type: str  # 'persistent_disk_volume' | 'ephemeral_container_filesystem'
    disk_space: DiskSpaceInfo
    render_environment: Dict[str, Any]
    datasets: Dict[str, Dict[str, Any]]
    corridors_ready: Dict[str, bool]


def _inspect_datasets(data_root: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, bool]]:
    """Inspect availability of primary scientific datasets on host disk."""
    items = {
        "mola_megdr_4ppd_elevation": os.path.join(data_root, "processed", "mola", "mola_megt90n000cb_elevation.tif"),
        "mola_megdr_4ppd_slope": os.path.join(data_root, "processed", "mola", "mola_megt90n000cb_slope.tif"),
        "mola_megdr_4ppd_roughness": os.path.join(data_root, "processed", "mola", "mola_megt90n000cb_roughness.tif"),
        "ctx_tyrrhena_dtm": os.path.join(data_root, "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"),
        "ctx_tyrrhena_slope": os.path.join(data_root, "derived", "traversability", "tyrrhena_slope.tif"),
        "ctx_apollinaris_dtm": os.path.join(data_root, "originals", "ctx", "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif"),
        "ctx_apollinaris_slope": os.path.join(data_root, "derived", "traversability", "apollinaris_slope.tif"),
        "hirise_holden_dtm": os.path.join(data_root, "originals", "hirise", "DTEEC_011635_1510_029542_1510_A01.tif"),
        "hirise_holden_slope": os.path.join(data_root, "derived", "traversability", "holden_slope.tif"),
        "tes_thermal_dayside": os.path.join(data_root, "originals", "themis", "DBmap2007.tif"),
        "tes_thermal_nightside": os.path.join(data_root, "originals", "themis", "NBmap2007.tif"),
        "mcd_climatology_cube": os.path.join(data_root, "derived", "climatology", "mcd_v6_2_climatology_cube.json"),
    }

    report = {}
    for name, path in items.items():
        present = os.path.isfile(path)
        sz = os.path.getsize(path) if present else 0
        report[name] = {
            "present": present,
            "size_bytes": sz,
            "path": path,
        }

    corridors = {
        "tyrrhena_fluvial": report["ctx_tyrrhena_dtm"]["present"] and report["ctx_tyrrhena_slope"]["present"],
        "apollinaris_yardangs": report["ctx_apollinaris_dtm"]["present"] and report["ctx_apollinaris_slope"]["present"],
        "holden_tactical": report["hirise_holden_dtm"]["present"] and report["hirise_holden_slope"]["present"],
        "mola_global_baseline": report["mola_megdr_4ppd_elevation"]["present"] and report["mola_megdr_4ppd_slope"]["present"],
        "tes_thermal_inertia": report["tes_thermal_dayside"]["present"],
        "mcd_climatology": report["mcd_climatology_cube"]["present"],
    }
    return report, corridors


@router.get("/storage", response_model=StorageInspectionResponse)
def get_storage_diagnostics() -> StorageInspectionResponse:
    """Inspect host storage volume, mount state, and dataset inventory."""
    exists = os.path.exists(DATA_ROOT)
    is_mount = False
    try:
        is_mount = os.path.ismount(DATA_ROOT)
    except Exception:
        pass

    # Disk usage
    target_dir = DATA_ROOT if exists else os.path.abspath(os.path.sep)
    usage = shutil.disk_usage(target_dir)
    total_gb = round(usage.total / (1024 ** 3), 2)
    used_gb = round(usage.used / (1024 ** 3), 2)
    free_gb = round(usage.free / (1024 ** 3), 2)
    pct_used = round((usage.used / usage.total) * 100.0, 1)

    storage_type = "persistent_disk_volume" if is_mount else "ephemeral_container_filesystem"

    render_env = {
        "is_render": bool(os.getenv("RENDER")),
        "service_id": os.getenv("RENDER_SERVICE_ID"),
        "instance_id": os.getenv("RENDER_INSTANCE_ID"),
        "service_name": os.getenv("RENDER_SERVICE_NAME"),
        "mars_data_dir_override": os.getenv("MARS_DATA_DIR"),
    }

    datasets_report, corridors_ready = _inspect_datasets(DATA_ROOT)

    return StorageInspectionResponse(
        data_root=DATA_ROOT,
        exists=exists,
        is_mount=is_mount,
        storage_type=storage_type,
        disk_space=DiskSpaceInfo(
            total_gb=total_gb,
            used_gb=used_gb,
            free_gb=free_gb,
            percent_used=pct_used,
        ),
        render_environment=render_env,
        datasets=datasets_report,
        corridors_ready=corridors_ready,
    )


class SyncRequest(BaseModel):
    tier: str = Field(default="core", pattern="^(core|extended|all)$")
    force: bool = False


@router.post("/sync")
def trigger_dataset_sync(request: SyncRequest) -> Dict[str, Any]:
    """Trigger authentic NASA/USGS/ASU dataset synchronization and verification."""
    from scripts.sync_production_datasets import sync_datasets
    try:
        logger.info("Triggered dataset synchronization via API: tier=%s, force=%s", request.tier, request.force)
        res = sync_datasets(tier=request.tier, data_root=DATA_ROOT, force=request.force)
        return res
    except Exception as e:
        logger.error("Dataset sync failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")
