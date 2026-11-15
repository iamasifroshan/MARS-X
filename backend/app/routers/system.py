"""System and Storage Diagnostics & Capability Discovery Router for MARS-X.

NASA Space Apps Challenge: Interplanetary Survival Guide: Martian Map.

Provides endpoints to:
1. Discover backend operating mode & capabilities (/system/capabilities)
   - Cloud Demo Mode vs. Local Full Science Mode
   - Dataset availability & validation status
   - Scientific feature readiness (Marswalk, elevation profile, climatology, etc.)
2. Inspect host filesystem mount status and storage capacity (/system/storage)
3. Audit authentic scientific dataset availability on disk
4. Trigger on-demand authentic dataset synchronization (/system/sync)
"""

import os
import shutil
import logging
from typing import Dict, List, Any, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Header
from pydantic import BaseModel, Field

from app.config import API_V1_PREFIX, DATA_ROOT

logger = logging.getLogger("MARS-X.routers.system")

router = APIRouter(prefix=f"{API_V1_PREFIX}/system", tags=["system"])


# ── Models for Capability Discovery ──────────────────────────────────────────

class DatasetCapability(BaseModel):
    id: str
    name: str
    tier: str  # 'core' | 'extended' | 'baseline'
    type: str  # 'raster_elevation' | 'raster_slope' | 'raster_thermal' | 'json_cube' | 'vector_geology'
    available: bool
    validation_status: str  # 'verified' | 'missing' | 'unverified'
    format: str
    description: str


class FeatureCapability(BaseModel):
    id: str
    name: str
    available: bool
    category: str  # 'raster_analysis' | 'analytical_data' | 'physics_model' | 'catalog'
    required_datasets: List[str]
    reason_if_unavailable: Optional[str] = None


class SystemCapabilitiesResponse(BaseModel):
    operating_mode: str  # 'cloud_demo' | 'local_full_science'
    api_online: bool = True
    api_available: bool = True
    environment: str  # 'production_cloud' | 'local_development'
    raster_processing_available: bool
    cloud_demo_notice: Optional[str] = None
    datasets: Dict[str, DatasetCapability]
    features: Dict[str, FeatureCapability]
    corridors_ready: Dict[str, bool]


# ── Models for Storage Diagnostics ───────────────────────────────────────────

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


# ── Helper Functions ──────────────────────────────────────────────────────────

def get_data_root() -> str:
    """Retrieve dynamically resolved data root honoring environment variable overrides."""
    from app.config import DEFAULT_DATA_DIR
    return os.getenv("MARS_DATA_DIR", os.getenv("DATA_ROOT", DEFAULT_DATA_DIR))


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
        "sim3292_geology": os.path.join(data_root, "originals", "geology", "sim3292_database.zip"),
    }

    report = {}
    for name, path in items.items():
        present = os.path.isfile(path) and os.path.getsize(path) > 0
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


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/capabilities", response_model=SystemCapabilitiesResponse)
def get_system_capabilities() -> SystemCapabilitiesResponse:
    """Discover backend operating mode, dataset availability, and scientific feature readiness."""
    data_root = get_data_root()
    report, corridors = _inspect_datasets(data_root)

    # Determine whether raster processing is available on this environment
    raster_processing_available = bool(
        report["mola_megdr_4ppd_elevation"]["present"] or
        report["ctx_tyrrhena_dtm"]["present"]
    )

    # Determine operating mode
    mode_override = os.getenv("MARS_OPERATING_MODE", "").lower().strip()
    is_render = bool(os.getenv("RENDER"))
    is_cloud_env = is_render or bool(os.getenv("VERCEL"))

    if mode_override in ("cloud_demo", "demo"):
        operating_mode = "cloud_demo"
    elif mode_override in ("local_full_science", "local_full", "full_science"):
        operating_mode = "local_full_science"
    elif is_cloud_env or not raster_processing_available:
        operating_mode = "cloud_demo"
    else:
        operating_mode = "local_full_science"

    cloud_demo_notice = (
        "Full raster-based terrain analysis is available in Local Full Science Mode. "
        "Start the local MARS-X backend with the required scientific datasets."
        if operating_mode == "cloud_demo"
        else None
    )

    # Dataset capabilities catalog
    dataset_caps = {
        "mola_megdr_4": DatasetCapability(
            id="mola_megdr_4",
            name="MOLA MEGDR 4ppd Global Baseline Elevation",
            tier="core",
            type="raster_elevation",
            available=report["mola_megdr_4ppd_elevation"]["present"],
            validation_status="verified" if report["mola_megdr_4ppd_elevation"]["present"] else "missing",
            format="COG (GeoTIFF)",
            description="Global continuous elevation baseline at 4 pixels per degree (~14.8 km/px)."
        ),
        "ctx_tyrrhena": DatasetCapability(
            id="ctx_tyrrhena",
            name="CTX Tyrrhena DTM 20m & Horn Slope",
            tier="core",
            type="raster_elevation",
            available=report["ctx_tyrrhena_dtm"]["present"],
            validation_status="verified" if report["ctx_tyrrhena_dtm"]["present"] else "missing",
            format="GeoTIFF",
            description="USGS controlled CTX stereo digital elevation model at 20 m/px across Tyrrhena Terra."
        ),
        "ctx_apollinaris": DatasetCapability(
            id="ctx_apollinaris",
            name="CTX Apollinaris DTM & Slope",
            tier="extended",
            type="raster_elevation",
            available=report["ctx_apollinaris_dtm"]["present"],
            validation_status="verified" if report["ctx_apollinaris_dtm"]["present"] else "missing",
            format="GeoTIFF",
            description="Controlled CTX DEM at Apollinaris Sulci yardang fields."
        ),
        "hirise_holden": DatasetCapability(
            id="hirise_holden",
            name="HiRISE Holden Crater 1m DTM & Slope",
            tier="extended",
            type="raster_elevation",
            available=report["hirise_holden_dtm"]["present"],
            validation_status="verified" if report["hirise_holden_dtm"]["present"] else "missing",
            format="GeoTIFF",
            description="Ultra-high-resolution 1.0 m/px HiRISE stereo DTM covering Holden Crater."
        ),
        "tes_thermal": DatasetCapability(
            id="tes_thermal",
            name="TES Thermal Inertia (Putzig 2007)",
            tier="core",
            type="raster_thermal",
            available=report["tes_thermal_dayside"]["present"],
            validation_status="verified" if report["tes_thermal_dayside"]["present"] else "missing",
            format="GeoTIFF",
            description="MGS TES derived thermal inertia map at 20 ppd."
        ),
        "mcd_climatology": DatasetCapability(
            id="mcd_climatology",
            name="Mars Climate Database v6.2 Climatology Cube",
            tier="core",
            type="json_cube",
            available=report["mcd_climatology_cube"]["present"],
            validation_status="verified" if report["mcd_climatology_cube"]["present"] else "missing",
            format="JSON",
            description="Curated LMD/ESA Mars Climate Database atmospheric cube."
        ),
        "sim3292_geology": DatasetCapability(
            id="sim3292_geology",
            name="USGS SIM 3292 Global Geologic Map of Mars",
            tier="extended",
            type="vector_geology",
            available=report["sim3292_geology"]["present"],
            validation_status="verified" if report["sim3292_geology"]["present"] else "missing",
            format="Shapefile/Zip",
            description="USGS 1:20,000,000-scale global geologic map by Tanaka et al. (2014)."
        ),
    }

    # Features capability dictionary
    raster_unavailable_reason = (
        "High-resolution DEM rasters are not present on host storage. "
        "Full raster-based terrain analysis is available in Local Full Science Mode. "
        "Start the local MARS-X backend with the required scientific datasets."
    )

    feature_caps = {
        "marswalk_routing": FeatureCapability(
            id="marswalk_routing",
            name="Marswalk A* Traverse Routing",
            available=bool(corridors["tyrrhena_fluvial"] or corridors["apollinaris_yardangs"] or corridors["holden_tactical"]),
            category="raster_analysis",
            required_datasets=["ctx_tyrrhena", "ctx_apollinaris", "hirise_holden"],
            reason_if_unavailable=(
                None if (corridors["tyrrhena_fluvial"] or corridors["apollinaris_yardangs"] or corridors["holden_tactical"])
                else raster_unavailable_reason
            ),
        ),
        "elevation_profile": FeatureCapability(
            id="elevation_profile",
            name="Elevation Profiling & Geodesic Transect",
            available=bool(report["mola_megdr_4ppd_elevation"]["present"] or report["ctx_tyrrhena_dtm"]["present"]),
            category="raster_analysis",
            required_datasets=["mola_megdr_4", "ctx_tyrrhena"],
            reason_if_unavailable=(
                None if (report["mola_megdr_4ppd_elevation"]["present"] or report["ctx_tyrrhena_dtm"]["present"])
                else raster_unavailable_reason
            ),
        ),
        "terrain_intelligence": FeatureCapability(
            id="terrain_intelligence",
            name="Planetary Terrain Intelligence & Multi-Scale Assessment",
            available=bool(report["mola_megdr_4ppd_elevation"]["present"] or report["ctx_tyrrhena_dtm"]["present"]),
            category="raster_analysis",
            required_datasets=["mola_megdr_4", "ctx_tyrrhena"],
            reason_if_unavailable=(
                None if (report["mola_megdr_4ppd_elevation"]["present"] or report["ctx_tyrrhena_dtm"]["present"])
                else raster_unavailable_reason
            ),
        ),
        "themis_thermal": FeatureCapability(
            id="themis_thermal",
            name="THEMIS / TES Thermal Inertia Analysis",
            available=bool(report["tes_thermal_dayside"]["present"]),
            category="raster_analysis",
            required_datasets=["tes_thermal"],
            reason_if_unavailable=(
                None if report["tes_thermal_dayside"]["present"]
                else "Thermal inertia rasters are not present on host storage."
            ),
        ),
        "mcd_climatology": FeatureCapability(
            id="mcd_climatology",
            name="Mars Climate Database Climatology & Diurnal Cycles",
            available=bool(report["mcd_climatology_cube"]["present"]),
            category="analytical_data",
            required_datasets=["mcd_climatology"],
            reason_if_unavailable=(
                None if report["mcd_climatology_cube"]["present"]
                else "Mars Climate Database climatology cube is missing."
            ),
        ),
        "solar_geometry": FeatureCapability(
            id="solar_geometry",
            name="Solar Irradiance & Ephemeris Geometry",
            available=True,
            category="physics_model",
            required_datasets=[],
            reason_if_unavailable=None,
        ),
        "atmospheric_pressure": FeatureCapability(
            id="atmospheric_pressure",
            name="Barometric Scale Height & Atmospheric Pressure Model",
            available=True,
            category="physics_model",
            required_datasets=[],
            reason_if_unavailable=None,
        ),
        "science_discovery": FeatureCapability(
            id="science_discovery",
            name="Martian Science Discovery & Feature Catalog",
            available=True,
            category="catalog",
            required_datasets=[],
            reason_if_unavailable=None,
        ),
    }

    return SystemCapabilitiesResponse(
        operating_mode=operating_mode,
        api_online=True,
        api_available=True,
        environment="production_cloud" if is_cloud_env else "local_development",
        raster_processing_available=raster_processing_available,
        cloud_demo_notice=cloud_demo_notice,
        datasets=dataset_caps,
        features=feature_caps,
        corridors_ready=corridors,
    )


@router.get("/storage", response_model=StorageInspectionResponse)
def get_storage_diagnostics() -> StorageInspectionResponse:
    """Inspect host storage volume, mount state, and dataset inventory."""
    data_root = get_data_root()
    exists = os.path.exists(data_root)
    is_mount = False
    try:
        is_mount = os.path.ismount(data_root)
    except Exception:
        pass

    # Disk usage
    target_dir = data_root if exists else os.path.abspath(os.path.sep)
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

    datasets_report, corridors_ready = _inspect_datasets(data_root)

    return StorageInspectionResponse(
        data_root=data_root,
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
