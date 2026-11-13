"""Dataset catalogue service — loads dataset metadata from JSON."""

import json
import pathlib
from typing import List, Optional

from app.models.dataset import DatasetMetadata

_DATA_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "nasa_datasets.json"

_catalogue: List[DatasetMetadata] = []


def _load() -> List[DatasetMetadata]:
    global _catalogue
    if not _catalogue:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _catalogue = [DatasetMetadata(**item) for item in raw]
    return _catalogue


def get_all_datasets() -> List[DatasetMetadata]:
    """Return every registered dataset."""
    return list(_load())


def get_datasets_by_mission(mission: str) -> List[DatasetMetadata]:
    """Return datasets whose mission field contains *mission* (case-insensitive)."""
    term = mission.lower()
    return [d for d in _load() if term in d.mission.lower()]
