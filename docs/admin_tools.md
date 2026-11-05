# Admin tools (staff side)

All functions live in `app/admin_services.py`.

```python
from app.admin_services import list_bookings, get_booking_details  # etc.
```

## Rules that apply to every function

- Errors are `ValueError` with a message that can be shown to the user as it is.
- Nothing is saved when a `ValueError` is raised.
- Ids are positive ints (`True` and `False` are rejected).
- Dates are `datetime.date` objects. Money values come back as `Decimal`.
- Optional filters: `None` means "not given". A blank string raises `ValueError`.
- For `status`, `fuel_type` and `transmission` filters, a string or a list of strings is accepted, case-insensitive. An empty list means "not given".
- List functions take `limit` (1 to 500, default 100) and `offset` (0 or more, default 0).
- An unknown filter key raises `ValueError`.

---

## Reading

### `list_active_rentals()`
Cars that are out right now, ordered by due date.
Returns a list of dicts: `rental_id, booking_id, pickup_date, due_date, customer_id, customer_name, phone, vehicle_id, registration_no, brand, model_name, days_overdue` (0 if not overdue).

### `list_bookings(filters=None, limit=100, offset=0)`
Filters: `status` (CONFIRMED, CANCELLED, COMPLETED), `customer_id`, `vehicle_id`, `from_date`, `to_date`.
The date filters return bookings that overlap the range. `from_date` cannot be after `to_date`.
Returns a list of dicts: `booking_id, booking_date, start_date, end_date, days, status, customer_id, customer_name, vehicle_id, registration_no, brand, model_name, total_amount`.
Ordered newest start date first.

### `get_booking_details(booking_id, customer_id=None)`
Everything about one booking. When `customer_id` is given, the booking must belong to that customer.
Returns a dict:
- `booking_id, booking_date, start_date, end_date, days, status`
- `vehicle_id, registration_no, brand, model_name, daily_rate`
- `customer`: dict with `customer_id, full_name, email, phone`
- `payments`: list of dicts with `transaction_id, transaction_type, amount, paid_at, rental_id`
- `rental`: dict (`rental_id, pickup_staff_id, return_staff_id, pickup_date, pickup_odometer, return_date, return_odometer, late_charge, other_charge, status`) or `None` before pickup
- `total_amount` (cost of the booking) and `total_paid` (sum of payments so far)

Raises: `Booking not found.` (also when the booking is not that customer's)

### `get_vehicle_history(vehicle_id)`
Returns a dict with the vehicle's details (`vehicle_id, registration_no, status, odometer, brand, model_name, fuel_type, transmission, seats, daily_rate`) and `entries`, a list of dicts for every booking, newest first: `booking_id, start_date, end_date, status, customer_id, customer_name, rental_id, pickup_date, pickup_odometer, return_date, return_odometer, late_charge, other_charge, rental_status`.
The rental fields are `None` when the booking has no rental.

Raises: `Vehicle not found.`

### `list_vehicles(filters=None, limit=100, offset=0)`
Filters:
- `status` (AVAILABLE, RENTED, UNAVAILABLE), `model_id`
- `registration_no`, `brand`, `model_name`: partial, case-insensitive match
- `fuel_type` (PETROL, DIESEL, CNG, LPG, ELECTRIC, HYBRID), `transmission` (MANUAL, AUTOMATIC)
- `min_seats`
- `min_daily_rate`, `max_daily_rate`: inclusive bounds, positive numbers, min cannot be above max

Returns a list of dicts: `vehicle_id, registration_no, status, odometer, model_id, brand, model_name, fuel_type, transmission, seats, daily_rate`.
Ordered by `vehicle_id`.

---

## Changing data

### `add_vehicle_model(brand, model_name, fuel_type, transmission, seats, daily_rate)`
Adds a car model to the catalogue. `seats` is a positive int. `daily_rate` is a positive number, rounded to 2 places.
Returns the new row as a dict, including `model_id`.

### `add_vehicle(model_id, registration_no, odometer=0, status="AVAILABLE")`
Adds a car to the fleet. `status` can be AVAILABLE or UNAVAILABLE only.
Returns the new row as a dict, including `vehicle_id`.

Raises: `Vehicle model not found.`, `Registration number already exists.`

### `set_vehicle_status(vehicle_id, new_status)`
Takes a car out of service (`UNAVAILABLE`) or puts it back (`AVAILABLE`). `RENTED` is not allowed here, since pickup and return set that.
Returns a dict: `vehicle_id, old_status, new_status, affected_bookings`.
`affected_bookings` is a list of dicts (`booking_id, customer_id, start_date, end_date`) for the car's future confirmed bookings when the new status is UNAVAILABLE, otherwise `[]`. These bookings are not changed, so staff can move them with `reassign_booking_vehicle`.

Raises: `Vehicle not found.`, `Vehicle has an active rental.`

### `reassign_booking_vehicle(booking_id, new_vehicle_id=None)`
Moves a confirmed booking to another car.
- `new_vehicle_id=None`: picks the lowest-id free car of the **same model**.
- `new_vehicle_id` given: staff choose any car, **including a different model** (for example an upgrade).

Returns a dict: `booking_id, old_vehicle_id, new_vehicle_id`.

Raises: `Booking not found.`, `Booking is not confirmed.`, `Booking already has a rental.`, `No other vehicle of the same model is free for these dates.`, `Cannot reassign to same vehicle.`, `Vehicle not found.`, `Vehicle is not available.`, `Vehicle has another confirmed booking in these dates.`

---

## Notes for the team

- The UI works with ids. Show registration numbers and names in the pages, and keep the id behind the selected row.