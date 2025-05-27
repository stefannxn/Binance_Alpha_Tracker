import os
import requests
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode
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
tz = pytz.timezone("Asia/Taipei")
MIN_TOKENS = 100_000
WATCHED_ADDRESS = "0x93dEb693b170d56BdDe1B0a5222B14c0F885d976"
NOTIFIED_FILE = "notified.txt"

def load_notified_hashes():
    if not os.path.exists(NOTIFIED_FILE):
        return set()
    with open(NOTIFIED_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_notified_hash(tx_hash):
    with open(NOTIFIED_FILE, "a") as f:
        f.write(tx_hash + "\n")

def get_transactions():
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&address={WATCHED_ADDRESS}&sort=desc&apikey={BSC_SCAN_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] != "1":
            return []
        return data["result"]
    except:
        return []

def format_tx(tx):
    symbol = tx.get("tokenSymbol", "")
    value = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
    tx_hash = tx.get("hash")
    time_stamp = datetime.fromtimestamp(int(tx.get("timeStamp")), tz)
    formatted_time = time_stamp.strftime('%Y-%m-%d %H:%M:%S')
    message = (
        f"*{symbol}* received\n"
        f"Amount: {value:,.4f}\n"
        f"https://bscscan.com/tx/{tx_hash}\n"
        f"{formatted_time} (UTC+8)"
    )
    return message

async def check_new_transaction():
    notified_hashes = load_notified_hashes()
    txs = get_transactions()
    for tx in txs:
        to_addr = tx.get("to", "").lower()
        tx_hash = tx.get("hash", "")
        if to_addr != WATCHED_ADDRESS.lower() or tx_hash in notified_hashes:
            continue
        try:
            value = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
        except:
            continue
        if value <= MIN_TOKENS:
            continue
        message = format_tx(tx)
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            save_notified_hash(tx_hash)
        except:
            pass
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

