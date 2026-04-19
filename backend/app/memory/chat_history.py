import logging

from pydantic import BaseModel

from app.db.database import get_connection, normalize_user_id
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatTurn(BaseModel):
    user_message: str
    assistant_message: str


class ChatHistoryStore:
    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages
        self._memory_turns: dict[str, list[dict[str, str]]] = {}

    def _should_use_memory(self, session_id: str) -> bool:
        return session_id.startswith(settings.memory_session_prefixes)

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        if self._should_use_memory(session_id):
            return list(self._memory_turns.get(session_id, []))

        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT user_message, assistant_message
                        FROM chat_turns
                        WHERE session_id = %s
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (session_id, self.max_messages),
                    )
                    rows = cursor.fetchall()

            rows = list(reversed(rows))
            return [ChatTurn(**dict(row)).model_dump() for row in rows]
        except Exception as exc:
            logger.warning(
                "chat_history: DB read failed for session=%s, falling back to memory. Error: %s",
                session_id,
                exc,
            )
            return list(self._memory_turns.get(session_id, []))

    def append_turn(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        if self._should_use_memory(session_id):
            turns = self._memory_turns.setdefault(session_id, [])
            turns.append(
                ChatTurn(
                    user_message=user_message,
                    assistant_message=assistant_message,
                ).model_dump()
            )
            if len(turns) > self.max_messages:
                del turns[:-self.max_messages]
            return

        user_id = normalize_user_id(user_id)
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO chat_turns (
                            session_id,
                            user_id,
                            user_message,
                            assistant_message
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (session_id, user_id, user_message, assistant_message),
                    )
        except Exception as exc:
            logger.warning(
                "chat_history: DB write failed for session=%s user=%s, falling back to memory. Error: %s",
                session_id,
                user_id,
                exc,
            )
            turns = self._memory_turns.setdefault(session_id, [])
            turns.append(
                ChatTurn(
                    user_message=user_message,
                    assistant_message=assistant_message,
                ).model_dump()
            )
            if len(turns) > self.max_messages:
                del turns[:-self.max_messages]
