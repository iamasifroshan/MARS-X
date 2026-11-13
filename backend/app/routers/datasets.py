"""Datasets router."""

from typing import List, Optional

from fastapi import APIRouter, Query

from app.config import API_V1_PREFIX
from app.models.dataset import DatasetMetadata
from app.services.dataset_catalogue import get_all_datasets, get_datasets_by_mission

router = APIRouter(prefix=API_V1_PREFIX, tags=["datasets"])


@router.get("/datasets", response_model=List[DatasetMetadata])
async def list_datasets(mission: Optional[str] = Query(None, description="Filter by mission name (substring, case-insensitive)")):
    """Return all registered Mars datasets, optionally filtered by mission."""
    if mission:
        return get_datasets_by_mission(mission)
    return get_all_datasets()
