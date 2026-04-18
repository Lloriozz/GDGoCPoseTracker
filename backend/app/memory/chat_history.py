from pydantic import BaseModel

from app.db.database import get_connection, normalize_user_id


class ChatTurn(BaseModel):
    user_message: str
    assistant_message: str


class ChatHistoryStore:
    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
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

    def append_turn(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        user_id = normalize_user_id(user_id)
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
