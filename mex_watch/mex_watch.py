# mex_watch.py  -- multi-chain wallet watcher (ETH + SOL) no private keys
import requests, time, json, sys, os
WALLETS_FILE = "wallets_list.txt"
ETHERSCAN_KEY = "T6H7KF46NT1GFP9BDRVNQ3D5GI7JPXZ671"  # your Etherscan API key
SOL_RPC = "https://api.mainnet-beta.solana.com"
BOT_TOKEN = ""   # optional: paste Telegram bot token here
CHAT_ID = ""     # optional: paste chat id here
POLL_INTERVAL = 60  # seconds

def tg_send(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print("tg err", e)

def check_eth(addr):
    out = {}
    try:
        bal_url = f"https://api.etherscan.io/api?module=account&action=balance&address={addr}&tag=latest&apikey={ETHERSCAN_KEY}"
        r = requests.get(bal_url, timeout=15).json()
        out['balance'] = int(r.get("result","0"))/1e18
    except Exception as e:
        out['balance'] = 0
        print("eth balance err", e)
    try:
        tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={addr}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"
        txs = requests.get(tx_url, timeout=15).json().get("result",[])
        out['last_tx'] = txs[0] if txs else None
    except Exception as e:
        out['last_tx'] = None
        print("eth tx err", e)
    return out

def sol_rpc(method, params):
    body = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r = requests.post(SOL_RPC, json=body, timeout=15).json()
    return r.get("result")

def check_sol(addr):
    out = {}
    try:
        res = sol_rpc("getBalance",[addr])
        out['balance'] = (res.get("value",0)/1e9) if res else 0
    except Exception as e:
        out['balance'] = 0
        print("sol balance err", e)
    try:
        sigs = sol_rpc("getSignaturesForAddress",[addr, {"limit":1}])
        out
