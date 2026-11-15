import os
import hashlib
import csv
import json
import struct
import pytest

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DOCS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs"))
PROJECT_ROOT = os.path.abspath(os.path.join(DATA_ROOT, ".."))

def test_registry_to_inventory_consistency():
    reg_path = os.path.join(DOCS_ROOT, "research", "dataset_provenance_registry.json")
    inv_path = os.path.join(DATA_ROOT, "manifests", "acquisition_inventory.csv")
    assert os.path.exists(reg_path)
    assert os.path.exists(inv_path)

    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)
    with open(inv_path, "r", encoding="utf-8") as f:
        inv_rows = list(csv.DictReader(f))

    inv_paths = {r["relative_path"].replace("\\", "/"): r for r in inv_rows}

    # Every downloaded_verified or downloaded_validation_pending dataset in originals must be in inventory
    for ds in reg["datasets"]:
        if ds.get("production_status") in ["downloaded_verified", "downloaded_validation_pending"]:
            local_files = ds.get("local_files", {})
            for key, rel_p in local_files.items():
                norm_p = rel_p.replace("\\", "/")
                if norm_p.startswith("data/originals/") or norm_p.startswith("data/visualization/"):
                    assert norm_p in inv_paths, f"Dataset {ds['dataset_id']} file {norm_p} not found in acquisition_inventory.csv"

def test_inventory_to_physical_file_existence():
    inv_path = os.path.join(DATA_ROOT, "manifests", "acquisition_inventory.csv")
    with open(inv_path, "r", encoding="utf-8") as f:
        inv_rows = list(csv.DictReader(f))

    assert len(inv_rows) == 34, f"Expected exactly 34 inventory records, got {len(inv_rows)}"
    for r in inv_rows:
        rel_p = r["relative_path"].replace("/", os.sep)
        full_p = os.path.join(PROJECT_ROOT, rel_p)
        assert os.path.exists(full_p), f"Physical file missing for inventory entry: {rel_p}"
        actual_size = os.path.getsize(full_p)
        expected_size = int(r["size_bytes"])
        assert actual_size == expected_size, f"Size mismatch for {rel_p}: expected {expected_size}, got {actual_size}"

def test_sha256_manifest_consistency():
    sha_path = os.path.join(DATA_ROOT, "manifests", "checksums.sha256")
    with open(sha_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    assert len(lines) >= 34, f"Expected at least 34 checksum records, got {len(lines)}"
    for line in lines:
        expected_sha, rel_p = line.split(maxsplit=1)
        full_p = os.path.join(PROJECT_ROOT, rel_p.replace("/", os.sep))
        assert os.path.exists(full_p), f"File {rel_p} does not exist"

        hasher = hashlib.sha256()
        with open(full_p, "rb") as bf:
            while chunk := bf.read(1024 * 1024):
                hasher.update(chunk)
        assert hasher.hexdigest().lower() == expected_sha.lower(), f"SHA-256 mismatch for {rel_p}"

def test_product_id_consistency_and_reconciliation():
    reg_path = os.path.join(DOCS_ROOT, "research", "dataset_provenance_registry.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    # 1. CTX: Distinguish operational Tyrrhena DTM from controlled DTM
    ctx_op = next(d for d in reg["datasets"] if d["dataset_id"] == "ctx-dtm-p21-009323")
    assert ctx_op["product_id"] == "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W"
    assert os.path.exists(os.path.join(PROJECT_ROOT, ctx_op["local_files"]["dtm"].replace("/", os.sep)))

    ctx_ctrl = next(d for d in reg["datasets"] if d["dataset_id"] == "ctx-dtm-controlled-t01-000893")
    assert "T01_000893" in ctx_ctrl["product_id"]
    assert os.path.exists(os.path.join(PROJECT_ROOT, ctx_ctrl["local_files"]["geotiff"].replace("/", os.sep)))

    # 2. HiRISE: DTEEC_011635 physically exists; DTEEC_042858/DTEEC_017118 are catalogued unavailable
    hirise_ctrl = next(d for d in reg["datasets"] if d["dataset_id"] == "hirise-dtm-controlled-esp-011635")
    assert "011635" in hirise_ctrl["original_filename"]
    assert os.path.exists(os.path.join(PROJECT_ROOT, hirise_ctrl["local_files"]["geotiff"].replace("/", os.sep)))

    hirise_jez = next(d for d in reg["datasets"] if d["dataset_id"] == "hirise-dtm-jezero")
    assert hirise_jez["production_status"] == "unavailable"

    # 3. MOLA 128 ppd: MEGT00N000HB (128 ppd, 129,761,280 bytes) verified on disk
    mola_128 = next(d for d in reg["datasets"] if d["dataset_id"] == "mola-megdr-128-00n000")
    assert mola_128["product_id"] == "MEGT00N000HB"
    mola_img_path = os.path.join(PROJECT_ROOT, mola_128["local_files"]["image"].replace("/", os.sep))
    assert os.path.exists(mola_img_path)
    assert os.path.getsize(mola_img_path) == 129761280

def test_themis_regional_vs_global_classification():
    reg_path = os.path.join(DOCS_ROOT, "research", "dataset_provenance_registry.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    # THEMIS IR mosaics are regional
    themis_ds = next(d for d in reg["datasets"] if d["dataset_id"] == "themis-ir-mosaics-regional")
    assert "regional" in themis_ds["dataset_id"]
    assert "regional" in themis_ds["product_id"].lower()
    # Footprint must be 0-30S, 0-30E
    assert "lat -30 to 0" in themis_ds["native_resolution"]["footprint"]

    # MGS TES Thermal Inertia is global
    tes_ds = next(d for d in reg["datasets"] if d["dataset_id"] == "tes-thermal-inertia-putzig-2007")
    assert "global" in tes_ds["archive_collection"].lower()

def test_themis_measurement_semantics():
    # Verify bit depth of PNG tiles is 8-bit (qualitative visualization)
    for name in ["thm_dir_N-30_000.png", "themis_nightir_N-30_000.png"]:
        p = os.path.join(DATA_ROOT, "originals", "themis", name)
        assert os.path.exists(p)
        with open(p, "rb") as f:
            sig = f.read(8)
            assert sig == b"\x89PNG\r\n\x1a\n"
            f.seek(16)
            w, h = struct.unpack(">II", f.read(8))
            bit_depth, color_type = struct.unpack("BB", f.read(2))
            assert (w, h) == (7680, 7680)
            assert bit_depth == 8, "Expected 8-bit visual display PNG"

def test_geological_gis_features_and_crs():
    gis_root = os.path.join(DATA_ROOT, "derived", "geology", "sim3292_database", "SIM3292_MarsGlobalGeologicGIS_20M")
    assert os.path.exists(gis_root), "Extracted GIS directory missing"

    # Verify SHP and DBF feature counts
    shp_geol = os.path.join(gis_root, "SIM3292_Shapefiles", "SIM3292_Global_Geology.shp")
    dbf_geol = os.path.join(gis_root, "SIM3292_Shapefiles", "SIM3292_Global_Geology.dbf")
    prj_geol = os.path.join(gis_root, "SIM3292_Shapefiles", "SIM3292_Global_Geology.prj")
    assert os.path.exists(shp_geol)
    assert os.path.exists(dbf_geol)
    assert os.path.exists(prj_geol)

    with open(dbf_geol, "rb") as f:
        dbf_hdr = f.read(32)
        num_records, = struct.unpack("<I", dbf_hdr[4:8])
        assert num_records == 1311, f"Expected 1,311 geological polygons, got {num_records}"

    with open(prj_geol, "r", encoding="utf-8", errors="ignore") as f:
        prj_text = f.read()
        assert "GCS_Mars_2000_Sphere" in prj_text
        assert "3396190.0" in prj_text

def test_pending_products_excluded_from_incompatible_processing():
    reg_path = os.path.join(DOCS_ROOT, "research", "dataset_provenance_registry.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    # HRSC is validation_pending due to spherical datum
    hrsc_ds = next(d for d in reg["datasets"] if d["dataset_id"] == "hrsc-dtm-h0018")
    assert hrsc_ds["production_status"] == "downloaded_validation_pending"
    assert "HEIGHT_ABOVE_SPHEROID" in hrsc_ds["vertical_datum"]
    assert "areoid" in hrsc_ds["validation_note"].lower()

    # CRISM is validation_pending due to corrections OFF
    crism_ds = next(d for d in reg["datasets"] if d["dataset_id"] == "crism-targeted-rdr-frt000027b2")
    assert crism_ds["production_status"] == "downloaded_validation_pending"
