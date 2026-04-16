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
            row = connection.execute(
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
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

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
            connection.execute(
                """
                INSERT INTO user_profiles (
                    user_id,
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
                    disliked_foods,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    age = excluded.age,
                    sex = excluded.sex,
                    height_cm = excluded.height_cm,
                    weight_kg = excluded.weight_kg,
                    goal = excluded.goal,
                    activity_level = excluded.activity_level,
                    workout_days_per_week = excluded.workout_days_per_week,
                    train_location = excluded.train_location,
                    experience_level = excluded.experience_level,
                    budget_level = excluded.budget_level,
                    cook_time_preference = excluded.cook_time_preference,
                    goal_detail = excluded.goal_detail,
                    injuries = excluded.injuries,
                    diet_preferences = excluded.diet_preferences,
                    allergies = excluded.allergies,
                    preferred_foods = excluded.preferred_foods,
                    disliked_foods = excluded.disliked_foods,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
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
                ),
            )
        return merged
