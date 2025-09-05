import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load .env
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read keys and wallets from .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ETH_SAFE_WALLET = os.getenv("ETH_SAFE_WALLET")
SOL_SAFE_WALLET = os.getenv("SOL_SAFE_WALLET")

# Subscription prices (example: can scale as you like)
SUBSCRIPTION_PLANS = {
    "12h": 10,
    "24h": 15,
    "weekly": 25,
    "monthly": 80,
    "yearly": 300
}

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to IceGods Bot!\n\n"
        "This bot monitors wallets, protects against dust/fake tokens, "
        "and provides subscription-based sweeping.\n\n"
        "Type /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Available Commands:*\n\n"
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
    msg = "💰 *Subscription Plans:*\n"
    for plan, price in SUBSCRIPTION_PLANS.items():
        msg += f"{plan} Plan → Send ${price} in USDT/ETH to:\n{ETH_SAFE_WALLET}\n\n"
    await update.message.reply_text(msg)

async def sweep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only allow owner
    if str(update.effective_chat.id) != str(CHAT_ID):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    # Placeholder for sweeping logic
    await update.message.reply_text("🧹 Sweeping fake tokens... (placeholder logic)")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and running smoothly!")

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("sweep", sweep))
    app.add_handler(CommandHandler("status", status))

    print("Bot is running...")
    app.run_polling()
