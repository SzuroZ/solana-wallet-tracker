import asyncio
from flask import Flask, jsonify, render_template, signal
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

def create_app():
    app = Flask(__name__)

    WALLET_ADDRESS = "6RoLbZJWJHpTk4sdPsWzocEHiRtzPS36WcBjnMXuQrfU"  # Cseréld ki a saját tárcád címére!
    wallet_balance = {"balance": 0, "pnl": 0}
    previous_balance = None
    background_task_running = False  # Flag to track if the background task is running

    async def get_balance(wallet_address: str) -> int:
        try:
            wallet = Pubkey.from_string(wallet_address)
            async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
                response = await client.get_balance(wallet)
                return response.value
        except Exception as e:
            print(f"Hiba a Solana API hívásakor: {e}")
            return None

    async def track_balance():
        nonlocal wallet_balance, previous_balance, background_task_running
        if background_task_running:  # Check if the task is already running
            return

        background_task_running = True
        while True:
            try:
                current_balance_lamports = await get_balance(WALLET_ADDRESS)
                if current_balance_lamports is None:
                    await asyncio.sleep(10)
                    continue

                current_balance = current_balance_lamports / 1_000_000_000
                wallet_balance["balance"] = current_balance

                if previous_balance is not None:
                    wallet_balance["pnl"] = current_balance - previous_balance
                previous_balance = current_balance

                await asyncio.sleep(10)
            except Exception as e:
                print(f"Hiba az egyenleg követése során: {e}")
                await asyncio.sleep(10)
            finally:
                background_task_running = False # Reset the flag when the loop breaks (e.g., on shutdown)

    @app.route("/balance")
    async def balance():
        return jsonify(wallet_balance)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.before_server_start
    async def start_background_task():
        asyncio.create_task(track_balance())

    return app