
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_FILE = "orders.db"

def initialize_database():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                from_city TEXT NOT NULL,
                to_city TEXT NOT NULL,
                tariff TEXT NOT NULL,
                trip_time TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Ожидает'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers (
                telegram_id INTEGER PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                car_number TEXT NOT NULL
            )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully.")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def insert_order(user_id, from_city, to_city, tariff, trip_time, phone_number):
    """Inserts a new order into the database."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO orders (user_id, from_city, to_city, tariff, trip_time, phone_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, from_city, to_city, tariff, trip_time, phone_number))
        
        conn.commit()
        logger.info(f"New order inserted for user {user_id}")

    except sqlite3.Error as e:
        logger.error(f"Failed to insert order: {e}")
    finally:
        if conn:
            conn.close()

def get_waiting_orders():
    """Retrieves all orders with the status 'Ожидает'."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders WHERE status = 'Ожидает'")
        orders = cursor.fetchall()
        return orders

    except sqlite3.Error as e:
        logger.error(f"Failed to get waiting orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_order_by_id(order_id):
    """Retrievess a single order by its ID."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        return order

    except sqlite3.Error as e:
        logger.error(f"Failed to get order by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_orders(user_id):
    """Retrieves all orders for a specific user."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
        orders = cursor.fetchall()
        return orders

    except sqlite3.Error as e:
        logger.error(f"Failed to get user orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_order_status(order_id, new_status):
    """Updates the status of a specific order."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        
        conn.commit()
        logger.info(f"Order {order_id} status updated to {new_status}")

    except sqlite3.Error as e:
        logger.error(f"Failed to update order status: {e}")
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
