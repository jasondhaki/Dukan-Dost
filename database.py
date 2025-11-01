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
