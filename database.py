import sqlite3
import datetime

# Function to create the table if it doesn't exist
def init_db():
    conn = sqlite3.connect('dukandost.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_number TEXT NOT NULL,
            message_body TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Function to save a new message
def save_message(sender, message):
    conn = sqlite3.connect('dukandost.db')
    cursor = conn.cursor()
    timestamp = datetime.datetime.now()
    cursor.execute('''
        INSERT INTO messages (sender_number, message_body, timestamp)
        VALUES (?, ?, ?)
    ''', (sender, message, timestamp))
    conn.commit()
    conn.close()
    print(f"Database: Saved message from {sender}")

# Run this function once when the app starts
init_db()


# --- NEW FUNCTIONS FOR DAY 4 ---

def init_inventory_db():
    """Creates the inventory table and pre-loads it with test data."""
    conn = sqlite3.connect('dukandost.db')
    cursor = conn.cursor()

    # Create the table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            item_name TEXT PRIMARY KEY,
            current_stock INTEGER,
            reorder_point INTEGER
        )
    ''')

    # Pre-load test data (ONLY if the table is empty)
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        test_items = [
            ('চাল', 100, 20),  # Bengali for "rice"
            ('ডাল', 50, 10),   # Bengali for "lentils"
            ('hello', 999, 999) # Test item
        ]
        cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?)", test_items)
        print("Database: Pre-loaded inventory with test data.")

    conn.commit()
    conn.close()

def update_stock(item_name: str, quantity: int) -> dict:
    """
    Updates the stock for an item and returns the new stock level 
    and a boolean indicating if an alert is needed.
    """
    conn = sqlite3.connect('dukandost.db')
    cursor = conn.cursor()

    try:
        # 1. Get current stock
        cursor.execute("SELECT current_stock, reorder_point FROM inventory WHERE item_name = ?", (item_name,))
        result = cursor.fetchone()

        if result is None:
            return {"error": f"Item '{item_name}' not found in inventory."}

        current_stock, reorder_point = result

        # 2. Calculate new stock
        new_stock = current_stock - quantity

        # 3. Save new stock
        cursor.execute("UPDATE inventory SET current_stock = ? WHERE item_name = ?", (new_stock, item_name))
        conn.commit()

        # 4. Check for alert
        alert_needed = (new_stock <= reorder_point)

        return {
            "item_name": item_name,
            "new_stock": new_stock,
            "alert_needed": alert_needed
        }

    except Exception as e:
        print(f"Database error in update_stock: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

# --- END OF NEW FUNCTIONS ---
# Run this function once when the app starts
init_db()
init_inventory_db() # <--- IT GOES HERE