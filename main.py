import requests
import time
from datetime import datetime
from telegram import Bot
import os

BSC_SCAN_API_KEY = os.getenv("D3IHW56XIXM372PWXEXBGDGC3THM3RN8UM")
TELEGRAM_BOT_TOKEN = os.getenv("7564511392:AAEBov5HVMW2p_B04-T_a2-Iu2wpyXWdW0E")
TELEGRAM_CHAT_ID = os.getenv("6998190008")
WATCHED_ADDRESS = "0x93dEb693b170d56BdDe1B0a5222B14c0F885d976"
MIN_TOKEN_VALUE = 20000 * (10 ** 18)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
notified_tx_hashes = set()
latest_start_timestamp = None

def get_token_transfers():
    global latest_start_timestamp
    url = (
        f"https://api.bscscan.com/api"
        f"?module=account&action=tokentx"
        f"&address={WATCHED_ADDRESS}"
        f"&sort=desc&apikey={BSC_SCAN_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        txs = data.get("result", [])
        if latest_start_timestamp is None and txs:
            latest_start_timestamp = int(txs[0]["timeStamp"])
        return txs
    except Exception:
        return []

def check_new_transfers():
    global notified_tx_hashes, latest_start_timestamp
    transfers = get_token_transfers()
    for tx in transfers:
        tx_time = int(tx["timeStamp"])
        if tx_time <= latest_start_timestamp:
            continue
        if tx["hash"] in notified_tx_hashes:
            continue

        from_addr = tx["from"].lower()
        to_addr = tx["to"].lower()

        if to_addr == WATCHED_ADDRESS.lower():
            tx_hash = tx["hash"]
            token_name = tx["tokenName"]
            token_symbol = tx["tokenSymbol"]
            token_value = int(tx["value"])
            token_decimals = int(tx["tokenDecimal"])
            readable_value = token_value / (10 ** token_decimals)
            timestamp = datetime.utcfromtimestamp(tx_time).strftime('%Y-%m-%d %H:%M:%S')

            if token_value >= MIN_TOKEN_VALUE:
                message = (
                    f"Detected deposit of {readable_value:,.2f} {token_symbol} to https://bscscan.com/address/{WATCHED_ADDRESS}\n"
                    f"\n————————————\n{timestamp} UTC"
                )
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            notified_tx_hashes.add(tx["hash"])

if __name__ == "__main__":
    while True:
        check_new_transfers()
        time.sleep(60)
