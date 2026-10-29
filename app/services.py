from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.db import get_connection

# Share of the total rental cost collected as the advance payment
# when the caller does not give an explicit amount.
ADVANCE_PERCENT = Decimal("0.20")

# Money columns are NUMERIC(10,2), so we keep exactly 2 decimal places.
TWO_PLACES = Decimal("0.01")
BOOKING_STATUSES = ("CONFIRMED", "CANCELLED", "COMPLETED")


def search_available_vehicles(
    start_date: date,
    end_date: date,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Return vehicles available throughout the requested date range.

    Optional filters:
        brand
        model_name
        fuel_type
        transmission
        min_seating_capacity
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
        "v.status <> 'UNAVAILABLE'",
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
        "brand": ("vm.brand ILIKE %s", "text"),
        "model_name": ("vm.model_name ILIKE %s", "text"),
        "fuel_type": ("vm.fuel_type = %s", "upper"),
        "transmission": ("vm.transmission = %s", "upper"),
        "min_seating_capacity": ("vm.seats >= %s", "positive_int"),
        "max_daily_rate": ("vm.daily_rate <= %s", "nonnegative_int"),
    }

    # 4. Add only the filters supplied by the caller.
    for filter_name, filter_value in (filters or {}).items():

        if filter_name not in filter_conditions:
            raise ValueError(
                f"Unsupported vehicle filter: {filter_name}"
            )

        # Omitted filters have no effect.
        if filter_value is None:
            continue

        if isinstance(filter_value, str) and not filter_value.strip():
            continue

        condition, filter_type = filter_conditions[filter_name]

        if filter_type in ("text", "upper"):
            if not isinstance(filter_value, str):
                raise ValueError(
                    f"Filter '{filter_name}' must be text."
                )

            filter_value = filter_value.strip()

            if filter_type == "text":
                filter_value = f"%{filter_value}%"
            else:
                filter_value = filter_value.upper()

        elif filter_type == "positive_int":
            if (
                isinstance(filter_value, bool)
                or not isinstance(filter_value, int)
                or filter_value < 1
            ):
                raise ValueError(
                    "Minimum seating capacity must be "
                    "a positive integer."
                )

        elif filter_type == "nonnegative_int":
            if (
                isinstance(filter_value, bool)
                or not isinstance(filter_value, int)
                or filter_value < 0
            ):
                raise ValueError(
                    "Maximum daily rate must be "
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
        WHERE {" AND ".join(conditions)}
        ORDER BY
            vm.daily_rate ASC,
            vm.brand ASC,
            vm.model_name ASC
    """

    # 6. Execute the parameterized query.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()

            column_names = [
                column.name for column in cursor.description
            ]

    # 7. Return a list of dictionaries for the UI teammate.
    return [
        dict(zip(column_names, row))
        for row in rows
    ]

def create_booking(
    customer_id: int,
    vehicle_id: int,
    start_date: date,
    end_date: date,
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

    if start_date < date.today():
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
    with get_connection() as connection:
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
            booking_id, booking_date, booking_status = cursor.fetchone()

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
            (transaction_id,) = cursor.fetchone()

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

def get_customer_bookings(
    customer_id: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return a customer's bookings, newest rental start first.

    Optional status filter: CONFIRMED, CANCELLED or COMPLETED
    (case-insensitive). Raises ValueError for invalid input or an
    unknown customer. A customer with no bookings gets an empty list.
    """

    # 1. Validate the inputs.
    if (
        isinstance(customer_id, bool)
        or not isinstance(customer_id, int)
        or customer_id < 1
    ):
        raise ValueError("customer_id must be a positive integer.")

    # An empty or whitespace-only status means "no filter".
    if isinstance(status, str) and not status.strip():
        status = None

    conditions = ["b.customer_id = %s"]
    parameters: list[Any] = [customer_id]

    if status is not None:
        if not isinstance(status, str):
            raise ValueError("Status must be text.")

        status = status.strip().upper()

        if status not in BOOKING_STATUSES:
            raise ValueError(
                "Status must be one of: "
                + ", ".join(BOOKING_STATUSES)
            )

        conditions.append("b.status = %s")
        parameters.append(status)

    # 2. Build the query. Dates are inclusive, so days = end - start + 1.
    query = f"""
        SELECT
            b.booking_id,
            b.booking_date,
            b.start_date,
            b.end_date,
            (b.end_date - b.start_date + 1) AS days,
            b.status,
            v.vehicle_id,
            v.registration_no,
            m.brand,
            m.model_name,
            m.daily_rate,
            m.daily_rate * (b.end_date - b.start_date + 1)
                AS total_amount
        FROM booking AS b
        JOIN vehicle AS v
            ON v.vehicle_id = b.vehicle_id
        JOIN vehicle_model AS m
            ON m.model_id = v.model_id
        WHERE {" AND ".join(conditions)}
        ORDER BY b.start_date DESC, b.booking_id DESC
    """

    # 3. Run it, and check that the customer exists in the same connection.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM customer WHERE customer_id = %s",
                (customer_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Customer not found.")

            cursor.execute(query, parameters)
            rows = cursor.fetchall()

            column_names = [
                column.name for column in cursor.description
            ]

    # 4. Return a list of dictionaries for the UI teammate.
    return [dict(zip(column_names, row)) for row in rows]


def cancel_booking(
    booking_id: int,
    customer_id: int | None = None,
) -> dict[str, Any]:
    """
    Cancel a CONFIRMED booking that has not been picked up yet.

    If customer_id is given, the booking must belong to that
    customer (customer-side cancel). If it is omitted, the call is
    treated as an admin cancel.

    The advance payment is kept on record; the returned
    'advance_paid' tells the caller how much was paid so a refund
    can be handled outside the database.

    Raises ValueError for invalid input, an unknown booking, a booking
    that belongs to someone else, a booking that is not CONFIRMED, or
    a booking whose vehicle has already been picked up.
    """

    # 1. Validate the inputs.
    if (
        isinstance(booking_id, bool)
        or not isinstance(booking_id, int)
        or booking_id < 1
    ):
        raise ValueError("booking_id must be a positive integer.")

    if customer_id is not None and (
        isinstance(customer_id, bool)
        or not isinstance(customer_id, int)
        or customer_id < 1
    ):
        raise ValueError("customer_id must be a positive integer.")

    # 2. Everything inside this block is ONE database transaction.
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # 2a. Fetch AND lock the booking row.
            cursor.execute(
                """
                SELECT customer_id, vehicle_id, start_date, end_date, status
                FROM booking
                WHERE booking_id = %s
                FOR UPDATE
                """,
                (booking_id,),
            )
            booking_row = cursor.fetchone()
            if booking_row is None:
                raise ValueError("Booking not found.")

            (
                owner_id,
                vehicle_id,
                start_date,
                end_date,
                current_status,
            ) = booking_row

            # 2b. A customer may only cancel their own booking.
            if customer_id is not None and owner_id != customer_id:
                raise ValueError("Booking not found.")

            # 2c. Only CONFIRMED bookings can be cancelled.
            if current_status != "CONFIRMED":
                raise ValueError(
                    "Only CONFIRMED bookings can be cancelled "
                    f"(status: {current_status})."
                )

            # 2d. Not after the vehicle has been picked up.
            cursor.execute(
                "SELECT 1 FROM rental WHERE booking_id = %s",
                (booking_id,),
            )
            if cursor.fetchone() is not None:
                raise ValueError(
                    "Booking cannot be cancelled: "
                    "the vehicle has already been picked up."
                )

            # 2e. Cancel it.
            cursor.execute(
                """
                UPDATE booking
                SET status = 'CANCELLED'
                WHERE booking_id = %s
                """,
                (booking_id,),
            )

            # 2f. How much has been paid for this booking so far?
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payment
                WHERE booking_id = %s
                """,
                (booking_id,),
            )
            (advance_paid,) = cursor.fetchone()

    # 3. Reaching this line means the transaction was committed.
    return {
        "booking_id": booking_id,
        "customer_id": owner_id,
        "vehicle_id": vehicle_id,
        "start_date": start_date,
        "end_date": end_date,
        "status": "CANCELLED",
        "advance_paid": advance_paid,
    }