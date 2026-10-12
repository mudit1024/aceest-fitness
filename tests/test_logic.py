"""Unit tests for the pure business logic in aceest.logic."""
from datetime import date

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


@pytest.mark.parametrize("weight,height,expected", [
    (80, 175, 26.1),
    (50, 180, 15.4),
    (70, 170, 24.2),
])
def test_calculate_bmi(weight, height, expected):
    assert logic.calculate_bmi(weight, height) == expected


@pytest.mark.parametrize("weight,height", [(0, 170), (70, 0), (None, 170)])
def test_calculate_bmi_rejects_missing_values(weight, height):
    with pytest.raises(ValueError):
        logic.calculate_bmi(weight, height)


@pytest.mark.parametrize("bmi,category", [
    (18.4, "Underweight"),
    (18.5, "Normal"),
    (24.9, "Normal"),
    (25.0, "Overweight"),
    (29.9, "Overweight"),
    (30.0, "Obese"),
])
def test_bmi_category_boundaries(bmi, category):
    assert logic.bmi_category(bmi)[0] == category


def test_membership_state():
    today = date(2026, 1, 10)
    assert logic.membership_state("2026-01-20", today) == {
        "status": "Active", "days_remaining": 10}
    assert logic.membership_state("2026-01-10", today)["status"] == "Active"
    assert logic.membership_state("2026-01-09", today) == {
        "status": "Expired", "days_remaining": 0}
    assert logic.membership_state(None, today)["status"] == "No end date"


def test_average_adherence():
    assert logic.average_adherence([80, 90, 100]) == 90.0
    assert logic.average_adherence([]) is None
    assert logic.average_adherence(iter([33, 34])) == 33.5
