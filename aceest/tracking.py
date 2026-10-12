"""Progress, workout and body-metric tracking endpoints (port of v3.x)."""
from datetime import date

from flask import Blueprint, abort, jsonify

from .clients import find_client
from .db import get_db
from .logic import WORKOUT_TYPES, average_adherence
from .validation import iso_date, json_body, number, reject_unknown, text

bp = Blueprint("tracking", __name__, url_prefix="/clients/<name>")


def created(payload):
    return jsonify(payload), 201


# ---------- Weekly adherence ----------

@bp.get("/progress")
def list_progress(name):
    client = find_client(name)
    rows = get_db().execute(
        "SELECT id, week, adherence FROM progress WHERE client_id = ? ORDER BY id",
        (client["id"],),
    ).fetchall()
    entries = [dict(r) for r in rows]
    return jsonify(
        client=name,
        entries=entries,
        average_adherence=average_adherence(e["adherence"] for e in entries),
    )


@bp.post("/progress")
def add_progress(name):
    client = find_client(name)
    data = json_body()
    reject_unknown(data, {"week", "adherence"})
    if "adherence" not in data:
        abort(400, description="'adherence' is required")
    entry = {
        "week": text(data, "week"),
        "adherence": number(data, "adherence", int, 0, 100),
    }
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO progress (client_id, week, adherence) VALUES (?, ?, ?)",
        (client["id"], entry["week"], entry["adherence"]),
    )
    conn.commit()
    return created({"id": cur.lastrowid, "client": name, **entry})


# ---------- Workouts & exercises ----------

def validate_exercise(item, index):
    if not isinstance(item, dict):
        abort(400, description=f"exercises[{index}] must be an object")
    reject_unknown(item, {"name", "sets", "reps", "weight"})
    for field in ("sets", "reps"):
        if field not in item:
            abort(400, description=f"exercises[{index}].{field} is required")
    return {
        "name": text(item, "name"),
        "sets": number(item, "sets", int, 1, 100),
        "reps": number(item, "reps", int, 1, 1000),
        "weight": number(item, "weight", float, 0, 1000) if "weight" in item else None,
    }


@bp.get("/workouts")
def list_workouts(name):
    client = find_client(name)
    conn = get_db()
    workouts = [dict(w) for w in conn.execute(
        "SELECT id, date, workout_type, duration_min, notes FROM workouts "
        "WHERE client_id = ? ORDER BY date DESC, id DESC",
        (client["id"],),
    ).fetchall()]
    for workout in workouts:
        workout["exercises"] = [dict(e) for e in conn.execute(
            "SELECT name, sets, reps, weight FROM exercises WHERE workout_id = ? ORDER BY id",
            (workout["id"],),
        ).fetchall()]
    return jsonify(client=name, workouts=workouts)


@bp.post("/workouts")
def add_workout(name):
    client = find_client(name)
    data = json_body()
    reject_unknown(data, {"date", "workout_type", "duration_min", "notes", "exercises"})

    workout_type = text(data, "workout_type")
    if workout_type not in WORKOUT_TYPES:
        abort(400, description=f"'workout_type' must be one of: {', '.join(WORKOUT_TYPES)}")
    if "duration_min" not in data:
        abort(400, description="'duration_min' is required")
    exercises = data.get("exercises", [])
    if not isinstance(exercises, list):
        abort(400, description="'exercises' must be a list")

    workout = {
        "date": iso_date(data, "date", default=date.today().isoformat()),
        "workout_type": workout_type,
        "duration_min": number(data, "duration_min", int, 1, 600),
        "notes": text(data, "notes", required=False),
        "exercises": [validate_exercise(e, i) for i, e in enumerate(exercises)],
    }

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO workouts (client_id, date, workout_type, duration_min, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (client["id"], workout["date"], workout_type,
         workout["duration_min"], workout["notes"]),
    )
    conn.executemany(
        "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
        [(cur.lastrowid, e["name"], e["sets"], e["reps"], e["weight"])
         for e in workout["exercises"]],
    )
    conn.commit()
    return created({"id": cur.lastrowid, "client": name, **workout})


# ---------- Body metrics ----------

METRIC_RANGES = {
    "weight": (20, 400),    # kg
    "waist": (30, 250),     # cm
    "bodyfat": (2, 70),     # %
}


@bp.get("/metrics")
def list_metrics(name):
    client = find_client(name)
    rows = get_db().execute(
        "SELECT id, date, weight, waist, bodyfat FROM metrics "
        "WHERE client_id = ? ORDER BY date, id",
        (client["id"],),
    ).fetchall()
    return jsonify(client=name, metrics=[dict(r) for r in rows])


@bp.post("/metrics")
def add_metric(name):
    client = find_client(name)
    data = json_body()
    reject_unknown(data, {"date", *METRIC_RANGES})
    values = {
        field: number(data, field, float, low, high) if field in data else None
        for field, (low, high) in METRIC_RANGES.items()
    }
    if all(v is None for v in values.values()):
        abort(400, description="Provide at least one of: weight, waist, bodyfat")
    entry = {"date": iso_date(data, "date", default=date.today().isoformat()), **values}
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO metrics (client_id, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)",
        (client["id"], entry["date"], entry["weight"], entry["waist"], entry["bodyfat"]),
    )
    conn.commit()
    return created({"id": cur.lastrowid, "client": name, **entry})
