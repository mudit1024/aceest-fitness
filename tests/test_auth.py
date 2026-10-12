"""Tests for login and the programme generator."""
import random

import pytest

from aceest import create_app, logic


def test_login_default_admin(client):
    resp = client.post("/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    assert resp.get_json() == {"username": "admin", "role": "Admin"}


@pytest.mark.parametrize("username,password", [
    ("admin", "wrong"),
    ("nobody", "admin"),
])
def test_login_rejects_bad_credentials(client, username, password):
    resp = client.post("/login", json={"username": username, "password": password})
    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Invalid username or password"


@pytest.mark.parametrize("payload", [{}, {"username": "admin"}, {"password": "x"}])
def test_login_requires_both_fields(client, payload):
    assert client.post("/login", json=payload).status_code == 400


def test_admin_password_is_configurable(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "auth.db"),
        "ADMIN_PASSWORD": "s3cret!",
        "PASSWORD_HASH_METHOD": "pbkdf2:sha256:1000",
    })
    client = app.test_client()
    default = {"username": "admin", "password": "admin"}
    custom = {"username": "admin", "password": "s3cret!"}
    assert client.post("/login", json=default).status_code == 401
    assert client.post("/login", json=custom).status_code == 200


def test_password_is_not_stored_in_plain_text(app):
    from aceest.db import get_db
    with app.app_context():
        stored = get_db().execute(
            "SELECT password_hash FROM users WHERE username = 'admin'").fetchone()[0]
    assert stored != "admin"
    assert stored.startswith("pbkdf2:")


def test_generate_program_is_reproducible_with_seed():
    first = logic.generate_program(random.Random(42))
    second = logic.generate_program(random.Random(42))
    assert first == second
    assert first["plan"] in logic.PROGRAM_TEMPLATES[first["program"]]


def test_generate_program_endpoint_updates_client(client):
    client.post("/clients", json={"name": "Ravi", "weight": 70})
    body = client.post("/clients/Ravi/program/generate").get_json()

    assert body["program"] in logic.PROGRAMS
    assert body["plan"] in logic.PROGRAM_TEMPLATES[body["program"]]
    assert body["calories"] == logic.calculate_calories(70, body["program"])
    assert client.get("/clients/Ravi").get_json()["program"] == body["program"]


def test_generate_program_for_unknown_client_returns_404(client):
    assert client.post("/clients/Ghost/program/generate").status_code == 404
