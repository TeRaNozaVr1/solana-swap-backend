import os
import requests
import base58
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import MemcmpOpts, TokenAccountOpts
from solders.signature import Signature
from solana.publickey import PublicKey
from solders.keypair import Keypair
from spl.token.instructions import transfer_checked
from spl.token.constants import TOKEN_PROGRAM_ID

# Завантаження змінних оточення
load_dotenv()

app = FastAPI()

# 🔹 Основні параметри
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_DECIMALS = 6  # USDT/USDC мають 6 знаків після коми

# 🔹 Адреси гаманців
SPL_RECEIVER_WALLET = PublicKey("3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo")  # Гаманець для прийому SPL
USDT_USDC_SENDER_WALLET = PublicKey("4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU")  # Гаманець для відправки USDT/USDC
USDT_USDC_MINT = PublicKey("Es9vMFrzaCER5FjexzX3p2rN3TDXfQFZ9if4x7bqc4Hy")  # USDT SPL-токен

# 🔹 Секретний ключ відправника
SECRET_KEY = os.getenv("SOLANA_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ ERROR: Set SOLANA_SECRET_KEY in environment variables!")

SENDER_KEYPAIR = Keypair.from_bytes(base58.b58decode(SECRET_KEY))


# 🔹 Отримання курсу SOL -> USDT
def get_usdt_exchange_rate():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
    response = requests.get(url).json()
    return float(response["price"]) * 0.00048  # Враховуємо курс токена SPL


# 🔹 Отримання суми SPL-токенів з транзакції
async def get_spl_amount(client: AsyncClient, transaction_id: str) -> int:
    txn = await client.get_transaction(Signature.from_string(transaction_id), commitment="finalized")

    if txn is None or "result" not in txn or txn["result"] is None:
        raise HTTPException(status_code=400, detail="Transaction not found")

    meta = txn["result"]["meta"]
    pre_balances = meta["preTokenBalances"]
    post_balances = meta["postTokenBalances"]

    for pre, post in zip(pre_balances, post_balances):
        if pre["owner"] == SPL_RECEIVER_WALLET.to_string():
            amount_received = int(post["uiTokenAmount"]["amount"]) - int(pre["uiTokenAmount"]["amount"])
            return amount_received

    raise HTTPException(status_code=400, detail="SPL amount not found in transaction")


# 🔹 Основна функція обміну
@app.post("/exchange")
async def exchange_tokens(user_wallet: str, spl_transaction_id: str):
    client = AsyncClient(SOLANA_RPC_URL)

    try:
        # 🔸 Отримуємо суму відправлених SPL-токенів
        spl_amount = await get_spl_amount(client, spl_transaction_id)
        if spl_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid SPL token amount")

        # 🔸 Конвертація у USDT
        usdt_amount = int(spl_amount * get_usdt_exchange_rate() * 10**TOKEN_DECIMALS)  # Конвертація у лампорти

        # 🔸 Отримуємо токен-акаунт користувача
        user_token_accounts = await client.get_token_accounts_by_owner(
            PublicKey(user_wallet),
            TokenAccountOpts(mint=USDT_USDC_MINT)
        )

        if not user_token_accounts["result"]["value"]:
            raise HTTPException(status_code=400, detail="User has no USDT/USDC token account")

        user_usdt_account = PublicKey(user_token_accounts["result"]["value"][0]["pubkey"])

        # 🔸 Створюємо інструкцію переказу USDT
        usdt_transfer_instr = transfer_checked(
            source=USDT_USDC_SENDER_WALLET,
            dest=user_usdt_account,
            owner=SENDER_KEYPAIR.pubkey(),
            mint=USDT_USDC_MINT,
            amount=usdt_amount,
            decimals=TOKEN_DECIMALS,
            program_id=TOKEN_PROGRAM_ID,
        )

        # 🔸 Відправляємо транзакцію
        txn = await client.send_transaction(usdt_transfer_instr, SENDER_KEYPAIR)

        return {"message": "Exchange successful", "transaction_id": txn.value}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await client.close()


