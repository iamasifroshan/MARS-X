"""Tests for health and status endpoints."""


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "MARS-X" in data["message"]
    assert "docs" in data
    assert "health" in data


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "MARS-X"
    assert "version" in data


def test_status(client):
    resp = client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "MARS-X"
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert "services" in data
    assert isinstance(data["services"], dict)
    assert "dataset_catalogue" in data["services"]
