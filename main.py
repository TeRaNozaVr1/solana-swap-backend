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
SUPPORTED_TOKENS = ["SPL", "USDT", "USDC"]

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

# Кеш використаних транзакцій
used_tx_hashes = set()

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

# Перевірка балансу користувача перед транзакцією (SOL, USDT, USDC, SPL)
def check_balance(wallet: str, currency: str, amount: float) -> bool:
    try:
        pubkey = Pubkey.from_string(wallet)
        if currency == "SOL":
            balance = client.get_balance(pubkey)
            return balance["result"]["value"] / 1e9 >= amount

        elif currency in ["USDT", "USDC", "SPL"]:
            response = client.get_token_accounts_by_owner(pubkey, {"mint": SPL_TOKEN_MINT}, "jsonParsed")
            if "result" in response and "value" in response["result"] and response["result"]["value"]:
                balance = int(response["result"]["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]) / 1e9
                return balance >= amount
        return False

    except Exception as e:
        logging.error(f"Помилка перевірки балансу: {str(e)}")
        return False

# Перевірка підтвердження транзакції через getParsedTransaction()
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    retries = 3
    for _ in range(retries):
        try:
            tx_data = client.get_parsed_transaction(tx_hash)
            if tx_data and "result" in tx_data and tx_data["result"]:
                instructions = tx_data["result"]["transaction"]["message"]["instructions"]
                for instruction in instructions:
                    if "parsed" in instruction and instruction["parsed"]["info"]["destination"] == RECEIVER_WALLET:
                        if instruction["parsed"]["info"]["authority"] == sender_wallet:
                            return True
            sleep(2)
        except Exception as e:
            logging.error(f"Помилка перевірки транзакції: {str(e)}")
    return False

# Перевірка чи вже використано транзакцію
def is_transaction_used(tx_hash: str) -> bool:
    return tx_hash in used_tx_hashes

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
    payout_token = data.get("payout_token", "SPL")  # SPL за замовчуванням

    # Валідація вхідних даних
    if not all([wallet, currency, amount, tx_hash]):
        raise HTTPException(status_code=400, detail="Invalid request data")

    if payout_token not in SUPPORTED_TOKENS:
        raise HTTPException(status_code=400, detail="Unsupported payout token")

    # Перевірка подвійного використання транзакції
    if is_transaction_used(tx_hash):
        raise HTTPException(status_code=400, detail="Transaction already processed")

    # Перевірка балансу перед обміном
    if not check_balance(wallet, currency, amount):
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Перевірка транзакції в блокчейні
    if not check_transaction(tx_hash, wallet):
        raise HTTPException(status_code=400, detail="Transaction not confirmed")

    # Додавання tx_hash в кеш використаних транзакцій
    used_tx_hashes.add(tx_hash)

    # Розрахунок виплати
    amount_out = calculate_spl_amount(currency, amount) if payout_token == "SPL" else amount

    logging.info(f"Транзакція підтверджена: {wallet} отримує {amount_out} {payout_token}.")
    
    return {"wallet": wallet, "amount_out": amount_out, "token": payout_token, "status": "Verified"}

# Логування запитів
@app.middleware("http")
async def log_requests(request, call_next):
    logging.info(f"Запит: {request.method} {request.url}")
    response = await call_next(request)
    logging.info(f"Відповідь: {response.status_code}")
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)






