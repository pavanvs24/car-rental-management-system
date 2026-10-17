
import os

import psycopg
from dotenv import load_dotenv

# Load database settings from the project's .env file.
load_dotenv()


def get_connection():
    """Create and return a connection to PostgreSQL."""

    required_settings = ["DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing_settings = [
        name for name in required_settings
        if not os.getenv(name)
    ]

    if missing_settings:
        raise RuntimeError(
            "Missing database settings: "
            + ", ".join(missing_settings)
        )

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )


def test_connection():
    """Verify the database connection."""

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), current_user;"
                )
                database_name, user_name = cursor.fetchone()

        print(f"Connected to database: {database_name}")
        print(f"Connected as user: {user_name}")
        return True

    except (psycopg.Error, RuntimeError, ValueError) as error:
        print(f"Database connection failed: {error}")
        return False


if __name__ == "__main__":
    test_connection()
