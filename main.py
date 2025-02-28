import os
import requests
import base58
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from solana.rpc.async_api import AsyncClient
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey as PublicKey
from solders.signature import Signature
from solders.keypair import Keypair
from spl.token.client import Token
from spl.token.instructions import transfer_checked

# Завантаження змінних оточення
load_dotenv()

app = FastAPI()

# 🔹 Основні параметри
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_DECIMALS = 6  # USDT та USDC мають 6 знаків після коми

# 🔹 Адреси гаманців
SPL_RECEIVER_WALLET = PublicKey.from_string("3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo")
USDT_USDC_SENDER_WALLET = PublicKey("4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU")
USDT_USDC_MINT = PublicKey("Es9vMFrzaCER5FjexzX3p2rN3TDXfQFZ9if4x7bqc4Hy")  # USDT SPL-токен

# 🔹 Секретний ключ відправника (додається в .env або Render)
SECRET_KEY = os.getenv("SOLANA_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ ERROR: Set SOLANA_SECRET_KEY in environment variables!")

SENDER_KEYPAIR = Keypair.from_bytes(base58.b58decode(SECRET_KEY))

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
        txn = await client.get_transaction(Signature.from_string(spl_transaction_id), commitment="finalized")
        if txn is None or "result" not in txn or txn["result"] is None:
            raise HTTPException(status_code=400, detail="Transaction not found")

        # 🔸 Отримуємо суму відправлених SPL-токенів (ПОТРІБНО ПАРСИТИ ФАКТИЧНІ ДАНІ)
        spl_amount = 1000  # 🔥 Потрібно замінити на реальне значення
        usdt_amount = int(spl_amount * get_usdt_exchange_rate() * 10**TOKEN_DECIMALS)  # Конвертація у лампорти

        # 🔸 Створюємо інструкцію переказу USDT
        usdt_transfer_instr = transfer_checked(
            source=USDT_USDC_SENDER_WALLET,
            dest=PublicKey(user_wallet),
            owner=SENDER_KEYPAIR.pubkey(),
            mint=USDT_USDC_MINT,
            amount=usdt_amount,
            decimals=TOKEN_DECIMALS,
        )

        # 🔸 Створюємо та підписуємо транзакцію
        txn = VersionedTransaction([usdt_transfer_instr])
        signed_txn = await client.send_transaction(txn, SENDER_KEYPAIR)

        return {"message": "Exchange successful", "transaction_id": signed_txn.value}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await client.close()


