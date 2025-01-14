import asyncio
from flask import Flask, jsonify, render_template
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import threading
from datetime import datetime, timedelta
import pytz  # For time zone handling

# Flask app létrehozása
app = Flask(__name__)

# Wallet address||
WALLET_ADDRESS = "6RoLbZJWJHpTk4sdPsWzocEHiRtzPS36WcBjnMXuQrfU"

# Tároló az aktuális egyenleghez és PNL-hez
wallet_data = {"balance": 0, "pnl": 0}

# Reference price (induló egyenleg, amit az induláskor határozunk meg)
reference_balance = None  # Dinamikusan kerül inicializálásra


# Function to get the balance of a wallet
async def get_balance(wallet_address: str) -> int:
    wallet = Pubkey.from_string(wallet_address)
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
        response = await client.get_balance(wallet)
        return response.value


# Background task to track balance changes
async def track_balance():
    global wallet_data, reference_balance

    # Lekérjük az induló egyenleget
    initial_balance = await get_balance(WALLET_ADDRESS)
    reference_balance = initial_balance / 1_000_000_000  # Convert lamports to SOL
    wallet_data["balance"] = reference_balance
    wallet_data["pnl"] = 0  # Induláskor nincs PNL, ezért 0

    while True:
        try:
            # Frissítjük az aktuális egyenleget
            current_balance = await get_balance(WALLET_ADDRESS)
            wallet_data["balance"] = current_balance / 1_000_000_000

            # PNL-t az induló egyenleg (reference_balance) alapján számoljuk
            wallet_data["pnl"] = wallet_data["balance"] - reference_balance
            await asyncio.sleep(3)  # Update every 3 seconds
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(3)


# Task to reset PNL at 11:59 PM EST
async def reset_pnl_at_11_59pm():
    global reference_balance, wallet_data

    while True:
        # Get the current time in EST
        est = pytz.timezone("US/Eastern")
        now = datetime.now(est)

        # Calculate the next 11:59 PM
        next_11_59pm = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= next_11_59pm:
            next_11_59pm += timedelta(days=1)  # Move to the next day if already past 11:59 PM

        # Calculate the time remaining until the next 11:59 PM
        time_until_reset = (next_11_59pm - now).total_seconds()
        print(f"Time until next reset: {time_until_reset} seconds")

        # Wait until the next 11:59 PM
        await asyncio.sleep(time_until_reset)

        # Reset the reference balance and PNL
        try:
            current_balance = await get_balance(WALLET_ADDRESS)
            reference_balance = current_balance / 1_000_000_000  # Update reference balance
            wallet_data["pnl"] = 0  # Reset PNL
            print("PNL reset at 11:59 PM EST")
        except Exception as e:
            print(f"Error during PNL reset: {e}")


# Flask route to serve the balance and PNL
@app.route("/balance")
def balance():
    return jsonify(wallet_data)


# Flask route to render the widget page
@app.route("/")
def index():
    return render_template("index.html")


# Start the Flask server and asyncio loop in parallel
def start_server():
    app.run(host="0.0.0.0", port=5000)


def start_async_loop():
    asyncio.run(main())


# Main coroutine to manage all background tasks
async def main():
    # Run tasks concurrently
    await asyncio.gather(track_balance(), reset_pnl_at_11_59pm())


if __name__ == "__main__":
    # Run Flask and asyncio in separate threads
    threading.Thread(target=start_server, daemon=True).start()
    start_async_loop()
