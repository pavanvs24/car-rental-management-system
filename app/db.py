import psycopg as pg
from psycopg_pool import ConnectionPool
import streamlit as st

@st.cache_resource
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

    return ConnectionPool(kwargs = st.secrets["postgres"], min_size = 1, max_size = 10)

ConnPool = get_connection()

def test_connection():
    #Verify the database connection.

    try:
        with ConnPool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), current_user;"
                )
                fetchvalue = cursor.fetchone()
                if fetchvalue is not None:
                    database_name, user_name = fetchvalue
                else:
                    raise ValueError("DB did not return records!")

        print(f"Connected to database: {database_name}")
        print(f"Connected as user: {user_name}")
        return True

    except (pg.Error, RuntimeError, ValueError) as error:
        print(f"Database connection failed: {error}!")
        return False




 