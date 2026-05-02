"""Smoke test — proves the app boots and exposes /health."""

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_lists_routers() -> None:
    """All domain routers should be mounted."""
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    for p in (
        "/vessels",
        "/vessels/{imo}",
        "/vessels/{imo}/score",
        "/vessels/{imo}/brief",
        "/vessels/{imo}/network",
        "/vessels/{imo}/sar",
        "/vessels/{imo}/evidence",
    ):
        assert p in paths, f"missing {p}"
