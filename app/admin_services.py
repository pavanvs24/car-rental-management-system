from app.db import get_connection
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from psycopg.errors import UniqueViolation, ForeignKeyViolation

BOOKING_STATUSES = ('CONFIRMED', 'CANCELLED', 'COMPLETED')
FUEL_TYPES = ('PETROL','DIESEL','CNG','LPG','ELECTRIC','HYBRID')
TRANSMISSIONS = ('MANUAL','AUTOMATIC')


def _rows_to_dicts(cursor):
    rows = cursor.fetchall()
    column_names = [column.name for column in cursor.description]

    return [dict(zip(column_names, row)) for row in rows]


def _require_id(value, name): 
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{name} must be a positive integer.")


def list_active_rentals():
    """
    Return list of dicts of active rentals, order by due_date, rental_id
    """
    
    query = """
        SELECT 
            r.rental_id,
            r.booking_id,
            r.pickup_date,
            b.end_date AS due_date,
            c.customer_id,
            c.full_name AS customer_name,
            c.phone,
            v.vehicle_id,
            v.registration_no,
            vm.brand,
            vm.model_name,
            GREATEST(CURRENT_DATE - b.end_date, 0) AS days_overdue
        FROM rental r
        JOIN booking b
        ON (b.booking_id = r.booking_id)
        JOIN customer c
        ON (c.customer_id = b.customer_id)
        JOIN vehicle v
        ON (v.vehicle_id = b.vehicle_id)
        JOIN vehicle_model vm
        ON (vm.model_id = v.model_id)
        WHERE r.status = 'ACTIVE'
        ORDER BY b.end_date, r.rental_id;
    """
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return _rows_to_dicts(cursor)


def get_vehicle_history(vehicle_id):
    """ Returns a dict of vehicle details with an 'entries' key holding a list of dicts of all bookings/rentals. """

    _require_id(vehicle_id, "vehicle_id")

    vehicle_query = """
        SELECT 
            v.vehicle_id,
            v.registration_no,
            v.status,
            v.odometer,
            vm.brand,
            vm.model_name,
            vm.fuel_type,
            vm.transmission,
            vm.seats,
            vm.daily_rate
        FROM vehicle v JOIN vehicle_model vm
        ON v.model_id = vm.model_id
        WHERE v.vehicle_id = %s;
    """

    entries_query = """
        SELECT
            b.booking_id,
            b.start_date,
            b.end_date,
            b.status,
            c.customer_id,
            c.full_name AS customer_name,
            r.rental_id,
            r.pickup_date,
            r.pickup_odometer,
            r.return_date,
            r.return_odometer,
            r.late_charge,
            r.other_charge,
            r.status AS rental_status
        FROM booking b
        LEFT JOIN rental r
        ON b.booking_id = r.booking_id
        JOIN customer c
        ON c.customer_id = b.customer_id
        WHERE b.vehicle_id = %s
        ORDER BY b.start_date DESC, b.booking_id DESC;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(vehicle_query, (vehicle_id,))
            result = _rows_to_dicts(cursor)

            if not result:
                raise ValueError("Vehicle not found.")
            result = result[0]

            cursor.execute(entries_query, (vehicle_id,))
            result["entries"] = _rows_to_dicts(cursor)

    return result


def list_bookings(filters=None, limit=100, offset=0):
    """ 
        Filters -> status, customer_id, vehicle_id, from_date & to_date.
            unknown filter will raise ValueError.
        Returns a list of dicts with keys 
            booking_id, booking_date, start_date, end_date,
            days, status, customer_id, customer_name,
            vehicle_id, registration_no, brand, model_name,
            total_amount.
    """

    filters = filters or {}

    allowed = ["status", "customer_id", "vehicle_id", "from_date", "to_date"]
    unknown = [key for key in filters if key not in allowed]
    if unknown:
        raise ValueError("Unsupported booking filter: " + ", ".join(unknown))

    conditions = []
    parameters = []

    if filters.get("status") is not None:
        status_filter = filters["status"]

        if not isinstance(status_filter, str) and not isinstance(status_filter, list):
            raise ValueError("Status should be a list or string.")
        
        if isinstance(status_filter, str):
            if status_filter.strip():
                statuses = [status_filter]
            else:
                raise ValueError("Invalid status value.")
        else:
            statuses = [status for status in status_filter]

        for i, status in enumerate(statuses):
            if not isinstance(status, str) or status.strip().upper() not in BOOKING_STATUSES:
                raise ValueError("Invalid status value.")
            statuses[i] = status.strip().upper()

        if statuses:
            conditions.append("b.status = ANY(%s)")
            parameters.append(statuses)

    if filters.get("customer_id") is not None:
        _require_id(filters["customer_id"], "customer_id")
        conditions.append("c.customer_id = %s")
        parameters.append(filters["customer_id"])

    if filters.get("vehicle_id") is not None:
        _require_id(filters["vehicle_id"], "vehicle_id")
        conditions.append("v.vehicle_id = %s")
        parameters.append(filters["vehicle_id"])

    if filters.get("from_date") is not None:
        if not isinstance(filters["from_date"], date):
            raise ValueError("Invalid from date.")
        conditions.append("b.end_date >= %s")
        parameters.append(filters["from_date"])

    if filters.get("to_date") is not None:
        if not isinstance(filters["to_date"], date):
            raise ValueError("Invalid to date.")
        conditions.append("b.start_date <= %s")
        parameters.append(filters["to_date"])

    if (
        filters.get("from_date") is not None 
        and filters.get("to_date") is not None 
        and filters["from_date"] > filters["to_date"]
    ):
        raise ValueError("The to_date cannot be earlier than from_date.")

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int) 
        or limit < 1 or limit > 500 
    ):
        raise ValueError("The limit should be an integer between 1 and 500.")

    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or offset < 0
    ):
        raise ValueError("The offset should be at least 0.")

    where = " AND ".join(conditions) if conditions else "TRUE"
    parameters.extend([limit, offset])

    query = f"""
        SELECT
            b.booking_id,
            b.booking_date,
            b.start_date,
            b.end_date,
            (b.end_date - b.start_date + 1) AS days,
            b.status,
            c.customer_id,
            c.full_name AS customer_name,
            v.vehicle_id,
            v.registration_no,
            vm.brand,
            vm.model_name,
            (vm.daily_rate * (b.end_date - b.start_date + 1)) AS total_amount
        FROM booking b
        JOIN customer c 
        ON c.customer_id = b.customer_id
        JOIN vehicle v
        ON v.vehicle_id = b.vehicle_id
        JOIN vehicle_model vm
        ON vm.model_id = v.model_id
        WHERE {where}
        ORDER BY b.start_date DESC, b.booking_id DESC
        LIMIT %s OFFSET %s
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return _rows_to_dicts(cursor)


def get_booking_details(booking_id, customer_id=None):
    """
        Returns everything about one booking as dict.
        customer_id is optional, when given it means
            "only if the customer owns this booking"
        Raises ValueError when not found.
    """

    _require_id(booking_id, "booking_id")
    conditions = ["b.booking_id = %s"]
    parameters = [booking_id]

    if customer_id is not None:
        _require_id(customer_id, "customer_id")
        conditions.append("b.customer_id = %s")
        parameters.append(customer_id)

    where = " AND ".join(conditions)

    main_query = f"""
        SELECT
            b.booking_id,
            b.booking_date,
            b.start_date,
            b.end_date,
            (b.end_date - b.start_date + 1) AS days,
            b.status,
            v.vehicle_id,
            v.registration_no,
            vm.brand,
            vm.model_name,
            vm.daily_rate
        FROM booking b
        JOIN vehicle v
        ON b.vehicle_id = v.vehicle_id
        JOIN vehicle_model vm
        ON v.model_id = vm.model_id
        WHERE {where}
    """

    customer_query = """
        SELECT
            customer_id,
            full_name,
            email,
            phone
        FROM customer
        WHERE customer_id = (
            SELECT customer_id
            FROM booking
            WHERE booking_id = %s
        )
    """

    payment_query = """
        SELECT
            transaction_id,
            transaction_type,
            amount,
            paid_at,
            rental_id
        FROM payment
        WHERE booking_id = %s
        ORDER BY paid_at, transaction_id;
    """

    rental_query = """
        SELECT 
            rental_id,
            pickup_staff_id,
            return_staff_id,
            pickup_date,
            pickup_odometer,
            return_date,
            return_odometer,
            late_charge,
            other_charge,
            status
        FROM rental
        WHERE booking_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(main_query, parameters)
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Booking not found.")
            column_names = [column.name for column in cursor.description]
            result = dict(zip(column_names, row))

            cursor.execute(customer_query, (booking_id,))
            result["customer"] = _rows_to_dicts(cursor)[0]

            cursor.execute(payment_query, (booking_id,))
            result["payments"] = _rows_to_dicts(cursor)

            cursor.execute(rental_query, (booking_id,))
            row = cursor.fetchone()
            if row is None:
                result["rental"] = None
            else:
                column_names = [column.name for column in cursor.description]
                result["rental"] = dict(zip(column_names, row))

    result["total_amount"] = result["daily_rate"] * result["days"]
    result["total_paid"] = sum((p["amount"] for p in result["payments"]), Decimal("0"))
    return result


def add_vehicle_model(brand, model_name, fuel_type, transmission, seats, daily_rate):
    """
        Returns the row inserted as a dict.
        Raises ValueError for invalid inputs.
    """
    if not isinstance(brand, str) or not brand.strip():
        raise ValueError("Invalid brand.")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Invalid model_name.")
    if not isinstance(fuel_type, str) or fuel_type.strip().upper() not in FUEL_TYPES:
        raise ValueError("Invalid fuel_type.")
    if not isinstance(transmission, str) or transmission.strip().upper() not in TRANSMISSIONS:
        raise ValueError("Invalid transmission.")

    _require_id(seats, "seats")

    try:
        daily_rate = Decimal(str(daily_rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError("Invalid daily_rate.")

    if not daily_rate.is_finite() or daily_rate <= 0:
        raise ValueError("The daily_rate must be positive.")

    brand, model_name = brand.strip(), model_name.strip()
    fuel_type, transmission = fuel_type.strip().upper(), transmission.strip().upper()

    query = """
        INSERT INTO vehicle_model
        ("brand", "model_name", "fuel_type", "transmission", "seats", "daily_rate")
        VALUES
        (%s, %s, %s, %s, %s, %s)
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query, 
                (brand, model_name, fuel_type, transmission, seats, daily_rate)
            )
            return _rows_to_dicts(cursor)[0]


def add_vehicle(model_id, registration_no, odometer=0, status='AVAILABLE'):
    """
        Returns the row inserted as a dict.
        Raises ValueError for invalid inputs.
    """
    _require_id(model_id, "model_id")

    if not isinstance(registration_no, str) or not registration_no.strip():
        raise ValueError("Invalid registration_no.")
    registration_no = registration_no.strip()

    if isinstance(odometer, bool) or not isinstance(odometer, int) or odometer < 0:
        raise ValueError("Invalid odometer.")

    if not isinstance(status, str) or status.strip().upper() not in ('AVAILABLE','UNAVAILABLE'):
        raise ValueError("Invalid status.")
    status = status.strip().upper()

    query = """
        INSERT INTO
        vehicle ("model_id", "registration_no", "odometer", "status")
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(query, (model_id, registration_no, odometer, status))
            except UniqueViolation:
                raise ValueError("Registration number already exists.")
            except ForeignKeyViolation:
                raise ValueError("Vehicle model not found.")

            return _rows_to_dicts(cursor)[0]


def set_vehicle_status(vehicle_id, new_status):
    """
        Returns a dict with vehicle_id, old_status, new_status, affected_bookings.
        affected_bookings is a list of dicts with booking_id, customer_id, start_date, end_date
        of future CONFIRMED boookings of the vehicle for reassigning by staff.
        (only when new_status is UNAVAILABLE) or else an empty list.
    """
    _require_id(vehicle_id, "vehicle_id")

    if not isinstance(new_status, str) or new_status.strip().upper() not in ('AVAILABLE','UNAVAILABLE'):
        raise ValueError("Invalid vehicle status.")
    new_status = new_status.strip().upper()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM vehicle WHERE vehicle_id = %s FOR UPDATE;",
                (vehicle_id,)    
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Vehicle not found.")
            old_status = row[0]
        
            cursor.execute("""
                SELECT 1 FROM rental r JOIN booking b
                ON r.booking_id = b.booking_id
                WHERE b.vehicle_id = %s
                AND r.rental = 'ACTIVE'
                LIMIT 1;""",
                (vehicle_id,)
            )
            if cursor.fetchone() is not None:
                raise ValueError("Vehicle has an active rental.")

            query = """
                UPDATE vehicle
                SET status = %s
                WHERE vehicle_id = %s
            """

            cursor.execute(query, (new_status, vehicle_id))

            result = {"vehicle_id": vehicle_id, "old_status": old_status, "new_status": new_status}

            if new_status == "AVAILABLE":
                result["affected_bookings"] = []
                return result

            booking_query = """
                SELECT 
                    booking_id,
                    customer_id,
                    start_date,
                    end_date
                FROM booking
                WHERE vehicle_id = %s
                AND end_date >= CURRENT_DATE
                AND status = 'CONFIRMED'
                ORDER BY start_date;
            """
            cursor.execute(booking_query, (vehicle_id,))
            result["affected_bookings"] = _rows_to_dicts(cursor)
            return result


def reassign_booking_vehicle(booking_id, new_vehicle_id=None):
    """
        Return a dict of booking_id, old_vehicle_id, new_vehicle_id
        Auto reassign works only for same vehicle model
        Manual reassign works for different model and upgrades.
    """
    # Validation
    _require_id(booking_id, "booking_id")

    if new_vehicle_id is not None:
        _require_id(new_vehicle_id, "new_vehicle_id")

    lock_booking_query = """
        SELECT vehicle_id, status, start_date, end_date
        FROM booking WHERE booking_id = %s
        FOR UPDATE;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            # Finding booking & locking
            cursor.execute(lock_booking_query, (booking_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Booking not found.")

            # Storing Booking details in result as dict
            column_names = [column.name for column in cursor.description]
            result = dict(zip(column_names, row))
            if result["status"] != "CONFIRMED":
                raise ValueError("Booking is not confirmed.")

            # Checking if booking has rental.
            cursor.execute("""
                SELECT 1 FROM rental WHERE booking_id = %s 
                LIMIT 1""", 
                (booking_id,)
            )
            if cursor.fetchone() is not None:
                raise ValueError("Booking already has a rental.")

            # Auto reassigning - finding new_vehicle_id.
            if new_vehicle_id is None:
                cursor.execute("""
                    SELECT model_id FROM vehicle
                    WHERE vehicle_id = %s""",
                    (result["vehicle_id"],)
                )
                model_id = cursor.fetchone()[0]
                candidate_query = """
                    SELECT vehicle_id
                    FROM vehicle v
                    WHERE v.model_id = %s
                        AND v.vehicle_id <> %s
                        AND v.status <> 'UNAVAILABLE'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM booking x
                            WHERE x.vehicle_id = v.vehicle_id
                                AND x.status = 'CONFIRMED'
                                AND x.start_date <= %s
                                AND x.end_date >= %s
                        )
                    ORDER BY v.vehicle_id;
                """
                cursor.execute(
                    candidate_query,
                    (model_id, result["vehicle_id"], result["end_date"], result["start_date"])
                )
                candidates = [r[0] for r in cursor.fetchall()]
                if not candidates:
                    raise ValueError("No other vehicle of the same model is free for these dates.")
                new_vehicle_id = candidates[0]

            # Reassigning.
            if new_vehicle_id == result["vehicle_id"]:
                raise ValueError("Cannot reassign to same vehicle.")

            cursor.execute("""
                SELECT status FROM vehicle
                WHERE vehicle_id = %s
                FOR UPDATE""",
                (new_vehicle_id,)
            )
            new_vehicle_row = cursor.fetchone()
            if new_vehicle_row is None:
                raise ValueError("Vehicle not found.")
            if new_vehicle_row[0] == 'UNAVAILABLE':
                raise ValueError("Vehicle is not available.")

            cursor.execute("""
                SELECT 1 FROM booking
                WHERE vehicle_id = %s
                    AND status = 'CONFIRMED'
                    AND start_date <= %s
                    AND end_date >= %s
                LIMIT 1""",
                (new_vehicle_id, result["end_date"], result["start_date"])
            )
            if cursor.fetchone() is not None:
                raise ValueError("Vehicle has another confirmed booking in these dates.")

            cursor.execute("""
                UPDATE booking
                SET vehicle_id = %s
                WHERE booking_id = %s""",
                (new_vehicle_id, booking_id)
            )
            return {
                "booking_id": booking_id,
                "old_vehicle_id": result["vehicle_id"],
                "new_vehicle_id": new_vehicle_id
            }
