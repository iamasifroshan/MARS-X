"""
Test Suite for Phase 8.3.2: Live Browser, Raster Seam & Scientific Display Verification.

Validates:
1. CTX coordinate & pixel registration (IAU:49910 projection, affine matrices, pixel-centre offset, Euclidean distance ~3.95 m).
2. Forward and inverse affine transform mathematical consistency.
3. Quantified MOLA tile seam continuity:
   - Seam 1: Equator (megt00n000hb vs megt44n000hb).
   - Seam 2: 90 deg E meridian (megt00n000hb vs megt00n090hb).
   - Seam 3: 0/360 deg wrap (Global MOLA 4 ppd).
4. Viewport coverage calculation and progressive fallback hierarchy.
5. End-to-end benchmark elevation agreement across raw raster, live API, and client UI.
"""

import math
import os
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.elevation_service import engine
from app.terrain.provenance import TERRAIN_DATASET_PROVENANCE

client = TestClient(app)


def get_ctx_path():
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "raw",
            "ctx",
            "P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif",
        )
    )


def test_ctx_coordinate_and_pixel_registration():
    """Verify CTX coordinate projection, affine inversion, pixel-centre distance, and sampling.

    Benchmark: Tyrrhena Terra (-4.600 deg N, 66.317 deg E).
    Projection: IAU:49910 (Equirectangular, standard parallel -4.0 deg, Mars sphere R = 3396190 m).
    """
    lat = -4.600
    lon = 66.317

    ctx_path = get_ctx_path()
    assert os.path.exists(ctx_path), f"CTX raster not found at {ctx_path}"

    with rasterio.open(ctx_path) as src:
        # 1. Forward projection to IAU:49910 spherical Equirectangular
        # Formula: X = R * radians(lon), Y = R * radians(lat)
        # where R = 3396190.0 m (Mars sphere standard radius)
        r_mars = 3396190.0
        proj_x = r_mars * math.radians(lon)
        proj_y = r_mars * math.radians(lat)

        assert abs(proj_x - 3930920.12) < 0.1
        assert abs(proj_y - (-272663.61)) < 0.1

        # 2. Continuous row, col via inverse affine
        inv_transform = ~src.transform
        col_cont, row_cont = inv_transform * (proj_x, proj_y)

        assert abs(col_cont - 844.675) < 0.01
        assert abs(row_cont - 1737.409) < 0.01

        # 3. Integer pixel selection (nearest neighbor floor index)
        col_int = int(math.floor(col_cont))
        row_int = int(math.floor(row_cont))
        assert col_int == 844
        assert row_int == 1737

        # 4. Pixel centre coordinate derived from forward affine
        # In GDAL/Rasterio pixel convention, cell centre is (col + 0.5, row + 0.5)
        pixel_centre_x, pixel_centre_y = src.transform * (col_int + 0.5, row_int + 0.5)
        assert abs(pixel_centre_x - 3930916.61) < 0.1
        assert abs(pixel_centre_y - (-272665.44)) < 0.1

        # 5. Euclidean distance between query coordinate and pixel centre
        dx = proj_x - pixel_centre_x
        dy = proj_y - pixel_centre_y
        dist = math.hypot(dx, dy)
        assert abs(dist - 3.95) < 0.1
        # Offset must be strictly less than 1 pixel width (20.0128 m)
        assert dist < src.res[0]

        # 6. Raw GeoTIFF stored float32 value
        raw_val = float(src.read(1)[row_int, col_int])
        assert abs(raw_val - 2189.485) < 0.01

    # 7. Live API response verification
    res = client.get(f"/api/v1/terrain/elevation/point?lat={lat}&lon={lon}")
    assert res.status_code == 200
    data = res.json()
    assert data["elevation_m"] == 2189.49
    assert data["dataset_id"] == "ctx-dtm-p21-009323"


def test_forward_inverse_affine_consistency():
    """Verify mathematical invertibility of affine transformations across the CTX raster."""
    ctx_path = get_ctx_path()

    with rasterio.open(ctx_path) as src:
        fwd = src.transform
        inv = ~fwd

        test_pixels = [
            (0, 0),
            (src.width - 1, 0),
            (0, src.height - 1),
            (src.width - 1, src.height - 1),
            (844, 1737),
            (1000, 2000),
        ]

        for c, r in test_pixels:
            x, y = fwd * (c + 0.5, r + 0.5)
            c_back, r_back = inv * (x, y)
            assert abs(c_back - (c + 0.5)) < 1e-9
            assert abs(r_back - (r + 0.5)) < 1e-9


def test_mola_tile_seam_continuity_equator():
    """Verify numerical continuity across MOLA 128 Seam 1 (Equator: megt00n000hb vs megt44n000hb).

    Row 0 of megt00n000hb (0 to 44 N) is centered at -1/256 deg.
    Row 5631 of megt44n000hb (-44 to 0 N) is centered at +1/256 deg.
    Spacing is exactly 1/128 deg (~463 m).
    Adjacent cells must not exhibit artificial step-discontinuities or NoData.
    """
    mola_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    n_tile = os.path.join(mola_dir, "megt00n000hb.img")
    s_tile = os.path.join(mola_dir, "megt44n000hb.img")

    if not (os.path.exists(n_tile) and os.path.exists(s_tile)):
        pytest.skip("MOLA raw tiles not available locally")

    # Map raw binary int16 arrays (5632 rows x 11520 cols)
    n_data = np.memmap(n_tile, dtype=">i2", mode="r", shape=(5632, 11520))
    s_data = np.memmap(s_tile, dtype=">i2", mode="r", shape=(5632, 11520))

    # Test transect across longitudes 5, 10, 20, 30, 45, 60, 80 deg E
    sample_lons = [5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 80.0]
    for lon in sample_lons:
        col = int(math.floor(lon * 128.0))
        n_elev = int(n_data[0, col])
        s_elev = int(s_data[5631, col])

        # Both must be valid numerical elevations (not NoData 32767)
        assert n_elev != 32767
        assert s_elev != 32767

        # Elevation difference between adjacent cells (463 m apart) must reflect natural terrain slope
        delta = abs(n_elev - s_elev)
        assert delta < 200, f"Excessive seam delta at {lon} deg E: {delta} m"


def test_mola_tile_seam_continuity_90_east():
    """Verify numerical continuity across MOLA 128 Seam 2 (90 deg E: megt00n000hb vs megt00n090hb).

    Col 11519 of megt00n000hb (0 to 90 E) is at lon 89.9961 deg.
    Col 0 of megt00n090hb (90 to 180 E) is at lon 90.0039 deg.
    Spacing is 1/128 deg.
    """
    mola_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "mola"))
    w_tile = os.path.join(mola_dir, "megt00n000hb.img")
    e_tile = os.path.join(mola_dir, "megt00n090hb.img")

    if not (os.path.exists(w_tile) and os.path.exists(e_tile)):
        pytest.skip("MOLA raw tiles not available locally")

    w_data = np.memmap(w_tile, dtype=">i2", mode="r", shape=(5632, 11520))
    e_data = np.memmap(e_tile, dtype=">i2", mode="r", shape=(5632, 11520))

    # Test transect across latitudes 5, 15, 25, 35 deg N
    sample_lats = [5.0, 15.0, 25.0, 35.0]
    for lat in sample_lats:
        # Row calculation from north: (44 - lat) * 128
        row = int(math.floor((44.0 - lat) * 128.0))
        w_elev = int(w_data[row, 11519])
        e_elev = int(e_data[row, 0])

        assert w_elev != 32767
        assert e_elev != 32767

        delta = abs(w_elev - e_elev)
        assert delta < 100, f"Excessive seam delta at {lat} deg N: {delta} m"


def test_mola_prime_meridian_wrap_continuity():
    """Verify global MOLA 4 ppd continuity across the 0/360 deg prime meridian wrap."""
    elev_cog = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "data",
            "processed",
            "mola",
            "mola_megt90n000cb_elevation.tif",
        )
    )
    if not os.path.exists(elev_cog):
        pytest.skip("Global MOLA COG not found")

    with rasterio.open(elev_cog) as src:
        # Col 0 (0.125 deg E) and Col 1439 (359.875 deg E)
        # Check continuity at equator (Row 360)
        left_val = src.read(1)[360, 0]
        right_val = src.read(1)[360, 1439]

        assert left_val != src.nodata
        assert right_val != src.nodata
        # Physical terrain continuity across prime meridian
        assert abs(left_val - right_val) < 300


def test_viewport_coverage_and_fallback_logic():
    """Verify window metadata calculation and progressive fallback hierarchy."""
    # 1. Inside CTX footprint
    res_ctx = client.get("/api/v1/terrain/render/window/metadata?min_lat=-4.8&max_lat=-4.4&min_lon=66.1&max_lon=66.5")
    assert res_ctx.status_code == 200
    data_ctx = res_ctx.json()
    assert data_ctx["dataset_id"] == "ctx-dtm-p21-009323"
    assert abs(data_ctx["source_resolution_m"] - 20.0128) < 0.01

    # 2. Inside MOLA 128 multi-tile region
    res_mola128 = client.get("/api/v1/terrain/render/window/metadata?min_lat=10.0&max_lat=20.0&min_lon=10.0&max_lon=20.0")
    assert res_mola128.status_code == 200
    data_mola128 = res_mola128.json()
    assert "mola-megdr-128" in data_mola128["dataset_id"]
    assert abs(data_mola128["source_resolution_m"] - 463.08) < 0.1

    # 3. Outside high-resolution coverage -> falls back to Global MOLA
    res_global = client.get("/api/v1/terrain/render/window/metadata?min_lat=-60.0&max_lat=-50.0&min_lon=200.0&max_lon=210.0")
    assert res_global.status_code == 200
    data_global = res_global.json()
    assert data_global["dataset_id"] == "mola-megdr-4"
    assert abs(data_global["source_resolution_m"] - 14818.67) < 1.0


def test_browser_api_elevation_benchmarks():
    """Verify exact elevation agreement for all primary benchmarks."""
    benchmarks = [
        (-2.0, 5.0, -909.0, "megt00n000hb"),
        (18.65, 226.2, 20009.0, "mola-megdr-4"),
        (-4.600, 66.317, 2189.49, "ctx-dtm-p21-009323"),
    ]

    for lat, lon, expected_elev, expected_dataset_sub in benchmarks:
        res = client.get(f"/api/v1/terrain/elevation/point?lat={lat}&lon={lon}")
        assert res.status_code == 200
        data = res.json()
        assert data["elevation_m"] == expected_elev
        assert expected_dataset_sub in data["dataset_id"]
        assert data["is_nodata"] is False
        assert data["is_valid"] is True
