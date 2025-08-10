# Simple periodic watcher that checks watches and sends Telegram messages when activity is detected.
import os
import time
from models import SessionLocal, Watch, User
from web3_utils import get_eth_balance, get_solana_balance
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in .env")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 60))  # seconds

# A very small state store in DB would be better; for speed we check "non-zero balance" once per interval.
def run():
    while True:
        db = SessionLocal()
        try:
            watches = db.query(Watch).all()
            for w in watches:
                addr = w.target
                user = db.query(User).filter_by(id=w.user_id).first()
                if not user:
                    continue
                try:
                    if addr.startswith('0x'):
                        bal = get_eth_balance(addr)
                        if bal and bal > 0:
                            bot.send_message(chat_id=int(user.telegram_id), text=f"Address {addr} has balance {bal} ETH (watch alert)")
                    else:
                        bal = get_solana_balance(addr)
                        if bal and bal > 0:
                            bot.send_message(chat_id=int(user.telegram_id), text=f"Address {addr} has balance {bal} SOL (watch alert)")
                except Exception as e:
                    print("single watch error", e)
        except Exception as e:
            print('scanner error', e)
        finally:
            db.close()
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    run()