import os
import streamlit as st
import psycopg


def get_connection():
    """Create and return a connection to PostgreSQL."""

    required_settings = ["dbname", "user", "password"]
    missing_settings = [
        name for name in required_settings if name not in st.secrets.get('postgres', {})
    ]

    if missing_settings:
        raise RuntimeError(
            "Missing database settings: "
            + ", ".join(missing_settings)
        )

    return psycopg.connect(kwargs = st.secrets["postgres"])


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
