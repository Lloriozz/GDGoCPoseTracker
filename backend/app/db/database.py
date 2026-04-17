from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from app.core.config import settings


@contextmanager
def get_connection():
    """Yield a psycopg2 connection to the shared PostgreSQL database.

    Tables are created and managed by Prisma (``prisma migrate dev``).
    This context manager is used exclusively by the Python chatbot to
    read and write rows via raw SQL.
    """
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
    """Verify the PostgreSQL connection on startup.

    Schema is owned by Prisma — no DDL is executed here.
    Run ``npx prisma migrate dev`` (in the backend directory) to
    create or update tables before starting the chatbot.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
