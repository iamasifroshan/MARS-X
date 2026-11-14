"""
Test Suite for Phase 8.4: Original Scientific Data Integrity & Provenance Enforcement.

Validates:
1. Complete provenance registry structure and schema compliance (POL-SCI-001).
2. Bit-for-bit cryptographic SHA-256 verification of all authentic local planetary datasets.
3. Strict documentation and lineage traceability for derived rasters (elevation COG, slope COG, roughness COG).
4. Strict isolation of test fixtures and prohibition of synthetic elevation data in production.
5. Explicit unviability reporting for catalogued but non-ingested datasets.
6. Mathematical and physical verification of MOLA 128 tile seam continuity and correct tile orientation.
"""

import os
import json
import math
import hashlib
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.validation import DatasetValidationRegistry, DatasetLifecycleState
from app.terrain.multi_resolution import MultiResolutionTerrainCatalog
from app.terrain.provenance import TERRAIN_DATASET_PROVENANCE

client = TestClient(app)

REGISTRY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "docs", "research", "dataset_provenance_registry.json")
)


def _compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_provenance_registry_exists_and_valid():
    """Verify that dataset_provenance_registry.json exists, parses cleanly, and adheres to POL-SCI-001."""
    assert os.path.exists(REGISTRY_PATH), f"Registry missing at {REGISTRY_PATH}"
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    assert registry.get("policy_compliance") == "POL-SCI-001"
    assert "datasets" in registry
    assert len(registry["datasets"]) >= 10

    required_keys = [
        "dataset_id",
        "product_id",
        "mission",
        "instrument",
        "provenance_status",
        "crs",
        "vertical_datum",
        "units",
        "nodata_value",
        "local_availability",
    ]

    for ds in registry["datasets"]:
        for key in required_keys:
            assert key in ds, f"Dataset {ds.get('dataset_id')} missing required key '{key}'"
        assert ds["provenance_status"] in [
            "authoritative_original",
            "derived_with_lineage",
            "catalogued_unavailable",
        ]


def test_authoritative_original_checksums_match_local_files():
    """Verify cryptographic SHA-256 checksums of all locally available original products."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    for ds in registry["datasets"]:
        if ds["provenance_status"] == "authoritative_original" and ds["local_availability"] == "available":
            for file_role, rel_path in ds.get("local_files", {}).items():
                abs_path = os.path.join(project_root, rel_path)
                assert os.path.exists(abs_path), f"File {rel_path} declared available but missing on disk"
                actual_sha = _compute_sha256(abs_path)
                expected_sha = ds["sha256"][file_role]
                assert actual_sha == expected_sha, (
                    f"Checksum mismatch for {rel_path}!\n"
                    f"Expected: {expected_sha}\n"
                    f"Actual:   {actual_sha}"
                )


def test_derived_products_have_traceable_lineage():
    """Verify that every derived raster has documented lineage and identical dimensions to source."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    derived_datasets = [d for d in registry["datasets"] if d["provenance_status"] == "derived_with_lineage"]
    assert len(derived_datasets) == 3  # elevation, slope, roughness

    for ds in derived_datasets:
        lineage = ds["derivation_lineage"]
        assert "source_file" in lineage
        assert "source_sha256" in lineage
        assert "processing_script" in lineage
        assert "algorithm" in lineage
        assert "output_dimensions" in lineage

        abs_path = os.path.join(project_root, ds["local_filename"])
        assert os.path.exists(abs_path), f"Derived file {ds['local_filename']} missing on disk"

        with rasterio.open(abs_path) as src:
            assert src.height == lineage["output_dimensions"]["lines"]
            assert src.width == lineage["output_dimensions"]["samples"]
            assert src.nodata == ds["nodata_value"]


def test_test_fixtures_isolated_from_production():
    """Verify that test fixtures and mock directories do not exist in production data directories."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    raw_dir = os.path.join(project_root, "data", "raw")
    proc_dir = os.path.join(project_root, "data", "processed")

    for d in [raw_dir, proc_dir]:
        for root, dirs, files in os.walk(d):
            for fname in files:
                lower = fname.lower()
                assert not lower.startswith("test_"), f"Test file {fname} found in production data dir {root}"
                assert not lower.startswith("mock_"), f"Mock file {fname} found in production data dir {root}"
                assert not "dummy" in lower, f"Dummy file {fname} found in production data dir {root}"
                assert not "synthetic" in lower, f"Synthetic file {fname} found in production data dir {root}"


def test_unavailable_datasets_are_strictly_marked_unavailable():
    """Verify that catalogued but non-downloaded datasets are explicitly reported as unavailable."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    unavailable_ids = {
        d["dataset_id"] for d in registry["datasets"] if d["provenance_status"] == "catalogued_unavailable"
    }
    assert len(unavailable_ids) >= 4

    catalog = MultiResolutionTerrainCatalog()
    for pid in unavailable_ids:
        report = DatasetValidationRegistry.get_report(pid)
        if report:
            assert report.raster_available_locally is False
            assert report.is_analysis_ready is False
            assert report.lifecycle_state in [
                DatasetLifecycleState.DISCOVERED,
                DatasetLifecycleState.UNAVAILABLE,
            ]


def test_no_synthetic_elevation_in_production_endpoints():
    """Verify that production API elevation queries return authentic planetary sources, never mocks."""
    test_coords = [
        (-2.0, 5.0, "megt00n000hb"),
        (18.65, 226.2, "mola-megdr-4"),
        (-4.600, 66.317, "ctx-dtm-p21-009323"),
    ]

    for lat, lon, expected_src in test_coords:
        res = client.get(f"/api/v1/terrain/elevation/point?lat={lat}&lon={lon}")
        assert res.status_code == 200
        data = res.json()
        assert data["elevation_m"] is not None
        assert expected_src in data["dataset_id"]
        assert data["is_nodata"] is False
        assert data["is_valid"] is True


def test_mola_seam_1_equator_correct_adjacency():
    """Verify Seam 1 (Equator) with correct PDS tile orientation.

    North Tile: megt44n000hb (covers 0 to +44 N). Bottom line is Row 5631 (lat = +0.0039 deg).
    South Tile: megt00n000hb (covers -44 to 0 N). Top line is Row 0 (lat = -0.0039 deg).
    Spacing is exactly 1/128 deg (~463.08 m).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    n_path = os.path.join(project_root, "data", "raw", "mola", "megt44n000hb.img")
    s_path = os.path.join(project_root, "data", "raw", "mola", "megt00n000hb.img")

    if not (os.path.exists(n_path) and os.path.exists(s_path)):
        pytest.skip("MOLA 128 tiles missing locally")

    n_tile = np.memmap(n_path, dtype=">i2", mode="r", shape=(5632, 11520))
    s_tile = np.memmap(s_path, dtype=">i2", mode="r", shape=(5632, 11520))

    # Test across transect points from 0 to 90 deg E
    sample_lons = [0.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 75.0, 89.5]
    for lon in sample_lons:
        col = int(math.floor(lon * 128.0))
        val_n = int(n_tile[5631, col])
        val_s = int(s_tile[0, col])

        assert val_n != -32768
        assert s_tile[0, col] != -32768

        diff = abs(val_n - val_s)
        # Natural terrain slopes across 463 m must be physically reasonable (< 150 m)
        assert diff < 150, f"Seam 1 discontinuity at lon {lon} deg E: diff = {diff} m"


def test_mola_seam_2_90_east_correct_adjacency():
    """Verify Seam 2 (90 deg E Meridian) adjacency between megt00n000hb and megt00n090hb.

    West Tile: megt00n000hb (covers 0 to 90 E, -44 to 0 N). Rightmost line is Col 11519.
    East Tile: megt00n090hb (covers 90 to 180 E, -44 to 0 N). Leftmost line is Col 0.
    Spacing is exactly 1/128 deg * cos(lat).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    w_path = os.path.join(project_root, "data", "raw", "mola", "megt00n000hb.img")
    e_path = os.path.join(project_root, "data", "raw", "mola", "megt00n090hb.img")

    if not (os.path.exists(w_path) and os.path.exists(e_path)):
        pytest.skip("MOLA 128 tiles missing locally")

    w_tile = np.memmap(w_path, dtype=">i2", mode="r", shape=(5632, 11520))
    e_tile = np.memmap(e_path, dtype=">i2", mode="r", shape=(5632, 11520))

    sample_lats = [0.0, -5.0, -10.0, -15.0, -20.0, -25.0, -30.0, -35.0, -40.0, -43.5]
    for lat in sample_lats:
        row = int(math.floor(abs(lat) * 128.0))
        val_w = int(w_tile[row, 11519])
        val_e = int(e_tile[row, 0])

        assert val_w != -32768
        assert val_e != -32768

        diff = abs(val_w - val_e)
        assert diff < 50, f"Seam 2 discontinuity at lat {lat} deg N: diff = {diff} m"

