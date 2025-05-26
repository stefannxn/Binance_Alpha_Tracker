import os
import time
import requests
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
from datetime import datetime
import pytz
import asyncio
import threading

load_dotenv()

BSC_SCAN_API_KEY = os.getenv("BSC_SCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running."

bot = Bot(token=TELEGRAM_BOT_TOKEN)
last_tx_time = None

tz = pytz.timezone("Asia/Taipei")

def get_transactions():
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&address=0x93dEb693b170d56BdDe1B0a5222B14c0F885d976&sort=desc&apikey={BSC_SCAN_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] != "1":
            return []
        return data["result"]
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []

def format_tx(tx):
    symbol = tx.get("tokenSymbol", "")
    value = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
    tx_hash = tx.get("hash")
    time_stamp = datetime.fromtimestamp(int(tx.get("timeStamp")), tz)
    formatted_time = time_stamp.strftime('%Y-%m-%d %H:%M:%S')
    return (
        f"{symbol} received / Amount: {value:,.4f} / https://bscscan.com/tx/{tx_hash}\n"
        f"{formatted_time} (UTC+8)"
    )

async def check_new_transaction():
    global last_tx_time
    txs = get_transactions()
    for tx in txs:
        to_addr = tx.get("to", "").lower()
        if to_addr != "0x93deb693b170d56bdde1b0a5222b14c0f885d976":
            continue
        tx_time = int(tx.get("timeStamp", 0))
        if last_tx_time is None or tx_time > last_tx_time:
            last_tx_time = tx_time
            message = format_tx(tx)
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            except Exception as e:
                print(f"Telegram error: {e}")
            break

def run_bot_loop():
    async def loop():
        while True:
            await check_new_transaction()
            await asyncio.sleep(20)
    asyncio.run(loop())

threading.Thread(target=run_bot_loop).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

