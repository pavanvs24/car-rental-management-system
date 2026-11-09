-- ============================================================
-- Car Rental Management System: report queries
-- Run after schema.sql and seed.sql.
-- Each query is labelled with the RDBMS concept it shows.
-- ============================================================


-- ------------------------------------------------------------
-- Query 1: Revenue per vehicle model
-- Concept: JOIN, GROUP BY, SUM
-- Purpose: which models earn the most
-- Check:   the sum of total_revenue equals SELECT SUM(amount) FROM payment;
-- ------------------------------------------------------------
SELECT vm.model_id,
       vm.brand,
       vm.model_name,
       COUNT(p.transaction_id) AS payments,
       SUM(p.amount)           AS total_revenue
FROM payment p
JOIN booking       b  ON b.booking_id = p.booking_id
JOIN vehicle       v  ON v.vehicle_id = b.vehicle_id
JOIN vehicle_model vm ON vm.model_id  = v.model_id
GROUP BY vm.model_id, vm.brand, vm.model_name
ORDER BY total_revenue DESC;


-- ------------------------------------------------------------
-- Query 2: Full booking report
-- Concept: multi-table JOIN (4 tables) + LEFT JOIN + aggregate
-- Purpose: one row per booking with customer, car and amount paid
-- Note:    LEFT JOIN on payment keeps bookings that have no payment
-- ------------------------------------------------------------
SELECT b.booking_id,
       c.full_name                        AS customer,
       vm.brand || ' ' || vm.model_name   AS vehicle,
       v.registration_no,
       b.start_date,
       b.end_date,
       b.status,
       COALESCE(SUM(p.amount), 0)         AS total_paid
FROM booking b
JOIN customer      c  ON c.customer_id = b.customer_id
JOIN vehicle       v  ON v.vehicle_id  = b.vehicle_id
JOIN vehicle_model vm ON vm.model_id   = v.model_id
LEFT JOIN payment  p  ON p.booking_id  = b.booking_id
GROUP BY b.booking_id, c.full_name, vm.brand, vm.model_name,
         v.registration_no, b.start_date, b.end_date, b.status
ORDER BY b.booking_id;


-- ------------------------------------------------------------
-- Query 3: Repeat customers (2 or more bookings)
-- Concept: GROUP BY with HAVING
-- Purpose: HAVING filters groups, WHERE filters rows
-- ------------------------------------------------------------
SELECT c.customer_id,
       c.full_name,
       COUNT(b.booking_id) AS bookings
FROM customer c
JOIN booking b ON b.customer_id = c.customer_id
GROUP BY c.customer_id, c.full_name
HAVING COUNT(b.booking_id) >= 2
ORDER BY bookings DESC, c.full_name;


-- ------------------------------------------------------------
-- Query 4: Vehicles that were never booked
-- Concept: correlated subquery with NOT EXISTS
-- Purpose: find idle cars
-- ------------------------------------------------------------
SELECT v.vehicle_id,
       v.registration_no,
       vm.brand,
       vm.model_name
FROM vehicle v
JOIN vehicle_model vm ON vm.model_id = v.model_id
WHERE NOT EXISTS (
    SELECT 1
    FROM booking b
    WHERE b.vehicle_id = v.vehicle_id
)
ORDER BY v.vehicle_id;


-- ------------------------------------------------------------
-- Query 5: Overdue rentals today, with days overdue
-- Concept: date arithmetic (date - date gives a number of days)
-- Purpose: cars still out after the booking's end_date
-- ------------------------------------------------------------
SELECT r.rental_id,
       c.full_name,
       v.registration_no,
       b.end_date,
       CURRENT_DATE - b.end_date AS days_overdue
FROM rental r
JOIN booking  b ON b.booking_id  = r.booking_id
JOIN customer c ON c.customer_id = b.customer_id
JOIN vehicle  v ON v.vehicle_id  = b.vehicle_id
WHERE r.status = 'ACTIVE'
  AND b.end_date < CURRENT_DATE
ORDER BY days_overdue DESC;


-- ------------------------------------------------------------
-- Query 6: Every vehicle with its booking count, including 0
-- Concept: LEFT JOIN
-- Purpose: an INNER JOIN would hide vehicles with no bookings
-- ------------------------------------------------------------
SELECT v.vehicle_id,
       v.registration_no,
       vm.brand,
       vm.model_name,
       COUNT(b.booking_id) AS booking_count
FROM vehicle v
JOIN vehicle_model vm ON vm.model_id = v.model_id
LEFT JOIN booking  b  ON b.vehicle_id = v.vehicle_id
GROUP BY v.vehicle_id, v.registration_no, vm.brand, vm.model_name
ORDER BY booking_count DESC, v.vehicle_id;


-- ------------------------------------------------------------
-- Query 7: booking_summary view
-- Concept: VIEW (a saved query that behaves like a table)
-- Purpose: one reusable report of every booking with its cost
--          and how much has been paid
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW booking_summary AS
SELECT b.booking_id,
       c.full_name                              AS customer,
       vm.brand || ' ' || vm.model_name         AS vehicle,
       v.registration_no,
       b.start_date,
       b.end_date,
       (b.end_date - b.start_date + 1)          AS days,
       vm.daily_rate,
       (b.end_date - b.start_date + 1) * vm.daily_rate AS total_cost,
       b.status,
       (SELECT COALESCE(SUM(p.amount), 0)
          FROM payment p
         WHERE p.booking_id = b.booking_id)     AS total_paid
FROM booking b
JOIN customer      c  ON c.customer_id = b.customer_id
JOIN vehicle       v  ON v.vehicle_id  = b.vehicle_id
JOIN vehicle_model vm ON vm.model_id   = v.model_id;

-- Using the view:
SELECT * FROM booking_summary ORDER BY booking_id;