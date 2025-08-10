import os
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from dotenv import load_dotenv
from models import SessionLocal, init_db, User, Wallet, Watch
from web3_utils import get_eth_balance, get_solana_balance
from sqlalchemy.exc import IntegrityError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in .env")

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Initialize DB
init_db()

# Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True, workers=0)

def start(update, context):
    user = update.effective_user
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(telegram_id=str(user.id)).first()
        if not u:
            u = User(telegram_id=str(user.id), first_name=user.first_name)
            db.add(u)
            db.commit()
        update.message.reply_text(
            f"Hi {user.first_name or 'there'}! Welcome to ChainPilot.\nCommands: /connect_wallet /balances /watch_add <address>"
        )
    finally:
        db.close()

def connect_wallet(update, context):
    update.message.reply_text(
        "To connect a wallet, open your mobile wallet and scan this WalletConnect QR (placeholder).\nNote: ChainPilot never asks for your private keys."
    )

def balances(update, context):
    user = update.effective_user
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(telegram_id=str(user.id)).first()
        if not u:
            update.message.reply_text("Please /start first.")
            return
        wallets = db.query(Wallet).filter_by(user_id=u.id).all()
        if not wallets:
            update.message.reply_text("No wallets connected. Use /connect_wallet (placeholder).")
            return
        lines = []
        for w in wallets:
            if w.chain.lower() == 'ethereum':
                bal = get_eth_balance(w.address)
                lines.append(f"{w.address} (ETH): {bal if bal is not None else 'N/A'}")
            elif w.chain.lower() == 'solana':
                bal = get_solana_balance(w.address)
                lines.append(f"{w.address} (SOL): {bal if bal is not None else 'N/A'}")
        update.message.reply_text("\n".join(lines))
    finally:
        db.close()

def watch_add(update, context):
    user = update.effective_user
    args = context.args
    if not args:
        update.message.reply_text("Usage: /watch_add <wallet_address>")
        return
    target = args[0]
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(telegram_id=str(user.id)).first()
        if not u:
            update.message.reply_text("Please /start first.")
            return
        w = Watch(user_id=u.id, target=target)
        db.add(w)
        db.commit()
        update.message.reply_text(f"Added watch for {target}. You'll get alerts here.")
    except IntegrityError:
        db.rollback()
        update.message.reply_text("Failed to add watch (duplicate?).")
    finally:
        db.close()

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("connect_wallet", connect_wallet))
dispatcher.add_handler(CommandHandler("balances", balances))
dispatcher.add_handler(CommandHandler("watch_add", watch_add))

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    except Exception as e:
        app.logger.exception("Failed to process update")
    return jsonify({"ok": True})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)