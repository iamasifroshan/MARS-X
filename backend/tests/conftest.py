"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """Starlette / HTTPX TestClient bound to the MARS-X FastAPI app."""
    with TestClient(app) as c:
        yield c
