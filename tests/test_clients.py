"""API tests for client management, BMI and membership."""
from datetime import date, timedelta

import pytest


@pytest.fixture
def arjun(client):
    resp = client.post("/clients", json={
        "name": "Arjun", "age": 28, "height": 175, "weight": 80,
        "program": "mg", "target_weight": 85, "target_adherence": 90,
    })
    assert resp.status_code == 201
    return resp.get_json()


def test_list_clients_starts_empty(client):
    assert client.get("/clients").get_json() == {"clients": []}


def test_create_client_computes_calories(client, arjun):
    assert arjun["name"] == "Arjun"
    assert arjun["program"] == "MG"            # normalised to upper case
    assert arjun["calories"] == 80 * 35
    assert arjun["membership_status"] == "Active"


def test_create_client_sets_location_header(client):
    resp = client.post("/clients", json={"name": "Meera"})
    assert resp.headers["Location"].endswith("/clients/Meera")


def test_create_client_minimal_has_no_calories(client):
    body = client.post("/clients", json={"name": "Meera"}).get_json()
    assert body["calories"] is None


def test_create_duplicate_client_returns_409(client, arjun):
    resp = client.post("/clients", json={"name": "Arjun"})
    assert resp.status_code == 409


def test_client_name_is_trimmed(client):
    client.post("/clients", json={"name": "  Ravi  "})
    assert client.get("/clients/Ravi").status_code == 200


@pytest.mark.parametrize("payload,message", [
    ({}, "'name' is required"),
    ({"name": "   "}, "'name' is required"),
    ({"name": "X", "age": "28"}, "'age' must be an integer"),
    ({"name": "X", "age": 28.5}, "'age' must be an integer"),
    ({"name": "X", "weight": True}, "'weight' must be a number"),
    ({"name": "X", "weight": 5}, "'weight' must be between"),
    ({"name": "X", "target_adherence": 101}, "'target_adherence' must be between"),
    ({"name": "X", "program": "ZZ"}, "Unknown program"),
    ({"name": "X", "membership_end": "31-12-2026"}, "YYYY-MM-DD"),
    ({"name": "X", "colour": "red"}, "Unknown field(s): colour"),
])
def test_create_client_validation(client, payload, message):
    resp = client.post("/clients", json=payload)
    assert resp.status_code == 400
    assert message in resp.get_json()["message"]


def test_create_client_requires_json(client):
    resp = client.post("/clients", data="name=Arjun",
                       content_type="application/x-www-form-urlencoded")
    assert resp.status_code == 400


def test_get_client(client, arjun):
    body = client.get("/clients/Arjun").get_json()
    assert body == arjun


def test_get_missing_client_returns_404(client):
    resp = client.get("/clients/Ghost")
    assert resp.status_code == 404
    assert "Ghost" in resp.get_json()["message"]


def test_list_clients_sorted_by_name(client):
    for name in ["Zara", "Arjun", "Meera"]:
        client.post("/clients", json={"name": name})
    names = [c["name"] for c in client.get("/clients").get_json()["clients"]]
    assert names == ["Arjun", "Meera", "Zara"]


def test_update_program_recalculates_calories(client, arjun):
    body = client.put("/clients/Arjun", json={"program": "FL"}).get_json()
    assert body["program"] == "FL"
    assert body["calories"] == 80 * 22


def test_patch_weight_recalculates_calories(client, arjun):
    body = client.patch("/clients/Arjun", json={"weight": 90}).get_json()
    assert body["weight"] == 90
    assert body["calories"] == 90 * 35
    assert body["age"] == 28                    # untouched fields preserved


def test_update_cannot_rename(client, arjun):
    resp = client.put("/clients/Arjun", json={"name": "Bob"})
    assert resp.status_code == 400


def test_update_with_empty_body_returns_400(client, arjun):
    assert client.put("/clients/Arjun", json={}).status_code == 400


def test_update_missing_client_returns_404(client):
    assert client.put("/clients/Ghost", json={"age": 30}).status_code == 404


def test_delete_client(client, arjun):
    resp = client.delete("/clients/Arjun")
    assert resp.get_json() == {"deleted": "Arjun"}
    assert client.get("/clients/Arjun").status_code == 404


def test_delete_missing_client_returns_404(client):
    assert client.delete("/clients/Ghost").status_code == 404


def test_bmi(client, arjun):
    body = client.get("/clients/Arjun/bmi").get_json()
    assert body["bmi"] == 26.1                  # 80 / 1.75^2
    assert body["category"] == "Overweight"


def test_bmi_needs_height_and_weight(client):
    client.post("/clients", json={"name": "Meera", "weight": 60})
    assert client.get("/clients/Meera/bmi").status_code == 422


def test_membership_active(client):
    end = (date.today() + timedelta(days=30)).isoformat()
    client.post("/clients", json={"name": "Meera", "membership_end": end})
    body = client.get("/clients/Meera/membership").get_json()
    assert body["status"] == "Active"
    assert body["days_remaining"] == 30


def test_membership_expired(client):
    client.post("/clients", json={"name": "Meera", "membership_end": "2020-01-01"})
    body = client.get("/clients/Meera/membership").get_json()
    assert body["status"] == "Expired"
    assert body["days_remaining"] == 0


def test_membership_without_end_date(client, arjun):
    body = client.get("/clients/Arjun/membership").get_json()
    assert body["status"] == "No end date"


def test_data_persists_across_app_instances(tmp_path):
    from aceest import create_app
    config = {"TESTING": True, "DATABASE": str(tmp_path / "persist.db")}
    create_app(config).test_client().post("/clients", json={"name": "Arjun"})
    resp = create_app(config).test_client().get("/clients/Arjun")
    assert resp.status_code == 200
