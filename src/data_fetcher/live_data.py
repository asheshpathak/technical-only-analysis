# src/data_fetcher/live_data.py
import datetime
import pandas as pd
import pytz
import time

from config.logging_config import logger
from config.settings import MARKET_OPEN_TIME, MARKET_CLOSE_TIME


class LiveDataFetcher:
    def __init__(self, kite_client):
        """Initialize the live data fetcher.

        Args:
            kite_client: Authenticated KiteConnect client
        """
        self.kite = kite_client
        self.indian_tz = pytz.timezone('Asia/Kolkata')

    def is_market_open(self):
        """Check if the market is currently open.

        Returns:
            Boolean indicating if market is open
        """
        now = datetime.datetime.now(self.indian_tz)
        today = now.date()

        # Check if today is a weekend
        if now.weekday() > 4:  # 5 = Saturday, 6 = Sunday
            logger.info("Market is closed (Weekend)")
            return False

        # Parse market hours
        market_open = datetime.datetime.strptime(MARKET_OPEN_TIME, "%H:%M:%S").time()
        market_close = datetime.datetime.strptime(MARKET_CLOSE_TIME, "%H:%M:%S").time()

        current_time = now.time()

        # Check if current time is within market hours
        if market_open <= current_time <= market_close:
            logger.info("Market is open")
            return True
        else:
            logger.info(f"Market is closed (Current time: {current_time}, Market hours: {market_open}-{market_close})")
            return False

    def get_quote(self, symbols):
        """Get live quotes for a list of symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary of quotes for each symbol
        """
        try:
            logger.debug(f"Fetching quotes for {len(symbols)} symbols")
            # Prepare symbols with exchange prefix
            exchange_symbols = [f"NSE:{symbol}" for symbol in symbols]
            quotes = self.kite.quote(exchange_symbols)

            logger.debug(f"Received quotes for {len(quotes)} symbols")
            return quotes
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}

    def get_live_option_chain(self, symbol, expiry_date=None):
        """Get live option chain for a symbol.

        Args:
            symbol: Stock symbol
            expiry_date: Option expiry date (if None, nearest expiry is used)

        Returns:
            DataFrame with option chain data
        """
        try:
            logger.info(f"Fetching option chain for {symbol}")

            # Get all instruments for the symbol
            instruments = self.kite.instruments("NFO")

            # Filter instruments for the given symbol
            symbol_instruments = [inst for inst in instruments if inst['name'] == symbol]

            if not symbol_instruments:
                logger.warning(f"No option instruments found for {symbol}")
                return pd.DataFrame()

            # Get expiry dates
            expiry_dates = sorted(list(set([inst['expiry'] for inst in symbol_instruments if inst['expiry']])))

            if not expiry_dates:
                logger.warning(f"No expiry dates found for {symbol}")
                return pd.DataFrame()

            # If expiry date is not provided, use the nearest one
            if not expiry_date:
                expiry_date = expiry_dates[0]
                logger.info(f"Using nearest expiry date: {expiry_date}")

            # Filter instruments for the selected expiry
            expiry_instruments = [
                inst for inst in symbol_instruments
                if inst['expiry'] == expiry_date and inst['instrument_type'] in ['CE', 'PE']
            ]

            if not expiry_instruments:
                logger.warning(f"No instruments found for {symbol} with expiry {expiry_date}")
                return pd.DataFrame()

            # Get quotes for these instruments
            instrument_tokens = [inst['instrument_token'] for inst in expiry_instruments]
            instrument_symbols = [f"NFO:{inst['tradingsymbol']}" for inst in expiry_instruments]

            # Batch quotes in chunks of 500 (API limit)
            chunk_size = 500
            all_quotes = {}

            for i in range(0, len(instrument_symbols), chunk_size):
                chunk = instrument_symbols[i:i + chunk_size]
                quotes_chunk = self.kite.quote(chunk)
                all_quotes.update(quotes_chunk)
                time.sleep(0.5)  # Avoid rate limiting

            # Prepare option chain data
            option_data = []

            for inst in expiry_instruments:
                quote_key = f"NFO:{inst['tradingsymbol']}"
                if quote_key in all_quotes:
                    quote = all_quotes[quote_key]
                    option_data.append({
                        'symbol': symbol,
                        'strike': inst['strike'],
                        'type': inst['instrument_type'],
                        'expiry': inst['expiry'],
                        'tradingsymbol': inst['tradingsymbol'],
                        'last_price': quote['last_price'],
                        'volume': quote.get('volume', 0),
                        'open_interest': quote.get('oi', 0),
                        'change': quote.get('change', 0),
                        'iv': quote.get('oi', 0) / 1000 if quote.get('oi', 0) > 0 else 0,  # Approximation for example
                    })

            # Convert to DataFrame
            df = pd.DataFrame(option_data)
            logger.info(f"Found {len(df)} option contracts for {symbol} with expiry {expiry_date}")

            return df

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return pd.DataFrame()

    def get_market_status(self):
        """Get current market status.

        Returns:
            String with market status
        """
        if self.is_market_open():
            return "Open"
        else:
            return "Closed"