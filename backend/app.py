import os
import logging
from datetime import datetime, date, time, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError

from config import Config, logger
from models import db, AppointmentSlot, Booking

def create_app():
    # Setup static folder pointing to frontend directory
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = Config.SECRET_KEY

    # Enable CORS for all routes so external frontends or Postman can access smoothly
    CORS(app)

    db.init_app(app)

    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        # Seed initial sample slots if table is empty
        seed_default_data_if_empty()

    # =========================================================================
    # Helpers
    # =========================================================================
    def parse_time(time_str):
        """Parse time from 'HH:MM' or 'HH:MM:SS' string"""
        if not time_str:
            return None
        time_str = time_str.strip()
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                pass
        return None

    def parse_date(date_str):
        """Parse date from 'YYYY-MM-DD' string"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            return None

    # =========================================================================
    # Frontend Routes
    # =========================================================================
    @app.route('/')
    def serve_frontend():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/favicon.ico')
    def favicon():
        return ('', 204)

    @app.route('/<path:path>')
    def serve_static_files(path):
        target = os.path.join(app.static_folder, path)
        if os.path.isfile(target):
            return send_from_directory(app.static_folder, path)
        if path.startswith(('api', 'slots', 'bookings')):
            return jsonify({'error': f'Endpoint /{path} not found.'}), 404
        return send_from_directory(app.static_folder, 'index.html')

    # =========================================================================
    # Health & System Status Endpoint
    # =========================================================================
    @app.route('/api/health', methods=['GET'])
    def health_check():
        db_engine = str(db.engine.url)
        # Redact password if present
        if '@' in db_engine:
            prefix, rest = db_engine.split('@', 1)
            driver_user = prefix.split(':')[0] + "://" + prefix.split(':')[1].split('//')[-1]
            db_engine = f"{driver_user}:****@{rest}"

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_engine,
            'message': 'Appointment Slot Booker API is running'
        }), 200

    # =========================================================================
    # Slot Management Endpoints
    # =========================================================================
    @app.route('/slots', methods=['GET'])
    def list_slots():
        """
        GET /slots
        List appointment slots.
        Query params:
          - status: 'AVAILABLE', 'BOOKED', 'CANCELLED' (defaults to 'AVAILABLE' unless 'all=true')
          - date: 'YYYY-MM-DD'
          - all: 'true' (lists all slots regardless of status)
        """
        status_param = request.args.get('status')
        date_param = request.args.get('date')
        show_all = request.args.get('all', 'false').lower() in ('true', '1')

        query = AppointmentSlot.query

        if date_param:
            parsed_d = parse_date(date_param)
            if not parsed_d:
                return jsonify({'error': 'Invalid date format. Expected YYYY-MM-DD.'}), 400
            query = query.filter(AppointmentSlot.slot_date == parsed_d)

        if not show_all:
            if status_param:
                query = query.filter(AppointmentSlot.status == status_param.upper())
            else:
                # Default to AVAILABLE slots
                query = query.filter(AppointmentSlot.status == 'AVAILABLE')
        elif status_param:
            query = query.filter(AppointmentSlot.status == status_param.upper())

        # Sort chronologically
        slots = query.order_by(AppointmentSlot.slot_date.asc(), AppointmentSlot.start_time.asc()).all()

        return jsonify({
            'total': len(slots),
            'slots': [slot.to_dict() for slot in slots]
        }), 200

    @app.route('/slots', methods=['POST'])
    def create_slot():
        """
        POST /slots
        Create a new appointment slot.
        JSON payload:
          - date / slot_date: 'YYYY-MM-DD'
          - start_time: 'HH:MM' (or 'HH:MM:SS')
          - end_time: 'HH:MM' (or 'HH:MM:SS')
        """
        data = request.get_json(silent=True) or {}
        date_input = data.get('slot_date') or data.get('date')
        start_input = data.get('start_time')
        end_input = data.get('end_time')

        if not date_input or not start_input or not end_input:
            return jsonify({
                'error': 'Missing required fields. Please provide date, start_time, and end_time.'
            }), 400

        parsed_date = parse_date(date_input)
        if not parsed_date:
            return jsonify({'error': 'Invalid date format. Expected YYYY-MM-DD.'}), 400

        # Reject past dates
        if parsed_date < date.today():
            return jsonify({'error': 'Cannot create an appointment slot in the past.'}), 400

        parsed_start = parse_time(start_input)
        parsed_end = parse_time(end_input)

        if not parsed_start or not parsed_end:
            return jsonify({'error': 'Invalid time format. Expected HH:MM or HH:MM:SS.'}), 400

        if parsed_start >= parsed_end:
            return jsonify({'error': 'start_time must be strictly before end_time.'}), 400

        # Check for overlapping slots on the same date
        # Two time intervals [A_start, A_end] and [B_start, B_end] overlap if A_start < B_end and A_end > B_start
        overlapping_slot = AppointmentSlot.query.filter(
            AppointmentSlot.slot_date == parsed_date,
            AppointmentSlot.status != 'CANCELLED',
            AppointmentSlot.start_time < parsed_end,
            AppointmentSlot.end_time > parsed_start
        ).first()

        if overlapping_slot:
            return jsonify({
                'error': f'Slot overlaps with an existing slot #{overlapping_slot.id} ({overlapping_slot.start_time.strftime("%H:%M")} - {overlapping_slot.end_time.strftime("%H:%M")}).'
            }), 409

        try:
            new_slot = AppointmentSlot(
                slot_date=parsed_date,
                start_time=parsed_start,
                end_time=parsed_end,
                status='AVAILABLE'
            )
            db.session.add(new_slot)
            db.session.commit()

            return jsonify({
                'message': 'Appointment slot created successfully.',
                'slot': new_slot.to_dict()
            }), 201
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'A slot with this exact date and time already exists.'}), 409
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating slot: {e}")
            return jsonify({'error': 'Failed to create slot due to internal error.'}), 500

    @app.route('/slots/batch', methods=['POST'])
    def batch_create_slots():
        """
        POST /slots/batch
        Utility endpoint to generate multiple recurring slots for a given day.
        JSON payload:
          - date: 'YYYY-MM-DD'
          - start_hour: int (e.g. 9)
          - end_hour: int (e.g. 17)
          - duration_minutes: int (default 30)
        """
        data = request.get_json(silent=True) or {}
        date_input = data.get('date') or data.get('slot_date')
        start_hour = int(data.get('start_hour', 9))
        end_hour = int(data.get('end_hour', 17))
        duration = int(data.get('duration_minutes', 30))

        parsed_date = parse_date(date_input)
        if not parsed_date or parsed_date < date.today():
            return jsonify({'error': 'Invalid date or date in past.'}), 400

        if start_hour >= end_hour or duration <= 0:
            return jsonify({'error': 'Invalid hour range or duration.'}), 400

        current_dt = datetime.combine(parsed_date, time(start_hour, 0))
        end_dt = datetime.combine(parsed_date, time(end_hour, 0))

        created_count = 0
        skipped_count = 0

        while current_dt + timedelta(minutes=duration) <= end_dt:
            slot_s = current_dt.time()
            slot_e = (current_dt + timedelta(minutes=duration)).time()

            # Check overlap
            exists = AppointmentSlot.query.filter(
                AppointmentSlot.slot_date == parsed_date,
                AppointmentSlot.status != 'CANCELLED',
                AppointmentSlot.start_time < slot_e,
                AppointmentSlot.end_time > slot_s
            ).first()

            if not exists:
                new_slot = AppointmentSlot(
                    slot_date=parsed_date,
                    start_time=slot_s,
                    end_time=slot_e,
                    status='AVAILABLE'
                )
                db.session.add(new_slot)
                created_count += 1
            else:
                skipped_count += 1

            current_dt += timedelta(minutes=duration)

        db.session.commit()
        return jsonify({
            'message': f'Batch slot creation completed. Created: {created_count}, Skipped (existing/overlaps): {skipped_count}.',
            'created_count': created_count,
            'skipped_count': skipped_count
        }), 201

    # =========================================================================
    # Booking Management Endpoints (Double-Booking Prevention Enforced)
    # =========================================================================
    @app.route('/bookings', methods=['POST'])
    def book_slot():
        """
        POST /bookings
        Book an available appointment slot.
        Enforces strict double-booking prevention using database transactions
        and pessimistic row locking (SELECT ... FOR UPDATE).
        JSON payload:
          - slot_id: int
          - customer_name: string
          - customer_email: optional string
          - customer_phone: optional string
        """
        data = request.get_json(silent=True) or {}
        slot_id = data.get('slot_id')
        customer_name = data.get('customer_name')
        customer_email = data.get('customer_email', '').strip()
        customer_phone = data.get('customer_phone', '').strip()

        if not slot_id:
            return jsonify({'error': 'slot_id is required.'}), 400

        if not customer_name or not str(customer_name).strip():
            return jsonify({'error': 'customer_name is required and cannot be empty.'}), 400

        customer_name = str(customer_name).strip()

        # Database transaction with Pessimistic Locking (SELECT ... FOR UPDATE)
        # Even under high concurrent requests, this locks the slot row in the database
        # until the transaction completes, preventing any race condition.
        try:
            # Begin explicit transaction
            slot = db.session.query(AppointmentSlot).filter(
                AppointmentSlot.id == slot_id
            ).with_for_update().one_or_none()

            if not slot:
                db.session.rollback()
                return jsonify({'error': f'Slot with ID {slot_id} not found.'}), 404

            # Critical validation: Prevent double booking
            if slot.status != 'AVAILABLE':
                db.session.rollback()
                return jsonify({
                    'error': f'This slot is already reserved or unavailable (current status: {slot.status}). Double-booking is strictly prohibited.',
                    'slot_id': slot_id,
                    'current_status': slot.status
                }), 409  # 409 Conflict

            # Validate that the slot has not already expired (past date/time)
            now = datetime.now()
            slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
            if slot_datetime < now:
                db.session.rollback()
                return jsonify({'error': 'Cannot book an appointment slot that has already passed.'}), 400

            # Atomic status update
            slot.status = 'BOOKED'

            # Create booking record
            booking = Booking(
                slot_id=slot.id,
                customer_name=customer_name,
                customer_email=customer_email or None,
                customer_phone=customer_phone or None,
                booking_status='CONFIRMED'
            )
            db.session.add(booking)
            db.session.commit()

            logger.info(f"Booking #{booking.id} confirmed for slot #{slot.id} by '{customer_name}'.")

            return jsonify({
                'message': 'Appointment booked successfully.',
                'booking': booking.to_dict()
            }), 201

        except IntegrityError as ie:
            db.session.rollback()
            logger.warning(f"Integrity error during booking attempt for slot #{slot_id}: {ie}")
            return jsonify({
                'error': 'This slot was just booked by another user. Double-booking prevented.',
                'slot_id': slot_id
            }), 409
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error booking slot #{slot_id}: {e}")
            return jsonify({'error': 'Failed to complete booking due to a server error.'}), 500

    @app.route('/bookings', methods=['GET'])
    def list_bookings():
        """
        GET /bookings
        View bookings with associated slot details.
        Query params:
          - status: 'CONFIRMED', 'CANCELLED' (default: all)
          - search: search by customer name, email, or phone
        """
        status_param = request.args.get('status')
        search_param = request.args.get('search')

        query = Booking.query.join(AppointmentSlot)

        if status_param:
            query = query.filter(Booking.booking_status == status_param.upper())

        if search_param:
            search_term = f"%{search_param.strip()}%"
            query = query.filter(
                or_(
                    Booking.customer_name.ilike(search_term),
                    Booking.customer_email.ilike(search_term),
                    Booking.customer_phone.ilike(search_term)
                )
            )

        # Sort by creation time descending
        bookings = query.order_by(Booking.created_at.desc()).all()

        return jsonify({
            'total': len(bookings),
            'bookings': [booking.to_dict() for booking in bookings]
        }), 200

    @app.route('/bookings/<int:booking_id>', methods=['DELETE'])
    def cancel_booking(booking_id):
        """
        DELETE /bookings/<id>
        Cancel an existing booking and release the reserved slot back to AVAILABLE.
        """
        try:
            booking = db.session.query(Booking).filter(
                Booking.id == booking_id
            ).with_for_update().one_or_none()

            if not booking:
                db.session.rollback()
                return jsonify({'error': f'Booking #{booking_id} not found.'}), 404

            if booking.booking_status == 'CANCELLED':
                db.session.rollback()
                return jsonify({'error': f'Booking #{booking_id} is already cancelled.'}), 400

            # Update booking status
            booking.booking_status = 'CANCELLED'

            # Release the slot back to AVAILABLE
            slot = db.session.query(AppointmentSlot).filter(
                AppointmentSlot.id == booking.slot_id
            ).with_for_update().one_or_none()

            if slot and slot.status == 'BOOKED':
                slot.status = 'AVAILABLE'
                logger.info(f"Slot #{slot.id} released back to AVAILABLE after booking #{booking_id} cancellation.")

            db.session.commit()

            return jsonify({
                'message': f'Booking #{booking_id} has been cancelled successfully. Slot #{booking.slot_id} is now available for new bookings.',
                'booking': booking.to_dict()
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cancelling booking #{booking_id}: {e}")
            return jsonify({'error': 'Failed to cancel booking due to internal error.'}), 500

    # =========================================================================
    # Reset / Demo Seed Endpoint
    # =========================================================================
    @app.route('/api/reset-demo', methods=['POST'])
    def reset_demo():
        """Reset demo database with fresh slots and sample bookings"""
        try:
            Booking.query.delete()
            AppointmentSlot.query.delete()
            db.session.commit()
            seed_default_data_if_empty(force=True)
            return jsonify({'message': 'Demo data reset successfully.'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    return app

def seed_default_data_if_empty(force=False):
    """Seed initial appointment slots and sample confirmed booking"""
    if not force and AppointmentSlot.query.first():
        return

    today = date.today()
    sample_slots = [
        # Today slots
        (today, time(9, 0), time(9, 30)),
        (today, time(9, 30), time(10, 0)),
        (today, time(10, 0), time(10, 30)),
        (today, time(11, 0), time(11, 30)),
        (today, time(14, 0), time(14, 30)),
        (today, time(15, 0), time(15, 30)),
        (today, time(16, 0), time(16, 30)),
        # Tomorrow slots
        (today + timedelta(days=1), time(9, 0), time(9, 30)),
        (today + timedelta(days=1), time(10, 0), time(10, 30)),
        (today + timedelta(days=1), time(11, 30), time(12, 0)),
        (today + timedelta(days=1), time(14, 0), time(14, 30)),
        (today + timedelta(days=1), time(15, 30), time(16, 0)),
        (today + timedelta(days=1), time(16, 30), time(17, 0)),
        # Day after tomorrow
        (today + timedelta(days=2), time(10, 0), time(10, 30)),
        (today + timedelta(days=2), time(11, 0), time(11, 30)),
        (today + timedelta(days=2), time(14, 0), time(14, 30)),
        (today + timedelta(days=2), time(15, 0), time(15, 30)),
    ]

    slots_to_add = []
    for s_date, s_start, s_end in sample_slots:
        slot = AppointmentSlot(
            slot_date=s_date,
            start_time=s_start,
            end_time=s_end,
            status='AVAILABLE'
        )
        slots_to_add.append(slot)

    db.session.add_all(slots_to_add)
    db.session.commit()

    # Pre-book one slot as sample
    first_slot = AppointmentSlot.query.first()
    if first_slot:
        first_slot.status = 'BOOKED'
        sample_booking = Booking(
            slot_id=first_slot.id,
            customer_name="Sarah Jenkins",
            customer_email="sarah.jenkins@example.com",
            customer_phone="+1 (555) 234-5678",
            booking_status='CONFIRMED'
        )
        db.session.add(sample_booking)
        db.session.commit()

    logger.info("Database seeded with sample slots and initial booking.")

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1')
    print("=" * 60)
    print(f"[*] Appointment Slot Booker API running on http://127.0.0.1:{port}")
    print(f"[*] Serving Frontend from: {app.static_folder}")
    print(f"[*] Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug)
