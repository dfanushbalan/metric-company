from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AppointmentSlot(db.Model):
    __tablename__ = 'appointment_slots'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slot_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='AVAILABLE', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='slot', lazy=True, cascade='all, delete-orphan')

    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('slot_date', 'start_time', 'end_time', name='uq_slot_date_time'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'slot_date': self.slot_date.strftime('%Y-%m-%d') if self.slot_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'formatted_time': f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}" if (self.start_time and self.end_time) else '',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('appointment_slots.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False, index=True)
    customer_email = db.Column(db.String(150), nullable=True)
    customer_phone = db.Column(db.String(30), nullable=True)
    booking_status = db.Column(db.String(20), nullable=False, default='CONFIRMED', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        data = {
            'id': self.id,
            'slot_id': self.slot_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'booking_status': self.booking_status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

        # Include slot details if relationship is populated
        if self.slot:
            data['slot'] = {
                'id': self.slot.id,
                'slot_date': self.slot.slot_date.strftime('%Y-%m-%d') if self.slot.slot_date else None,
                'start_time': self.slot.start_time.strftime('%H:%M') if self.slot.start_time else None,
                'end_time': self.slot.end_time.strftime('%H:%M') if self.slot.end_time else None,
                'formatted_time': f"{self.slot.start_time.strftime('%I:%M %p')} - {self.slot.end_time.strftime('%I:%M %p')}" if (self.slot.start_time and self.slot.end_time) else '',
                'status': self.slot.status
            }
        return data
