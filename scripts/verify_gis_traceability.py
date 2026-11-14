import os
import sys
import json
sys.path.insert(0, os.path.abspath("backend"))

from app.science.geology_service import get_geology_service
from app.science.discovery_service import CANDIDATE_DISCOVERIES, mars_haversine_distance_km

gs = get_geology_service()

print("Verifying 18 Candidate Discoveries against SIM 3292 GIS records...")
for i, d in enumerate(CANDIDATE_DISCOVERIES):
    lat = d["latitude"]
    lon = d["longitude"]
    norm_lon_180 = ((lon + 180.0) % 360.0) - 180.0
    
    geo_pt = gs.query_point(lat, lon)
    unit_code = geo_pt.get("unit") if geo_pt else None
    unit_name = geo_pt.get("unit_name") if geo_pt else None
    
    # Check matching landing site if landing_site category
    matching_landing = None
    if d["category"] == "landing_site":
        for l_rec in gs._dbf_records.get("landing_sites", []):
            lx, ly = l_rec.get("X_COORD"), l_rec.get("Y_COORD")
            if lx is not None and ly is not None:
                dist = mars_haversine_distance_km(lat, norm_lon_180, ly, lx)
                if dist < 100.0:
                    matching_landing = (l_rec.get("NAME"), l_rec.get("OBJECTID"), round(dist, 1))
                    break
    
    # Find nearest structure
    min_s_dist = 999999.0
    s_feat = None
    for idx, (xmin, ymin, xmax, ymax) in enumerate(gs._shp_bboxes.get("structure", [])):
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        d_s = mars_haversine_distance_km(lat, norm_lon_180, cy, cx)
        if d_s < min_s_dist:
            min_s_dist = d_s
            s_rec = gs._dbf_records["structure"][idx]
            s_feat = (s_rec.get("Origin"), s_rec.get("Interpreta"), s_rec.get("OBJECTID"), round(d_s, 1))

    # Find nearest contact
    min_c_dist = 999999.0
    c_feat = None
    for idx, (xmin, ymin, xmax, ymax) in enumerate(gs._shp_bboxes.get("contacts", [])):
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        d_c = mars_haversine_distance_km(lat, norm_lon_180, cy, cx)
        if d_c < min_c_dist:
            min_c_dist = d_c
            c_rec = gs._dbf_records["contacts"][idx]
            c_feat = (c_rec.get("ConType"), c_rec.get("OBJECTID"), round(d_c, 1))

    print(f"[{i+1}] {d['id']} ({d['title']})")
    print(f"    Coords: {lat}°, {lon}°E")
    print(f"    Queried Unit: {unit_code} - {unit_name}")
    if matching_landing:
        print(f"    Landing site match: {matching_landing[0]} (OBJECTID {matching_landing[1]}, {matching_landing[2]} km)")
    print(f"    Nearest structure: {s_feat[0]} - {s_feat[1]} (OBJECTID {s_feat[2]}, {s_feat[3]} km)")
    print(f"    Nearest contact: {c_feat[0]} (OBJECTID {c_feat[1]}, {c_feat[2]} km)")
