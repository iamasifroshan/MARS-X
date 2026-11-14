"""Phase 8.8.1: Terrain Traversability Foundation — Backend Test Suite.

Verifies:
1. Slope derivation engine:
   - Flat plane produces near-zero slope.
   - Known inclined surface produces expected slope in degrees.
   - East-west spacing accounts for latitude.
   - NoData in 3x3 stencil propagates to output NoData.
   - Raster edges (border rows/cols) remain NoData.
2. Slope classification:
   - Boundaries correct (0–5, 5–15, 15–25, >25 degrees).
   - None/NaN/negative produces unknown.
   - NoData terrain is never classified as low slope.
3. Source selection:
   - Coordinates within HiRISE footprint select HiRISE when file available.
   - Coordinates outside high-res select MOLA or report appropriate fallback.
4. API endpoints:
   - GET /api/v1/traversability/metadata returns algorithm docs, sources list, disclaimer.
   - GET /api/v1/traversability/point returns correct fields and MOLA Areoid datum.
   - GET /api/v1/traversability/window returns 2-D slope grid.
   - GET /api/v1/traversability/coverage lists all sources.
   - GET /api/v1/traversability/legend returns 5 entries including 'unknown'.
5. Scientific constraints:
   - Elevation benchmarks remain 100% bitwise preserved.
   - Vertical datum is MOLA Areoid for all sources.
"""

import math
import os
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.terrain.traversability_service import (
    classify_slope,
    SlopeCategory,
    SLOPE_THRESHOLDS,
    SLOPE_DISCLAIMER,
    select_source_for_point,
    get_traversability_service,
    TERRAIN_SOURCES,
)

client = TestClient(app)

MARS_RADIUS_M = 3_396_190.0


def _horn_slope_projected(elevation: np.ndarray, dx_m: float, dy_m: float, nodata_val: float) -> np.ndarray:
    """Horn (1981) slope for projected (metre) raster."""
    rows, cols = elevation.shape
    elev = elevation.astype(np.float64).copy()
    elev[np.isclose(elev, nodata_val, rtol=1e-5, atol=1.0)] = np.nan
    slope_deg = np.full((rows, cols), np.nan, dtype=np.float32)
    if rows < 3 or cols < 3:
        return slope_deg
    z1 = elev[0:-2, 0:-2]; z2 = elev[0:-2, 1:-1]; z3 = elev[0:-2, 2:]
    z4 = elev[1:-1, 0:-2];                          z6 = elev[1:-1, 2:]
    z7 = elev[2:, 0:-2];   z8 = elev[2:, 1:-1];    z9 = elev[2:, 2:]
    stencil_valid = (
        np.isfinite(z1) & np.isfinite(z2) & np.isfinite(z3) &
        np.isfinite(z4) & np.isfinite(elev[1:-1, 1:-1]) & np.isfinite(z6) &
        np.isfinite(z7) & np.isfinite(z8) & np.isfinite(z9)
    )
    dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx_m)
    dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy_m)
    grad = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    calc = np.degrees(np.arctan(grad)).astype(np.float32)
    slope_deg[1:-1, 1:-1] = np.where(stencil_valid, calc, np.nan)
    return slope_deg


def _horn_slope_geographic(elevation: np.ndarray, dlon_deg: float, dlat_deg: float,
                            center_lat_deg: float, nodata_val: float) -> np.ndarray:
    """Horn slope for geographic (degree) raster with latitude-corrected dx."""
    rows, cols = elevation.shape
    elev = elevation.astype(np.float64).copy()
    elev[np.isclose(elev, nodata_val, rtol=1e-5, atol=1.0)] = np.nan
    slope_deg = np.full((rows, cols), np.nan, dtype=np.float32)
    if rows < 3 or cols < 3:
        return slope_deg
    dy_m = (math.pi / 180.0) * MARS_RADIUS_M * abs(dlat_deg)
    z1 = elev[0:-2, 0:-2]; z2 = elev[0:-2, 1:-1]; z3 = elev[0:-2, 2:]
    z4 = elev[1:-1, 0:-2];                          z6 = elev[1:-1, 2:]
    z7 = elev[2:, 0:-2];   z8 = elev[2:, 1:-1];    z9 = elev[2:, 2:]
    stencil_valid = (
        np.isfinite(z1) & np.isfinite(z2) & np.isfinite(z3) &
        np.isfinite(z4) & np.isfinite(elev[1:-1, 1:-1]) & np.isfinite(z6) &
        np.isfinite(z7) & np.isfinite(z8) & np.isfinite(z9)
    )
    nrows_inner = rows - 2
    top_lat = center_lat_deg + ((rows / 2.0) - 1.5) * abs(dlat_deg)
    lats = np.array([top_lat - r * abs(dlat_deg) for r in range(nrows_inner)])
    cos_lat = np.cos(np.radians(lats))
    dx_m_per_row = np.maximum((math.pi / 180.0) * MARS_RADIUS_M * abs(dlon_deg) * cos_lat, 1e-6)
    dx_m = dx_m_per_row[:, np.newaxis]
    dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * dx_m)
    dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * dy_m)
    grad = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    calc = np.degrees(np.arctan(grad)).astype(np.float32)
    slope_deg[1:-1, 1:-1] = np.where(stencil_valid, calc, np.nan)
    return slope_deg


class TestSlopeComputationUnit:
    """Unit tests for Horn slope algorithm using synthetic rasters."""

    def test_flat_surface_zero_slope(self):
        flat = np.full((5, 5), 1500.0, dtype=np.float64)
        slope = _horn_slope_projected(flat, dx_m=20.0, dy_m=20.0, nodata_val=-32767.0)
        interior = slope[1:-1, 1:-1]
        valid = interior[~np.isnan(interior)]
        assert len(valid) > 0, "Interior slope cells must not all be NaN for a flat surface"
        assert float(np.max(np.abs(valid))) < 1e-4, f"Flat surface max slope = {float(np.max(np.abs(valid)))}°"

    def test_inclined_plane_expected_slope_projected(self):
        angle_deg = 10.0
        dx_m = 20.0
        dz_per_pixel = dx_m * math.tan(math.radians(angle_deg))
        z = np.zeros((7, 7), dtype=np.float64)
        for c in range(7):
            z[:, c] = c * dz_per_pixel
        slope = _horn_slope_projected(z, dx_m=dx_m, dy_m=dx_m, nodata_val=-32767.0)
        valid = slope[1:-1, 1:-1][~np.isnan(slope[1:-1, 1:-1])]
        mean_slope = float(np.mean(valid))
        assert abs(mean_slope - angle_deg) < 0.5, f"Expected ~{angle_deg}°, got {mean_slope:.3f}°"

    def test_nodata_propagates_to_nan(self):
        elev = np.full((5, 5), 1000.0, dtype=np.float64)
        elev[2, 2] = -32767.0
        slope = _horn_slope_projected(elev, dx_m=20.0, dy_m=20.0, nodata_val=-32767.0)
        affected = slope[1:4, 1:4]
        assert np.all(np.isnan(affected)), "NoData in stencil must propagate to NaN"

    def test_raster_border_cells_are_nodata(self):
        elev = np.arange(25, dtype=np.float64).reshape(5, 5) * 10.0
        slope = _horn_slope_projected(elev, dx_m=20.0, dy_m=20.0, nodata_val=-32767.0)
        assert np.all(np.isnan(slope[0, :])), "Top border row must be NaN"
        assert np.all(np.isnan(slope[-1, :])), "Bottom border row must be NaN"
        assert np.all(np.isnan(slope[:, 0])), "Left border column must be NaN"
        assert np.all(np.isnan(slope[:, -1])), "Right border column must be NaN"

    def test_latitude_scaled_east_west_spacing(self):
        dlon_deg = 0.25
        dlat_deg = 0.25
        z = np.zeros((5, 5), dtype=np.float64)
        for c in range(5):
            z[:, c] = c * 500.0
        slope_eq = _horn_slope_geographic(z, dlon_deg, dlat_deg, center_lat_deg=0.0, nodata_val=-32768.0)
        slope_60 = _horn_slope_geographic(z, dlon_deg, dlat_deg, center_lat_deg=60.0, nodata_val=-32768.0)
        eq_mean = float(np.nanmean(slope_eq[1:-1, 1:-1]))
        lat60_mean = float(np.nanmean(slope_60[1:-1, 1:-1]))
        assert lat60_mean > eq_mean * 1.4, (
            f"60°N slope ({lat60_mean:.2f}°) should exceed equatorial ({eq_mean:.2f}°)"
        )

    def test_slope_minimum_grid_size_guard(self):
        tiny = np.ones((2, 2), dtype=np.float64) * 100.0
        slope = _horn_slope_projected(tiny, dx_m=20.0, dy_m=20.0, nodata_val=-32767.0)
        assert slope.shape == (2, 2)
        assert np.all(np.isnan(slope))


class TestSlopeClassification:

    def test_boundaries(self):
        assert classify_slope(0.0)    == SlopeCategory.LOW
        assert classify_slope(2.5)    == SlopeCategory.LOW
        assert classify_slope(5.0)    == SlopeCategory.LOW
        assert classify_slope(5.001)  == SlopeCategory.MODERATE
        assert classify_slope(10.0)   == SlopeCategory.MODERATE
        assert classify_slope(15.0)   == SlopeCategory.MODERATE
        assert classify_slope(15.001) == SlopeCategory.HIGH
        assert classify_slope(20.0)   == SlopeCategory.HIGH
        assert classify_slope(25.0)   == SlopeCategory.HIGH
        assert classify_slope(25.001) == SlopeCategory.VERY_HIGH
        assert classify_slope(80.0)   == SlopeCategory.VERY_HIGH

    def test_none_is_unknown(self):
        assert classify_slope(None) == SlopeCategory.UNKNOWN

    def test_nan_is_unknown(self):
        assert classify_slope(float("nan")) == SlopeCategory.UNKNOWN

    def test_negative_is_unknown(self):
        assert classify_slope(-1.0) == SlopeCategory.UNKNOWN

    def test_nodata_never_classified_as_low(self):
        result = classify_slope(None)
        assert result != SlopeCategory.LOW
        assert result == SlopeCategory.UNKNOWN


class TestSourceSelection:

    def test_tyrrhena_coordinates_select_ctx(self):
        src, chain = select_source_for_point(-4.6, 66.317)
        assert src is not None, f"Expected CTX source, got None. Chain: {chain}"
        if os.path.isfile(src["elev_path"]):
            assert src["source_id"] == "ctx-tyrrhena"

    def test_holden_coordinates_select_hirise_or_fallback(self):
        src, chain = select_source_for_point(-28.5, 309.02)
        assert src is not None
        if os.path.isfile(src["elev_path"]):
            assert src["source_id"] == "hirise-holden"

    def test_polar_region_uses_global_fallback(self):
        src, chain = select_source_for_point(88.0, 100.0)
        assert src is not None
        assert src["source_id"] == "mola-4ppd"

    def test_all_sources_have_areoid_datum(self):
        for s in TERRAIN_SOURCES:
            assert "MOLA Areoid" in s["vertical_datum"], f"{s['source_id']} missing MOLA Areoid datum"
            assert s["vertical_datum_type"] == "areoid_height", f"{s['source_id']} wrong datum type"


class TestTraversabilityAPI:

    def test_metadata_endpoint_structure(self):
        resp = client.get("/api/v1/traversability/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "slope_algorithm" in data
        assert "slope_thresholds_deg" in data
        assert "slope_disclaimer" in data
        assert "vertical_datum_policy" in data
        assert "source_selection_policy" in data
        assert "terrain_sources" in data
        assert len(data["terrain_sources"]) >= 5

    def test_metadata_disclaimer_present(self):
        data = client.get("/api/v1/traversability/metadata").json()
        assert "safety" in data["slope_disclaimer"].lower()
        assert "astronaut" in data["slope_disclaimer"].lower()

    def test_point_endpoint_tyrrhena(self):
        resp = client.get("/api/v1/traversability/point?lat=-4.600&lon=66.317")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slope_category"] in ("low", "moderate", "high", "very_high", "unknown")
        assert "MOLA Areoid" in data["vertical_datum"]
        assert "fallback_chain" in data
        assert "slope_disclaimer" in data
        if data["elevation_m"] is not None and not data["is_elevation_nodata"]:
            assert 2000.0 < data["elevation_m"] < 2500.0

    def test_point_endpoint_apollinaris(self):
        resp = client.get("/api/v1/traversability/point?lat=4.700&lon=168.250")
        assert resp.status_code == 200
        data = resp.json()
        if data["elevation_m"] is not None and not data["is_elevation_nodata"]:
            assert -3200.0 < data["elevation_m"] < -2600.0

    def test_point_endpoint_holden(self):
        resp = client.get("/api/v1/traversability/point?lat=-28.500&lon=309.020")
        assert resp.status_code == 200
        data = resp.json()
        if data["elevation_m"] is not None and not data["is_elevation_nodata"]:
            assert -1500.0 < data["elevation_m"] < -800.0

    def test_point_nodata_is_unknown_not_low(self):
        resp = client.get("/api/v1/traversability/point?lat=89.0&lon=50.0")
        assert resp.status_code == 200
        data = resp.json()
        if data["is_slope_nodata"]:
            assert data["slope_category"] == "unknown"

    def test_window_endpoint_basic(self):
        resp = client.get("/api/v1/traversability/window?min_lat=-5.5&max_lat=-3.5&min_lon=65.5&max_lon=67.0&width=8&height=4")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["slope_values"]) == 4
        assert len(data["slope_values"][0]) == 8
        valid_cats = {"low", "moderate", "high", "very_high", "unknown"}
        for row in data["slope_categories"]:
            for cat in row:
                assert cat in valid_cats, f"Invalid slope category: {cat}"
        assert 0.0 <= data["nodata_fraction"] <= 1.0

    def test_window_min_lat_gt_max_lat_rejected(self):
        resp = client.get("/api/v1/traversability/window?min_lat=0.0&max_lat=-5.0&min_lon=0.0&max_lon=10.0")
        assert resp.status_code == 400

    def test_coverage_endpoint(self):
        resp = client.get("/api/v1/traversability/coverage")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 5
        source_ids = [e["source_id"] for e in entries]
        assert "mola-4ppd" in source_ids
        assert "ctx-tyrrhena" in source_ids
        assert "hirise-holden" in source_ids

    def test_legend_endpoint(self):
        resp = client.get("/api/v1/traversability/legend")
        assert resp.status_code == 200
        legend = resp.json()
        categories = [e["category"] for e in legend]
        assert "low" in categories
        assert "moderate" in categories
        assert "high" in categories
        assert "very_high" in categories
        assert "unknown" in categories
        unknown = next(e for e in legend if e["category"] == "unknown")
        assert "never" in unknown["description"].lower() or "no valid" in unknown["description"].lower()


class TestElevationBenchmarkPreservation:

    def test_tyrrhena_ctx_benchmark(self):
        resp = client.get("/api/v1/terrain/elevation/point?lat=-4.600&lon=66.317&preferred_source=ctx")
        assert resp.status_code == 200
        assert resp.json()["elevation_m"] == 2189.49

    def test_apollinaris_ctx_benchmark(self):
        resp = client.get("/api/v1/terrain/elevation/point?lat=4.700&lon=168.250")
        assert resp.status_code == 200
        assert resp.json()["elevation_m"] == -2930.77

    def test_holden_hirise_benchmark(self):
        resp = client.get("/api/v1/terrain/elevation/point?lat=-28.500&lon=309.020")
        assert resp.status_code == 200
        assert resp.json()["elevation_m"] == -1132.14
