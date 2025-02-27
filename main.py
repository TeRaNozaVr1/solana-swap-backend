from fastapi import FastAPI, HTTPException
import requests
from solana.rpc.api import Client
from solders.pubkey import Pubkey

# Налаштування
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"
SPL_TOKEN_MINT = "3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo"

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

# Перевірка транзакції (без ключа)
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    try:
        tx_data = client.get_transaction(tx_hash)
        if not tx_data or "result" not in tx_data or not tx_data["result"]:
            return False
        
        # Перевіряємо, чи є в транзакції переказ SPL-токенів на наш гаманець
        for instruction in tx_data["result"]["transaction"]["message"]["instructions"]:
            if isinstance(instruction, dict) and "parsed" in instruction:
                parsed = instruction["parsed"]
                if parsed["info"]["destination"] == RECEIVER_WALLET and parsed["info"]["authority"] == sender_wallet:
                    return True
        return False
    except Exception as e:
        print("Помилка перевірки транзакції:", str(e))
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




