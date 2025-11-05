
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_FILE = "drivers.db"

def initialize_driver_database():
    """Creates the drivers database and table if they don't exist."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                telegram_id INTEGER PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                car_number TEXT NOT NULL
            )
        """)
        
        conn.commit()
        logger.info("Driver database initialized successfully.")

    except sqlite3.Error as e:
        logger.error(f"Driver database error: {e}")
    finally:
        if conn:
            conn.close()

def get_driver_by_phone(phone_number):
    """Retrieves a driver by their phone number."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM drivers WHERE phone_number = ?", (phone_number,))
        driver = cursor.fetchone()
        return driver

    except sqlite3.Error as e:
        logger.error(f"Failed to get driver by phone: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_driver_by_telegram_id(telegram_id):
    """Retrieves a driver by their Telegram ID."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM drivers WHERE telegram_id = ?", (telegram_id,))
        driver = cursor.fetchone()
        return driver

    except sqlite3.Error as e:
        logger.error(f"Failed to get driver by Telegram ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_driver(telegram_id, phone_number, full_name, car_number):
    """Adds a new driver to the database."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO drivers (telegram_id, phone_number, full_name, car_number)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, phone_number, full_name, car_number))
        
        conn.commit()
        logger.info(f"New driver added: {full_name} ({telegram_id})")

    except sqlite3.Error as e:
        logger.error(f"Failed to add driver: {e}")
    finally:
        if conn:
            conn.close()

def update_driver_telegram_id(phone_number, telegram_id):
    """Updates the telegram_id for a driver with the given phone number."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute("UPDATE drivers SET telegram_id = ? WHERE phone_number = ?", (telegram_id, phone_number))

        conn.commit()
        logger.info(f"Updated telegram_id for driver with phone number {phone_number}")

    except sqlite3.Error as e:
        logger.error(f"Failed to update telegram_id: {e}")
    finally:
        if conn:
            conn.close()


