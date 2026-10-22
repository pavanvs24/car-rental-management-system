-- Dates are examples. The Python code passes real values instead.

-- 1. Available vehicles for a date range (dates inclusive)
SELECT v.vehicle_id, m.brand, m.model_name, m.fuel_type, m.transmission, m.seats, m.daily_rate
FROM vehicle v
JOIN vehicle_model m ON m.model_id = v.model_id
WHERE v.status <> 'UNAVAILABLE'
  AND NOT EXISTS (
    SELECT 1 FROM booking b
    WHERE b.vehicle_id = v.vehicle_id
      AND b.status = 'CONFIRMED'
      AND b.start_date <= CURRENT_DATE + 7   -- new end date
      AND b.end_date   >= CURRENT_DATE + 6   -- new start date
  );

-- 2. Create a booking with its advance payment (one statement, so both or neither)
WITH new_booking AS (
  INSERT INTO booking (customer_id, vehicle_id, start_date, end_date)
  VALUES (1, 2, CURRENT_DATE + 1, CURRENT_DATE + 3)
  RETURNING booking_id
)
INSERT INTO payment (booking_id, transaction_type, amount)
SELECT booking_id, 'ADVANCE', 1000 FROM new_booking;

-- 3. Confirm pickup (booking 3, staff 1)
BEGIN;
INSERT INTO rental (booking_id, pickup_staff_id, pickup_date, pickup_odometer)
VALUES (3, 1, CURRENT_DATE, 40000);
UPDATE vehicle SET status = 'RENTED'
WHERE vehicle_id = (SELECT vehicle_id FROM booking WHERE booking_id = 3);
COMMIT;

-- 4. Process a return: staff enters the registration number
WITH target AS (
  SELECT r.rental_id, r.booking_id, b.vehicle_id
  FROM rental r
  JOIN booking b ON b.booking_id = r.booking_id
  JOIN vehicle v ON v.vehicle_id = b.vehicle_id
  WHERE v.registration_no = 'KA01AB2001' AND r.status = 'ACTIVE'
),
ret AS (
  UPDATE rental
  SET return_staff_id = 2, return_date = CURRENT_DATE, return_odometer = 25400,
      late_charge = 0, other_charge = 0, status = 'COMPLETED'
  WHERE rental_id = (SELECT rental_id FROM target)
  RETURNING rental_id, booking_id
),
pay AS (
  INSERT INTO payment (booking_id, rental_id, transaction_type, amount)
  SELECT booking_id, rental_id, 'FINAL', 4000 FROM ret
),
veh AS (
  UPDATE vehicle SET status = 'AVAILABLE', odometer = 25400
  WHERE vehicle_id = (SELECT vehicle_id FROM target)
)
UPDATE booking SET status = 'COMPLETED'
WHERE booking_id = (SELECT booking_id FROM target);

-- 5. A customer's bookings
SELECT b.booking_id, m.brand, m.model_name, v.registration_no, b.start_date, b.end_date, b.status
FROM booking b
JOIN vehicle v ON v.vehicle_id = b.vehicle_id
JOIN vehicle_model m ON m.model_id = v.model_id
WHERE b.customer_id = 1
ORDER BY b.start_date DESC;

-- 6. Login lookups (the app then checks the password against password_hash)
SELECT customer_id, full_name, password_hash FROM customer WHERE email = 'asha@example.com';
SELECT staff_id, full_name, password_hash FROM staff WHERE email = 'staff@carrental.com';

