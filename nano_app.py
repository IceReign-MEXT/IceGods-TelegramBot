import os
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from web3 import Web3
import sqlite3
import requests

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ETHEREUM_RPC = os.getenv("ETHEREUM_RPC")
SOLANA_RPC = os.getenv("SOLANA_RPC")
DATABASE_URL = os.getenv("DATABASE_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))

# Initialize Flask app
app = Flask(__name__)

# Connect to Ethereum
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Initialize SQLite DB
conn = sqlite3.connect('chainpilot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT UNIQUE,
    subscription TEXT,
    start_time INTEGER
)
''')
conn.commit()

# Telegram messaging function
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

# Check subscription status
def is_subscription_active(start_time, plan):
    now = int(time.time())
    durations = {
        "1_hour": 3600,
        "4_hours": 14400,
        "8_hours": 28800,
        "12_hours": 43200,
        "24_hours": 86400,
        "1_week": 604800,
        "1_month": 2592000,
        "1_year": 31536000
    }
    duration = durations.get(plan, 0)
    return now - start_time < duration

# Routes
@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.json
    telegram_id = data.get("telegram_id")
    plan = data.get("plan")
    start_time = int(time.time())

    cursor.execute("INSERT OR REPLACE INTO users (telegram_id, subscription, start_time) VALUES (?, ?, ?)",
                   (telegram_id, plan, start_time))
    conn.commit()
    send_telegram_message(telegram_id, f"Subscription activated for {plan}!")
    return jsonify({"status": "success", "plan": plan})

@app.route('/check_subscription/<telegram_id>', methods=['GET'])
def check_subscription(telegram_id):
    cursor.execute("SELECT subscription, start_time FROM users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    if not result:
        return jsonify({"active": False})
    plan, start_time = result
    active = is_subscription_active(start_time, plan)
    return jsonify({"active": active, "plan": plan})

# Start the Flask server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
