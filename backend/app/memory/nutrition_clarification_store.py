from __future__ import annotations

import json
import logging

from app.db.database import get_connection, normalize_user_id
from app.core.config import settings

logger = logging.getLogger(__name__)


class NutritionClarificationStore:
    def __init__(self) -> None:
        self._memory_payloads: dict[str, dict[str, object]] = {}

    def _should_use_memory(self, session_id: str) -> bool:
        return session_id.startswith(settings.memory_session_prefixes)

    def get(self, session_id: str) -> dict[str, object] | None:
        if self._should_use_memory(session_id):
            return self._memory_payloads.get(session_id)

        try:
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
        except Exception as exc:
            logger.warning(
                "nutrition_clarification_store: DB read failed for session=%s, falling back to memory. Error: %s",
                session_id,
                exc,
            )
            return self._memory_payloads.get(session_id)

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
        if self._should_use_memory(session_id):
            self._memory_payloads[session_id] = {
                **payload,
                "session_id": session_id,
                "user_id": user_id,
                "original_message": original_message,
            }
            return

        user_id = normalize_user_id(user_id)
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        try:
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
        except Exception as exc:
            logger.warning(
                "nutrition_clarification_store: DB write failed for session=%s, falling back to memory. Error: %s",
                session_id,
                exc,
            )
            self._memory_payloads[session_id] = {
                **payload,
                "session_id": session_id,
                "user_id": user_id,
                "original_message": original_message,
            }

    def clear(self, session_id: str) -> None:
        self._memory_payloads.pop(session_id, None)
        if self._should_use_memory(session_id):
            return

        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM nutrition_clarifications
                        WHERE session_id = %s
                        """,
                        (session_id,),
                    )
        except Exception as exc:
            logger.warning(
                "nutrition_clarification_store: DB delete failed for session=%s. Error: %s",
                session_id,
                exc,
            )
            return
