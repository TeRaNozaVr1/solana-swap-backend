import os
import requests
import base58
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from solana.rpc.async_api import AsyncClient
from solders.transaction import Transaction
from solders.system_program import transfer
from solana.publickey import PublicKey
from solders.signature import Signature
from solders.keypair import Keypair

# Завантаження змінних оточення
load_dotenv()

app = FastAPI()

# 🔹 Головні параметри
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# 🔹 Адреси гаманців
SPL_RECEIVER_WALLET = PublicKey("3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo")  # Гаманець для прийому SPL
USDT_USDC_SENDER_WALLET = PublicKey("4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU")  # Гаманець для відправки USDT/USDC

# 🔹 Секретний ключ відправника (додається в .env або Render)
SECRET_KEY = os.getenv("SOLANA_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ ERROR: Set SOLANA_SECRET_KEY in environment variables!")
SENDER_KEYPAIR = Keypair.from_secret_key(base58.b58decode(SECRET_KEY))

# 🔹 Отримання курсу SOL -> USDT
def get_usdt_exchange_rate():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
    response = requests.get(url).json()
    return float(response["price"]) * 0.00048  # Враховуємо курс токена SPL

# 🔹 Основна функція обміну
@app.post("/exchange")
async def exchange_tokens(user_wallet: str, spl_transaction_id: str):
    client = AsyncClient(SOLANA_RPC_URL)

    try:
        # 🔸 Перевіряємо чи існує транзакція
        txn = await client.get_transaction(Signature.from_string(str(spl_transaction_id)), commitment="finalized")
        if not txn:
            raise HTTPException(status_code=400, detail="Transaction not found")

        # 🔸 Отримуємо суму надісланих SPL-токенів (ПОТРІБНО РЕАЛІЗУВАТИ ОТРИМАННЯ СПРАВЖНЬОЇ СУМИ)
        spl_amount = 1000  # 🔥 Потрібно змінити на значення з транзакції
        usdt_amount = spl_amount * get_usdt_exchange_rate()

        # 🔸 Створюємо транзакцію на відправку USDT/USDC
        txn = Transaction().add(
            transfer(
                source=USDT_USDC_SENDER_WALLET,
                dest=PublicKey(user_wallet),
                lamports=int(usdt_amount * 1e6)  # USDT має 6 знаків після коми
            )
        )

        # 🔸 Підписуємо та відправляємо транзакцію
        signed_txn = await client.send_transaction(txn, SENDER_KEYPAIR)

        return {"message": "Exchange successful", "transaction_id": signed_txn["result"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await client.close()

