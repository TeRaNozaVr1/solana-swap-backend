from fastapi import FastAPI, HTTPException
import requests
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import Transaction
from solana.rpc.types import TxOpts
from spl.token.instructions import transfer, get_associated_token_address
from spl.token.client import Token

# Налаштування
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
TOKEN_PRICE = 0.00048  # 1 SPL = 0.00048$
RECEIVER_WALLET = "Ваш_Гаманець"
SPL_TOKEN_MINT = "Ваш_Токен"
PRIVATE_KEY = "Ваш_Приватний_Ключ"

app = FastAPI()
client = Client(SOLANA_RPC_URL)

# Отримуємо курс валют
def get_token_price(pair: str) -> float:
    try:
        response = requests.get(f"{BINANCE_API_URL}?symbol={pair}")
        return float(response.json()["price"])
    except:
        return 0.0

# Розраховуємо кількість SPL-токенів
def calculate_spl_amount(currency: str, amount: float) -> float:
    price = {
        "SOL": get_token_price("SOLUSDT"),
        "USDT": 1,
        "USDC": get_token_price("USDCUSDT")
    }.get(currency, 0)
    
    return round((amount * price) / TOKEN_PRICE, 2)

# Перевіряємо транзакцію
def check_transaction(tx_hash: str, sender_wallet: str) -> bool:
    try:
        tx_data = client.get_confirmed_transaction(tx_hash)
        if not tx_data["result"]:
            return False
        
        for instruction in tx_data["result"]["transaction"]["message"]["instructions"]:
            if instruction["programIdIndex"] == 2:
                if instruction["accounts"][1] == sender_wallet and instruction["accounts"][2] == RECEIVER_WALLET:
                    return True
        return False
    except:
        return False

# Відправляємо SPL-токени
def send_spl_tokens(to_wallet: str, amount: float):
    sender = Keypair.from_base58_string(PRIVATE_KEY)
    receiver = Pubkey.from_string(to_wallet)
    mint = Pubkey.from_string(SPL_TOKEN_MINT)

    # Знаходимо ATA (associated token account) отримувача
    receiver_ata = get_associated_token_address(receiver, mint)
    
    # Знаходимо ATA відправника
    sender_ata = get_associated_token_address(sender.pubkey(), mint)

    # Створюємо транзакцію
    tx = Transaction().add(
        transfer(
            source=sender_ata,
            dest=receiver_ata,
            owner=sender.pubkey(),
            amount=int(amount * (10**9)),  # Якщо токен має 9 знаків після коми
        )
    )

    # Відправляємо транзакцію
    response = client.send_transaction(tx, sender, opts=TxOpts(skip_preflight=True))
    return response["result"]

# Ендпойнти
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
    tx_hash = send_spl_tokens(wallet, spl_tokens)

    return {"message": "Tokens sent successfully", "txHash": tx_hash}


