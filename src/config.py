"""
Configuration settings for Tool_premodel data collection.
"""
from pathlib import Path

# Binance WebSocket
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
BINANCE_SYMBOL = "BTCUSDT"

# Polymarket CLOB API
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws"
POLYMARKET_POLL_INTERVAL = 1.0  # seconds

# Data storage
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Collection settings
COLLECTION_INTERVAL = 1.0  # seconds between aligned data points
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5.0  # seconds

# Market discovery keywords for 15-minute BTC binary options
MARKET_KEYWORDS = ["bitcoin", "btc", "15 min", "15min", "15-min"]
