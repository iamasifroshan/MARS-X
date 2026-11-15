"""Automated verification of production and development CORS configuration in MARS-X."""

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import CORS_ORIGINS, DEFAULT_CORS_ORIGINS


@pytest.fixture
def client():
    return TestClient(app)


def test_production_vercel_origin_in_cors_origins():
    """Requirement 1: Allow the production frontend origin: https://mars-x-nasa.vercel.app."""
    assert "https://mars-x-nasa.vercel.app" in CORS_ORIGINS, (
        "Production frontend origin https://mars-x-nasa.vercel.app must be present in CORS_ORIGINS"
    )


def test_localhost_development_origins_preserved():
    """Requirement 2: Preserve localhost development origins, including http://localhost:3005."""
    assert "http://localhost:3005" in CORS_ORIGINS
    assert "http://127.0.0.1:3005" in CORS_ORIGINS
    assert "http://localhost:3000" in CORS_ORIGINS
    assert "http://127.0.0.1:3000" in CORS_ORIGINS


def test_no_wildcards_when_credentials_enabled():
    """Requirement 5: Do not use wildcard origins when credentials are enabled."""
    assert "*" not in CORS_ORIGINS, "CORS_ORIGINS must not contain wildcard '*' when credentials are enabled"
    for origin in CORS_ORIGINS:
        assert origin != "*", f"Origin '{origin}' is a wildcard, violating CORS credential security"


def test_preflight_production_vercel_origin(client):
    """Test that preflight OPTIONS request for production origin returns 200 with correct headers."""
    response = client.options(
        "/health",
        headers={
            "Origin": "https://mars-x-nasa.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://mars-x-nasa.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_preflight_localhost_3005_origin(client):
    """Test that preflight OPTIONS request for http://localhost:3005 returns 200 with correct headers."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3005",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3005"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_get_request_cors_headers(client):
    """Test that actual GET request returns appropriate CORS headers."""
    response = client.get(
        "/health",
        headers={"Origin": "https://mars-x-nasa.vercel.app"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://mars-x-nasa.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_disallowed_origin_rejected(client):
    """Test that unauthorized origins are rejected during preflight."""
    response = client.options(
        "/health",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
