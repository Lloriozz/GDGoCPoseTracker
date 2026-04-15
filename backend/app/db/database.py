from contextlib import contextmanager
from pathlib import Path
import sqlite3

from app.core.config import settings


def get_database_path() -> Path:
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@contextmanager
def get_connection():
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=MEMORY")
    connection.execute("PRAGMA synchronous=NORMAL")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                age INTEGER,
                sex TEXT,
                height_cm REAL,
                weight_kg REAL,
                goal TEXT,
                activity_level TEXT,
                workout_days_per_week INTEGER,
                train_location TEXT,
                experience_level TEXT,
                budget_level TEXT,
                cook_time_preference TEXT,
                goal_detail TEXT,
                injuries TEXT NOT NULL DEFAULT '[]',
                diet_preferences TEXT NOT NULL DEFAULT '[]',
                allergies TEXT NOT NULL DEFAULT '[]',
                preferred_foods TEXT NOT NULL DEFAULT '[]',
                disliked_foods TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_chat_turns_session_id
            ON chat_turns(session_id, id DESC);

            CREATE TABLE IF NOT EXISTS nutrition_clarifications (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                original_message TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _ensure_user_profile_columns(connection)


def _ensure_user_profile_columns(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(user_profiles)").fetchall()
    }
    required_columns = {
        "experience_level": "TEXT",
        "budget_level": "TEXT",
        "cook_time_preference": "TEXT",
        "goal_detail": "TEXT",
        "preferred_foods": "TEXT NOT NULL DEFAULT '[]'",
        "disliked_foods": "TEXT NOT NULL DEFAULT '[]'",
    }
    for column_name, column_sql in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE user_profiles ADD COLUMN {column_name} {column_sql}"
            )
