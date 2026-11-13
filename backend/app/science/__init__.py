"""Science observation package for MARS-X.

Manages scientific targets of interest, instrument footprints,
and observation planning across orbiters and surface assets.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ScienceTarget(BaseModel):
    target_id: str
    name: str
    latitude: float
    longitude: float
    priority: int = Field(1, ge=1, le=5)
    scientific_rationale: str
    recommended_instruments: List[str] = []
    associated_datasets: List[str] = []
    status: str = "registered"
