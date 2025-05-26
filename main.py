import requests
import time
import os
from datetime import datetime, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# 讀取 .env 環境變數
load_dotenv()

# 環境變數
BSC_SCAN_API_KEY = os.getenv("BSC_SCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WATCHED_ADDRESS = "0x93dEb693b170d56BdDe1B0a5222B14c0F885d976"
MIN_TOKEN_VALUE = 1 * (10 ** 18)  # 20,000 個 token

# 建立 Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
notified_tx_hashes = set()
latest_start_timestamp = 0  # 改成 0，這樣第一次就能抓資料

# 取得該地址的轉帳紀錄
def get_token_transfers():
    url = (
        f"https://api.bscscan.com/api"
        f"?module=account&action=tokentx"
        f"&address={WATCHED_ADDRESS}"
        f"&sort=desc&apikey={BSC_SCAN_API_KEY}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        return data.get("result", [])
    except Exception as e:
        print(f"Error getting transfers: {e}")
        return []

# 檢查有沒有新轉帳
def check_new_transfers():
    global notified_tx_hashes, latest_start_timestamp
    now_tw = datetime.utcnow() + timedelta(hours=8)
    print(f"[{now_tw.strftime('%Y-%m-%d %H:%M:%S')}] 正在檢查轉帳紀錄...")

    transfers = get_token_transfers()
    for tx in transfers:
        tx_time = int(tx["timeStamp"])
        if tx_time <= latest_start_timestamp:
            continue
        if tx["hash"] in notified_tx_hashes:
            continue

        # 是不是轉入監控錢包
        to_addr = tx["to"].lower()
        if to_addr == WATCHED_ADDRESS.lower():
            token_name = tx["tokenName"]
            token_symbol = tx["tokenSymbol"]
            token_value = int(tx["value"])
            token_decimals = int(tx["tokenDecimal"])
            readable_value = token_value / (10 ** token_decimals)
            # 台灣時間
            timestamp = (datetime.utcfromtimestamp(tx_time) + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

            print(f"偵測到 {readable_value:.2f} {token_symbol}，時間：{timestamp}（台灣時間）")

            if token_value >= MIN_TOKEN_VALUE:
                message = (
                    f"🚨 大額入帳：{readable_value:,.2f} {token_symbol}\n"
                    f"📍 地址: https://bscscan.com/address/{WATCHED_ADDRESS}\n"
                    f"🕒 時間: {timestamp}（台灣時間）"
                )
                try:
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                    print(f"✅ 已發送 Telegram 通知")
                except Exception as e:
                    print(f"❌ 傳送訊息失敗: {e}")

            notified_tx_hashes.add(tx["hash"])
            # 更新時間為最新一筆
            if tx_time > latest_start_timestamp:
                latest_start_timestamp = tx_time

# Flask for uptime monitor
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 定時執行主邏輯
def run_bot():
    while True:
        check_new_transfers()
        time.sleep(60)

if __name__ == "__main__":
    # 測試環境變數是否讀取成功
    print("🔧 啟動設定：")
    print(f"BSC_SCAN_API_KEY: {'OK' if BSC_SCAN_API_KEY else 'MISSING'}")
    print(f"TELEGRAM_BOT_TOKEN: {'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    print(f"TELEGRAM_CHAT_ID: {'OK' if TELEGRAM_CHAT_ID else 'MISSING'}")
    print(f"監控地址: {WATCHED_ADDRESS}")

    Thread(target=run_flask).start()
    Thread(target=run_bot).start()

