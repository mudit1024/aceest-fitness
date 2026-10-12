"""Tests for the application shell: health, index and error handling."""
from aceest import __version__


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "version": __version__}


def test_index_lists_endpoints(client):
    body = client.get("/").get_json()
    assert body["service"] == "ACEest Fitness & Gym API"
    assert "/health" in body["endpoints"]
    assert "/programs" in body["endpoints"]


def test_unknown_route_returns_json_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json()["error"] == "Not Found"


def test_wrong_method_returns_json_405(client):
    resp = client.delete("/health")
    assert resp.status_code == 405
    assert resp.get_json()["error"] == "Method Not Allowed"
