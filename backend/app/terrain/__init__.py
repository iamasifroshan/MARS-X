"""Terrain analysis package for MARS-X.

Provides interfaces and data models for Martian terrain characterisation:
- Slope and aspect computation
- Surface roughness and obstacle hazards
- Elevation profiles and line-of-sight analysis

Scientific constraint: Separates visual shaded-relief imagery from numerical
Digital Terrain Models (DTMs). Numerical DTMs are strictly required for calculations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class TerrainPoint(BaseModel):
    """Martian geographic location with elevation."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Martian planetocentric latitude (degrees)")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Martian positive east longitude (degrees)")
    elevation_m: Optional[float] = Field(None, description="Areoid relative elevation in meters")


class TerrainProfileRequest(BaseModel):
    """Request model for an elevation profile between two coordinates."""
    start: TerrainPoint
    end: TerrainPoint
    sampling_interval_m: float = Field(100.0, gt=0, description="Sampling distance along traverse in meters")
    dtm_dataset_id: str = Field("mola-megdr", description="Source numerical DTM dataset")


class TerrainProfileResponse(BaseModel):
    """Profile calculation response with terrain metrics."""
    dataset_id: str
    points: List[TerrainPoint] = []
    max_slope_deg: Optional[float] = None
    mean_slope_deg: Optional[float] = None
    total_distance_m: Optional[float] = None
    status: str = "pending_raster_engine"
