"""
Database Inspector Utility
Allows viewing tables, schema details, and records directly from terminal.
Works with both MySQL and the active SQLite database.
"""

import sys
import os

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from models import db, AppointmentSlot, Booking
from sqlalchemy import text

def inspect_database():
    with app.app_context():
        print("=" * 65)
        print("           DATABASE SCHEMA & DATA INSPECTOR")
        print("=" * 65)
        print(f"Connected to: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("=" * 65)

        # 1. Inspect Appointment Slots Table
        print("\n[TABLE 1: appointment_slots]")
        print("-" * 65)
        slots = AppointmentSlot.query.order_by(AppointmentSlot.slot_date, AppointmentSlot.start_time).all()
        print(f"Total Rows: {len(slots)}")
        print(f"{'ID':<5} | {'Date':<12} | {'Time Range':<22} | {'Status':<10}")
        print("-" * 65)
        for s in slots:
            time_range = f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}"
            print(f"{s.id:<5} | {s.slot_date.strftime('%Y-%m-%d'):<12} | {time_range:<22} | {s.status:<10}")

        # 2. Inspect Bookings Table
        print("\n[TABLE 2: bookings]")
        print("-" * 65)
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        print(f"Total Rows: {len(bookings)}")
        print(f"{'ID':<5} | {'Customer Name':<20} | {'Slot ID':<8} | {'Status':<10} | {'Phone / Email'}")
        print("-" * 65)
        if not bookings:
            print("  (No bookings recorded yet)")
        for b in bookings:
            contact = b.customer_phone or b.customer_email or "N/A"
            print(f"{b.id:<5} | {b.customer_name:<20} | #{b.slot_id:<7} | {b.booking_status:<10} | {contact}")

        print("=" * 65)
        print("  Database is active and healthy.")
        print("=" * 65)

if __name__ == '__main__':
    inspect_database()
