"""Mission and EVA planning package for MARS-X.

Coordinates surface exploration operations:
- Habitat landing sites
- Crewed EVA checklists and hazard assessments
- Communications line-of-sight and relay orbiter passes
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class EVAPlan(BaseModel):
    eva_id: str
    mission_sol: int = Field(..., ge=1, description="Martian sol of the EVA")
    crew_members: List[str]
    primary_objective: str
    contingency_return_time_min: int = Field(45, description="Safe walkback buffer in minutes")
    status: str = "draft"
