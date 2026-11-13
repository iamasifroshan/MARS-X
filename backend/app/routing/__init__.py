"""Route and traverse planning package for MARS-X.

Provides pathfinding and energy-cost models for:
- Astronaut Extravehicular Activity (EVA) Marswalks
- Robotic uncrewed rovers

Accounts for slope impedance, soil trafficability, solar exposure,
and life-support safety limits.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    id: str
    latitude: float
    longitude: float
    name: Optional[str] = None
    stay_duration_minutes: float = Field(0.0, ge=0)


class RouteConstraints(BaseModel):
    max_slope_deg: float = Field(15.0, description="Max traversable slope for astronaut safety")
    max_distance_km: float = Field(10.0, description="Max round-trip radius from habitat/rover")
    max_duration_hours: float = Field(6.0, description="Life support consumable margin")


class RoutePlan(BaseModel):
    route_id: str
    name: str
    waypoints: List[Waypoint]
    constraints: RouteConstraints
    status: str = "planned"
