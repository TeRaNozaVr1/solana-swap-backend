from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.publickey import PublicKey
from solana.system_program import TransferParams, transfer
from solders.keypair import Keypair
import os

app = Flask(__name__)
CORS(app)

# Solana Mainnet API
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
solana_client = Client(SOLANA_RPC_URL)

# Гаманець, на який користувачі будуть надсилати токени
RECEIVING_WALLET = "4ofLfgCmaJYC233vTGv78WFD4AfezzcMiViu26dF3cVU"

# Завантаження секретного ключа сервісного гаманця
SERVICE_WALLET_SECRET = os.getenv("SERVICE_WALLET_SECRET")  # Змінна середовища
service_wallet = Keypair.from_base58_string(SERVICE_WALLET_SECRET)

# URL для пошуку кращого маршруту для обміну
EXCHANGE_API_URL = "https://api.1sol.io/swap"  # Приклад API для маршрутування

@app.route("/connect_wallet", methods=["POST"])
def connect_wallet():
    """Підключення гаманця користувача"""
    data = request.json
    wallet_address = data.get("wallet")
    wallet_type = data.get("type")

    if not wallet_address:
        return jsonify({"error": "Wallet address required"}), 400

    return jsonify({"success": True, "wallet": wallet_address, "type": wallet_type})

@app.route("/exchange", methods=["POST"])
def exchange_tokens():
    """Обмін SPL-токенів на USDT/USDC"""
    data = request.json
    user_wallet = data.get("wallet")
    amount = float(data.get("amount"))
    token_type = data.get("token_type")

    if not user_wallet or amount <= 0:
        return jsonify({"error": "Invalid request"}), 400

    if token_type not in ["USDT", "USDC"]:
        return jsonify({"error": "Only USDT and USDC supported"}), 400

    try:
        # Крок 1: Запит для пошуку найкращого маршруту
        params = {
            "fromToken": "SPL_TOKEN_ADDRESS",  # замінити на адресу вашого токена
            "toToken": "USDT" if token_type == "USDT" else "USDC",
            "amount": amount
        }

        response = requests.get(EXCHANGE_API_URL, params=params)
        exchange_route = response.json()

        if "error" in exchange_route:
            return jsonify({"error": "Exchange route not found"}), 500

        # Крок 2: Створення транзакції для обміну
        # Тут необхідно використовувати алгоритм для заміни токенів через знайдений маршрут
        tx = Transaction()

        tx.add(
            transfer(
                TransferParams(
                    from_pubkey=service_wallet.pubkey(),
                    to_pubkey=PublicKey(user_wallet),
                    lamports=int(amount * 1_000_000)  # Конвертувати в lamports (1 USDT = 1_000_000 lamports)
                )
            )
        )

        # Крок 3: Підпис транзакції
        tx.sign(service_wallet)

        # Крок 4: Відправка транзакції
        tx_sig = solana_client.send_transaction(tx)

        return jsonify({"success": True, "txid": str(tx_sig)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/check_transaction/<txid>", methods=["GET"])
def check_transaction(txid):
    """Перевірка статусу транзакції"""
    try:
        result = solana_client.get_transaction(txid)
        return jsonify({"status": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

