"""
Configuration file for the trading system.
Contains API keys, trading parameters, and risk management settings.
"""
import os
from typing import List

# ==================== API CREDENTIALS ====================
GROWW_API_TOKEN = os.getenv("GROWW_API_TOKEN", "eyJraWQiOiJaTUtjVXciLCJhbGciOiJFUzI1NiJ9.eyJleHAiOjI1NTkzODgyMTAsImlhdCI6MTc3MDk4ODIxMCwibmJmIjoxNzcwOTg4MjEwLCJzdWIiOiJ7XCJ0b2tlblJlZklkXCI6XCJmMTQ4YzBkNC0yN2M1LTQ0MjMtYWJmOC0wZDBhMGEzNDc3MjNcIixcInZlbmRvckludGVncmF0aW9uS2V5XCI6XCJlMzFmZjIzYjA4NmI0MDZjODg3NGIyZjZkODQ5NTMxM1wiLFwidXNlckFjY291bnRJZFwiOlwiMjgwYzIzY2ItODY5MS00OWJmLWEzYjktOTU1MGNkMGE1MDA0XCIsXCJkZXZpY2VJZFwiOlwiYWM5NDFiYTYtNjRmZi01NDY2LWEwYTctZTdiM2E4ZGRmMzU3XCIsXCJzZXNzaW9uSWRcIjpcImFhYTA1ZWI2LWU4YmItNDgwZC05ZDRjLWJiMjZhZmEyZWY2MVwiLFwiYWRkaXRpb25hbERhdGFcIjpcIno1NC9NZzltdjE2WXdmb0gvS0EwYkRWbVE5VStlbjVhd3RKRkRWam45TG5lUzJ3b1dwR2RCY2krZ1FmZnYvQ0ZEQitDczUrSk9waG10d3pHOXhpV2x3PT1cIixcInJvbGVcIjpcImF1dGgtdG90cFwiLFwic291cmNlSXBBZGRyZXNzXCI6XCIxNzUuMjIzLjE5Ljk4LDE0MS4xMDEuODQuNzQsMzUuMjQxLjIzLjEyM1wiLFwidHdvRmFFeHBpcnlUc1wiOjI1NTkzODgyMTAwMzJ9IiwiaXNzIjoiYXBleC1hdXRoLXByb2QtYXBwIn0.o4WG1FeFWht0x3cOqLQzsqZNB6_ywaD5TZWC6QEBz3frNqB4DujgSyQ6eD38P_YEy2eYzZVeL7wJJZx6Tic3dA")
GROWW_API_SECRET = os.getenv("GROWW_API_SECRET", "0zSo@GvhWu3E4MAG-xFkqhwpLJ6m$1$p")

# ==================== TRADING PARAMETERS ====================
# Prime Bot Configuration (Bajaj Finance focused)

nifty50 = "256265"
wipro = "969473"
bajajfin = "4268801"
niftyBank = "260105"

SYMBOLS: List[str] = [{"exchange": "NSE", "segment": "CASH", "exchange_token": "4268801"},{"exchange": "NSE", "segment": "CASH", "exchange_token": "256265"}]

   # Primary: Bajaj Finance
NIFTY_SYMBOL = [{"exchange": "NSE", "segment": "CASH", "exchange_token": "256265"}]
  # For relative performance calculation
TIMEFRAME = "5min"  # 5-minute candles (matching your original bot)
TRADING_HOURS = {
    "start": "09:15",  # NSE opens at 9:15 AM
    "end": "15:30"     # NSE closes at 3:30 PM
}

# ==================== RISK MANAGEMENT ====================
MAX_POSITION_SIZE = 50000  # Maximum INR per position
MAX_TOTAL_EXPOSURE = 200000  # Maximum total capital at risk
MAX_LOSS_PER_DAY = 1000  # Stop trading if daily loss exceeds this
MAX_ORDERS_PER_MINUTE = 100  # Rate limiting

# Stop Loss and Take Profit (as % of entry price)
STOP_LOSS_PCT = 0.02  # 2% stop loss
TAKE_PROFIT_PCT = 0.05  # 5% take profit

# Position Sizing
POSITION_SIZE_METHOD = "fixed"  # Options: "fixed", "kelly", "risk_parity"
FIXED_POSITION_SIZE = 10000  # INR per trade (if using "fixed" method)

# ==================== DATABASE ====================
DB_PATH = "trading_system.db"
ENABLE_TICK_RECORDING = True  # Record every tick (uses more storage)

# ==================== LOGGING & MONITORING ====================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "trading.log"
ENABLE_TELEGRAM_ALERTS = False  # Set to True and add bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==================== STRATEGY PARAMETERS ====================
# Prime Bot V2 Configuration
XGBOOST_MODEL_PATH = "models/bajaj_xgboost_v1.json"
FEATURE_WINDOW = 100  # Window for Hurst, momentum, volatility features

# Prime Bot specific thresholds (from your original bot)
PRIME_SCORE_THRESHOLD = 0.00375  # XGBoost score threshold
PRIME_ADX_MIN = 35  # Minimum ADX for trade execution

# Legacy parameter (kept for compatibility)
MIN_PREDICTION_CONFIDENCE = 0.65  # Not used in Prime Bot (uses score threshold instead)

# ==================== MODE ====================
TRADING_MODE = "paper"  # Options: "paper" (simulation) or "live" (real money)

# ==================== ADVANCED SETTINGS ====================
WEBSOCKET_RECONNECT_DELAY = 5  # Seconds before reconnecting on disconnect
HEARTBEAT_INTERVAL = 30  # Ping the broker every N seconds
MAX_RECONNECT_ATTEMPTS = 10  # Give up after this many failed reconnections

# Data validation
PRICE_SANITY_CHECK = {
    "min_price": 1,  # Reject prices below ₹1
    "max_price": 100000,  # Reject prices above ₹1L
    "max_tick_change": 0.10  # Reject if price changes >10% in one tick
}
