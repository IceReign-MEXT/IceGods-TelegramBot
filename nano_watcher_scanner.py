import os
import time
import requests
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ETHEREUM_RPC = os.getenv("ETHEREUM_RPC")
WATCHED_WALLETS = [
    os.getenv("BACKUP_WALLET_1"),
    os.getenv("BACKUP_WALLET_2")
]
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))

# Connect to Ethereum
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Telegram messaging function
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

# Function to fetch ETH balance
def get_eth_balance(address):
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, "ether")
        return balance_eth
    except Exception as e:
        print(f"Error fetching ETH balance: {e}")
        return None

# Main watcher loop
def watcher():
    print("Watcher started...")
    last_balances = {wallet: None for wallet in WATCHED_WALLETS}

    while True:
        for wallet in WATCHED_WALLETS:
            balance = get_eth_balance(wallet)
            if balance is not None:
                if last_balances[wallet] != balance:
                    print(f"Balance change detected for {wallet}: {balance} ETH")
                    # Send Telegram notification
                    send_telegram_message(TELEGRAM_BOT_TOKEN, 
                        f"Wallet {wallet} balance changed: {balance} ETH")
                    last_balances[wallet] = balance
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    watcher()
