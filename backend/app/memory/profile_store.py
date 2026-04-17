import json

from app.db.database import get_connection
from app.schemas.user_profile import UserProfile, UserProfilePatch


class ProfileStore:
    def __init__(self) -> None:
        self._list_fields = (
            "injuries",
            "diet_preferences",
            "allergies",
            "preferred_foods",
            "disliked_foods",
        )

    def get(self, user_id: str) -> UserProfile:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        age,
                        sex,
                        height_cm,
                        weight_kg,
                        goal,
                        activity_level,
                        workout_days_per_week,
                        train_location,
                        experience_level,
                        budget_level,
                        cook_time_preference,
                        goal_detail,
                        injuries,
                        diet_preferences,
                        allergies,
                        preferred_foods,
                        disliked_foods
                    FROM user_profiles
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()


        if row is None:
            return UserProfile()

        payload = dict(row)
        for field_name in self._list_fields:
            payload[field_name] = json.loads(payload[field_name] or "[]")
        return UserProfile(**payload)

    def upsert_from_patch(self, user_id: str, patch: UserProfilePatch | None) -> UserProfile:
        current = self.get(user_id)
        if patch is None:
            return current

        merged = current.model_copy(update=patch.model_dump(exclude_none=True))
        payload = merged.model_dump()
        for field_name in self._list_fields:
            payload[field_name] = json.dumps(payload[field_name], ensure_ascii=False)

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE user_profiles SET
                        age = %s,
                        sex = %s,
                        height_cm = %s,
                        weight_kg = %s,
                        goal = %s,
                        activity_level = %s,
                        workout_days_per_week = %s,
                        train_location = %s,
                        experience_level = %s,
                        budget_level = %s,
                        cook_time_preference = %s,
                        goal_detail = %s,
                        injuries = %s,
                        diet_preferences = %s,
                        allergies = %s,
                        preferred_foods = %s,
                        disliked_foods = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        payload["age"],
                        payload["sex"],
                        payload["height_cm"],
                        payload["weight_kg"],
                        payload["goal"],
                        payload["activity_level"],
                        payload["workout_days_per_week"],
                        payload["train_location"],
                        payload["experience_level"],
                        payload["budget_level"],
                        payload["cook_time_preference"],
                        payload["goal_detail"],
                        payload["injuries"],
                        payload["diet_preferences"],
                        payload["allergies"],
                        payload["preferred_foods"],
                        payload["disliked_foods"],
                        user_id,
                    ),
                )
        return merged
