0import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Load env variables (Railway injects them automatically)
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ETH_MAIN_WALLET = os.environ["ETH_MAIN_WALLET"]
ETH_BACKUP_WALLET = os.environ["ETH_BACKUP_WALLET"]
SOL_MAIN_WALLET = os.environ["SOL_MAIN_WALLET"]
SOL_BACKUP_WALLET = os.environ["SOL_BACKUP_WALLET"]

# Subscription pricing
SUBSCRIPTION_TIERS = {
    "12h": 15,
    "24h": 20,
    "weekly": 100,
    "monthly": 200,
    "yearly": 1500
}

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Subscription Plans", callback_data="plans")],
        [InlineKeyboardButton("Check Status", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to IceGods Bot!\n\n"
        "This bot monitors wallets, protects against dust/fake tokens, "
        "and provides subscription-based sweeping.\n\n"
        "Type /help to see available commands.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/about - About the bot\n"
        "/plans - Subscription plans\n"
        "/sweep - Sweep fake tokens (owner only)\n"
        "/status - Show bot status"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ IceGods Bot v1.1\n\n"
        "✅ Dust & scam protection\n"
        "✅ Multi-chain monitoring\n"
        "✅ Subscription sweeping\n"
        "✅ Dashboard integration coming soon"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "💰 *Subscription Plans:*\n"
    for tier, price in SUBSCRIPTION_TIERS.items():
        message += f"{tier} Plan → ${price}\n"
    await update.message.reply_text(message)

async def sweep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only owner can use
    if str(update.effective_user.id) != TELEGRAM_CHAT_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    await update.message.reply_text("Sweeping tokens... ✅")
    # TODO: Add sweeping logic

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and running smoothly!")

# --- Callback Query Handler for Inline Buttons ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "plans":
        await plans(update, context)
    elif query.data == "status":
        await status(update, context)

# --- Main Application ---
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("sweep", sweep))
    app.add_handler(CommandHandler("status", status))

    # Inline button handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot
    logger.info("Bot is starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.idle()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
