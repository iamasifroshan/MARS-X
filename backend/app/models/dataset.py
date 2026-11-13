"""Dataset metadata models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ProcessingStatus(str, Enum):
    registered = "registered"
    available = "available"
    downloaded = "downloaded"
    validated = "validated"
    error = "error"


class DatasetMetadata(BaseModel):
    dataset_id: str
    name: str
    mission: str
    instrument: str
    product_type: str
    spatial_resolution: Optional[str] = None
    acquisition_date_range: Optional[str] = None
    geographic_footprint: Optional[str] = None
    crs: str
    source_url: str
    data_format: str
    coverage: str
    processing_status: ProcessingStatus
    scientific_limitations: Optional[str] = None
    description: str
