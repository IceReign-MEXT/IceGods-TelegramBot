import os
from web3 import Web3
from solana.rpc.api import Client as SolanaClient

ETH_RPC = os.environ.get("ETHEREUM_RPC")
SOL_RPC = os.environ.get("SOLANA_RPC")

w3 = Web3(Web3.HTTPProvider(ETH_RPC)) if ETH_RPC else None
sol_client = SolanaClient(SOL_RPC) if SOL_RPC else None

def get_eth_balance(address):
    if not w3:
        return None
    try:
        balance = w3.eth.get_balance(address)
        return float(w3.fromWei(balance, "ether"))
    except Exception:
        return None

def get_solana_balance(address):
    if not sol_client:
        return None
    try:
        resp = sol_client.get_balance(address)
        val = resp.get("result", {}).get("value") if resp else None
        return val / 1e9 if val else None
    except Exception:
        return None