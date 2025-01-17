import asyncio
from flask import Flask, jsonify, render_template
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import threading
from datetime import datetime, timedelta
import pytz  # For time zone handling

app = Flask(__name__)

WALLET_ADDRESS = "3RmzSs3B1Qd6Kf3LTN6r3W5TQhh7M6hBnntpEExMr17m"
wallet_data = {"balance": 0, "pnl": 0}
reference_balance = None  # Induló egyenleg

async def get_balance(wallet_address: str) -> float:
    wallet = Pubkey.from_string(wallet_address)
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
        response = await client.get_balance(wallet)
        return response.value / 1_000_000_000  # Lamports -> SOL

async def track_balance():
    global wallet_data, reference_balance
    reference_balance = await get_balance(WALLET_ADDRESS)
    wallet_data["balance"] = reference_balance
    wallet_data["pnl"] = 0

    while True:
        try:
            current_balance = await get_balance(WALLET_ADDRESS)
            wallet_data["balance"] = current_balance
            wallet_data["pnl"] = current_balance - reference_balance
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(3)  # Frissítés 3 másodpercenként

async def reset_pnl_at_11_59pm():
    global reference_balance, wallet_data
    est = pytz.timezone("US/Eastern")

    while True:
        now = datetime.now(est)
        next_11_59pm = now.replace(hour=23, minute=59, second=0, microsecond=0)

        if now >= next_11_59pm:
            next_11_59pm += timedelta(days=1)

        time_until_reset = (next_11_59pm - now).total_seconds()
        await asyncio.sleep(time_until_reset)

        try:
            reference_balance = await get_balance(WALLET_ADDRESS)
            wallet_data["pnl"] = 0
            print("PNL reset at 11:59 PM EST")
        except Exception as e:
            print(f"Error during PNL reset: {e}")

@app.route("/balance")
def balance():
    return jsonify(wallet_data)

@app.route("/")
def index():
    return render_template("index.html")

def start_flask():
    app.run(host="0.0.0.0", port=5000)

async def main():
    await asyncio.gather(track_balance(), reset_pnl_at_11_59pm())

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
