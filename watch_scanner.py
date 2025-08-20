import time
import os
from dotenv import load_dotenv
from telegram import Bot
from models import SessionLocal, Watch
from web3_utils import get_eth_balance, get_solana_balance

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))

def check_watches():
    db = SessionLocal()
    try:
        watches = db.query(Watch).all()
        for w in watches:
            if w.target.startswith("0x"):  # Ethereum
                bal = get_eth_balance(w.target)
            else:  # Assume Solana
                bal = get_solana_balance(w.target)
            
            if bal is not None:
                bot.send_message(
                    chat_id=w.user.telegram_id,
                    text=f"Watched address {w.target} balance: {bal}"
                )
    finally:
        db.close()

if __name__ == "__main__":
    while True:
        check_watches()
        time.sleep(POLL_INTERVAL)