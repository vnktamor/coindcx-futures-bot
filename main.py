import os
import time
import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

# ====================== CONFIG ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COINDCX_API_KEY = os.getenv("COINDCX_API_KEY")
COINDCX_API_SECRET = os.getenv("COINDCX_API_SECRET")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

PAPER_TRADING = os.getenv("PAPER_TRADING", "True").lower() == "true"
DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", 5))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", 10))

PAIR_MAP = {
    "BTC": "B-BTC_USDT",
    "ETH": "B-ETH_USDT",
    "SOL": "B-SOL_USDT",
    "XRP": "B-XRP_USDT",
    "DOGE": "B-DOGE_USDT",
    "BNB": "B-BNB_USDT",
}

BASE_URL = "https://api.coindcx.com"

# ====================== COINDCX CLIENT ======================
class CoinDCXFutures:
    def __init__(self):
        self.api_key = COINDCX_API_KEY
        self.api_secret = COINDCX_API_SECRET

    def _sign(self, body: dict) -> str:
        json_body = json.dumps(body, separators=(',', ':'))
        secret_bytes = bytes(self.api_secret, encoding='utf-8')
        return hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    def _headers(self, signature: str) -> dict:
        return {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature
        }

    def get_usdt_inr_rate(self) -> float:
        try:
            url = f"{BASE_URL}/exchange/ticker"
            data = requests.get(url, timeout=5).json()
            for item in data:
                if item.get("market") == "USDTINR":
                    return float(item["last_price"])
            return 84.0
        except Exception:
            return 84.0

    def get_mark_price(self, pair: str) -> float:
        try:
            url = f"{BASE_URL}/exchange/v1/derivatives/futures/data/instrument?pair={pair}"
            data = requests.get(url, timeout=5).json()
            return float(data["instrument"]["mark_price"])
        except Exception as e:
            raise Exception(f"Could not fetch price for {pair}: {e}")

    def get_positions(self):
        if PAPER_TRADING:
            return []

        body = {
            "timestamp": int(time.time() * 1000),
            "page": "1",
            "size": "50",
            "margin_currency_short_name": ["USDT"]
        }
        signature = self._sign(body)
        url = f"{BASE_URL}/exchange/v1/derivatives/futures/positions"
        response = requests.post(
            url,
            data=json.dumps(body, separators=(',', ':')),
            headers=self._headers(signature),
            timeout=10
        )
        return response.json()

    def create_order(self, pair: str, side: str, quantity: float, leverage: int):
        if PAPER_TRADING:
            return {
                "status": "paper",
                "message": f"PAPER: {side.upper()} {quantity} {pair} @ {leverage}x"
            }

        body = {
            "timestamp": int(time.time() * 1000),
            "order": {
                "side": side.lower(),
                "pair": pair,
                "order_type": "market_order",
                "total_quantity": quantity,
                "leverage": leverage,
                "notification": "no_notification",
                "margin_currency_short_name": "USDT"
            }
        }
        signature = self._sign(body)
        url = f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create"
        response = requests.post(
            url,
            data=json.dumps(body, separators=(',', ':')),
            headers=self._headers(signature),
            timeout=10
        )
        return response.json()

client = CoinDCXFutures()

# ====================== SECURITY ======================
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ALLOWED_USER_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    return wrapper

# ====================== COMMANDS ======================
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = "PAPER TRADING" if PAPER_TRADING else "LIVE"
    await update.message.reply_text(
        f"CoinDCX Futures Bot\n"
        f"Mode: {mode}\n\n"
        f"Commands:\n"
        f"/price BTC\n"
        f"/positions\n"
        f"/long BTC 0.01 5\n"
        f"/short BTC 0.01 5\n"
        f"/status"
    )

@restricted
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price BTC")
        return

    symbol = context.args[0].upper()
    pair = PAIR_MAP.get(symbol)
    if not pair:
        await update.message.reply_text(f"Supported: {', '.join(PAIR_MAP.keys())}")
        return

    try:
        mark_price = client.get_mark_price(pair)
        usdt_inr = client.get_usdt_inr_rate()
        inr_price = mark_price * usdt_inr

        text = (
            f"*{symbol}/USDT Futures*\n"
            f"Mark Price : `${mark_price:,.2f}`\n"
            f"≈ ₹{inr_price:,.0f}\n"
            f"(1 USDT ≈ ₹{usdt_inr:.2f})"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@restricted
async def long_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _place_order(update, context, side="buy")

@restricted
async def short_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _place_order(update, context, side="sell")

async def _place_order(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str):
    if len(context.args) < 2:
        await update.message.reply_text(f"Usage: /{side} BTC 0.01 [leverage]")
        return

    symbol = context.args[0].upper()
    try:
        qty = float(context.args[1])
        leverage = int(context.args[2]) if len(context.args) > 2 else DEFAULT_LEVERAGE
    except ValueError:
        await update.message.reply_text("Invalid quantity or leverage")
        return

    if leverage > MAX_LEVERAGE:
        await update.message.reply_text(f"Max leverage allowed is {MAX_LEVERAGE}x")
        return

    pair = PAIR_MAP.get(symbol)
    if not pair:
        await update.message.reply_text("Unsupported pair")
        return

    result = client.create_order(pair, side, qty, leverage)
    await update.message.reply_text(str(result))

@restricted
async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = client.get_positions()
        if not data:
            await update.message.reply_text("No open positions" + (" (Paper mode)" if PAPER_TRADING else ""))
            return

        usdt_inr = client.get_usdt_inr_rate()
        text = "*Open Positions*\n\n"
        for pos in data:
            if float(pos.get("active_pos", 0)) == 0:
                continue
            pair = pos.get("pair", "")
            size = pos.get("active_pos")
            entry = float(pos.get("avg_price", 0))
            pnl = float(pos.get("pnl", 0) or 0)
            text += (
                f"`{pair}`\n"
                f"Size: {size}\n"
                f"Entry: ${entry:,.2f} (₹{entry * usdt_inr:,.0f})\n"
                f"PnL: ${pnl:,.2f} (₹{pnl * usdt_inr:,.0f})\n\n"
            )
        await update.message.reply_text(text or "No open positions", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

@restricted
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    rate = client.get_usdt_inr_rate()
    await update.message.reply_text(
        f"Mode: {mode}\n"
        f"USDT/INR: ₹{rate:.2f}\n"
        f"Default Leverage: {DEFAULT_LEVERAGE}x\n"
        f"Max Leverage: {MAX_LEVERAGE}x"
    )

# ====================== START BOT ======================
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("long", long_cmd))
    app.add_handler(CommandHandler("short", short_cmd))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("status", status))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
