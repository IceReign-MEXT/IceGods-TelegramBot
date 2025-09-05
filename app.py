from flask import Flask, jsonify
from models import init_db, get_subscriptions, get_sweeps, get_wallet_balances
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///database.db")

init_db(DB_PATH)

@app.route("/api/status")
def status():
    return jsonify({"status": "online"})

@app.route("/api/subscriptions")
def subscriptions():
    data = get_subscriptions()
    return jsonify(data)

@app.route("/api/sweeps")
def sweeps():
    data = get_sweeps()
    return jsonify(data)

@app.route("/api/wallets")
def wallets():
    data = get_wallet_balances()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
