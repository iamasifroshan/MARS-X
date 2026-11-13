"""PDS3 label parser and binary raster reader for MOLA MEGDR products.

Parses official NASA Planetary Data System (PDS3) label files (.lbl) and reads
associated fixed-record binary raster images (.img).
"""

import os
import re
import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("MARS-X.terrain.pds_parser")


class PDS3LabelParser:
    """Parses PDS3 text labels into structured key-value dictionaries and object hierarchies."""

    @staticmethod
    def parse_label_file(lbl_path: str) -> Dict[str, Any]:
        """Parse a PDS3 label file (.lbl) into a nested Python dictionary."""
        if not os.path.exists(lbl_path):
            raise FileNotFoundError(f"PDS3 label file not found: {lbl_path}")

        with open(lbl_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return PDS3LabelParser.parse_label_text(content)

    @staticmethod
    def parse_label_text(text: str) -> Dict[str, Any]:
        """Parse raw PDS3 label text."""
        result: Dict[str, Any] = {}
        current_obj: Optional[str] = None
        obj_dict: Dict[str, Any] = {}

        # Remove comments
        cleaned = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

        lines = cleaned.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("/*"):
                continue

            if line == "END":
                break

            # Object starts
            match_obj_start = re.match(r"^OBJECT\s*=\s*([A-Za-z0-9_]+)", line)
            if match_obj_start:
                current_obj = match_obj_start.group(1).upper()
                obj_dict = {}
                continue

            # Object ends
            match_obj_end = re.match(r"^END_OBJECT\s*=\s*([A-Za-z0-9_]+)", line)
            if match_obj_end:
                obj_name = match_obj_end.group(1).upper()
                if current_obj == obj_name:
                    result[current_obj] = obj_dict
                    current_obj = None
                    obj_dict = {}
                continue

            # Key-value pair
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip().upper()
                val = val.strip().strip('"').strip("'")
                # Remove unit annotations like <KM> or <DEGREE>
                val_clean = re.sub(r"<[A-Za-z/]+>", "", val).strip()

                target = obj_dict if current_obj else result
                target[key] = val_clean

        return result


def read_pds3_image_binary(
    img_path: str,
    lbl_data: Dict[str, Any],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Read raw PDS3 binary raster (.img) based on parameters in the PDS3 label (.lbl).

    Returns:
        (elevation_array_2d, metadata_dict)
    """
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"PDS3 binary image not found: {img_path}")

    img_obj = lbl_data.get("IMAGE", {})
    if not img_obj:
        raise ValueError("PDS label does not contain an OBJECT = IMAGE section.")

    lines = int(img_obj.get("LINES", 0))
    line_samples = int(img_obj.get("LINE_SAMPLES", 0))
    sample_bits = int(img_obj.get("SAMPLE_BITS", 16))
    sample_type = img_obj.get("SAMPLE_TYPE", "MSB_INTEGER").upper()

    if lines <= 0 or line_samples <= 0:
        raise ValueError(f"Invalid raster dimensions in PDS label: LINES={lines}, SAMPLES={line_samples}")

    # Determine dtype from PDS3 sample type
    if sample_bits == 16:
        if "MSB" in sample_type or "SUN" in sample_type or "MAC" in sample_type:
            dtype = np.dtype(">i2")  # Big-Endian signed 16-bit integer
        else:
            dtype = np.dtype("<i2")  # Little-Endian signed 16-bit integer
    elif sample_bits == 32:
        if "REAL" in sample_type or "FLOAT" in sample_type:
            dtype = np.dtype(">f4") if "MSB" in sample_type else np.dtype("<f4")
        else:
            dtype = np.dtype(">i4") if "MSB" in sample_type else np.dtype("<i4")
    elif sample_bits == 8:
        dtype = np.dtype("u1") if "UNSIGNED" in sample_type else np.dtype("i1")
    else:
        raise ValueError(f"Unsupported PDS3 SAMPLE_BITS: {sample_bits}")

    expected_bytes = lines * line_samples * (sample_bits // 8)
    file_size = os.path.getsize(img_path)

    # Calculate offset if header is embedded
    offset = 0
    if file_size > expected_bytes:
        record_bytes = int(lbl_data.get("RECORD_BYTES", 0))
        img_pointer = lbl_data.get("^IMAGE")
        if isinstance(img_pointer, int) and record_bytes > 0:
            offset = (img_pointer - 1) * record_bytes

    with open(img_path, "rb") as f:
        if offset > 0:
            f.seek(offset)
        raw_bytes = f.read(expected_bytes)

    data = np.frombuffer(raw_bytes, dtype=dtype).reshape((lines, line_samples))

    # Convert to standard machine endianness for downstream NumPy processing
    data = data.astype(np.float32)

    proj_obj = lbl_data.get("IMAGE_MAP_PROJECTION", {})
    metadata = {
        "lines": lines,
        "line_samples": line_samples,
        "sample_type": sample_type,
        "sample_bits": sample_bits,
        "unit": img_obj.get("UNIT", "METER"),
        "map_projection_type": proj_obj.get("MAP_PROJECTION_TYPE", "SIMPLE CYLINDRICAL"),
        "map_resolution_ppd": float(proj_obj.get("MAP_RESOLUTION", 4.0)),
        "max_latitude": float(proj_obj.get("MAXIMUM_LATITUDE", 90.0)),
        "min_latitude": float(proj_obj.get("MINIMUM_LATITUDE", -90.0)),
        "west_longitude": float(proj_obj.get("WESTERNMOST_LONGITUDE", 0.0)),
        "east_longitude": float(proj_obj.get("EASTERNMOST_LONGITUDE", 360.0)),
        "a_axis_radius_km": float(proj_obj.get("A_AXIS_RADIUS", 3396.0)),
        "coordinate_system": proj_obj.get("COORDINATE_SYSTEM_NAME", "PLANETOCENTRIC"),
    }

    return data, metadata

