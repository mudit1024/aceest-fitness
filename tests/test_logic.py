"""Unit tests for the pure business logic in aceest.logic."""
import pytest

from aceest import logic


@pytest.mark.parametrize("code", ["FL", "fl", " mg ", "Bg"])
def test_get_program_is_case_insensitive(code):
    assert logic.get_program(code)["code"] == code.strip().upper()


@pytest.mark.parametrize("code", ["XX", "", None, 42])
def test_get_program_unknown_returns_none(code):
    assert logic.get_program(code) is None


@pytest.mark.parametrize("weight,code,expected", [
    (70, "FL", 1540),     # 70 x 22
    (80, "MG", 2800),     # 80 x 35
    (60.5, "BG", 1573),   # 60.5 x 26 = 1573.0
    (72.9, "FL", 1603),   # truncated, matching the legacy int() behaviour
])
def test_calculate_calories(weight, code, expected):
    assert logic.calculate_calories(weight, code) == expected


@pytest.mark.parametrize("weight", [0, -5, "70", None, True])
def test_calculate_calories_rejects_bad_weight(weight):
    with pytest.raises(ValueError):
        logic.calculate_calories(weight, "FL")


def test_calculate_calories_rejects_unknown_program():
    with pytest.raises(ValueError, match="Unknown program"):
        logic.calculate_calories(70, "ZZ")


def test_every_program_has_required_fields():
    for code, program in logic.PROGRAMS.items():
        assert program["code"] == code
        assert program["workout"] and program["diet"]
        assert program["calorie_factor"] > 0
