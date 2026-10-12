"""Client management endpoints."""
import sqlite3

from flask import Blueprint, abort, jsonify, url_for

from .db import get_db
from .logic import (
    bmi_category, calculate_bmi, calculate_calories, generate_program, get_program,
    membership_state,
)
from .validation import iso_date, json_body, number, reject_unknown, text

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
    reject_unknown(data, UPDATABLE_FIELDS | ({"name"} if creating else set()))

    clean = {"name": text(data, "name")} if creating else {}
    for field, (kind, low, high) in NUMERIC_FIELDS.items():
        if field in data:
            clean[field] = number(data, field, kind, low, high)

    if "program" in data:
        program = get_program(data["program"])
        if program is None:
            abort(400, description=f"Unknown program: {data['program']!r}")
        clean["program"] = program["code"]

    if "membership_end" in data:
        clean["membership_end"] = iso_date(data, "membership_end")
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
    fields = validate_client(json_body(), creating=False)
    if not fields:
        abort(400, description="No fields to update")
    fields = with_calories(fields, existing)
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


@bp.post("/<name>/program/generate")
def generate_client_program(name):
    """Assign a randomly generated programme and plan to the client."""
    client = find_client(name)
    generated = generate_program()
    fields = with_calories({"program": generated["program"]}, client)
    assignments = ", ".join(f"{col} = ?" for col in fields)
    conn = get_db()
    conn.execute(
        f"UPDATE clients SET {assignments} WHERE id = ?",
        (*fields.values(), client["id"]),
    )
    conn.commit()
    return jsonify(client=name, **generated, calories=fields.get("calories"))
