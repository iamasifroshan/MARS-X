"""Pydantic data models and schemas for Multi-Stop Marswalk Planning — Phase 8.8.3.

Supports:
- Science stop representation with Phase 8.7 discovery integration
- Multi-stop traverse requests with TSP-style optimization strategies
- Pairwise route leg telemetry and feasibility tracking
- Connected traverse geometry and aggregated multi-stop analytical summaries
- Clear distinction between physical surface distance and analytical optimization cost
- Non-negotiable astronaut safety disclaimers
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.marswalk.marswalk_models import MARSWALK_SAFETY_DISCLAIMER


class ScienceStop(BaseModel):
    """A designated waypoint or science target on Mars."""

    stop_id: str = Field(..., description="Unique stop identifier, e.g. 'stop-01' or 'disc-terr-tyrrhena-ctx'")
    name: str = Field(..., description="Human-readable name or landmark title")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude (-90° to +90°)")
    lon: float = Field(..., description="Longitude (0° to 360° or -180° to +180°)")
    discovery_id: Optional[str] = Field(None, description="Optional associated Phase 8.7 discovery candidate ID")
    is_mandatory: bool = Field(default=True, description="Whether this stop must be visited or can be dropped if stop limit exceeded")
    target_geology: Optional[str] = Field(None, description="Geological unit, rock type or feature description")
    description: Optional[str] = Field(None, description="Exploration objective or notes")


class MultiStopRouteRequest(BaseModel):
    """Request payload for multi-stop Marswalk traverse planning."""

    start_lat: float = Field(..., ge=-90.0, le=90.0, description="Origin latitude (-90° to +90°)")
    start_lon: float = Field(..., description="Origin longitude (0° to 360° or -180° to +180°)")
    start_name: Optional[str] = Field(default="Base Camp / Lander", description="Label for starting location")

    dest_lat: float = Field(..., ge=-90.0, le=90.0, description="Final destination latitude (-90° to +90°)")
    dest_lon: float = Field(..., description="Final destination longitude (0° to 360° or -180° to +180°)")
    dest_name: Optional[str] = Field(default="Return Vehicle / Outpost", description="Label for final destination")

    stops: List[ScienceStop] = Field(
        default_factory=list,
        description="List of candidate science stops to visit along the traverse",
    )
    discovery_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of Phase 8.7 discovery IDs to automatically convert into science stops",
    )
    max_stops: Optional[int] = Field(
        default=None,
        ge=1,
        le=12,
        description="Maximum number of intermediate science stops to include in the final traverse",
    )
    optimization_strategy: str = Field(
        default="optimize_tsp",
        description="Ordering strategy: 'optimize_tsp' (nearest-neighbor + 2-opt), 'nearest_neighbor', or 'preserve_order'",
    )
    preferred_source: Optional[str] = Field(
        default="auto",
        description="Preferred DEM dataset ('auto', 'hirise-holden', 'ctx-tyrrhena', 'ctx-apollinaris', 'mola-128ppd', 'mola-4ppd')",
    )
    slope_penalty_factor: float = Field(
        default=2.0,
        ge=0.0,
        le=20.0,
        description="Quadratic penalty weight beta for steep slopes",
    )
    max_slope_deg: float = Field(
        default=25.0,
        ge=1.0,
        le=45.0,
        description="Hard maximum slope cutoff angle in degrees",
    )
    max_search_nodes: int = Field(
        default=150000,
        ge=1000,
        le=1000000,
        description="Maximum A* node expansion limit per pairwise route leg",
    )
    traverse_name: Optional[str] = Field(
        default=None,
        description="Optional descriptive title for the traverse",
    )


class PairwiseRouteLeg(BaseModel):
    """Detailed telemetry and geometry for a single directional leg between two stops."""

    leg_index: int = Field(..., description="0-based sequence index of the leg in the traverse")
    from_stop_id: str = Field(..., description="Origin stop ID")
    from_stop_name: str = Field(..., description="Origin stop name")
    to_stop_id: str = Field(..., description="Destination stop ID")
    to_stop_name: str = Field(..., description="Destination stop name")
    from_coord: Tuple[float, float] = Field(..., description="(lat, lon) of origin")
    to_coord: Tuple[float, float] = Field(..., description="(lat, lon) of destination")

    route_id: str = Field(..., description="Underlying A* route identifier")
    is_feasible: bool = Field(default=True, description="Whether this leg was successfully navigated within slope and bounds")
    surface_distance_m: float = Field(..., description="Physical 3D surface traversal distance in metres")
    horizontal_distance_m: float = Field(..., description="Planimetric 2D traversal distance in metres")
    optimization_cost: float = Field(..., description="Total cost-function value minimized by A*")
    elevation_gain_m: float = Field(..., description="Cumulative elevation ascent in metres")
    elevation_loss_m: float = Field(..., description="Cumulative elevation descent in metres")
    min_elevation_m: float = Field(..., description="Minimum elevation along leg in metres")
    max_elevation_m: float = Field(..., description="Maximum elevation along leg in metres")
    max_slope_deg: float = Field(..., description="Maximum slope encountered on leg in degrees")
    mean_slope_deg: float = Field(..., description="Distance-weighted mean slope on leg in degrees")
    slope_band_exposure_pct: Dict[str, float] = Field(..., description="Exposure breakdown across slope categories")
    source_dataset: str = Field(..., description="DEM dataset used for this leg")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON LineString geometry for this leg")
    error_message: Optional[str] = Field(default=None, description="Error detail if leg is infeasible")


class MultiStopTraverseResponse(BaseModel):
    """Complete multi-stop science traverse response with connected geometry and aggregated analytics."""

    traverse_id: str = Field(..., description="Unique multi-stop traverse identifier, e.g. 'mst-1a2b3c4d'")
    status: str = Field(default="success", description="'success', 'partial', or 'unreachable_stops'")
    traverse_name: str = Field(..., description="Title of the planned traverse")

    start_stop: ScienceStop = Field(..., description="Origin stop location")
    dest_stop: ScienceStop = Field(..., description="Final destination stop location")
    ordered_stops: List[ScienceStop] = Field(..., description="Optimized sequence of intermediate science stops")
    legs: List[PairwiseRouteLeg] = Field(..., description="Ordered list of individual pairwise route legs")

    total_surface_distance_m: float = Field(..., description="Total physical 3D ground distance across all legs in metres")
    total_horizontal_distance_m: float = Field(..., description="Total 2D planimetric distance in metres")
    total_optimization_cost: float = Field(
        ...,
        description="Total analytical graph traversal cost (minimized by A* and TSP). Distinct from physical ground distance.",
    )
    cumulative_elevation_gain_m: float = Field(..., description="Sum of elevation gain across all legs in metres")
    cumulative_elevation_loss_m: float = Field(..., description="Sum of elevation loss across all legs in metres")
    min_elevation_m: float = Field(..., description="Absolute lowest elevation encountered on traverse")
    max_elevation_m: float = Field(..., description="Absolute highest elevation encountered on traverse")
    max_route_slope_deg: float = Field(..., description="Steepest slope encountered on any segment of the traverse")
    mean_route_slope_deg: float = Field(..., description="Distance-weighted average slope across the entire traverse")
    slope_band_exposure_pct: Dict[str, float] = Field(..., description="Aggregated exposure percentages across slope categories")
    unknown_data_exposure_pct: float = Field(default=0.0, description="Percentage of traverse in NoData areas (must be 0.0)")

    source_dataset: str = Field(..., description="Primary DEM dataset resolving all stops")
    instrument: str = Field(..., description="Instrument name (HiRISE, CTX, MOLA)")
    tier: str = Field(..., description="Resolution tier (local_tactical, regional, etc.)")
    native_resolution_desc: str = Field(..., description="Human-readable pixel spacing description")

    connected_geometry: Dict[str, Any] = Field(
        ...,
        description="Single connected GeoJSON LineString geometry joining all legs without duplicate junction vertices",
    )
    optimization_strategy: str = Field(..., description="Strategy employed: 'exact_permutation', 'nearest_neighbor_2opt', 'preserve_order'")
    is_heuristic_solution: bool = Field(..., description="True if heuristic (2-opt), False if proved exact (brute-force)")
    unreachable_stops: List[Dict[str, Any]] = Field(default_factory=list, description="List of any stops that could not be routed")
    computation_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance and search statistics")
    safety_disclaimer: str = Field(default=MARSWALK_SAFETY_DISCLAIMER, description="Mandatory astronaut safety warning")


class MultiStopPreset(BaseModel):
    """Curated multi-stop traverse preset for interactive demonstration."""

    preset_id: str
    name: str
    region: str
    source_dataset: str
    start_lat: float
    start_lon: float
    dest_lat: float
    dest_lon: float
    stops: List[ScienceStop]
    description: str
    target_geology: str


class MultiStopMetadataResponse(BaseModel):
    """Metadata describing multi-stop traversal capabilities, optimization algorithms, and presets."""

    supported_strategies: List[Dict[str, str]]
    max_allowed_stops: int
    cost_function_definition: str
    optimization_objective: str
    curated_presets: List[MultiStopPreset]
    engine_versions: Dict[str, str]
    safety_disclaimer: str = MARSWALK_SAFETY_DISCLAIMER
