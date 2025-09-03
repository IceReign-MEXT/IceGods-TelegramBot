#!/usr/bin/env python3
import os
import sqlite3
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# -------------------------
# Config & Logging
# -------------------------
load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger("icegod")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0").strip() or 0)
SUBSCRIPTION_WALLET = os.getenv("SUBSCRIPTION_WALLET", "").strip()  # receiving wallet (public)
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
USDT_CONTRACT = os.getenv("USDT_CONTRACT", "0xdAC17F958D2ee523a2206206994597C13D831ec7").strip()
DB_PATH = os.getenv("DB_PATH", "subscriptions.db")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN missing in .env")
if not SUBSCRIPTION_WALLET:
    raise SystemExit("SUBSCRIPTION_WALLET missing in .env")
if not ETHERSCAN_API_KEY:
    raise SystemExit("ETHERSCAN_API_KEY missing in .env")

# Pricing
PLANS = {
    "12h":  {"usd": 10,  "hours": 12},
    "24h":  {"usd": 15,  "hours": 24},
    "week": {"usd": 25,  "hours": 7 * 24},
    "month":{"usd": 80,  "hours": 30 * 24},
    "year": {"usd": 300, "hours": 365 * 24},
}

# -------------------------
# Database helpers
# -------------------------
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def db_init():
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                wallet TEXT,
                plan TEXT,
                expires_at INTEGER DEFAULT 0
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                txhash TEXT PRIMARY KEY,
                user_id INTEGER,
                plan TEXT,
                amount_usd REAL,
                currency TEXT,
                created_at INTEGER,
                valid INTEGER
            )""")
        con.commit()

def set_user_wallet(user_id: int, username: str, wallet: str):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO users(user_id, username, wallet, plan, expires_at) VALUES(?,?,?,?,?)",
                    (user_id, username, wallet, None, 0))
        cur.execute("UPDATE users SET username=?, wallet=? WHERE user_id=?",
                    (username, wallet, user_id))
        con.commit()

def activate_subscription(user_id: int, username: str, plan: str):
    hours = PLANS[plan]["hours"]
    now = int(time.time())
    expires_at = now + hours * 3600
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO users(user_id, username, wallet, plan, expires_at) VALUES(?,?,?,?,?)",
                    (user_id, username, None, plan, expires_at))
        cur.execute("UPDATE users SET username=?, plan=?, expires_at=? WHERE user_id=?",
                    (username, plan, expires_at, user_id))
        con.commit()
    return expires_at

def get_user(user_id: int) -> Optional[Dict]:
    with db_conn() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def record_payment(txhash: str, user_id: int, plan: str, usd: float, currency: str, valid: int):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO payments(txhash, user_id, plan, amount_usd, currency, created_at, valid)
            VALUES(?,?,?,?,?,?,?)
        """, (txhash, user_id, plan, usd, currency, int(time.time()), valid))
        con.commit()

# -------------------------
# Etherscan helpers
# -------------------------
ETHERSCAN_API = "https://api.etherscan.io/api"

def etherscan_request(params: dict):
    p = params.copy()
    p["apikey"] = ETHERSCAN_API_KEY
    r = requests.get(ETHERSCAN_API, params=p, timeout=18)
    r.raise_for_status()
    return r.json()

def check_tx_receipt(txhash: str) -> bool:
    # getTransactionReceipt via proxy
    j = etherscan_request({"module": "proxy", "action": "eth_getTransactionReceipt", "txhash": txhash})
    res = j.get("result")
    if not res:
        return False
    status = res.get("status")
    # status "0x1" => success
    return status == "0x1"

def get_tx(txhash: str):
    j = etherscan_request({"module": "proxy", "action": "eth_getTransactionByHash", "txhash": txhash})
    return j.get("result") or {}

def find_usdt_transfer_to_wallet(txhash: str, wallet: str) -> Optional[int]:
    # fetch token transfers for wallet and search for txhash
    j = etherscan_request({"module": "account", "action": "tokentx", "address": wallet, "page":1, "offset":100, "sort":"desc", "contractaddress": USDT_CONTRACT})
    if j.get("status") != "1":
        return None
    for it in j.get("result", []):
        if it.get("hash","").lower() == txhash.lower() and it.get("to","").lower() == wallet.lower():
            try:
                return int(it.get("value", "0"))
            except:
                return None
    return None

def get_eth_price_usd() -> float:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids":"ethereum","vs_currencies":"usd"}
        headers = {}
        if COINGECKO_API_KEY:
            headers["x-cg-pro-api-key"] = COINGECKO_API_KEY
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        return float(r.json()["ethereum"]["usd"])
    except Exception as e:
        log.warning("Coingecko failed, fallback to 3000 USD: %s", e)
        return 3000.0

def usd_to_min_wei(usd: float) -> int:
    eth_price = get_eth_price_usd()
    eth_amount = (usd / eth_price) * 1.02  # 2% buffer
    return int(eth_amount * 10**18)

def verify_payment(txhash: str, plan_key: str, wallet: str):
    # returns tuple: (ok:bool, currency:str, message:str, amount_usd:float)
    if plan_key not in PLANS:
        return False, "N/A", "Unknown plan", 0.0

    if not check_tx_receipt(txhash):
        return False, "N/A", "Transaction receipt not ready or failed", 0.0

    tx = get_tx(txhash)
    value_hex = tx.get("value", "0x0")
    try:
        value_wei = int(value_hex, 16)
    except:
        value_wei = 0
    to_addr = (tx.get("to") or "").lower()

    # Direct ETH payment
    if to_addr == wallet.lower() and value_wei > 0:
        required_wei = usd_to_min_wei(PLANS[plan_key]["usd"])
        if value_wei >= required_wei:
            paid_eth = value_wei / 1e18
            amount_usd = paid_eth * get_eth_price_usd()
            return True, "ETH", f"ETH payment detected ({paid_eth:.6f} ETH)", float(amount_usd)
        else:
            return False, "ETH", "ETH amount below required plan price", 0.0

    # Check USDT token transfer
    usdt_units = find_usdt_transfer_to_wallet(txhash, wallet)
    if usdt_units is not None and usdt_units > 0:
        paid_usdt = usdt_units / 1_000_000  # USDT 6 decimals
        if paid_usdt + 1e-6 >= PLANS[plan_key]["usd"]:
            return True, "USDT", f"USDT payment detected ({paid_usdt:.2f} USDT)", float(paid_usdt)
        else:
            return False, "USDT", "USDT amount below required plan price", float(paid_usdt)

    return False, "N/A", "No ETH/USDT payment to subscription wallet found in this tx", 0.0

# -------------------------
# Telegram Handlers
# -------------------------
WELCOME = "👋 Welcome to IceGods Bot! Type /help"

HELP = (
    "/start - Welcome\n"
    "/help - This help\n"
    "/about - About\n"
    "/plans - Subscription address & amounts\n"
    "/subscribe <plan> - Select plan (12h, 24h, week, month, year)\n"
    "/pay <txhash> <plan> - Verify payment and activate\n"
    "/setwallet <address> - Save your own wallet for sweeping\n    (owner-only actions remain restricted)\n"
    "/status - Your subscription status\n"
)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)

async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("IceGods Bot — payment verification + subscriptions.")

async def cmd_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = [f"Send payment to: `{SUBSCRIPTION_WALLET}`", ""]
    for k, v in PLANS.items():
        msg.append(f"- {k}: ${v['usd']}")
    msg.append("\nAfter paying run: `/pay <txhash> <plan>`")
    await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("Usage: /subscribe <plan>")
    plan = ctx.args[0].lower()
    if plan not in PLANS:
        return await update.message.reply_text("Unknown plan. Use: 12h, 24h, week, month, year")
    usd = PLANS[plan]["usd"]
    await update.message.reply_text(f"Selected {plan} (${usd}). Send ETH/USDT to {SUBSCRIPTION_WALLET} and then run:\n`/pay <txhash> {plan}`", parse_mode="Markdown")

async def cmd_pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        return await update.message.reply_text("Usage: /pay <txhash> <plan>")
    txhash = ctx.args[0].strip()
    plan = ctx.args[1].strip().lower()
    user = update.effective_user
    try:
        ok, currency, detail, amount_usd = verify_payment(txhash, plan, SUBSCRIPTION_WALLET)
        record_payment(txhash, user.id, plan, amount_usd, currency, int(ok))
        if ok:
            exp_ts = activate_subscription(user.id, user.username or "", plan)
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            await update.message.reply_text(f"✅ Payment verified ({currency}). Plan {plan} active until {exp_dt.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            await update.message.reply_text(f"❌ Payment not valid: {detail}")
    except Exception as e:
        log.exception("cmd_pay error")
        await update.message.reply_text(f"Error verifying payment: {e}")

async def cmd_setwallet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("Usage: /setwallet <address>")
    wallet = ctx.args[0].strip()
    set_user_wallet(update.effective_user.id, update.effective_user.username or "", wallet)
    await update.message.reply_text(f"Saved wallet: `{wallet}`", parse_mode="Markdown")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not u:
        await update.message.reply_text("No profile set. Use /setwallet and /subscribe")
        return
    active = int(u.get("expires_at", 0)) > int(time.time())
    out = [
        f"User: @{u.get('username')}",
        f"Wallet: {u.get('wallet')}",
        f"Plan: {u.get('plan') or 'none'}",
        f"Active: {'yes' if active else 'no'}",
    ]
    if active:
        exp_dt = datetime.fromtimestamp(u["expires_at"], tz=timezone.utc)
        out.append(f"Expires: {exp_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    await update.message.reply_text("\n".join(out))

async def cmd_sweep(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Not authorized.")
    # --- PLACEHOLDER ---
    # Real sweeping requires secure signing (do NOT put private keys in your git repo)
    await update.message.reply_text("Sweep triggered (placeholder). Use safe manual sweep flow or multisig.")

async def unknown_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. /help")

# -------------------------
# App start
# -------------------------
async def run_bot():
    db_init()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("plans", cmd_plans))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("pay", cmd_pay))
    app.add_handler(CommandHandler("setwallet", cmd_setwallet))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("sweep", cmd_sweep))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))

    log.info("Starting bot (polling)...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        log.info("Shutting down")


