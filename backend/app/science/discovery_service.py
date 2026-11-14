"""Science Discovery Engine for MARS-X.

Transforms verified Martian datasets (USGS SIM 3292 Geology, MGS TES Thermal Inertia,
2001 Mars Odyssey THEMIS 256 ppd IR, and CTX / HiRISE / MOLA Elevation Models) into
evidence-based scientific discoveries and location-based science profiles.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Any, Tuple

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

# Authoritative Catalog of Evidence-Based Science Discoveries
CANDIDATE_DISCOVERIES: List[Dict[str, Any]] = [
    # ── 1. High-Resolution Terrain Discoveries ───────────────────────────────
    {
        "id": "disc-terr-tyrrhena-ctx",
        "title": "Tyrrhena Terra Ancient Valley & Cratered Highland",
        "category": "high_res_terrain",
        "latitude": -4.600,
        "longitude": 66.317,
        "target_site": "Tyrrhena Terra",
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
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "20.0128 m/px stereo CTX elevation co-registered with 463 m/px MOLA 128",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "CTX DTM coverage is strictly local (~40 km wide swath); outside swath terrain reverts to 463 m/px MOLA 128.",
        "investigation_opportunities": [
            "Assess degradation state and erosional rim morphology of Noachian impact structures using 20m vertical profile.",
            "Characterize local trafficability corridors and micro-slopes for wheeled rover or astronaut traverses.",
            "Evaluate relationship between bedrock exposures and surrounding coarse sand lag.",
        ],
    },
    {
        "id": "disc-terr-apollinaris-ctx",
        "title": "Apollinaris Sulci Volcanic Scarp & Basal Plains",
        "category": "high_res_terrain",
        "latitude": 4.700,
        "longitude": 168.250,
        "target_site": "Apollinaris Sulci",
        "supporting_datasets": [
            "ctx-dtm-controlled-t01-000893",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "source_references": [
            "GeoTIFF: T01_000893_1847_XN_04N191W_A_01_D01_B01.tif",
            "SIM 3292 Polygon (Unit eHt, Early Hesperian transition unit)",
        ],
        "scientific_significance": (
            "Apollinaris Sulci exposes intricate dissected terrain south of the Apollinaris Mons volcanic caldera. "
            "The 20m controlled stereo DTM captures steep basal scarps and fan deposits, marking the transition "
            "between explosive pyroclastic/volcaniclastic units and lowland plains."
        ),
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "20.0 m/px controlled USGS stereo CTX DTM",
        "evidence_strength": "high_direct_observation",
        "limitations": "Controlled DTM footprint is restricted to lat 4.5°–5.0°N, lon 168.0°–168.5°E.",
        "investigation_opportunities": [
            "Measure vertical scarp height and slope angles to differentiate tectonic vs. sapping origins.",
            "Inspect contact boundary between dissected volcanic materials and younger sedimentary deposits.",
        ],
    },
    {
        "id": "disc-terr-holden-hirise",
        "title": "Holden Crater Megabreccia & Layered Lacustrine Strata",
        "category": "high_res_terrain",
        "latitude": -28.500,
        "longitude": 309.020,
        "target_site": "Holden Crater",
        "supporting_datasets": [
            "hirise-dtm-controlled-esp-011635",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "source_references": [
            "GeoTIFF: ESP_011635_1510_ESP_012057_1510_A01_ORTHO.tif (1.01m controlled DTM)",
            "SIM 3292 Polygon (Unit eNh, Early Noachian cratered rim)",
        ],
        "scientific_significance": (
            "Holden Crater preserves one of the most complete aqueous sedimentary sequences on Mars. "
            "The 1.01m controlled HiRISE DTM provides decimeter-scale vertical discrimination of "
            "alluvial fans, megabreccia blocks thrown out by the Holden impact, and finely layered lacustrine beds."
        ),
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "1.01 m/px ultra-high-resolution controlled HiRISE DTM",
        "evidence_strength": "high_direct_observation",
        "limitations": "HiRISE coverage is a narrow targeted swath (~6 km width); surrounding regional terrain relies on MOLA baseline.",
        "investigation_opportunities": [
            "Map individual megabreccia boulder dimensions (>5m) and orientation to infer impact ejecta mechanics.",
            "Quantify millimeter-to-meter bed dip and strike for ancient lacustrine depositional models.",
            "Identify safe traverse routes around boulder fields for robotic or human sample return.",
        ],
    },

    # ── 2. Historical Surface Landing Sites ───────────────────────────────────
    {
        "id": "disc-land-curiosity",
        "title": "Gale Crater & Mount Sharp (MSL Curiosity)",
        "category": "landing_site",
        "latitude": -4.590,
        "longitude": 137.440,
        "target_site": "Gale Crater",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 0 (MSL Curiosity, 2012)",
            "SIM 3292 Polygon Unit Htu (Hesperian transition undivided unit, Feature ID 754)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Mars Science Laboratory (Curiosity) rover in 2012. Gale Crater features a "
            "5-km-high central sedimentary mound (Aeolis Mons / Mount Sharp) exhibiting transitions from "
            "clay-bearing to sulfate-bearing strata, recording the drying of ancient Mars."
        ),
        "evidence_classification": "confirmed_multi_dataset",
        "spatial_resolution_desc": "Ground surface exploration site validated by orbital GIS and 463 m/px MOLA 128 altimetry",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Orbital data cannot substitute for in-situ rover APXS/CheMin spectroscopic analyses.",
        "investigation_opportunities": [
            "Trace regional contact between Gale floor transitional unit (Htu) and crater rim massifs.",
            "Analyze elevation descent from northern crater rim to Aeolis Palus landing ellipse.",
        ],
    },
    {
        "id": "disc-land-opportunity",
        "title": "Meridiani Planum Hematite Plains (MER-B Opportunity)",
        "category": "landing_site",
        "latitude": -1.946,
        "longitude": 354.473,
        "target_site": "Meridiani Planum",
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "themis-ir-mosaics-regional",
            "mola-megdr-128",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 7 (MER Opportunity, 2003)",
            "SIM 3292 Polygon Unit mNh (Middle Noachian highland unit)",
            "TES DBmap2007.tif (High thermal inertia hematite / basalt lag)",
            "THEMIS 256 ppd IR tile N-30_000",
        ],
        "scientific_significance": (
            "Landing site of NASA's Opportunity rover in 2004 within Eagle Crater. Characterized by crystalline "
            "gray hematite spherules ('blueberries') in sulfate-rich sedimentary rocks, providing decisive "
            "in-situ evidence for persistent acidic groundwater in the Martian past."
        ),
        "evidence_classification": "confirmed_multi_dataset",
        "spatial_resolution_desc": "Ground surface in-situ rover site supported by 256 ppd THEMIS IR and 20 ppd TES thermal inertia",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Regional 256 ppd THEMIS imagery is qualitative Band 9 visual display DN (not calibrated temperature).",
        "investigation_opportunities": [
            "Correlate TES high thermal inertia signature (>600 TIU) with hematite-rich lag distributions.",
            "Compare Meridiani sulfate plains with surrounding Noachian highland bedrock.",
        ],
    },
    {
        "id": "disc-land-spirit",
        "title": "Gusev Crater Basaltic Floor (MER-A Spirit)",
        "category": "landing_site",
        "latitude": -14.569,
        "longitude": 175.473,
        "target_site": "Gusev Crater",
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-128",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 6 (MER Spirit, 2003)",
            "SIM 3292 Polygon Unit eHv (Early Hesperian volcanic unit)",
            "MOLA 128 tile megt00n090hb",
        ],
        "scientific_significance": (
            "Landing site of NASA's Spirit rover in 2004. Explored olivine-rich flood basalts on the crater floor "
            "and hydrothermal silica deposits and carbonate-rich outcrops in the Columbia Hills."
        ),
        "evidence_classification": "inferred_context",
        "spatial_resolution_desc": "In-situ mission coordinates co-located with 463 m/px MOLA 128 altimetry",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Coarse orbital datasets cannot resolve hydrothermal micro-structures discovered in Columbia Hills.",
        "investigation_opportunities": [
            "Analyze relationship between Ma'adim Vallis outflow breach into Gusev and volcanic resurfacing.",
        ],
    },
    {
        "id": "disc-land-pathfinder",
        "title": "Ares Vallis Catastrophic Floodplain (Mars Pathfinder)",
        "category": "landing_site",
        "latitude": 19.261,
        "longitude": 326.747,
        "target_site": "Ares Vallis",
        "supporting_datasets": [
            "sim3292-geology",
            "tes-thermal-inertia-putzig-2007",
            "mola-megdr-4",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 5 (Mars Pathfinder, 1996)",
            "SIM 3292 Polygon Unit Hto (Hesperian transition outflow unit)",
            "SIM 3292 Structure Line (Channel axis, fluvial origin)",
        ],
        "scientific_significance": (
            "Landing site of Mars Pathfinder and Sojourner rover (1997). Situated at the mouth of Ares Vallis "
            "where catastrophic outburst floods deposited poorly sorted boulders and conglomerate rocks sourced "
            "from diverse crustal provinces."
        ),
        "evidence_classification": "confirmed_multi_dataset",
        "spatial_resolution_desc": "In-situ ground truth site with global SIM 3292 outflow channel vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Local terrain is represented by MOLA 4 ppd baseline in the western hemisphere.",
        "investigation_opportunities": [
            "Trace outflow channel alignment from Chryse Planitia basin northward.",
        ],
    },
    {
        "id": "disc-land-viking1",
        "title": "Chryse Planitia Volcanic-Sedimentary Lowlands (Viking 1)",
        "category": "landing_site",
        "latitude": 22.457,
        "longitude": 312.049,
        "target_site": "Chryse Planitia",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Landing Site Record ID 3 (Viking 1, 1975)",
            "SIM 3292 Polygon Unit lHl (Late Hesperian lowland unit)",
        ],
        "scientific_significance": (
            "First successful long-term Mars surface lander (July 1976). Located on a rolling volcanic plain "
            "littered with impact ejecta boulders, conducting the first in-situ biology and soil chemistry experiments."
        ),
        "evidence_classification": "inferred_context",
        "spatial_resolution_desc": "Historic surface coordinate on 1:20M scale global chronostratigraphic unit lHl",
        "evidence_strength": "high_direct_observation",
        "limitations": "Surface rocks are below orbital MOLA resolution.",
        "investigation_opportunities": [
            "Characterize lowland plain resurfacing history relative to circum-Chryse outflow channels.",
        ],
    },

    # ── 3. Geological Units & Contacts ───────────────────────────────────────
    {
        "id": "disc-geol-olympus-mons",
        "title": "Olympus Mons Summit Caldera & Basal Scarp",
        "category": "geological_unit_contact",
        "latitude": 18.650,
        "longitude": 226.200,
        "target_site": "Olympus Mons",
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
        "evidence_classification": "derived_measurement",
        "spatial_resolution_desc": "Global MOLA continuous elevation baseline co-registered with 1:20M GIS geologic vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Terrain in western Tharsis is covered by the 4 ppd MOLA baseline; high-res CTX coverage is absent at summit.",
        "investigation_opportunities": [
            "Examine nested caldera collapse sequences using structural rim polylines and elevation contours.",
            "Analyze atmospheric dust deposition on upper shield via day/night thermal inertia contrasts.",
        ],
    },
    {
        "id": "disc-geol-valles-marineris",
        "title": "Melas Chasma Central Tectonic Rift (Valles Marineris)",
        "category": "geological_unit_contact",
        "latitude": -9.800,
        "longitude": 283.600,
        "target_site": "Melas Chasma",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Polygon Unit lHl (Late Hesperian lowland / chasma interior)",
            "SIM 3292 Structure Lines (Graben axes and fault scarps, tectonic origin)",
            "MOLA elevation baseline (-4,500 m to -7,000 m floor depths)",
        ],
        "scientific_significance": (
            "Melas Chasma is the deepest and widest segment of the Valles Marineris canyon system. "
            "Extensional fault scarps and interior layered deposits record episodic lacustrine and "
            "subaqueous volcanism in an enormous tectonic rift valley."
        ),
        "evidence_classification": "derived_measurement",
        "spatial_resolution_desc": "Global MOLA elevation baseline with tectonic structure GIS polylines",
        "evidence_strength": "high_direct_observation",
        "limitations": "Steep canyon walls produce radar shadow and data gaps in some orbital instruments.",
        "investigation_opportunities": [
            "Map depth profile and fault throw across graben axes using MOLA vertical profiles.",
            "Investigate interior layered deposits for evaporite and sulfate mineralization indicators.",
        ],
    },
    {
        "id": "disc-geol-noachis-massifs",
        "title": "Noachis Terra Ancient Crustal Massifs",
        "category": "geological_unit_contact",
        "latitude": -35.000,
        "longitude": 30.000,
        "target_site": "Noachis Terra",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-128",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Polygon Unit eNhm (Early Noachian highland massif unit)",
            "MOLA 128 tile megt00n000hb",
            "TES DBmap2007.tif",
        ],
        "scientific_significance": (
            "Unit eNhm represents isolated mountainous massifs and rugged blocks of primitive Martian "
            "crust that survived early heavy bombardment. These massifs provide a rare window into the "
            "deep compositional and tectonic architecture of pre-Noachian and early Noachian crust."
        ),
        "evidence_classification": "derived_measurement",
        "spatial_resolution_desc": "463 m/px MOLA 128 altimetry co-registered with SIM 3292 unit eNhm polygons",
        "evidence_strength": "derived_stratigraphic",
        "limitations": "Massif units are heavily cratered and degraded; contacts are mapped at 1:20M regional scale.",
        "investigation_opportunities": [
            "Differentiate primitive crustal block elevations from surrounding cratered plateau materials.",
            "Evaluate ancient fracture networks bounding massif perimeters.",
        ],
    },

    # ── 4. Tectonic & Morphologic Structures ─────────────────────────────────
    {
        "id": "disc-struct-syrtis-ridges",
        "title": "Syrtis Major Wrinkle Ridge Compressive Network",
        "category": "structural_feature",
        "latitude": 8.500,
        "longitude": 68.000,
        "target_site": "Syrtis Major",
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
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "463 m/px MOLA 128 regional topography with GIS structural polyline overlay",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Individual thrust fault planes beneath wrinkle ridges cannot be imaged directly from orbit.",
        "investigation_opportunities": [
            "Calculate horizontal shortening strain across the wrinkle ridge network using topographic crest heights.",
            "Assess high thermal inertia (>500 TIU) basaltic sand accumulation along ridge windward slopes.",
        ],
    },
    {
        "id": "disc-struct-cerberus-graben",
        "title": "Cerberus Fossae Extensional Graben System",
        "category": "structural_feature",
        "latitude": 10.500,
        "longitude": 158.000,
        "target_site": "Cerberus Fossae",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Structure Records (Origin: Tectonic, Interpreta: Graben axis, Morphology: Trough)",
            "SIM 3292 Polygon Unit lAv (Late Amazonian volcanic unit)",
        ],
        "scientific_significance": (
            "Cerberus Fossae consists of subparallel steep-sided extensional rifts cutting through some of the "
            "youngest volcanic plains on Mars. Source of the Athabasca Valles flood lavas and the primary "
            "origin locus of marsquakes detected by the NASA InSight seismometer."
        ),
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "GIS tectonic structure vectors co-registered with MOLA baseline",
        "evidence_strength": "high_direct_observation",
        "limitations": "Narrow fracture widths (<1 km) are below MOLA 4 ppd resolution; requires local high-res imagery for fracture detail.",
        "investigation_opportunities": [
            "Relate graben orientation to regional stress fields induced by the Elysium volcanic rise.",
            "Inspect graben floor vents as candidate sites for recent volcanic degassing or subsurface water release.",
        ],
    },
    {
        "id": "disc-struct-shalbatana-channel",
        "title": "Shalbatana Vallis Catastrophic Outflow Channel",
        "category": "structural_feature",
        "latitude": 7.800,
        "longitude": 317.900,
        "target_site": "Shalbatana Vallis",
        "supporting_datasets": [
            "sim3292-geology",
            "mola-megdr-4",
            "tes-thermal-inertia-putzig-2007",
        ],
        "source_references": [
            "SIM 3292 Structure Record (Origin: Fluvial, Interpreta: Outflow Channel / Channel axis)",
            "SIM 3292 Polygon Unit Hto (Hesperian transition outflow unit)",
        ],
        "scientific_significance": (
            "Shalbatana Vallis originates abruptly from chaotic terrain and carves an enormous steep-walled "
            "canyon down into Chryse Planitia. Serves as a classic example of catastrophic groundwater "
            "outburst flooding and canyon head sapping on early Mars."
        ),
        "evidence_classification": "direct_observation",
        "spatial_resolution_desc": "GIS fluvial axis vectors and 1:20M geologic unit boundaries",
        "evidence_strength": "derived_stratigraphic",
        "limitations": "Fluvial flow velocities and discharge rates can only be inferred through hydrodynamic modeling.",
        "investigation_opportunities": [
            "Model catastrophic flood peak discharge from channel cross-sectional area and bed slope.",
            "Trace sediment deposition fan where Shalbatana discharges into the Chryse basin floor.",
        ],
    },

    # ── 5. Thermal-Inertia Contrasts ─────────────────────────────────────────
    {
        "id": "disc-therm-sinus-meridiani",
        "title": "Sinus Meridiani High Thermal-Inertia Plains",
        "category": "thermal_contrast",
        "latitude": -2.000,
        "longitude": 5.000,
        "target_site": "Sinus Meridiani",
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
        "evidence_classification": "indicative_proxy",
        "spatial_resolution_desc": "20 ppd (~3 km/px) calibrated TES thermal inertia and 256 ppd (~231.5 m/px) THEMIS IR mosaic",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "TES values are legend-calibrated estimates (unvalidated nominal proxy); THEMIS mosaic is 8-bit visual display DN.",
        "investigation_opportunities": [
            "Map spatial boundary between high-inertia dark plains and adjacent lower-inertia cratered highlands.",
            "Evaluate wind stripping mechanisms preventing dust accumulation in the Meridiani corridor.",
        ],
    },
    {
        "id": "disc-therm-tharsis-dust",
        "title": "Tharsis Montes Low Thermal-Inertia Dust Reservoir",
        "category": "thermal_contrast",
        "latitude": 10.000,
        "longitude": 250.000,
        "target_site": "Tharsis Plains",
        "supporting_datasets": [
            "tes-thermal-inertia-putzig-2007",
            "sim3292-geology",
            "mola-megdr-4",
        ],
        "source_references": [
            "TES DBmap2007.tif (Pixel TI = 82.9 TIU, fine unindurated dust mantle)",
            "SIM 3292 Polygon Unit lAv (Late Amazonian volcanic unit)",
            "MOLA elevation baseline",
        ],
        "scientific_significance": (
            "The elevated Tharsis plateau exhibits an extremely low thermal inertia regime (<90 TIU), "
            "indicating a deep, unindurated aeolian dust mantle (>several centimeters thick). This dust "
            "acts as an effective thermal insulator, concealing underlying basaltic lava flows."
        ),
        "evidence_classification": "indicative_proxy",
        "spatial_resolution_desc": "20 ppd (~3 km/px) global MGS TES apparent thermal inertia",
        "evidence_strength": "indicative_proxy",
        "limitations": "Underlying bedrock is completely masked by dust; optical and thermal sensors only detect upper millimeters.",
        "investigation_opportunities": [
            "Estimate dust mantle thickness from daytime vs. nighttime cooling curves.",
            "Identify wind-scoured craters or kipukas where underlying volcanic bedrock pierces through the mantle.",
        ],
    },

    # ── 6. Multi-Dataset Science Intersections ────────────────────────────────
    {
        "id": "disc-multi-tyrrhena-corridor",
        "title": "Tyrrhena Terra Multi-Instrument Science Corridor",
        "category": "multi_dataset_intersection",
        "latitude": -4.600,
        "longitude": 66.317,
        "target_site": "Tyrrhena Terra",
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
        "evidence_classification": "confirmed_multi_dataset",
        "spatial_resolution_desc": "Full multi-tier stack: 20m CTX + 463m MOLA + 3km TES + 1:20M GIS vectors",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "Coverage of 20m CTX is restricted to swath footprint; does not have HiRISE 1m coverage.",
        "investigation_opportunities": [
            "Perform cross-instrument validation of slope metrics between 20m CTX and 463m MOLA.",
            "Assess safe traverse corridors and scientific sampling targets across ancient cratered terrain.",
        ],
    },
    {
        "id": "disc-multi-meridiani-gateway",
        "title": "Sinus Meridiani Stratigraphic Gateway",
        "category": "multi_dataset_intersection",
        "latitude": -2.000,
        "longitude": 5.000,
        "target_site": "Sinus Meridiani",
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
        "evidence_classification": "confirmed_multi_dataset",
        "spatial_resolution_desc": "Multi-instrument overlap: 231.5 m/px THEMIS + 463 m/px MOLA + 3 km/px TES",
        "evidence_strength": "confirmed_multi_dataset",
        "limitations": "No local numerical CTX or HiRISE stereo DTM is acquired in this specific regional tile.",
        "investigation_opportunities": [
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
        """Retrieve discovery by ID enriched with live point measurements."""
        if discovery_id not in self._discoveries:
            return None
        disc = dict(self._discoveries[discovery_id])
        # Enrich with live profile
        profile = self.get_science_profile(disc["latitude"], disc["longitude"], radius_km=300.0)
        disc["live_measurements"] = profile
        return disc

    def get_nearby_discoveries(
        self, lat: float, lon: float, radius_km: float = 1500.0, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find candidate science discoveries within a great-circle radius on Mars."""
        results = []
        for d in self._discoveries.values():
            dist = mars_haversine_distance_km(lat, lon, d["latitude"], d["longitude"])
            if dist <= radius_km:
                item = dict(d)
                item["distance_km"] = round(dist, 1)
                results.append(item)

        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]

    def get_science_profile(self, lat: float, lon: float, radius_km: float = 500.0) -> Dict[str, Any]:
        """Generate a location-specific science opportunity profile from integrated Mars datasets."""
        # Normalize longitude to [-180, +180] and [0, 360]
        norm_lon_180 = ((lon + 180.0) % 360.0) - 180.0
        norm_lon_360 = lon % 360.0

        # 1. Sample Elevation via multi-resolution terrain engine
        elev_data = _sample_point_elevation(lat, lon)
        elevation_dict = {
            "elevation_m": elev_data.elevation_m,
            "dataset_id": elev_data.dataset_id,
            "tier": elev_data.tier,
            "instrument": elev_data.instrument,
            "native_resolution_desc": elev_data.native_resolution_desc,
            "vertical_reference": elev_data.vertical_reference,
            "is_nodata": elev_data.is_nodata,
        }

        # 2. Query USGS SIM 3292 Geology
        geo_data = self.geology_service.query_point(lat, lon)
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
            "semantics_note": "Qualitative 8-bit visual display DN (Band 9, 12.57 um). NOT calibrated temperature.",
        }

        # 5. Check High-Resolution DTM Footprints
        in_tyrrhena_ctx = (-5.19 <= lat <= -4.00 and 66.04 <= norm_lon_360 <= 66.62)
        in_apollinaris_ctx = (4.50 <= lat <= 5.00 and 168.00 <= norm_lon_360 <= 168.50)
        in_holden_hirise = (-28.70 <= lat <= -28.30 and 308.80 <= norm_lon_360 <= 309.20)

        dtm_coverage_dict = {
            "has_high_res_dtm": in_tyrrhena_ctx or in_apollinaris_ctx or in_holden_hirise,
            "active_product": (
                "ctx-dtm-p21-009323 (20m)"
                if in_tyrrhena_ctx
                else "ctx-dtm-controlled-t01-000893 (20m)"
                if in_apollinaris_ctx
                else "hirise-dtm-controlled-esp-011635 (1.01m)"
                if in_holden_hirise
                else "mola-megdr-128 (463m)"
                if elev_data.tier == "regional_high_resolution"
                else "mola-megdr-4 (14.8km)"
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

        # 7. Proximity to Geological Contacts (SIM 3292 Contacts)
        nearest_contact: Optional[Dict[str, Any]] = None
        contact_bboxes = self.geology_service._shp_bboxes.get("contacts", [])
        contact_recs = self.geology_service._dbf_records.get("contacts", [])
        min_contact_dist = 999999.0
        min_contact_idx = -1

        for i, (xmin, ymin, xmax, ymax) in enumerate(contact_bboxes):
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

        # 8. Nearby Historical Landing Sites
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

        # 10. Direct vs. Derived vs. Inferred Separation
        return {
            "coordinates": {
                "latitude": round(lat, 5),
                "longitude_deg_e": round(norm_lon_360, 5),
                "longitude_deg_w180": round(norm_lon_180, 5),
            },
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
            "dataset_provenance_and_limitations": {
                "elevation_source": elevation_dict.get("dataset_id"),
                "geology_source": "USGS SIM 3292 (Tanaka et al. 2014, DOI:10.3133/sim3292)",
                "thermal_source": "MGS TES Apparent Thermal Inertia (Putzig & Mellon 2007, Icarus 191)",
                "themis_source": "2001 Mars Odyssey THEMIS 256 ppd IR Regional Mosaic (ASU/USGS PDS)",
                "limitations": [
                    "Thermal inertia values are unvalidated nominal proxy estimates from 8-bit color-mapped TIFFs.",
                    "THEMIS mosaics are 8-bit visual display DN; quantitative temperature conversion is prohibited.",
                    "Planar map display introduces Web Mercator scale distortion away from the equator.",
                    "Absent high-resolution DTM does not imply flat topography.",
                ],
            },
        }

    def compare_locations(self, location_keys: List[str]) -> Dict[str, Any]:
        """Compare multiple science locations side-by-side using integrated datasets."""
        profiles = []
        for key in location_keys[:5]:  # Bound comparison to at most 5 sites
            # Check if key is a discovery ID
            if key in self._discoveries:
                d = self._discoveries[key]
                prof = self.get_science_profile(d["latitude"], d["longitude"])
                prof["discovery_id"] = d["id"]
                prof["title"] = d["title"]
                prof["category"] = d["category"]
                profiles.append(prof)
            elif "," in key:
                # Coordinate string format 'lat,lon'
                parts = key.split(",")
                try:
                    p_lat = float(parts[0].strip())
                    p_lon = float(parts[1].strip())
                    prof = self.get_science_profile(p_lat, p_lon)
                    prof["discovery_id"] = f"custom-coord-{round(p_lat, 2)}-{round(p_lon, 2)}"
                    prof["title"] = f"Custom Site ({round(p_lat, 2)}°, {round(p_lon, 2)}°)"
                    prof["category"] = "custom_coordinate"
                    profiles.append(prof)
                except ValueError:
                    continue

        return {
            "comparison_count": len(profiles),
            "comparison_profiles": profiles,
        }


def get_discovery_service() -> ScienceDiscoveryService:
    """Retrieve singleton ScienceDiscoveryService."""
    if ScienceDiscoveryService._instance is None:
        ScienceDiscoveryService._instance = ScienceDiscoveryService()
    return ScienceDiscoveryService._instance
