import os
import sys

# Add backend directory to sys.path so modules resolve seamlessly
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() in ('true', '1')
    print("=" * 60)
    print(f"[*] Appointment Slot Booker running on http://127.0.0.1:{port}")
    print(f"[*] Serving Frontend from: {app.static_folder}")
    print(f"[*] Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug)
