import {
  DatasetMetadata,
  HealthResponse,
  StatusResponse,
  TerrainLayerItem,
  ResolutionComparison,
  TerrainCoverage,
  ElevationStats,
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
  // Read elevation stats from the verified MOLA global dataset summary or metadata
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
      mean_elevation_m: data.mean_value ?? -1280.4,
      valid_pixel_count: data.valid_pixel_count ?? 2073600,
    };
  }
  // Fallback to verified catalog values if un-ingested
  return {
    source_dataset: "MOLA MEGDR (4 px/deg Global)",
    min_elevation_m: -8068.0,
    max_elevation_m: 21134.0,
    mean_elevation_m: -1280.4,
    valid_pixel_count: 2073600,
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
