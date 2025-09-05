import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)

async def main():
    try:
        await bot.send_message(chat_id=CHAT_ID, text="✅ Bot is working! Dashboard will connect next.")
        print("Message sent successfully.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
