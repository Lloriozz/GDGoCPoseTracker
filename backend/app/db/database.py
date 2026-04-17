from __future__ import annotations

from contextlib import contextmanager
import re

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from app.core.config import settings


_SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _get_database_schema() -> str:
    schema_name = (settings.database_schema or "public").strip()
    if not _SCHEMA_NAME_PATTERN.fullmatch(schema_name):
        raise ValueError(
            "DATABASE_SCHEMA must start with a letter or underscore and contain only letters, digits, or underscores."
        )
    return schema_name


def _connect_raw():
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _apply_search_path(connection) -> None:
    schema_name = _get_database_schema()
    with connection.cursor() as cursor:
        if schema_name != "public":
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name))
            )
        cursor.execute(
            sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name))
        )


@contextmanager
def get_connection():
    connection = _connect_raw()
    try:
        _apply_search_path(connection)
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
                    id TEXT PRIMARY KEY,
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
                    user_id TEXT NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
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
                    user_id TEXT NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
                    original_message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("SELECT 1")


def drop_schema(schema_name: str | None = None) -> None:
    active_schema = schema_name or _get_database_schema()
    if active_schema == "public":
        raise ValueError("Refusing to drop the public schema.")
    if not _SCHEMA_NAME_PATTERN.fullmatch(active_schema):
        raise ValueError(
            "Schema names must start with a letter or underscore and contain only letters, digits, or underscores."
        )

    connection = _connect_raw()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(active_schema))
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
