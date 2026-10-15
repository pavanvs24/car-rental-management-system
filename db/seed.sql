-- Run schema.sql first. IDs below assume freshly created tables.
-- All test accounts use the password: password123

INSERT INTO staff (full_name, email, password_hash) VALUES
('Staff One', 'staff@carrental.com', '$2b$12$c/98nbQKhdKDpGRI6fcef.h/i1jwe/Zc.uxLfxka7RKS76rbu9ly6'),
('Staff Two', 'staff2@carrental.com', '$2b$12$c/98nbQKhdKDpGRI6fcef.h/i1jwe/Zc.uxLfxka7RKS76rbu9ly6');

INSERT INTO customer (full_name, email, password_hash, phone, license_no) VALUES
('Asha Rao', 'asha@example.com', '$2b$12$c/98nbQKhdKDpGRI6fcef.h/i1jwe/Zc.uxLfxka7RKS76rbu9ly6', '9876500001', 'DL-0001'),
('Ravi Kumar', 'ravi@example.com', '$2b$12$c/98nbQKhdKDpGRI6fcef.h/i1jwe/Zc.uxLfxka7RKS76rbu9ly6', '9876500002', 'DL-0002'),
('Meera Nair', 'meera@example.com', '$2b$12$c/98nbQKhdKDpGRI6fcef.h/i1jwe/Zc.uxLfxka7RKS76rbu9ly6', '9876500003', 'DL-0003');

INSERT INTO vehicle_model (brand, model_name, fuel_type, transmission, seats, daily_rate) VALUES
('Maruti', 'Swift', 'PETROL', 'MANUAL', 5, 2000),
('Hyundai', 'Creta', 'DIESEL', 'AUTOMATIC', 5, 3500),
('Toyota', 'Innova', 'DIESEL', 'MANUAL', 7, 4000),
('Tata', 'Nexon EV', 'ELECTRIC', 'AUTOMATIC', 5, 3000);

INSERT INTO vehicle (model_id, registration_no, status, odometer) VALUES
(1, 'KA01AB1001', 'AVAILABLE', 10450),
(1, 'KA01AB1002', 'AVAILABLE', 5000),
(2, 'KA01AB2001', 'RENTED', 25000),
(3, 'KA01AB3001', 'AVAILABLE', 40000),
(4, 'KA01AB4001', 'AVAILABLE', 3000),
(1, 'KA01AB1003', 'UNAVAILABLE', 60000);

-- Booking 1: past, completed, returned 1 day late
-- Booking 2: car currently out with the customer
-- Booking 3: future booking, not picked up yet
INSERT INTO booking (customer_id, vehicle_id, booking_date, start_date, end_date, status) VALUES
(1, 1, CURRENT_DATE - 15, CURRENT_DATE - 10, CURRENT_DATE - 8, 'COMPLETED'),
(2, 3, CURRENT_DATE - 5,  CURRENT_DATE - 1,  CURRENT_DATE + 2, 'CONFIRMED'),
(3, 4, CURRENT_DATE,      CURRENT_DATE + 5,  CURRENT_DATE + 8, 'CONFIRMED');

INSERT INTO rental (booking_id, pickup_staff_id, return_staff_id, pickup_date, pickup_odometer, return_date, return_odometer, late_charge, other_charge, status) VALUES
(1, 1, 2, CURRENT_DATE - 10, 10000, CURRENT_DATE - 7, 10450, 500, 0, 'COMPLETED'),
(2, 1, NULL, CURRENT_DATE - 1, 25000, NULL, NULL, 0, 0, 'ACTIVE');

INSERT INTO payment (booking_id, rental_id, transaction_type, amount, paid_at) VALUES
(1, NULL, 'ADVANCE', 1000, NOW() - INTERVAL '15 days'),
(1, 1, 'FINAL', 5500, NOW() - INTERVAL '7 days'),
(2, NULL, 'ADVANCE', 1500, NOW() - INTERVAL '5 days'),
(3, NULL, 'ADVANCE', 2000, NOW());