"""Phase 8.7: Science Discovery System Test Suite.

Verifies:
1. Discovery categories catalog and metadata.
2. Evidence-based discovery candidate filtering (category, bounding box, search).
3. Mars spherical Haversine distance calculations and longitude wraparound.
4. Location science opportunity profiles (elevation, geology, thermal, structures, contacts).
5. Nearby discoveries spatial queries.
6. Multi-location comparative science profiling.
7. Separation of direct observations, derived measurements, and scientific hypotheses.
8. Benchmark preservation (+2189.49 m, -2930.77 m, -1132.14 m).
"""

import math
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.science.discovery_service import (
    get_discovery_service,
    mars_haversine_distance_km,
    MARS_RADIUS_KM,
)

client = TestClient(app)


def test_discovery_categories():
    """Verify all 6 discovery categories with counts and metadata."""
    resp = client.get("/api/v1/discovery/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) == 6

    cat_ids = [c["id"] for c in cats]
    expected_ids = [
        "high_res_terrain",
        "landing_site",
        "geological_unit_contact",
        "structural_feature",
        "thermal_contrast",
        "multi_dataset_intersection",
    ]
    for eid in expected_ids:
        assert eid in cat_ids

    # Every category must have at least one candidate discovery
    for c in cats:
        assert c["discovery_count"] >= 1
        assert "title" in c
        assert "description" in c


def test_discovery_list_and_filters():
    """Verify discovery listing, category filtering, search, and bounding box queries."""
    # 1. Full list
    resp_all = client.get("/api/v1/discovery/list")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["total_count"] >= 18
    assert len(data_all["discoveries"]) >= 18

    # 2. Filter by category
    resp_terr = client.get("/api/v1/discovery/list?category=high_res_terrain")
    assert resp_terr.status_code == 200
    data_terr = resp_terr.json()
    assert data_terr["returned_count"] == 3
    for d in data_terr["discoveries"]:
        assert d["category"] == "high_res_terrain"

    # 3. Filter by search query
    resp_search = client.get("/api/v1/discovery/list?search=Holden")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert data_search["returned_count"] >= 1
    assert any("Holden" in d["title"] for d in data_search["discoveries"])

    # 4. Viewport bounding box filter
    resp_bbox = client.get("/api/v1/discovery/list?min_lat=-10&max_lat=10&min_lon=0&max_lon=80")
    assert resp_bbox.status_code == 200
    data_bbox = resp_bbox.json()
    assert data_bbox["returned_count"] >= 2
    for d in data_bbox["discoveries"]:
        assert -10 <= d["latitude"] <= 10

    # 5. Invalid bbox error handling
    resp_inv = client.get("/api/v1/discovery/list?min_lat=20&max_lat=10")
    assert resp_inv.status_code == 400


def test_mars_haversine_distance_and_wraparound():
    """Verify Mars spherical geodesic distance and antimeridian longitude wrapping."""
    # 1. Distance along equator for 1 degree: (2 * pi * 3396.19) / 360 = ~59.27 km
    d_1deg = mars_haversine_distance_km(0.0, 0.0, 0.0, 1.0)
    assert round(d_1deg, 2) == 59.27

    # 2. Pole to equator: pi * R / 2 = ~5334.79 km
    d_pole = mars_haversine_distance_km(0.0, 0.0, 90.0, 0.0)
    expected_pole = (math.pi * MARS_RADIUS_KM) / 2.0
    assert abs(d_pole - expected_pole) < 0.1

    # 3. Longitude wraparound across antimeridian: 179°E to -179°W is 2° apart (~118.5 km), NOT 358°!
    d_wrap = mars_haversine_distance_km(0.0, 179.0, 0.0, -179.0)
    assert round(d_wrap, 1) == round(2.0 * d_1deg, 1)

    # 4. Identical coordinates must have 0 distance
    d_zero = mars_haversine_distance_km(-4.6, 66.317, -4.6, 66.317)
    assert d_zero == 0.0


def test_single_discovery_enrichment():
    """Verify single discovery retrieval returns live co-registered measurements."""
    resp = client.get("/api/v1/discovery/disc-terr-tyrrhena-ctx")
    assert resp.status_code == 200
    disc = resp.json()

    assert disc["id"] == "disc-terr-tyrrhena-ctx"
    assert disc["category"] == "high_res_terrain"
    assert disc["evidence_strength"] == "confirmed_multi_dataset"
    assert "live_measurements" in disc

    live = disc["live_measurements"]
    assert live["derived_measurements"]["elevation"]["elevation_m"] == 2189.49
    assert live["derived_measurements"]["geological_mapping"]["unit"] == "eNh"
    assert live["indicative_proxies"]["thermal_inertia"]["calibrated_thermal_inertia_estimate_tiu"] is not None

    # Not found
    resp_404 = client.get("/api/v1/discovery/non-existent-id")
    assert resp_404.status_code == 404


def test_location_science_profile_tyrrhena():
    """Verify comprehensive science profile generation at Tyrrhena Terra benchmark."""
    resp = client.get("/api/v1/discovery/profile?lat=-4.600&lon=66.317")
    assert resp.status_code == 200
    prof = resp.json()

    # Coordinates
    assert prof["coordinates"]["latitude"] == -4.6
    assert prof["coordinates"]["longitude_deg_e"] == 66.317

    # Direct observations
    direct = prof["direct_observations"]
    assert direct["high_resolution_dtm_coverage"]["has_high_res_dtm"] is True
    assert direct["high_resolution_dtm_coverage"]["tyrrhena_ctx_coverage"] is True

    # Derived measurements
    derived = prof["derived_measurements"]
    assert derived["elevation"]["elevation_m"] == 2189.49
    assert derived["elevation"]["tier"] == "local_high_resolution"
    assert derived["geological_mapping"]["unit"] == "eNh"
    assert derived["geological_mapping"]["chronostratigraphic_period"] == "Noachian"
    assert derived["nearest_structural_feature"] is not None

    # Indicative proxies
    indicative = prof["indicative_proxies"]
    assert indicative["thermal_inertia"]["calibrated_thermal_inertia_estimate_tiu"] is not None
    assert indicative["thermal_inertia"]["units"] == "J m^-2 K^-1 s^-1/2 (Thermal Inertia Units, tiu)"
    assert "temperature" in indicative["thermal_inertia"]["temperature_warning"].lower()

    # Scientific hypotheses & opportunities
    hypotheses = prof["scientific_hypotheses_and_opportunities"]
    assert len(hypotheses["investigation_questions"]) >= 3
    assert "candidate_investigation_opportunities" in hypotheses["status"]
    assert "NOT confirmed discoveries" in hypotheses["disclaimer"]

    # Provenance
    prov = prof["dataset_provenance_and_limitations"]
    assert "ctx-dtm-p21-009323" in prov["elevation_source"]
    assert len(prov["limitations"]) >= 3


def test_location_science_profile_meridiani_themis():
    """Verify science profile within THEMIS 256 ppd regional footprint."""
    resp = client.get("/api/v1/discovery/profile?lat=-2.000&lon=5.000")
    assert resp.status_code == 200
    prof = resp.json()

    direct = prof["direct_observations"]
    assert direct["themis_qualitative_imagery"]["in_regional_coverage"] is True
    assert direct["themis_qualitative_imagery"]["grid_resolution"] == "256 ppd (~231.55 m/px equatorial)"
    assert direct["themis_qualitative_imagery"]["is_raw_100m_raster"] is False
    assert len(direct["themis_qualitative_imagery"]["modes_available"]) == 2

    # High thermal inertia plains
    ti = prof["indicative_proxies"]["thermal_inertia"]["calibrated_thermal_inertia_estimate_tiu"]
    assert ti >= 500.0


def test_nearby_discoveries_query():
    """Verify nearby discoveries sorted by geodesic distance."""
    resp = client.get("/api/v1/discovery/nearby?lat=-4.600&lon=66.317&radius_km=3000&limit=5")
    assert resp.status_code == 200
    nearby = resp.json()

    assert len(nearby) >= 1
    # First must be the co-located Tyrrhena discovery at 0.0 km
    assert nearby[0]["id"] == "disc-terr-tyrrhena-ctx" or nearby[0]["id"] == "disc-multi-tyrrhena-corridor"
    assert nearby[0]["distance_km"] < 1.0

    # Distances must be sorted ascending
    for i in range(len(nearby) - 1):
        assert nearby[i]["distance_km"] <= nearby[i + 1]["distance_km"]


def test_multi_location_comparison():
    """Verify comparison of multiple locations."""
    body = {
        "locations": [
            "disc-terr-tyrrhena-ctx",
            "disc-land-curiosity",
            "-2.0,5.0",
        ]
    }
    resp = client.post("/api/v1/discovery/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["comparison_count"] == 3
    profiles = data["comparison_profiles"]
    assert len(profiles) == 3

    assert profiles[0]["discovery_id"] == "disc-terr-tyrrhena-ctx"
    assert profiles[1]["discovery_id"] == "disc-land-curiosity"
    assert "custom-coord" in profiles[2]["discovery_id"]


def test_elevation_benchmark_preservation():
    """Verify all three numerical elevation benchmarks remain 100% bitwise preserved."""
    # 1. Tyrrhena CTX Benchmark: lat=-4.600, lon=66.317 -> +2189.49 m
    resp_tyr = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317&preferred_source=ctx")
    assert resp_tyr.status_code == 200
    assert resp_tyr.json()["elevation_m"] == 2189.49

    # 2. Apollinaris Sulci Controlled CTX DTM: lat=4.700, lon=168.250 -> -2930.77 m
    resp_apo = client.get("/api/v1/terrain/elevation/point?lat=4.700&lon=168.250")
    assert resp_apo.status_code == 200
    assert resp_apo.json()["elevation_m"] == -2930.77

    # 3. Holden Crater Controlled HiRISE DTM: lat=-28.500, lon=309.020 -> -1132.14 m
    resp_hi = client.get("/api/v1/terrain/elevation/point?lat=-28.500&lon=309.020")
    assert resp_hi.status_code == 200
    assert resp_hi.json()["elevation_m"] == -1132.14
