from app.schemas.user_profile import UserProfile


def calculate_tdee(profile: UserProfile) -> dict[str, float]:
    if None in (profile.age, profile.height_cm, profile.weight_kg, profile.sex, profile.activity_level):
        return {}

    weight = float(profile.weight_kg)
    height = float(profile.height_cm)
    age = int(profile.age)

    if profile.sex == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    multipliers = {
        "low": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "high": 1.725,
    }
    tdee = bmr * multipliers[profile.activity_level]
    return {
        "estimated_bmr": round(bmr, 2),
        "estimated_tdee": round(tdee, 2),
    }
