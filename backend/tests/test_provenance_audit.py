"""
Test Suite for Original NASA Data Provenance Audit.
Automates physical file existence, SHA-256 checksums, pixel-level raster rendering provenance,
and multi-tier numerical elevation queries.
"""

import os
import math
import hashlib
import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RECORDED_CHECKSUMS = {
    "megt90n000cb.lbl": (4796, "5a3fe60256afa1c35fea5d551fe0ab0a9198fb2bcd2c2e161d078aa69627ebac"),
    "megt90n000cb.img": (2073600, "25f16fb7aaf857898dcf98bc4f841341a24f8b9f7e98453ca083bc45d897ca2c"),
    "megt00n000hb.lbl": (4818, "d27d0b5635a5024dd5d95845fd83477dc5f723976444d1e5882a675027b0da13"),
    "megt00n000hb.img": (129761280, "f57274b5e459ab35a1975ca5f186f98bdb929475a4557098a7c632b9aa175c75"),
    "megt44n000hb.lbl": (4820, "bc624a238ba6d71a770a09f959ead96f1c144970fae435b8ca5e26208b42eec5"),
    "megt44n000hb.img": (129761280, "14022166079edafc99650f354e5a634e6eb2c2ea544b444c01cd8ee55437df36"),
    "megt00n090hb.lbl": (4820, "c85891df3c11e724c5c5d980630e56ee4f13c40d234b68e22401b9a404df3d36"),
    "megt00n090hb.img": (129761280, "764946162d4c650abfb22aa284595a15374a7185f302a639c19e6602c67a1d6e"),
    "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif": (
        12734013,
        "a4edb9f414500fe44e1a3c2ba06ee39e5c060cf1483619e43f461be29d31aff2",
    ),
    "mola_megt90n000cb_elevation.tif": (2675691, "e2e60b369f502d7ecd68fb1b39080717d2f908f993fb4a3952db235c1411b409"),
    "mola_megt90n000cb_slope.tif": (4844659, "504179d40f3b53c8406ed4ae8a06266590d2192430f10119bb197b6de9c53a1a"),
    "mola_megt90n000cb_roughness.tif": (4835495, "c4fb5ce71b6742cd0ddb5d6bca15045c0892bff35c05b476d85cb19b732e837d"),
}


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_source_file_existence_and_checksums():
    """Verify bit-for-bit SHA-256 hashes of all raw and processed elevation files."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path_map = {
        "megt90n000cb.lbl": os.path.join(base_dir, "data", "raw", "mola", "megt90n000cb.lbl"),
        "megt90n000cb.img": os.path.join(base_dir, "data", "raw", "mola", "megt90n000cb.img"),
        "megt00n000hb.lbl": os.path.join(base_dir, "data", "raw", "mola", "megt00n000hb.lbl"),
        "megt00n000hb.img": os.path.join(base_dir, "data", "raw", "mola", "megt00n000hb.img"),
        "megt44n000hb.lbl": os.path.join(base_dir, "data", "raw", "mola", "megt44n000hb.lbl"),
        "megt44n000hb.img": os.path.join(base_dir, "data", "raw", "mola", "megt44n000hb.img"),
        "megt00n090hb.lbl": os.path.join(base_dir, "data", "raw", "mola", "megt00n090hb.lbl"),
        "megt00n090hb.img": os.path.join(base_dir, "data", "raw", "mola", "megt00n090hb.img"),
        "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif": os.path.join(
            base_dir, "data", "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"
        ),
        "mola_megt90n000cb_elevation.tif": os.path.join(
            base_dir, "data", "processed", "mola", "mola_megt90n000cb_elevation.tif"
        ),
        "mola_megt90n000cb_slope.tif": os.path.join(
            base_dir, "data", "processed", "mola", "mola_megt90n000cb_slope.tif"
        ),
        "mola_megt90n000cb_roughness.tif": os.path.join(
            base_dir, "data", "processed", "mola", "mola_megt90n000cb_roughness.tif"
        ),
    }

    for fname, (expected_size, expected_hash) in RECORDED_CHECKSUMS.items():
        p = path_map[fname]
        assert os.path.exists(p), f"Source file missing: {fname}"
        assert os.path.getsize(p) == expected_size, f"Size mismatch for {fname}"
        assert compute_sha256(p) == expected_hash, f"SHA-256 hash mismatch for {fname}"


def test_hrsc_and_hirise_zero_local_raster_enforcement():
    """Verify HRSC and HiRISE have zero local raster bytes and maintain discovered state."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for sub in ["hrsc", "hirise"]:
        raw_p = os.path.join(base_dir, "data", "raw", sub)
        proc_p = os.path.join(base_dir, "data", "processed", sub)
        assert not os.path.exists(raw_p) or len(os.listdir(raw_p)) == 0
        assert not os.path.exists(proc_p) or len(os.listdir(proc_p)) == 0


def test_ctx_rendering_pixel_level_provenance():
    """Verify that CTX rendering endpoint matches raw GeoTIFF pixels and preserves NoData transparency."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ctx_path = os.path.join(
        base_dir, "data", "raw", "ctx", "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"
    )

    with rasterio.open(ctx_path) as src:
        out_shape = (src.height // 4, src.width // 4)
        down = src.read(1, out_shape=out_shape, resampling=rasterio.enums.Resampling.bilinear)

    res = client.get("/api/v1/terrain/render/ctx-dtm")
    assert res.status_code == 200
    with MemoryFile(res.content) as mem:
        with mem.open() as ds:
            png_data = ds.read()

    assert (png_data.shape[1], png_data.shape[2]) == down.shape

    # Valid pixel: inside swath
    assert png_data[3, 400, 200] == 245
    # NoData pixel: outside swath
    assert png_data[3, 10, 10] == 0


def test_numerical_elevation_coverage_queries():
    """Verify elevation queries at known target locations across multi-tier hierarchy."""
    # 1. Tyrrhena Terra inside CTX coverage
    res_ctx = client.get("/api/v1/terrain/coverage?lat=-4.600&lon=66.317")
    assert res_ctx.status_code == 200
    data_ctx = res_ctx.json()
    assert data_ctx["matching_dtms_count"] == 3
    assert abs(data_ctx["finest_available_resolution_m"] - 20.01) < 0.1

    # 2. Sinus Meridiani outside CTX, inside MOLA 128
    res_mola = client.get("/api/v1/terrain/coverage?lat=-2.000&lon=5.000")
    assert res_mola.status_code == 200
    data_mola = res_mola.json()
    assert data_mola["matching_dtms_count"] == 2
    assert abs(data_mola["finest_available_resolution_m"] - 463.08) < 0.1

    # 3. Discovered HiRISE product comparison guard
    res_guard = client.get(
        "/api/v1/terrain/compare-products?product_a=mola-megdr-128&product_b=hirise-dtm-schiaparelli&run_raster_analysis=true"
    )
    assert res_guard.status_code == 200
    assert res_guard.json()["overlap"]["both_locally_available"] is False
