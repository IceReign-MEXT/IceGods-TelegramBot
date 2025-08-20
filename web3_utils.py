import os
from web3 import Web3
from solana.rpc.api import Client
from dotenv import load_dotenv

load_dotenv()

# Ethereum setup
ETH_NODE_URL = os.getenv("ETH_NODE_URL") or os.getenv("ETHEREUM_RPC")
web3 = Web3(Web3.HTTPProvider(ETH_NODE_URL)) if ETH_NODE_URL else None

# Solana setup
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL") or os.getenv("SOLANA_RPC")
solana_client = Client(SOLANA_RPC_URL) if SOLANA_RPC_URL else None


def get_eth_balance(address: str):
    try:
        if not web3:
            return None
        balance_wei = web3.eth.get_balance(address)
        return web3.from_wei(balance_wei, "ether")
    except Exception as e:
        print(f"ETH balance error: {e}")
        return None


def get_solana_balance(address: str):
    try:
        if not solana_client:
            return None
        result = solana_client.get_balance(address)
        if "result" in result:
            return result["result"]["value"] / 1e9
        return None
    except Exception as e:
        print(f"SOL balance error: {e}")
        return None