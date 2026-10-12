"""API tests for the programme catalogue and calorie calculator."""
import pytest


def test_list_programs_returns_all_three(client):
    resp = client.get("/programs")
    assert resp.status_code == 200
    codes = {p["code"] for p in resp.get_json()["programs"]}
    assert codes == {"FL", "MG", "BG"}


def test_program_detail(client):
    body = client.get("/programs/mg").get_json()
    assert body["name"] == "Muscle Gain"
    assert body["calorie_factor"] == 35
    assert any("Deadlift" in day for day in body["workout"])


def test_program_detail_unknown_returns_404(client):
    resp = client.get("/programs/XYZ")
    assert resp.status_code == 404
    assert "XYZ" in resp.get_json()["message"]


def test_calories_endpoint(client):
    resp = client.post("/calories", json={"weight": 70, "program": "fl"})
    assert resp.status_code == 200
    assert resp.get_json() == {"weight": 70, "program": "FL", "calories": 1540}


@pytest.mark.parametrize("payload", [
    {"weight": 70, "program": "NOPE"},
    {"weight": -1, "program": "FL"},
    {"program": "FL"},
    {"weight": 70},
])
def test_calories_endpoint_validation(client, payload):
    resp = client.post("/calories", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Bad Request"


def test_calories_endpoint_requires_json_object(client):
    resp = client.post("/calories", data="not json",
                       content_type="text/plain")
    assert resp.status_code == 400
