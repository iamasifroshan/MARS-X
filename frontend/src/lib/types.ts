export type ProcessingStatus =
  | "registered"
  | "available"
  | "downloaded"
  | "validated"
  | "error";

export interface DatasetMetadata {
  dataset_id: string;
  name: string;
  mission: string;
  instrument: string;
  product_type: string;
  spatial_resolution: string | null;
  acquisition_date_range: string | null;
  geographic_footprint: string | null;
  crs: string;
  source_url: string;
  data_format: string;
  coverage: string | null;
  processing_status: ProcessingStatus;
  scientific_limitations: string | null;
  description: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export interface StatusResponse {
  status: string;
  app: string;
  version: string;
  uptime_seconds: number;
  services: Record<string, string>;
}

export interface MapLayer {
  id: string;
  name: string;
  mission: string;
  type: "shaded_relief" | "elevation_dtm" | "slope_dtm" | "roughness_dtm" | "multispectral" | "geology" | "orbital_imagery";
  crs: string;
  enabled: boolean;
  isAvailable: boolean;
  statusNote: string;
  resolution?: string;
  groundSpacingM?: number;
}

export interface TerrainLayerItem {
  layer_id: string;
  name: string;
  product_type: "elevation" | "slope" | "roughness";
  instrument: string;
  resolution_desc: string;
  ground_spacing_m: number;
  crs: string;
  vertical_datum: string;
  unit: string;
  value_range?: { min: number; max: number };
  is_available: boolean;
  file_format: string;
  file_path?: string | null;
  coverage_footprint?: string;
}

export interface IntersectingProduct {
  id: string;
  name: string;
  tier: string;
  pixel_spacing_m: number;
  coverage_type: string;
  source_archive: string;
}

export interface TerrainCoverage {
  query_coordinate: { latitude: number; longitude: number };
  matching_dtms_count: number;
  finest_available_resolution_m: number | null;
  covering_dtms: IntersectingProduct[];
}

export interface ResolutionComparison {
  product_a: string;
  product_b: string;
  resolution_a_m: number;
  resolution_b_m: number;
  resolution_ratio: number;
  finer_product: string;
  coarser_product: string;
  vertical_datum_compatible: boolean;
  vertical_datum_notes: string;
  anti_upsampling_notice: string;
}

export interface ElevationStats {
  source_dataset: string;
  min_elevation_m: number;
  max_elevation_m: number;
  mean_elevation_m: number;
  valid_pixel_count: number;
}
