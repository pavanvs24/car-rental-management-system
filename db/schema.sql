DROP TABLE IF EXISTS payment, rental, booking, vehicle, vehicle_model, staff, customer CASCADE;

CREATE TABLE customer (
    customer_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    license_no VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE staff (
    staff_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE vehicle_model (
    model_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    fuel_type VARCHAR(20) NOT NULL CHECK (fuel_type IN ('PETROL','DIESEL','CNG','LPG','ELECTRIC','HYBRID')),
    transmission VARCHAR(20) NOT NULL CHECK (transmission IN ('MANUAL','AUTOMATIC')),
    seats INT NOT NULL CHECK (seats > 0),
    daily_rate INT NOT NULL CHECK (daily_rate > 0)
);

CREATE TABLE vehicle (
    vehicle_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_id INT NOT NULL REFERENCES vehicle_model(model_id),
    registration_no VARCHAR(20) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','RENTED','UNAVAILABLE')),
    odometer INT NOT NULL CHECK (odometer >= 0)
);

CREATE TABLE booking (
    booking_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customer(customer_id),
    vehicle_id INT NOT NULL REFERENCES vehicle(vehicle_id),
    booking_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED' CHECK (status IN ('CONFIRMED','CANCELLED','COMPLETED')),
    CHECK (start_date <= end_date)
);

CREATE TABLE rental (
    rental_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE REFERENCES booking(booking_id),
    pickup_staff_id INT NOT NULL REFERENCES staff(staff_id),
    return_staff_id INT REFERENCES staff(staff_id),
    pickup_date DATE NOT NULL,
    pickup_odometer INT NOT NULL,
    return_date DATE,
    return_odometer INT CHECK (return_odometer > pickup_odometer),
    late_charge NUMERIC(10,2) NOT NULL DEFAULT 0,
    other_charge NUMERIC(10,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','COMPLETED'))
);

CREATE TABLE payment (
    transaction_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id INT NOT NULL REFERENCES booking(booking_id),
    rental_id INT REFERENCES rental(rental_id),
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('ADVANCE','FINAL')),
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    paid_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CHECK ((transaction_type = 'FINAL') = (rental_id IS NOT NULL))
);
