# main.py
import os
import time
import re
import sqlite3
from datetime import timedelta

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========= ENV =========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

ETH_MAIN_WALLET = os.getenv("ETH_MAIN_WALLET", "").strip()
SOL_MAIN_WALLET = os.getenv("SOL_MAIN_WALLET", "").strip()
ETH_BACKUP_WALLET = os.getenv("ETH_BACKUP_WALLET", "").strip()
SOL_BACKUP_WALLET = os.getenv("SOL_BACKUP_WALLET", "").strip()

# Optional but recommended
APP_NAME = os.getenv("APP_NAME", "ChainPilot Bot").strip()
BOT_HANDLE = os.getenv("BOT_HANDLE", "@Ice_ChainPilot_bot").strip()

# ========= PRICING / PLANS =========
# Change these anytime — they display in /plans and are used by /subscribe
PLANS = {
    "1_hour":   {"seconds": 1 * 60 * 60,      "price": "$1"},
    "4_hours":  {"seconds": 4 * 60 * 60,      "price": "$3"},
    "8_hours":  {"seconds": 8 * 60 * 60,      "price": "$5"},
    "12_hours": {"seconds": 12 * 60 * 60,     "price": "$7"},
    "24_hours": {"seconds": 24 * 60 * 60,     "price": "$10"},
    "1_week":   {"seconds": 7 * 24 * 60 * 60, "price": "$29"},
    "1_month":  {"seconds": 30 * 24 * 60 * 60,"price": "$79"},
    "1_year":   {"seconds": 365 * 24 * 60 * 60,"price": "$699"},
}

PRICE_BANNER = (
    "🛡️ ChainPilot — Pro Plans\n"
    "────────────────────────\n"
    "⏱️ 1 Hour  → $1\n"
    "⏱️ 4 Hours → $3\n"
    "⏱️ 8 Hours → $5\n"
    "⏱️ 12 Hrs  → $7\n"
    "📅 24 Hrs  → $10\n"
    "📅 1 Week  → $29\n"
    "📅 1 Month → $79\n"
    "📆 1 Year  → $699\n"
    "────────────────────────\n"
    "Pay to the wallets below, then /subscribe <plan> and /status\n"
)

# ========= DB =========
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///chainpilot.db")
# Normalize to local file if needed
if DB_PATH.startswith("sqlite:///"):
    DB_FILE = DB_PATH.replace("sqlite:///", "")
else:
    DB_FILE = "chainpilot.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE,
        wallet_address TEXT,
        chain TEXT,
        plan TEXT,
        start_time INTEGER
    )
    """
)
conn.commit()

# ========= HELPERS =========
def is_valid_eth_address(addr: str) -> bool:
    # 0x + 40 hex chars
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", addr or ""))

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def is_valid_solana_address(addr: str) -> bool:
    if not addr:
        return False
    if not (32 <= len(addr) <= 44):
        return False
    for ch in addr:
        if ch not in _BASE58:
            return False
    return True

def now_ts() -> int:
    return int(time.time())

def is_active(start_time: int | None, plan: str | None) -> bool:
    if not start_time or not plan or plan not in PLANS:
        return False
    duration = PLANS[plan]["seconds"]
    return now_ts() - start_time < duration

def remaining_time(start_time: int | None, plan: str | None) -> str:
    if not start_time or not plan or plan not in PLANS:
        return "No active subscription."
    end_ts = start_time + PLANS[plan]["seconds"]
    remaining = max(0, end_ts - now_ts())
    return str(timedelta(seconds=remaining))

def get_user_row(tg_id: str):
    cur.execute("SELECT telegram_id, wallet_address, chain, plan, start_time FROM users WHERE telegram_id=?",(tg_id,))
    return cur.fetchone()

def upsert_user(tg_id: str, **fields):
    row = get_user_row(tg_id)
    if row is None:
        cur.execute("INSERT INTO users (telegram_id) VALUES (?)", (tg_id,))
        conn.commit()
    # build update
    cols, vals = [], []
    for k, v in fields.items():
        cols.append(f"{k}=?")
        vals.append(v)
    if cols:
        vals.append(tg_id)
        cur.execute(f"UPDATE users SET {', '.join(cols)} WHERE telegram_id=?", tuple(vals))
        conn.commit()

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"👋 Welcome to {APP_NAME} {BOT_HANDLE}\n\n"
        "I can help you manage subscriptions and link your wallet.\n\n"
        "Commands:\n"
        "• /help – Show help\n"
        "• /plans – View plans & prices\n"
        "• /address – Where to pay\n"
        "• /link <wallet> – Link ETH or Solana wallet\n"
        "• /unlink – Remove linked wallet\n"
        "• /subscribe <plan> – Start a plan (records time)\n"
        "• /status – Check your plan & time remaining\n"
    )
    await update.message.reply_text(msg)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # build from PLANS
    lines = ["📋 Available Plans:"]
    for key, cfg in PLANS.items():
        seconds = cfg["seconds"]
        price = cfg["price"]
        if seconds % (24*3600) == 0:
            dur = f"{seconds // (24*3600)}d"
        elif seconds % 3600 == 0:
            dur = f"{seconds // 3600}h"
        else:
            dur = f"{seconds // 60}m"
        lines.append(f"• {key} ({dur}) → {price}")
    lines.append("\n" + PRICE_BANNER)
    await update.message.reply_text("\n".join(lines))

async def address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = ["💳 Payment Addresses:"]
    if ETH_MAIN_WALLET:
        parts.append(f"• ETH Main: `{ETH_MAIN_WALLET}`")
    if SOL_MAIN_WALLET:
        parts.append(f"• SOL Main: `{SOL_MAIN_WALLET}`")
    if ETH_BACKUP_WALLET:
        parts.append(f"• ETH Backup: `{ETH_BACKUP_WALLET}`")
    if SOL_BACKUP_WALLET:
        parts.append(f"• SOL Backup: `{SOL_BACKUP_WALLET}`")
    parts.append("\nSend, then use /subscribe <plan> and /status.")
    await update.message.reply_markdown("\n".join(parts))

async def link_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    arg = " ".join(context.args).strip() if context.args else ""

    if not arg:
        await update.message.reply_text("Usage: /link <ETH_or_SOL_wallet_address>")
        return

    chain = None
    if is_valid_eth_address(arg):
        chain = "ETH"
    elif is_valid_solana_address(arg):
        chain = "SOL"
    else:
        await update.message.reply_text("❌ Invalid wallet address. Please send a valid **ETH (0x...)** or **Solana (base58)** address.")
        return

    upsert_user(tg_id, wallet_address=arg, chain=chain)
    await update.message.reply_text(f"✅ Linked {chain} wallet:\n{arg}")

async def unlink_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    upsert_user(tg_id, wallet_address=None, chain=None)
    await update.message.reply_text("🔓 Wallet unlinked.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    plan = " ".join(context.args).strip().lower() if context.args else ""
    if plan not in PLANS:
        valid = ", ".join(sorted(PLANS.keys()))
        await update.message.reply_text(f"Usage: /subscribe <plan>\nValid: {valid}")
        return
    # record start now
    upsert_user(tg_id, plan=plan, start_time=now_ts())
    await update.message.reply_text(f"✅ Subscription started: {plan}\nUse /status to check remaining time.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    row = get_user_row(tg_id)
    if not row:
        await update.message.reply_text("No record found. Try /link and /subscribe.")
        return
    _, wallet, chain, plan, start_time = row
    active = is_active(start_time, plan)
    remain = remaining_time(start_time, plan) if active else "Expired / Not active."
    lines = [
        f"👤 User: {tg_id}",
        f"🔗 Wallet: {wallet or '—'}",
        f"⛓️ Chain: {chain or '—'}",
        f"📦 Plan: {plan or '—'}",
        f"⏳ Active: {'Yes' if active else 'No'}",
        f"🕒 Remaining: {remain}",
    ]
    await update.message.reply_text("\n".join(lines))

async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Helpful hint on unknown text
    await update.message.reply_text("🤖 Try /help for commands.")

# ========= MAIN =========
def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("address", address))
    app.add_handler(CommandHandler("link", link_wallet))
    app.add_handler(CommandHandler("unlink", unlink_wallet))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    print(f"🤖 {APP_NAME} is running…")
    app.run_polling()

if __name__ == "__main__":
    main()
