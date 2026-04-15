from app.schemas.user_profile import UserProfile
from app.tools.tdee import calculate_tdee


CALORIE_ADJUSTMENTS = {
    "fat_loss": -400,
    "maintenance": 0,
    "muscle_gain": 250,
    "recomp": -100,
}


def calculate_macros(profile: UserProfile) -> dict[str, object]:
    tdee_result = calculate_tdee(profile)
    if not tdee_result or profile.goal is None or profile.weight_kg is None:
        return {}

    goal = profile.goal
    weight_kg = float(profile.weight_kg)
    estimated_tdee = float(tdee_result["estimated_tdee"])
    calorie_adjustment = CALORIE_ADJUSTMENTS[goal]
    target_calories = round(estimated_tdee + calorie_adjustment)

    protein_g = round(weight_kg * 2.0)
    fat_multiplier = 0.8 if goal == "fat_loss" else 1.0
    fat_g = round(weight_kg * fat_multiplier)

    calories_after_protein_and_fat = target_calories - protein_g * 4 - fat_g * 9
    carb_g = max(round(calories_after_protein_and_fat / 4), 0)

    return {
        "goal": goal,
        "estimated_bmr": tdee_result["estimated_bmr"],
        "estimated_tdee": tdee_result["estimated_tdee"],
        "target_calories": target_calories,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carb_g": carb_g,
        "calorie_adjustment": calorie_adjustment,
        "notes": [
            "Protein set at 2.0 g/kg body weight",
            f"Fat set at {fat_multiplier:.1f} g/kg body weight",
            "Carbs fill the remaining calories",
        ],
    }
