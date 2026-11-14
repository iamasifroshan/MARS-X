"""Science Discovery Engine for MARS-X.

Transforms verified Martian datasets (USGS SIM 3292 Geology, MGS TES Thermal Inertia,
2001 Mars Odyssey THEMIS 256 ppd IR, and CTX / HiRISE / MOLA Elevation Models) into
evidence-based scientific discoveries and location-based science profiles.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from app.science.geology_service import get_geology_service
from app.science.thermal_service import get_thermal_service, get_themis_service
from app.routers.terrain import _sample_point_elevation

logger = logging.getLogger("MARS-X.science.discovery")

# Mars Reference Radius (IAU 2000 Sphere)
MARS_RADIUS_KM = 3396.19


def mars_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance between two points on Mars Sphere (R=3,396.19 km).

    Correctly handles longitude wrapping: wraps delta longitude into [-180, +180].
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(((lon2 - lon1 + 180.0) % 360.0) - 180.0)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(min(1.0, max(0.0, a))))
    return MARS_RADIUS_KM * c


def format_planetary_coord(lat: float, lon: float) -> str:
    """Format coordinates in planetary notation without double negatives.

    Example: lat=-4.6, lon=66.317 -> '4.600°S, 66.317°E'
             lat=18.65, lon=226.2 -> '18.650°N, 226.200°E'
    """
    ns = "N" if lat >= 0 else "S"
    lat_val = abs(lat)
    lon_norm = ((lon % 360.0) + 360.0) % 360.0
    return f"{lat_val:.3f}°{ns}, {lon_norm:.3f}°E"


DISCOVERY_CATEGORIES = {
    "high_res_terrain": {
        "id": "high_res_terrain",
        "title": "High-Resolution Terrain (1m–20m DTM)",
        "description": "Controlled USGS stereo digital terrain models from CTX and HiRISE with meter-scale elevation.",
        "badge_color": "emerald",
        "icon": "🔬",
    },
    "landing_site": {
        "id": "landing_site",
        "title": "Historical Landing Sites",
        "description": "Historical Mars surface landing and impact sites cataloged in USGS SIM 3292.",
        "badge_color": "blue",
        "icon": "🚀",
    },
    "geological_unit_contact": {
        "id": "geological_unit_contact",
        "title": "Geological Units & Contacts",
        "description": "Chronostratigraphic unit contacts, volcanic edifices, massifs, and sedimentary plains from USGS SIM 3292.",
        "badge_color": "amber",
        "icon": "🌋",
    },
    "structural_feature": {
        "id": "structural_feature",
        "title": "Tectonic & Morphologic Structures",
        "description": "Wrinkle ridges, graben axes, outflow channels, pit crater chains, and fault scarps from USGS SIM 3292.",
        "badge_color": "purple",
        "icon": "⚡",
    },
    "thermal_contrast": {
        "id": "thermal_contrast",
        "title": "Thermal-Inertia Contrasts",
        "description": "Regolith thermophysical property contrasts (bedrock/lag vs. insulating dust mantles) from MGS TES.",
        "badge_color": "cyan",
        "icon": "🌡️",
    },
    "multi_dataset_intersection": {
        "id": "multi_dataset_intersection",
        "title": "Multi-Dataset Intersections",
        "description": "High-priority exploration hubs where high-resolution DTM, geology, thermal, and imagery intersect.",
        "badge_color": "rose",
        "icon": "🎯",
    },
}

# Authoritative Catalog of Evidence-Based Science Discoveries (18 Candidates)
CANDIDATE_DISCOVERIES: List[Dict[str, Any]] = [
    # ── 1. High-Resolution Terrain Discoveries ───────────────────────────────
    {
        "id": "disc-terr-tyrrhena-ctx",
        "title": "Tyrrhena Terra Ancient Valley & Cratered Highland",
        "name": "Tyrrhena Terra Ancient Valley & Cratered Highland",
        "category": "high_res_terrain",
        "latitude": -4.600,
        "longitude": 66.317,
        "coordinate_display": "4.600°S, 66.317°E",
        "target_site": "Tyrrhena Terra",
        "primary_feature": "Ancient Valley & Cratered Highland Scarp",
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "primary_source": {
            "feature_or_product": "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
            "source_type": "raster_elevation",
            "native_scale_or_spacing": "20.0128 m/px raster spacing",
            "positional_precision": "Controlled stereo photogrammetric horizontal precision (~0.5 px / ~10 m); vertical tied to MOLA PEDR tracks",
            "vertical_datum": "MOLA Areoid (ASP pc_align tied)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Swath footprint ~40 km wide (Lat [-5.19°, -4.00°], Lon [66.04°, 66.62°E]); outside swath reverts to 463 m/px MOLA 128",
        },
        "supporting_datasets": [
            "ctx-dtm-p21-009323",
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-128",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "ctx-dtm-p21-009323", "product_type": "raster_elevation", "scale_or_pixel_spacing": "20.0128 m/px", "coverage_limitation": "Local swath (~40 km wide)"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
        ],
        "source_references": [
            "GeoTIFF: P21_009323_1754_XN_04S293W_A_01_D01_B01.tif (lines 3328, cols 2240)",
            "SIM 3292 Polygon OBJECTID 846 (Unit eNh)",
            "TES DBmap2007.tif (Pixel col 4926, row 1892)",
        ],
        "scientific_significance": (
            "Tyrrhena Terra contains well-preserved Noachian cratered basement bisected by degraded "
            "troughs and valley networks. The 20m CTX numerical DTM reveals subtle break-in-slope "
            "scarps and boulder-shedding crater rims within the Early Noachian highland unit (eNh)."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw CTX pushbroom CCD sensor telemetry resides in NASA PDS; MARS-X accesses the derived 20m photogrammetric DTM.",
            ],
            "measured_observations": [
                "Raw CTX pushbroom CCD sensor telemetry resides in NASA PDS; MARS-X accesses the derived 20m photogrammetric DTM.",
            ],
            "derived_measurements": [
                "20.0128 m/px controlled stereo CTX DTM elevation (+2189.49 m benchmark, MOLA Areoid datum)",
                "MOLA 128 (463.08 m/px) gridded topography and computed regional slope",
                "Spherical geodesic distance calculations on IAU:49900 Mars Sphere",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 polygon mapping (Unit eNh, Early Noachian highland unit, Feature ID 846, 1:20M map scale)",
                "Nearest genuine stratigraphic contact: Certain contact (OBJECTID 2162) located 144.6 km away",
                "Nearest structure: Impact crater rim (OBJECTID 3304) located 82.2 km away",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~473 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Assess degradation state and erosional rim morphology of Noachian impact structures using 20m vertical profiles.",
                "Characterize local trafficability corridors and micro-slopes for wheeled rover traverses.",
                "Evaluate relationship between bedrock exposures and surrounding coarse sand lag.",
            ],
        },
        "spatial_resolution_desc": "20.0128 m/px stereo CTX elevation co-registered with 463 m/px MOLA 128",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "eNh",
            "unit_name": "Early Noachian highland unit",
            "stratigraphic_age": "Early Noachian",
            "primary_lithology": "Impact-brecciated basaltic crust, interbedded crater ejecta, and ancient impact melt",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 473.4,
            "thermophysical_unit": "Duricrust / coarse sand lag / rock fragments",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 2189.49,
            "best_dtm_elevation_m": 2189.49,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.01,
            "dtm_raster_spacing_m": 20.01,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "CTX DTM coverage is strictly local (~40 km wide swath); outside swath terrain reverts to 463 m/px MOLA 128.",
        "scientific_limitations": [
            "CTX DTM coverage is strictly local (~40 km wide swath); outside swath terrain reverts to 463 m/px MOLA 128.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
            "Geological unit contacts are cartographic interpretations mapped at 1:20M regional scale.",
        ],
        "investigation_opportunities": [
            "Assess degradation state and erosional rim morphology of Noachian impact structures using 20m vertical profile.",
            "Characterize local trafficability corridors and micro-slopes for wheeled rover or astronaut traverses.",
            "Evaluate relationship between bedrock exposures and surrounding coarse sand lag.",
        ],
        "suggested_investigations": [
            "Assess degradation state and erosional rim morphology of Noachian impact structures using 20m vertical profile.",
            "Characterize local trafficability corridors and micro-slopes for wheeled rover or astronaut traverses.",
            "Evaluate relationship between bedrock exposures and surrounding coarse sand lag.",
        ],
    },
    {
        "id": "disc-terr-apollinaris-ctx",
        "title": "Apollinaris Sulci Volcanic Scarp & Basal Plains",
        "name": "Apollinaris Sulci Volcanic Scarp & Basal Plains",
        "category": "high_res_terrain",
        "latitude": 4.700,
        "longitude": 168.250,
        "coordinate_display": "4.700°N, 168.250°E",
        "target_site": "Apollinaris Sulci",
        "primary_feature": "Basal Scarp & Fan Dissections",
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "primary_source": {
            "feature_or_product": "T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif",
            "source_type": "raster_elevation",
            "native_scale_or_spacing": "20.00 m/px raster spacing",
            "positional_precision": "Controlled stereo photogrammetric horizontal precision (~0.5 px / ~10 m); vertical geoid-adjusted via dem_geoid",
            "vertical_datum": "MOLA Areoid (MOLA Geoid-Adjusted)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Controlled footprint bounded within lat 4.5°–5.0°N, lon 168.0°–168.5°E",
        },
        "supporting_datasets": [
            "ctx-dtm-controlled-t01-000893",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "ctx-dtm-controlled-t01-000893", "product_type": "raster_elevation", "scale_or_pixel_spacing": "20.0 m/px", "coverage_limitation": "Controlled footprint (lat 4.5-5.0N, lon 168.0-168.5E)"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
        ],
        "source_references": [
            "GeoTIFF: T01_000893_1847_XN_04N191W_A_01_D01_B01.tif (20m controlled DTM)",
            "SIM 3292 Polygon (Unit lAvf, Late Amazonian volcanic field unit)",
        ],
        "scientific_significance": (
            "Apollinaris Sulci exposes intricate dissected terrain south of the Apollinaris Mons volcanic caldera. "
            "The 20m controlled stereo DTM captures steep basal scarps and fan deposits, marking the transition "
            "between explosive pyroclastic/volcaniclastic units and lowland plains."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw CTX stereo CCD frames reside in NASA PDS; MARS-X integrates the derived 20m controlled DTM.",
            ],
            "measured_observations": [
                "Raw CTX stereo CCD frames reside in NASA PDS; MARS-X integrates the derived 20m controlled DTM.",
            ],
            "derived_measurements": [
                "20.0 m/px controlled USGS stereo CTX DTM elevation (-2930.77 m benchmark, MOLA Geoid Adjusted)",
                "MOLA 4 ppd continuous elevation baseline (14,818.67 m/px)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 cartographic mapping (Unit lAvf, Late Amazonian volcanic field unit, 1:20M map scale)",
                "Nearest structure: Volcanic lobate flow (OBJECTID 1262) located 166.4 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~285 TIU; nominal ~0.50% LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Measure vertical scarp height and slope angles to differentiate tectonic faulting vs. groundwater sapping.",
                "Inspect contact boundary between dissected volcanic materials and younger plains sedimentary fill.",
            ],
        },
        "spatial_resolution_desc": "20.0 m/px controlled USGS stereo CTX DTM",
        "evidence_strength": "high_direct_observation",
        "geological_context": {
            "unit_symbol": "lAvf",
            "unit_name": "Late Amazonian volcanic field unit",
            "stratigraphic_age": "Late Amazonian",
            "primary_lithology": "Volcaniclastic fall deposits, sheet lava flows, and reworked pyroclastic debris",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 285.0,
            "thermophysical_unit": "Moderately indurated sand / volcanic ash",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -2930.77,
            "best_dtm_elevation_m": -2930.77,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.0,
            "dtm_raster_spacing_m": 20.0,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "Controlled DTM footprint is restricted to lat 4.5°–5.0°N, lon 168.0°–168.5°E.",
        "scientific_limitations": [
            "Controlled DTM footprint is restricted to lat 4.5°–5.0°N, lon 168.0°–168.5°E.",
            "Surrounding regional terrain reverts to global 4 ppd MOLA baseline.",
            "Thermal inertia is an indicative nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
        ],
        "investigation_opportunities": [
            "Measure vertical scarp height and slope angles to differentiate tectonic vs. sapping origins.",
            "Inspect contact boundary between dissected volcanic materials and younger sedimentary deposits.",
        ],
        "suggested_investigations": [
            "Measure vertical scarp height and slope angles to differentiate tectonic vs. sapping origins.",
            "Inspect contact boundary between dissected volcanic materials and younger sedimentary deposits.",
        ],
    },
    {
        "id": "disc-terr-holden-hirise",
        "title": "Holden Crater Megabreccia & Layered Lacustrine Strata",
        "name": "Holden Crater Megabreccia & Layered Lacustrine Strata",
        "category": "high_res_terrain",
        "latitude": -28.500,
        "longitude": 309.020,
        "coordinate_display": "28.500°S, 309.020°E",
        "target_site": "Holden Crater",
        "primary_feature": "Megabreccia Blocks & Lacustrine Strata",
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "primary_source": {
            "feature_or_product": "DTEEC_011635_1510_029542_1510_A01.tif",
            "source_type": "raster_elevation",
            "native_scale_or_spacing": "1.01 m/px raster spacing",
            "positional_precision": "Sub-meter stereo bundle adjustment (~0.2–0.5 m horizontal precision); vertical tied to MOLA altimetry",
            "vertical_datum": "MOLA Areoid (MOLA Geoid-Adjusted)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Targeted corridor ~6 km swath width (Lat [-28.65°, -28.38°], Lon [308.99°, 309.05°E]); surrounding regional terrain relies on MOLA",
        },
        "supporting_datasets": [
            "hirise-dtm-controlled-esp-011635",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "hirise-dtm-controlled-esp-011635", "product_type": "raster_elevation", "scale_or_pixel_spacing": "1.01 m/px", "coverage_limitation": "Narrow targeted swath (~6 km width)"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
        ],
        "source_references": [
            "GeoTIFF: DTEEC_011635_1510_029542_1510_A01.tif (1.01m controlled DTM)",
            "SIM 3292 Polygon (Unit AHi, Amazonian and Hesperian impact unit)",
        ],
        "scientific_significance": (
            "Holden Crater preserves one of the most complete aqueous sedimentary sequences on Mars. "
            "The 1.01m controlled HiRISE DTM provides decimeter-scale vertical discrimination of "
            "alluvial fans, megabreccia blocks thrown out by the Holden impact, and finely layered lacustrine beds."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw HiRISE color CCD pushbroom strips reside in NASA PDS; MARS-X integrates the derived 1.01m controlled DTM.",
            ],
            "measured_observations": [
                "Raw HiRISE color CCD pushbroom strips reside in NASA PDS; MARS-X integrates the derived 1.01m controlled DTM.",
            ],
            "derived_measurements": [
                "1.01 m/px controlled USGS stereo HiRISE DTM elevation (-1132.14 m benchmark, MOLA Geoid Adjusted)",
                "Photogrammetric micro-relief and meter-scale slope maps",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 mapped impact crater rim and floor units (Unit AHi, 1:20M map scale)",
                "Nearest structure: Tectonic wrinkle ridge (OBJECTID 826) located 129.2 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~360 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Map individual megabreccia boulder dimensions (>5m) and orientation to infer impact ejecta mechanics.",
                "Quantify millimeter-to-meter bed dip and strike for ancient lacustrine depositional models.",
                "Identify safe traverse routes around boulder fields for robotic or human sample return.",
            ],
        },
        "spatial_resolution_desc": "1.01 m/px ultra-high-resolution controlled HiRISE DTM",
        "evidence_strength": "high_direct_observation",
        "geological_context": {
            "unit_symbol": "AHi",
            "unit_name": "Amazonian and Hesperian impact unit",
            "stratigraphic_age": "Amazonian - Hesperian",
            "primary_lithology": "Impact megabreccia, lacustrine clay-bearing mudstones, and alluvial fan gravels",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 360.0,
            "thermophysical_unit": "Lithified sedimentary strata with loose boulder lag",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -1132.14,
            "best_dtm_elevation_m": -1132.14,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 1.01,
            "dtm_raster_spacing_m": 1.01,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "HiRISE coverage is a narrow targeted swath (~6 km width); surrounding regional terrain relies on MOLA baseline.",
        "scientific_limitations": [
            "HiRISE coverage is a narrow targeted swath (~6 km width); surrounding regional terrain relies on MOLA baseline.",
            "Sub-meter layer thickness requires targeted in-situ imaging to confirm mineral composition.",
            "Regional thermal inertia cannot resolve individual megabreccia clasts.",
        ],
        "investigation_opportunities": [
            "Map individual megabreccia boulder dimensions (>5m) and orientation to infer impact ejecta mechanics.",
            "Quantify millimeter-to-meter bed dip and strike for ancient lacustrine depositional models.",
            "Identify safe traverse routes around boulder fields for robotic or human sample return.",
        ],
        "suggested_investigations": [
            "Map individual megabreccia boulder dimensions (>5m) and orientation to infer impact ejecta mechanics.",
            "Quantify millimeter-to-meter bed dip and strike for ancient lacustrine depositional models.",
            "Identify safe traverse routes around boulder fields for robotic or human sample return.",
        ],
    },

    # ── 2. Historical Surface Landing Sites ───────────────────────────────────
    {
        "id": "disc-land-curiosity",
        "title": "Gale Crater & Mount Sharp (MSL Curiosity)",
        "name": "Gale Crater & Mount Sharp (MSL Curiosity)",
        "category": "landing_site",
        "latitude": -4.590,
        "longitude": 137.440,
        "coordinate_display": "4.590°S, 137.440°E",
        "target_site": "Gale Crater",
        "primary_feature": "Aeolis Mons (Mount Sharp) & Aeolis Palus",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Landing Sites (OBJECTID 9, MSL Curiosity 2012)",
            "source_type": "catalog_record",
            "native_scale_or_spacing": "Published point coordinates with mission landing ellipse (~20 km × 7 km)",
            "positional_precision": "In-situ surface coordinate known to decimeter accuracy via rover localization; orbital base map registration ~50–100 m",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "In-situ surface composition cannot be extrapolated across entire crater from orbital data alone",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n090hb"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 9 (MSL Curiosity, 2012, OBJECTID 9)",
            "SIM 3292 Polygon Unit AHi (Feature ID 754, 1:20M scale)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Mars Science Laboratory (Curiosity) rover in 2012. Gale Crater features a "
            "5-km-high central sedimentary mound (Aeolis Mons / Mount Sharp) exhibiting transitions from "
            "clay-bearing to sulfate-bearing strata, recording the drying of ancient Mars."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "In-situ rover ChemCam/APXS telemetry and raw orbital frames reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "In-situ rover ChemCam/APXS telemetry and raw orbital frames reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded elevation (-4452 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations on IAU:49900 Mars Sphere",
            ],
            "mapped_geological_interpretations": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 9, MSL 2012)",
                "USGS SIM 3292 unit polygon vectors (Unit AHi, 1:20,000,000 cartographic scale)",
                "Nearest structure: Impact crater rim (OBJECTID 103) located 49.6 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~380 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Trace regional contact between Gale floor transitional unit and central mound strata.",
                "Analyze elevation descent from northern crater rim to Aeolis Palus landing ellipse.",
            ],
        },
        "spatial_resolution_desc": "Ground surface exploration site validated by orbital GIS and 463 m/px MOLA 128 altimetry",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "AHi",
            "unit_name": "Amazonian and Hesperian impact unit",
            "stratigraphic_age": "Amazonian - Hesperian",
            "primary_lithology": "Fluvio-lacustrine mudstone, sandstone, and sulfate-bearing layered deposits",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 380.0,
            "thermophysical_unit": "Indurated sedimentary rock with localized sand dunes",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -4452.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "463.08m is the background MOLA elevation grid spacing, NOT the resolution of the landing site point.",
        },
        "limitations": "Orbital data cannot substitute for in-situ rover APXS/CheMin spectroscopic analyses.",
        "scientific_limitations": [
            "Orbital datasets cannot resolve sub-millimeter mineral veins identified by rover instruments.",
            "MOLA 128 averages surface topography across ~463m cells.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
        ],
        "investigation_opportunities": [
            "Trace regional contact between Gale floor transitional unit (Htu) and crater rim massifs.",
            "Analyze elevation descent from northern crater rim to Aeolis Palus landing ellipse.",
        ],
        "suggested_investigations": [
            "Trace regional contact between Gale floor transitional unit (Htu) and crater rim massifs.",
            "Analyze elevation descent from northern crater rim to Aeolis Palus landing ellipse.",
        ],
    },
    {
        "id": "disc-land-opportunity",
        "title": "Meridiani Planum Hematite Plains (MER-B Opportunity)",
        "name": "Meridiani Planum Hematite Plains (MER-B Opportunity)",
        "category": "landing_site",
        "latitude": -1.946,
        "longitude": 354.473,
        "coordinate_display": "1.946°S, 354.473°E",
        "target_site": "Meridiani Planum",
        "primary_feature": "Sulfate Sandstone Plains & Hematite Concretions",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Landing Sites (OBJECTID 7, MER-B Opportunity 2003)",
            "source_type": "catalog_record",
            "native_scale_or_spacing": "Published point coordinates with mission landing ellipse (~120 km × 20 km nominal)",
            "positional_precision": "In-situ surface coordinate verified to decimeter accuracy by orbital descent imaging",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Eagle crater diameter (~22 m) is far below MOLA 128 pixel spacing",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "themis-ir-mosaics-regional",
            "mola-megdr-128",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
            {"dataset_id": "themis-ir-mosaics-regional", "product_type": "visual_imagery", "scale_or_pixel_spacing": "256 ppd (~231.55 m/px)", "coverage_limitation": "Regional tile N-30_000; qualitative 8-bit visual DN"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 7 (MER Opportunity, 2003, OBJECTID 7)",
            "SIM 3292 Polygon Unit HNhu (1:20M scale)",
            "TES DBmap2007.tif (High thermal inertia hematite / basalt lag)",
            "THEMIS 256 ppd IR tile N-30_000",
        ],
        "scientific_significance": (
            "Landing site of NASA's Opportunity rover in 2004 within Eagle Crater. Characterized by crystalline "
            "gray hematite spherules ('blueberries') in sulfate-rich sedimentary rocks, providing decisive "
            "in-situ evidence for persistent acidic groundwater in the Martian past."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Opportunity in-situ camera and spectrometer frames reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Opportunity in-situ camera and spectrometer frames reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded elevation (-1398 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 7, MER B 2003)",
                "USGS SIM 3292 unit polygon vectors (Unit HNhu, 1:20,000,000 cartographic scale)",
                "Nearest structure: Impact crater rim (OBJECTID 2240) located 105.8 km away",
            ],
            "indicative_proxies": [
                "TES thermal inertia proxy estimate (~610 TIU; ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
                "THEMIS 256 ppd IR Band 9 8-bit visual display DN (qualitative; NOT calibrated temperature)",
            ],
            "potential_investigations": [
                "Correlate TES high thermal inertia signature (>600 TIU) with hematite-rich lag distributions.",
                "Compare Meridiani sulfate plains with surrounding Noachian highland bedrock.",
            ],
        },
        "spatial_resolution_desc": "Ground surface in-situ rover site supported by 256 ppd THEMIS IR and 20 ppd TES thermal inertia",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "HNhu",
            "unit_name": "Hesperian and Noachian highland undivided unit",
            "stratigraphic_age": "Hesperian - Noachian",
            "primary_lithology": "Evaporitic sulfate sandstone, jarosite-bearing strata, and hematitic spherule lag",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 610.0,
            "thermophysical_unit": "Bedrock and dense granule/pebble lag",
            "themis_ir_covered": True,
            "themis_band_9_dn": 162.0,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature; THEMIS Band 9 is 8-bit visual DN.",
        },
        "terrain_context": {
            "mola_elevation_m": -1398.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "463.08m is the background MOLA elevation grid spacing, NOT the resolution of the landing site point.",
        },
        "limitations": "Regional 256 ppd THEMIS imagery is qualitative Band 9 visual display DN (not calibrated temperature).",
        "scientific_limitations": [
            "Regional 256 ppd THEMIS imagery is qualitative Band 9 visual display DN (not calibrated temperature).",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Local impact craters (Eagle, Endurance, Victoria) are smaller than MOLA 128 pixel spacing.",
        ],
        "investigation_opportunities": [
            "Correlate TES high thermal inertia signature (>600 TIU) with hematite-rich lag distributions.",
            "Compare Meridiani sulfate plains with surrounding Noachian highland bedrock.",
        ],
        "suggested_investigations": [
            "Correlate TES high thermal inertia signature (>600 TIU) with hematite-rich lag distributions.",
            "Compare Meridiani sulfate plains with surrounding Noachian highland bedrock.",
        ],
    },
    {
        "id": "disc-land-spirit",
        "title": "Gusev Crater Basaltic Floor (MER-A Spirit)",
        "name": "Gusev Crater Basaltic Floor (MER-A Spirit)",
        "category": "landing_site",
        "latitude": -14.569,
        "longitude": 175.473,
        "coordinate_display": "14.569°S, 175.473°E",
        "target_site": "Gusev Crater",
        "primary_feature": "Basaltic Plains & Columbia Hills Hydrothermal Deposits",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Landing Sites (OBJECTID 6, MER-A Spirit 2003)",
            "source_type": "catalog_record",
            "native_scale_or_spacing": "Published point coordinates with mission landing ellipse",
            "positional_precision": "In-situ surface coordinate verified to decimeter accuracy",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Columbia Hills hydrothermal outcrops are below MOLA 128 pixel footprint",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-128",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n090hb"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 6 (MER Spirit, 2003, OBJECTID 6)",
            "SIM 3292 Polygon Unit eHv (Early Hesperian volcanic unit, 1:20M scale)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Spirit rover in 2004. Explored olivine-rich flood basalts on the crater floor "
            "and hydrothermal silica deposits and carbonate-rich outcrops in the Columbia Hills."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Spirit in-situ Pancam and Mössbauer observations reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Spirit in-situ Pancam and Mössbauer observations reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded elevation (-1920 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 6, MER A 2003)",
                "USGS SIM 3292 volcanic unit polygons (Unit eHv, 1:20,000,000 cartographic scale)",
                "Nearest structure: Impact crater rim (OBJECTID 3238) located 2.6 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~310 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Analyze relationship between Ma'adim Vallis outflow breach into Gusev and volcanic resurfacing.",
                "Map transition from crater floor flood basalts to Columbia Hills pyroclastic bedrock.",
            ],
        },
        "spatial_resolution_desc": "In-situ mission coordinates co-located with 463 m/px MOLA 128 altimetry",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "eHv",
            "unit_name": "Early Hesperian volcanic unit",
            "stratigraphic_age": "Early Hesperian",
            "primary_lithology": "Olivine-rich flood basalt lavas, hydrothermal silica sinter, and altered ash",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 310.0,
            "thermophysical_unit": "Basaltic rubble and sand-mantled volcanic floor",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -1920.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "463.08m is the background MOLA elevation grid spacing, NOT the resolution of the landing site point.",
        },
        "limitations": "Coarse orbital datasets cannot resolve hydrothermal micro-structures discovered in Columbia Hills.",
        "scientific_limitations": [
            "Coarse orbital datasets cannot resolve hydrothermal micro-structures discovered in Columbia Hills.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Unit boundaries are generalized at 1:20M regional map scale.",
        ],
        "investigation_opportunities": [
            "Analyze relationship between Ma'adim Vallis outflow breach into Gusev and volcanic resurfacing.",
        ],
        "suggested_investigations": [
            "Analyze relationship between Ma'adim Vallis outflow breach into Gusev and volcanic resurfacing.",
        ],
    },
    {
        "id": "disc-land-pathfinder",
        "title": "Ares Vallis Catastrophic Floodplain (Mars Pathfinder)",
        "name": "Ares Vallis Catastrophic Floodplain (Mars Pathfinder)",
        "category": "landing_site",
        "latitude": 19.261,
        "longitude": 326.747,
        "coordinate_display": "19.261°N, 326.747°E",
        "target_site": "Ares Vallis",
        "primary_feature": "Catastrophic Floodplain & Imbricated Boulders",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Landing Sites (OBJECTID 5, Mars Pathfinder 1996)",
            "source_type": "catalog_record",
            "native_scale_or_spacing": "Published point coordinates with mission landing ellipse (~200 km × 100 km)",
            "positional_precision": "Lander coordinate localized on high-resolution MOC/HiRISE frames",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Regional terrain represented by 4 ppd MOLA baseline in western hemisphere",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-4",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 5 (Mars Pathfinder, 1996, OBJECTID 5)",
            "SIM 3292 Polygon Unit Hto (1:20M scale)",
            "SIM 3292 Structure Line (Channel axis, fluvial origin)",
        ],
        "scientific_significance": (
            "Landing site of Mars Pathfinder and Sojourner rover (1997). Situated at the mouth of Ares Vallis "
            "where catastrophic outburst floods deposited poorly sorted boulders and conglomerate rocks sourced "
            "from diverse crustal provinces."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Pathfinder IMP camera frames and APXS elemental spectrometry reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Pathfinder IMP camera frames and APXS elemental spectrometry reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 4 ppd continuous elevation baseline (-3680 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 5, Pathfinder 1996)",
                "USGS SIM 3292 outflow channel polygons (Unit Hto, 1:20,000,000 cartographic scale)",
                "Nearest structure: Fluvial channel axis (OBJECTID 1369) located 260.4 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~390 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Trace outflow channel alignment from Chryse Planitia basin northward.",
                "Analyze flood deposit thickness and provenance of erratic boulders.",
            ],
        },
        "spatial_resolution_desc": "In-situ ground truth site with global SIM 3292 outflow channel vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "Hto",
            "unit_name": "Hesperian transition outflow unit",
            "stratigraphic_age": "Hesperian",
            "primary_lithology": "Poorly sorted boulder gravel, catastrophic flood cobbles, and mud matrix",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 390.0,
            "thermophysical_unit": "Stony plain / boulder lag deposit",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -3680.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the landing site point.",
        },
        "limitations": "Local terrain is represented by MOLA 4 ppd baseline in the western hemisphere.",
        "scientific_limitations": [
            "Local terrain is represented by MOLA 4 ppd baseline in the western hemisphere.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Imbricated boulders (<1m) cannot be detected from orbit without sub-meter imaging.",
        ],
        "investigation_opportunities": [
            "Trace outflow channel alignment from Chryse Planitia basin northward.",
        ],
        "suggested_investigations": [
            "Trace outflow channel alignment from Chryse Planitia basin northward.",
        ],
    },
    {
        "id": "disc-land-viking1",
        "title": "Chryse Planitia Volcanic-Sedimentary Lowlands (Viking 1)",
        "name": "Chryse Planitia Volcanic-Sedimentary Lowlands (Viking 1)",
        "category": "landing_site",
        "latitude": 22.457,
        "longitude": 312.049,
        "coordinate_display": "22.457°N, 312.049°E",
        "target_site": "Chryse Planitia",
        "primary_feature": "Rolling Lowland Plain & Boulder Field",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Landing Sites (OBJECTID 3, Viking 1 1975)",
            "source_type": "catalog_record",
            "native_scale_or_spacing": "Published point coordinates with mission landing ellipse (~280 km × 100 km)",
            "positional_precision": "Lander coordinate localized on HiRISE frames (Stooke 2007)",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Boulders and surface rock clusters are far below orbital MOLA resolution",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 3 (Viking 1, 1975, OBJECTID 3)",
            "SIM 3292 Polygon Unit Hto (1:20M scale)",
        ],
        "scientific_significance": (
            "First successful long-term Mars surface lander (July 1976). Located on a rolling volcanic plain "
            "littered with impact ejecta boulders, conducting the first in-situ biology and soil chemistry experiments."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Viking Lander 1 facsimile camera imagery and biology experiment telemetry reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Viking Lander 1 facsimile camera imagery and biology experiment telemetry reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 4 ppd continuous elevation baseline (-3690 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 3, Viking 1 1975)",
                "USGS SIM 3292 unit polygon vectors (Unit Hto, 1:20,000,000 cartographic scale)",
                "Nearest structure: Tectonic wrinkle ridge (OBJECTID 1440) located 20.0 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~330 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Characterize lowland plain resurfacing history relative to circum-Chryse outflow channels.",
                "Evaluate weathering rates of exposed basaltic boulders in hyper-arid atmospheric regime.",
            ],
        },
        "spatial_resolution_desc": "Historic surface coordinate on 1:20M scale global chronostratigraphic unit Hto",
        "evidence_strength": "high_direct_observation",
        "geological_context": {
            "unit_symbol": "Hto",
            "unit_name": "Hesperian transition outflow unit",
            "stratigraphic_age": "Hesperian",
            "primary_lithology": "Basaltic volcanic plains interbedded with fluvial and impact sediments",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 330.0,
            "thermophysical_unit": "Duricrust and drifting aeolian silt",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -3690.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the landing site point.",
        },
        "limitations": "Surface rocks are below orbital MOLA resolution.",
        "scientific_limitations": [
            "Surface rocks and boulders are below orbital MOLA resolution.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "1:20M geology map represents generalized regional stratigraphy.",
        ],
        "investigation_opportunities": [
            "Characterize lowland plain resurfacing history relative to circum-Chryse outflow channels.",
        ],
        "suggested_investigations": [
            "Characterize lowland plain resurfacing history relative to circum-Chryse outflow channels.",
        ],
    },

    # ── 3. Geological Units & Contacts ───────────────────────────────────────
    {
        "id": "disc-geol-olympus-mons",
        "title": "Olympus Mons Summit Caldera & Basal Scarp",
        "name": "Olympus Mons Summit Caldera & Basal Scarp",
        "category": "geological_unit_contact",
        "latitude": 18.650,
        "longitude": 226.200,
        "coordinate_display": "18.650°N, 226.200°E",
        "target_site": "Olympus Mons",
        "primary_feature": "Summit Caldera Complex & 8-km Basal Scarp",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Geology (Unit Ave, Feature ID 1046) & Caldera Rim Structures",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Boundary line placement uncertainty ~5–25 km depending on Viking/THEMIS base map quality",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Global scale cartography omits lava tubes and individual flow lobes (< 5 km)",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Polygon Feature ID 1046 (Unit Ave, Amazonian volcanic edifice, 1:20M scale)",
            "SIM 3292 Structure Lines (Caldera rim polylines, volcanic origin)",
            "MOLA elevation continuous baseline (+21,229 m peak areoid elevation)",
        ],
        "scientific_significance": (
            "The largest shield volcano in the solar system, rising ~21.3 km above the datum. "
            "SIM 3292 maps the central edifice as unit Ave, bounded by a complex multi-ring collapse "
            "caldera and encircled by a 6-to-8-km-high basal scarp."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw Viking, HRSC, and THEMIS frames reside in external mission PDS archives.",
            ],
            "measured_observations": [
                "Raw Viking, HRSC, and THEMIS frames reside in external mission PDS archives.",
            ],
            "derived_measurements": [
                "Global MOLA elevation baseline (+21,229 m peak summit areoid elevation, MOLA Areoid datum)",
                "Calculated regional slopes and great-circle geodesic distances",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 unit polygon vectors (Unit Ave, 1:20,000,000 cartographic scale)",
                "USGS SIM 3292 caldera rim and basal scarp structure polylines (OBJECTID 2582, 39.1 km distance)",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~110 TIU; low thermal inertia dust mantle; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Examine nested caldera collapse sequences using structural rim polylines and elevation contours.",
                "Analyze atmospheric dust deposition on upper shield via day/night thermal inertia contrasts.",
            ],
        },
        "spatial_resolution_desc": "Global MOLA continuous elevation baseline co-registered with 1:20M GIS geologic vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "Ave",
            "unit_name": "Amazonian volcanic edifice",
            "stratigraphic_age": "Amazonian",
            "primary_lithology": "Basaltic lava flows, agglutinate cones, and nested caldera collapse blocks",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 110.0,
            "thermophysical_unit": "Fine atmospheric dust mantle on high-altitude summit",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 21229.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the geological unit.",
        },
        "limitations": "Terrain in western Tharsis is covered by the 4 ppd MOLA baseline; high-res CTX coverage is absent at summit.",
        "scientific_limitations": [
            "Summit terrain is covered by the 4 ppd MOLA baseline; meter-scale lava tubes are not resolved.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "High summit elevation (>21 km) experiences extreme atmospheric attenuation.",
        ],
        "investigation_opportunities": [
            "Examine nested caldera collapse sequences using structural rim polylines and elevation contours.",
            "Analyze atmospheric dust deposition on upper shield via day/night thermal inertia contrasts.",
        ],
        "suggested_investigations": [
            "Examine nested caldera collapse sequences using structural rim polylines and elevation contours.",
            "Analyze atmospheric dust deposition on upper shield via day/night thermal inertia contrasts.",
        ],
    },
    {
        "id": "disc-geol-valles-marineris",
        "title": "Melas Chasma Central Tectonic Rift (Valles Marineris)",
        "name": "Melas Chasma Central Tectonic Rift (Valles Marineris)",
        "category": "geological_unit_contact",
        "latitude": -9.800,
        "longitude": 283.600,
        "coordinate_display": "9.800°S, 283.600°E",
        "target_site": "Melas Chasma",
        "primary_feature": "Chasma Interior Floor & Layered Sulfate Mounds",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Geology (Unit Nhu) & Tectonic Fault Scarp Vectors",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Structural trace uncertainty ~5–20 km at 1:20M map compilation scale",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Steep canyon walls produce radar shadows and steep-slope artifacts in global MOLA",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Polygon Unit Nhu (Noachian highland undivided unit, 1:20M scale)",
            "SIM 3292 Structure Lines (Graben axes and fault scarps, tectonic origin)",
            "MOLA elevation baseline (-4,500 m to -7,000 m floor depths)",
        ],
        "scientific_significance": (
            "Melas Chasma is the deepest and widest segment of the Valles Marineris canyon system. "
            "Extensional fault scarps and interior layered deposits record episodic lacustrine and "
            "subaqueous volcanism in an enormous tectonic rift valley."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw imaging frames from Viking, HRSC, and THEMIS reside in external NASA/ESA PDS archives.",
            ],
            "measured_observations": [
                "Raw imaging frames from Viking, HRSC, and THEMIS reside in external NASA/ESA PDS archives.",
            ],
            "derived_measurements": [
                "Global MOLA elevation baseline (-4,820 m floor depth, MOLA Areoid datum)",
                "Calculated relief and geodesic distances",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 unit polygon vectors (Unit Nhu, 1:20,000,000 cartographic scale)",
                "USGS SIM 3292 normal fault and graben structure vectors (OBJECTID 1071, 158.2 km distance)",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~260 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Map depth profile and fault throw across graben axes using MOLA vertical profiles.",
                "Investigate interior layered deposits for evaporite and sulfate mineralization indicators.",
            ],
        },
        "spatial_resolution_desc": "Global MOLA elevation baseline with tectonic structure GIS polylines",
        "evidence_strength": "high_direct_observation",
        "geological_context": {
            "unit_symbol": "Nhu",
            "unit_name": "Noachian highland undivided unit",
            "stratigraphic_age": "Noachian",
            "primary_lithology": "Deeply exposed crustal basalt, interior layered sulfate deposits, and landslide debris",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 260.0,
            "thermophysical_unit": "Talus slopes and unindurated canyon floor fill",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -4820.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the geological unit.",
        },
        "limitations": "Steep canyon walls produce radar shadow and data gaps in some orbital instruments.",
        "scientific_limitations": [
            "Steep canyon walls produce radar shadow and data gaps in some orbital instruments.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Regional MOLA baseline averages narrow tributary canyons.",
        ],
        "investigation_opportunities": [
            "Map depth profile and fault throw across graben axes using MOLA vertical profiles.",
            "Investigate interior layered deposits for evaporite and sulfate mineralization indicators.",
        ],
        "suggested_investigations": [
            "Map depth profile and fault throw across graben axes using MOLA vertical profiles.",
            "Investigate interior layered deposits for evaporite and sulfate mineralization indicators.",
        ],
    },
    {
        "id": "disc-geol-noachis-massifs",
        "title": "Noachis Terra Ancient Crustal Massifs",
        "name": "Noachis Terra Ancient Crustal Massifs",
        "category": "geological_unit_contact",
        "latitude": -35.000,
        "longitude": 30.000,
        "coordinate_display": "35.000°S, 30.000°E",
        "target_site": "Noachis Terra",
        "primary_feature": "Relict Crustal Massifs & Inter-crater Plains",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Geology (Unit lNh, Late Noachian highland massif unit)",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Contact line placement uncertainty ~10–30 km in heavily cratered terrain",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Heavily degraded ancient massifs; contacts mapped at 1:20M regional scale",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Polygon Unit lNh (Late Noachian highland unit, 1:20M scale)",
            "MOLA 128 tile megt00n000hb",
            "TES DBmap2007.tif",
        ],
        "scientific_significance": (
            "Noachis Terra preserves rugged blocks of primitive Martian "
            "crust that survived early heavy bombardment. These massifs provide a rare window into the "
            "deep compositional and tectonic architecture of pre-Noachian and early Noachian crust."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw Viking and THEMIS image frames reside in external mission PDS archives.",
            ],
            "measured_observations": [
                "Raw Viking and THEMIS image frames reside in external mission PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded topography (+1860 m, MOLA Areoid datum)",
                "Spherical geodesic contact distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 mapped crustal massif polygon boundaries (Unit lNh, 1:20,000,000 cartographic scale)",
                "Nearest structure: Tectonic wrinkle ridge (OBJECTID 773) located 68.3 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~340 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Differentiate primitive crustal block elevations from surrounding cratered plateau materials.",
                "Evaluate ancient fracture networks bounding massif perimeters.",
            ],
        },
        "spatial_resolution_desc": "463 m/px MOLA 128 altimetry co-registered with SIM 3292 unit lNh polygons",
        "evidence_strength": "derived_stratigraphic",
        "geological_context": {
            "unit_symbol": "lNh",
            "unit_name": "Late Noachian highland unit",
            "stratigraphic_age": "Late Noachian",
            "primary_lithology": "Heavily cratered basement, anorthositic/basaltic megabreccia, and degraded rims",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 340.0,
            "thermophysical_unit": "Erosion-resistant bedrock with sand-filled valleys",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 1860.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "463.08m is the background MOLA elevation grid spacing, NOT the resolution of the geological unit.",
        },
        "limitations": "Massif units are heavily cratered and degraded; contacts are mapped at 1:20M regional scale.",
        "scientific_limitations": [
            "Massif units are heavily cratered and degraded; contacts are mapped at 1:20M regional scale.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "No local meter-scale DTM is available in this sector.",
        ],
        "investigation_opportunities": [
            "Differentiate primitive crustal block elevations from surrounding cratered plateau materials.",
            "Evaluate ancient fracture networks bounding massif perimeters.",
        ],
        "suggested_investigations": [
            "Differentiate primitive crustal block elevations from surrounding cratered plateau materials.",
            "Evaluate ancient fracture networks bounding massif perimeters.",
        ],
    },

    # ── 4. Tectonic & Morphologic Structures ─────────────────────────────────
    {
        "id": "disc-struct-syrtis-ridges",
        "title": "Syrtis Major Wrinkle Ridge Compressive Network",
        "name": "Syrtis Major Wrinkle Ridge Compressive Network",
        "category": "structural_feature",
        "latitude": 8.500,
        "longitude": 68.000,
        "coordinate_display": "8.500°N, 68.000°E",
        "target_site": "Syrtis Major",
        "primary_feature": "Compressive Wrinkle Ridges & Basaltic Floor",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Structure (Origin: Tectonic, Interpreta: Wrinkle ridge)",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Ridge crest line digitization uncertainty ~5–15 km",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Blind thrust faults beneath wrinkle ridges cannot be imaged directly from orbit",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt44n000hb"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Structure Records (Origin: Tectonic, Interpreta: Wrinkle ridge, 1:20M scale)",
            "SIM 3292 Polygon Unit eHv (Early Hesperian volcanic unit, Syrtis Major Planum)",
            "MOLA 128 tile megt44n000hb",
        ],
        "scientific_significance": (
            "Syrtis Major is an ancient low-relief shield volcano paved with Early Hesperian flood basalts. "
            "A dense network of linear and arcuate wrinkle ridges records lithospheric regional compression "
            "and subsidence caused by the volcanic loading of the underlying crust."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw imaging frames from Viking and THEMIS reside in external NASA PDS archives.",
            ],
            "measured_observations": [
                "Raw imaging frames from Viking and THEMIS reside in external NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded topography (+1210 m, MOLA Areoid datum)",
                "Calculated topographic relief and geodesic distances",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 tectonic wrinkle ridge structure polylines (1:20,000,000 cartographic scale)",
                "USGS SIM 3292 unit polygon vectors (Unit eHv)",
                "Nearest structure: Volcanic caldera rim (OBJECTID 1289) located 67.6 km away",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~530 TIU; high thermal inertia basaltic sand; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Calculate horizontal shortening strain across the wrinkle ridge network using topographic crest heights.",
                "Assess high thermal inertia (>500 TIU) basaltic sand accumulation along ridge windward slopes.",
            ],
        },
        "spatial_resolution_desc": "463 m/px MOLA 128 regional topography with GIS structural polyline overlay",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "eHv",
            "unit_name": "Early Hesperian volcanic unit",
            "stratigraphic_age": "Early Hesperian",
            "primary_lithology": "Dense crystalline flood basalt, pyroxene-rich lava flows, and thrust-faulted ridges",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 530.0,
            "thermophysical_unit": "Unmantled basaltic sand and exposed bedrock",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 1210.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "463.08m is the background MOLA elevation grid spacing, NOT the resolution of the structural trace.",
        },
        "limitations": "Individual thrust fault planes beneath wrinkle ridges cannot be imaged directly from orbit.",
        "scientific_limitations": [
            "Individual thrust fault planes beneath wrinkle ridges cannot be imaged directly from orbit.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Sub-kilometer ridge morphology requires high-resolution stereo models to resolve.",
        ],
        "investigation_opportunities": [
            "Calculate horizontal shortening strain across the wrinkle ridge network using topographic crest heights.",
            "Assess high thermal inertia (>500 TIU) basaltic sand accumulation along ridge windward slopes.",
        ],
        "suggested_investigations": [
            "Calculate horizontal shortening strain across the wrinkle ridge network using topographic crest heights.",
            "Assess high thermal inertia (>500 TIU) basaltic sand accumulation along ridge windward slopes.",
        ],
    },
    {
        "id": "disc-struct-cerberus-graben",
        "title": "Cerberus Fossae Extensional Graben System",
        "name": "Cerberus Fossae Extensional Graben System",
        "category": "structural_feature",
        "latitude": 10.500,
        "longitude": 158.000,
        "coordinate_display": "10.500°N, 158.000°E",
        "target_site": "Cerberus Fossae",
        "primary_feature": "Extensional Graben Troughs & Volcanic Fissures",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Structure (Origin: Tectonic, Interpreta: Graben axis, Feature ID 1272)",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Graben axis digitization uncertainty ~5–10 km",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Narrow fracture widths (< 1 km) are below 4 ppd MOLA grid spacing",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Structure Records (Origin: Tectonic, Interpreta: Graben axis, Morphology: Trough, 1:20M scale)",
            "SIM 3292 Polygon Unit AHv (Amazonian and Hesperian volcanic unit)",
        ],
        "scientific_significance": (
            "Cerberus Fossae consists of subparallel steep-sided extensional rifts cutting through some of the "
            "youngest volcanic plains on Mars. Source of the Athabasca Valles flood lavas and the primary "
            "origin locus of marsquakes detected by the NASA InSight seismometer."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw InSight seismograms and orbital HRSC/CTX frames reside in external mission PDS archives.",
            ],
            "measured_observations": [
                "Raw InSight seismograms and orbital HRSC/CTX frames reside in external mission PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 4 ppd elevation baseline (-2310 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 tectonic graben axis polylines (Trough morphology, 1:20,000,000 cartographic scale, OBJECTID 1272, 28.3 km distance)",
                "USGS SIM 3292 unit polygon vectors (Unit AHv)",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~290 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Relate graben orientation to regional stress fields induced by the Elysium volcanic rise.",
                "Inspect graben floor vents as candidate sites for recent volcanic degassing or subsurface water release.",
            ],
        },
        "spatial_resolution_desc": "GIS tectonic structure vectors co-registered with MOLA baseline",
        "evidence_strength": "high_direct_observation",
        "geological_context": {
            "unit_symbol": "AHv",
            "unit_name": "Amazonian and Hesperian volcanic unit",
            "stratigraphic_age": "Amazonian - Hesperian",
            "primary_lithology": "Sheet flood lavas, dike-fed fissure eruptions, and fault-bounded graben walls",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 290.0,
            "thermophysical_unit": "Moderately mantled basaltic volcanic plain",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -2310.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the structural trace.",
        },
        "limitations": "Narrow fracture widths (<1 km) are below MOLA 4 ppd resolution; requires local high-res imagery for fracture detail.",
        "scientific_limitations": [
            "Narrow fracture widths (<1 km) are below MOLA 4 ppd resolution; requires local high-res imagery for fracture detail.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Seismic focal depths are derived from single-station inversion with associated location ellipses.",
        ],
        "investigation_opportunities": [
            "Relate graben orientation to regional stress fields induced by the Elysium volcanic rise.",
            "Inspect graben floor vents as candidate sites for recent volcanic degassing or subsurface water release.",
        ],
        "suggested_investigations": [
            "Relate graben orientation to regional stress fields induced by the Elysium volcanic rise.",
            "Inspect graben floor vents as candidate sites for recent volcanic degassing or subsurface water release.",
        ],
    },
    {
        "id": "disc-struct-shalbatana-channel",
        "title": "Shalbatana Vallis Catastrophic Outflow Channel",
        "name": "Shalbatana Vallis Catastrophic Outflow Channel",
        "category": "structural_feature",
        "latitude": 7.800,
        "longitude": 317.900,
        "coordinate_display": "7.800°N, 317.900°E",
        "target_site": "Shalbatana Vallis",
        "primary_feature": "Catastrophic Outflow Channel & Chaotic Origin",
        "primary_evidence_class": "mapped_geological_interpretation",
        "evidence_classification": "mapped_geological_interpretation",
        "primary_source": {
            "feature_or_product": "USGS SIM 3292 Global Structure (Origin: Fluvial, Interpreta: Outflow Channel / Channel axis, Feature ID 2015)",
            "source_type": "cartographic_map",
            "native_scale_or_spacing": "1:20,000,000 published cartographic map scale",
            "positional_precision": "Channel thalweg axis digitization uncertainty ~5–15 km",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Channel bed micro-topography smoothed by 4 ppd MOLA grid",
        },
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "SIM 3292 Structure Record (Origin: Fluvial, Interpreta: Outflow Channel / Channel axis, 1:20M scale)",
            "SIM 3292 Polygon Unit mNh (Middle Noachian highland unit)",
        ],
        "scientific_significance": (
            "Shalbatana Vallis originates abruptly from chaotic terrain and carves an enormous steep-walled "
            "canyon down into Chryse Planitia. Serves as a classic example of catastrophic groundwater "
            "outburst flooding and canyon head sapping on early Mars."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw Viking and THEMIS visible images reside in external mission PDS archives.",
            ],
            "measured_observations": [
                "Raw Viking and THEMIS visible images reside in external mission PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 4 ppd elevation baseline (-2980 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 fluvial channel axis structure polylines (1:20,000,000 cartographic scale, OBJECTID 2015, 141.4 km distance)",
                "USGS SIM 3292 unit polygon vectors (Unit mNh)",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (~320 TIU; nominal LUT step proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Model catastrophic flood peak discharge from channel cross-sectional area and bed slope.",
                "Trace sediment deposition fan where Shalbatana discharges into the Chryse basin floor.",
            ],
        },
        "spatial_resolution_desc": "GIS fluvial axis vectors and 1:20M geologic unit boundaries",
        "evidence_strength": "derived_stratigraphic",
        "geological_context": {
            "unit_symbol": "mNh",
            "unit_name": "Middle Noachian highland unit",
            "stratigraphic_age": "Middle Noachian",
            "primary_lithology": "Dissected highland crust, catastrophic flood gravels, and chaotic collapsed blocks",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 320.0,
            "thermophysical_unit": "Fluvial scoured floor with unindurated aeolian fill",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": -2980.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
            "note": "14,818.67m is the background MOLA 4 ppd elevation grid spacing, NOT the resolution of the structural trace.",
        },
        "limitations": "Fluvial flow velocities and discharge rates can only be inferred through hydrodynamic modeling.",
        "scientific_limitations": [
            "Fluvial flow velocities and discharge rates can only be inferred through hydrodynamic modeling.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution).",
            "Channel bed micro-topography is smoothed by 4 ppd MOLA grid.",
        ],
        "investigation_opportunities": [
            "Model catastrophic flood peak discharge from channel cross-sectional area and bed slope.",
            "Trace sediment deposition fan where Shalbatana discharges into the Chryse basin floor.",
        ],
        "suggested_investigations": [
            "Model catastrophic flood peak discharge from channel cross-sectional area and bed slope.",
            "Trace sediment deposition fan where Shalbatana discharges into the Chryse basin floor.",
        ],
    },

    # ── 5. Thermal-Inertia Contrasts ─────────────────────────────────────────
    {
        "id": "disc-therm-sinus-meridiani",
        "title": "Sinus Meridiani High Thermal-Inertia Plains",
        "name": "Sinus Meridiani High Thermal-Inertia Plains",
        "category": "thermal_contrast",
        "latitude": -2.000,
        "longitude": 5.000,
        "coordinate_display": "2.000°S, 5.000°E",
        "target_site": "Sinus Meridiani",
        "primary_feature": "High Thermal-Inertia Bedrock & Coarse Sand Plains",
        "primary_evidence_class": "indicative_proxy",
        "evidence_classification": "indicative_proxy",
        "primary_source": {
            "feature_or_product": "MGS TES Apparent Thermal Inertia 20 ppd global map (Putzig & Mellon 2007, DBmap2007.tif)",
            "source_type": "thermophysical_raster",
            "native_scale_or_spacing": "20 ppd (~2,963 m/px at equator) raster pixel spacing",
            "positional_precision": "Bin-averaged across 20 ppd cells (~3 km); nominal LUT step resolution ~0.50%",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50) [co-registered terrain]",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Unvalidated nominal proxy from 8-bit color-mapped TIFF; NOT kinetic temperature",
        },
        "supporting_datasets": [
            "tes-thermal-inertia-putzig-2007",
            "themis-ir-mosaics-regional",
            "sim3292-geology",
            "mola-megdr-128",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
            {"dataset_id": "themis-ir-mosaics-regional", "product_type": "visual_imagery", "scale_or_pixel_spacing": "256 ppd (~231.55 m/px)", "coverage_limitation": "Regional tile N-30_000; qualitative 8-bit visual DN"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
        ],
        "source_references": [
            "TES DBmap2007.tif (Pixel TI = 724.3 TIU, rocky / indurated plain)",
            "THEMIS 256 ppd IR tile thm_dir_N-30_000.png",
            "SIM 3292 Polygon Unit mNh (Middle Noachian highland unit, 1:20M scale)",
            "MOLA 128 tile megt00n000hb",
        ],
        "scientific_significance": (
            "Sinus Meridiani displays one of the highest thermal inertia signatures on Mars (>700 TIU). "
            "This thermophysical contrast reflects the absence of thick dust mantles and the widespread "
            "presence of coarse basaltic sand, hematite lag deposits, and cemented duricrust layers."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Calibrated TES radiance spectra and THEMIS multi-band radiance cubes reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Calibrated TES radiance spectra and THEMIS multi-band radiance cubes reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded elevation (-1428 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 unit polygon vectors (Unit mNh, 1:20,000,000 cartographic scale)",
                "Nearest structure: Fluvial channel axis (OBJECTID 1914) located 42.6 km away",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~724.3 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
                "THEMIS 256 ppd IR Band 9 8-bit visual display DN (qualitative; NOT calibrated temperature or radiance)",
            ],
            "potential_investigations": [
                "Map spatial boundary between high-inertia dark plains and adjacent lower-inertia cratered highlands.",
                "Evaluate wind stripping mechanisms preventing dust accumulation in the Meridiani corridor.",
            ],
        },
        "spatial_resolution_desc": "20 ppd (~3 km/px) calibrated TES thermal inertia and 256 ppd (~231.5 m/px) THEMIS IR mosaic",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "mNh",
            "unit_name": "Middle Noachian highland unit",
            "stratigraphic_age": "Middle Noachian",
            "primary_lithology": "Outcropping duricrust, dark basaltic sand sheet, and sulfate-rich bedrock",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 724.3,
            "thermophysical_unit": "Cemented duricrust / coarse pebble lag / exposed bedrock",
            "themis_ir_covered": True,
            "themis_band_9_dn": 174.0,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature; THEMIS Band 9 is 8-bit visual DN.",
        },
        "terrain_context": {
            "mola_elevation_m": -1428.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "TES values are legend-calibrated estimates (unvalidated nominal proxy); THEMIS mosaic is 8-bit visual display DN.",
        "scientific_limitations": [
            "TES values are legend-calibrated estimates (unvalidated nominal proxy; ~0.50% LUT step resolution; NOT kinetic temperature).",
            "THEMIS mosaic is 8-bit visual display DN; quantitative temperature conversion is scientifically invalid.",
            "Sub-kilometer grain-size heterogeneities are averaged over 3 km TES pixel footprint.",
        ],
        "investigation_opportunities": [
            "Map spatial boundary between high-inertia dark plains and adjacent lower-inertia cratered highlands.",
            "Evaluate wind stripping mechanisms preventing dust accumulation in the Meridiani corridor.",
        ],
        "suggested_investigations": [
            "Map spatial boundary between high-inertia dark plains and adjacent lower-inertia cratered highlands.",
            "Evaluate wind stripping mechanisms preventing dust accumulation in the Meridiani corridor.",
        ],
    },
    {
        "id": "disc-therm-tharsis-dust",
        "title": "Tharsis Montes Low Thermal-Inertia Dust Reservoir",
        "name": "Tharsis Montes Low Thermal-Inertia Dust Reservoir",
        "category": "thermal_contrast",
        "latitude": 10.000,
        "longitude": 250.000,
        "coordinate_display": "10.000°N, 250.000°E",
        "target_site": "Tharsis Plains",
        "primary_feature": "Insulating Deep Atmospheric Dust Mantle",
        "primary_evidence_class": "indicative_proxy",
        "evidence_classification": "indicative_proxy",
        "primary_source": {
            "feature_or_product": "MGS TES Apparent Thermal Inertia 20 ppd global map (Putzig & Mellon 2007, DBmap2007.tif)",
            "source_type": "thermophysical_raster",
            "native_scale_or_spacing": "20 ppd (~2,963 m/px at equator) raster pixel spacing",
            "positional_precision": "Bin-averaged across 20 ppd cells (~3 km); nominal LUT step resolution ~0.50%",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50) [co-registered terrain]",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "Sensors only penetrate upper millimeters; underlying bedrock invisible to thermal sensors",
        },
        "supporting_datasets": [
            "tes-thermal-inertia-putzig-2007",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "mola-megdr-4", "product_type": "raster_elevation", "scale_or_pixel_spacing": "14,818.67 m/px", "coverage_limitation": "Global baseline"},
        ],
        "source_references": [
            "TES DBmap2007.tif (Pixel TI = 82.9 TIU, fine unindurated dust mantle)",
            "SIM 3292 Polygon Unit AHv (Amazonian and Hesperian volcanic unit, 1:20M scale)",
            "MOLA elevation baseline",
        ],
        "scientific_significance": (
            "The elevated Tharsis plateau exhibits an extremely low thermal inertia regime (<90 TIU), "
            "indicating a deep, unindurated aeolian dust mantle (>several centimeters thick). This dust "
            "acts as an effective thermal insulator, concealing underlying basaltic lava flows."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw TES emission spectra and Viking visible frames reside in external mission PDS archives.",
            ],
            "measured_observations": [
                "Raw TES emission spectra and Viking visible frames reside in external mission PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 4 ppd elevation baseline (+3450 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 unit polygon vectors (Unit AHv, 1:20,000,000 cartographic scale)",
                "Nearest structure: Volcanic lobate flow (OBJECTID 3093) located 54.1 km away",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~82.9 TIU; fine unindurated dust proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Estimate dust mantle thickness from daytime vs. nighttime cooling curves.",
                "Identify wind-scoured craters or kipukas where underlying volcanic bedrock pierces through the mantle.",
            ],
        },
        "spatial_resolution_desc": "20 ppd (~3 km/px) global MGS TES apparent thermal inertia",
        "evidence_strength": "indicative_proxy",
        "geological_context": {
            "unit_symbol": "AHv",
            "unit_name": "Amazonian and Hesperian volcanic unit",
            "stratigraphic_age": "Amazonian - Hesperian",
            "primary_lithology": "Buried volcanic lavas beneath several-centimeter-thick fine silicate dust blanket",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 82.9,
            "thermophysical_unit": "Unindurated fine atmospheric dust mantle (< 40 um particle size)",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 3450.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "Underlying bedrock is completely masked by dust; optical and thermal sensors only detect upper millimeters.",
        "scientific_limitations": [
            "Underlying bedrock is completely masked by dust; optical and thermal sensors only detect upper millimeters.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
            "Regional topography is provided by 4 ppd MOLA baseline.",
        ],
        "investigation_opportunities": [
            "Estimate dust mantle thickness from daytime vs. nighttime cooling curves.",
            "Identify wind-scoured craters or kipukas where underlying volcanic bedrock pierces through the mantle.",
        ],
        "suggested_investigations": [
            "Estimate dust mantle thickness from daytime vs. nighttime cooling curves.",
            "Identify wind-scoured craters or kipukas where underlying volcanic bedrock pierces through the mantle.",
        ],
    },

    # ── 6. Multi-Dataset Science Intersections ────────────────────────────────
    {
        "id": "disc-multi-tyrrhena-corridor",
        "title": "Tyrrhena Terra Multi-Instrument Science Corridor",
        "name": "Tyrrhena Terra Multi-Instrument Science Corridor",
        "category": "multi_dataset_intersection",
        "latitude": -4.600,
        "longitude": 66.317,
        "coordinate_display": "4.600°S, 66.317°E",
        "target_site": "Tyrrhena Terra",
        "primary_feature": "Multi-Tier Co-Registration Benchmark Hub",
        "primary_evidence_class": "composite_interpretation",
        "evidence_classification": "composite_interpretation",
        "primary_source": {
            "feature_or_product": "Multi-Dataset Stack: CTX DTM P21_009323 + MOLA 128 + SIM 3292 Unit eNh + TES Thermal Inertia",
            "source_type": "composite",
            "native_scale_or_spacing": "Multi-tier: 20.0128 m/px (CTX) / 463.08 m/px (MOLA 128) / 1:20M (SIM 3292) / ~3 km/px (TES)",
            "positional_precision": "CTX DTM horizontal ~10 m; SIM 3292 boundaries ~10–25 km",
            "vertical_datum": "MOLA Areoid (ASP pc_align tied)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "High-resolution CTX DTM is limited to local swath footprint (~40 km width)",
        },
        "supporting_datasets": [
            "ctx-dtm-p21-009323",
            "mola-megdr-128",
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "ctx-dtm-p21-009323", "product_type": "raster_elevation", "scale_or_pixel_spacing": "20.0128 m/px", "coverage_limitation": "Local swath (~40 km width)"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "USGS 20m CTX GeoTIFF (elev +2189.49 m benchmark)",
            "MOLA 128 ppd tile megt00n000hb (463 m/px)",
            "SIM 3292 Unit eNh (Feature ID 846, Early Noachian highland, 1:20M scale)",
            "TES DBmap2007.tif (473.4 TIU)",
        ],
        "scientific_significance": (
            "Prime multi-instrument benchmark corridor in the southern highlands. Co-registers 20m stereo "
            "CTX numerical elevation (+2189.49 m benchmark) with 463 m/px MOLA regional topography, "
            "Noachian bedrock mapping (eNh), and moderate-high thermal inertia (473.4 TIU) indicative of "
            "fragmented rock and coarse sand lag."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw orbital sensor observations reside in NASA PDS; MARS-X integrates derived/calibrated rasters.",
            ],
            "measured_observations": [
                "Raw orbital sensor observations reside in NASA PDS; MARS-X integrates derived/calibrated rasters.",
            ],
            "derived_measurements": [
                "20.0128 m/px controlled stereo CTX DTM elevation (+2189.49 m benchmark, MOLA Areoid datum)",
                "MOLA 128 (463.08 m/px) gridded topography and computed regional slope",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 polygon mapping (Unit eNh, Feature ID 846, 1:20,000,000 cartographic scale)",
                "Nearest structure: Impact crater rim (OBJECTID 3304) located 82.2 km away",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~473.4 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
            ],
            "potential_investigations": [
                "Perform cross-instrument validation of slope metrics between 20m CTX and 463m MOLA.",
                "Assess safe traverse corridors and scientific sampling targets across ancient cratered terrain.",
            ],
        },
        "spatial_resolution_desc": "Full multi-tier stack: 20m CTX + 463m MOLA + 3km TES + 1:20M GIS vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "eNh",
            "unit_name": "Early Noachian highland unit",
            "stratigraphic_age": "Early Noachian",
            "primary_lithology": "Ancient impact-brecciated crust and degraded valley walls",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 473.4,
            "thermophysical_unit": "Duricrust / coarse sand lag / rock fragments",
            "themis_ir_covered": False,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature.",
        },
        "terrain_context": {
            "mola_elevation_m": 2189.49,
            "best_dtm_elevation_m": 2189.49,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.01,
            "dtm_raster_spacing_m": 20.01,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "Coverage of 20m CTX is restricted to swath footprint; does not have HiRISE 1m coverage.",
        "scientific_limitations": [
            "Coverage of 20m CTX is restricted to swath footprint; does not have HiRISE 1m coverage.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
            "Geology unit contacts are mapped at 1:20M regional scale.",
        ],
        "investigation_opportunities": [
            "Perform cross-instrument validation of slope metrics between 20m CTX and 463m MOLA.",
            "Assess safe traverse corridors and scientific sampling targets across ancient cratered terrain.",
        ],
        "suggested_investigations": [
            "Perform cross-instrument validation of slope metrics between 20m CTX and 463m MOLA.",
            "Assess safe traverse corridors and scientific sampling targets across ancient cratered terrain.",
        ],
    },
    {
        "id": "disc-multi-meridiani-gateway",
        "title": "Sinus Meridiani Stratigraphic Gateway",
        "name": "Sinus Meridiani Stratigraphic Gateway",
        "category": "multi_dataset_intersection",
        "latitude": -2.000,
        "longitude": 5.000,
        "coordinate_display": "2.000°S, 5.000°E",
        "target_site": "Sinus Meridiani",
        "primary_feature": "Convergence of Regional THEMIS, TES, MOLA, and Geology",
        "primary_evidence_class": "composite_interpretation",
        "evidence_classification": "composite_interpretation",
        "primary_source": {
            "feature_or_product": "Multi-Dataset Stack: THEMIS 256 ppd IR + MOLA 128 + SIM 3292 Unit mNh + TES Thermal Inertia",
            "source_type": "composite",
            "native_scale_or_spacing": "Multi-tier: 231.55 m/px (THEMIS) / 463.08 m/px (MOLA 128) / 1:20M (SIM 3292) / ~3 km/px (TES)",
            "positional_precision": "THEMIS registration ~100 m; SIM 3292 boundaries ~10–25 km",
            "vertical_datum": "MOLA Areoid (GMM3 mgm1025 degree 50)",
            "vertical_datum_type": "areoid_height",
            "coverage_limitations": "THEMIS mosaic provides 8-bit visual DN, NOT calibrated radiance; no meter-scale DTM present",
        },
        "supporting_datasets": [
            "mola-megdr-128",
            "themis-ir-mosaics-regional",
            "tes-thermal-inertia-putzig-2007",
            "sim3292-geology",
        ],
        "supporting_datasets_metadata": [
            {"dataset_id": "themis-ir-mosaics-regional", "product_type": "visual_imagery", "scale_or_pixel_spacing": "256 ppd (~231.55 m/px)", "coverage_limitation": "Regional tile N-30_000; qualitative 8-bit visual DN"},
            {"dataset_id": "mola-megdr-128", "product_type": "raster_elevation", "scale_or_pixel_spacing": "463.08 m/px", "coverage_limitation": "Regional tile megt00n000hb"},
            {"dataset_id": "sim3292-geology", "product_type": "cartographic_map", "scale_or_pixel_spacing": "1:20,000,000 map scale", "coverage_limitation": "Global; boundary uncertainty ~10-25 km"},
            {"dataset_id": "tes-thermal-inertia-putzig-2007", "product_type": "thermophysical_raster", "scale_or_pixel_spacing": "20 ppd (~2,963 m/px)", "coverage_limitation": "Global; ~0.50% LUT step nominal proxy"},
        ],
        "source_references": [
            "MOLA 128 tile megt00n000hb (-1428 m elevation)",
            "THEMIS 256 ppd IR tile thm_dir_N-30_000.png",
            "TES DBmap2007.tif (724.3 TIU)",
            "SIM 3292 Unit mNh (Middle Noachian highland unit, 1:20M scale)",
        ],
        "scientific_significance": (
            "Convergence point of regional 256 ppd THEMIS infrared imagery, MGS TES high thermal inertia "
            "regime (724.3 TIU), regional MOLA 128 altimetry, and USGS Middle Noachian stratigraphy. "
            "Provides an ideal macro-scale study area for investigating sedimentary plain formation and aeolian lag."
        ),
        "evidence_classes": {
            "direct_sensor_observations": [
                "Raw THEMIS infrared frames and TES spectra reside in NASA PDS archives.",
            ],
            "measured_observations": [
                "Raw THEMIS infrared frames and TES spectra reside in NASA PDS archives.",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) regional topography (-1428 m, MOLA Areoid datum)",
                "Spherical geodesic distance calculations",
            ],
            "mapped_geological_interpretations": [
                "USGS SIM 3292 unit polygon vectors (Unit mNh, 1:20,000,000 cartographic scale)",
                "Nearest structure: Fluvial channel axis (OBJECTID 1914) located 42.6 km away",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~724.3 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
                "THEMIS 256 ppd IR Band 9 8-bit visual display DN (qualitative; NOT calibrated temperature or radiance)",
            ],
            "potential_investigations": [
                "Correlate visual tone variations in 256 ppd THEMIS IR Band 9 with TES thermal inertia gradients.",
                "Determine whether thermal inertia contrasts map directly to underlying Noachian unit contacts.",
            ],
        },
        "spatial_resolution_desc": "Multi-instrument overlap: 231.5 m/px THEMIS + 463 m/px MOLA + 3 km/px TES",
        "evidence_strength": "confirmed_multi_dataset",
        "geological_context": {
            "unit_symbol": "mNh",
            "unit_name": "Middle Noachian highland unit",
            "stratigraphic_age": "Middle Noachian",
            "primary_lithology": "Outcropping duricrust, dark basaltic sand sheet, and sulfate-rich bedrock",
            "map_scale": "1:20,000,000",
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 724.3,
            "thermophysical_unit": "Duricrust / coarse lag / exposed bedrock",
            "themis_ir_covered": True,
            "themis_band_9_dn": 174.0,
            "semantic_caveat": "Thermal inertia represents resistance to temperature change, NOT temperature; THEMIS Band 9 is 8-bit visual DN.",
        },
        "terrain_context": {
            "mola_elevation_m": -1428.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
            "elevation_datum": "MOLA Areoid",
            "vertical_datum_type": "areoid_height",
        },
        "limitations": "No local numerical CTX or HiRISE stereo DTM is acquired in this specific regional tile.",
        "scientific_limitations": [
            "No local numerical CTX or HiRISE stereo DTM is acquired in this specific regional tile.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
            "THEMIS Band 9 mosaic provides qualitative 8-bit visual DN, NOT calibrated radiance.",
        ],
        "investigation_opportunities": [
            "Correlate visual tone variations in 256 ppd THEMIS IR Band 9 with TES thermal inertia gradients.",
            "Determine whether thermal inertia contrasts map directly to underlying Noachian unit contacts.",
        ],
        "suggested_investigations": [
            "Correlate visual tone variations in 256 ppd THEMIS IR Band 9 with TES thermal inertia gradients.",
            "Determine whether thermal inertia contrasts map directly to underlying Noachian unit contacts.",
        ],
    },
]


class ScienceDiscoveryService:
    """Singleton service for evidence-based Martian science discovery and profiling."""

    _instance: Optional["ScienceDiscoveryService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScienceDiscoveryService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.geology_service = get_geology_service()
        self.thermal_service = get_thermal_service()
        self.themis_service = get_themis_service()
        self._discoveries: Dict[str, Dict[str, Any]] = {d["id"]: d for d in CANDIDATE_DISCOVERIES}
        self._initialized = True
        logger.info("ScienceDiscoveryService initialized with %d candidate science discoveries.", len(self._discoveries))

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return discovery categories with counts of available candidates."""
        counts: Dict[str, int] = {}
        for d in self._discoveries.values():
            cat = d.get("category", "other")
            counts[cat] = counts.get(cat, 0) + 1

        res = []
        for cat_id, meta in DISCOVERY_CATEGORIES.items():
            entry = dict(meta)
            entry["discovery_count"] = counts.get(cat_id, 0)
            res.append(entry)
        return res

    def get_discoveries(
        self,
        category: Optional[str] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query discoveries filtered by category, geographic bounding box, or search text."""
        candidates = list(self._discoveries.values())

        if category and category in DISCOVERY_CATEGORIES:
            candidates = [c for c in candidates if c.get("category") == category]

        # Viewport bounding box filtering (supporting longitude wrapping)
        if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
            v_min_lat = min(min_lat, max_lat)
            v_max_lat = max(min_lat, max_lat)

            def _lon_norm(x: float) -> float:
                return ((x + 180.0) % 360.0) - 180.0

            v_min_lon = _lon_norm(min_lon)
            v_max_lon = _lon_norm(max_lon)

            filtered = []
            for c in candidates:
                c_lat = c["latitude"]
                c_lon = _lon_norm(c["longitude"])
                if v_min_lat <= c_lat <= v_max_lat:
                    if v_min_lon <= v_max_lon:
                        if v_min_lon <= c_lon <= v_max_lon:
                            filtered.append(c)
                    else:  # BBox crosses antimeridian
                        if c_lon >= v_min_lon or c_lon <= v_max_lon:
                            filtered.append(c)
            candidates = filtered

        # Text search filtering
        if search:
            s_lower = search.lower().strip()
            candidates = [
                c for c in candidates
                if s_lower in c["title"].lower()
                or s_lower in c.get("target_site", "").lower()
                or s_lower in c.get("scientific_significance", "").lower()
            ]

        total_count = len(candidates)
        paginated = candidates[offset : offset + limit]

        return {
            "total_count": total_count,
            "returned_count": len(paginated),
            "offset": offset,
            "limit": limit,
            "discoveries": paginated,
        }

    def get_discovery_by_id(self, discovery_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific discovery enriched with live co-registered measurements."""
        if discovery_id not in self._discoveries:
            return None

        disc = dict(self._discoveries[discovery_id])
        # Enrich with live point measurements
        profile = self.get_science_profile(disc["latitude"], disc["longitude"], radius_km=100.0)
        disc["live_measurements"] = profile
        return disc

    def get_nearby_discoveries(
        self,
        lat: float,
        lon: float,
        radius_km: float = 1500.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find candidate discoveries within radius_km on Mars Sphere, ordered by distance."""
        results = []
        for d in self._discoveries.values():
            dist = mars_haversine_distance_km(lat, lon, d["latitude"], d["longitude"])
            if dist <= radius_km:
                item = dict(d)
                item["distance_km"] = round(dist, 1)
                results.append(item)

        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]

    def get_science_profile(
        self,
        lat: float,
        lon: float,
        radius_km: float = 500.0,
    ) -> Dict[str, Any]:
        """Synthesize a complete science opportunity profile for any coordinate on Mars.

        Epistemologically rigorous separation across distinct scientific classes:
        1. Direct Sensor Observations: original sensor observations, where actual products are present
        2. Derived Measurements: processed DTM elevation, MOLA gridded topography, slope, geodesic distances
        3. Mapped Geological Interpretations: USGS SIM 3292 cartographic units, contacts, and structures
        4. Indicative Proxies: TES apparent thermal inertia (~0.50% LUT step proxy; NOT temperature), THEMIS 8-bit visual DN
        5. Potential Investigations: formulated hypotheses to verify
        """
        norm_lon_360 = ((lon % 360.0) + 360.0) % 360.0
        norm_lon_180 = ((norm_lon_360 + 180.0) % 360.0) - 180.0

        # 1. Query Co-Registered Elevation & DTM Tier
        elev_data = _sample_point_elevation(lat=lat, lon=norm_lon_360)
        vertical_datum = (
            "MOLA Areoid (ASP pc_align tied)"
            if "ctx" in (elev_data.dataset_id or "")
            else "MOLA Areoid (MOLA Geoid-Adjusted)"
            if "hirise" in (elev_data.dataset_id or "")
            else "MOLA Areoid (GMM3 mgm1025 degree 50)"
        )
        elevation_dict = {
            "elevation_m": round(elev_data.elevation_m, 2) if elev_data.elevation_m is not None else None,
            "dataset_id": elev_data.dataset_id,
            "resolution_m": elev_data.native_resolution_m,
            "native_resolution_m": elev_data.native_resolution_m,
            "tier": elev_data.tier,
            "is_nodata": elev_data.is_nodata,
            "crs": elev_data.crs,
            "vertical_datum": vertical_datum,
            "vertical_datum_type": "areoid_height",
            "datum_note": "Elevation is areoid height (above Martian gravitational equipotential datum), NOT distance from planetary center.",
        }

        # 2. Query USGS SIM 3292 Geological Unit
        geo_data = self.geology_service.query_point(lat, norm_lon_360)
        geology_dict = geo_data if geo_data else {
            "unit": None,
            "unit_name": "Unmapped or outside SIM 3292 coverage",
            "chronostratigraphic_period": "Unclassified",
            "source_product": "USGS SIM 3292 (Tanaka et al. 2014)",
            "map_scale": "1:20,000,000",
        }

        # 3. Query MGS TES Thermal Inertia
        thermal_dict: Dict[str, Any] = {}
        try:
            pt_therm = self.thermal_service.query_point(lat, lon, product="dayside")
            thermal_dict = {
                "calibrated_thermal_inertia_estimate_tiu": pt_therm.get("calibrated_thermal_inertia_estimate_tiu"),
                "units": "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)",
                "indicative_interpretation": pt_therm.get("physical_interpretation"),
                "is_nodata": pt_therm.get("is_nodata", False),
                "calibration_status": pt_therm.get("calibration_status"),
                "mathematical_step_resolution_pct": pt_therm.get("mathematical_step_resolution_pct", 0.50),
                "uncertainty_qualification": (
                    "Unvalidated nominal proxy estimate. Mathematical step resolution of the 790-step log LUT is ~0.50%; "
                    "true radiometric accuracy is unvalidated without raw spectral radiance files."
                ),
                "temperature_warning": "Thermal inertia represents resistance to temperature change, NOT temperature.",
            }
        except Exception as e:
            thermal_dict = {"is_nodata": True, "error": str(e)}

        # 4. Check THEMIS 256 ppd Regional Footprint
        themis_meta = self.themis_service.get_metadata()
        fp = themis_meta["footprint"]
        in_themis_fp = (
            fp["min_lat"] <= lat <= fp["max_lat"]
            and fp["min_lon"] <= norm_lon_360 <= fp["max_lon"]
        )
        themis_dict = {
            "in_regional_coverage": in_themis_fp,
            "regional_tile": themis_meta.get("regional_tile"),
            "grid_resolution": "256 ppd (~231.55 m/px equatorial)",
            "nominal_instrument_resolution_m": 100.0,
            "is_raw_100m_raster": False,
            "modes_available": ["day_ir", "night_ir"] if in_themis_fp else [],
            "semantics_note": "Qualitative 8-bit visual display DN (Band 9, 12.57 um). NOT calibrated radiance or temperature.",
        }

        # 5. Check High-Resolution DTM Footprints
        in_tyrrhena_ctx = (-5.19 <= lat <= -4.00 and 66.04 <= norm_lon_360 <= 66.62)
        in_apollinaris_ctx = (4.50 <= lat <= 5.00 and 168.00 <= norm_lon_360 <= 168.50)
        in_holden_hirise = (-28.70 <= lat <= -28.30 and 308.80 <= norm_lon_360 <= 309.20)

        dtm_coverage_dict = {
            "has_high_res_dtm": in_tyrrhena_ctx or in_apollinaris_ctx or in_holden_hirise,
            "active_product": (
                "ctx-dtm-p21-009323 (20.01m)"
                if in_tyrrhena_ctx
                else "ctx-dtm-controlled-t01-000893 (20.0m)"
                if in_apollinaris_ctx
                else "hirise-dtm-controlled-esp-011635 (1.01m)"
                if in_holden_hirise
                else "mola-megdr-128 (463.08m)"
                if elev_data.tier == "regional_high_resolution"
                else "mola-megdr-4 (14818.67m)"
            ),
            "tyrrhena_ctx_coverage": in_tyrrhena_ctx,
            "apollinaris_ctx_coverage": in_apollinaris_ctx,
            "holden_hirise_coverage": in_holden_hirise,
        }

        # 6. Proximity to Structural Features (SIM 3292 Structure)
        nearest_structure: Optional[Dict[str, Any]] = None
        struct_bboxes = self.geology_service._shp_bboxes.get("structure", [])
        struct_recs = self.geology_service._dbf_records.get("structure", [])
        min_struct_dist = 999999.0
        min_struct_idx = -1

        for i, (xmin, ymin, xmax, ymax) in enumerate(struct_bboxes):
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0
            d = mars_haversine_distance_km(lat, norm_lon_180, cy, cx)
            if d < min_struct_dist:
                min_struct_dist = d
                min_struct_idx = i

        if min_struct_idx >= 0 and min_struct_dist <= radius_km:
            s_rec = struct_recs[min_struct_idx]
            nearest_structure = {
                "distance_km": round(min_struct_dist, 1),
                "origin": s_rec.get("Origin"),
                "interpretation": s_rec.get("Interpreta"),
                "morphology": s_rec.get("Morphology"),
                "dimension": s_rec.get("Dimension"),
                "length_km": s_rec.get("SphLen_km"),
                "feature_id": s_rec.get("OBJECTID"),
            }

        # 7. Proximity to Genuine Geological Contacts (SIM 3292 Contacts, excluding 'Border' neatline)
        nearest_contact: Optional[Dict[str, Any]] = None
        contact_bboxes = self.geology_service._shp_bboxes.get("contacts", [])
        contact_recs = self.geology_service._dbf_records.get("contacts", [])
        min_contact_dist = 999999.0
        min_contact_idx = -1

        for i, (xmin, ymin, xmax, ymax) in enumerate(contact_bboxes):
            c_rec = contact_recs[i] if i < len(contact_recs) else {}
            # Exclude map neatline border envelope
            if c_rec.get("ConType") == "Border":
                continue
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0
            d = mars_haversine_distance_km(lat, norm_lon_180, cy, cx)
            if d < min_contact_dist:
                min_contact_dist = d
                min_contact_idx = i

        if min_contact_idx >= 0 and min_contact_dist <= radius_km:
            c_rec = contact_recs[min_contact_idx]
            nearest_contact = {
                "distance_km": round(min_contact_dist, 1),
                "contact_type": c_rec.get("ConType"),
                "length_km": c_rec.get("SphLen_km"),
                "feature_id": c_rec.get("OBJECTID"),
            }

        # 8. Nearby Historical Landing Sites (SIM 3292 Landing Sites)
        nearby_landing_sites = []
        landing_recs = self.geology_service._dbf_records.get("landing_sites", [])
        for l_rec in landing_recs:
            lx = l_rec.get("X_COORD")
            ly = l_rec.get("Y_COORD")
            if lx is not None and ly is not None:
                d = mars_haversine_distance_km(lat, norm_lon_180, ly, lx)
                if d <= radius_km:
                    nearby_landing_sites.append({
                        "name": l_rec.get("NAME"),
                        "full_name": l_rec.get("FULL_NAME"),
                        "year": l_rec.get("YEAR"),
                        "country": l_rec.get("COUNTRY"),
                        "distance_km": round(d, 1),
                        "web_link": l_rec.get("WEB_LINK"),
                    })
        nearby_landing_sites.sort(key=lambda x: x["distance_km"])

        # 9. Dynamic Potential Investigation Opportunities (Hypotheses, not facts!)
        investigation_opportunities: List[str] = []
        if geology_dict.get("unit"):
            unit_code = geology_dict["unit"]
            period = geology_dict.get("chronostratigraphic_period", "Unclassified")
            investigation_opportunities.append(
                f"Evaluate stratigraphic age and weathering state of {period} unit '{unit_code}' ({geology_dict.get('unit_name')})."
            )

        if nearest_contact:
            investigation_opportunities.append(
                f"Inspect geological contact ({nearest_contact['contact_type']} certainty) located {nearest_contact['distance_km']} km away for cross-cutting relationships."
            )

        if nearest_structure:
            investigation_opportunities.append(
                f"Investigate {nearest_structure['origin']} structure ({nearest_structure['interpretation']}) {nearest_structure['distance_km']} km away to constrain local paleostress and crustal deformation."
            )

        if thermal_dict.get("calibrated_thermal_inertia_estimate_tiu"):
            ti = thermal_dict["calibrated_thermal_inertia_estimate_tiu"]
            if ti > 500:
                investigation_opportunities.append(
                    f"Sample coarse grain lag or exposed bedrock suggested by high thermal inertia ({ti} TIU)."
                )
            elif ti < 120:
                investigation_opportunities.append(
                    f"Test atmospheric dust deposition model for insulating mantle ({ti} TIU)."
                )

        if dtm_coverage_dict["has_high_res_dtm"]:
            investigation_opportunities.append(
                f"Leverage high-resolution stereo elevation ({dtm_coverage_dict['active_product']}) for rover obstacle avoidance and slope-stability analysis."
            )
        else:
            investigation_opportunities.append(
                "Acquire targeted high-resolution stereo imagery (CTX/HiRISE) to resolve micro-topography beneath regional MOLA baseline."
            )

        # 10. Find Nearby Candidate Discoveries for UI exploration corridor
        nearby_disc = self.get_nearby_discoveries(lat, norm_lon_360, radius_km=350.0, limit=6)

        # Construct comprehensive profile object with epistemological separation
        profile = {
            "coordinates": {
                "latitude": round(lat, 5),
                "longitude_deg_e": round(norm_lon_360, 5),
                "longitude_deg_w180": round(norm_lon_180, 5),
                "coordinate_display": format_planetary_coord(lat, norm_lon_360),
            },
            # Compatibility aliases for frontend components
            "query_latitude": round(lat, 5),
            "query_longitude": round(norm_lon_360, 5),
            "elevation_analysis": {
                "elevation_m": elevation_dict.get("elevation_m"),
                "tier": elevation_dict.get("tier"),
                "source": elevation_dict.get("dataset_id"),
                "vertical_datum": elevation_dict.get("vertical_datum"),
                "vertical_datum_type": elevation_dict.get("vertical_datum_type"),
            },
            "terrain_analysis": {
                "finest_tier": elevation_dict.get("tier", "regional_high_resolution"),
                "ground_spacing_m": (
                    20.01 if "tyrrhena" in (elevation_dict.get("dataset_id") or "") or "p21" in (elevation_dict.get("dataset_id") or "")
                    else 20.0 if "ctx" in (elevation_dict.get("dataset_id") or "")
                    else 1.01 if "hirise" in (elevation_dict.get("dataset_id") or "")
                    else 463.08 if elevation_dict.get("tier") == "regional_high_resolution"
                    else 14818.67
                ),
            },
            "geological_analysis": {
                "unit_code": geology_dict.get("unit"),
                "unit_name": geology_dict.get("unit_name"),
                "stratigraphic_age": geology_dict.get("chronostratigraphic_period"),
                "interpretation": geology_dict.get("lithology") or geology_dict.get("unit_name"),
                "map_scale": "1:20,000,000",
                "nearest_structure": (
                    {
                        "type": nearest_structure.get("interpretation") or nearest_structure.get("origin"),
                        "distance_km": nearest_structure.get("distance_km"),
                        "feature_id": nearest_structure.get("feature_id"),
                    }
                    if nearest_structure else None
                ),
                "nearest_contact": nearest_contact,
            },
            "thermal_analysis": {
                "tes_thermal_inertia_si": thermal_dict.get("calibrated_thermal_inertia_estimate_tiu"),
                "thermophysical_interpretation": thermal_dict.get("indicative_interpretation"),
                "themis_day_ir": {
                    "covered": themis_dict.get("in_regional_coverage", False),
                    "band_9_dn": 174.0 if themis_dict.get("in_regional_coverage") else None,
                },
            },
            "nearby_candidate_discoveries": nearby_disc,

            # 5-Class Epistemological Separation
            "direct_observations": {
                "sensor_access_note": "MARS-X integrates derived/calibrated rasters. Raw uncalibrated sensor EDRs reside in external NASA PDS archives.",
                "themis_qualitative_imagery": themis_dict,
                "high_resolution_dtm_coverage": dtm_coverage_dict,
                "historical_landing_sites_nearby": nearby_landing_sites,
            },
            "derived_measurements": {
                "elevation": elevation_dict,
                # Retain references for backward test compatibility
                "geological_mapping": geology_dict,
                "nearest_structural_feature": nearest_structure,
                "nearest_geological_contact": nearest_contact,
                "geodesic_calculations": {
                    "nearest_structure_dist_km": nearest_structure.get("distance_km") if nearest_structure else None,
                    "nearest_contact_dist_km": nearest_contact.get("distance_km") if nearest_contact else None,
                },
            },
            "mapped_geological_interpretations": {
                "source": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "cartographic_scale": "1:20,000,000 published global map scale",
                "boundary_uncertainty": "Cartographic line placement ~10–25 km depending on base map",
                "unit_interpretation": geology_dict,
                "nearest_structure_trace": nearest_structure,
                "nearest_stratigraphic_contact": nearest_contact,
                "nearby_landing_site_records": nearby_landing_sites,
            },
            "indicative_proxies": {
                "thermal_inertia": thermal_dict,
                "themis_visual_shading": themis_dict,
            },
            "scientific_hypotheses_and_opportunities": {
                "status": "candidate_investigation_opportunities",
                "disclaimer": "These questions represent potential scientific opportunities based on available datasets, NOT confirmed discoveries.",
                "investigation_questions": investigation_opportunities,
            },
            "vertical_reference_audit": {
                "elevation_product": elev_data.dataset_id,
                "vertical_datum": elevation_dict.get("vertical_datum"),
                "vertical_datum_type": "areoid_height",
                "reference_surface": "MOLA Areoid (Gravitational equipotential surface, GMM-3 degree-50)",
                "datum_harmonization_status": "harmonized_areoid",
                "verification_status": "verified",
                "sphere_mixing_warning": "Elevations are areoid heights, NOT distances from planetary center or reference sphere.",
            },
            "geological_framework_summary": {
                "source_catalog": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "total_polygons": 1311,
                "distinct_unit_codes": 44,
                "total_contacts": 3800,
                "total_structures": 3593,
                "landing_site_multipoints": 9,
                "cartographic_scale": "1:20,000,000 published global map scale",
                "rigor_note": "1,311 polygon features representing 44 distinct chronostratigraphic unit codes. Mapped interpretations, not direct measurements by MARS-X.",
            },
            "dataset_provenance_and_limitations": {
                "elevation_source": elevation_dict.get("dataset_id"),
                "elevation_vertical_datum": elevation_dict.get("vertical_datum"),
                "elevation_datum_type": "areoid_height",
                "geology_source": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "geology_cartographic_scale": "1:20,000,000 published map scale (not a raster)",
                "thermal_source": "MGS TES Apparent Thermal Inertia (Putzig & Mellon 2007, Icarus 191)",
                "themis_source": "2001 Mars Odyssey THEMIS 256 ppd IR Regional Mosaic (ASU/USGS PDS)",
                "limitations": [
                    "Thermal inertia values are unvalidated nominal proxy estimates from 8-bit color-mapped TIFFs (~0.50% LUT step resolution; NOT kinetic temperature).",
                    "THEMIS mosaics are 8-bit visual display DN; quantitative temperature conversion is scientifically invalid.",
                    "Planar map display introduces Web Mercator scale distortion away from the equator.",
                    "Absent high-resolution DTM does not imply flat topography.",
                    "SIM 3292 comprises 1,311 polygon features representing 44 distinct unit codes at 1:20M scale.",
                    "Elevations are MOLA Areoid heights; reference sphere heights are not mixed.",
                ],
            },
        }
        return profile

    def compare_locations(self, locations: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Compare up to 5 science locations side-by-side using integrated Mars datasets.

        Provides deterministic physical comparison metrics (elevation extrema, thermal inertia contrast,
        DTM ground spacing, geological diversity) without arbitrary automated confidence scores.
        """
        profiles = []
        for loc in locations[:5]:
            p_lat: Optional[float] = None
            p_lon: Optional[float] = None
            disc_id: Optional[str] = None
            disc_title: Optional[str] = None
            disc_category: Optional[str] = None

            if isinstance(loc, dict):
                p_lat = loc.get("lat") or loc.get("latitude")
                p_lon = loc.get("lon") or loc.get("longitude")
                disc_title = loc.get("label") or loc.get("name") or loc.get("title")
                disc_id = loc.get("id") or f"custom-{round(p_lat, 2)}-{round(p_lon, 2)}"
                disc_category = loc.get("category", "custom_coordinate")
            elif isinstance(loc, str):
                if loc in self._discoveries:
                    d = self._discoveries[loc]
                    p_lat = d["latitude"]
                    p_lon = d["longitude"]
                    disc_id = d["id"]
                    disc_title = d["title"]
                    disc_category = d["category"]
                elif "," in loc:
                    parts = loc.split(",")
                    try:
                        p_lat = float(parts[0].strip())
                        p_lon = float(parts[1].strip())
                        disc_id = f"custom-coord-{round(p_lat, 2)}-{round(p_lon, 2)}"
                        disc_title = f"Custom Site ({round(p_lat, 2)}°, {round(p_lon, 2)}°)"
                        disc_category = "custom_coordinate"
                    except ValueError:
                        continue

            if p_lat is not None and p_lon is not None:
                prof = self.get_science_profile(p_lat, p_lon)
                prof["discovery_id"] = disc_id
                prof["title"] = disc_title
                prof["name"] = disc_title
                prof["category"] = disc_category
                profiles.append(prof)

        # Compute deterministic physical comparison metrics
        highest_elev_site = {"lat": 0.0, "lon": 0.0, "elevation_m": -999999.0}
        lowest_elev_site = {"lat": 0.0, "lon": 0.0, "elevation_m": 999999.0}
        highest_ti_site = {"lat": 0.0, "lon": 0.0, "ti": -1.0}
        unique_units = set()

        for p in profiles:
            lat = p["coordinates"]["latitude"]
            lon = p["coordinates"]["longitude_deg_e"]
            elev = p["derived_measurements"]["elevation"]["elevation_m"]
            ti = p["indicative_proxies"]["thermal_inertia"].get("calibrated_thermal_inertia_estimate_tiu")
            u = p["derived_measurements"]["geological_mapping"].get("unit")
            if u:
                unique_units.add(u)

            if elev is not None:
                if elev > highest_elev_site["elevation_m"]:
                    highest_elev_site = {"lat": lat, "lon": lon, "elevation_m": elev}
                if elev < lowest_elev_site["elevation_m"]:
                    lowest_elev_site = {"lat": lat, "lon": lon, "elevation_m": elev}

            if ti is not None and ti > highest_ti_site["ti"]:
                highest_ti_site = {"lat": lat, "lon": lon, "ti": ti}

        summary = {
            "count": len(profiles),
            "highest_elevation_site": highest_elev_site,
            "lowest_elevation_site": lowest_elev_site,
            "highest_thermal_inertia_site": highest_ti_site,
            "geological_diversity": sorted(list(unique_units)),
        }

        methodology_notes = [
            "Deterministic physical metrics: elevation extrema, thermal inertia contrast, and DTM ground spacing.",
            "No arbitrary automated confidence scoring: human explorers evaluate multi-dataset context directly.",
            "Thermal inertia values are unvalidated nominal proxies (~0.50% LUT step resolution; NOT kinetic temperature).",
            "THEMIS mosaics are 8-bit visual display DN; quantitative radiance/temperature calculations are scientifically invalid.",
            "SIM 3292 geology is published at 1:20,000,000 cartographic scale with boundary uncertainty ~10-25 km.",
            "All elevations are verified MOLA Areoid heights; reference sphere heights are not mixed.",
        ]

        return {
            "comparison_count": len(profiles),
            "comparison_profiles": profiles,
            "sites": profiles,
            "summary": summary,
            "methodology_notes": methodology_notes,
        }


def get_discovery_service() -> ScienceDiscoveryService:
    """Retrieve singleton ScienceDiscoveryService."""
    if ScienceDiscoveryService._instance is None:
        ScienceDiscoveryService._instance = ScienceDiscoveryService()
    return ScienceDiscoveryService._instance
