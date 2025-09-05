import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            plan TEXT,
            payment_amount REAL,
            active INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sweeps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            token TEXT,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_subscriptions():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions")
    data = cursor.fetchall()
    conn.close()
    return data

def get_sweeps():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sweeps")
    data = cursor.fetchall()
    conn.close()
    return data

def get_wallet_balances():
    # Placeholder: replace with real blockchain API calls
    return {
        "ETH": 0.5,
        "SOL": 10.2
    }
