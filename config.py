import os
from dotenv import load_dotenv

load_dotenv()

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
