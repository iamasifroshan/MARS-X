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
  spherical_area_fraction_pct: number;
  download_status: string;
  is_downloaded: boolean;
  is_integrity_verified: boolean;
  is_geospatially_validated: boolean;
  is_scientifically_validated: boolean;
  validation_status: string;
  sha256_img: string | null;
}

export interface Mola128InventoryReport {
  expected_tile_count: number;
  downloaded_tile_count: number;
  integrity_verified_tile_count: number;
  geospatially_validated_tile_count: number;
  scientifically_validated_tile_count: number;
  missing_tile_count: number;
  latitude_coverage_deg: [number, number];
  longitude_coverage_deg: [number, number];
  theoretical_archive_coverage_pct: number;
  catalogued_tile_coverage_pct: number;
  downloaded_tile_coverage_pct: number;
  integrity_verified_coverage_pct: number;
  geospatially_validated_coverage_pct: number;
  scientifically_validated_coverage_pct: number;
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

export interface SpatialScaleMetadata {
  native_pixel_spacing_m: number;
  analysis_window_size_m: number;
  analysis_window_pixel_span: number;
  minimum_detectable_feature_scale_m: number;
  operational_scale_tier: string;
  scale_limitation_warning: string;
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
  spatial_scale: SpatialScaleMetadata;
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

// ── Phase 6 Routing Types ────────────────────────────────────────────────────

export type PathfindingAlgorithm = "astar" | "dijkstra";
export type NeighborConnectivity = 4 | 8;

export interface TerrainCostWeights {
  weight_slope: number;
  weight_roughness: number;
  weight_relief: number;
  weight_complexity: number;
}

export interface ExclusionZone {
  name: string;
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}

export interface RoutePlanRequest {
  start_lat: number;
  start_lon: number;
  dest_lat: number;
  dest_lon: number;
  dataset_id?: string;
  algorithm?: "astar" | "dijkstra";
  connectivity?: 4 | 8;
  cost_weights?: TerrainCostWeights;
  max_slope_deg?: number;
  max_snapping_distance_m?: number;
  max_search_nodes?: number;
  exclusion_zones?: ExclusionZone[];
}

export interface RouteWaypoint {
  latitude: number;
  longitude: number;
  elevation_m: number;
  slope_deg: number;
  roughness_m: number;
  relief_m: number;
  cumulative_distance_m: number;
  complexity_class: string;
}

export interface RouteSummaryMetrics {
  total_distance_m: number;
  cumulative_elevation_gain_m: number;
  cumulative_elevation_loss_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  max_slope_deg: number;
  mean_slope_deg: number;
  mean_roughness_m: number;
  mean_local_relief_m: number;
  high_complexity_fraction: number;
  nodes_expanded: number;
  nodes_visited: number;
  search_duration_ms: number;
  total_cost: number;
}

export interface RouteValidationSummary {
  is_valid: boolean;
  passed_checks: string[];
  failed_checks: string[];
  max_encountered_slope_deg: number;
  steepest_segment_indices?: [number, number] | null;
  diagonal_corner_cuts_count: number;
  nodata_violations_count: number;
}

export interface RoutePlanResponse {
  route_id: string;
  algorithm: "astar" | "dijkstra";
  requested_start: [number, number];
  requested_dest: [number, number];
  snapped_start: [number, number];
  snapped_dest: [number, number];
  snapping_distance_start_m: number;
  snapping_distance_dest_m: number;
  waypoints: RouteWaypoint[];
  metrics: RouteSummaryMetrics;
  validation: RouteValidationSummary;
  dataset_id: string;
  dataset_checksum: string;
  native_resolution_m: number;
  planning_grid_spacing_m: number;
  cost_weights: TerrainCostWeights;
  max_slope_threshold_deg: number;
  explanation: string;
  scientific_disclaimer: string;
}

export interface RouteComparisonResponse {
  request: RoutePlanRequest;
  astar_route: RoutePlanResponse;
  dijkstra_route: RoutePlanResponse;
  cost_difference: number;
  cost_difference_pct: number;
  distance_difference_m: number;
  runtime_speedup_factor: number;
  nodes_expanded_ratio: number;
  path_geometries_identical: boolean;
  scientific_synthesis: string;
}

// ── Phase 7 Multi-Resolution Types ──────────────────────────────────────────

export interface DTMProductProfile {
  product_id: string;
  instrument: string;
  mission: string;
  tier: "global_coarse" | "global_base" | "regional" | "local_tactical" | string;
  pixel_spacing_m: number;
  pixel_spacing_desc: string;
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  crs: string;
  vertical_datum: string;
  nodata_value: number;
  source_archive: string;
  download_url: string;
  is_tiled: boolean;
  status: string;
  quality_notes: string;
}

export interface ProductOverlapResult {
  product_a: string;
  product_b: string;
  has_overlap: boolean;
  overlap_lat_min?: number | null;
  overlap_lat_max?: number | null;
  overlap_lon_min?: number | null;
  overlap_lon_max?: number | null;
  overlap_area_km2: number;
  relative_resolution_ratio: number;
  both_locally_available: boolean;
  scientific_compatibility: string;
  notes: string;
}

export interface RasterElevationComparisonResult {
  product_a: string;
  product_b: string;
  sample_points_count: number;
  mean_elevation_a_m: number;
  mean_elevation_b_m: number;
  mean_delta_m: number;
  std_delta_m: number;
  min_delta_m: number;
  max_delta_m: number;
  overlap_bounds: {
    lat_min: number;
    lat_max: number;
    lon_min: number;
    lon_max: number;
  };
  scientific_interpretation: string;
}

export interface RegionCoverageResult {
  bounding_box: {
    min_lat: number;
    min_lon: number;
    max_lat: number;
    max_lon: number;
  };
  intersecting_products_count: number;
  highest_available_resolution_m: number;
  intersecting_products: DTMProductProfile[];
}

export interface RoutingDataAvailability {
  bounding_box: {
    min_lat: number;
    min_lon: number;
    max_lat: number;
    max_lon: number;
  };
  routing_eligible: boolean;
  available_tiers: string[];
  intersecting_products_count: number;
  intersecting_products: Array<{
    product_id: string;
    instrument: string;
    tier: string;
    pixel_spacing_m: number;
    vertical_datum: string;
    status: string;
  }>;
  highest_available_resolution_m: number;
  recommended_product: string;
  downloaded_mola_tiles: string[];
  supported_algorithms: string[];
  scientific_notes: string[];
}

