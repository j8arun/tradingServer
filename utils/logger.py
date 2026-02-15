"""
Logging Utility - Better than print() statements
"""
import logging
import config
from datetime import datetime

def setup_logger(name: str = "TradingBot") -> logging.Logger:
    """Setup centralized logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Optional: Telegram alerts for critical events
def send_telegram_alert(message: str):
    """Send alert via Telegram (if configured)"""
    if not config.ENABLE_TELEGRAM_ALERTS:
        return
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": f"🤖 Trading Bot Alert\n\n{message}",
            "parse_mode": "HTML"
        }
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
