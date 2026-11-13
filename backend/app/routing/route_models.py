"""Pydantic data models for Mars terrain-constrained route planning."""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field


class PathfindingAlgorithm(str, Enum):
    """Supported pathfinding algorithms."""
    ASTAR = "astar"
    DIJKSTRA = "dijkstra"


class NeighborConnectivity(int, Enum):
    """Grid neighbor connectivity."""
    FOUR_WAY = 4
    EIGHT_WAY = 8


class TerrainCostWeights(BaseModel):
    """Configurable weights for soft terrain hazard penalties."""
    weight_slope: float = Field(2.0, ge=0.0, le=10.0, description="Multiplier for normalized slope penalty")
    weight_roughness: float = Field(1.5, ge=0.0, le=10.0, description="Multiplier for local roughness penalty")
    weight_relief: float = Field(1.0, ge=0.0, le=10.0, description="Multiplier for local elevation relief penalty")
    weight_complexity: float = Field(1.5, ge=0.0, le=10.0, description="Multiplier for discrete terrain complexity category")


class ExclusionZone(BaseModel):
    """Geographic bounding box defining an impassable obstacle or restricted zone."""
    name: str = "Exclusion Zone"
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


class RoutePlanRequest(BaseModel):
    """User mission routing request."""
    start_lat: float = Field(..., ge=-90.0, le=90.0, description="Start latitude in planetocentric degrees")
    start_lon: float = Field(..., ge=0.0, le=360.0, description="Start positive-East longitude in degrees")
    dest_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination latitude in planetocentric degrees")
    dest_lon: float = Field(..., ge=0.0, le=360.0, description="Destination positive-East longitude in degrees")
    dataset_id: str = Field("mola-megdr-128", description="Target elevation DTM dataset ID")
    algorithm: PathfindingAlgorithm = Field(PathfindingAlgorithm.ASTAR, description="Pathfinding algorithm (A* or Dijkstra)")
    connectivity: NeighborConnectivity = Field(NeighborConnectivity.EIGHT_WAY, description="Movement connectivity (4-way or 8-way)")
    cost_weights: TerrainCostWeights = Field(default_factory=TerrainCostWeights, description="Cost surface weights")
    max_slope_deg: float = Field(15.0, ge=1.0, le=45.0, description="Maximum allowed slope in degrees before impassable")
    max_snapping_distance_m: float = Field(2000.0, ge=100.0, le=10000.0, description="Maximum distance to snap coordinates to valid raster pixels")
    max_search_nodes: int = Field(150000, ge=1000, le=1000000, description="Resource limit on expanded nodes")
    exclusion_zones: List[ExclusionZone] = Field(default_factory=list, description="Optional impassable exclusion zones")


class RouteWaypoint(BaseModel):
    """Single point along a planned route."""
    latitude: float
    longitude: float
    elevation_m: float
    slope_deg: float
    roughness_m: float
    relief_m: float
    cumulative_distance_m: float
    complexity_class: str


class RouteSummaryMetrics(BaseModel):
    """Aggregate scientific and geometric metrics for a generated route."""
    total_distance_m: float
    cumulative_elevation_gain_m: float
    cumulative_elevation_loss_m: float
    min_elevation_m: float
    max_elevation_m: float
    max_slope_deg: float
    mean_slope_deg: float
    mean_roughness_m: float
    mean_local_relief_m: float
    high_complexity_fraction: float
    nodes_expanded: int
    nodes_visited: int
    search_duration_ms: float
    total_cost: float


class RouteValidationSummary(BaseModel):
    """Results of independent scientific route verification."""
    is_valid: bool
    passed_checks: List[str]
    failed_checks: List[str]
    max_encountered_slope_deg: float
    steepest_segment_indices: Optional[Tuple[int, int]] = None
    diagonal_corner_cuts_count: int = 0
    nodata_violations_count: int = 0


class RoutePlanResponse(BaseModel):
    """Complete route-planning response with explainability and disclaimers."""
    route_id: str
    algorithm: PathfindingAlgorithm
    requested_start: Tuple[float, float]
    requested_dest: Tuple[float, float]
    snapped_start: Tuple[float, float]
    snapped_dest: Tuple[float, float]
    snapping_distance_start_m: float
    snapping_distance_dest_m: float
    waypoints: List[RouteWaypoint]
    metrics: RouteSummaryMetrics
    validation: RouteValidationSummary
    dataset_id: str
    dataset_checksum: str
    native_resolution_m: float
    planning_grid_spacing_m: float
    cost_weights: TerrainCostWeights
    max_slope_threshold_deg: float
    explanation: str
    scientific_disclaimer: str = (
        "MARS-X route planning is an experimental terrain-cost simulation based on the selected digital terrain model. "
        "It does NOT establish astronaut safety, EVA feasibility, obstacle clearance, or operational navigability. "
        "Results are limited by source resolution (463 m/px), coverage, and data uncertainty."
    )


class RouteComparisonResponse(BaseModel):
    """Side-by-side comparison between A* and Dijkstra on identical mission inputs."""
    request: RoutePlanRequest
    astar_route: RoutePlanResponse
    dijkstra_route: RoutePlanResponse
    cost_difference: float
    cost_difference_pct: float
    distance_difference_m: float
    runtime_speedup_factor: float
    nodes_expanded_ratio: float
    path_geometries_identical: bool
    scientific_synthesis: str
