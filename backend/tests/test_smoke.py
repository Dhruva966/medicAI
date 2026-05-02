"""Smoke test — proves the app boots and exposes /health."""

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_lists_routers() -> None:
    """All five domain routers should be mounted."""
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/vessels" in paths
    assert "/vessels/{imo}" in paths
    assert "/vessels/{imo}/score" in paths
    assert "/vessels/{imo}/brief" in paths
    assert "/vessels/{imo}/network" in paths
    assert "/vessels/{imo}/sar" in paths
