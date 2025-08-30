import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Hello {update.effective_user.first_name}! 🎉\n"
                                    f"Your chat ID is: {chat_id}")

# Main entry
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
