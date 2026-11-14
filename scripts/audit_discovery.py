import os
import sys
import json
sys.path.insert(0, os.path.abspath("backend"))

from app.science.geology_service import get_geology_service
from app.science.thermal_service import get_thermal_service, get_themis_service
from app.science.discovery_service import get_discovery_service, CANDIDATE_DISCOVERIES
import rasterio

print("=== 1. AUDITING GEOLOGY SERVICE (SIM 3292) ===")
gs = get_geology_service()
meta = gs.get_metadata()
counts = meta.get("shapefile_counts", {})
print("Shapefile record counts:")
for k, v in counts.items():
    print(f"  {k}: {v}")

geo_records = gs._dbf_records.get("geology", [])
unit_codes = sorted(list(set(r.get("Unit") for r in geo_records if r.get("Unit"))))
print(f"Polygon features: {len(geo_records)}")
print(f"Distinct unit codes count: {len(unit_codes)}")
print(f"Sample unit codes: {unit_codes[:10]} ... {unit_codes[-5:]}")

contacts_records = gs._dbf_records.get("contacts", [])
print(f"Geological contacts count: {len(contacts_records)}")

structure_records = gs._dbf_records.get("structure", [])
print(f"Structural features count: {len(structure_records)}")

landing_records = gs._dbf_records.get("landing_sites", [])
print(f"Landing sites count: {len(landing_records)}")

print("\n=== 2. AUDITING TERRAIN RASTER VERTICAL DATUMS ===")
terrain_files = {
    "Tyrrhena CTX": "data/processed/ctx/P21_009323_1754_XN_04S293W_A_01_D01_B01.tif",
    "Apollinaris CTX": "data/processed/ctx/T01_000893_1847_XN_04N191W_A_01_D01_B01.tif",
    "Holden HiRISE": "data/processed/hirise/ESP_011635_1510_ESP_012057_1510_A01_ORTHO.tif",
    "MOLA 128 (00n000)": "data/processed/mola/megt00n000hb.tif",
    "MOLA 4 (Global)": "data/processed/mola/mola_elevation_global_4ppd.tif",
}

for name, rel_path in terrain_files.items():
    if os.path.exists(rel_path):
        with rasterio.open(rel_path) as src:
            tags = src.tags()
            print(f"--- {name} ({rel_path}) ---")
            print(f"  CRS: {src.crs}")
            print(f"  Resolution: {src.res}")
            print(f"  Tags: {tags}")
    else:
        print(f"--- {name} ({rel_path}) NOT FOUND ---")

print("\n=== 3. AUDITING CANDIDATE DISCOVERIES (18 TOTAL) ===")
service = get_discovery_service()
print(f"Total candidate discoveries: {len(CANDIDATE_DISCOVERIES)}")
for idx, d in enumerate(CANDIDATE_DISCOVERIES):
    print(f"[{idx+1}] ID: {d['id']}")
    print(f"    Title: {d['title']}")
    print(f"    Category: {d['category']}")
    print(f"    Coords: lat={d['latitude']}, lon={d['longitude']}")
    print(f"    Evidence Classification: {d.get('evidence_classification')}")
    print(f"    Supporting Datasets: {d.get('supporting_datasets')}")
    print(f"    Sources: {d.get('source_references')}")
    print(f"    Limitations: {d.get('limitations')}")
