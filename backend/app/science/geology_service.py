"""Geological GIS Service for USGS SIM 3292 (Geologic Map of Mars).

Authoritative Data:
- USGS Scientific Investigations Map 3292 (Tanaka et al. 2014, DOI: 10.3133/sim3292)
- USGS Data Release (Skinner, Fortezzo, Hare 2023, DOI: 10.5066/P9UGAC18)
- Native CRS: GCS_Mars_2000_Sphere (R=3,396,190.0 m, flattening=0.0)
"""

import os
import struct
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("MARS-X.science.geology")

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
GIS_ROOT = os.path.join(DATA_ROOT, "derived", "geology", "sim3292_database", "SIM3292_MarsGlobalGeologicGIS_20M")
SHP_DIR = os.path.join(GIS_ROOT, "SIM3292_Shapefiles")

LAYER_CONFIG = {
    "geology": {
        "filename": "SIM3292_Global_Geology",
        "geometry_type": "Polygon",
        "description": "Global chronostratigraphic map units (1:20,000,000)",
        "expected_features": 1311
    },
    "contacts": {
        "filename": "SIM3292_Global_Contacts",
        "geometry_type": "PolyLine",
        "description": "Geological contact boundaries and lineations",
        "expected_features": 3800
    },
    "structure": {
        "filename": "SIM3292_Global_Structure",
        "geometry_type": "PolyLine",
        "description": "Tectonic and structural features (faults, grabens, wrinkle ridges)",
        "expected_features": 3593
    },
    "landing_sites": {
        "filename": "SIM3292_Global_Landing_sites",
        "geometry_type": "Point",
        "description": "Historical Mars surface landing and impact sites",
        "expected_features": 9
    }
}


class GeologyService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeologyService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._dbf_records: Dict[str, List[Dict[str, Any]]] = {}
        self._shp_bboxes: Dict[str, List[Tuple[float, float, float, float]]] = {}
        self._shp_offsets: Dict[str, List[Tuple[int, int]]] = {}
        self._unit_legend: Dict[str, Dict[str, Any]] = {}
        self._load_metadata_and_indices()
        self._initialized = True

    def _load_metadata_and_indices(self):
        """Pre-index DBF records and bounding boxes for spatial filtering."""
        if not os.path.exists(SHP_DIR):
            logger.warning("Geological GIS directory not found at: %s", SHP_DIR)
            return

        for layer_key, cfg in LAYER_CONFIG.items():
            base_path = os.path.join(SHP_DIR, cfg["filename"])
            shp_path = base_path + ".shp"
            dbf_path = base_path + ".dbf"
            if not os.path.exists(shp_path) or not os.path.exists(dbf_path):
                logger.warning("Layer %s missing .shp or .dbf at %s", layer_key, base_path)
                continue

            records = self._read_dbf(dbf_path)
            self._dbf_records[layer_key] = records

            bboxes, offsets = self._index_shp(shp_path)
            self._shp_bboxes[layer_key] = bboxes
            self._shp_offsets[layer_key] = offsets
            logger.info("Loaded %d features for geological layer: %s", len(records), layer_key)

        # Build legend from geology layer
        if "geology" in self._dbf_records:
            for rec in self._dbf_records["geology"]:
                unit = rec.get("Unit", "").strip()
                desc = rec.get("UnitDesc", "").strip()
                if unit and unit not in self._unit_legend:
                    # Parse era
                    era = "Undivided"
                    if unit.startswith("eN") or unit.startswith("mN") or unit.startswith("lN") or unit.startswith("N"):
                        era = "Noachian"
                    elif unit.startswith("eH") or unit.startswith("mH") or unit.startswith("lH") or unit.startswith("H"):
                        era = "Hesperian"
                    elif unit.startswith("eA") or unit.startswith("mA") or unit.startswith("lA") or unit.startswith("A"):
                        era = "Amazonian"
                    elif "H" in unit and "N" in unit:
                        era = "Hesperian-Noachian"
                    elif "A" in unit and "H" in unit:
                        era = "Amazonian-Hesperian"

                    self._unit_legend[unit] = {
                        "unit": unit,
                        "description": desc,
                        "chronostratigraphic_period": era,
                        "feature_count": 0,
                        "total_area_sq_km": 0.0
                    }
                if unit in self._unit_legend:
                    self._unit_legend[unit]["feature_count"] += 1
                    try:
                        self._unit_legend[unit]["total_area_sq_km"] += float(rec.get("SphArea_km", 0.0))
                    except (ValueError, TypeError):
                        pass

    def _read_dbf(self, dbf_path: str) -> List[Dict[str, Any]]:
        records = []
        with open(dbf_path, "rb") as f:
            hdr = f.read(32)
            num_recs, hlen, rlen = struct.unpack("<IHH", hdr[4:12])
            fields = []
            while True:
                b = f.read(32)
                if not b or b[0] == 0x0D:
                    break
                fname = b[0:11].replace(b"\x00", b"").decode("ascii", errors="ignore").strip()
                ftype = chr(b[11])
                flen = b[16]
                fields.append((fname, ftype, flen))

            f.seek(hlen)
            for i in range(num_recs):
                raw = f.read(rlen)
                if len(raw) < rlen:
                    break
                offset = 1  # delete flag
                row = {"_objectid": i + 1}
                for fname, ftype, flen in fields:
                    val_str = raw[offset:offset+flen].decode("latin1", errors="ignore").strip()
                    offset += flen
                    if ftype == "N":
                        try:
                            val: Any = int(val_str) if "." not in val_str else float(val_str)
                        except ValueError:
                            val = val_str
                    elif ftype == "F":
                        try:
                            val = float(val_str)
                        except ValueError:
                            val = val_str
                    else:
                        val = val_str
                    row[fname] = val
                records.append(row)
        return records

    def _index_shp(self, shp_path: str) -> Tuple[List[Tuple[float, float, float, float]], List[Tuple[int, int]]]:
        bboxes = []
        offsets = []
        with open(shp_path, "rb") as f:
            f.seek(100)
            while True:
                pos = f.tell()
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                num, length_words = struct.unpack(">II", hdr)
                content_bytes = length_words * 2
                stype_b = f.read(4)
                if len(stype_b) < 4:
                    break
                stype, = struct.unpack("<I", stype_b)
                if stype in [3, 5]:  # PolyLine or Polygon
                    box = struct.unpack("<4d", f.read(32))  # xmin, ymin, xmax, ymax
                    bboxes.append(box)
                    f.seek(content_bytes - 36, os.SEEK_CUR)
                elif stype == 1:  # Point
                    pt = struct.unpack("<2d", f.read(16))  # x, y
                    bboxes.append((pt[0], pt[1], pt[0], pt[1]))
                elif stype == 8:  # MultiPoint
                    box = struct.unpack("<4d", f.read(32))
                    bboxes.append(box)
                    f.seek(content_bytes - 36, os.SEEK_CUR)
                else:
                    bboxes.append((0.0, 0.0, 0.0, 0.0))
                    f.seek(content_bytes - 4, os.SEEK_CUR)
                offsets.append((pos, content_bytes + 8))
        return bboxes, offsets

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "title": "Database of the Geologic Map of Mars (USGS SIM 3292)",
            "authors": "Tanaka, K.L., Skinner, J.A., Jr., Dohm, J.M., Irwin, R.P., III, Kolb, E.J., Fortezzo, C.M., Platz, T., Michael, G.G., and Hare, T.M.",
            "publication_year": 2014,
            "publication_doi": "10.3133/sim3292",
            "data_release_doi": "10.5066/P9UGAC18",
            "archive_source": "USGS Publications Warehouse & USGS Astrogeology Science Center",
            "scale": "1:20,000,000",
            "crs": "GCS_Mars_2000_Sphere (R=3,396,190.0 m, flattening=0.0)",
            "native_projection": "Robinson Projection (Central Meridian 0.0 deg E)",
            "display_transformation_note": (
                "Shapefile features store native coordinates in decimal degrees (GCS_Mars_2000_Sphere, R=3,396,190 m). "
                "In MapLibre, these coordinates are projected to the viewport canvas via the Web Mercator projection. "
                "Direct consumption of decimal degrees avoids an offline file reprojection step, but does NOT eliminate "
                "projection distortion: linear and areal scale factors increase with latitude as sec(phi) and sec^2(phi)."
            ),
            "layers": {
                k: {
                    "filename": cfg["filename"],
                    "geometry_type": cfg["geometry_type"],
                    "description": cfg["description"],
                    "feature_count": len(self._dbf_records.get(k, []))
                }
                for k, cfg in LAYER_CONFIG.items()
            },
            "attribution": "U.S. Geological Survey (USGS) Astrogeology Science Center",
            "production_status": "downloaded_verified",
            "application_integration_status": "integrated_backend_api"
        }

    def get_legend(self) -> List[Dict[str, Any]]:
        return sorted(list(self._unit_legend.values()), key=lambda x: x["unit"])

    def get_unit_details(self, unit_id: str) -> Optional[Dict[str, Any]]:
        norm_unit = unit_id.strip()
        for u, d in self._unit_legend.items():
            if u.lower() == norm_unit.lower():
                res = dict(d)
                res["unit_name"] = d.get("description", "")
                return res
        return None

    def _read_geometry_geojson(self, layer: str, index: int) -> Optional[Dict[str, Any]]:
        """Read geometry for a single feature by index and convert to GeoJSON."""
        if layer not in self._shp_offsets or index >= len(self._shp_offsets[layer]):
            return None
        cfg = LAYER_CONFIG[layer]
        shp_path = os.path.join(SHP_DIR, cfg["filename"] + ".shp")
        offset, total_len = self._shp_offsets[layer][index]

        with open(shp_path, "rb") as f:
            f.seek(offset + 8)  # skip 8-byte record header
            stype, = struct.unpack("<I", f.read(4))

            if stype == 1:  # Point
                x, y = struct.unpack("<2d", f.read(16))
                return {"type": "Point", "coordinates": [round(x, 6), round(y, 6)]}

            if stype == 8:  # MultiPoint
                box = struct.unpack("<4d", f.read(32))
                num_pts, = struct.unpack("<I", f.read(4))
                pts = [list(struct.unpack("<2d", f.read(16))) for _ in range(num_pts)]
                return {"type": "MultiPoint", "coordinates": [[round(p[0], 6), round(p[1], 6)] for p in pts]}

            if stype in [3, 5]:  # PolyLine or Polygon
                box = struct.unpack("<4d", f.read(32))
                num_parts, num_pts = struct.unpack("<II", f.read(8))
                part_indices = list(struct.unpack(f"<{num_parts}I", f.read(4 * num_parts)))
                pts = [struct.unpack("<2d", f.read(16)) for _ in range(num_pts)]

                # Partition into parts
                rings = []
                for p_idx in range(num_parts):
                    start = part_indices[p_idx]
                    end = part_indices[p_idx + 1] if p_idx + 1 < num_parts else num_pts
                    rings.append([[round(pt[0], 6), round(pt[1], 6)] for pt in pts[start:end]])

                if stype == 3:
                    return {"type": "MultiLineString" if len(rings) > 1 else "LineString",
                            "coordinates": rings if len(rings) > 1 else rings[0]}
                else:
                    return {"type": "Polygon", "coordinates": rings}
        return None

    def query_viewport(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        layer: str = "geology",
        limit: int = 200
    ) -> Dict[str, Any]:
        """Query features intersecting a bounding box in degrees [-180 to 180, -90 to 90]."""
        if layer not in LAYER_CONFIG:
            raise ValueError(f"Invalid layer '{layer}'. Available: {list(LAYER_CONFIG.keys())}")

        bboxes = self._shp_bboxes.get(layer, [])
        records = self._dbf_records.get(layer, [])

        # Normalize viewport to -180..180
        def norm180(x):
            return ((x + 180.0) % 360.0) - 180.0

        v_min_lon = min(norm180(min_lon), norm180(max_lon))
        v_max_lon = max(norm180(min_lon), norm180(max_lon))
        v_min_lat = min(min_lat, max_lat)
        v_max_lat = max(min_lat, max_lat)

        features = []
        for i, box in enumerate(bboxes):
            xmin, ymin, xmax, ymax = box
            # Intersects test
            if xmin <= v_max_lon and xmax >= v_min_lon and ymin <= v_max_lat and ymax >= v_min_lat:
                geom = self._read_geometry_geojson(layer, i)
                if geom:
                    props = dict(records[i])
                    features.append({
                        "type": "Feature",
                        "id": props.get("OBJECTID", i + 1),
                        "geometry": geom,
                        "properties": props
                    })
                if len(features) >= limit:
                    break

        return {
            "type": "FeatureCollection",
            "layer": layer,
            "total_matches": len(features),
            "viewport_bounds": {
                "min_lon": v_min_lon,
                "min_lat": v_min_lat,
                "max_lon": v_max_lon,
                "max_lat": v_max_lat
            },
            "features": features
        }

    def query_point(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Point-in-polygon query for geological unit at coordinates."""
        if "geology" not in self._shp_bboxes:
            return None

        # Normalize lon to -180..180
        norm_lon = ((lon + 180.0) % 360.0) - 180.0
        bboxes = self._shp_bboxes["geology"]
        records = self._dbf_records["geology"]

        # Filter candidate indices
        candidates = []
        for i, (xmin, ymin, xmax, ymax) in enumerate(bboxes):
            if xmin <= norm_lon <= xmax and ymin <= lat <= ymax:
                candidates.append(i)

        for idx in candidates:
            geom = self._read_geometry_geojson("geology", idx)
            if not geom or geom["type"] != "Polygon":
                continue
            rings = geom["coordinates"]
            # Exterior ring ray casting
            exterior = rings[0]
            if self._point_in_ring(norm_lon, lat, exterior):
                # Check holes
                in_hole = False
                for hole in rings[1:]:
                    if self._point_in_ring(norm_lon, lat, hole):
                        in_hole = True
                        break
                if not in_hole:
                    props = dict(records[idx])
                    unit_code = props.get("Unit", "").strip()
                    legend_info = self._unit_legend.get(unit_code, {})
                    return {
                        "latitude": lat,
                        "longitude": lon,
                        "normalized_longitude": round(norm_lon, 5),
                        "unit": unit_code,
                        "unit_name": legend_info.get("description", props.get("UnitDesc", "")),
                        "chronostratigraphic_period": legend_info.get("chronostratigraphic_period", "Undivided"),
                        "spherical_area_sq_km": props.get("SphArea_km"),
                        "feature_id": props.get("OBJECTID", idx + 1),
                        "source_product": "USGS SIM 3292 (Tanaka et al. 2014)",
                        "crs": "GCS_Mars_2000_Sphere (R=3,396,190 m)",
                        "attribution": "U.S. Geological Survey Astrogeology Science Center"
                    }
        return None

    @staticmethod
    def _point_in_ring(x: float, y: float, ring: List[List[float]]) -> bool:
        inside = False
        n = len(ring)
        p1x, p1y = ring[0]
        for i in range(n + 1):
            p2x, p2y = ring[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside


def get_geology_service() -> GeologyService:
    """Retrieve singleton GeologyService."""
    if GeologyService._instance is None:
        GeologyService._instance = GeologyService()
    return GeologyService._instance


SIM3292GeologyService = GeologyService

