-- ====================================================================
-- Database Schema for Appointment Slot Booker
-- Target: MySQL 5.7+ / 8.0+
-- ====================================================================

-- 1. Create Database if not exists
CREATE DATABASE IF NOT EXISTS appointment_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE appointment_db;

-- 2. Drop existing tables if needed (respecting foreign keys)
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS appointment_slots;

-- 3. Create `appointment_slots` table
-- Tracks available and reserved appointment time slots
CREATE TABLE appointment_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Ensure slot times are valid (start < end)
    CONSTRAINT chk_slot_time CHECK (start_time < end_time),
    
    -- Ensure status is one of the valid enum states
    CONSTRAINT chk_slot_status CHECK (status IN ('AVAILABLE', 'BOOKED', 'CANCELLED')),
    
    -- Prevent duplicate slots with exact same date and times
    CONSTRAINT uq_slot_date_time UNIQUE (slot_date, start_time, end_time),
    
    -- Index for fast queries by date and status
    INDEX idx_slots_date_status (slot_date, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Create `bookings` table
-- Tracks customer bookings for reserved slots
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_id INT NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(150),
    customer_phone VARCHAR(30),
    booking_status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Ensure booking status is valid
    CONSTRAINT chk_booking_status CHECK (booking_status IN ('CONFIRMED', 'CANCELLED')),
    
    -- Foreign key linking to appointment slot
    CONSTRAINT fk_bookings_slot FOREIGN KEY (slot_id) 
        REFERENCES appointment_slots(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
        
    -- Index for fast lookup by customer name or slot
    INDEX idx_bookings_customer (customer_name),
    INDEX idx_bookings_slot (slot_id),
    INDEX idx_bookings_status (booking_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ====================================================================
-- Sample Initial Data for Testing & Demonstration
-- ====================================================================

-- Insert sample slots for tomorrow and upcoming days
INSERT INTO appointment_slots (slot_date, start_time, end_time, status) VALUES
    (CURDATE(), '09:00:00', '09:30:00', 'AVAILABLE'),
    (CURDATE(), '09:30:00', '10:00:00', 'AVAILABLE'),
    (CURDATE(), '10:00:00', '10:30:00', 'AVAILABLE'),
    (CURDATE(), '11:00:00', '11:30:00', 'AVAILABLE'),
    (CURDATE(), '14:00:00', '14:30:00', 'AVAILABLE'),
    (CURDATE(), '15:00:00', '15:30:00', 'AVAILABLE'),
    (DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '09:30:00', 'AVAILABLE'),
    (DATE_ADD(CURDATE(), INTERVAL 1 DAY), '10:00:00', '10:30:00', 'AVAILABLE'),
    (DATE_ADD(CURDATE(), INTERVAL 1 DAY), '11:30:00', '12:00:00', 'AVAILABLE'),
    (DATE_ADD(CURDATE(), INTERVAL 1 DAY), '14:00:00', '14:30:00', 'AVAILABLE'),
    (DATE_ADD(CURDATE(), INTERVAL 1 DAY), '16:00:00', '16:30:00', 'AVAILABLE');
