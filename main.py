import os
from solana.rpc.api import Client
from solana.PublicKey import PublicKey
from solana.keypair import Keypair
from pyserum.client import Client as SerumClient
from pyserum.market import Market
from pyserum.transaction import Transaction
from solana.system_program import TransferParams, transfer

# Налаштування Solana Mainnet
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
solana_client = Client(SOLANA_RPC_URL)

# Завантажуємо секретний ключ користувача
SERVICE_WALLET_SECRET = os.getenv("SERVICE_WALLET_SECRET")  # Змінна середовища
service_wallet = Keypair.from_secret_key(bytes.fromhex(SERVICE_WALLET_SECRET))

# Встановлюємо адреси токенів
USDT_MINT_ADDRESS = PublicKey("Es9vMFrzrQZsjAFVUtzz5N7Z9WhwZ1x7pH2aVttYhf5d")
USDC_MINT_ADDRESS = PublicKey("Es9vMFrzrQZsjAFVUtzz5N7Z9WhwZ1x7pH2aVttYhf5d")
TOKEN_ACCOUNT = PublicKey("4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU")

# Підключення до ринку Serum для обміну токенів
serum_client = SerumClient(SOLANA_RPC_URL)
market_address = PublicKey("4PssYJzH2mmY1wb7u3xmf62rPY4DZcHg6b17Zj2uJKrb")
market = Market.load(serum_client, market_address)

# Виконання обміну SPL-токенів
def exchange_tokens(amount, token_type):
    try:
        # Підготовка трансакції для обміну токенів
        transaction = Transaction()

        if token_type == "USDT":
            # Встановлюємо адреси обміну USDT
            token_to_send = USDT_MINT_ADDRESS
        elif token_type == "USDC":
            # Встановлюємо адреси обміну USDC
            token_to_send = USDC_MINT_ADDRESS
        else:
            raise ValueError("Unsupported token type")

        # Параметри для переведення
        transfer_params = TransferParams(
            from_pubkey=service_wallet.public_key,
            to_pubkey=TOKEN_ACCOUNT,
            lamports=int(amount * 1_000_000)  # Припускаємо, що 1 USDT = 1_000_000 lamports
        )

        # Додаємо операцію переведення
        transaction.add(transfer(transfer_params))

        # Підписуємо транзакцію
        transaction.sign(service_wallet)

        # Відправка транзакції в мережу
        tx_sig = solana_client.send_transaction(transaction)

        return {"success": True, "txid": tx_sig["result"]}
    except Exception as e:
        return {"error": str(e)}

# Призначити адреси для замовлення
@app.route("/exchange", methods=["POST"])
def exchange():
    data = request.json
    amount = data.get("amount")
    token_type = data.get("token_type")

    if not amount or not token_type:
        return jsonify({"error": "Missing required parameters"}), 400

    # Виконання обміну
    result = exchange_tokens(amount, token_type)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)


