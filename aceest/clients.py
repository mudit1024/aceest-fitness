"""Client management endpoints."""
import sqlite3
from datetime import date

from flask import Blueprint, abort, jsonify, request, url_for

from .db import get_db
from .logic import (
    bmi_category, calculate_bmi, calculate_calories, get_program,
    membership_state,
)

bp = Blueprint("clients", __name__, url_prefix="/clients")

# field -> (type, min, max)
NUMERIC_FIELDS = {
    "age": (int, 1, 120),
    "height": (float, 50, 250),          # cm
    "weight": (float, 20, 400),          # kg
    "target_weight": (float, 20, 400),   # kg
    "target_adherence": (int, 0, 100),   # %
}
UPDATABLE_FIELDS = set(NUMERIC_FIELDS) | {"program", "membership_end"}


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Request body must be a JSON object")
    return data


def find_client(name):
    """Return the client row for ``name`` or abort with 404."""
    row = get_db().execute(
        "SELECT * FROM clients WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        abort(404, description=f"Client '{name}' not found")
    return row


def validate_client(data, creating):
    """Validate a create/update payload and return the cleaned fields."""
    allowed = UPDATABLE_FIELDS | ({"name"} if creating else set())
    unknown = set(data) - allowed
    if unknown:
        abort(400, description=f"Unknown field(s): {', '.join(sorted(unknown))}")

    clean = {}
    if creating:
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            abort(400, description="'name' is required")
        clean["name"] = name.strip()

    for field, (kind, low, high) in NUMERIC_FIELDS.items():
        if field not in data:
            continue
        value = data[field]
        numeric = (int,) if kind is int else (int, float)
        if isinstance(value, bool) or not isinstance(value, numeric):
            abort(400, description=f"'{field}' must be {'an integer' if kind is int else 'a number'}")
        if not low <= value <= high:
            abort(400, description=f"'{field}' must be between {low} and {high}")
        clean[field] = value

    if "program" in data:
        program = get_program(data["program"])
        if program is None:
            abort(400, description=f"Unknown program: {data['program']!r}")
        clean["program"] = program["code"]

    if "membership_end" in data:
        try:
            clean["membership_end"] = date.fromisoformat(str(data["membership_end"])).isoformat()
        except ValueError:
            abort(400, description="'membership_end' must be a date in YYYY-MM-DD format")

    return clean


def with_calories(fields, existing=None):
    """Recalculate calories whenever weight and programme are both known."""
    merged = {**(dict(existing) if existing else {}), **fields}
    if merged.get("weight") and merged.get("program"):
        fields["calories"] = calculate_calories(merged["weight"], merged["program"])
    return fields


def serialize(row):
    return dict(row)


@bp.get("")
def list_clients():
    rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
    return jsonify(clients=[serialize(r) for r in rows])


@bp.post("")
def create_client():
    fields = with_calories(validate_client(json_body(), creating=True))
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    conn = get_db()
    try:
        conn.execute(
            f"INSERT INTO clients ({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        abort(409, description=f"Client '{fields['name']}' already exists")
    row = find_client(fields["name"])
    resp = jsonify(serialize(row))
    resp.status_code = 201
    resp.headers["Location"] = url_for(".get_client", name=fields["name"])
    return resp


@bp.get("/<name>")
def get_client(name):
    return jsonify(serialize(find_client(name)))


@bp.route("/<name>", methods=["PUT", "PATCH"])
def update_client(name):
    existing = find_client(name)
    fields = with_calories(validate_client(json_body(), creating=False), existing)
    if not fields:
        abort(400, description="No fields to update")
    assignments = ", ".join(f"{col} = ?" for col in fields)
    conn = get_db()
    conn.execute(
        f"UPDATE clients SET {assignments} WHERE id = ?",
        (*fields.values(), existing["id"]),
    )
    conn.commit()
    return jsonify(serialize(find_client(name)))


@bp.delete("/<name>")
def delete_client(name):
    client = find_client(name)
    conn = get_db()
    conn.execute("DELETE FROM clients WHERE id = ?", (client["id"],))
    conn.commit()
    return jsonify(deleted=name)


@bp.get("/<name>/bmi")
def client_bmi(name):
    client = find_client(name)
    if not client["weight"] or not client["height"]:
        abort(422, description="Client needs both weight and height to calculate BMI")
    bmi = calculate_bmi(client["weight"], client["height"])
    category, risk = bmi_category(bmi)
    return jsonify(client=name, bmi=bmi, category=category, risk=risk)


@bp.get("/<name>/membership")
def client_membership(name):
    client = find_client(name)
    state = membership_state(client["membership_end"])
    return jsonify(client=name, membership_end=client["membership_end"], **state)
