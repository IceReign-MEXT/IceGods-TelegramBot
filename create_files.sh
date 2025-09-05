#!/usr/bin/env bash
set -e

cat > requirements.txt <<'EOF'
flask==2.3.2
python-dotenv==1.0.1
python-telegram-bot==21.6
web3==6.20.1
solana==0.36.9
requests==2.32.5
eth-account==0.8.1
pyjwt==2.8.0
httpx==0.28.1
sqlite3==0.0.0
EOF

cat > .env.sample <<'EOF'
# === Telegram ===
TELEGRAM_BOT_TOKEN=replace_with_bot_token
TELEGRAM_OWNER_ID=replace_with_owner_telegram_id

# === DB ===
DB_PATH=icegods.db

# === Payments / RPCs / APIs ===
# Solana RPC
SOLANA_RPC=https://api.mainnet-beta.solana.com
PAYMENT_WALLET_SOL=replace_with_sol_receive_address

# EVM / Infura / Etherscan
INFURA_URL=https://mainnet.infura.io/v3/replace_with_infura_key
PAYMENT_WALLET_USDT=replace_with_eth_receive_address
ETHERSCAN_API_KEY=replace_with_etherscan_key

# Safe sweep wallets (for reporting; non-custodial by default)
SAFE_SOL_WALLET=replace_with_safe_sol_wallet
SAFE_ETH_WALLET=replace_with_safe_eth_wallet

# API base for local testing (Flask)
API_BASE=http://127.0.0.1:5000
EOF

cat > create_db.sh <<'EOF'
#!/usr/bin/env bash
python - <<'PY'
import sqlite3, os
db = os.getenv("DB_PATH","icegods.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
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
    telegram_id INTEGER,
    plan_code TEXT,
    amount_usd REAL,
    currency TEXT,
    address TEXT,
    memo TEXT,
    tx_hash TEXT,
    status TEXT,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT,
    telegram_id INTEGER,
    tx_hash TEXT,
    amount REAL,
    currency TEXT,
    status TEXT,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS sweeps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    wallet_address TEXT,
    chain TEXT,
    unsigned_payload TEXT,
    signed_tx TEXT,
    tx_hash TEXT,
    status TEXT,
    created_at INTEGER
);
""")
conn.commit()
print("DB initialized at", db)
conn.close()
PY
EOF
chmod +x create_db.sh

cat > db.py <<'PY'
# db.py - sqlite helpers
import sqlite3, time, os
from dotenv import load_dotenv
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "icegods.db")

def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        c.executescript(open("create_db.sh").read().splitlines() and "")
    c.close()

def add_invoice(inv):
    c = conn()
    cur = c.cursor()
    cur.execute("INSERT INTO invoices (id, telegram_id, plan_code, amount_usd, currency, address, memo, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (inv['id'], inv['telegram_id'], inv['plan_code'], inv['amount_usd'], inv['currency'], inv['address'], inv['memo'], 'pending', int(time.time())))
    c.commit()
    c.close()

def mark_invoice_paid(invoice_id, tx_hash):
    c = conn()
    cur = c.cursor()
    cur.execute("UPDATE invoices SET status='paid', tx_hash=? WHERE id=?", (tx_hash, invoice_id))
    c.commit()
    c.close()

def get_unpaid_invoices():
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM invoices WHERE status='pending'")
    rows = cur.fetchall()
    c.close()
    return rows

def activate_subscription(telegram_id, plan_code, expires_at):
    c = conn()
    cur = c.cursor()
    cur.execute("INSERT OR REPLACE INTO users (telegram_id, plan_code, plan_active, plan_expires) VALUES (?,?,?,?)", (telegram_id, plan_code, 1, expires_at))
    c.commit()
    c.close()
PY

cat > tx_check.py <<'PY'
# tx_check.py - verify ETH/ERC20 via Etherscan, Solana via RPC
import os, requests, time
from dotenv import load_dotenv
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")

def verify_eth_tx(tx_hash, expected_address):
    # Try to get transaction receipt via Etherscan proxy
    try:
        url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
        r = requests.get(url, timeout=15).json()
        result = r.get("result")
        if not result:
            return False
        to_addr = result.get("to")
        if to_addr and to_addr.lower() == expected_address.lower():
            return True
        # Fallback: check receipt logs for ERC20 transfer to expected_address
        rec_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionReceipt&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
        rec = requests.get(rec_url, timeout=15).json().get("result")
        if rec and 'logs' in rec:
            for log in rec['logs']:
                # log.topics[2] may contain recipient for transfer events; naive check for address bytes
                data = log.get('data','')
                if expected_address.lower().replace('0x','') in (data or '').lower():
                    return True
    except Exception:
        return False
    return False

def verify_sol_tx(tx_hash, expected_address):
    try:
        payload = {"jsonrpc":"2.0","id":1,"method":"getTransaction","params":[tx_hash, {"encoding":"jsonParsed"}]}
        r = requests.post(SOLANA_RPC, json=payload, timeout=15).json()
        result = r.get("result")
        if not result:
            return False
        # Inspect parsed instructions for destination
        instrs = result.get("transaction",{}).get("message",{}).get("instructions",[])
        for instr in instrs:
            parsed = instr.get("parsed")
            if not parsed:
                continue
            info = parsed.get("info",{})
            # check common keys
            if info.get("destination") == expected_address or info.get("to") == expected_address:
                return True
    except Exception:
        return False
    return False
PY

cat > sweep_builder.py <<'PY'
# sweep_builder.py - build unsigned tx payloads for client-side signing (non-custodial)
import os
from dotenv import load_dotenv
from web3 import Web3
load_dotenv()
INFURA_URL = os.getenv("INFURA_URL")
SAFE_ETH = os.getenv("SAFE_ETH_WALLET")
w3 = Web3(Web3.HTTPProvider(INFURA_URL)) if INFURA_URL else None

ERC20_ABI = [
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}
]

def build_erc20_transfer_unsigned(user_address, token_address, amount_wei):
    if w3 is None:
        raise RuntimeError("INFURA_URL not configured")
    token = w3.eth.contract(address=w3.toChecksumAddress(token_address), abi=ERC20_ABI)
    data = token.encodeABI(fn_name="transfer", args=[w3.toChecksumAddress(SAFE_ETH), int(amount_wei)])
    nonce = w3.eth.get_transaction_count(user_address)
    gas_price = w3.eth.gas_price
    tx = {
        "nonce": nonce,
        "to": w3.toChecksumAddress(token_address),
        "value": 0,
        "gas": 200000,
        "gasPrice": gas_price,
        "data": data,
        "chainId": w3.eth.chain_id
    }
    return tx

def build_sol_transfer_instruction(user_pubkey, mint_address, amount_raw):
    # Frontend creates and signs the Solana transfer using Phantom / wallet adapter.
    return {"user": user_pubkey, "mint": mint_address, "amount": amount_raw, "to": os.getenv("SAFE_SOL_WALLET")}
PY

cat > app.py <<'PY'
# Flask API - invoices, verify tx, build sweep payload
import os, json, uuid, time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from db import add_invoice, get_unpaid_invoices, mark_invoice_paid, activate_subscription, conn
from tx_check import verify_eth_tx, verify_sol_tx
from sweep_builder import build_erc20_transfer_unsigned, build_sol_transfer_instruction

load_dotenv()
app = Flask(__name__)

PAYMENT_WALLET_SOL = os.getenv("PAYMENT_WALLET_SOL")
PAYMENT_WALLET_USDT = os.getenv("PAYMENT_WALLET_USDT")
API_BASE = os.getenv("API_BASE","http://127.0.0.1:5000")

@app.route("/api/create_invoice", methods=["POST"])
def create_invoice():
    body = request.json
    tg_id = body.get("telegram_id")
    plan_code = body.get("plan_code")
    amount_usd = body.get("amount_usd")
    currency = body.get("currency","USDC_SOL")
    invoice_id = str(uuid.uuid4())
    memo = uuid.uuid4().hex[:32]
    address = PAYMENT_WALLET_SOL if currency == "USDC_SOL" else PAYMENT_WALLET_USDT
    inv = {"id": invoice_id, "telegram_id": tg_id, "plan_code": plan_code, "amount_usd": amount_usd, "currency": currency, "address": address, "memo": memo}
    add_invoice(inv)
    return jsonify(inv)

@app.route("/api/verify_tx", methods=["POST"])
def verify_tx():
    body = request.json
    tx_hash = body.get("tx_hash")
    chain = body.get("chain")
    expected_address = body.get("expected_address")
    ok = False
    if chain == "eth":
        ok = verify_eth_tx(tx_hash, expected_address)
    elif chain == "sol":
        ok = verify_sol_tx(tx_hash, expected_address)
    return jsonify({"ok": ok})

@app.route("/api/build_sweep", methods=["POST"])
def build_sweep():
    body = request.json
    chain = body.get("chain")
    user_addr = body.get("user_addr")
    token = body.get("token_address")
    amount = body.get("amount_wei")
    if chain == "eth":
        tx = build_erc20_transfer_unsigned(user_addr, token, amount)
        return jsonify({"unsigned_tx": tx})
    else:
        instr = build_sol_transfer_instruction(user_addr, token, amount)
        return jsonify({"instruction": instr})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
PY

cat > bot_full.py <<'PY'
# bot_full.py - Telegram bot integrated with invoice flow & tx verification
import os, requests, uuid, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from db import add_invoice, mark_invoice_paid, activate_subscription, conn, init_db

load_dotenv()
init_db()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID","0"))
API_BASE = os.getenv("API_BASE","http://127.0.0.1:5000")
PAYMENT_WALLET_USDT = os.getenv("PAYMENT_WALLET_USDT")
PAYMENT_WALLET_SOL = os.getenv("PAYMENT_WALLET_SOL")

PRICES = {
    "plan_6h": 3,
    "plan_12h": 7,
    "plan_24h": 12,
    "plan_week": 60,
    "plan_month": 200,
    "plan_year": 2000
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to IceGods Bot! Use /plans to subscribe.")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("6h - $3", callback_data="plan_6h"), InlineKeyboardButton("12h - $7", callback_data="plan_12h")],
        [InlineKeyboardButton("24h - $12", callback_data="plan_24h"), InlineKeyboardButton("Weekly - $60", callback_data="plan_week")],
        [InlineKeyboardButton("Monthly - $200", callback_data="plan_month"), InlineKeyboardButton("Yearly - $2000", callback_data="plan_year")],
    ]
    await update.message.reply_text("Choose a plan:", reply_markup=InlineKeyboardMarkup(keyboard))

async def plan_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    plan = q.data
    price = PRICES.get(plan, 0)
    currency = "USDC_SOL"
    # create invoice via API
    payload = {"telegram_id": update.effective_user.id, "plan_code": plan, "amount_usd": price, "currency": currency}
    r = requests.post(f"{API_BASE}/api/create_invoice", json=payload).json()
    # store invoice in DB (redundant: API added it; but keep local copy logic minimal)
    add_invoice(r)
    msg = f"Pay ${price} in USDC(SOL) to:\n{r['address']}\n\nMemo EXACT: {r['memo']}\n\nAfter payment, reply here with the TX signature (transaction hash)."
    await q.edit_message_text(msg)

async def tx_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx = update.message.text.strip()
    # Check most recent unpaid invoice for this user
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM invoices WHERE telegram_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1", (update.effective_user.id,))
    inv = cur.fetchone()
    if not inv:
        await update.message.reply_text("No pending invoice found. Use /plans to create an invoice first.")
        return
    # verify using API
    chain = "sol" if len(tx) < 70 else "eth"
    res = requests.post(f"{API_BASE}/api/verify_tx", json={"tx_hash": tx, "chain": chain, "expected_address": inv['address']}).json()
    if res.get("ok"):
        mark_invoice_paid(inv['id'], tx)
        # activate subscription: calculate expiry
        plan = inv['plan_code']
        now = int(time.time())
        durations = {"plan_6h":6*3600, "plan_12h":12*3600, "plan_24h":24*3600, "plan_week":7*24*3600, "plan_month":30*24*3600, "plan_year":365*24*3600}
        dur = durations.get(plan, 24*3600)
        activate_subscription(update.effective_user.id, plan, now+dur)
        await update.message.reply_text("✅ Payment verified and subscription activated. Enjoy protection!")
    else:
        await update.message.reply_text("❌ Could not verify transaction. Make sure tx hash and chain are correct and confirmed.")

async def sweep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not authorized.")
        return
    await update.message.reply_text("🧹 Sweep command received. Use dashboard to create unsigned TX and have user sign it.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot online. Use /plans to create invoices.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CallbackQueryHandler(plan_button, pattern="^plan_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tx_listener))
    app.add_handler(CommandHandler("sweep", sweep_cmd))
    app.add_handler(CommandHandler("status", status))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
PY

cat > README.md <<'MD'
# IceGods — Local Deployment (Termux)

## Quick start (Termux)
1. Copy `.env.sample` to `.env` and fill values:
   ```bash
   cp .env.sample .env
   nano .env   # paste your secrets (bot token, wallets, API keys)
