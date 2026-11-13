"""Unit and integration tests for MARS-X Multi-Resolution Terrain Intelligence.

Validates:
- DTM hierarchy profiles (MOLA, HRSC, CTX, HiRISE).
- Spatial footprint intersection and point queries.
- Resolution comparison, scale ratios, and anti-upsampling guarantees.
- Vertical datum compatibility rules.
- Tile adjacency calculation for MOLA MEGDR tiles.
- REST endpoints: /api/v1/terrain/layers, /coverage, /compare, /products/{id}.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.terrain.multi_resolution import (
    MultiResolutionTerrainCatalog,
    DTMProductProfile,
    ResolutionComparisonResult,
    TileAdjacencyResult,
)

client = TestClient(app)


class TestMultiResolutionCatalog:
    """Test suite for MultiResolutionTerrainCatalog core logic."""

    def test_catalog_initialization_contains_all_tiers(self):
        """Verify the catalog contains products across multiple tiers."""
        products = MultiResolutionTerrainCatalog.get_all_products()
        assert len(products) >= 5

        tiers = {p.tier for p in products}
        assert "global_coarse" in tiers
        assert "global_base" in tiers
        assert "regional" in tiers
        assert "local_tactical" in tiers

    def test_jezero_crater_footprint_intersection(self):
        """Query Jezero Crater (18.38°N, 77.58°E) and verify multi-resolution stack."""
        lat = 18.38
        lon = 77.58

        intersecting = MultiResolutionTerrainCatalog.find_intersecting_dtms(lat, lon)
        assert len(intersecting) >= 3

        # Must be ordered finest to coarsest
        assert intersecting[0].tier == "local_tactical"
        assert intersecting[0].product_id == "hirise-dtm-jezero"
        assert intersecting[0].pixel_spacing_m == 1.0

        # Should also include CTX (20m) and MOLA (14.8km global)
        product_ids = [p.product_id for p in intersecting]
        assert "ctx-dtm-jezero" in product_ids
        assert "mola-megdr-4" in product_ids

    def test_olympus_mons_footprint_intersection(self):
        """Query Olympus Mons caldera (18.65°N, 226.20°E / -133.8°W)."""
        lat = 18.65
        lon = 226.20

        intersecting = MultiResolutionTerrainCatalog.find_intersecting_dtms(lat, lon)
        assert len(intersecting) >= 2

        product_ids = [p.product_id for p in intersecting]
        # Global MOLA must cover it
        assert "mola-megdr-4" in product_ids
        # HRSC MC-11 covers 0-30°N, 315-360°E, so 226°E is outside HRSC MC-11
        assert "hrsc-dtm-mc11" not in product_ids

    def test_compare_products_mola_to_hirise(self):
        """Compare MOLA 128 px/deg (463 m) to HiRISE (1.0 m)."""
        cmp = MultiResolutionTerrainCatalog.compare_products(
            "mola-megdr-128", "hirise-dtm-jezero"
        )
        assert cmp.finer_product == "hirise-dtm-jezero"
        assert cmp.coarser_product == "mola-megdr-128"
        assert cmp.ratio == pytest.approx(463.08, rel=1e-2)
        assert cmp.vertical_datum_compatible is True
        assert "never be upsampled" in cmp.anti_upsampling_guarantee

    def test_compare_products_invalid_id_raises_value_error(self):
        """Attempting to compare nonexistent product must fail cleanly."""
        with pytest.raises(ValueError) as excinfo:
            MultiResolutionTerrainCatalog.compare_products("mola-megdr-4", "nonexistent-dtm")
        assert "not found in catalog" in str(excinfo.value)

    def test_tile_adjacency_mola_128(self):
        """Verify neighbor calculation between MOLA tiles megt00n000hb and megt44n000hb."""
        adj = MultiResolutionTerrainCatalog.inspect_tile_adjacency("megt00n000hb", "megt44n000hb")
        assert adj.tile_a == "megt00n000hb"
        assert adj.tile_b == "megt44n000hb"
        assert adj.shares_boundary is True
        assert adj.boundary_type == "north_south"
        assert adj.common_edge_value == 0.0
        assert adj.crs_match is True
        assert adj.resolution_match is True


class TestTerrainMultiResolutionEndpoints:
    """Test suite for FastAPI multi-resolution endpoints."""

    def test_get_terrain_layers(self):
        """GET /api/v1/terrain/layers returns configured DTM layers."""
        response = client.get("/api/v1/terrain/layers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 4

        layer_ids = [layer["layer_id"] for layer in data]
        assert "mola-elevation-global" in layer_ids
        assert "mola-slope-global" in layer_ids
        assert "mola-roughness-global" in layer_ids
        assert "mola-megdr-128-tile-00n000" in layer_ids
        assert "hirise-dtm-jezero" in layer_ids

    def test_get_terrain_coverage_point_query(self):
        """GET /api/v1/terrain/coverage?lat=18.38&lon=77.58 returns Jezero stack."""
        response = client.get("/api/v1/terrain/coverage?lat=18.38&lon=77.58")
        assert response.status_code == 200
        data = response.json()

        assert data["query_coordinate"]["latitude"] == 18.38
        assert data["query_coordinate"]["longitude"] == 77.58
        assert data["finest_available_resolution_m"] == 1.0
        assert data["matching_dtms_count"] >= 3

        covering_ids = [d["product_id"] for d in data["covering_dtms"]]
        assert "hirise-dtm-jezero" in covering_ids

    def test_get_terrain_coverage_full_catalog(self):
        """GET /api/v1/terrain/coverage without params returns catalog tier overview."""
        response = client.get("/api/v1/terrain/coverage")
        assert response.status_code == 200
        data = response.json()
        assert "catalog_tiers" in data
        assert "products" in data
        assert len(data["products"]) >= 5

    def test_compare_terrain_resolutions_endpoint(self):
        """GET /api/v1/terrain/compare?product_a=...&product_b=... returns ratio and anti-upsampling note."""
        response = client.get(
            "/api/v1/terrain/compare?product_a=mola-megdr-4&product_b=ctx-dtm-jezero"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["product_a"] == "mola-megdr-4"
        assert data["product_b"] == "ctx-dtm-jezero"
        assert data["ratio"] > 700.0
        assert data["finer_product"] == "ctx-dtm-jezero"
        assert "never be upsampled" in data["anti_upsampling_guarantee"]

    def test_compare_terrain_resolutions_not_found(self):
        """GET /api/v1/terrain/compare with invalid ID returns 404."""
        response = client.get(
            "/api/v1/terrain/compare?product_a=invalid-1&product_b=invalid-2"
        )
        assert response.status_code == 404

    def test_get_product_profile(self):
        """GET /api/v1/terrain/products/{id} returns full product profile."""
        response = client.get("/api/v1/terrain/products/hirise-dtm-jezero")
        assert response.status_code == 200
        data = response.json()

        assert data["product_id"] == "hirise-dtm-jezero"
        assert data["tier"] == "local_tactical"
        assert data["pixel_spacing_m"] == 1.0
        assert data["vertical_datum"] == "MOLA Areoid (tied)"
        assert data["source_archive"] == "University of Arizona HiRISE DTM Archive / NASA PDS"
        assert data["lat_min"] == 18.30
        assert data["lat_max"] == 18.55
