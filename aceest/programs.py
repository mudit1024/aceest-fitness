"""Programme catalogue and calorie calculator endpoints."""
from flask import Blueprint, abort, jsonify, request

from .logic import PROGRAMS, calculate_calories, get_program

bp = Blueprint("programs", __name__)


@bp.get("/programs")
def list_programs():
    return jsonify(programs=list(PROGRAMS.values()))


@bp.get("/programs/<code>")
def program_detail(code):
    program = get_program(code)
    if program is None:
        abort(404, description=f"Program '{code}' not found")
    return jsonify(program)


@bp.post("/calories")
def calories():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Request body must be a JSON object")
    try:
        kcal = calculate_calories(data.get("weight"), data.get("program"))
    except ValueError as exc:
        abort(400, description=str(exc))
    return jsonify(
        weight=data["weight"],
        program=data["program"].upper(),
        calories=kcal,
    )
