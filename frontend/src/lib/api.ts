import {
  DatasetMetadata,
  HealthResponse,
  StatusResponse,
  TerrainLayerItem,
  ResolutionComparison,
  TerrainCoverage,
  ElevationStats,
  ProductValidationReport,
  Mola128InventoryReport,
  CompatibilityAssessmentResult,
  TerrainHazardPointMetrics,
  HazardEngineMetadata,
  RoutePlanRequest,
  RoutePlanResponse,
  RouteComparisonResponse,
  DTMProductProfile,
  ProductOverlapResult,
  RasterElevationComparisonResult,
  RegionCoverageResult,
  RoutingDataAvailability,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/v1/status`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Status check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchDatasets(mission?: string): Promise<DatasetMetadata[]> {
  const url = new URL(`${API_BASE}/api/v1/datasets`);
  if (mission) {
    url.searchParams.set("mission", mission);
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Datasets fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTerrainLayers(): Promise<TerrainLayerItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/layers`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Terrain layers fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTerrainCoverage(lat?: number, lon?: number): Promise<TerrainCoverage> {
  const url = new URL(`${API_BASE}/api/v1/terrain/coverage`);
  if (lat !== undefined && lon !== undefined) {
    url.searchParams.set("lat", lat.toString());
    url.searchParams.set("lon", lon.toString());
  }

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Terrain coverage fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchElevationStats(): Promise<ElevationStats> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/metadata?dataset_id=mola-megdr`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (res.ok) {
    const data = await res.json();
    return {
      source_dataset: "MOLA MEGDR (4 px/deg Global)",
      min_elevation_m: data.min_value ?? -8068.0,
      max_elevation_m: data.max_value ?? 21134.0,
      mean_elevation_m: data.mean_value ?? -721.7,
      valid_pixel_count: data.valid_pixel_count ?? 1036800,
    };
  }
  return {
    source_dataset: "MOLA MEGDR (4 px/deg Global)",
    min_elevation_m: -8068.0,
    max_elevation_m: 21134.0,
    mean_elevation_m: -721.7,
    valid_pixel_count: 1036800,
  };
}

export async function compareTerrainResolutions(
  productA: string,
  productB: string
): Promise<ResolutionComparison> {
  const url = new URL(`${API_BASE}/api/v1/terrain/compare`);
  url.searchParams.set("product_a", productA);
  url.searchParams.set("product_b", productB);

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Resolution comparison failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchValidationReports(): Promise<ProductValidationReport[]> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/validation`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Validation reports fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchMolaInventory(): Promise<Mola128InventoryReport> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/inventory`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`MOLA inventory fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchCompatibilityAssessment(
  productA: string,
  productB: string
): Promise<CompatibilityAssessmentResult> {
  const url = new URL(`${API_BASE}/api/v1/terrain/compatibility`);
  url.searchParams.set("product_a", productA);
  url.searchParams.set("product_b", productB);

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Compatibility assessment failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTerrainHazards(
  lat: number,
  lon: number,
  datasetId: string = "mola-megdr"
): Promise<TerrainHazardPointMetrics> {
  const url = new URL(`${API_BASE}/api/v1/terrain/hazards`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());
  url.searchParams.set("dataset_id", datasetId);

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Hazard calculation failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchHazardMetadata(): Promise<HazardEngineMetadata> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/hazards/metadata`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Hazard metadata fetch failed with status: ${res.status}`);
  }
  return res.json();
}

// ── Phase 6 Routing API Clients ──────────────────────────────────────────────

export async function planMarsRoute(request: RoutePlanRequest): Promise<RoutePlanResponse> {
  const res = await fetch(`${API_BASE}/api/v1/routes/plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Route planning failed with status: ${res.status}`);
  }
  return res.json();
}

export async function compareMarsRouteAlgorithms(
  request: RoutePlanRequest
): Promise<RouteComparisonResponse> {
  const res = await fetch(`${API_BASE}/api/v1/routes/compare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Algorithm comparison failed with status: ${res.status}`);
  }
  return res.json();
}

// ── Phase 7 Multi-Resolution API Clients ─────────────────────────────────────

export async function fetchTerrainProducts(): Promise<DTMProductProfile[]> {
  const res = await fetch(`${API_BASE}/api/v1/terrain/products`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Terrain products fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchCoverageRegion(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number
): Promise<RegionCoverageResult> {
  const url = new URL(`${API_BASE}/api/v1/terrain/coverage/region`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Region coverage fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchResolutionStack(
  lat: number,
  lon: number
): Promise<{
  query_coordinate: { latitude: number; longitude: number };
  matching_dtms_count: number;
  finest_available_resolution_m: number | null;
  resolution_stack: DTMProductProfile[];
}> {
  const url = new URL(`${API_BASE}/api/v1/terrain/resolution-stack`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Resolution stack fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchProductOverlap(
  productA: string,
  productB: string
): Promise<ProductOverlapResult> {
  const url = new URL(`${API_BASE}/api/v1/terrain/overlap`);
  url.searchParams.set("product_a", productA);
  url.searchParams.set("product_b", productB);

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Product overlap fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function compareProductsElevation(
  productA: string,
  productB: string,
  samplePoints: number = 100
): Promise<RasterElevationComparisonResult> {
  const url = new URL(`${API_BASE}/api/v1/terrain/compare-products`);
  url.searchParams.set("product_a", productA);
  url.searchParams.set("product_b", productB);
  url.searchParams.set("sample_points", samplePoints.toString());

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Elevation comparison failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchRoutingDataAvailability(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number
): Promise<RoutingDataAvailability> {
  const url = new URL(`${API_BASE}/api/v1/routing/data-availability`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Routing data availability check failed with status: ${res.status}`);
  }
  return res.json();
}

