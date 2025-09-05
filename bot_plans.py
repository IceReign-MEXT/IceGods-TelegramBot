#!/usr/bin/env python3
"""
IceGods - Plans & Invoice generator (non-custodial)
Minimal bot to show /plans and create an on-chain invoice for SOL-USDC memo flow.
Requirements: python-telegram-bot, python-dotenv, requests, sqlite3, uuid
Run: python bot_plans.py
"""

import os
import sqlite3
import uuid
import time
from typing import Optional
from dataclasses import dataclass

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOL_USDC_ADDRESS = os.getenv("SOL_USDC_ADDRESS")  # Your USDC receiving address on Solana
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
DB_PATH = os.getenv("DB_PATH", "icegods.db")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in env")

# Pricing (use values you approved)
PRICES_USD = {
    "FREE": 0,
    "STARTER": 29,
    "GROWTH": 119,
    "PRO": 279,
    "ENT": 3499
}

@dataclass
class Invoice:
    id: str
    user_id: int
    plan_code: str
    amount_usd: float
    currency: str
    address: str
    memo: str
    paid: int  # 0/1
    created_at: float

# Ensure DB and tables
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id INTEGER UNIQUE,
        username TEXT,
        plan_code TEXT,
        plan_active INTEGER DEFAULT 0,
        plan_expires_at REAL
    );
    """)
    cur.execute("""
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
    """)
    conn.commit()
    return conn

DB = init_db()

# Helpers
def create_invoice_db(user_id: int, plan_code: str, amount_usd: float, currency: str, address: str, memo: str) -> Invoice:
    invoice_id = str(uuid.uuid4())
    ts = time.time()
    cur = DB.cursor()
    cur.execute("INSERT INTO invoices (id, user_id, plan_code, amount_usd, currency, address, memo, paid, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (invoice_id, user_id, plan_code, amount_usd, currency, address, memo, ts))
    DB.commit()
    return Invoice(invoice_id, user_id, plan_code, amount_usd, currency, address, memo, 0, ts)

def get_user_by_tgid(tg_user_id: int) -> Optional[dict]:
    cur = DB.cursor()
    cur.execute("SELECT id, tg_user_id, username, plan_code, plan_active FROM users WHERE tg_user_id = ?", (tg_user_id,))
    row = cur.fetchone()
    if row:
        return {"id": row[0], "tg_user_id": row[1], "username": row[2], "plan_code": row[3], "plan_active": row[4]}
    return None

def ensure_user(tg_user_id: int, username: str):
    u = get_user_by_tgid(tg_user_id)
    cur = DB.cursor()
    if not u:
        cur.execute("INSERT INTO users (tg_user_id, username) VALUES (?, ?)", (tg_user_id, username))
        DB.commit()
        return get_user_by_tgid(tg_user_id)
    return u

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username or user.first_name or "")
    text = f"Hello {user.first_name or 'friend'}!\nUse /plans to view available subscription plans."
    await update.message.reply_text(text)

def plans_text():
    lines = ["🔥 IceGods Plans 🔥\n"]
    for code, price in PRICES_USD.items():
        if code == "FREE":
            lines.append(f"{code}: Free trial")
        else:
            lines.append(f"{code}: ${price} USD")
    lines.append("\nUse /subscribe <PLAN_CODE> to get an invoice.")
    return "\n".join(lines)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(plans_text())

async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username or user.first_name or "")
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /subscribe <PLAN_CODE>\nExample: /subscribe STARTER")
        return
    code = args[0].upper()
    if code not in PRICES_USD:
        await update.message.reply_text("Unknown plan code. Try FREE, STARTER, GROWTH, PRO, ENT")
        return

    amount = PRICES_USD[code]
    if amount == 0:
        # free trial activation
        cur = DB.cursor()
        cur.execute("UPDATE users SET plan_code = ?, plan_active = 1 WHERE tg_user_id = ?", (code, user.id))
        DB.commit()
        await update.message.reply_text("Free trial activated. Enjoy!")
        return

    # For crypto invoice: create memo (UUID) and show SOL USDC address + memo
    memo = str(uuid.uuid4()).replace("-", "")[:32]
    address = SOL_USDC_ADDRESS or "SOL_USDC_ADDRESS_NOT_CONFIGURED"
    inv = create_invoice_db(user.id, code, amount, "USDC_SOL", address, memo)
    msg = (
        f"Invoice created:\nPlan: {code}\nAmount: ${amount} (USDC)\n\n"
        f"Send USDC (Solana) to address:\n{address}\n\n"
        f"Memo (exact): {memo}\n\n"
        "⚠️ Use exact memo. Your subscription will be activated after the payment is confirmed."
    )
    await update.message.reply_text(msg)

async def invoice_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cur = DB.cursor()
    cur.execute("SELECT id, plan_code, amount_usd, currency, address, memo, paid FROM invoices WHERE user_id = (SELECT id FROM users WHERE tg_user_id = ?)", (user.id,))
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("No invoices found for your account.")
        return
    lines = []
    for r in rows:
        lines.append(f"ID: {r[0]} | Plan: {r[1]} | ${r[2]} | Paid: {r[6]}\nMemo: {r[5]}")
    await update.message.reply_text("\n\n".join(lines))

# Callback query handler stub (not used here)
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Button pressed")

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CommandHandler("invoices", invoice_list))
    app.add_handler(CallbackQueryHandler(on_button))
    print("Bot is running (plans/invoice).")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
