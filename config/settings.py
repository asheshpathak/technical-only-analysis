# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
dotenv_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Zerodha API credentials
ZERODHA_API_KEY = os.environ.get("ZERODHA_API_KEY", "")
ZERODHA_API_SECRET = os.environ.get("ZERODHA_API_SECRET", "")
ZERODHA_REDIRECT_URL = "https://localhost:5000/redirect"

# Data directories
DATA_DIR = BASE_DIR / "data"
HISTORICAL_DATA_DIR = DATA_DIR / "historical"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
STOCKS_LIST_FILE = DATA_DIR / "stocks_list.txt"

# Create directories if they don't exist
for directory in [HISTORICAL_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# SSL certificates
SSL_CERT_FILE = BASE_DIR / "certs" / "cert.pem"
SSL_KEY_FILE = BASE_DIR / "certs" / "key.pem"

# Trading parameters
MARKET_OPEN_TIME = "09:15:00"
MARKET_CLOSE_TIME = "15:30:00"
MAX_RISK_PERCENT = 2.0  # Maximum risk per trade as percentage of portfolio
PORTFOLIO_SIZE = 100000  # Default portfolio size in INR

# Technical analysis parameters
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ADX_PERIOD = 14
VOLATILITY_PERIOD = 20

# API settings
API_HOST = "0.0.0.0"
API_PORT = 5000