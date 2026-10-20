import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'appointment-slot-booker-secret-key-2025')
    JSON_SORT_KEYS = False

    DB_TYPE = os.getenv('DB_TYPE', 'mysql').lower()
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'appointment_db')
    AUTO_FALLBACK_SQLITE = os.getenv('AUTO_FALLBACK_SQLITE', 'True').lower() in ('true', '1', 'yes')

    @classmethod
    def get_database_uri(cls):
        # Allow explicit DATABASE_URL override
        explicit_url = os.getenv('DATABASE_URL')
        if explicit_url:
            return explicit_url

        if cls.DB_TYPE == 'mysql':
            # Attempt MySQL connection string
            # Format: mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4
            password_part = f":{cls.DB_PASSWORD}" if cls.DB_PASSWORD else ""
            mysql_uri = f"mysql+pymysql://{cls.DB_USER}{password_part}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?charset=utf8mb4"
            
            # Test if MySQL server is reachable, or auto-create the database if missing
            try:
                import pymysql
                conn = pymysql.connect(
                    host=cls.DB_HOST,
                    port=int(cls.DB_PORT),
                    user=cls.DB_USER,
                    password=cls.DB_PASSWORD,
                    connect_timeout=3
                )
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{cls.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                conn.commit()
                conn.close()
                logger.info(f"Connected to MySQL on {cls.DB_HOST}:{cls.DB_PORT}, using database '{cls.DB_NAME}'.")
                return mysql_uri
            except Exception as e:
                logger.warning(f"Could not connect to MySQL server ({e}).")
                if cls.AUTO_FALLBACK_SQLITE:
                    sqlite_path = os.path.join(os.path.dirname(__file__), 'appointment_booker.db')
                    logger.info(f"Falling back to local SQLite database at: {sqlite_path}")
                    return f"sqlite:///{sqlite_path}"
                else:
                    logger.error("AUTO_FALLBACK_SQLITE is disabled; returning MySQL URI despite connection error.")
                    return mysql_uri
        else:
            sqlite_path = os.path.join(os.path.dirname(__file__), 'appointment_booker.db')
            return f"sqlite:///{sqlite_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
