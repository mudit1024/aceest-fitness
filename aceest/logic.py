"""Pure business logic, ported from the legacy Tkinter app.

Nothing in this module touches Flask or the database, so it can be unit
tested directly.
"""
from datetime import date


PROGRAMS = {
    "FL": {
        "code": "FL",
        "name": "Fat Loss",
        "workout": [
            "Mon: Back Squat 5x5 + Core",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: Deadlift + Box Jumps",
            "Fri: Zone 2 Cardio 30min",
        ],
        "diet": [
            "Breakfast: Egg Whites + Oats",
            "Lunch: Grilled Chicken + Brown Rice",
            "Dinner: Fish Curry + Millet Roti",
            "Target: ~2000 kcal",
        ],
        "calorie_factor": 22,
    },
    "MG": {
        "code": "MG",
        "name": "Muscle Gain",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "Breakfast: Eggs + Peanut Butter Oats",
            "Lunch: Chicken Biryani",
            "Dinner: Mutton Curry + Rice",
            "Target: ~3200 kcal",
        ],
        "calorie_factor": 35,
    },
    "BG": {
        "code": "BG",
        "name": "Beginner",
        "workout": [
            "Full Body Circuit: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique & Consistency",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli / Dosa / Rice + Dal",
            "Protein Target: 120g/day",
        ],
        "calorie_factor": 26,
    },
}


def get_program(code):
    """Return the programme for ``code`` (case-insensitive), or None."""
    if not isinstance(code, str):
        return None
    return PROGRAMS.get(code.strip().upper())


def calculate_calories(weight_kg, program_code):
    """Estimate daily calories as body weight (kg) x programme factor."""
    program = get_program(program_code)
    if program is None:
        raise ValueError(f"Unknown program: {program_code!r}")
    if isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float)):
        raise ValueError("weight must be a number")
    if weight_kg <= 0:
        raise ValueError("weight must be greater than 0")
    return int(weight_kg * program["calorie_factor"])


def calculate_bmi(weight_kg, height_cm):
    """Body-mass index rounded to one decimal place."""
    if not weight_kg or not height_cm or weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight and height must both be greater than 0")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def bmi_category(bmi):
    """Return (category, risk note) for a BMI value, as in legacy v2.2.4."""
    if bmi < 18.5:
        return "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return "Normal", "Low risk if active and strong."
    if bmi < 30:
        return "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."


def membership_state(membership_end, today=None):
    """Work out membership status and days remaining from an ISO end date.

    Returns a dict with ``status`` ("Active", "Expired" or "No end date")
    and ``days_remaining`` (None when there is no end date).
    """
    if not membership_end:
        return {"status": "No end date", "days_remaining": None}
    today = today or date.today()
    days = (date.fromisoformat(membership_end) - today).days
    return {
        "status": "Active" if days >= 0 else "Expired",
        "days_remaining": max(days, 0),
    }


WORKOUT_TYPES = ("Strength", "Hypertrophy", "Cardio", "Mobility")


def average_adherence(values):
    """Mean adherence percentage rounded to one decimal, or None if empty."""
    values = list(values)
    if not values:
        return None
    return round(sum(values) / len(values), 1)
