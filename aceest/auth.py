"""Authentication endpoint (port of the v3.x login screen)."""
from flask import Blueprint, abort, jsonify
from werkzeug.security import check_password_hash

from .db import get_db
from .validation import json_body, text

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    data = json_body()
    username = text(data, "username")
    password = text(data, "password")
    user = get_db().execute(
        "SELECT username, password_hash, role FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        abort(401, description="Invalid username or password")
    return jsonify(username=user["username"], role=user["role"])
