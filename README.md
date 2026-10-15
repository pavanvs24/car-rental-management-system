# Car Rental Platform

DBMS course project: PostgreSQL + Python (psycopg) + Streamlit.

## Setup
1. Create a virtual environment: `python -m venv venv`, then activate it (Windows: `venv\Scripts\activate`).
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your local database details.
4. Create the database: `createdb car_rental`
5. Load schema and sample data:
   `psql -d car_rental -f db/schema.sql`
   `psql -d car_rental -f db/seed.sql`
6. Run the app: `streamlit run app/streamlit_app.py`

## Structure
- `db/`: schema, seed data, queries
- `app/db.py`, `app/services.py`: database connection and Python functions
- `app/streamlit_app.py`, `app/pages/`: UI
- `docs/`: schema reference

## Team workflow
- `main` always runs. Work on a branch (`yourname/task`), pull `main` before starting, merge through a pull request.
