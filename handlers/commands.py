from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_ID, PAIR_MAP, DEFAULT_LEVERAGE, MAX_LEVERAGE, PAPER_TRADING
from exchange.futures_client import CoinDCXFutures

client = CoinDCXFutures()


def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ALLOWED_USER_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)

    return wrapper


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
