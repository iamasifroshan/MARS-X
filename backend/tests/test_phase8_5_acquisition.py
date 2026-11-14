import os
import hashlib
import csv
import json
import pytest

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DOCS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs"))

def test_manifests_exist_and_populated():
    inv_path = os.path.join(DATA_ROOT, "manifests", "acquisition_inventory.csv")
    sha_path = os.path.join(DATA_ROOT, "manifests", "checksums.sha256")
    assert os.path.exists(inv_path), f"Missing {inv_path}"
    assert os.path.exists(sha_path), f"Missing {sha_path}"

    with open(inv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) >= 30, f"Expected at least 30 records, got {len(reader)}"

    with open(sha_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        assert len(lines) >= 30, f"Expected at least 30 checksums, got {len(lines)}"

def test_sha256_checksums_match_files_on_disk():
    sha_path = os.path.join(DATA_ROOT, "manifests", "checksums.sha256")
    project_root = os.path.abspath(os.path.join(DATA_ROOT, ".."))

    with open(sha_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            expected_sha, rel_path = line.split(maxsplit=1)
            full_path = os.path.join(project_root, rel_path.replace("/", os.sep))
            assert os.path.exists(full_path), f"File in manifest does not exist: {full_path}"
            assert os.path.getsize(full_path) > 0, f"File in manifest is 0 bytes: {full_path}"

            hasher = hashlib.sha256()
            with open(full_path, "rb") as bf:
                while chunk := bf.read(1024 * 1024):
                    hasher.update(chunk)
            actual_sha = hasher.hexdigest()
            assert actual_sha == expected_sha, f"SHA-256 mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}"

def test_published_checksums_match():
    # HRSC MEX Level 4 DTM MD5
    hrsc_path = os.path.join(DATA_ROOT, "originals", "hrsc", "h0018_0000_dt4.img")
    assert os.path.exists(hrsc_path)
    md5_hrsc = hashlib.md5(open(hrsc_path, "rb").read()).hexdigest().upper()
    assert md5_hrsc == "BFAF16E930228E9C9ACA7E10B396446F", f"HRSC MD5 mismatch: {md5_hrsc}"

    # CRISM Targeted RDR MD5
    crism_path = os.path.join(DATA_ROOT, "originals", "crism", "frt000027b2_01_if156l_trr3.img")
    assert os.path.exists(crism_path)
    md5_crism = hashlib.md5(open(crism_path, "rb").read()).hexdigest().upper()
    assert md5_crism == "6935C24B14926ABD43BED6B63F750A2F", f"CRISM MD5 mismatch: {md5_crism}"

def test_provenance_registry_contains_new_datasets():
    reg_path = os.path.join(DOCS_ROOT, "research", "dataset_provenance_registry.json")
    assert os.path.exists(reg_path)
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    dataset_ids = {d["dataset_id"] for d in reg["datasets"]}
    expected_new = {
        "hrsc-dtm-h0018",
        "ctx-dtm-controlled-t01-000893",
        "hirise-dtm-controlled-esp-011635",
        "tes-thermal-inertia-putzig-2007",
        "usgs-geology-sim3292",
        "crism-targeted-rdr-frt000027b2",
        "meda-environmental-sol0001",
        "rems-environmental-sol0001",
        "nasa-3d-visualization-assets"
    }
    for eid in expected_new:
        assert eid in dataset_ids, f"Expected {eid} in dataset provenance registry"

def test_separation_of_3d_assets_from_numerical_dtms():
    vis_dir = os.path.join(DATA_ROOT, "visualization", "nasa_3d")
    assert os.path.exists(vis_dir)
    vis_files = os.listdir(vis_dir)
    assert any(f.endswith(".glb") for f in vis_files), "Expected .glb in visualization directory"

    # Enforce POL-SCI-001: No .glb meshes in originals or raw
    for root_dir in [os.path.join(DATA_ROOT, "originals"), os.path.join(DATA_ROOT, "raw")]:
        for root, dirs, files in os.walk(root_dir):
            for f in files:
                assert not f.endswith(".glb"), f"3D mesh {f} found in numerical directory {root}!"

def test_pds_labels_parseable():
    crism_lbl = os.path.join(DATA_ROOT, "originals", "crism", "frt000027b2_01_if156l_trr3.lbl")
    assert os.path.exists(crism_lbl)
    with open(crism_lbl, "r", encoding="latin1") as f:
        text = f.read()
        assert "PDS_VERSION_ID" in text
        assert "CRISM" in text or "MRO" in text

    hirise_lbl = os.path.join(DATA_ROOT, "originals", "hirise", "ESP_011635_1510_RED_A_02_ORTHO.LBL")
    assert os.path.exists(hirise_lbl)
    with open(hirise_lbl, "r", encoding="latin1") as f:
        text = f.read()
        assert "PDS_VERSION_ID" in text
        assert "HIRISE" in text or "MRO" in text
