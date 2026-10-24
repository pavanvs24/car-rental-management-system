import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, cast
from typing_extensions import LiteralString
from db import ConnPool
import streamlit as st

#===============================DATA RETRIEVAL=============================

def GetPassHash(select, identifier):
    with ConnPool.connection() as conn:
        with conn.cursor() as cur:
            if select == "staff":

                try:
                    int(identifier)

                except ValueError:
                    return None
                
                cur.execute("SELECT password_hash FROM staff WHERE staff_id = %s;", (int(identifier),))
                hash = cur.fetchone()

                return hash[0] if hash else None
            
            if select == "customer":

                cur.execute("SELECT password_hash FROM customer WHERE email = %s;", (identifier,))
                hash = cur.fetchone()

                return hash[0] if hash else None

#-----------------------------------------------------------

@st.cache_data(ttl=dt.timedelta(minutes=30))
def Get_Filter_Options() -> dict[str,Any]:

    query = f"""
                SELECT DISTINCT 'brand' AS col, brand::text AS val FROM vehicle_model WHERE brand IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'fuel_type', fuel_type::text FROM vehicle_model WHERE fuel_type IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'transmission', transmission::text FROM vehicle_model WHERE transmission IS NOT NULL
                UNION ALL
                SELECT DISTINCT 'seats', seats::text FROM vehicle_model WHERE seats IS NOT NULL
                UNION ALL
                SELECT 'min_rate', MIN(daily_rate)::text FROM vehicle_model
                UNION ALL
                SELECT 'max_rate', MAX(daily_rate)::text FROM vehicle_model;
            """

    filter_options = {}

    with ConnPool.connection() as conn:
        with conn.cursor() as cur:

            safe_query = cast(LiteralString, query)
            
            cur.execute(safe_query)
    
            for col, val in cur.fetchall():

                if col in ("seats", "min_rate", "max_rate"):

                    filter_options.setdefault(col, []).append(int(val))

                else:

                    filter_options.setdefault(col, []).append(val)

                filter_options[col].sort()

    return filter_options

def get_models(brand_names: list[str]) -> list[str]:

    query = f"SELECT DISTINCT model_name FROM vehicle_model WHERE brand = ANY(%s)"

    with ConnPool.connection() as conn:
        with conn.cursor() as cur:
            safe_query = cast(LiteralString, query)

            cur.execute(safe_query, (brand_names,))

            rows = cur.fetchall() or []

    return [row[0] for row in rows]
#-----------------------------------------------------------

@st.cache_data(ttl=dt.timedelta(minutes=5))
def search_available_vehicles(
    start_date: dt.date,
    end_date: dt.date,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Return vehicles available throughout the requested date range.

    Optional filters:

        seating_capacity
        brand
        model_name
        fuel_type
        transmission
        min_daily_rate
        max_daily_rate

    Text filters for brand and model_name use partial,
    case-insensitive matching.

    Fuel type and transmission use case-insensitive input
    normalization followed by exact matching.
    """

    # 1. Validate the requested dates.
    if start_date > end_date:
        raise ValueError("End date must be on or after start date.")

    # 2. Require available vehicles and exclude overlapping
    # confirmed bookings.
    conditions = [
        "v.status = 'AVAILABLE'",
        """
        NOT EXISTS (
            SELECT 1
            FROM booking AS b
            WHERE b.vehicle_id = v.vehicle_id
              AND b.status = 'CONFIRMED'
              AND b.start_date <= %s
              AND b.end_date >= %s
        )
        """,
    ]

    # A booking overlaps the requested period when its start
    # is on or before the requested end and its end is on or
    # after the requested start.
    parameters: list[Any] = [end_date, start_date]

    # 3. Map accepted filter names to actual database columns.
    filter_conditions = {
        "brand": ("vm.brand = ANY(%s)", "text_list"),
        "model": ("vm.model_name = ANY(%s)", "text_list"),
        "fuel_type": ("vm.fuel_type = ANY(%s)", "text_list"),
        "transmission": ("vm.transmission = ANY(%s)", "text_list"),
        "seats": ("vm.seats = ANY(%s)", "positive_int_list"),
        "min_daily_rate": ("vm.daily_rate >= %s", "nonnegative_int"),
        "max_daily_rate": ("vm.daily_rate <= %s", "nonnegative_int"),
    }

    # 4. Add only the filters supplied by the caller.
    for filter_name, filter_value in (filters or {}).items():

        if filter_name not in filter_conditions:
            #raise ValueError(
            #    f"Unsupported vehicle filter: {filter_name}"
            #)
            print("test")

        # Omitted filters have no effect.
        if filter_value is None:
            continue

        if isinstance(filter_value, str) and not filter_value.strip():
            continue

        condition, filter_type = filter_conditions[filter_name]

        if filter_type == "text_list":

            if not isinstance(filter_value, list):
                raise ValueError(
                    f"Filter '{filter_name}' must be a list."
                )
            
            if not all(isinstance(x, str) for x in filter_value):
                raise ValueError(
                    f"Filter '{filter_name}' must have strings"
                )

            #filter_value = filter_value.strip()

            #if filter_type == "text":
            #    filter_value = f"%{filter_value}%"
            #else:
            #    filter_value = filter_value.upper()

            conditions.append(condition)
            parameters.append(filter_value)

        elif filter_type == "positive_int_list":

            if not isinstance(filter_value, list):
                raise ValueError(
                    f"Filter '{filter_name}' must be a list."
                )

            if not (all(x > 0 for x in filter_value)):
                raise ValueError(
                    "Minimum seating capacity must be "
                    "a positive integer."
                )
            
            conditions.append(condition)
            parameters.append(filter_value)

        elif filter_type == "nonnegative_int":
            
            if not (isinstance(filter_value, int) and filter_value > -1 ):
                raise ValueError(
                    "Maximum/Minimum daily rate must be "
                    "a non-negative integer."
                )

            conditions.append(condition)
            parameters.append(filter_value)            

    # 5. Fetch vehicles and their model details.
    query = f"""
        SELECT
            v.vehicle_id,
            v.registration_no,
            v.odometer,
            v.status,
            vm.model_id,
            vm.brand,
            vm.model_name,
            vm.seats,
            vm.transmission,
            vm.fuel_type,
            vm.daily_rate
        FROM vehicle AS v
        JOIN vehicle_model AS vm
            ON vm.model_id = v.model_id
        WHERE {' AND '.join(conditions)}
        ORDER BY
            vm.daily_rate ASC,
            vm.brand ASC,
            vm.model_name ASC
    """

    # 6. Execute the parameterized query.
    with ConnPool.connection() as connection:
        with connection.cursor() as cursor:

            safe_query = cast(LiteralString, query)

            cursor.execute(safe_query, parameters)
            rows = cursor.fetchall()

            column_names = [
                column.name for column in cursor.description or []
            ]

    # 7. Return a list of dictionaries for the UI teammate.
    return [
        dict(zip(column_names, row))
        for row in rows
    ]


#=============================BOOKING=================================


ADVANCE_PERCENT = Decimal("0.20")

# Money columns are NUMERIC(10,2), so we keep exactly 2 decimal places.
TWO_PLACES = Decimal("0.01")
BOOKING_STATUSES = ("CONFIRMED", "CANCELLED", "COMPLETED")


def create_booking(
    customer_id: int,
    vehicle_id: int,
    start_date: dt.date,
    end_date: dt.date,
    advance_amount: Decimal | int | str | None = None,
) -> dict[str, Any]:
    """
    Create a CONFIRMED booking and its ADVANCE payment together.

    Both rows are saved in one database transaction: either both
    exist afterwards, or neither does.

    Raises ValueError for invalid input, an unknown customer or
    vehicle, an unavailable vehicle, or overlapping bookings.
    """

    # 1. Validate the inputs before touching the database.
    for name, value in (
        ("customer_id", customer_id),
        ("vehicle_id", vehicle_id),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")

    if start_date > end_date:
        raise ValueError("End date must be on or after start date.")

    if start_date < dt.date.today():
        raise ValueError("Start date cannot be in the past.")

    if advance_amount is not None:
        if isinstance(advance_amount, bool):
            raise ValueError("Advance amount must be a number.")
        try:
            advance_amount = Decimal(str(advance_amount))
        except InvalidOperation:
            raise ValueError("Advance amount must be a number.") from None
        if not advance_amount.is_finite():
            raise ValueError("Advance amount must be a finite number.")

    # Both dates are inclusive: 1 Nov to 1 Nov is one billable day.
    days = (end_date - start_date).days + 1

    # 2. Everything inside this block is ONE database transaction.
    with ConnPool.connection() as connection:
        with connection.cursor() as cursor:

            # 2a. The customer must exist.
            cursor.execute(
                "SELECT 1 FROM customer WHERE customer_id = %s",
                (customer_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Customer not found.")

            # 2b. Fetch AND lock the vehicle row (see explanation below).
            cursor.execute(
                """
                SELECT v.status, vm.daily_rate
                FROM vehicle AS v
                JOIN vehicle_model AS vm
                    ON vm.model_id = v.model_id
                WHERE v.vehicle_id = %s
                FOR UPDATE OF v
                """,
                (vehicle_id,),
            )
            vehicle_row = cursor.fetchone()
            if vehicle_row is None:
                raise ValueError("Vehicle not found.")

            vehicle_status, daily_rate = vehicle_row
            if vehicle_status == "UNAVAILABLE":
                raise ValueError(
                    f"Vehicle is not available (status: {vehicle_status})."
                )

            # 2c. Work out the money.
            total_amount = (Decimal(str(daily_rate)) * days).quantize(TWO_PLACES)

            if advance_amount is None:
                advance = (total_amount * ADVANCE_PERCENT).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )
            else:
                advance = advance_amount.quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )

            if advance <= 0 or advance > total_amount:
                raise ValueError(
                    "Advance amount must be more than 0 and "
                    f"at most the total amount ({total_amount})."
                )

            # 2d. Reject the booking if it overlaps a confirmed one.
            cursor.execute(
                """
                SELECT 1
                FROM booking
                WHERE vehicle_id = %s
                  AND status = 'CONFIRMED'
                  AND start_date <= %s
                  AND end_date >= %s
                LIMIT 1
                """,
                (vehicle_id, end_date, start_date),
            )
            if cursor.fetchone() is not None:
                raise ValueError(
                    "Vehicle is already booked for part of these dates."
                )

            # 2e. Insert the booking.
            cursor.execute(
                """
                INSERT INTO booking
                    (customer_id, vehicle_id, start_date, end_date)
                VALUES (%s, %s, %s, %s)
                RETURNING booking_id, booking_date, status
                """,
                (customer_id, vehicle_id, start_date, end_date),
            )
            booking_id, booking_date, booking_status = cursor.fetchone() or (None, None, None)

            # 2f. Insert the ADVANCE payment (rental_id stays NULL).
            cursor.execute(
                """
                INSERT INTO payment
                    (booking_id, rental_id, transaction_type, amount)
                VALUES (%s, NULL, 'ADVANCE', %s)
                RETURNING transaction_id
                """,
                (booking_id, advance),
            )
            (transaction_id,) = cursor.fetchone() or (None,)

    # 3. Reaching this line means the transaction was committed.
    return {
        "booking_id": booking_id,
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "booking_date": booking_date,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "daily_rate": daily_rate,
        "total_amount": total_amount,
        "advance_amount": advance,
        "status": booking_status,
    }

def ClearOldCache():

    Get_Filter_Options.clear()
    search_available_vehicles.clear()
