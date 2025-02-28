import os
import requests
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solders.signature import Signature
from time import sleep

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Константи
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"
SPL_TOKEN_MINT = "3EwV6VTHYHrkrZ3UJcRRAxnuHiaeb8EntqX85Khj98Zo"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # Приватний ключ для відправки SPL

app = FastAPI()
client = Client(SOLANA_RPC_URL)

# Налаштування CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функція отримання курсу валют
def get_token_price(pair: str) -> float:
    try:
        response = requests.get(f"{BINANCE_API_URL}?symbol={pair}")
        return float(response.json()["price"])
    except:
        return 0.0

# Розрахунок кількості SPL-токенів
def calculate_spl_amount(amount: float) -> float:
    return round(amount / TOKEN_PRICE, 2)

# Перевірка отриманої транзакції
def check_transaction(tx_hash: str) -> bool:
    retries = 3
    for _ in range(retries):
        try:
            tx_data = client.get_parsed_transaction(tx_hash)
            if tx_data and "result" in tx_data and tx_data["result"]:
                instructions = tx_data["result"]["transaction"]["message"]["instructions"]
                for instruction in instructions:
                    if "parsed" in instruction and instruction["parsed"]["info"]["destination"] == RECEIVER_WALLET:
                        return True
            sleep(2)
        except Exception as e:
            logging.error(f"Помилка перевірки транзакції: {str(e)}")
    return False

# Відправка SPL-токенів
def send_spl_tokens(user_wallet: str, amount: float) -> str:
    try:
        sender = Keypair.from_base58_string(PRIVATE_KEY)
        receiver = Pubkey.from_string(user_wallet)
        txn = Transaction().add(
            transfer(TransferParams(from_pubkey=sender.pubkey(), to_pubkey=receiver, lamports=int(amount * 1e9)))
        )
        signature = client.send_transaction(txn, sender)
        return signature.value
    except Exception as e:
        logging.error(f"Помилка відправки SPL: {str(e)}")
        return ""

@app.post("/swap")
def swap(data: dict):
    wallet = data.get("wallet")
    amount = data.get("amount")
    tx_hash = data.get("tx_hash")
    
    if not all([wallet, amount, tx_hash]):
        raise HTTPException(status_code=400, detail="Invalid request data")
    
    if not check_transaction(tx_hash):
        raise HTTPException(status_code=400, detail="Transaction not confirmed")
    
    spl_amount = calculate_spl_amount(amount)
    tx_signature = send_spl_tokens(wallet, spl_amount)
    
    if not tx_signature:
        raise HTTPException(status_code=500, detail="SPL transfer failed")
    
    return {"wallet": wallet, "amount": spl_amount, "status": "Success", "tx": tx_signature}





