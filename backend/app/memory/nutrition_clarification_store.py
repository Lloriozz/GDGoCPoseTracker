from __future__ import annotations

import json

from app.db.database import get_connection, normalize_user_id


class NutritionClarificationStore:
    def get(self, session_id: str) -> dict[str, object] | None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_id, user_id, original_message, payload, updated_at
                    FROM nutrition_clarifications
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        payload = json.loads(row["payload"] or "{}")
        payload["session_id"] = row["session_id"]
        payload["user_id"] = row["user_id"]
        payload["original_message"] = row["original_message"]
        payload["updated_at"] = row["updated_at"]
        return payload

    def set(
        self,
        session_id: str,
        user_id: str,
        original_message: str,
        payload: dict[str, object],
    ) -> None:
        user_id = normalize_user_id(user_id)
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO nutrition_clarifications (
                        session_id,
                        user_id,
                        original_message,
                        payload,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        original_message = EXCLUDED.original_message,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (session_id, user_id, original_message, encoded_payload),
                )

    def clear(self, session_id: str) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM nutrition_clarifications
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
