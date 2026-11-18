"""Smoke tests for FastAPI app and healthcheck."""

from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_openapi_schema_loads() -> None:
    with TestClient(app) as client:
        resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/instances" in paths
    assert "/api/v1/messages/{instance_name}/text" in paths
    assert "/api/v1/groups/{instance_name}" in paths
    assert "/api/v1/webhooks/evolution" in paths
    assert "/api/v1/ai/generate" in paths
    assert "/api/v1/ai/{instance_name}/send" in paths
    assert "/api/v1/ai/{instance_name}/memory/{number}" in paths
    assert "/api/v1/backups" in paths
    assert "/api/v1/backups/snapshot" in paths
    assert "/api/v1/backups/maintenance" in paths
