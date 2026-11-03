from datetime import date,datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.db import get_connection

# Share of the total rental cost collected as the advance payment
# when the caller does not give an explicit amount.
ADVANCE_PERCENT = Decimal("0.20")

# Money columns are NUMERIC(10,2), so we keep exactly 2 decimal places.
TWO_PLACES = Decimal("0.01")
BOOKING_STATUSES = ("CONFIRMED", "CANCELLED", "COMPLETED")


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

def _clean_text_list(
    name: str,
    value: Any,
    *,
    upper: bool = False,
) -> list[str] | None:
    """
    Turn a UI filter value into a clean list of lower-case
    (or upper-case, if upper=True) strings.

    Returns None when the filter should be ignored: the value is
    missing, empty, or contains the UI's "All" option.
    """

    if value is None:
        return None

    # A single text value is treated as a one-item list.
    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple, set)):
        raise ValueError(f"Filter '{name}' must be a list of text values.")

    cleaned: list[str] = []

    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"Filter '{name}' must contain only text values."
            )

        item = item.strip()

        if not item:
            continue

        if item.lower() == "all":
            return None

        cleaned.append(item.upper() if upper else item.lower())

    return cleaned or None


def _clean_seat_list(value: Any) -> list[int] | None:
    """Same idea as _clean_text_list, for a list of seat counts."""

    if value is None:
        return None

    if isinstance(value, (int, str)) and not isinstance(value, bool):
        value = [value]

    if not isinstance(value, (list, tuple, set)):
        raise ValueError("Filter 'seats' must be a list of whole numbers.")

    cleaned: list[int] = []

    for item in value:
        if isinstance(item, str):
            item = item.strip()

            if not item:
                continue

            if item.lower() == "all":
                return None

            try:
                item = int(item)
            except ValueError:
                raise ValueError(
                    "Filter 'seats' must contain whole numbers."
                ) from None

        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise ValueError(
                "Filter 'seats' must contain positive whole numbers."
            )

        cleaned.append(item)

    return cleaned or None


def _clean_rate(name: str, value: Any) -> Decimal | None:
    """Validate a daily-rate limit. None or blank text means 'no limit'."""

    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    if isinstance(value, bool):
        raise ValueError(f"Filter '{name}' must be a number.")

    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Filter '{name}' must be a number.") from None

    if not number.is_finite() or number < 0:
        raise ValueError(f"Filter '{name}' must be a non-negative number.")

    return number


def search_available_vehicles(
    start_date: date,
    end_date: date,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Return vehicles available throughout the requested date range.

    Vehicles with status UNAVAILABLE are excluded, and so are vehicles
    with a CONFIRMED booking that overlaps the dates (both dates are
    inclusive).

    Optional filters (the keys the Streamlit page sends):
        brand           list of brand names (case-insensitive)
        model           list of model names (case-insensitive)
        fuel_type       list, e.g. ["PETROL"] (case-insensitive)
        transmission    list, e.g. ["MANUAL"] (case-insensitive)
        seats           list of seat counts, e.g. [4, 5]
        min_daily_rate  number: daily_rate >= value
        max_daily_rate  number: daily_rate <= value

    A filter that is missing, None, empty, or contains "All" is
    ignored. Unsupported filter names and invalid values raise
    ValueError.
    """

    # 1. Validate the requested dates.
    if start_date > end_date:
        raise ValueError("End date must be on or after start date.")

    # 2. Exclude UNAVAILABLE vehicles and overlapping confirmed bookings.
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
    parameters: list[Any] = [end_date, start_date]

    # 3. Reject filter names we do not support.
    filters = filters or {}
    allowed = {
        "brand",
        "model",
        "fuel_type",
        "transmission",
        "seats",
        "min_daily_rate",
        "max_daily_rate",
    }
    unknown = [str(key) for key in filters if key not in allowed]

    if unknown:
        raise ValueError(
            "Unsupported vehicle filter: " + ", ".join(sorted(unknown))
        )

    # 4. Add only the filters that have a real value.
    brands = _clean_text_list("brand", filters.get("brand"))
    if brands:
        conditions.append("LOWER(vm.brand) = ANY(%s)")
        parameters.append(brands)

    models = _clean_text_list("model", filters.get("model"))
    if models:
        conditions.append("LOWER(vm.model_name) = ANY(%s)")
        parameters.append(models)

    fuel_types = _clean_text_list(
        "fuel_type", filters.get("fuel_type"), upper=True
    )
    if fuel_types:
        conditions.append("vm.fuel_type = ANY(%s)")
        parameters.append(fuel_types)

    transmissions = _clean_text_list(
        "transmission", filters.get("transmission"), upper=True
    )
    if transmissions:
        conditions.append("vm.transmission = ANY(%s)")
        parameters.append(transmissions)

    seats = _clean_seat_list(filters.get("seats"))
    if seats:
        conditions.append("vm.seats = ANY(%s)")
        parameters.append(seats)

    min_rate = _clean_rate("min_daily_rate", filters.get("min_daily_rate"))
    max_rate = _clean_rate("max_daily_rate", filters.get("max_daily_rate"))

    if min_rate is not None and max_rate is not None and min_rate > max_rate:
        raise ValueError(
            "Minimum daily rate cannot be higher than maximum daily rate."
        )

    if min_rate is not None:
        conditions.append("vm.daily_rate >= %s")
        parameters.append(min_rate)

    if max_rate is not None:
        conditions.append("vm.daily_rate <= %s")
        parameters.append(max_rate)

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


def confirm_pickup(booking_id, staff_id, pickup_odometer=None, pickup_date=None):
    """Confirm a pickup: create the rental row and mark the vehicle RENTED.

    Returns a dict: rental_id, booking_id, vehicle_id, registration_no,
    staff_id, pickup_date, pickup_odometer, status, vehicle_status.

    Raises ValueError for: bad input types, unknown booking, booking not
    CONFIRMED, rental already exists, unknown staff, pickup date outside
    start_date..end_date, vehicle UNAVAILABLE or still RENTED, odometer
    lower than the vehicle's recorded odometer.
    """
    # 1. Validate inputs before touching the database
    for name, value in (("booking_id", booking_id), ("staff_id", staff_id)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if pickup_odometer is not None:
        if (isinstance(pickup_odometer, bool) or not isinstance(pickup_odometer, int)
                or pickup_odometer < 0):
            raise ValueError("pickup_odometer must be a non-negative integer")
    if pickup_date is None:
        pickup_date = date.today()
    elif isinstance(pickup_date, datetime) or not isinstance(pickup_date, date):
        raise ValueError("pickup_date must be a date")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            # 2. Lock the booking row (same lock cancel_booking takes)
            cursor.execute(
                "SELECT vehicle_id, start_date, end_date, status "
                "FROM booking WHERE booking_id = %s FOR UPDATE",
                (booking_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Booking not found")
            vehicle_id, start_date, end_date, status = row

            # 3. Booking must be CONFIRMED
            if status != "CONFIRMED":
                raise ValueError(f"Booking is {status}, only CONFIRMED bookings can be picked up")

            # 4. No rental may exist yet (UNIQUE constraint is the safety net)
            cursor.execute("SELECT 1 FROM rental WHERE booking_id = %s", (booking_id,))
            if cursor.fetchone() is not None:
                raise ValueError("This booking has already been picked up")

            # 5. Staff must exist
            cursor.execute("SELECT 1 FROM staff WHERE staff_id = %s", (staff_id,))
            if cursor.fetchone() is None:
                raise ValueError("Staff member not found")

            # 6. Pickup window, both ends inclusive
            if not (start_date <= pickup_date <= end_date):
                raise ValueError(
                    f"Pickup date must be between {start_date} and {end_date}"
                )

            # 7. Lock the vehicle row and check its status
            cursor.execute(
                "SELECT registration_no, status, odometer "
                "FROM vehicle WHERE vehicle_id = %s FOR UPDATE",
                (vehicle_id,),
            )
            registration_no, vehicle_status, recorded_odometer = cursor.fetchone()
            if vehicle_status == "UNAVAILABLE":
                raise ValueError("Vehicle is UNAVAILABLE")
            if vehicle_status == "RENTED":
                raise ValueError(
                    "Vehicle is still out on another rental; wait for its return "
                    "or move the booking to another car"
                )

            # 8. Odometer: default to recorded value, never lower
            if pickup_odometer is None:
                pickup_odometer = recorded_odometer
            elif pickup_odometer < recorded_odometer:
                raise ValueError(
                    f"pickup_odometer cannot be lower than the recorded odometer ({recorded_odometer})"
                )

            # 9. Create the rental row
            cursor.execute(
                "INSERT INTO rental (booking_id, pickup_staff_id, pickup_date, pickup_odometer) "
                "VALUES (%s, %s, %s, %s) RETURNING rental_id, status",
                (booking_id, staff_id, pickup_date, pickup_odometer),
            )
            rental_id, rental_status = cursor.fetchone()

            # 10. Mark the vehicle RENTED (booking stays CONFIRMED, no payment here)
            cursor.execute(
                "UPDATE vehicle SET status = 'RENTED' WHERE vehicle_id = %s",
                (vehicle_id,),
            )

    return {
        "rental_id": rental_id,
        "booking_id": booking_id,
        "vehicle_id": vehicle_id,
        "registration_no": registration_no,
        "staff_id": staff_id,
        "pickup_date": pickup_date,
        "pickup_odometer": pickup_odometer,
        "status": rental_status,
        "vehicle_status": "RENTED",
    }

def process_return(registration_no, staff_id, return_odometer, return_date=None, other_charge=0):
    """Process a return: close the rental, bill the final amount, free the car.

    Returns a dict: rental_id, booking_id, vehicle_id, registration_no,
    return_date, return_odometer, distance, days_booked, late_days,
    base_amount, late_charge, other_charge, advance_paid, final_amount,
    final_payment_id (None when no row written), refund_due.

    Raises ValueError for: bad input types, no ACTIVE rental for the
    registration number, unknown staff, return_date before pickup_date,
    return_odometer not above pickup_odometer, negative or invalid other_charge.
    """
    # 1. Validate inputs before touching the database
    if not isinstance(registration_no, str) or not registration_no.strip():
        raise ValueError("registration_no must be non-blank text")
    registration_no = registration_no.strip()
    if isinstance(staff_id, bool) or not isinstance(staff_id, int) or staff_id <= 0:
        raise ValueError("staff_id must be a positive integer")
    if (isinstance(return_odometer, bool) or not isinstance(return_odometer, int)
            or return_odometer < 0):
        raise ValueError("return_odometer must be a non-negative integer")
    if return_date is None:
        return_date = date.today()
    elif isinstance(return_date, datetime) or not isinstance(return_date, date):
        raise ValueError("return_date must be a date")
    if isinstance(other_charge, bool):
        raise ValueError("other_charge must be a number")
    try:
        other_charge = Decimal(str(other_charge))
    except InvalidOperation:
        raise ValueError("other_charge must be a number")
    if not other_charge.is_finite() or other_charge < 0:
        raise ValueError("other_charge must be a finite amount, zero or more")
    cent = Decimal("0.01")
    other_charge = other_charge.quantize(cent, rounding=ROUND_HALF_UP)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            # 2. Find the ACTIVE rental for this registration number (plain read)
            cursor.execute(
                "SELECT r.rental_id, r.booking_id, b.vehicle_id "
                "FROM rental r "
                "JOIN booking b ON b.booking_id = r.booking_id "
                "JOIN vehicle v ON v.vehicle_id = b.vehicle_id "
                "JOIN vehicle_model m ON m.model_id = v.model_id "
                "WHERE v.registration_no = %s AND r.status = 'ACTIVE'",
                (registration_no,),
            )
            found = cursor.fetchone()
            if found is None:
                raise ValueError("No active rental for this vehicle")
            rental_id, booking_id, vehicle_id = found

            # 3. Lock booking, then rental, then vehicle; re-check ACTIVE
            cursor.execute(
                "SELECT start_date, end_date FROM booking "
                "WHERE booking_id = %s FOR UPDATE",
                (booking_id,),
            )
            start_date, end_date = cursor.fetchone()
            cursor.execute(
                "SELECT pickup_date, pickup_odometer, status FROM rental "
                "WHERE rental_id = %s FOR UPDATE",
                (rental_id,),
            )
            pickup_date, pickup_odometer, rental_status = cursor.fetchone()
            if rental_status != "ACTIVE":
                raise ValueError("No active rental for this vehicle")
            cursor.execute(
                "SELECT m.daily_rate FROM vehicle v "
                "JOIN vehicle_model m ON m.model_id = v.model_id "
                "WHERE v.vehicle_id = %s FOR UPDATE OF v",
                (vehicle_id,),
            )
            daily_rate = Decimal(str(cursor.fetchone()[0]))

            # 4. Staff must exist
            cursor.execute("SELECT 1 FROM staff WHERE staff_id = %s", (staff_id,))
            if cursor.fetchone() is None:
                raise ValueError("Staff member not found")

            # 5. Date and odometer sanity (clear messages before the CHECK fires)
            if return_date < pickup_date:
                raise ValueError(f"return_date cannot be before pickup date ({pickup_date})")
            if return_odometer <= pickup_odometer:
                raise ValueError(
                    f"return_odometer must be above the pickup reading ({pickup_odometer})"
                )

            # 6. Money (all Decimal, 2 places)
            days_booked = (end_date - start_date).days + 1
            base_amount = (daily_rate * days_booked).quantize(cent, rounding=ROUND_HALF_UP)
            late_days = max((return_date - end_date).days, 0)
            late_charge = (daily_rate * late_days).quantize(cent, rounding=ROUND_HALF_UP)
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payment "
                "WHERE booking_id = %s AND transaction_type = 'ADVANCE'",
                (booking_id,),
            )
            advance_paid = Decimal(str(cursor.fetchone()[0])).quantize(cent, rounding=ROUND_HALF_UP)
            final_amount = (base_amount + late_charge + other_charge - advance_paid).quantize(
                cent, rounding=ROUND_HALF_UP
            )

            # 7. Close the rental
            cursor.execute(
                "UPDATE rental SET return_staff_id = %s, return_date = %s, "
                "return_odometer = %s, late_charge = %s, other_charge = %s, "
                "status = 'COMPLETED' WHERE rental_id = %s",
                (staff_id, return_date, return_odometer, late_charge, other_charge, rental_id),
            )

            # 8. FINAL payment only if something is owed (amount must be > 0)
            final_payment_id = None
            if final_amount > 0:
                cursor.execute(
                    "INSERT INTO payment (booking_id, rental_id, transaction_type, amount) "
                    "VALUES (%s, %s, 'FINAL', %s) RETURNING transaction_id",
                    (booking_id, rental_id, final_amount),
                )
                final_payment_id = cursor.fetchone()[0]
                refund_due = Decimal("0.00")
            else:
                refund_due = (-final_amount).quantize(cent, rounding=ROUND_HALF_UP)

            # 9. Free the vehicle and record the new odometer
            cursor.execute(
                "UPDATE vehicle SET status = 'AVAILABLE', odometer = %s WHERE vehicle_id = %s",
                (return_odometer, vehicle_id),
            )

            # 10. Complete the booking
            cursor.execute(
                "UPDATE booking SET status = 'COMPLETED' WHERE booking_id = %s",
                (booking_id,),
            )

    return {
        "rental_id": rental_id,
        "booking_id": booking_id,
        "vehicle_id": vehicle_id,
        "registration_no": registration_no,
        "return_date": return_date,
        "return_odometer": return_odometer,
        "distance": return_odometer - pickup_odometer,
        "days_booked": days_booked,
        "late_days": late_days,
        "base_amount": base_amount,
        "late_charge": late_charge,
        "other_charge": other_charge,
        "advance_paid": advance_paid,
        "final_amount": final_amount,
        "final_payment_id": final_payment_id,
        "refund_due": refund_due,
    }