export type ProcessingStatus =
  | "registered"
  | "available"
  | "downloaded"
  | "validated"
  | "error";

export type DatasetLifecycleState =
  | "registered"
  | "discovered"
  | "downloaded"
  | "integrity_verified"
  | "metadata_validated"
  | "geospatially_validated"
  | "scientifically_validated"
  | "analysis_ready"
  | "failed"
  | "unavailable";

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
  product_id: string;
  instrument: string;
  mission: string;
  tier: string;
  pixel_spacing_m: number;
  pixel_spacing_desc: string;
  crs: string;
  vertical_datum: string;
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
  ratio: number;
  finer_product: string;
  coarser_product: string;
  vertical_datum_compatible: boolean;
  vertical_datum_notes: string;
  anti_upsampling_guarantee: string;
}

export interface ElevationStats {
  source_dataset: string;
  min_elevation_m: number;
  max_elevation_m: number;
  mean_elevation_m: number;
  valid_pixel_count: number;
}

export interface ValidationEvidence {
  check_name: string;
  passed: boolean;
  details: string;
  timestamp: string;
}

export interface ProductValidationReport {
  product_id: string;
  instrument: string;
  source_archive: string;
  native_resolution_desc: string;
  pixel_spacing_m: number;
  raster_available_locally: boolean;
  lifecycle_state: DatasetLifecycleState;
  horizontal_crs: string;
  vertical_datum: string;
  nodata_definition: number;
  pixel_registration: string;
  source_checksum: string | null;
  validation_timestamp: string;
  is_analysis_ready: boolean;
  evidence_checks: ValidationEvidence[];
  unresolved_limitations: string[];
}

export interface Mola128TileRecord {
  tile_id: string;
  product_filename: string;
  label_filename: string;
  pds_url_img: string;
  pds_url_lbl: string;
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  download_status: string;
  validation_status: string;
  sha256_img: string | null;
}

export interface Mola128InventoryReport {
  expected_tile_count: number;
  downloaded_tile_count: number;
  validated_tile_count: number;
  missing_tile_count: number;
  latitude_coverage_deg: [number, number];
  longitude_coverage_deg: [number, number];
  total_surface_coverage_pct: number;
  coverage_calculation_method: string;
  tiles: Mola128TileRecord[];
}

export interface CompatibilityAssessmentResult {
  product_a: string;
  product_b: string;
  horizontal_status: string;
  horizontal_notes: string;
  vertical_status: string;
  vertical_notes: string;
  resolution_ratio: number;
  finer_product: string;
  coarser_product: string;
  decision: string;
  anti_upsampling_enforced: boolean;
  reasons_blocked: string[];
  preservation_guarantee: string;
}

export interface TerrainHazardPointMetrics {
  latitude: number;
  longitude: number;
  elevation_m: number;
  slope_deg: number | null;
  slope_pct: number | null;
  local_relief_m: number | null;
  roughness_m: number | null;
  discontinuity_detected: boolean;
  discontinuity_type: string | null;
  data_confidence_score: number;
  complexity_class: string;
  source_dataset: string;
  source_resolution_m: number;
  analysis_window_m: number;
  explanation: string;
  safety_disclaimer: string;
}

export interface HazardEngineMetadata {
  slope_algorithm: string;
  relief_algorithm: string;
  roughness_algorithm: string;
  discontinuity_algorithm: string;
  confidence_scoring: string;
  metric_units: Record<string, string>;
  scientific_limitations: string[];
}
