from __future__ import annotations

import json

from app.db.database import get_connection


class NutritionClarificationStore:
    def get(self, session_id: str) -> dict[str, object] | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT session_id, user_id, original_message, payload, updated_at
                FROM nutrition_clarifications
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

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
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO nutrition_clarifications (
                    session_id,
                    user_id,
                    original_message,
                    payload,
                    updated_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    original_message = excluded.original_message,
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session_id, user_id, original_message, encoded_payload),
            )

    def clear(self, session_id: str) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM nutrition_clarifications
                WHERE session_id = ?
                """,
                (session_id,),
            )
