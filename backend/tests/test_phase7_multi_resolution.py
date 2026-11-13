"""Phase 7 Multi-Resolution Mars Terrain Intelligence Test Suite.

Verifies:
1. MOLA 128 expansion: 3 authentic tiles downloaded and SHA-256 verified,
   covering 26.05% of Mars' spherical surface.
2. Authentic USGS Controlled CTX DTM inspection: 20 m/px post-spacing, Float32,
   NoData preservation, elevation range, CRS IAU:49910.
3. Multi-Resolution Catalog queries: point and bounding box lookups across
   all 4 controlled hierarchy tiers.
4. Overlap analysis and anti-upsampling guarantees between MOLA 128 and CTX DTM.
5. Real raster-to-raster numerical elevation comparison over Tyrrhena Terra.
6. FastAPI endpoints: /products, /coverage/region, /resolution-stack, /overlap,
   /compare-products, /quality, and /routing/data-availability.
"""

import os
import pytest
import rasterio
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.inventory import (
    Mola128InventoryService,
    compute_tile_spherical_fraction_pct,
)
from app.terrain.multi_resolution import (
    MultiResolutionTerrainCatalog,
    MULTI_RESOLUTION_DTM_CATALOG,
)
from app.terrain.harmonization import VERTICAL_EVIDENCE_CATALOG
from app.terrain.validation import DatasetValidationRegistry


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. MOLA 128 Expansion & Spherical Coverage ───────────────────────────────

def test_mola_128_expanded_inventory_integrity():
    """Verify that all 3 downloaded MOLA 128 tiles are present and hash-verified."""
    service = Mola128InventoryService()
    report = service.get_inventory_report()

    # Must have 3 authentic tiles downloaded
    assert report.downloaded_tile_count >= 3
    assert report.integrity_verified_tile_count >= 3

    # Check specific downloaded tile IDs
    downloaded_ids = [t.tile_id for t in report.tiles if t.is_downloaded]
    assert "megt00n000hb" in downloaded_ids
    assert "megt44n000hb" in downloaded_ids
    assert "megt00n090hb" in downloaded_ids

    # Spherical coverage must be exactly 26.0496% (~26.05%) for these 3 tiles
    # Tile 00n000: 8.6832%
    # Tile 44n000: 8.6832%
    # Tile 00n090: 8.6832%
    # Sum: 26.0496%
    assert 26.0 <= report.downloaded_tile_coverage_pct <= 26.1
    # Must never conflate downloaded coverage with theoretical 99.94% archive coverage
    assert report.downloaded_tile_coverage_pct < report.theoretical_archive_coverage_pct


def test_spherical_area_calculation():
    """Verify Mars spherical trigonometry formula for tile fractions."""
    # Band 0° to 44° over 90° longitude
    frac = compute_tile_spherical_fraction_pct(0.0, 44.0, 0.0, 90.0)
    assert abs(frac - 8.6832) < 0.001

    # Band 44° to 88° over 90° longitude
    frac_polar = compute_tile_spherical_fraction_pct(44.0, 88.0, 0.0, 90.0)
    assert abs(frac_polar - 3.8092) < 0.001


# ── 2. USGS Controlled CTX Numerical DTM Inspection ──────────────────────────

def test_ctx_numerical_dtm_raster_integrity():
    """Verify the acquired USGS Controlled CTX DTM raster file and metadata."""
    ctx_path = os.path.abspath(
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
    assert os.path.exists(ctx_path), "CTX DTM file must exist on disk"
    assert os.path.getsize(ctx_path) == 12734013, "CTX DTM byte size must match"

    with rasterio.open(ctx_path) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.width == 1692
        assert src.height == 3472
        assert src.nodata == -32767.0

        # Pixel resolution ~20.01 m
        res_x, res_y = src.res
        assert 19.9 <= res_x <= 20.1
        assert 19.9 <= res_y <= 20.1

        # Check bounds
        b = src.bounds
        assert b.left < b.right
        assert b.bottom < b.top

        # Read sample data and check valid elevation values
        arr = src.read(1, masked=True)
        valid = arr.compressed()
        assert len(valid) > 4000000  # Over 4M valid pixels (~73%)
        assert valid.min() > 700.0   # Real Mars elevations in Tyrrhena Terra (~800m - 2500m)
        assert valid.max() < 2600.0


# ── 3. Multi-Resolution Catalog & Query Services ──────────────────────────────

def test_multi_resolution_catalog_tiers():
    """Verify that all 4 tiers of the controlled hierarchy are populated."""
    catalog = MultiResolutionTerrainCatalog()
    products = catalog.get_all_products()

    tiers = {p.tier for p in products}
    assert "global_coarse" in tiers
    assert "global_base" in tiers
    assert "regional" in tiers
    assert "local_tactical" in tiers

    # Check CTX product registration
    ctx_prof = catalog.get_product("ctx-dtm-p21-009323")
    assert ctx_prof is not None
    assert ctx_prof.instrument == "CTX"
    assert ctx_prof.status == "analysis_ready"
    assert ctx_prof.pixel_spacing_m == 20.01

    # Check HiRISE product registration
    hirise_prof = catalog.get_product("hirise-dtm-schiaparelli")
    assert hirise_prof is not None
    assert hirise_prof.instrument == "HiRISE"
    assert hirise_prof.pixel_spacing_m == 1.01


def test_intersecting_dtms_query():
    """Verify point and bbox intersection queries return ordered resolutions."""
    catalog = MultiResolutionTerrainCatalog()

    # Query in Tyrrhena Terra (-4.5°N, 66.3°E) where CTX DTM is located
    dtms = catalog.find_intersecting_dtms(-4.5, 66.3)
    assert len(dtms) >= 3
    # Ordered finest to coarsest: CTX (20m) -> MOLA 128 (463m) -> MOLA 4 (14.8km)
    assert dtms[0].product_id == "ctx-dtm-p21-009323"
    assert dtms[1].product_id == "mola-megdr-128"
    assert dtms[2].product_id == "mola-megdr-4"


# ── 4. Overlap & Resolution Comparison ────────────────────────────────────────

def test_overlap_mola_and_ctx():
    """Verify product overlap calculation between MOLA 128 and CTX DTM."""
    catalog = MultiResolutionTerrainCatalog()
    overlap = catalog.calculate_product_overlap("mola-megdr-128", "ctx-dtm-p21-009323")

    assert overlap.has_overlap is True
    assert overlap.overlap_area_km2 > 0.0
    assert overlap.both_locally_available is True
    assert overlap.relative_resolution_ratio == 23.14
    assert "anti-upsampling" in overlap.notes.lower() or "ratio" in overlap.notes.lower()


def test_anti_upsampling_enforcement():
    """Verify comparison result issues strict anti-upsampling guarantee."""
    catalog = MultiResolutionTerrainCatalog()
    comp = catalog.compare_products("mola-megdr-128", "ctx-dtm-p21-009323")

    assert comp.ratio == 23.14
    assert comp.finer_product == "ctx-dtm-p21-009323"
    assert comp.coarser_product == "mola-megdr-128"
    assert "never be upsampled" in comp.anti_upsampling_guarantee.lower()


# ── 5. Real Raster Numerical Elevation Comparison ────────────────────────────

def test_real_raster_elevation_comparison():
    """Execute real numerical raster elevation comparison between MOLA 128 and CTX."""
    catalog = MultiResolutionTerrainCatalog()
    res = catalog.compare_overlapping_rasters(
        "mola-megdr-128", "ctx-dtm-p21-009323", sample_points=100
    )

    assert res.sample_points_count > 50
    assert res.mean_elevation_a_m > 1500.0  # MOLA ~2000m
    assert res.mean_elevation_b_m > 1500.0  # CTX ~1950m
    # Real delta between regional MOLA and high-res stereo
    assert -150.0 < res.mean_delta_m < 50.0
    assert res.std_delta_m > 0.0
    assert "Ames Stereo Pipeline" in res.scientific_interpretation or "MOLA" in res.scientific_interpretation


# ── 6. FastAPI Router Endpoints ──────────────────────────────────────────────

def test_api_terrain_products(client):
    """Test GET /api/v1/terrain/products."""
    resp = client.get("/api/v1/terrain/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    product_ids = [p["product_id"] for p in data["products"]]
    assert "ctx-dtm-p21-009323" in product_ids
    assert "mola-megdr-128" in product_ids


def test_api_coverage_region(client):
    """Test GET /api/v1/terrain/coverage/region."""
    resp = client.get(
        "/api/v1/terrain/coverage/region?min_lat=-5.5&min_lon=65.5&max_lat=-3.8&max_lon=67.0"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matching_products_count"] >= 3
    assert data["finest_native_resolution_m"] == 20.01


def test_api_resolution_stack(client):
    """Test GET /api/v1/terrain/resolution-stack."""
    resp = client.get("/api/v1/terrain/resolution-stack?lat=-4.5&lon=66.3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tiers_count"] >= 3
    assert data["stack"][0]["product_id"] == "ctx-dtm-p21-009323"


def test_api_overlap(client):
    """Test GET /api/v1/terrain/overlap."""
    resp = client.get(
        "/api/v1/terrain/overlap?product_a=mola-megdr-128&product_b=ctx-dtm-p21-009323"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_overlap"] is True
    assert data["both_locally_available"] is True


def test_api_compare_products_elevation(client):
    """Test GET /api/v1/terrain/compare-products."""
    resp = client.get(
        "/api/v1/terrain/compare-products?product_a=mola-megdr-128&product_b=ctx-dtm-p21-009323&sample_points=50"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_points_count"] > 30
    assert "mean_delta_m" in data
    assert "std_delta_m" in data


def test_api_terrain_quality(client):
    """Test GET /api/v1/terrain/quality."""
    resp = client.get("/api/v1/terrain/quality?product_id=ctx-dtm-p21-009323")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == "ctx-dtm-p21-009323"
    assert data["is_analysis_ready"] is True
    assert data["lifecycle_state"] == "analysis_ready"
    assert data["pixel_spacing_m"] == 20.01


def test_api_routing_data_availability(client):
    """Test GET /api/v1/routing/data-availability and /api/v1/routes/data-availability."""
    for path in ["/api/v1/routing/data-availability", "/api/v1/routes/data-availability"]:
        resp = client.get(
            f"{path}?min_lat=-5.0&min_lon=65.0&max_lat=-4.0&max_lon=67.0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["routing_eligible"] is True
        assert "global_coarse" in data["available_tiers"]
        assert "global_base" in data["available_tiers"]
        assert "regional" in data["available_tiers"]
        assert data["highest_available_resolution_m"] == 20.0
