# Car Rental Platform: Relational Schema

Database: PostgreSQL. Seven tables.

## Tables

### customer
| Column | Type | Constraints |
|---|---|---|
| customer_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| full_name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(100) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| phone | VARCHAR(20) | NOT NULL |
| license_no | VARCHAR(30) | NOT NULL, UNIQUE |

### staff
| Column | Type | Constraints |
|---|---|---|
| staff_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| full_name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(100) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |

### vehicle_model
| Column | Type | Constraints |
|---|---|---|
| model_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| brand | VARCHAR(50) | NOT NULL |
| model_name | VARCHAR(50) | NOT NULL |
| fuel_type | VARCHAR(20) | NOT NULL, CHECK in (PETROL, DIESEL, CNG, LPG, ELECTRIC, HYBRID) |
| transmission | VARCHAR(20) | NOT NULL, CHECK in (MANUAL, AUTOMATIC) |
| seats | INT | NOT NULL, CHECK (seats > 0) |
| daily_rate | NUMERIC(10,2) | NOT NULL, CHECK (daily_rate > 0) |

### vehicle
| Column | Type | Constraints |
|---|---|---|
| vehicle_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| model_id | INT | NOT NULL, FK → vehicle_model(model_id) |
| registration_no | VARCHAR(20) | NOT NULL, UNIQUE |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'AVAILABLE', CHECK in (AVAILABLE, RENTED, UNAVAILABLE) |
| odometer | INT | NOT NULL, CHECK (odometer >= 0) |

### booking
| Column | Type | Constraints |
|---|---|---|
| booking_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| customer_id | INT | NOT NULL, FK → customer(customer_id) |
| vehicle_id | INT | NOT NULL, FK → vehicle(vehicle_id) |
| booking_date | DATE | NOT NULL, DEFAULT CURRENT_DATE |
| start_date | DATE | NOT NULL |
| end_date | DATE | NOT NULL, CHECK (start_date <= end_date) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'CONFIRMED', CHECK in (CONFIRMED, CANCELLED, COMPLETED) |

### rental
| Column | Type | Constraints |
|---|---|---|
| rental_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| booking_id | INT | NOT NULL, UNIQUE, FK → booking(booking_id) |
| pickup_staff_id | INT | NOT NULL, FK → staff(staff_id) |
| return_staff_id | INT | NULL until return, FK → staff(staff_id) |
| pickup_date | DATE | NOT NULL |
| pickup_odometer | INT | NOT NULL |
| return_date | DATE | NULL until return |
| return_odometer | INT | NULL until return, CHECK (return_odometer > pickup_odometer) |
| late_charge | NUMERIC(10,2) | NOT NULL, DEFAULT 0 |
| other_charge | NUMERIC(10,2) | NOT NULL, DEFAULT 0 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'ACTIVE', CHECK in (ACTIVE, COMPLETED) |

### transaction
| Column | Type | Constraints |
|---|---|---|
| transaction_id | INT GENERATED ALWAYS AS IDENTITY | PRIMARY KEY |
| booking_id | INT | NOT NULL, FK → booking(booking_id) |
| rental_id | INT | NULL for advance, FK → rental(rental_id) |
| transaction_type | VARCHAR(10) | NOT NULL, CHECK in (ADVANCE, FINAL) |
| amount | NUMERIC(10,2) | NOT NULL, CHECK (amount > 0) |
| paid_at | TIMESTAMP | NOT NULL, DEFAULT NOW() |

Table-level check: `(transaction_type = 'FINAL') = (rental_id IS NOT NULL)`.

`transaction` is a reserved word in SQL. If it causes trouble, quote it as `"transaction"` or name the table `payment`.

## Nullable columns

Everything is NOT NULL except `rental.return_staff_id`, `rental.return_date`, `rental.return_odometer` and `transaction.rental_id`. The first three are filled when the car comes back, and `rental_id` is filled only for the final payment.

## Notes for the backend

1. **Availability search.** `start_date` and `end_date` are both inclusive, so a booking can start and end on the same day (pickup and return on the same day). A vehicle can only be used by one booking per day: the next booking can start on the day after the previous booking's `end_date`. A vehicle is free for `[s, e]` when no booking for it with status `CONFIRMED` satisfies `existing.start_date <= e AND existing.end_date >= s`. Also exclude vehicles whose status is UNAVAILABLE. The database does not enforce the no-overlap rule on its own, so the backend (or a trigger) must check it before every insert. Billable days are `end_date - start_date + 1`.
2. **Vehicle status is physical state only.** Future availability comes from bookings, not from `vehicle.status`.
3. **Creating a booking** inserts the booking and its ADVANCE transaction (`rental_id` NULL) in one database transaction.
4. **Pickup** inserts the rental row (with `pickup_staff_id`, `pickup_date`, `pickup_odometer`) and sets the vehicle status to RENTED.
5. **Return** updates the rental with `return_staff_id`, `return_date`, `return_odometer` and the charges, inserts the FINAL transaction with `rental_id`, and sets the vehicle status back to AVAILABLE.
6. **Late fee** is computed in the backend from `return_date` against the booking's `end_date` and stored in `late_charge`, so later rate changes don't alter past bills.
7. **Late return blocking the next booking:** staff move that booking to another free vehicle of the same model with `UPDATE booking SET vehicle_id = ...`.
8. **Customers and staff are separate tables** with separate login routes. Never store plain passwords, only hashes.
