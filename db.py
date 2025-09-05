# db.py
import sqlite3
import time
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "icegods.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = get_conn().cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE,
        username TEXT,
        wallet_address TEXT,
        wallet_chain TEXT,
        consent_message TEXT,
        consent_signature TEXT,
        plan_code TEXT,
        plan_active INTEGER DEFAULT 0,
        plan_expires INTEGER
    );
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        tg_id INTEGER,
        plan_code TEXT,
        amount_usd REAL,
        currency TEXT,
        address TEXT,
        memo TEXT,
        paid INTEGER DEFAULT 0,
        created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS sweeps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,
        wallet_address TEXT,
        chain TEXT,
        unsigned_payload TEXT,
        signed_tx TEXT,
        tx_hash TEXT,
        status TEXT,
        created_at INTEGER
    );
    """)
    get_conn().commit()

def add_invoice(inv):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO invoices (id,tg_id,plan_code,amount_usd,currency,address,memo,paid,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (inv['id'], inv['tg_id'], inv['plan_code'], inv['amount_usd'], inv['currency'], inv['address'], inv['memo'], 0, int(time.time())))
    conn.commit()

def mark_invoice_paid(inv_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE invoices SET paid=1 WHERE id=?", (inv_id,))
    conn.commit()

# additional getters omitted for brevity; add as needed
