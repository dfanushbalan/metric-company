# 📅 Appointment Slot Booker (High-Concurrency Safe)

A full-stack web application designed to allow users to view available appointment slots and book reservations with **absolute zero double-booking**, enforced at the database level even under high concurrent traffic.

---

## 🌟 Key Features

1. **List Available Slots (`GET /slots`)**:
   - Filter by date, status (`AVAILABLE`, `BOOKED`), or view all slots.
   - Quick date filters: Today, Tomorrow, Custom Date.
   - Clean badges and formatted display times.

2. **Book an Appointment (`POST /bookings`)**:
   - Reserve an open slot with customer name, email, and phone number.
   - Validates that slots are in the future and open.

3. **Prevent Double-Booking (`409 Conflict`)**:
   - **Pessimistic Row-Level Locking (`SELECT ... FOR UPDATE`)**: MySQL InnoDB engine locks the specific slot row within an ACID transaction.
   - Any concurrent request attempting to book the identical slot waits until the first transaction commits, then is rejected with `HTTP 409 Conflict`.
   - Built-in live browser concurrency simulator to demonstrate and verify race condition safety.

4. **View Bookings (`GET /bookings`)**:
   - Complete overview of customer appointments with linked slot details.
   - Real-time client-side search across customer name, email, and phone.

5. **Cancel an Appointment (`DELETE /bookings/{id}`)**:
   - Releases the reserved slot back to `AVAILABLE` status automatically.

6. **Validate Appointments**:
   - Rejects past dates and times.
   - Enforces `start_time < end_time`.
   - Prevents overlapping appointment slots on the same date.

---

## 🏗️ Tech Stack

- **Frontend**: HTML5, Vanilla CSS (Modern Luxury Dark Glassmorphism, Google Fonts `Outfit` & `Plus Jakarta Sans`), JavaScript (ES6+ async/await).
- **Backend**: Python 3.9+ with Flask, Flask-CORS, Flask-SQLAlchemy.
- **Database**: MySQL 5.7+ / 8.0+ (with InnoDB engine). *Includes zero-config auto-fallback to SQLite if MySQL is offline during local development.*
- **API Testing**: Postman Collection (v2.1) & Python Multi-threaded Concurrency Test Script.

---

## 📁 Project Structure

```
project/
├── backend/
│   ├── app.py                   # Main Flask REST API & static server
│   ├── config.py                # Database connection & environment manager
│   ├── models.py                # SQLAlchemy Models (AppointmentSlot, Booking)
│   ├── schema.sql               # Pure MySQL DDL schema script
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment configuration template
│   ├── .env                     # Local environment configuration
│   └── test_concurrency.py      # Multi-threaded stress test script
├── frontend/
│   ├── index.html               # Modern Single Page Application
│   ├── css/
│   │   └── style.css            # Custom CSS design system
│   └── js/
│       └── app.js               # Frontend controller & UI race simulator
├── postman/
│   └── Appointment_Slot_Booker.postman_collection.json # Ready-to-import Postman suite
└── README.md                    # Documentation
```

---

## 🗄️ Database Architecture

### `appointment_slots` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique slot identifier |
| `slot_date` | `DATE` | `NOT NULL, INDEX` | Date of the slot |
| `start_time` | `TIME` | `NOT NULL` | Slot start time |
| `end_time` | `TIME` | `NOT NULL` | Slot end time |
| `status` | `VARCHAR(20)`| `NOT NULL DEFAULT 'AVAILABLE'` | `AVAILABLE`, `BOOKED`, `CANCELLED` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |

### `bookings` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | Unique booking identifier |
| `slot_id` | `INT` | `FOREIGN KEY (appointment_slots.id)` | Reserved slot ID |
| `customer_name`| `VARCHAR(100)`| `NOT NULL, INDEX` | Customer name |
| `customer_email`| `VARCHAR(150)`| `NULL` | Customer email |
| `customer_phone`| `VARCHAR(30)` | `NULL` | Customer phone number |
| `booking_status`| `VARCHAR(20)`| `NOT NULL DEFAULT 'CONFIRMED'` | `CONFIRMED` or `CANCELLED` |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Booking timestamp |

---

## ⚡ Concurrency & Double-Booking Prevention Mechanism

The application handles race conditions using a **three-tier defense**:

1. **Pessimistic Row Lock (`SELECT ... FOR UPDATE`)**:
   ```python
   slot = db.session.query(AppointmentSlot).filter(
       AppointmentSlot.id == slot_id
   ).with_for_update().one_or_none()
   ```
   When User A and User B click "Book" at the exact same millisecond:
   - User A's transaction obtains an exclusive lock on slot row #X.
   - User B's transaction is blocked by MySQL InnoDB until User A's transaction completes.
   - User A updates `slot.status = 'BOOKED'`, inserts the booking, and commits.
   - User B is now unblocked, reads the updated `status == 'BOOKED'`, and is instantly rejected with `HTTP 409 Conflict`.

2. **Atomic State Check**:
   The backend explicitly checks `if slot.status != 'AVAILABLE': return 409 Conflict`.

3. **Foreign Key Integrity**:
   Foreign key relationships maintain strict relational integrity with automatic cascade management.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+ installed (`python --version`)
- MySQL Server (Optional: if MySQL is not running, the application automatically uses local SQLite so you can test immediately).

### 2. Configure Environment (`backend/.env`)
Edit `backend/.env` with your MySQL database credentials:
```env
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=appointment_db
AUTO_FALLBACK_SQLITE=True
```

### 3. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Optional: Run MySQL Schema Script
If you prefer creating the MySQL database manually:
```bash
mysql -u root -p < backend/schema.sql
```
*(Note: Flask will also automatically create the database and tables on startup if you have MySQL running).*

### 5. Launch the Application
```bash
python backend/app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

The web interface will display available slots, active bookings, slot creation forms, and the live concurrency simulator.

---

## 🧪 Testing Concurrency & Double-Booking

### Option A: Interactive In-Browser Race Condition Simulator
1. Open `http://127.0.0.1:5000`
2. Click the **"⚡ Concurrency Tester"** tab.
3. Select an available slot.
4. Click **"🚀 Launch 2 Simultaneous Bookings"**.
5. Observe the live console: Request A receives `201 CREATED` and Request B is rejected with `409 CONFLICT`.

### Option B: Automated Multi-Threaded Stress Test Script
Run 10 simultaneous threads attempting to book the exact same slot at the exact same microsecond:
```bash
python backend/test_concurrency.py 10
```
**Expected Output:**
```
Total Requests: 10
  • Successful Bookings (201 Created): 1
  • Rejected Double-Bookings (409 Conflict): 9
  🎉 VERIFICATION PASSED: Double-booking was 100% PREVENTED!
```

---

## 📬 Postman API Testing Guide

1. Open Postman.
2. Click **Import** (top left).
3. Select the file:
   `postman/Appointment_Slot_Booker.postman_collection.json`
4. The collection includes 10 pre-configured requests with automated test assertions:
   - `0. Health Check` (`GET /api/health`)
   - `1. List Available Slots` (`GET /slots?status=AVAILABLE`)
   - `2. List All Slots` (`GET /slots?all=true`)
   - `3. Create a New Slot` (`POST /slots`)
   - `4. Book an Available Slot` (`POST /bookings`)
   - `5. Prevent Double-Booking (Expect 409 Conflict)` (`POST /bookings`)
   - `6. View Bookings` (`GET /bookings`)
   - `7. Cancel a Booking` (`DELETE /bookings/:id`)
   - `8. Validation: Reject Past Date Slot` (`POST /slots`)
   - `9. Validation: Reject Empty Customer Name` (`POST /bookings`)
5. Click **Run Collection** to run all tests in sequence!

---

## 📡 REST API Reference

### 1. List Available Slots
- **`GET /slots`**
- Query Parameters:
  - `status`: Filter by status (`AVAILABLE`, `BOOKED`, `CANCELLED`). Default: `AVAILABLE`.
  - `date`: Filter by date (`YYYY-MM-DD`).
  - `all`: `true` returns all slots regardless of status.
- Response `200 OK`:
  ```json
  {
    "total": 5,
    "slots": [
      {
        "id": 1,
        "slot_date": "2026-10-21",
        "start_time": "09:00",
        "end_time": "09:30",
        "formatted_time": "09:00 AM - 09:30 AM",
        "status": "AVAILABLE"
      }
    ]
  }
  ```

### 2. Create Appointment Slot
- **`POST /slots`**
- Request Body:
  ```json
  {
    "date": "2026-10-22",
    "start_time": "14:00",
    "end_time": "14:30"
  }
  ```
- Response `201 Created` or `409 Conflict` (if overlapping slot exists).

### 3. Book an Available Slot
- **`POST /bookings`**
- Request Body:
  ```json
  {
    "slot_id": 1,
    "customer_name": "Eleanor Vance",
    "customer_email": "eleanor@example.com",
    "customer_phone": "+1 555-0142"
  }
  ```
- Response `201 Created`:
  ```json
  {
    "message": "Appointment booked successfully.",
    "booking": {
      "id": 1,
      "slot_id": 1,
      "customer_name": "Eleanor Vance",
      "booking_status": "CONFIRMED"
    }
  }
  ```
- Response `409 Conflict` (Double booking rejected):
  ```json
  {
    "error": "This slot is already reserved or unavailable (current status: BOOKED). Double-booking is strictly prohibited.",
    "slot_id": 1
  }
  ```

### 4. View Bookings
- **`GET /bookings`**
- Query Parameters:
  - `status`: `CONFIRMED` or `CANCELLED`.
  - `search`: Search query string matching customer name, email, or phone.
- Response `200 OK`.

### 5. Cancel a Booking
- **`DELETE /bookings/{id}`**
- Response `200 OK`:
  ```json
  {
    "message": "Booking #1 has been cancelled successfully. Slot #1 is now available for new bookings."
  }
  ```
