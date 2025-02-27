from fastapi import FastAPI, HTTPException
import requests
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
from spl.token.client import Token

# Константи
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = Pubkey.from_string("4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26")
SPL_TOKEN_MINT = Pubkey.from_string("3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo")

app = FastAPI()
client = Client(SOLANA_RPC_URL)

# Отримання курсу валют
def get_token_price(pair: str) -> float:
    try:
        response = requests.get(f"{BINANCE_API_URL}?symbol={pair}")
        return float(response.json()["price"])
    except:
        return 0.0

# Розрахунок кількості SPL-токенів
def calculate_spl_amount(currency: str, amount: float) -> float:
    price = {
        "SOL": get_token_price("SOLUSDT"),
        "USDT": 1,
        "USDC": get_token_price("USDCUSDT")
    }.get(currency, 0)
    
    return round((amount * price) / TOKEN_PRICE, 2)

# Перевірка транзакції
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    try:
        status = client.get_signature_status(tx_hash)
        if not status["result"]["value"]:
            return False
        
        confirmations = status["result"]["value"]["confirmations"]
        if confirmations and confirmations < 1:
            return False
        
        return True
    except:
        return False

# API ендпойнти
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}
    
@app.get("/price")
def get_price(pair: str):
    return {"price": get_token_price(pair)}

@app.post("/swap")
def swap(data: dict):
    wallet = data.get("wallet")
    currency = data.get("currency")
    amount = data.get("amount")
    tx_hash = data.get("tx_hash")

    if not all([wallet, currency, amount, tx_hash]):
        raise HTTPException(status_code=400, detail="Invalid request data")

    if not check_transaction(tx_hash, wallet):
        raise HTTPException(status_code=400, detail="Transaction not found")

    spl_tokens = calculate_spl_amount(currency, amount)
    
    return {
        "wallet": wallet,
        "spl_tokens": spl_tokens,
        "status": "Verified"
    }




