import time
import hmac
import hashlib
import json

import requests

from config import COINDCX_API_KEY, COINDCX_API_SECRET, PAPER_TRADING

BASE_URL = "https://api.coindcx.com"


class CoinDCXFutures:
    def __init__(self):
        self.api_key = COINDCX_API_KEY
        self.api_secret = COINDCX_API_SECRET

    def _sign(self, body: dict) -> str:
        json_body = json.dumps(body, separators=(",", ":"))
        secret_bytes = bytes(self.api_secret, encoding="utf-8")
        return hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    def _headers(self, signature: str) -> dict:
        return {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature,
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
            "margin_currency_short_name": ["USDT"],
        }
        signature = self._sign(body)
        url = f"{BASE_URL}/exchange/v1/derivatives/futures/positions"
        response = requests.post(
            url,
            data=json.dumps(body, separators=(",", ":")),
            headers=self._headers(signature),
            timeout=10,
        )
        return response.json()

    def create_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        leverage: int,
        order_type: str = "market_order",
    ):
        if PAPER_TRADING:
            return {
                "status": "paper",
                "message": f"PAPER: {side.upper()} {quantity} {pair} @ {leverage}x",
            }

        body = {
            "timestamp": int(time.time() * 1000),
            "order": {
                "side": side.lower(),
                "pair": pair,
                "order_type": order_type,
                "total_quantity": quantity,
                "leverage": leverage,
                "notification": "no_notification",
                "margin_currency_short_name": "USDT",
            },
        }
        signature = self._sign(body)
        url = f"{BASE_URL}/exchange/v1/derivatives/futures/orders/create"
        response = requests.post(
            url,
            data=json.dumps(body, separators=(",", ":")),
            headers=self._headers(signature),
            timeout=10,
        )
        return response.json()
