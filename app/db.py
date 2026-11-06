import tomllib
from pathlib import Path

import psycopg

# Database login lives in app/.streamlit/secrets.toml.
# That file is never committed. Copy secrets.toml.example and fill it in.
SECRETS_FILE = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"


def _load_settings():
    """Read the [postgres] section of secrets.toml."""

    if not SECRETS_FILE.exists():
        raise RuntimeError(
            f"Missing {SECRETS_FILE}. "
            "Copy secrets.toml.example to secrets.toml and fill it in."
        )

    with open(SECRETS_FILE, "rb") as file:
        settings = tomllib.load(file).get("postgres", {})

    missing = [
        name for name in ("dbname", "user", "password")
        if not settings.get(name)
    ]

    if missing:
        raise RuntimeError(
            "Missing database settings in secrets.toml: "
            + ", ".join(missing)
        )

    return settings


def get_connection():
    """Create and return a connection to PostgreSQL."""

    settings = _load_settings()

    return psycopg.connect(
        host=settings.get("host", "localhost"),
        port=int(settings.get("port", 5432)),
        dbname=settings["dbname"],
        user=settings["user"],
        password=settings["password"],
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
 