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
  ResolutionSelectionResult,
  MultiScaleAnalysisResult,
  ResolutionTransitionEvaluation,
  RegionTerrainAssessment,
  RegionComparisonResponse,
  RouteTerrainSourceResponse,
  PointElevationDetail,
  ElevationProfileResponse,
  WindowRenderMetadata,
  DiscoveryCategory,
  ScienceDiscovery,
  ScienceProfile,
  ScienceComparisonResponse,
  TraversabilityMetadata,
  TraversabilityPointResult,
  TraversabilityWindowResult,
  TraversabilityCoverageEntry,
  TraversabilityLegendEntry,
  MarswalkRouteRequest,
  MarswalkRouteResponse,
  MarswalkMetadataResponse,
  MultiStopRouteRequest,
  MultiStopTraverseResponse,
  MultiStopMetadataResponse,
  RouteIntelligenceReport,
  MultiStopTraverseIntelligenceReport,
  RouteIntelligenceMetadataResponse,
  AtmosphericPressureEstimate,
  PressureResidualBenchmark,
  MarsSolarGeometry,
  MarsTimeConversion,
  HistoricalWeatherSummary,
  RouteEnvironmentalSummary,
  EnvironmentalMetadataResponse,
  ClimatologyPoint,
  ClimatologyProfileResponse,
  ClimatologyMetadataResponse,
  ClimatologyCoverageResponse,
  RouteClimatologySummary,
} from "./types";


export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
}

// In-flight GET request deduplication map to avoid thundering-herd on identical endpoints
const _IN_FLIGHT_GETS = new Map<string, Promise<Response>>();

async function apiFetch(urlStr: string, options: ApiFetchOptions = {}): Promise<Response> {
  const method = (options.method || "GET").toUpperCase();
  const isIdempotent = method === "GET" || method === "HEAD";
  const maxRetries = options.retries !== undefined ? options.retries : (isIdempotent ? 2 : 0);
  const baseDelay = options.retryDelayMs || 400;
  const timeoutMs = options.timeoutMs || 15000;

  // Deduplicate identical in-flight GET requests
  if (isIdempotent && !options.body && options.signal === undefined) {
    const existing = _IN_FLIGHT_GETS.get(urlStr);
    if (existing) {
      const resp = await existing;
      return resp.clone();
    }
  }

  const executeFetch = async (): Promise<Response> => {
    let attempt = 0;
    while (true) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      // If caller passed an external AbortSignal, link it
      const onExternalAbort = () => controller.abort();
      if (options.signal) {
        options.signal.addEventListener("abort", onExternalAbort);
      }

      try {
        const res = await fetch(urlStr, {
          ...options,
          signal: controller.signal,
          cache: options.cache || "no-store",
          headers: {
            Accept: "application/json",
            ...(options.headers || {}),
          },
        });

        // Retry transient server errors (502, 503, 504) on idempotent calls
        if (isIdempotent && attempt < maxRetries && [502, 503, 504].includes(res.status)) {
          attempt++;
          const jitter = Math.random() * 150;
          const delay = Math.min(2500, baseDelay * Math.pow(2, attempt) + jitter);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        return res;
      } catch (err: unknown) {
        const isAbort = err instanceof Error && err.name === "AbortError";
        if (isAbort && options.signal?.aborted) {
          throw err; // Caller explicitly aborted
        }

        // Only retry transient network errors or timeouts on idempotent requests
        if (isIdempotent && attempt < maxRetries) {
          attempt++;
          const jitter = Math.random() * 150;
          const delay = Math.min(2500, baseDelay * Math.pow(2, attempt) + jitter);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        if (isAbort) {
          throw new Error(`Request to ${urlStr} timed out after ${timeoutMs}ms. Please ensure the backend is responsive.`);
        }
        throw new Error(`MARS-X Backend unreachable at ${API_BASE}. Ensure FastAPI server is running on port 8000.`);
      } finally {
        clearTimeout(timeoutId);
        if (options.signal) {
          options.signal.removeEventListener("abort", onExternalAbort);
        }
      }
    }
  };

  if (isIdempotent && !options.body && options.signal === undefined) {
    const fetchPromise = executeFetch();
    _IN_FLIGHT_GETS.set(urlStr, fetchPromise);
    try {
      const resp = await fetchPromise;
      return resp.clone();
    } finally {
      _IN_FLIGHT_GETS.delete(urlStr);
    }
  }

  return executeFetch();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await apiFetch(`${API_BASE}/health`, { timeoutMs: 5000 });
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/status`, { timeoutMs: 5000 });
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

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Datasets fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTerrainLayers(): Promise<TerrainLayerItem[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/layers`, {
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

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Terrain coverage fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchElevationStats(): Promise<ElevationStats> {
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/metadata?dataset_id=mola-megdr`, {
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

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Resolution comparison failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchValidationReports(): Promise<ProductValidationReport[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/validation`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Validation reports fetch failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchMolaInventory(): Promise<Mola128InventoryReport> {
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/inventory`, {
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

  const res = await apiFetch(url.toString(), {
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

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Hazard calculation failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchHazardMetadata(): Promise<HazardEngineMetadata> {
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/hazards/metadata`, {
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
  const res = await apiFetch(`${API_BASE}/api/v1/routes/plan`, {
    method: "POST",
    timeoutMs: 30000,
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
  const res = await apiFetch(`${API_BASE}/api/v1/routes/compare`, {
    method: "POST",
    timeoutMs: 30000,
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
  const res = await apiFetch(`${API_BASE}/api/v1/terrain/products`, {
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

  const res = await apiFetch(url.toString(), {
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

  const res = await apiFetch(url.toString(), {
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

  const res = await apiFetch(url.toString(), {
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

  const res = await apiFetch(url.toString(), {
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

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Routing data availability check failed with status: ${res.status}`);
  }
  return res.json();
}


// ── Phase 8: Resolution-Aware Terrain Intelligence Endpoints ───────────────────

export async function fetchResolutionSelection(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number,
  analysisType: string = "traverse_planning",
  targetScaleM?: number
): Promise<ResolutionSelectionResult> {
  const url = new URL(`${API_BASE}/api/v1/science/resolution-selection`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());
  url.searchParams.set("analysis_type", analysisType);
  if (targetScaleM) {
    url.searchParams.set("target_scale_m", targetScaleM.toString());
  }

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Resolution selection failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTerrainProfile(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number,
  datasetId?: string,
  windowsM: string = "100,500,1000,2000"
): Promise<MultiScaleAnalysisResult> {
  const url = new URL(`${API_BASE}/api/v1/science/terrain-profile`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());
  if (datasetId) {
    url.searchParams.set("dataset_id", datasetId);
  }
  url.searchParams.set("windows_m", windowsM);

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Terrain profile analysis failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchTransitionCompatibility(
  productA: string,
  productB: string
): Promise<ResolutionTransitionEvaluation> {
  const url = new URL(`${API_BASE}/api/v1/science/transition-compatibility`);
  url.searchParams.set("product_a", productA);
  url.searchParams.set("product_b", productB);

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Transition compatibility check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchRegionAssessment(
  minLat: number,
  minLon: number,
  maxLat: number,
  maxLon: number,
  name: string = "Target Region",
  targetScaleM: number = 500.0
): Promise<RegionTerrainAssessment> {
  const url = new URL(`${API_BASE}/api/v1/science/region-assessment`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());
  url.searchParams.set("name", name);
  url.searchParams.set("target_scale_m", targetScaleM.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Region assessment failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchPresetRegionComparison(
  targetScaleM: number = 500.0
): Promise<RegionComparisonResponse> {
  const url = new URL(`${API_BASE}/api/v1/science/region-comparison`);
  url.searchParams.set("target_scale_m", targetScaleM.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Region comparison failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchRouteTerrainSource(
  startLat: number,
  startLon: number,
  destLat: number,
  destLon: number,
  targetScaleM?: number
): Promise<RouteTerrainSourceResponse> {
  const url = new URL(`${API_BASE}/api/v1/routing/terrain-source`);
  url.searchParams.set("start_lat", startLat.toString());
  url.searchParams.set("start_lon", startLon.toString());
  url.searchParams.set("dest_lat", destLat.toString());
  url.searchParams.set("dest_lon", destLon.toString());
  if (targetScaleM) {
    url.searchParams.set("target_scale_m", targetScaleM.toString());
  }

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Route terrain source evaluation failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchPointElevation(lat: number, lon: number): Promise<PointElevationDetail> {
  const url = new URL(`${API_BASE}/api/v1/terrain/elevation/point`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Point elevation query failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchElevationProfile(
  startLat: number,
  startLon: number,
  endLat: number,
  endLon: number,
  numSamples: number = 100
): Promise<ElevationProfileResponse> {
  const url = new URL(`${API_BASE}/api/v1/terrain/elevation/profile`);
  url.searchParams.set("start_lat", startLat.toString());
  url.searchParams.set("start_lon", startLon.toString());
  url.searchParams.set("end_lat", endLat.toString());
  url.searchParams.set("end_lon", endLon.toString());
  url.searchParams.set("num_samples", numSamples.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
    timeoutMs: 15000,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Elevation profile query failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchWindowRenderMetadata(
  minLon: number,
  minLat: number,
  maxLon: number,
  maxLat: number,
  width: number = 512,
  height: number = 512
): Promise<WindowRenderMetadata> {
  const url = new URL(`${API_BASE}/api/v1/terrain/render/window/metadata`);
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("max_lon", maxLon.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("width", width.toString());
  url.searchParams.set("height", height.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Window render metadata query failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchGeologyPoint(lat: number, lon: number): Promise<any> {
  const url = new URL(`${API_BASE}/api/v1/geology/point`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Geology point query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchGeologyMetadata(): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/geology/metadata`);
  if (!res.ok) {
    throw new Error(`Geology metadata query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchThermalPoint(lat: number, lon: number, product: string = "dayside"): Promise<any> {
  const url = new URL(`${API_BASE}/api/v1/thermal/point`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());
  url.searchParams.set("product", product);

  const res = await apiFetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Thermal point query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchThermalMetadata(): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/thermal/metadata`);
  if (!res.ok) {
    throw new Error(`Thermal metadata query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchThemisMetadata(): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/themis/metadata`);
  if (!res.ok) {
    throw new Error(`THEMIS metadata query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchScientificProvenance(): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/v1/science/provenance`);
  if (!res.ok) {
    throw new Error(`Scientific provenance query failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 8.7 Science Discovery API Functions
// ---------------------------------------------------------------------------

export async function fetchDiscoveryCategories(): Promise<DiscoveryCategory[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/discovery/categories`);
  if (!res.ok) {
    throw new Error(`Discovery categories query failed: ${res.status}`);
  }
  return res.json();
}

function toArray(val: any): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  if (typeof val === "string") return [val];
  return [];
}

function normalizeDiscovery(d: any): ScienceDiscovery {
  const opps = toArray(d.suggested_investigations || d.investigation_opportunities);
  const limits = toArray(d.scientific_limitations || d.limitations);

  let evidenceClasses = d.evidence_classes;
  if (!evidenceClasses || typeof evidenceClasses !== "object" || Array.isArray(evidenceClasses)) {
    evidenceClasses = {
      measured_observations: [
        "Calibrated instrument sensor observation",
        ...(d.supporting_datasets || []),
      ],
      derived_measurements: [
        d.spatial_resolution_desc ? `Spatial ground spacing: ${d.spatial_resolution_desc}` : "Interpolated elevation and slope",
      ],
      indicative_proxies: [
        "Thermophysical grain-size proxy from MGS TES thermal inertia",
      ],
      potential_investigations: opps.slice(0, 3),
    };
  }

  return {
    id: d.id,
    name: d.name || d.title || "Unnamed Discovery",
    category: d.category,
    latitude: d.latitude,
    longitude: d.longitude,
    coordinate_display: d.coordinate_display,
    primary_feature: d.primary_feature || d.target_site || d.title || "",
    primary_evidence_class: d.primary_evidence_class,
    primary_source: d.primary_source,
    scientific_significance: d.scientific_significance || "",
    geological_context: d.geological_context || {
      unit_symbol: d.live_measurements?.geology_unit_code,
      unit_name: d.live_measurements?.geology_unit_name,
      stratigraphic_age: d.live_measurements?.geology_age,
      primary_lithology: d.live_measurements?.geology_lithology,
    },
    thermal_context: d.thermal_context || {
      tes_thermal_inertia_si: d.live_measurements?.tes_thermal_inertia_si,
      thermophysical_unit: d.live_measurements?.thermal_unit,
      themis_ir_covered: d.live_measurements?.themis_day_ir_dn !== null && d.live_measurements?.themis_day_ir_dn !== undefined,
      themis_band_9_dn: d.live_measurements?.themis_day_ir_dn,
    },
    terrain_context: d.terrain_context || {
      mola_elevation_m: d.live_measurements?.mola_elevation_m,
      best_dtm_elevation_m: d.live_measurements?.best_dtm_elevation_m,
      highest_resolution_tier: d.live_measurements?.highest_tier,
      finest_ground_spacing_m: d.live_measurements?.finest_ground_spacing_m,
    },
    supporting_datasets: toArray(d.supporting_datasets),
    evidence_classes: evidenceClasses,
    suggested_investigations: opps,
    scientific_limitations: limits,
    derived_metrics: d.derived_metrics || {},
    distance_km: d.distance_km,
  };
}

export async function fetchDiscoveries(params?: {
  category?: string;
  minLat?: number;
  maxLat?: number;
  minLon?: number;
  maxLon?: number;
  search?: string;
}): Promise<ScienceDiscovery[]> {
  const url = new URL(`${API_BASE}/api/v1/discovery/list`);
  if (params?.category) url.searchParams.set("category", params.category);
  if (params?.minLat !== undefined) url.searchParams.set("min_lat", params.minLat.toString());
  if (params?.maxLat !== undefined) url.searchParams.set("max_lat", params.maxLat.toString());
  if (params?.minLon !== undefined) url.searchParams.set("min_lon", params.minLon.toString());
  if (params?.maxLon !== undefined) url.searchParams.set("max_lon", params.maxLon.toString());
  if (params?.search) url.searchParams.set("search", params.search);

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Discoveries query failed: ${res.status}`);
  }
  const json = await res.json();
  const list = Array.isArray(json) ? json : json.discoveries || [];
  return list.map(normalizeDiscovery);
}

export async function fetchDiscoveryById(discoveryId: string): Promise<ScienceDiscovery> {
  const res = await apiFetch(`${API_BASE}/api/v1/discovery/${encodeURIComponent(discoveryId)}`);
  if (!res.ok) {
    throw new Error(`Discovery detail query failed: ${res.status}`);
  }
  const d = await res.json();
  return normalizeDiscovery(d);
}

export async function fetchScienceProfile(
  lat: number,
  lon: number,
  radiusKm: number = 250.0
): Promise<ScienceProfile> {
  const url = new URL(`${API_BASE}/api/v1/discovery/profile`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());
  url.searchParams.set("radius_km", radiusKm.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Science profile query failed: ${res.status}`);
  }
  const json = await res.json();
  if (json.nearby_candidate_discoveries) {
    json.nearby_candidate_discoveries = json.nearby_candidate_discoveries.map(normalizeDiscovery);
  }
  return json;
}

export async function fetchNearbyDiscoveries(
  lat: number,
  lon: number,
  radiusKm: number = 500.0,
  limit: number = 5
): Promise<ScienceDiscovery[]> {
  const url = new URL(`${API_BASE}/api/v1/discovery/nearby`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());
  url.searchParams.set("radius_km", radiusKm.toString());
  url.searchParams.set("limit", limit.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Nearby discoveries query failed: ${res.status}`);
  }
  const json = await res.json();
  const list = Array.isArray(json) ? json : json.nearby_discoveries || [];
  return list.map(normalizeDiscovery);
}

export async function compareScienceLocations(
  locations: Array<{ lat: number; lon: number; label?: string }>
): Promise<ScienceComparisonResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/discovery/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locations }),
  });
  if (!res.ok) {
    throw new Error(`Science comparison failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 8.8.1: Terrain Traversability Foundation API
// ---------------------------------------------------------------------------

export async function fetchTraversabilityMetadata(): Promise<TraversabilityMetadata> {
  const res = await apiFetch(`${API_BASE}/api/v1/traversability/metadata`);
  if (!res.ok) {
    throw new Error(`Traversability metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchTraversabilityPoint(
  lat: number,
  lon: number
): Promise<TraversabilityPointResult> {
  const url = new URL(`${API_BASE}/api/v1/traversability/point`);
  url.searchParams.set("lat", lat.toString());
  url.searchParams.set("lon", lon.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Traversability point query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchTraversabilityWindow(
  minLat: number,
  maxLat: number,
  minLon: number,
  maxLon: number,
  width: number = 64,
  height: number = 32
): Promise<TraversabilityWindowResult> {
  const url = new URL(`${API_BASE}/api/v1/traversability/window`);
  url.searchParams.set("min_lat", minLat.toString());
  url.searchParams.set("max_lat", maxLat.toString());
  url.searchParams.set("min_lon", minLon.toString());
  url.searchParams.set("max_lon", maxLon.toString());
  url.searchParams.set("width", width.toString());
  url.searchParams.set("height", height.toString());

  const res = await apiFetch(url.toString());
  if (!res.ok) {
    throw new Error(`Traversability window query failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchTraversabilityCoverage(): Promise<TraversabilityCoverageEntry[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/traversability/coverage`);
  if (!res.ok) {
    throw new Error(`Traversability coverage fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchTraversabilityLegend(): Promise<TraversabilityLegendEntry[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/traversability/legend`);
  if (!res.ok) {
    throw new Error(`Traversability legend fetch failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Marswalk Route Planning API — Phase 8.8.2
// ---------------------------------------------------------------------------

export async function fetchMarswalkMetadata(): Promise<MarswalkMetadataResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/metadata`);
  if (!res.ok) {
    throw new Error(`Marswalk metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function planMarswalkRoute(
  request: MarswalkRouteRequest
): Promise<MarswalkRouteResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    timeoutMs: 30000,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Marswalk route planning failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchMarswalkRoute(
  routeId: string
): Promise<MarswalkRouteResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/route/${encodeURIComponent(routeId)}`);
  if (!res.ok) {
    throw new Error(`Marswalk route fetch failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Multi-Stop Marswalk Planning — Phase 8.8.3
// ---------------------------------------------------------------------------

export async function fetchMultiStopMetadata(): Promise<MultiStopMetadataResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/multi-stop/metadata`);
  if (!res.ok) {
    throw new Error(`Multi-stop metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function planMultiStopTraverse(
  request: MultiStopRouteRequest
): Promise<MultiStopTraverseResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/multi-stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    timeoutMs: 30000,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Multi-stop planning failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchMultiStopTraverse(
  traverseId: string
): Promise<MultiStopTraverseResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/multi-stop/${encodeURIComponent(traverseId)}`);
  if (!res.ok) {
    throw new Error(`Multi-stop traverse fetch failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Route Intelligence & Scientific Traverse Analysis API — Phase 8.8.4
// ---------------------------------------------------------------------------

export async function fetchRouteIntelligenceMetadata(): Promise<RouteIntelligenceMetadataResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/analysis/metadata`);
  if (!res.ok) {
    throw new Error(`Route intelligence metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchRouteIntelligence(
  routeId: string
): Promise<RouteIntelligenceReport> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/analysis/route/${encodeURIComponent(routeId)}`, {
    timeoutMs: 30000,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Route intelligence analysis failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchMultiStopTraverseIntelligence(
  traverseId: string
): Promise<MultiStopTraverseIntelligenceReport> {
  const res = await apiFetch(`${API_BASE}/api/v1/marswalk/analysis/multi-stop/${encodeURIComponent(traverseId)}`, {
    timeoutMs: 30000,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Multi-stop traverse intelligence analysis failed: ${res.status}`);
  }
  return res.json();
}

// ── Environmental Intelligence API Fetchers — Phase 8.9.1 ──────────────────

export async function fetchEnvironmentalMetadata(): Promise<EnvironmentalMetadataResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/metadata`);
  if (!res.ok) {
    throw new Error(`Environmental metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchAtmosphericPressureEstimate(
  elevationM: number,
  pRefPa?: number,
  scaleHeightM?: number
): Promise<AtmosphericPressureEstimate> {
  const params = new URLSearchParams();
  params.append("elevation_m", elevationM.toString());
  if (pRefPa !== undefined) params.append("p_ref_pa", pRefPa.toString());
  if (scaleHeightM !== undefined) params.append("scale_height_m", scaleHeightM.toString());

  const res = await apiFetch(`${API_BASE}/api/v1/environmental/pressure/estimate?${params.toString()}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Pressure estimation failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPressureResiduals(): Promise<Record<string, PressureResidualBenchmark>> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/pressure/residuals`);
  if (!res.ok) {
    throw new Error(`Pressure residuals fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchSolarGeometry(
  lat: number,
  lon: number,
  lsDeg: number = 0.0,
  ltstHours: number = 12.0,
  tau?: number,
  timeSystem?: string,
  lonConvention?: string
): Promise<MarsSolarGeometry> {
  const params = new URLSearchParams();
  params.append("lat", lat.toString());
  params.append("lon", lon.toString());
  params.append("ls_deg", lsDeg.toString());
  params.append("ltst_hours", ltstHours.toString());
  if (tau !== undefined) params.append("tau", tau.toString());
  if (timeSystem) params.append("time_system", timeSystem);
  if (lonConvention) params.append("lon_convention", lonConvention);

  const res = await apiFetch(`${API_BASE}/api/v1/environmental/solar-geometry?${params.toString()}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Solar geometry calculation failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchEquationOfTime(lsDeg: number = 0.0): Promise<{
  solar_longitude_ls_deg: number;
  equation_of_time_deg: number;
  equation_of_time_hours: number;
  equation_of_time_minutes: number;
  classification: string;
  citation: string;
}> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/time/eot?ls_deg=${lsDeg}`);
  if (!res.ok) {
    throw new Error(`Equation of Time fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function convertMarsTime(
  timeHours: number,
  fromSystem: "LMST" | "LTST" | "MTC",
  toSystem: "LMST" | "LTST" | "MTC",
  lonDeg: number,
  lsDeg: number = 0.0,
  lonConvention: "east_positive" | "west_positive" = "east_positive"
): Promise<MarsTimeConversion> {
  const params = new URLSearchParams({
    time_hours: timeHours.toString(),
    from_system: fromSystem,
    to_system: toSystem,
    lon_deg: lonDeg.toString(),
    ls_deg: lsDeg.toString(),
    lon_convention: lonConvention,
  });
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/time/convert?${params.toString()}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Mars time conversion failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchHistoricalMeda(): Promise<HistoricalWeatherSummary> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/historical/meda`);
  if (!res.ok) {
    throw new Error(`MEDA Sol 1 fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchHistoricalRems(): Promise<HistoricalWeatherSummary> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/historical/rems`);
  if (!res.ok) {
    throw new Error(`REMS Sol 1 fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function enrichRouteEnvironment(
  routePoints: Array<{ lat: number; lon: number; elevation_m: number; distance_m: number }>,
  lsDeg: number = 0.0,
  ltstHours: number = 12.0,
  tau?: number,
  maxSamples: number = 50
): Promise<RouteEnvironmentalSummary> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/route/enrich`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      route_points: routePoints,
      ls_deg: lsDeg,
      ltst_hours: ltstHours,
      tau,
      max_samples: maxSamples,
    }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Route environmental enrichment failed: ${res.status}`);
  }
  return res.json();
}

// ── Climatology API Fetchers — Phase 8.9.2 (MCD v6.2) ──────────────────────

export async function fetchClimatologyMetadata(): Promise<ClimatologyMetadataResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/climatology/metadata`);
  if (!res.ok) {
    throw new Error(`Climatology metadata fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchClimatologyPoint(
  lat: number,
  lon: number,
  lsDeg: number = 0.0,
  ltstHours: number = 12.0,
  elevationM?: number
): Promise<ClimatologyPoint> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    ls_deg: lsDeg.toString(),
    ltst_hours: ltstHours.toString(),
  });
  if (elevationM !== undefined && elevationM !== null) {
    params.set("elevation_m", elevationM.toString());
  }

  const res = await apiFetch(`${API_BASE}/api/v1/environmental/climatology/point?${params.toString()}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Climatology point calculation failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchClimatologyProfile(
  lat: number,
  lon: number,
  profileType: "diurnal" | "seasonal" = "diurnal",
  fixedParam: number = 0.0,
  elevationM?: number,
  stepCount: number = 24
): Promise<ClimatologyProfileResponse> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    profile_type: profileType,
    fixed_param: fixedParam.toString(),
    step_count: stepCount.toString(),
  });
  if (elevationM !== undefined && elevationM !== null) {
    params.set("elevation_m", elevationM.toString());
  }

  const res = await apiFetch(`${API_BASE}/api/v1/environmental/climatology/profile?${params.toString()}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Climatology profile calculation failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchClimatologyCoverage(): Promise<ClimatologyCoverageResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/climatology/coverage`);
  if (!res.ok) {
    throw new Error(`Climatology coverage fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function enrichRouteClimatology(
  routePoints: Array<{ lat: number; lon: number; elevation_m: number; distance_m: number }>,
  lsDeg: number = 0.0,
  ltstHours: number = 12.0
): Promise<RouteClimatologySummary> {
  const res = await apiFetch(`${API_BASE}/api/v1/environmental/climatology/route/enrich`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      route_points: routePoints,
      ls_deg: lsDeg,
      ltst_hours: ltstHours,
    }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Route climatological enrichment failed: ${res.status}`);
  }
  return res.json();
}







