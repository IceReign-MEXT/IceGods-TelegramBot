import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
TARGET_WALLETS = os.getenv("TARGET_WALLETS", "").split(",")

def sweep_eth(wallet, private_key):
    """Placeholder: sweep ETH/ERC20 funds to SAFE_ETH_WALLET"""
    logging.info(f"💸 Sweeping ETH wallet {wallet} → {SAFE_ETH_WALLET}")
    # TODO: Implement Web3 transfer
    return True

def sweep_sol(wallet, private_key):
    """Placeholder: sweep SOL/Token funds to SAFE_SOL_WALLET"""
    logging.info(f"💸 Sweeping SOL wallet {wallet} → {SAFE_SOL_WALLET}")
    # TODO: Implement Solana transfer
    return True

def run_sweeper():
    """Go through target wallets and sweep"""
    logging.info("🚀 Running sweeper...")
    for w in TARGET_WALLETS:
        if w.startswith("0x"):
            sweep_eth(w, "PRIVATE_KEY_PLACEHOLDER")
        else:
            sweep_sol(w, "PRIVATE_KEY_PLACEHOLDER")
