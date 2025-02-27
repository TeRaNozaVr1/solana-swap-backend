import os
import requests
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from time import sleep

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Константи
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"
SPL_TOKEN_MINT = "3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo"

app = FastAPI()
client = Client(SOLANA_RPC_URL)

# Налаштування CORS
origins = [
    "https://inquisitive-manatee-aa9f3b.netlify.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Отримання курсу валют
def get_token_price(pair: str) -> float:
    try:
        response = requests.get(f"{BINANCE_API_URL}?symbol={pair}")
        return float(response.json()["price"])
    except:
        return 0.0

# Розрахунок SPL-токенів
def calculate_spl_amount(currency: str, amount: float) -> float:
    price = {
        "SOL": get_token_price("SOLUSDT"),
        "USDT": 1,
        "USDC": get_token_price("USDCUSDT")
    }.get(currency, 0)

    return round((amount * price) / TOKEN_PRICE, 2)

# Перевірка підтвердження транзакції
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    retries = 3
    for _ in range(retries):
        try:
            tx_data = client.get_transaction(tx_hash)
            if tx_data and "result" in tx_data and tx_data["result"]:
                for instruction in tx_data["result"]["transaction"]["message"]["instructions"]:
                    if isinstance(instruction, dict) and "parsed" in instruction:
                        parsed = instruction["parsed"]
                        if parsed["info"]["destination"] == RECEIVER_WALLET and parsed["info"]["authority"] == sender_wallet:
                            return True
            sleep(2)  # Очікуємо 2 секунди перед повторною перевіркою
        except Exception as e:
            logging.error(f"Помилка перевірки транзакції: {str(e)}")
    return False

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
        raise HTTPException(status_code=400, detail="Transaction not confirmed")

    spl_tokens = calculate_spl_amount(currency, amount)
    logging.info(f"Транзакція підтверджена: {wallet} отримує {spl_tokens} SPL-токенів.")

    return {"wallet": wallet, "spl_tokens": spl_tokens, "status": "Verified"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)





