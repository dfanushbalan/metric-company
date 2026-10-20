import os
import sys

# Change working directory and add backend to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from check_db import inspect_database

if __name__ == '__main__':
    inspect_database()
