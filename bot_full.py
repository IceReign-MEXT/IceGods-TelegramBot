from telegram.ext import Application
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Application.builder().token(BOT_TOKEN).connect_timeout(60).read_timeout(60).build()

# Load env
load_dotenv()

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ TELEGRAM_BOT_TOKEN missing in .env")

OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

PRICES = {
    "plan_1h": 1,
    "plan_4h": 3,
    "plan_8h": 5,
    "plan_12h": 7,
    "plan_24h": 10,
    "plan_week": 50,
    "plan_month": 150,
    "plan_year": 1000
}

PAYMENT_WALLET_USDT = os.getenv("PAYMENT_WALLET_USDT")
PAYMENT_WALLET_SOL = os.getenv("PAYMENT_WALLET_SOL")

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to IceGods Bot!")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1h - $1", callback_data="plan_1h"),
         InlineKeyboardButton("4h - $3", callback_data="plan_4h")],
        [InlineKeyboardButton("1d - $10", callback_data="plan_24h"),
         InlineKeyboardButton("weekly - $50", callback_data="plan_week")],
    ]
    await update.message.reply_text("Choose a plan:", reply_markup={"inline_keyboard": keyboard})

async def plan_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    plan = q.data
    price = PRICES.get(plan)
    payload = {"tg_id": update.effective_user.id, "plan": plan}
    try:
        r = requests.post(f"{API_BASE}/api/create_invoice", json=payload, timeout=15)
        r.raise_for_status()
    except Exception as e:
        await q.edit_message_text(f"⚠️ Error creating invoice: {e}")
        return
    msg = f"💸 Pay ${price} in USDC(Solana) to:\n{PAYMENT_WALLET_SOL}\n\nThen reply with tx hash."
    await q.edit_message_text(msg)

async def tx_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    ok = False
    try:
        r = requests.post(f"{API_BASE}/api/verify_tx", json={"tx": txt}, timeout=15)
        ok = r.json().get("ok", False)
    except Exception:
        pass
    if ok:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM invoices WHERE tg_id=%s ORDER BY created_at DESC LIMIT 1",
                    (update.effective_user.id,))
        row = cur.fetchone()
        if row:
            mark_invoice_paid(row['id'])
        await update.message.reply_text("✅ Payment verified!")
    else:
        await update.message.reply_text("❌ Could not verify payment.")

async def sweep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not authorized.")
        return
    await update.message.reply_text("🧹 Sweeping wallets...")

# Main
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CallbackQueryHandler(plan_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tx_listener))
    app.add_handler(CommandHandler("sweep", sweep_cmd))

    print("🚀 IceGods Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
