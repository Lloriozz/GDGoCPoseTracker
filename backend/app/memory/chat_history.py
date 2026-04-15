from pydantic import BaseModel

from app.db.database import get_connection


class ChatTurn(BaseModel):
    user_message: str
    assistant_message: str


class ChatHistoryStore:
    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT user_message, assistant_message
                FROM chat_turns
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, self.max_messages),
            ).fetchall()

        rows = list(reversed(rows))
        return [ChatTurn(**dict(row)).model_dump() for row in rows]

    def append_turn(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO chat_turns (
                    session_id,
                    user_id,
                    user_message,
                    assistant_message
                )
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, user_message, assistant_message),
            )
