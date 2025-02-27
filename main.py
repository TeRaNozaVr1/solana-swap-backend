import os
import logging
import requests
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from fastapi.responses import JSONResponse

# Налаштування
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"
SPL_TOKEN_MINT = "3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo"

# Логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
client = Client(SOLANA_RPC_URL)

# Налаштування CORS
origins = [
    "https://inquisitive-manatee-aa9f3b.netlify.app",
    "http://localhost:3000",  # Для тестування локально
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# Отримання курсу валют
def get_token_price(pair: str) -> float:
    try:
        response = requests.get(f"{BINANCE_API_URL}?symbol={pair}", timeout=5)
        response.raise_for_status()
        return float(response.json()["price"])
    except requests.RequestException as e:
        logger.error(f"Помилка отримання ціни {pair}: {e}")
        return 0.0

# Розрахунок кількості SPL-токенів
def calculate_spl_amount(currency: str, amount: float) -> float:
    price = {
        "SOL": get_token_price("SOLUSDT"),
        "USDT": 1,
        "USDC": get_token_price("USDCUSDT")
    }.get(currency, 0)
    
    if price == 0:
        logger.error(f"Невідомий курс для валюти {currency}")
        return 0.0
    
    return round((amount * price) / TOKEN_PRICE, 2)

# Перевірка транзакції
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    try:
        tx_data = client.get_transaction(tx_hash)
        if not tx_data or "result" not in tx_data or not tx_data["result"]:
            logger.warning(f"Транзакція {tx_hash} не знайдена")
            return False

        for instruction in tx_data["result"]["transaction"]["message"]["instructions"]:
            if isinstance(instruction, dict) and "parsed" in instruction:
                parsed = instruction["parsed"]
                if parsed["info"]["destination"] == RECEIVER_WALLET \
                        and parsed["info"]["authority"] == sender_wallet:
                    return True
        return False
    except Exception as e:
        logger.error(f"Помилка перевірки транзакції {tx_hash}: {e}")
        return False

# Запобігання частим запитам
async def rate_limit(request: Request):
    client_ip = request.client.host
    logger.info(f"Запит від IP: {client_ip}")

# API ендпойнти
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}
    
@app.get("/price")
def get_price(pair: str):
    return {"price": get_token_price(pair)}

@app.post("/swap")
def swap(data: dict, request: Request, rate_limit: None = Depends(rate_limit)):
    wallet = data.get("wallet")
    currency = data.get("currency")
    amount = data.get("amount")
    tx_hash = data.get("tx_hash")

    if not all([wallet, currency, amount, tx_hash]):
        logger.warning("Неправильні вхідні дані")
        raise HTTPException(status_code=400, detail="Invalid request data")

    if not check_transaction(tx_hash, wallet):
        logger.warning(f"Транзакція {tx_hash} не підтверджена")
        raise HTTPException(status_code=400, detail="Transaction not found")

    spl_tokens = calculate_spl_amount(currency, amount)
    logger.info(f"Успішний обмін: {wallet} отримує {spl_tokens} SPL")
    
    return {
        "wallet": wallet,
        "spl_tokens": spl_tokens,
        "status": "Verified"
    }

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)






