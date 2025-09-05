# tx_check.py
import os, requests
from dotenv import load_dotenv

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")

def verify_eth_tx(tx_hash, expected_address):
    # check tx existence and to-address (ERC20 transfers require reading logs; this is a simple check for native tx)
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_API_KEY}"
    r = requests.get(url, timeout=15).json()
    if 'result' not in r or r['result'] is None:
        return False
    to_addr = r['result'].get('to')
    if not to_addr:
        return False
    return to_addr.lower() == expected_address.lower()

def verify_sol_tx(tx_hash, expected_address):
    payload = {"jsonrpc":"2.0","id":1,"method":"getTransaction","params":[tx_hash, {"encoding":"jsonParsed"}]}
    resp = requests.post(SOLANA_RPC, json=payload, timeout=15).json()
    if resp.get("result") is None:
        return False
    # naive: check if destination account present in instructions' parsed info
    try:
        instrs = resp["result"]["transaction"]["message"]["instructions"]
        for ins in instrs:
            parsed = ins.get("parsed")
            if not parsed: 
                continue
            info = parsed.get("info", {})
            if info.get("destination") == expected_address or info.get("to") == expected_address:
                return True
    except Exception:
        pass
    return False
