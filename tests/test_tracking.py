"""API tests for progress, workout and body-metric tracking."""
from datetime import date

import pytest


@pytest.fixture(autouse=True)
def meera(client):
    client.post("/clients", json={"name": "Meera"})


# ---------- progress ----------

def test_add_and_list_progress(client):
    resp = client.post("/clients/Meera/progress", json={"week": "W1", "adherence": 80})
    assert resp.status_code == 201
    assert resp.get_json()["adherence"] == 80
    client.post("/clients/Meera/progress", json={"week": "W2", "adherence": 95})

    body = client.get("/clients/Meera/progress").get_json()
    assert [e["week"] for e in body["entries"]] == ["W1", "W2"]
    assert body["average_adherence"] == 87.5


def test_progress_empty_has_no_average(client):
    body = client.get("/clients/Meera/progress").get_json()
    assert body == {"client": "Meera", "entries": [], "average_adherence": None}


@pytest.mark.parametrize("payload", [
    {"week": "W1"},
    {"adherence": 80},
    {"week": "W1", "adherence": 120},
    {"week": "W1", "adherence": -1},
    {"week": "W1", "adherence": "80"},
    {"week": "W1", "adherence": 80, "extra": 1},
])
def test_progress_validation(client, payload):
    assert client.post("/clients/Meera/progress", json=payload).status_code == 400


def test_progress_for_unknown_client_returns_404(client):
    resp = client.post("/clients/Ghost/progress", json={"week": "W1", "adherence": 80})
    assert resp.status_code == 404


# ---------- workouts ----------

def test_add_workout_with_exercises(client):
    resp = client.post("/clients/Meera/workouts", json={
        "date": "2026-03-01",
        "workout_type": "Strength",
        "duration_min": 60,
        "notes": "Felt strong",
        "exercises": [
            {"name": "Back Squat", "sets": 5, "reps": 5, "weight": 60},
            {"name": "Push-ups", "sets": 3, "reps": 15},
        ],
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["date"] == "2026-03-01"
    assert len(body["exercises"]) == 2
    assert body["exercises"][1]["weight"] is None


def test_workout_date_defaults_to_today(client):
    body = client.post("/clients/Meera/workouts", json={
        "workout_type": "Cardio", "duration_min": 30,
    }).get_json()
    assert body["date"] == date.today().isoformat()
    assert body["exercises"] == []


def test_list_workouts_newest_first_with_exercises(client):
    client.post("/clients/Meera/workouts", json={
        "date": "2026-01-01", "workout_type": "Mobility", "duration_min": 20})
    client.post("/clients/Meera/workouts", json={
        "date": "2026-02-01", "workout_type": "Strength", "duration_min": 45,
        "exercises": [{"name": "Deadlift", "sets": 4, "reps": 6, "weight": 80}]})

    workouts = client.get("/clients/Meera/workouts").get_json()["workouts"]
    assert [w["date"] for w in workouts] == ["2026-02-01", "2026-01-01"]
    assert workouts[0]["exercises"][0]["name"] == "Deadlift"


@pytest.mark.parametrize("payload", [
    {"duration_min": 30},                                         # no type
    {"workout_type": "Yoga", "duration_min": 30},                 # unknown type
    {"workout_type": "Cardio"},                                   # no duration
    {"workout_type": "Cardio", "duration_min": 0},
    {"workout_type": "Cardio", "duration_min": 30, "date": "yesterday"},
    {"workout_type": "Cardio", "duration_min": 30, "exercises": "squats"},
    {"workout_type": "Cardio", "duration_min": 30, "exercises": ["squats"]},
    {"workout_type": "Cardio", "duration_min": 30,
     "exercises": [{"name": "Squat", "reps": 5}]},                # no sets
    {"workout_type": "Cardio", "duration_min": 30,
     "exercises": [{"name": "", "sets": 3, "reps": 5}]},          # blank name
])
def test_workout_validation(client, payload):
    assert client.post("/clients/Meera/workouts", json=payload).status_code == 400


def test_invalid_exercise_does_not_save_workout(client):
    client.post("/clients/Meera/workouts", json={
        "workout_type": "Strength", "duration_min": 30,
        "exercises": [{"name": "Squat", "sets": 0, "reps": 5}]})
    assert client.get("/clients/Meera/workouts").get_json()["workouts"] == []


# ---------- metrics ----------

def test_add_and_list_metrics(client):
    resp = client.post("/clients/Meera/metrics", json={
        "date": "2026-01-05", "weight": 62.5, "waist": 70, "bodyfat": 24})
    assert resp.status_code == 201
    client.post("/clients/Meera/metrics", json={"date": "2026-01-01", "weight": 63})

    metrics = client.get("/clients/Meera/metrics").get_json()["metrics"]
    assert [m["date"] for m in metrics] == ["2026-01-01", "2026-01-05"]
    assert metrics[0]["waist"] is None


@pytest.mark.parametrize("payload", [
    {},
    {"date": "2026-01-01"},
    {"bodyfat": 90},
    {"weight": "heavy"},
    {"height": 170},
])
def test_metrics_validation(client, payload):
    assert client.post("/clients/Meera/metrics", json=payload).status_code == 400


# ---------- cascade ----------

def test_deleting_client_removes_tracking_data(client, app):
    client.post("/clients/Meera/progress", json={"week": "W1", "adherence": 80})
    client.post("/clients/Meera/workouts", json={
        "workout_type": "Strength", "duration_min": 30,
        "exercises": [{"name": "Squat", "sets": 3, "reps": 5}]})
    client.post("/clients/Meera/metrics", json={"weight": 60})
    client.delete("/clients/Meera")

    from aceest.db import get_db
    with app.app_context():
        conn = get_db()
        for table in ("progress", "workouts", "exercises", "metrics"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
