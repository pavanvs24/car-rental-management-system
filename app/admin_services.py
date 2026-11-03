from app.db import get_connection


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
