"""Tests for the datasets catalogue endpoint."""

REQUIRED_FIELDS = {
    "dataset_id", "name", "mission", "instrument", "product_type",
    "crs", "source_url", "data_format", "coverage",
    "processing_status", "description",
}


def test_list_datasets(client):
    resp = client.get("/api/v1/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 11, f"Expected at least 11 datasets, got {len(data)}"


def test_dataset_required_fields(client):
    resp = client.get("/api/v1/datasets")
    data = resp.json()
    for ds in data:
        for field in REQUIRED_FIELDS:
            assert field in ds, f"Missing field '{field}' in dataset '{ds.get('name', '?')}'"


def test_all_datasets_registered(client):
    resp = client.get("/api/v1/datasets")
    data = resp.json()
    for ds in data:
        assert ds["processing_status"] == "registered", (
            f"Dataset '{ds['name']}' has status '{ds['processing_status']}', expected 'registered'"
        )


def test_filter_by_mission_mro(client):
    resp = client.get("/api/v1/datasets", params={"mission": "MRO"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3, f"Expected at least 3 MRO datasets, got {len(data)}"
    for ds in data:
        assert "mro" in ds["mission"].lower() or "reconnaissance" in ds["mission"].lower()


def test_filter_by_mission_no_match(client):
    resp = client.get("/api/v1/datasets", params={"mission": "nonexistent_mission_xyz"})
    assert resp.status_code == 200
    data = resp.json()
    assert data == []
