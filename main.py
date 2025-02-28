from fastapi import FastAPI, HTTPException
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import transfer
from solana.publickey import PublicKey
from solders.signature import Signature
import requests
import asyncio
import base58

app = FastAPI()

# Адреси гаманців
SPL_RECEIVER_WALLET = "3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo"
USDT_USDC_SENDER_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"

# Solana RPC URL
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Функція отримання курсу з Binance API
def get_usdt_exchange_rate():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
    response = requests.get(url).json()
    return float(response["price"]) * 0.00048  # Ціна SPL-токена у USDT

@app.post("/exchange")
async def exchange_tokens(user_wallet: str, spl_transaction_id: str):
    client = AsyncClient(SOLANA_RPC_URL)
    
    try:
        # Перевіряємо, чи надійшли SPL-токени на гаманець
        txn = await client.get_transaction(Signature.from_string(spl_transaction_id), commitment="finalized")
        if not txn:
            raise HTTPException(status_code=400, detail="Transaction not found")

        # Отримуємо суму відправлених SPL-токенів
        spl_amount = 1000  # Потрібно витягнути точну суму з транзакції
        usdt_amount = spl_amount * get_usdt_exchange_rate()

        # Виконуємо відправку USDT/USDC користувачеві
        txn = Transaction().add(
            transfer(
                source=PublicKey(USDT_USDC_SENDER_WALLET),
                dest=PublicKey(user_wallet),
                lamports=int(usdt_amount * 1e6)  # Конвертація у мікро-токени
            )
        )
        signed_txn = await client.send_transaction(txn, USDT_USDC_SENDER_WALLET)
        return {"message": "Exchange successful", "transaction_id": signed_txn["result"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await client.close()
