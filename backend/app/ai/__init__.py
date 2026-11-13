"""AI assistant and intelligence package for MARS-X.

Coordinates Martian terrain intelligence, natural-language mission queries,
and multimodal tool calling for traverse safety and science target prioritization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AIQueryRequest(BaseModel):
    prompt: str = Field(..., description="User exploration or mission planning query")
    context_coordinates: Optional[Dict[str, float]] = Field(None, description="Optional Martian lat/lon focus")
    selected_datasets: List[str] = Field(default_factory=list)


class AIQueryResponse(BaseModel):
    query_id: str
    response_text: str
    suggested_actions: List[str] = []
    source_datasets: List[str] = []
    status: str = "foundation_stub"

