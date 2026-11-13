"""Health and status response models."""

from typing import Dict
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str


class StatusResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    uptime_seconds: float
    services: Dict[str, str]
