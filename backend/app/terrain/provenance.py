"""Dataset provenance and catalog registry for Martian numerical elevation products."""

from typing import Dict, List, Optional, Any
from app.terrain.models import TerrainSummaryResponse, RasterCoverageResponse

TERRAIN_DATASET_PROVENANCE: Dict[str, Dict[str, Any]] = {
    "mola-megdr": {
        "dataset_id": "mola-megdr",
        "name": "MOLA Mission Experiment Gridded Data Records (MEGDR)",
        "mission": "Mars Global Surveyor (MGS)",
        "instrument": "Mars Orbiter Laser Altimeter (MOLA)",
        "product_type": "Numerical Topographic DTM",
        "status": "registered",
        "elevation_unit": "metres relative to MOLA Areoid",
        "native_resolution_desc": "128 pixels/degree (~463 m/px at equator)",
        "is_numerical_dtm": True,
        "coverage": "Near-global (±88° Lat, 0°–360° East Lon)",
        "nodata_value_repr": "-32768 (int16)",
        "scientific_limitations": "Spatial resolution limited to ~463 m; polar gap beyond 88° latitude; microtopography (<100m) not resolved.",
        "provenance_source": "NASA Planetary Data System (PDS) Geosciences Node / Smith et al. (2001)",
        "source_url": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
        "coverage_bounds": {
            "is_global": True,
            "lat_min": -88.0,
            "lat_max": 88.0,
            "lon_min": 0.0,
            "lon_max": 360.0,
            "crs": "IAU:49900",
            "total_area_approx_pct": 98.6,
            "notes": "Global cylindrical coverage excluding narrow 2° polar caps covered by polar stereographic megp products."
        }
    },
    "hrsc-dtm": {
        "dataset_id": "hrsc-dtm",
        "name": "HRSC High Resolution Stereo Camera DTMs",
        "mission": "Mars Express (ESA/MEX)",
        "instrument": "High Resolution Stereo Camera (HRSC)",
        "product_type": "Stereophotogrammetric DTM",
        "status": "registered",
        "elevation_unit": "metres relative to MOLA Areoid",
        "native_resolution_desc": "50–100 m/px",
        "is_numerical_dtm": True,
        "coverage": "Regional orbital swaths (covering ~50%–70% of Martian surface)",
        "nodata_value_repr": "-32768.0 (float32)",
        "scientific_limitations": "Non-contiguous strip coverage; precision depends on stereo convergence angle and atmospheric dust optical depth.",
        "provenance_source": "ESA Planetary Science Archive / DLR Institute of Planetary Research / Gwinner et al. (2010)",
        "source_url": "https://pds-geosciences.wustl.edu/missions/mars_express/hrsc.htm",
        "coverage_bounds": {
            "is_global": False,
            "lat_min": -85.0,
            "lat_max": 85.0,
            "lon_min": 0.0,
            "lon_max": 360.0,
            "crs": "IAU:49900",
            "total_area_approx_pct": 60.0,
            "notes": "Strip-based regional mosaics, including MC-11 quadrangle products (Oxia Planum / Ares Vallis)."
        }
    },
    "hirise-dtm": {
        "dataset_id": "hirise-dtm",
        "name": "HiRISE High Resolution Imaging Science Experiment DTMs",
        "mission": "Mars Reconnaissance Orbiter (MRO)",
        "instrument": "High Resolution Imaging Science Experiment (HiRISE)",
        "product_type": "Ultra-High-Resolution Stereo DTM",
        "status": "registered",
        "elevation_unit": "metres relative to MOLA Areoid",
        "native_resolution_desc": "1.0 m/px (post-spacing derived from 0.25 m imagery)",
        "is_numerical_dtm": True,
        "coverage": "Targeted candidate landing sites and high-priority scientific targets (<0.1% global coverage)",
        "nodata_value_repr": "-3.4028235e+38 (float32 IEEE-754)",
        "scientific_limitations": "Extremely sparse spatial footprint (~5 km x 20 km swaths); DTM edges contain photogrammetric interpolation artifacts.",
        "provenance_source": "University of Arizona Lunar & Planetary Laboratory / NASA PDS / McEwen et al. (2007)",
        "source_url": "https://www.uahirise.org/dtm/",
        "coverage_bounds": {
            "is_global": False,
            "lat_min": -70.0,
            "lat_max": 70.0,
            "lon_min": 0.0,
            "lon_max": 360.0,
            "crs": "Equirectangular Mars",
            "total_area_approx_pct": 0.08,
            "notes": "Targeted high-resolution swaths around Jezero, Gale, Gusev, and candidate human landing zones."
        }
    },
    "ctx-dtm": {
        "dataset_id": "ctx-dtm",
        "name": "CTX Context Camera Stereo DTMs",
        "mission": "Mars Reconnaissance Orbiter (MRO)",
        "instrument": "Context Camera (CTX)",
        "product_type": "Regional Stereo Photogrammetric DTM",
        "status": "registered",
        "elevation_unit": "metres relative to MOLA Areoid",
        "native_resolution_desc": "18–24 m/px (processed from 6 m optical frames)",
        "is_numerical_dtm": True,
        "coverage": "Regional corridors around major craters, rift canyons, and landing sites (~5%–10% of surface)",
        "nodata_value_repr": "-32768.0 (float32)",
        "scientific_limitations": "Stereo pairs processed on demand via NASA Ames Stereo Pipeline; gaps between non-overlapping orbits.",
        "provenance_source": "NASA Ames Stereo Pipeline (ASP) / Murray Lab Caltech / Malin et al. (2007)",
        "source_url": "https://pds-imaging.jpl.nasa.gov/volumes/mro.html",
        "coverage_bounds": {
            "is_global": False,
            "lat_min": -80.0,
            "lat_max": 80.0,
            "lon_min": 0.0,
            "lon_max": 360.0,
            "crs": "IAU:49900",
            "total_area_approx_pct": 8.0,
            "notes": "Targeted and regional corridors around landing sites and high-relief geologic targets."
        }
    }
}


def list_terrain_datasets() -> List[TerrainSummaryResponse]:
    """Return summary responses for all registered numerical terrain datasets."""
    return [
        TerrainSummaryResponse(
            dataset_id=item["dataset_id"],
            name=item["name"],
            mission=item["mission"],
            instrument=item["instrument"],
            product_type=item["product_type"],
            status=item["status"],
            elevation_unit=item["elevation_unit"],
            native_resolution_desc=item["native_resolution_desc"],
            is_numerical_dtm=item["is_numerical_dtm"],
            coverage=item["coverage"],
            nodata_value_repr=item["nodata_value_repr"],
            scientific_limitations=item["scientific_limitations"],
            provenance_source=item["provenance_source"],
        )
        for item in TERRAIN_DATASET_PROVENANCE.values()
    ]


def get_terrain_dataset_coverage(dataset_id: str) -> Optional[RasterCoverageResponse]:
    """Retrieve coverage footprint information for a given dataset ID."""
    entry = TERRAIN_DATASET_PROVENANCE.get(dataset_id.lower())
    if not entry:
        return None
    cov = entry["coverage_bounds"]
    return RasterCoverageResponse(
        dataset_id=entry["dataset_id"],
        is_global=cov["is_global"],
        lat_min=cov["lat_min"],
        lat_max=cov["lat_max"],
        lon_min=cov["lon_min"],
        lon_max=cov["lon_max"],
        crs=cov["crs"],
        total_area_approx_pct=cov["total_area_approx_pct"],
        notes=cov["notes"],
    )


def get_terrain_dataset_summary(dataset_id: str) -> Optional[TerrainSummaryResponse]:
    """Retrieve complete metadata summary for a single terrain dataset."""
    entry = TERRAIN_DATASET_PROVENANCE.get(dataset_id.lower())
    if not entry:
        return None
    return TerrainSummaryResponse(
        dataset_id=entry["dataset_id"],
        name=entry["name"],
        mission=entry["mission"],
        instrument=entry["instrument"],
        product_type=entry["product_type"],
        status=entry["status"],
        elevation_unit=entry["elevation_unit"],
        native_resolution_desc=entry["native_resolution_desc"],
        is_numerical_dtm=entry["is_numerical_dtm"],
        coverage=entry["coverage"],
        nodata_value_repr=entry["nodata_value_repr"],
        scientific_limitations=entry["scientific_limitations"],
        provenance_source=entry["provenance_source"],
    )
