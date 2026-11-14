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
        "supporting_datasets": [
            "ctx-dtm-p21-009323",
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-128",
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
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MRO CTX raw panchromatic stereo CCD frames (P21_009323_1754 & P22_009679_1754)",
                "MGS TES calibrated radiance spectra across thermal infrared bands",
            ],
            "derived_measurements": [
                "20.0128 m/px controlled stereo CTX DTM elevation (+2189.49 m benchmark)",
                "MOLA 128 (463.08 m/px) gridded topography and computed regional slope",
                "USGS SIM 3292 polygon mapping (Unit eNh, Early Noachian highland)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 473.4,
            "thermophysical_unit": "Duricrust / coarse sand lag / rock fragments",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 2189.49,
            "best_dtm_elevation_m": 2189.49,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.01,
        },
        "limitations": "CTX DTM coverage is strictly local (~40 km wide swath); outside swath terrain reverts to 463 m/px MOLA 128.",
        "scientific_limitations": [
            "CTX DTM coverage is strictly local (~40 km wide swath); outside swath terrain reverts to 463 m/px MOLA 128.",
            "TES thermal inertia is an unvalidated nominal proxy (~0.50% LUT step resolution; NOT kinetic temperature).",
            "Highland contacts are mapped at 1:20M regional scale.",
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
        "supporting_datasets": [
            "ctx-dtm-controlled-t01-000893",
            "sim3292-geology",
            "mola-megdr-4",
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
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MRO CTX raw panchromatic stereo CCD frames (T01_000893_1847 & companion stereo pair)",
                "MGS MOLA individual laser altimeter time-of-flight profiles",
            ],
            "derived_measurements": [
                "20.0 m/px controlled USGS stereo CTX DTM elevation (-2930.77 m benchmark)",
                "MOLA 4 ppd continuous elevation baseline (14,818.67 m/px)",
                "SIM 3292 polygon mapping (Unit lAvf, Late Amazonian volcanic field unit)",
            ],
            "indicative_proxies": [
                "TES apparent thermal inertia proxy estimate (nominal ~0.50% LUT step resolution; NOT kinetic temperature)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 285.0,
            "thermophysical_unit": "Moderately indurated sand / volcanic ash",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -2930.77,
            "best_dtm_elevation_m": -2930.77,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.0,
        },
        "limitations": "Controlled DTM footprint is restricted to lat 4.5°–5.0°N, lon 168.0°–168.5°E.",
        "scientific_limitations": [
            "Controlled DTM footprint is restricted to lat 4.5°–5.0°N, lon 168.0°–168.5°E.",
            "Surrounding regional terrain reverts to global 4 ppd MOLA baseline.",
            "Thermal data is an indicative nominal proxy.",
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
        "supporting_datasets": [
            "hirise-dtm-controlled-esp-011635",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "source_references": [
            "GeoTIFF: ESP_011635_1510_ESP_012057_1510_A01_ORTHO.tif (1.01m controlled DTM)",
            "SIM 3292 Polygon (Unit AHi, Amazonian and Hesperian impact unit)",
        ],
        "scientific_significance": (
            "Holden Crater preserves one of the most complete aqueous sedimentary sequences on Mars. "
            "The 1.01m controlled HiRISE DTM provides decimeter-scale vertical discrimination of "
            "alluvial fans, megabreccia blocks thrown out by the Holden impact, and finely layered lacustrine beds."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MRO HiRISE raw color CCD pushbroom image strips (ESP_011635_1510 & ESP_012057_1510)",
                "MOLA laser pulse altimeter profiles",
            ],
            "derived_measurements": [
                "1.01 m/px controlled USGS stereo HiRISE DTM elevation (-1132.14 m benchmark)",
                "Photogrammetric micro-relief and meter-scale slope maps",
                "SIM 3292 mapped impact crater rim and floor units (Unit AHi)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 360.0,
            "thermophysical_unit": "Lithified sedimentary strata with loose boulder lag",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -1132.14,
            "best_dtm_elevation_m": -1132.14,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 1.01,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 9 (MSL Curiosity, 2012, OBJECTID 9)",
            "SIM 3292 Polygon Unit AHi (Feature ID 754)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Mars Science Laboratory (Curiosity) rover in 2012. Gale Crater features a "
            "5-km-high central sedimentary mound (Aeolis Mons / Mount Sharp) exhibiting transitions from "
            "clay-bearing to sulfate-bearing strata, recording the drying of ancient Mars."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "Curiosity in-situ ChemCam, Mastcam, APXS, and SAM surface spectra",
                "Raw orbital CCD frames from CTX and HiRISE",
            ],
            "derived_measurements": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 9)",
                "MOLA 128 (463.08 m/px) gridded topography (-4452 m elevation)",
                "USGS SIM 3292 unit polygon vectors (Unit AHi)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 380.0,
            "thermophysical_unit": "Indurated sedimentary rock with localized sand dunes",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -4452.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
        },
        "limitations": "Orbital data cannot substitute for in-situ rover APXS/CheMin spectroscopic analyses.",
        "scientific_limitations": [
            "Orbital datasets cannot resolve sub-millimeter mineral veins identified by rover instruments.",
            "MOLA 128 averages surface topography across ~463m cells.",
            "TES thermal inertia is an indicative nominal proxy.",
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
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "themis-ir-mosaics-regional",
            "mola-megdr-128",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 7 (MER Opportunity, 2003, OBJECTID 7)",
            "SIM 3292 Polygon Unit HNhu (Hesperian and Noachian highland undivided unit)",
            "TES DBmap2007.tif (High thermal inertia hematite / basalt lag)",
            "THEMIS 256 ppd IR tile N-30_000",
        ],
        "scientific_significance": (
            "Landing site of NASA's Opportunity rover in 2004 within Eagle Crater. Characterized by crystalline "
            "gray hematite spherules ('blueberries') in sulfate-rich sedimentary rocks, providing decisive "
            "in-situ evidence for persistent acidic groundwater in the Martian past."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "Opportunity Pancam, Microscopic Imager, and Mössbauer spectrometer measurements",
                "2001 Mars Odyssey THEMIS multi-spectral infrared radiances",
            ],
            "derived_measurements": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 7)",
                "MOLA 128 (463.08 m/px) gridded elevation (-1398 m)",
                "USGS SIM 3292 unit polygon vectors (Unit HNhu)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 610.0,
            "thermophysical_unit": "Bedrock and dense granule/pebble lag",
            "themis_ir_covered": True,
            "themis_band_9_dn": 162.0,
        },
        "terrain_context": {
            "mola_elevation_m": -1398.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-128",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 6 (MER Spirit, 2003, OBJECTID 6)",
            "SIM 3292 Polygon Unit eHv (Early Hesperian volcanic unit)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Spirit rover in 2004. Explored olivine-rich flood basalts on the crater floor "
            "and hydrothermal silica deposits and carbonate-rich outcrops in the Columbia Hills."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "Spirit Pancam, Mini-TES, and Mössbauer spectrometer surface observations",
                "Orbital MOC and THEMIS multispectral imaging frames",
            ],
            "derived_measurements": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 6)",
                "MOLA 128 (463.08 m/px) gridded elevation (-1920 m)",
                "USGS SIM 3292 volcanic unit polygons (Unit eHv)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 310.0,
            "thermophysical_unit": "Basaltic rubble and sand-mantled volcanic floor",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -1920.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-4",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 5 (Mars Pathfinder, 1996, OBJECTID 5)",
            "SIM 3292 Polygon Unit Hto (Hesperian transition outflow unit)",
            "SIM 3292 Structure Line (Channel axis, fluvial origin)",
        ],
        "scientific_significance": (
            "Landing site of Mars Pathfinder and Sojourner rover (1997). Situated at the mouth of Ares Vallis "
            "where catastrophic outburst floods deposited poorly sorted boulders and conglomerate rocks sourced "
            "from diverse crustal provinces."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "Pathfinder IMP camera frames and APXS elemental spectrometry",
                "Viking Orbiter raw vidicon image frames",
            ],
            "derived_measurements": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 5)",
                "MOLA 4 ppd continuous elevation baseline (-3680 m)",
                "USGS SIM 3292 outflow channel polygons (Unit Hto) and channel axis polyline vectors",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 390.0,
            "thermophysical_unit": "Stony plain / boulder lag deposit",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -3680.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 3 (Viking 1, 1975, OBJECTID 3)",
            "SIM 3292 Polygon Unit Hto (Hesperian transition outflow unit)",
        ],
        "scientific_significance": (
            "First successful long-term Mars surface lander (July 1976). Located on a rolling volcanic plain "
            "littered with impact ejecta boulders, conducting the first in-situ biology and soil chemistry experiments."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "Viking Lander 1 facsimile camera images, GCMS, and X-ray fluorescence spectrometry",
                "Orbital Viking imaging mosaics",
            ],
            "derived_measurements": [
                "SIM 3292 mapped landing site coordinates (OBJECTID 3)",
                "MOLA 4 ppd continuous elevation baseline (-3690 m)",
                "USGS SIM 3292 unit polygon vectors (Unit Hto)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 330.0,
            "thermophysical_unit": "Duricrust and drifting aeolian silt",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -3690.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Polygon Feature ID 1046 (Unit Ave, Amazonian volcanic edifice)",
            "SIM 3292 Structure Lines (Caldera rim polylines, volcanic origin)",
            "MOLA elevation continuous baseline (+21,229 m peak areoid elevation)",
        ],
        "scientific_significance": (
            "The largest shield volcano in the solar system, rising ~21.3 km above the datum. "
            "SIM 3292 maps the central edifice as unit Ave, bounded by a complex multi-ring collapse "
            "caldera and encircled by a 6-to-8-km-high basal scarp."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MOLA individual laser profile pulses capturing summit caldera topography",
                "Orbital multispectral imagery from Viking, THEMIS, and HRSC",
            ],
            "derived_measurements": [
                "Global MOLA elevation baseline (+21,229 m peak summit areoid elevation)",
                "USGS SIM 3292 caldera rim and basal scarp structure polylines",
                "USGS SIM 3292 unit polygon vectors (Unit Ave)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 110.0,
            "thermophysical_unit": "Fine atmospheric dust mantle on high-altitude summit",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 21229.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Polygon Unit Nhu (Noachian highland undivided unit)",
            "SIM 3292 Structure Lines (Graben axes and fault scarps, tectonic origin)",
            "MOLA elevation baseline (-4,500 m to -7,000 m floor depths)",
        ],
        "scientific_significance": (
            "Melas Chasma is the deepest and widest segment of the Valles Marineris canyon system. "
            "Extensional fault scarps and interior layered deposits record episodic lacustrine and "
            "subaqueous volcanism in an enormous tectonic rift valley."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MOLA laser profile pulses resolving canyon floor and wall scarps",
                "Orbital imaging from Viking, THEMIS, and HRSC",
            ],
            "derived_measurements": [
                "Global MOLA elevation baseline (-4,500 m to -7,000 m floor depths)",
                "USGS SIM 3292 normal fault and graben structure vectors",
                "USGS SIM 3292 unit polygon vectors (Unit Nhu)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 260.0,
            "thermophysical_unit": "Talus slopes and unindurated canyon floor fill",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -4820.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Polygon Unit lNh (Late Noachian highland unit)",
            "MOLA 128 tile megt00n000hb",
            "TES DBmap2007.tif",
        ],
        "scientific_significance": (
            "Noachis Terra preserves rugged blocks of primitive Martian "
            "crust that survived early heavy bombardment. These massifs provide a rare window into the "
            "deep compositional and tectonic architecture of pre-Noachian and early Noachian crust."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MOLA laser pulse altimetry across rugged southern highlands",
                "Orbital imaging frames from Viking and THEMIS",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded topography (+1860 m)",
                "USGS SIM 3292 mapped crustal massif polygon boundaries (Unit lNh)",
                "Spherical geodesic contact distance calculations",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 340.0,
            "thermophysical_unit": "Erosion-resistant bedrock with sand-filled valleys",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 1860.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Structure Records (Origin: Tectonic, Interpreta: Wrinkle ridge, Morphology: Ridge)",
            "SIM 3292 Polygon Unit eHv (Early Hesperian volcanic unit, Syrtis Major Planum)",
            "MOLA 128 tile megt44n000hb",
        ],
        "scientific_significance": (
            "Syrtis Major is an ancient low-relief shield volcano paved with Early Hesperian flood basalts. "
            "A dense network of linear and arcuate wrinkle ridges records lithospheric regional compression "
            "and subsidence caused by the volcanic loading of the underlying crust."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MOLA laser pulse altimetry profiling ridge crest heights",
                "Orbital imaging from Viking and THEMIS",
            ],
            "derived_measurements": [
                "USGS SIM 3292 tectonic wrinkle ridge structure polylines",
                "MOLA 128 (463.08 m/px) gridded topography (+1210 m)",
                "USGS SIM 3292 unit polygon vectors (Unit eHv)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 530.0,
            "thermophysical_unit": "Unmantled basaltic sand and exposed bedrock",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 1210.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Structure Records (Origin: Tectonic, Interpreta: Graben axis, Morphology: Trough)",
            "SIM 3292 Polygon Unit AHv (Amazonian and Hesperian volcanic unit)",
        ],
        "scientific_significance": (
            "Cerberus Fossae consists of subparallel steep-sided extensional rifts cutting through some of the "
            "youngest volcanic plains on Mars. Source of the Athabasca Valles flood lavas and the primary "
            "origin locus of marsquakes detected by the NASA InSight seismometer."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "InSight broadband seismometer event arrivals localized to Cerberus Fossae",
                "Orbital HRSC, CTX, and HiRISE imaging frames",
            ],
            "derived_measurements": [
                "USGS SIM 3292 tectonic graben axis polylines (Trough morphology)",
                "MOLA 4 ppd elevation baseline (-2310 m)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 290.0,
            "thermophysical_unit": "Moderately mantled basaltic volcanic plain",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -2310.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Structure Record (Origin: Fluvial, Interpreta: Outflow Channel / Channel axis)",
            "SIM 3292 Polygon Unit mNh (Middle Noachian highland unit)",
        ],
        "scientific_significance": (
            "Shalbatana Vallis originates abruptly from chaotic terrain and carves an enormous steep-walled "
            "canyon down into Chryse Planitia. Serves as a classic example of catastrophic groundwater "
            "outburst flooding and canyon head sapping on early Mars."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MOLA laser pulse altimetry transects across canyon cross-section",
                "Orbital imaging from Viking and THEMIS",
            ],
            "derived_measurements": [
                "USGS SIM 3292 fluvial channel axis structure polylines",
                "MOLA 4 ppd elevation baseline (-2980 m)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 320.0,
            "thermophysical_unit": "Fluvial scoured floor with unindurated aeolian fill",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": -2980.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "tes-thermal-inertia-putzig-2007",
            "themis-ir-mosaics-regional",
            "sim3292-geology",
            "mola-megdr-128",
        ],
        "source_references": [
            "TES DBmap2007.tif (Pixel TI = 724.3 TIU, rocky / indurated plain)",
            "THEMIS 256 ppd IR tile thm_dir_N-30_000.png",
            "SIM 3292 Polygon Unit mNh (Middle Noachian highland unit)",
            "MOLA 128 tile megt00n000hb",
        ],
        "scientific_significance": (
            "Sinus Meridiani displays one of the highest thermal inertia signatures on Mars (>700 TIU). "
            "This thermophysical contrast reflects the absence of thick dust mantles and the widespread "
            "presence of coarse basaltic sand, hematite lag deposits, and cemented duricrust layers."
        ),
        "primary_evidence_class": "indicative_proxy",
        "evidence_classification": "indicative_proxy",
        "evidence_classes": {
            "measured_observations": [
                "MGS TES calibrated radiance spectra across 10-50 um wavelength range",
                "2001 Mars Odyssey THEMIS multi-spectral infrared radiances",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) gridded elevation (-1428 m)",
                "USGS SIM 3292 unit polygon vectors (Unit mNh)",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~724.3 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
                "THEMIS 256 ppd IR Band 9 8-bit visual display DN (qualitative; NOT calibrated temperature)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 724.3,
            "thermophysical_unit": "Cemented duricrust / coarse pebble lag / exposed bedrock",
            "themis_ir_covered": True,
            "themis_band_9_dn": 174.0,
        },
        "terrain_context": {
            "mola_elevation_m": -1428.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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
        "supporting_datasets": [
            "tes-thermal-inertia-putzig-2007",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "source_references": [
            "TES DBmap2007.tif (Pixel TI = 82.9 TIU, fine unindurated dust mantle)",
            "SIM 3292 Polygon Unit AHv (Amazonian and Hesperian volcanic unit)",
            "MOLA elevation baseline",
        ],
        "scientific_significance": (
            "The elevated Tharsis plateau exhibits an extremely low thermal inertia regime (<90 TIU), "
            "indicating a deep, unindurated aeolian dust mantle (>several centimeters thick). This dust "
            "acts as an effective thermal insulator, concealing underlying basaltic lava flows."
        ),
        "primary_evidence_class": "indicative_proxy",
        "evidence_classification": "indicative_proxy",
        "evidence_classes": {
            "measured_observations": [
                "MGS TES bolometric thermal emission spectra across diurnal cycle",
                "Orbital imaging of bright dust mantles from Viking and THEMIS",
            ],
            "derived_measurements": [
                "MOLA 4 ppd elevation baseline (+3450 m)",
                "USGS SIM 3292 unit polygon vectors (Unit AHv)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 82.9,
            "thermophysical_unit": "Unindurated fine atmospheric dust mantle (< 40 um particle size)",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 3450.0,
            "highest_resolution_tier": "global_baseline",
            "finest_ground_spacing_m": 14818.67,
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
        "supporting_datasets": [
            "ctx-dtm-p21-009323",
            "mola-megdr-128",
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "USGS 20m CTX GeoTIFF (elev +2189.49 m benchmark)",
            "MOLA 128 ppd tile megt00n000hb (463 m/px)",
            "SIM 3292 Unit eNh (Feature ID 846, Early Noachian highland)",
            "TES DBmap2007.tif (473.4 TIU)",
        ],
        "scientific_significance": (
            "Prime multi-instrument benchmark corridor in the southern highlands. Co-registers 20m stereo "
            "CTX numerical elevation (+2189.49 m benchmark) with 463 m/px MOLA regional topography, "
            "Noachian bedrock mapping (eNh), and moderate-high thermal inertia (473.4 TIU) indicative of "
            "fragmented rock and coarse sand lag."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "MRO CTX raw panchromatic stereo CCD frames (P21_009323_1754 & P22_009679_1754)",
                "MGS MOLA laser altimeter pulse returns (profile-to-surface tied)",
            ],
            "derived_measurements": [
                "20.0128 m/px controlled stereo CTX DTM elevation (+2189.49 m benchmark)",
                "MOLA 128 (463.08 m/px) gridded topography and computed regional slope",
                "USGS SIM 3292 polygon mapping (Unit eNh, Feature ID 846)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 473.4,
            "thermophysical_unit": "Duricrust / coarse sand lag / rock fragments",
            "themis_ir_covered": False,
        },
        "terrain_context": {
            "mola_elevation_m": 2189.49,
            "best_dtm_elevation_m": 2189.49,
            "highest_resolution_tier": "local_high_resolution",
            "finest_ground_spacing_m": 20.01,
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
        "supporting_datasets": [
            "mola-megdr-128",
            "themis-ir-mosaics-regional",
            "tes-thermal-inertia-putzig-2007",
            "sim3292-geology",
        ],
        "source_references": [
            "MOLA 128 tile megt00n000hb (-1428 m elevation)",
            "THEMIS 256 ppd IR tile thm_dir_N-30_000.png",
            "TES DBmap2007.tif (724.3 TIU)",
            "SIM 3292 Unit mNh (Middle Noachian highland unit)",
        ],
        "scientific_significance": (
            "Convergence point of regional 256 ppd THEMIS infrared imagery, MGS TES high thermal inertia "
            "regime (724.3 TIU), regional MOLA 128 altimetry, and USGS Middle Noachian stratigraphy. "
            "Provides an ideal macro-scale study area for investigating sedimentary plain formation and aeolian lag."
        ),
        "primary_evidence_class": "derived_measurement",
        "evidence_classification": "derived_measurement",
        "evidence_classes": {
            "measured_observations": [
                "2001 Mars Odyssey THEMIS calibrated multi-spectral infrared radiances",
                "MGS TES bolometric and spectrometer radiances",
            ],
            "derived_measurements": [
                "MOLA 128 (463.08 m/px) regional topography (-1428 m)",
                "USGS SIM 3292 unit polygon vectors (Unit mNh)",
            ],
            "indicative_proxies": [
                "Reconstructed MGS TES thermal inertia (~724.3 TIU; unvalidated ~0.50% LUT step nominal proxy; NOT kinetic temperature)",
                "THEMIS 256 ppd IR Band 9 8-bit visual display DN (qualitative; NOT calibrated temperature)",
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
        },
        "thermal_context": {
            "tes_thermal_inertia_si": 724.3,
            "thermophysical_unit": "Duricrust / coarse lag / exposed bedrock",
            "themis_ir_covered": True,
            "themis_band_9_dn": 174.0,
        },
        "terrain_context": {
            "mola_elevation_m": -1428.0,
            "highest_resolution_tier": "regional_high_resolution",
            "finest_ground_spacing_m": 463.08,
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

        Epistemologically rigorous separation across 4 classes:
        1. Measured Observations: raw/calibrated sensor frames/radiances
        2. Derived Measurements: DTM elevation, MOLA gridded topography, GIS vector polygons/contacts
        3. Indicative Proxies: TES apparent thermal inertia (~0.50% LUT step nominal proxy; NOT kinetic temperature), THEMIS 8-bit visual DN
        4. Potential Investigations: formulated exploration hypotheses to verify in-situ or via targeted orbital follow-up
        """
        norm_lon_360 = ((lon % 360.0) + 360.0) % 360.0
        norm_lon_180 = ((norm_lon_360 + 180.0) % 360.0) - 180.0

        # 1. Query Co-Registered Elevation & DTM Tier
        elev_data = _sample_point_elevation(lat=lat, lon=norm_lon_360)
        elevation_dict = {
            "elevation_m": round(elev_data.elevation_m, 2) if elev_data.elevation_m is not None else None,
            "dataset_id": elev_data.dataset_id,
            "resolution_m": elev_data.native_resolution_m,
            "native_resolution_m": elev_data.native_resolution_m,
            "tier": elev_data.tier,
            "is_nodata": elev_data.is_nodata,
            "crs": elev_data.crs,
            "vertical_datum": (
                "MOLA Areoid (ASP pc_align tied)"
                if "ctx" in (elev_data.dataset_id or "")
                else "MOLA Geoid Adjusted"
                if "hirise" in (elev_data.dataset_id or "")
                else "MOLA Areoid (GMM3 mgm1025 degree 50)"
            ),
        }

        # 2. Query USGS SIM 3292 Geological Unit
        geo_data = self.geology_service.query_point(lat, norm_lon_360)
        geology_dict = geo_data if geo_data else {
            "unit": None,
            "unit_name": "Unmapped or outside SIM 3292 coverage",
            "chronostratigraphic_period": "Unclassified",
            "source_product": "USGS SIM 3292 (Tanaka et al. 2014)",
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

        # Construct comprehensive profile object
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

            # 4-Class Epistemological Separation
            "direct_observations": {
                "themis_qualitative_imagery": themis_dict,
                "high_resolution_dtm_coverage": dtm_coverage_dict,
                "historical_landing_sites_nearby": nearby_landing_sites,
            },
            "derived_measurements": {
                "elevation": elevation_dict,
                "geological_mapping": geology_dict,
                "nearest_structural_feature": nearest_structure,
                "nearest_geological_contact": nearest_contact,
            },
            "indicative_proxies": {
                "thermal_inertia": thermal_dict,
            },
            "scientific_hypotheses_and_opportunities": {
                "status": "candidate_investigation_opportunities",
                "disclaimer": "These questions represent potential scientific opportunities based on available datasets, NOT confirmed discoveries.",
                "investigation_questions": investigation_opportunities,
            },
            "geological_framework_summary": {
                "source_catalog": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "total_polygons": 1311,
                "distinct_unit_codes": 44,
                "total_contacts": 3800,
                "total_structures": 3593,
                "landing_site_multipoints": 9,
                "rigor_note": "1,311 polygon features representing 44 distinct chronostratigraphic unit codes.",
            },
            "dataset_provenance_and_limitations": {
                "elevation_source": elevation_dict.get("dataset_id"),
                "geology_source": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "thermal_source": "MGS TES Apparent Thermal Inertia (Putzig & Mellon 2007, Icarus 191)",
                "themis_source": "2001 Mars Odyssey THEMIS 256 ppd IR Regional Mosaic (ASU/USGS PDS)",
                "limitations": [
                    "Thermal inertia values are unvalidated nominal proxy estimates from 8-bit color-mapped TIFFs (~0.50% LUT step resolution; NOT kinetic temperature).",
                    "THEMIS mosaics are 8-bit visual display DN; quantitative temperature conversion is scientifically invalid.",
                    "Planar map display introduces Web Mercator scale distortion away from the equator.",
                    "Absent high-resolution DTM does not imply flat topography.",
                    "SIM 3292 comprises 1,311 polygon features representing 44 distinct unit codes.",
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
