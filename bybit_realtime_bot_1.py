#!/usr/bin/env python3
"""
Bybit Real-time Crypto Price Telegram Bot
ဈေးနှုန်း ပြောင်းတိုင်း Telegram Group မှာ Post တင်တဲ့ Bot
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
CHANGE_THRESHOLD = 0.1   # 0.1% ပြောင်းတိုင်း ပို့မည်
COOLDOWN_SECONDS = 30    # 30 စက္ကန့် Cooldown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==========================================
# 🧠 Price State Tracker
# ==========================================
last_prices = {}
last_sent   = {}

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ==========================================
# 📤 Telegram ပို့သည်
# ==========================================
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
def format_price_message(symbol, price, change_24h, direction):
    info  = COINS[symbol]
    now   = datetime.now().strftime("%H:%M:%S")
    arrow = "🟢 ▲" if direction == "up" else "🔴 ▼"
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
# 🔄 Price Change စစ်ဆေးသည်
# ==========================================
async def process_ticker(symbol, price, change_24h):
    now = datetime.now().timestamp()

    if symbol in last_sent:
        if now - last_sent[symbol] < COOLDOWN_SECONDS:
            return

    if symbol in last_prices:
        prev_price = last_prices[symbol]
        if prev_price > 0:
            pct_change = abs((price - prev_price) / prev_price) * 100
            if pct_change >= CHANGE_THRESHOLD:
                direction = "up" if price > prev_price else "down"
                msg = format_price_message(symbol, price, change_24h, direction)
                await send_message(msg)
                last_sent[symbol] = now
                logger.info(f"📤 Sent: {symbol} ${price:.4f} ({pct_change:.2f}% change)")

    last_prices[symbol] = price

# ==========================================
# 🌐 Bybit WebSocket အဆက်အသွယ်
# ==========================================
async def connect_websocket():
    url = "wss://stream.bybit.com/v5/public/spot"

    symbols = list(COINS.keys())
    subscribe_msg = {
        "op": "subscribe",
        "args": [f"tickers.{s}" for s in symbols]
    }

    logger.info("🔌 Bybit WebSocket အဆက်အသွယ် စတင်နေသည်...")

    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                await ws.send(json.dumps(subscribe_msg))
                logger.info("✅ WebSocket ချိတ်ဆက်ပြီ!")

                await send_message(
                    "🤖 *Bybit Real-time Bot စတင်လည်ပတ်ပြီ!*\n\n"
                    "📊 ဈေးနှုန်း ပြောင်းတိုင်း အသိပေးမည်\n"
                    f"⚡ Threshold: {CHANGE_THRESHOLD}% ပြောင်းရင် ပို့မည်\n\n"
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
    await connect_websocket()

if __name__ == "__main__":
    asyncio.run(main())
