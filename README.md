# Car Rental Management System

DBMS course project (Semester 3): a single-branch car rental system with two roles, Customer and Staff/Admin.

**Stack:** PostgreSQL, Python (psycopg), Streamlit.

## Features
- **Customer:** register and log in, browse and filter vehicles, book with an advance payment, view and cancel bookings, manage profile.
- **Staff/Admin:** view active rentals and bookings, confirm pickup, process returns (late and other charges, final payment), manage vehicles and models, change vehicle status, reassign a booking to another vehicle, view vehicle history.

## Setup
1. Create a virtual environment: `python -m venv venv`, then activate it (Windows: `venv\Scripts\activate`).
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `app/.streamlit/secrets.toml.example` to `app/.streamlit/secrets.toml` and fill in your local database details. Never commit `secrets.toml`.
4. Create the database: `createdb car_rental`
5. Load schema and sample data: `psql -d car_rental -f db/schema.sql`, then `psql -d car_rental -f db/seed.sql`
6. Run the app from the project root: `streamlit run app/streamlit_app.py`

To run the report queries: `psql -d car_rental -f db/queries.sql`

## Project structure
- `db/`
  - `schema.sql`: tables and constraints (7 tables)
  - `seed.sql`: sample data
  - `queries.sql`: 7 report queries, each labelled with the RDBMS concept it shows, plus the `booking_summary` view
- `app/`
  - `streamlit_app.py`: landing page
  - `views/`: Streamlit pages (login, registration, booking, profile, staff dashboard)
  - `ui_helpers.py`: shared UI helpers
  - `db.py`: database connection
  - `services.py`: customer and rental functions (booking, pickup, return)
  - `admin_services.py`: staff/admin functions (see `docs/admin_tools.md`)
- `docs/`
  - `er_diagram.png`: ER diagram
  - `car_rental_schema.md`: relational schema and normalization
  - `admin_tools.md`: admin function reference

## RDBMS concepts used
- Primary, foreign and unique keys; NOT NULL, CHECK and DEFAULT constraints
- ER-to-relational mapping and normalization (BCNF)
- Joins, aggregates, GROUP BY / HAVING, subqueries, a view
- Transactions (a booking and its advance payment commit together or not at all)
- Concurrency control with `SELECT ... FOR UPDATE` row locking

## Team
- **Zap:** database and admin tools
- **Pranay:** backend customer and rental functions
- **Akhil:** Streamlit UI

## Team workflow
`main` always runs. Work on a branch (`yourname/task`), pull `main` before starting, and merge through a pull request.