-- Run this once to create basic tables if you prefer SQL migration (sqlite)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER UNIQUE,
    username TEXT,
    plan_code TEXT,
    plan_active INTEGER DEFAULT 0,
    plan_expires_at REAL
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    plan_code TEXT,
    amount_usd REAL,
    currency TEXT,
    address TEXT,
    memo TEXT,
    paid INTEGER DEFAULT 0,
    created_at REAL
);
