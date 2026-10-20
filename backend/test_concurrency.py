"""
Concurrency & Double-Booking Stress Test Script
Objective: Validate that simultaneous booking attempts on the exact same slot
result in exactly ONE successful booking (HTTP 201) and all other concurrent
attempts being cleanly rejected with HTTP 409 Conflict.
"""

import sys
import time
import requests
import concurrent.futures

BASE_URL = "http://127.0.0.1:5000"

def get_first_available_slot():
    try:
        res = requests.get(f"{BASE_URL}/slots?status=AVAILABLE", timeout=5)
        if res.status_code != 200:
            print(f"[-] Failed to fetch slots: {res.status_code} {res.text}")
            return None
        data = res.json()
        slots = data.get('slots', [])
        if not slots:
            print("[-] No available slots found. Try creating a slot first or resetting demo.")
            return None
        return slots[0]
    except Exception as e:
        print(f"[-] Error connecting to server: {e}")
        return None

def attempt_booking(worker_id, slot_id, barrier):
    # Wait at barrier so all threads fire at the exact same microsecond
    barrier.wait()
    payload = {
        "slot_id": slot_id,
        "customer_name": f"Concurrent User {worker_id}",
        "customer_email": f"user{worker_id}@test.com",
        "customer_phone": f"555-010{worker_id}"
    }
    start = time.time()
    try:
        res = requests.post(f"{BASE_URL}/bookings", json=payload, timeout=10)
        elapsed = (time.time() - start) * 1000
        return {
            "worker_id": worker_id,
            "status_code": res.status_code,
            "elapsed_ms": round(elapsed, 2),
            "response": res.json()
        }
    except Exception as e:
        return {
            "worker_id": worker_id,
            "status_code": 0,
            "error": str(e)
        }

def run_stress_test(num_threads=10):
    print("=" * 70)
    print("  [*] CONCURRENCY & DOUBLE-BOOKING PREVENTION STRESS TEST")
    print("=" * 70)
    print(f"Connecting to target server: {BASE_URL}")

    # Check health
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=3)
        if health.status_code != 200:
            print(f"[-] Server not healthy: {health.status_code}")
            return
        print(f"[+] Server is ONLINE ({health.json().get('database')})")
    except Exception as e:
        print(f"[-] Server is NOT running at {BASE_URL}. Please start 'python backend/app.py' first.")
        return

    slot = get_first_available_slot()
    if not slot:
        return

    slot_id = slot['id']
    print(f"[+] Selected Target Slot: #{slot_id} on {slot['slot_date']} ({slot['formatted_time']})")
    print(f"[+] Launching {num_threads} simultaneous threads attempting to book Slot #{slot_id} at the exact same instant...")
    print("-" * 70)

    import threading
    barrier = threading.Barrier(num_threads)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(attempt_booking, i + 1, slot_id, barrier)
            for i in range(num_threads)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Tally results
    success_count = sum(1 for r in results if r['status_code'] == 201)
    conflict_count = sum(1 for r in results if r['status_code'] == 409)
    other_count = sum(1 for r in results if r['status_code'] not in (201, 409))

    print(f"\n[RESULTS BREAKDOWN]")
    for r in sorted(results, key=lambda x: x['worker_id']):
        status = r['status_code']
        icon = "[SUCCESS 201]" if status == 201 else ("[CONFLICT 409]" if status == 409 else "[ERROR]")
        msg = r.get('response', {}).get('message') or r.get('response', {}).get('error', 'Error')
        print(f"  Thread #{r['worker_id']:02d}: Status {status} {icon} | {msg} ({r.get('elapsed_ms')}ms)")

    print("-" * 70)
    print(f"Total Requests: {num_threads}")
    print(f"  * Successful Bookings (201 Created): {success_count}")
    print(f"  * Rejected Double-Bookings (409 Conflict): {conflict_count}")
    print(f"  * Other / Failed: {other_count}")

    print("=" * 70)
    if success_count == 1 and conflict_count == (num_threads - 1):
        print("  [PASSED] Double-booking was 100% PREVENTED!")
        print("  The database pessimistic lock correctly serialized concurrent bookings.")
    else:
        print("  [FAILED] An unexpected number of bookings succeeded.")
    print("=" * 70)

if __name__ == '__main__':
    threads = 10
    if len(sys.argv) > 1:
        try:
            threads = int(sys.argv[1])
        except ValueError:
            pass
    run_stress_test(threads)
