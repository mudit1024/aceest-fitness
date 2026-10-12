"""Request validation helpers shared by the API blueprints.

Each helper aborts with HTTP 400 and a readable message on invalid input.
"""
from datetime import date

from flask import abort, request


def json_body():
    """Return the request's JSON object, or abort if it is not one."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Request body must be a JSON object")
    return data


def reject_unknown(data, allowed):
    unknown = set(data) - set(allowed)
    if unknown:
        abort(400, description=f"Unknown field(s): {', '.join(sorted(unknown))}")


def number(data, field, kind, low, high):
    """Validate ``data[field]`` as an int (``kind is int``) or float in range."""
    value = data[field]
    accepted = (int,) if kind is int else (int, float)
    if isinstance(value, bool) or not isinstance(value, accepted):
        expected = "an integer" if kind is int else "a number"
        abort(400, description=f"'{field}' must be {expected}")
    if not low <= value <= high:
        abort(400, description=f"'{field}' must be between {low} and {high}")
    return value


def text(data, field, required=True):
    value = data.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        abort(400, description=f"'{field}' is required")
    return value.strip()


def iso_date(data, field, default=None):
    """Validate an ISO ``YYYY-MM-DD`` date; fall back to ``default`` if absent."""
    if field not in data:
        return default
    try:
        return date.fromisoformat(str(data[field])).isoformat()
    except ValueError:
        abort(400, description=f"'{field}' must be a date in YYYY-MM-DD format")
