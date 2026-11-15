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


// ── Phase 8: Resolution-Aware Terrain Intelligence Types ───────────────────────

export interface CandidateEvaluation {
  product_id: string;
  instrument: string;
  tier: string;
  native_resolution_m: number;
  is_locally_available: boolean;
  local_file_path?: string | null;
  lifecycle_status: string;
  coverage_area_km2: number;
  coverage_percentage: number;
  horizontal_crs: string;
  vertical_datum: string;
  vertical_datum_compatibility: string;
  scale_suitability_score: number;
  is_eligible: boolean;
  disqualification_reason?: string | null;
}

export interface SelectionRejectionReason {
  product_id: string;
  stage: string;
  reason: string;
}

export interface ResolutionSelectionResult {
  status: "selected" | "partial_coverage" | "insufficient_data" | "no_coverage";
  selected_product_id?: string | null;
  selected_product?: DTMProductProfile | null;
  fallback_product_id?: string | null;
  native_resolution_m?: number | null;
  coverage_percentage: number;
  covered_area_km2: number;
  requested_area_km2: number;
  selection_rationale: string;
  rejected_products: SelectionRejectionReason[];
  evaluated_candidates: CandidateEvaluation[];
  uncertainty_notes: string[];
  scientific_limitations: string[];
}

export interface ScaleMetrics {
  window_m: number;
  neighborhood_pixels: number;
  requested_analysis_scale_m?: number;
  kernel_size_pixels?: number;
  effective_analysis_scale_x_m?: number;
  effective_analysis_scale_y_m?: number;
  effective_analysis_area_km2?: number;
  scale_resolution_ratio?: number;
  scale_suitability?: string;
  scale_limitation?: string;
  source_product: string;
  native_resolution_m: number;
  crs: string;
  vertical_datum: string;
  valid_data_pct: number;
  mean_elevation_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  elevation_std_m: number;
  elevation_iqr_m: number;
  mean_slope_deg: number;
  max_slope_deg: number;
  p50_slope_deg: number;
  p90_slope_deg: number;
  p95_slope_deg: number;
  mean_local_relief_m: number;
  max_local_relief_m: number;
  mean_roughness_m: number;
  max_roughness_m: number;
  complexity_class: "low_complexity" | "moderate_complexity" | "high_complexity" | "insufficient_data";
  complexity_rationale: string;
  algorithm_details?: Record<string, any>;
}

export interface MultiScaleAnalysisResult {
  region_bounds: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
  selected_product_id: string;
  native_resolution_m: number;
  crs: string;
  vertical_datum: string;
  scales: ScaleMetrics[];
  cross_scale_summary: string;
  scientific_limitations: string[];
}

export interface ResolutionTransitionEvaluation {
  product_a: string;
  product_b: string;
  transition_status: "compatible" | "compatible_with_documented_transformation" | "incompatible" | "insufficient_overlap" | "unknown";
  has_overlap: boolean;
  overlap_area_km2: number;
  overlap_bounds?: { min_lat: number; max_lat: number; min_lon: number; max_lon: number } | null;
  resolution_a_m: number;
  resolution_b_m: number;
  resolution_ratio: number;
  horizontal_crs_status: string;
  horizontal_scale_drift_ppm: number;
  vertical_datum_status: string;
  vertical_datum_notes: string;
  pixel_registration_match: boolean;
  permitted_operations: string[];
  forbidden_operations: string[];
  partition_strategy?: {
    strategy: string;
    high_resolution_infill: string;
    regional_context_surround: string;
    boundary_buffer_m: number;
    recommendation: string;
  } | null;
  scientific_justification: string;
  anti_upsampling_safeguards: string[];
}

export interface RegionTerrainAssessment {
  region_id: string;
  name: string;
  bounds: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
  area_km2: number;
  selected_dataset_id: string;
  native_resolution_m: number;
  data_availability: "local_verified" | "local_partial" | "remote_only";
  valid_data_coverage_pct: number;
  analysis_scale_m: number;
  effective_analysis_scale_x_m?: number;
  effective_analysis_scale_y_m?: number;
  effective_analysis_area_km2?: number;
  scale_suitability?: string;
  mean_slope_deg: number;
  max_slope_deg: number;
  p50_slope_deg: number;
  p90_slope_deg: number;
  mean_local_relief_m: number;
  max_local_relief_m: number;
  mean_roughness_m: number;
  max_roughness_m: number;
  elevation_min_m: number;
  elevation_max_m: number;
  elevation_mean_m: number;
  elevation_std_m: number;
  terrain_complexity_class: string;
  complexity_rationale: string;
  terrain_data_quality_index?: number;
  data_confidence_score: number;
  confidence_breakdown: Record<string, number>;
  scientific_summary: string;
  limitations: string[];
}

export interface RegionPairComparison {
  region_a_id: string;
  region_b_id: string;
  slope_contrast: string;
  roughness_contrast: string;
  coverage_contrast: string;
  resolution_contrast: string;
  scale_compatibility?: string;
  comparative_summary: string;
}

export interface RegionComparisonResponse {
  comparison_scale_m: number;
  regions_evaluated: RegionTerrainAssessment[];
  pairwise_comparisons: RegionPairComparison[];
  methodological_notes: string[];
  scientific_disclaimer: string;
}

export interface RouteTerrainSourceResponse {
  start_coord: [number, number];
  dest_coord: [number, number];
  corridor_bounds: { min_lat: number; max_lat: number; min_lon: number; max_lon: number };
  corridor_length_km: number;
  corridor_buffer_m?: number;
  centerline_valid_coverage_pct?: number;
  corridor_envelope_valid_coverage_pct?: number;
  bounding_box_valid_coverage_pct?: number;
  nodata_intersections?: number;
  continuous_traversable_graph_supported?: boolean;
  primary_terrain_product: string;
  primary_resolution_m: number;
  routing_eligible: boolean;
  valid_data_coverage_pct: number;
  unsupported_segments: string[];
  horizontal_crs: string;
  vertical_datum: string;
  datum_compatibility: string;
  selection_rationale: string;
  scientific_limitations: string[];
}

export interface PointElevationDetail {
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  dataset_id: string;
  instrument: string;
  tier: string;
  native_resolution_m: number;
  native_resolution_desc: string;
  display_resolution_m: number | null;
  crs: string;
  vertical_reference: string;
  is_nodata: boolean;
  is_valid: boolean;
  query_status: string;
  status_note: string;
  source_checksum: string;
}

export interface ElevationProfilePoint {
  point_index: number;
  lat: number;
  lon: number;
  distance_m: number;
  elevation_m: number | null;
  dataset_id: string;
  resolution_m: number;
  is_nodata: boolean;
}

export interface ElevationProfileResponse {
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  total_distance_m: number;
  sampling_interval_m: number;
  num_samples: number;
  min_elevation_m: number | null;
  max_elevation_m: number | null;
  elevation_gain_m: number;
  elevation_loss_m: number;
  datasets_used: string[];
  nodata_count: number;
  points: ElevationProfilePoint[];
}

export interface WindowRenderMetadata {
  bbox: number[];
  width: number;
  height: number;
  dataset_id: string;
  source_resolution_m: number;
  display_resolution_m: number;
  resampling_method: string;
  source_checksum: string;
}

// ---------------------------------------------------------------------------
// Phase 8.7 Science Discovery Types
// ---------------------------------------------------------------------------

export interface DiscoveryCategory {
  id: string;
  title: string;
  description: string;
  badge_color: string;
  icon: string;
  discovery_count: number;
}

export interface ScienceDiscovery {
  id: string;
  name: string;
  category: string;
  latitude: number;
  longitude: number;
  coordinate_display?: string;
  primary_feature: string;
  primary_evidence_class?: string;
  primary_source?: {
    feature_or_product: string;
    source_type: string;
    native_scale_or_spacing: string;
    positional_precision?: string;
    vertical_datum?: string;
    vertical_datum_type?: string;
    coverage_limitations?: string;
  };
  scientific_significance: string;
  geological_context: {
    unit_symbol?: string;
    unit_name?: string;
    stratigraphic_age?: string;
    primary_lithology?: string;
    geologic_province?: string;
    [key: string]: any;
  };
  thermal_context: {
    tes_thermal_inertia_si?: number;
    thermophysical_unit?: string;
    themis_ir_covered?: boolean;
    themis_band_9_dn?: number;
    [key: string]: any;
  };
  terrain_context: {
    mola_elevation_m?: number;
    best_dtm_elevation_m?: number;
    highest_resolution_tier?: string;
    finest_ground_spacing_m?: number;
    [key: string]: any;
  };
  supporting_datasets: string[];
  evidence_classes: {
    direct_sensor_observations?: string[];
    measured_observations?: string[];
    derived_measurements: string[];
    mapped_geological_interpretations?: string[];
    indicative_proxies: string[];
    potential_investigations: string[];
  };
  suggested_investigations: string[];
  scientific_limitations: string[];
  derived_metrics?: Record<string, any>;
  distance_km?: number;
}

export interface ScienceProfile {
  query_latitude: number;
  query_longitude: number;
  elevation_analysis: {
    elevation_m: number | null;
    highest_tier: string;
    resolution_m: number;
    vertical_datum: string;
    horizontal_crs: string;
    source_dataset_id: string;
  };
  geological_analysis: {
    unit_code: string | null;
    unit_name: string | null;
    stratigraphic_age: string | null;
    lithology: string | null;
    province: string | null;
    interpretation: string | null;
    nearest_contact: {
      type: string;
      units: string;
      distance_km: number;
    } | null;
    nearest_structure: {
      type: string;
      class: string;
      distance_km: number;
    } | null;
  };
  thermal_analysis: {
    tes_thermal_inertia_si: number | null;
    thermal_unit: string;
    themis_day_ir: {
      covered: boolean;
      product_id: string | null;
      band_9_dn: number | null;
      resolution_m: number | null;
    };
    thermophysical_interpretation: string;
  };
  terrain_analysis: {
    finest_tier: string;
    ground_spacing_m: number;
    available_dtms: string[];
  };
  potential_investigations: string[];
  scientific_limitations: string[];
  nearby_candidate_discoveries: ScienceDiscovery[];
}

export interface ScienceComparisonResponse {
  sites: ScienceProfile[];
  summary: {
    count: number;
    highest_elevation_site: { lat: number; lon: number; elevation_m: number };
    lowest_elevation_site: { lat: number; lon: number; elevation_m: number };
    highest_thermal_inertia_site: { lat: number; lon: number; ti: number };
    geological_diversity: string[];
  };
}

// ---------------------------------------------------------------------------
// Phase 8.8.1: Terrain Traversability Foundation
// ---------------------------------------------------------------------------

export type SlopeCategory = "low" | "moderate" | "high" | "very_high" | "unknown";

export interface TraversabilityMetadata {
  description: string;
  slope_algorithm: string;
  slope_units: string;
  slope_thresholds_deg: Record<string, [number, number]>;
  slope_disclaimer: string;
  vertical_datum_policy: string;
  source_selection_policy: string[];
  anti_upsampling_guarantee: string;
  nodata_policy: string;
  terrain_sources: Array<{
    source_id: string;
    instrument: string;
    mission: string;
    tier: string;
    pixel_spacing_m: number;
    pixel_spacing_desc: string;
    crs: string;
    vertical_datum: string;
    vertical_datum_type: string;
    product_id: string;
    coverage_note: string;
    elevation_file_available: boolean;
    slope_file_available: boolean;
  }>;
}

export interface TraversabilityPointResult {
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  slope_deg: number | null;
  slope_pct: number | null;
  slope_category: SlopeCategory;
  source_id: string;
  instrument: string;
  native_pixel_spacing_m: number;
  native_pixel_spacing_desc: string;
  vertical_datum: string;
  vertical_datum_type: string;
  is_elevation_nodata: boolean;
  is_slope_nodata: boolean;
  source_selection_reason: string;
  fallback_chain: string[];
  slope_disclaimer: string;
  slope_thresholds_deg: Record<string, [number, number]>;
}

export interface TraversabilityWindowResult {
  bbox: number[];
  width_px: number;
  height_px: number;
  source_id: string;
  native_pixel_spacing_m: number;
  display_pixel_spacing_m: number;
  sampling_regime: string;
  slope_values: Array<Array<number | null>>;
  slope_categories: Array<Array<string>>;
  nodata_fraction: number;
  coverage_within_bbox_fraction: number;
  slope_disclaimer: string;
}

export interface TraversabilityCoverageEntry {
  source_id: string;
  instrument: string;
  tier: string;
  pixel_spacing_m: number;
  pixel_spacing_desc: string;
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  elevation_file_available: boolean;
  slope_file_available: boolean;
  coverage_note: string;
  vertical_datum: string;
}

export interface TraversabilityLegendEntry {
  category: string;
  label: string;
  slope_range_deg: string;
  color_hex: string;
  description: string;
}

// ---------------------------------------------------------------------------
// Marswalk Route Planning — Phase 8.8.2
// ---------------------------------------------------------------------------

export interface MarswalkRouteRequest {
  start_lat: number;
  start_lon: number;
  dest_lat: number;
  dest_lon: number;
  preferred_source?: string;
  slope_penalty_factor?: number;
  max_slope_deg?: number;
  max_search_nodes?: number;
  route_name?: string;
}

export interface MarswalkRoutePoint {
  index: number;
  lat: number;
  lon: number;
  elevation_m: number;
  slope_deg: number;
  slope_category: string;
  cumulative_distance_m: number;
}

export interface MarswalkRouteResponse {
  route_id: string;
  status: string;
  route_name?: string;
  start_coord: [number, number];
  dest_coord: [number, number];
  snapped_start_coord: [number, number];
  snapped_dest_coord: [number, number];
  source_dataset: string;
  instrument: string;
  tier: string;
  native_resolution_m: number;
  native_resolution_desc: string;
  vertical_datum: string;
  vertical_datum_type: string;
  total_surface_distance_m: number;
  total_horizontal_distance_m: number;
  total_optimization_cost?: number;
  cumulative_elevation_gain_m: number;
  cumulative_elevation_loss_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  max_route_slope_deg: number;
  mean_route_slope_deg: number;
  slope_band_exposure_pct: Record<string, number>;
  unknown_data_exposure_pct: number;
  geometry: {
    type: "LineString";
    coordinates: Array<[number, number]>;
  };
  path_points: MarswalkRoutePoint[];
  cost_function_parameters: Record<string, any>;
  search_metrics: Record<string, any>;
  coverage_limitations: string;
  safety_disclaimer: string;
}

export interface ValidatedCorridorPreset {
  corridor_id: string;
  name: string;
  region: string;
  source_dataset: string;
  start_lat: number;
  start_lon: number;
  dest_lat: number;
  dest_lon: number;
  description: string;
  target_geology: string;
}

export interface MarswalkMetadataResponse {
  supported_datasets: Array<Record<string, any>>;
  resolution_tiers: Array<Record<string, any>>;
  slope_thresholds_deg: Record<string, [number, number]>;
  default_parameters: Record<string, any>;
  cost_function_definition: string;
  heuristic_definition: string;
  engine_versions?: Record<string, string>;
  safety_disclaimer: string;
  validated_corridors: ValidatedCorridorPreset[];
}

// ---------------------------------------------------------------------------
// Multi-Stop Marswalk Planning — Phase 8.8.3
// ---------------------------------------------------------------------------

export interface ScienceStop {
  stop_id: string;
  name: string;
  lat: number;
  lon: number;
  discovery_id?: string;
  is_mandatory?: boolean;
  target_geology?: string;
  description?: string;
}

export interface MultiStopRouteRequest {
  start_lat: number;
  start_lon: number;
  start_name?: string;
  dest_lat: number;
  dest_lon: number;
  dest_name?: string;
  stops: ScienceStop[];
  discovery_ids?: string[];
  max_stops?: number;
  optimization_strategy?: string;
  preferred_source?: string;
  slope_penalty_factor?: number;
  max_slope_deg?: number;
  max_search_nodes?: number;
  traverse_name?: string;
}

export interface PairwiseRouteLeg {
  leg_index: number;
  from_stop_id: string;
  from_stop_name: string;
  to_stop_id: string;
  to_stop_name: string;
  from_coord: [number, number];
  to_coord: [number, number];
  route_id: string;
  is_feasible: boolean;
  surface_distance_m: number;
  horizontal_distance_m: number;
  optimization_cost: number;
  elevation_gain_m: number;
  elevation_loss_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  max_slope_deg: number;
  mean_slope_deg: number;
  slope_band_exposure_pct: Record<string, number>;
  source_dataset: string;
  geometry: {
    type: "LineString";
    coordinates: Array<[number, number]>;
  };
  error_message?: string;
}

export interface MultiStopTraverseResponse {
  traverse_id: string;
  status: string;
  traverse_name: string;
  start_stop: ScienceStop;
  dest_stop: ScienceStop;
  ordered_stops: ScienceStop[];
  legs: PairwiseRouteLeg[];
  total_surface_distance_m: number;
  total_horizontal_distance_m: number;
  total_optimization_cost: number;
  cumulative_elevation_gain_m: number;
  cumulative_elevation_loss_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  max_route_slope_deg: number;
  mean_route_slope_deg: number;
  slope_band_exposure_pct: Record<string, number>;
  unknown_data_exposure_pct: number;
  source_dataset: string;
  instrument: string;
  tier: string;
  native_resolution_desc: string;
  connected_geometry: {
    type: "LineString";
    coordinates: Array<[number, number]>;
  };
  optimization_strategy: string;
  is_heuristic_solution: boolean;
  unreachable_stops: Array<Record<string, any>>;
  computation_metrics: Record<string, any>;
  safety_disclaimer: string;
}

export interface MultiStopPreset {
  preset_id: string;
  name: string;
  region: string;
  source_dataset: string;
  start_lat: number;
  start_lon: number;
  dest_lat: number;
  dest_lon: number;
  stops: ScienceStop[];
  description: string;
  target_geology: string;
}

export interface MultiStopMetadataResponse {
  supported_strategies: Array<{ strategy: string; description: string }>;
  max_allowed_stops: number;
  cost_function_definition: string;
  optimization_objective: string;
  curated_presets: MultiStopPreset[];
  engine_versions: Record<string, string>;
  safety_disclaimer: string;
}

// ---------------------------------------------------------------------------
// Route Intelligence & Scientific Traverse Analysis — Phase 8.8.4
// ---------------------------------------------------------------------------

export interface RouteElevationProfilePoint {
  sample_index: number;
  distance_m: number;
  lat: number;
  lon: number;
  elevation_m: number;
  slope_deg: number;
  local_gradient_pct: number;
  dem_source: string;
  resolution_m: number;
}

export interface ElevationProfileSummary {
  min_elevation_m: number;
  max_elevation_m: number;
  cumulative_elevation_gain_m: number;
  cumulative_elevation_loss_m: number;
  net_elevation_change_m: number;
  max_gradient_pct: number;
  mean_gradient_pct: number;
  sampling_interval_m: number;
  total_samples: number;
  vertical_datum: string;
  points: RouteElevationProfilePoint[];
}

export interface SlopeExposureBand {
  category: string;
  description: string;
  distance_m: number;
  percentage: number;
}

export interface DemSourceSegment {
  source_id: string;
  instrument: string;
  native_resolution_m: number;
  start_distance_m: number;
  end_distance_m: number;
}

export interface TerrainIntelligenceSummary {
  slope_distribution: Record<string, number>;
  slope_exposure_bands: SlopeExposureBand[];
  mean_slope_deg: number;
  max_slope_deg: number;
  roughness_index_m: number;
  roughness_classification: string;
  nodata_distance_m: number;
  nodata_pct: number;
  coverage_status: string;
  dem_source_segments: DemSourceSegment[];
  cross_resolution_transition: boolean;
  terrain_limitations: string;
}

export interface GeologicalContactCrossing {
  distance_m: number;
  coord: [number, number];
  from_unit: string;
  to_unit: string;
  contact_type: string;
}

export interface GeologicalUnitSegment {
  unit_code: string;
  unit_name: string;
  chronostratigraphic_period: string;
  distance_start_m: number;
  distance_end_m: number;
  traversed_length_m: number;
  traversed_pct: number;
  description: string;
}

export interface NearbyGeologicalStructure {
  object_id: number;
  morphology: string;
  origin: string;
  interpretation: string;
  preservation: string;
  dimension: string;
  distance_from_route_km: number;
  closest_coord: [number, number];
}

export interface GeologicalRouteContext {
  units_traversed: GeologicalUnitSegment[];
  boundaries_crossed: GeologicalContactCrossing[];
  nearby_structures: NearbyGeologicalStructure[];
  published_scale: string;
  cartographic_source: string;
  positional_uncertainty_km: number;
  limitations_disclaimer: string;
}

export interface ThermalInertiaSample {
  distance_m: number;
  lat: number;
  lon: number;
  thermal_inertia_tiu: number | null;
  physical_interpretation: string;
}

export interface ThermophysicalRouteContext {
  min_tiu: number | null;
  max_tiu: number | null;
  mean_tiu: number | null;
  predominant_interpretation: string;
  samples: ThermalInertiaSample[];
  source_product: string;
  native_resolution_desc: string;
  units: string;
  calibration_notes: string;
  themis_context: string;
  temperature_prohibition_disclaimer: string;
}

export interface RouteScienceOpportunity {
  discovery_id: string;
  title: string;
  category: string;
  category_title: string;
  distance_from_route_km: number;
  closest_route_milepost_m: number;
  evidence_class: string;
  supporting_datasets: string[];
  primary_feature: string;
  potential_investigation: string;
  scientific_limitations: string;
}

export interface LegRouteIntelligence {
  leg_index: number;
  from_stop_id: string;
  from_stop_name: string;
  to_stop_id: string;
  to_stop_name: string;
  from_coord: [number, number];
  to_coord: [number, number];
  surface_distance_m: number;
  horizontal_distance_m: number;
  optimization_cost: number;
  elevation_profile: ElevationProfileSummary;
  terrain_intelligence: TerrainIntelligenceSummary;
  geological_context: GeologicalRouteContext;
  thermophysical_context: ThermophysicalRouteContext;
  nearby_science_opportunities: RouteScienceOpportunity[];
  dem_source: string;
  native_resolution_desc: string;
  coverage_limitations: string;
  environmental_context?: RouteEnvironmentalSummary | null;
}

export interface RouteIntelligenceReport {
  route_id: string;
  route_name?: string;
  surface_distance_m: number;
  horizontal_distance_m: number;
  optimization_cost: number;
  start_coord: [number, number];
  dest_coord: [number, number];
  elevation_profile: ElevationProfileSummary;
  terrain_intelligence: TerrainIntelligenceSummary;
  geological_context: GeologicalRouteContext;
  thermophysical_context: ThermophysicalRouteContext;
  nearby_science_opportunities: RouteScienceOpportunity[];
  dem_source: string;
  instrument: string;
  tier: string;
  native_resolution_desc: string;
  vertical_datum: string;
  environmental_context?: RouteEnvironmentalSummary | null;
  safety_disclaimer: string;
}

export interface MultiStopTraverseIntelligenceReport {
  traverse_id: string;
  traverse_name: string;
  total_surface_distance_m: number;
  total_horizontal_distance_m: number;
  total_optimization_cost: number;
  total_legs: number;
  ordered_stop_names: string[];
  legs: LegRouteIntelligence[];
  aggregated_elevation_profile: ElevationProfileSummary;
  aggregated_terrain_intelligence: TerrainIntelligenceSummary;
  aggregated_geological_context: GeologicalRouteContext;
  aggregated_thermophysical_context: ThermophysicalRouteContext;
  aggregated_science_opportunities: RouteScienceOpportunity[];
  dem_source: string;
  instrument: string;
  tier: string;
  native_resolution_desc: string;
  vertical_datum: string;
  aggregated_environmental_context?: RouteEnvironmentalSummary | null;
  safety_disclaimer: string;
}

export interface RouteIntelligenceMetadataResponse {
  system_name: string;
  version: string;
  vertical_datum: string;
  geological_map: Record<string, any>;
  thermal_dataset: Record<string, any>;
  terrain_datasets: Array<Record<string, any>>;
  evidence_classes: Array<{ class: string; description: string }>;
  scientific_rules: string[];
  safety_disclaimer: string;
}

// ── Environmental Intelligence Types — Phase 8.9.1 ─────────────────────────

export type ProvenanceClassification = 
  | "Historical Observation"
  | "Analytical Model"
  | "Climatological Model"
  | "Derived Estimate"
  | "Unavailable";

export interface AtmosphericPressureEstimate {
  elevation_m: number;
  reference_pressure_p0_pa: number;
  scale_height_h_m: number;
  reference_atmospheric_pressure_estimate_pa: number;
  vertical_datum: string;
  classification: ProvenanceClassification;
  model_formula: string;
  scientific_limitations: string;
  safety_disclaimer: string;
}

export interface PressureResidualBenchmark {
  station_id: string;
  station_name: string;
  mission: string;
  landing_site: string;
  coordinates: [number, number];
  elevation_m: number;
  model_pressure_pa: number;
  observed_mean_pressure_pa: number;
  residual_pa: number;
  residual_percent: number;
  observation_sol: number;
  instrument_lid: string;
  classification: ProvenanceClassification;
  notes: string;
}

export interface MarsTimeConversion {
  input_time_hours: number;
  input_system: "LMST" | "LTST" | "MTC";
  lon_deg: number;
  lon_convention: "east_positive" | "west_positive";
  ls_deg: number;
  equation_of_time_hours: number;
  equation_of_time_minutes: number;
  lmst_hours: number;
  ltst_hours: number;
  mtc_hours: number;
  classification: ProvenanceClassification;
  methodology: string;
}

export interface MarsSolarGeometry {
  lat: number;
  lon: number;
  solar_longitude_ls_deg: number;
  local_true_solar_time_hours: number;
  local_mean_solar_time_hours: number;
  equation_of_time_hours: number;
  equation_of_time_minutes: number;
  season_name: string;
  mars_sun_distance_au: number;
  solar_declination_deg: number;
  hour_angle_deg: number;
  solar_zenith_angle_deg: number;
  solar_elevation_deg: number;
  day_night_status: string;
  is_day: boolean;
  sunrise_hour?: number | null;
  sunset_hour?: number | null;
  polar_condition?: string | null;
  toa_normal_irradiance_w_m2: number;
  toa_horizontal_irradiance_w_m2: number;
  surface_direct_normal_irradiance_w_m2?: number | null;
  surface_direct_horizontal_irradiance_w_m2: number;
  top_of_atmosphere_solar_flux_w_m2: number;
  optical_depth_tau?: number | null;
  surface_solar_flux_w_m2: number;
  classification: ProvenanceClassification;
  methodology_citation: string;
  safety_disclaimer: string;
}

export interface HistoricalRoverWeatherRecord {
  station: string;
  timestamp_or_sclk: string;
  lmst: string;
  ltst: string;
  pressure_pa?: number | null;
  ambient_temperature_k?: number | null;
  ground_temperature_k?: number | null;
  relative_humidity_percent?: number | null;
  sensor_flags?: Record<string, any> | null;
}

export interface HistoricalWeatherSummary {
  station_id: string;
  instrument_name: string;
  mission: string;
  site_name: string;
  coordinates: [number, number];
  elevation_m: number;
  sol: number;
  solar_longitude_range_deg: [number, number];
  total_samples: number;
  pressure_summary_pa?: { min_pa: number; max_pa: number; mean_pa: number; count: number } | null;
  ambient_temp_summary_k?: { min_k: number; max_k: number; mean_k: number; count: number } | null;
  ground_temp_summary_k?: { min_k: number; max_k: number; mean_k: number; count: number } | null;
  relative_humidity_summary_pct?: Record<string, number> | null;
  irradiance_summary_w_m2?: Record<string, number> | null;
  pds4_source_lid: string;
  classification: ProvenanceClassification;
  temporal_disclaimer: string;
  sample_records: HistoricalRoverWeatherRecord[];
}

export interface RoutePointEnvironment {
  point_index: number;
  lat: number;
  lon: number;
  distance_m: number;
  elevation_m: number;
  reference_pressure_pa: number;
  solar_zenith_angle_deg: number;
  solar_elevation_deg: number;
  is_day: boolean;
  toa_normal_irradiance_w_m2: number;
  toa_horizontal_irradiance_w_m2: number;
  surface_direct_horizontal_irradiance_w_m2: number;
  toa_solar_flux_w_m2: number;
  surface_solar_flux_w_m2: number;
}

export interface RouteEnvironmentalSummary {
  solar_longitude_ls_deg: number;
  local_true_solar_time_hours: number;
  optical_depth_tau?: number | null;
  min_pressure_pa: number;
  max_pressure_pa: number;
  mean_pressure_pa: number;
  min_surface_flux_w_m2: number;
  max_surface_flux_w_m2: number;
  mean_surface_flux_w_m2: number;
  daylight_percentage: number;
  samples: RoutePointEnvironment[];
  classification: ProvenanceClassification;
  safety_disclaimer: string;
}

export interface EnvironmentalMetadataResponse {
  service_name: string;
  version: string;
  available_models: string[];
  reference_parameters: Record<string, any>;
  classification_tiers: ProvenanceClassification[];
  scientific_limitations: string;
  safety_disclaimer: string;
}

// ── Climatology Types — Phase 8.9.2 (MCD v6.2) ─────────────────────────────

export interface ClimatologyPoint {
  latitude: number;
  longitude: number;
  solar_longitude_ls_deg: number;
  local_true_solar_time_hours: number;
  elevation_m: number;
  season_name: string;
  surface_pressure_pa: number;
  atmospheric_temperature_k: number;
  surface_temperature_k: number;
  wind_speed_m_s: number;
  wind_direction_deg: number;
  wind_cardinal: string;
  dust_optical_depth: number;
  density_kg_m3: number;
  interpolation_method: string;
  is_landmark: boolean;
  nearest_landmark?: string | null;
  distance_to_landmark_km?: number | null;
  classification: ProvenanceClassification;
  model_version: string;
  safety_disclaimer: string;
}

export interface ClimatologyProfilePoint {
  step_value: number;
  surface_pressure_pa: number;
  atmospheric_temperature_k: number;
  surface_temperature_k: number;
  wind_speed_m_s: number;
  dust_optical_depth: number;
}

export interface ClimatologyProfileResponse {
  latitude: number;
  longitude: number;
  elevation_m: number;
  profile_type: "diurnal" | "seasonal";
  fixed_parameter: string;
  independent_variable: string;
  points: ClimatologyProfilePoint[];
  min_temperature_k: number;
  max_temperature_k: number;
  mean_temperature_k: number;
  min_pressure_pa: number;
  max_pressure_pa: number;
  mean_pressure_pa: number;
  classification: ProvenanceClassification;
  model_version: string;
  safety_disclaimer: string;
}

export interface ClimatologyVariableMetadata {
  name: string;
  label: string;
  unit: string;
  valid_range: [number, number];
  description: string;
}

export interface ClimatologyMetadataResponse {
  service_name: string;
  version: string;
  model_name: string;
  scenario: string;
  authoritative_source: string;
  citation: string;
  native_spatial_resolution: string;
  vertical_level: string;
  temporal_coverage: string;
  available_variables: ClimatologyVariableMetadata[];
  classification_tiers: ProvenanceClassification[];
  scientific_limitations: string;
  safety_disclaimer: string;
}

export interface ClimatologyCoverageResponse {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  seasonal_coverage: string;
  diurnal_coverage: string;
  grid_latitudes_deg: number[];
  grid_longitudes_deg: number[];
  landmarks: Record<string, any>;
  classification: ProvenanceClassification;
}

export interface RoutePointClimatology {
  point_index: number;
  lat: number;
  lon: number;
  distance_m: number;
  elevation_m: number;
  climatological_pressure_pa: number;
  climatological_temperature_k: number;
  climatological_surface_temperature_k: number;
  climatological_wind_speed_m_s: number;
  climatological_wind_direction_deg: number;
  climatological_dust_optical_depth: number;
}

export interface RouteClimatologySummary {
  solar_longitude_ls_deg: number;
  local_true_solar_time_hours: number;
  min_climatology_pressure_pa: number;
  max_climatology_pressure_pa: number;
  mean_climatology_pressure_pa: number;
  min_climatology_temp_k: number;
  max_climatology_temp_k: number;
  mean_climatology_temp_k: number;
  min_surface_temp_k: number;
  max_surface_temp_k: number;
  mean_surface_temp_k: number;
  mean_wind_speed_m_s: number;
  max_wind_speed_m_s: number;
  mean_dust_tau: number;
  samples: RoutePointClimatology[];
  classification: ProvenanceClassification;
  safety_disclaimer: string;
}






