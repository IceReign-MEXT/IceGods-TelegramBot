import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

# ---------------- Environment Variables ---------------- #
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ETH_MAIN_WALLET = os.getenv("ETH_MAIN_WALLET")
ETH_BACKUP_WALLET = os.getenv("ETH_BACKUP_WALLET")
SOL_MAIN_WALLET = os.getenv("SOL_MAIN_WALLET")
SOL_BACKUP_WALLET = os.getenv("SOL_BACKUP_WALLET")

INFURA_API_KEY = os.getenv("INFURA_API_KEY")
INFURA_SECRET = os.getenv("INFURA_SECRET")
INFURA_JWT = os.getenv("INFURA_JWT")

ALCHEMY_ETH_RPC = os.getenv("ALCHEMY_ETH_RPC")
ALCHEMY_ZKSYNC_RPC = os.getenv("ALCHEMY_ZKSYNC_RPC")
ALCHEMY_WORLDCHAIN_RPC = os.getenv("ALCHEMY_WORLDCHAIN_RPC")
ALCHEMY_SHAPE_RPC = os.getenv("ALCHEMY_SHAPE_RPC")
ALCHEMY_SAPPHIRE_DEVNET = os.getenv("ALCHEMY_SAPPHIRE_DEVNET")

TELEGRAM_OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID", CHAT_ID))

# ---------------- Logging ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Subscription Tiers ---------------- #
SUBSCRIPTION_TIERS = {
    "12h": 15,
    "24h": 20,
    "weekly": 100,
    "monthly": 200,
    "yearly": 1500,
}

# ---------------- Bot Commands ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to IceGods Bot!\n\n"
        "This bot monitors wallets, protects against dust/fake tokens, and provides subscription-based sweeping.\n"
        "Type /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "📖 *Available Commands:*\n\n"
    help_text += "/start - Welcome message\n"
    help_text += "/help - Show this help\n"
    help_text += "/about - About the bot\n"
    help_text += "/plans - Subscription plans\n"
    help_text += "/sweep - Sweep fake tokens (owner only)\n"
    help_text += "/status - Show bot status\n"
    await update.message.reply_text(help_text)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "⚡ IceGods Bot v1.1\n\n"
        "✅ Dust & scam protection\n"
        "✅ Multi-chain monitoring\n"
        "✅ Subscription sweeping\n"
        "✅ Dashboard integration coming soon"
    )
    await update.message.reply_text(about_text)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💰 *Subscription Plans:*\n"
    for plan, price in SUBSCRIPTION_TIERS.items():
        text += f"{plan} → ${price} in USDT/ETH\n"
    await update.message.reply_text(text)

async def sweep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != TELEGRAM_OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    await update.message.reply_text("🧹 Sweeping fake tokens... (placeholder logic)")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and running smoothly!")

# ---------------- Main ---------------- #
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("plans", plans))
    application.add_handler(CommandHandler("sweep", sweep))
    application.add_handler(CommandHandler("status", status))

    logger.info("✅ Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()

