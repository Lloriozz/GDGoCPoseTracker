import json
from hashlib import sha256

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
        email, username = self._build_placeholder_identity(user_id)

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_profiles (
                        id,
                        email,
                        username,
                        password_hash,
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
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        age = EXCLUDED.age,
                        sex = EXCLUDED.sex,
                        height_cm = EXCLUDED.height_cm,
                        weight_kg = EXCLUDED.weight_kg,
                        goal = EXCLUDED.goal,
                        activity_level = EXCLUDED.activity_level,
                        workout_days_per_week = EXCLUDED.workout_days_per_week,
                        train_location = EXCLUDED.train_location,
                        experience_level = EXCLUDED.experience_level,
                        budget_level = EXCLUDED.budget_level,
                        cook_time_preference = EXCLUDED.cook_time_preference,
                        goal_detail = EXCLUDED.goal_detail,
                        injuries = EXCLUDED.injuries,
                        diet_preferences = EXCLUDED.diet_preferences,
                        allergies = EXCLUDED.allergies,
                        preferred_foods = EXCLUDED.preferred_foods,
                        disliked_foods = EXCLUDED.disliked_foods,
                        updated_at = NOW()
                    """,
                    (
                        user_id,
                        email,
                        username,
                        "__chatbot_only__",
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

    def _build_placeholder_identity(self, user_id: str) -> tuple[str, str]:
        digest = sha256(user_id.encode("utf-8")).hexdigest()[:24]
        return (
            f"chatbot+{digest}@local.invalid",
            f"chatbot_{digest}",
        )
