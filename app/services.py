from datetime import date
from typing import Any

from app.db import get_connection


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
