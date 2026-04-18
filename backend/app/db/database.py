from __future__ import annotations

from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app.core.config import settings

import uuid
import hashlib

def normalize_user_id(user_id: str) -> str:
    try:
        return str(uuid.UUID(user_id))
    except ValueError:
        return str(uuid.UUID(hashlib.md5(user_id.encode("utf-8")).hexdigest()))


@contextmanager
def get_connection():
    connection = psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id UUID PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    avatar_url TEXT,
                    bio TEXT,
                    age INTEGER,
                    sex TEXT,
                    height_cm DOUBLE PRECISION,
                    weight_kg DOUBLE PRECISION,
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
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_turns (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
                    user_message TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_turns_session_id
                ON chat_turns(session_id, id DESC)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS nutrition_clarifications (
                    session_id TEXT PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
                    original_message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("SELECT 1")
