CREATE DATABASE IF NOT EXISTS busdb;
USE busdb;

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  passenger_name VARCHAR(80) NOT NULL,
  source VARCHAR(40) NOT NULL,
  destination VARCHAR(40) NOT NULL,
  seat_no INT NULL UNIQUE,              -- NULL once cancelled, frees the seat
  status ENUM('CONFIRMED','CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
  fare_amount DECIMAL(10,2) NOT NULL DEFAULT 750.00,
  payment_status VARCHAR(20) NOT NULL DEFAULT 'PAID',
  refund_amount DECIMAL(10,2) NULL,
  transaction_id VARCHAR(64) NULL,
  user_id VARCHAR(80) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_cities CHECK (source <> destination),
  CONSTRAINT chk_seat CHECK (seat_no IS NULL OR seat_no BETWEEN 1 AND 40)
);

CREATE TABLE IF NOT EXISTS schedules (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bus_number VARCHAR(20) NOT NULL,
  source VARCHAR(40) NOT NULL,
  destination VARCHAR(40) NOT NULL,
  departure_time VARCHAR(20) NOT NULL,
  arrival_time VARCHAR(20) NOT NULL,
  bus_type VARCHAR(40) NOT NULL DEFAULT 'AC Semi-Sleeper',
  fare DECIMAL(10,2) NOT NULL DEFAULT 750.00,
  total_seats INT NOT NULL DEFAULT 40,
  CONSTRAINT chk_sched_cities CHECK (source <> destination)
);
