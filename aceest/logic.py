"""Pure business logic, ported from the legacy Tkinter app.

Nothing in this module touches Flask or the database, so it can be unit
tested directly.
"""

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
