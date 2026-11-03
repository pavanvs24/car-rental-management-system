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

