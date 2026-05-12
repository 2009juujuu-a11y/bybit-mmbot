#!/usr/bin/env python3
"""
Bybit Real-time Crypto Price Telegram Bot
ဈေးနှုန်း ပြောင်းတိုင်း ပို့ပြီး တစ်မိနစ်နောက် Auto Delete
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# ==========================================
# ⚙️ သင့် Token နှင့် ID များ
# ==========================================
TELEGRAM_BOT_TOKEN = "8331925403:AAGXelVvEdcCY7ZdhYzcVSBm6XO-dFKKR6g"
TELEGRAM_CHAT_ID   = "-1002369865337"

# ==========================================
# 📊 Big Coins များ
# ==========================================
COINS = {
    "BTCUSDT": {"name": "Bitcoin",  "emoji": "₿",  "short": "BTC"},
    "ETHUSDT": {"name": "Ethereum", "emoji": "Ξ",  "short": "ETH"},
    "BNBUSDT": {"name": "BNB",      "emoji": "🔶", "short": "BNB"},
    "SOLUSDT": {"name": "Solana",   "emoji": "☀️", "short": "SOL"},
    "XRPUSDT": {"name": "XRP",      "emoji": "💧", "short": "XRP"},
    "ADAUSDT": {"name": "Cardano",  "emoji": "🔵", "short": "ADA"},
    "DOGEUSDT":{"name": "Dogecoin", "emoji": "🐕", "short": "DOGE"},
    "AVAXUSDT":{"name": "Avalanche","emoji": "🔺", "short": "AVAX"},
    "TONUSDT": {"name": "Toncoin",  "emoji": "💎", "short": "TON"},
}

# ==========================================
# ⚙️ Settings
# ==========================================
# Coin တစ်ခုစီ တစ်မိနစ်တစ်ကြိမ် ပို့မည် (Threshold မသုံးတော့)
SEND_INTERVAL = 60      # တစ်မိနစ်တစ်ကြိမ် တစ်ကြောင်းချင်း ပို့
DELETE_AFTER  = 60      # ပို့ပြီး ၁မိနစ်နောက် Delete

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==========================================
# 🧠 Price State Tracker
# ==========================================
last_sent   = {}
latest_data = {}

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ==========================================
# 📤 ပို့ပြီး တစ်မိနစ်နောက် Auto Delete
# ==========================================
async def send_and_delete(text):
    try:
        msg = await bot.send_message(
            chat_id    = TELEGRAM_CHAT_ID,
            text       = text,
            parse_mode = "Markdown"
        )
        asyncio.create_task(delete_after_delay(msg.chat_id, msg.message_id))
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")

async def delete_after_delay(chat_id, message_id):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"🗑 Deleted message {message_id}")
    except TelegramError as e:
        logger.error(f"Delete error: {e}")

async def send_message(text):
    try:
        await bot.send_message(
            chat_id    = TELEGRAM_CHAT_ID,
            text       = text,
            parse_mode = "Markdown"
        )
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")

# ==========================================
# 📝 Message Format
# ==========================================
def format_price_message(symbol, price, change_24h):
    info  = COINS[symbol]
    now   = datetime.now().strftime("%H:%M:%S")
    arrow = "🟢 ▲" if change_24h >= 0 else "🔴 ▼"
    sign  = "+" if change_24h >= 0 else ""

    msg  = f"{info['emoji']} *{info['name']} ({info['short']})*\n"
    msg += f"━━━━━━━━━━━━━━\n"
    msg += f"💵 စျေးနှုန်း: `${price:,.4f}`\n"
    msg += f"{arrow} ၂၄နာရီ: `{sign}{change_24h:.2f}%`\n"
    msg += f"🕐 အချိန်: `{now}`\n"
    msg += f"━━━━━━━━━━━━━━\n"
    msg += f"📱 *https://t.me/bybitexchangemm*\n"
    msg += f" #{info['short']} "

    return msg

# ==========================================
# ⏰ တစ်မိနစ်တစ်ကြိမ် Coin တစ်ခုစီ ပို့သည်
# ==========================================
async def send_all_coins_loop():
    # Bot Start ပြီး data စုဆောင်းဖို့ 10 စက္ကန့် စောင့်
    await asyncio.sleep(10)

    while True:
        now = datetime.now().timestamp()
        for symbol in COINS:
            if symbol in latest_data:
                price      = latest_data[symbol]["price"]
                change_24h = latest_data[symbol]["change_24h"]
                msg = format_price_message(symbol, price, change_24h)
                await send_and_delete(msg)
                logger.info(f"📤 Sent: {symbol} ${price:.4f}")
                await asyncio.sleep(2)  # Coin တစ်ခုစီ ၂ စက္ကန့် ခြားပြီး ပို့

        await asyncio.sleep(SEND_INTERVAL)

# ==========================================
# 🔄 WebSocket မှ Data လက်ခံ
# ==========================================
async def process_ticker(symbol, price, change_24h):
    latest_data[symbol] = {"price": price, "change_24h": change_24h}

# ==========================================
# 🌐 Bybit WebSocket
# ==========================================
async def connect_websocket():
    url = "wss://stream.bybit.com/v5/public/spot"
    symbols = list(COINS.keys())
    subscribe_msg = {
        "op": "subscribe",
        "args": [f"tickers.{s}" for s in symbols]
    }

    logger.info("🔌 WebSocket စတင်နေသည်...")

    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logger.info("✅ WebSocket ချိတ်ဆက်ပြီ!")

                await send_message(
                    "🤖 *Bybit Real-time Bot စတင်လည်ပတ်ပြီ!*\n\n"
                    "📊 တစ်မိနစ်တစ်ကြိမ် Coin အားလုံး ပို့မည်\n"
                    "🗑 တစ်မိနစ်နောက် Auto Delete လုပ်မည်\n\n"
                    "Coins: BTC | ETH | BNB | SOL | XRP | ADA | DOGE | TON | AVAX\n"
                    "https://t.me/bybitexchangemm"
                )

                async for message in ws:
                    try:
                        data = json.loads(message)
                        if "data" in data and "topic" in data:
                            topic  = data["topic"]
                            symbol = topic.split(".")[1]
                            if symbol in COINS:
                                ticker     = data["data"]
                                price      = float(ticker.get("lastPrice", 0))
                                change_24h = float(ticker.get("price24hPcnt", 0)) * 100
                                if price > 0:
                                    await process_ticker(symbol, price, change_24h)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.error(f"Data parse error: {e}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            logger.info("🔄 ၅ စက္ကန့်နောက် ပြန်ချိတ်မည်...")
            await asyncio.sleep(5)

# ==========================================
# 🚀 Main
# ==========================================
async def main():
    logger.info("🚀 Bot စတင်သည်...")
    await asyncio.gather(
        connect_websocket(),
        send_all_coins_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
