# src/data_fetcher/live_data.py

import datetime
import pandas as pd
import pytz
import time
import os
import json
from pathlib import Path

from config.logging_config import logger
from config.settings import MARKET_OPEN_TIME, MARKET_CLOSE_TIME, DATA_DIR


class LiveDataFetcher:
    def __init__(self, kite_client):
        """Initialize the live data fetcher.

        Args:
            kite_client: Authenticated KiteConnect client
        """
        self.kite = kite_client
        self.indian_tz = pytz.timezone('Asia/Kolkata')
        self.cache_dir = DATA_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.option_cache = {}
        self.last_api_call = 0
        self.rate_limit_count = 0
        self.max_rate_limit = 30  # Adjust based on Zerodha's actual rate limits
        self.rate_window = 60  # Time window in seconds

    def is_market_open(self):
        """Check if the market is currently open.

        Returns:
            Boolean indicating if market is open
        """
        try:
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
                logger.info(
                    f"Market is closed (Current time: {current_time}, Market hours: {market_open}-{market_close})")
                return False
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False

    def get_quote(self, symbols):
        """Get live quotes for a list of symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary of quotes for each symbol
        """
        if not symbols:
            logger.warning("No symbols provided for quotes")
            return {}

        try:
            # Apply rate limiting
            self._rate_limit_api_call()

            logger.debug(f"Fetching quotes for {len(symbols)} symbols")
            # Prepare symbols with exchange prefix
            exchange_symbols = [f"NSE:{symbol}" for symbol in symbols]
            quotes = self.kite.quote(exchange_symbols)

            logger.debug(f"Received quotes for {len(quotes)} symbols")
            return quotes
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}

    def _rate_limit_api_call(self):
        """Implement rate limiting for API calls.

        Returns:
            Boolean indicating if API call should proceed
        """
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        # Reset rate limit counter if we're outside the window
        if time_since_last_call > self.rate_window:
            self.rate_limit_count = 0

        # Check if we've hit the rate limit
        if self.rate_limit_count >= self.max_rate_limit:
            # Calculate time to wait
            wait_time = self.rate_window - time_since_last_call
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                self.rate_limit_count = 0

        # Update last call time and increment counter
        self.last_api_call = time.time()
        self.rate_limit_count += 1
        return True

    def _get_option_cache_path(self, symbol, expiry_date=None):
        """Get path for cached option data."""
        if expiry_date:
            expiry_str = expiry_date.strftime('%Y%m%d')
            return self.cache_dir / f"{symbol}_options_{expiry_str}.json"
        else:
            return self.cache_dir / f"{symbol}_options.json"

    def _load_cached_option_data(self, symbol, expiry_date=None):
        """Load option data from cache if available and fresh."""
        cache_path = self._get_option_cache_path(symbol, expiry_date)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is still valid (less than 1 hour old)
            cache_time = cache_data.get('timestamp', 0)
            if time.time() - cache_time <= 3600:  # 1 hour in seconds
                logger.info(f"Using cached option data for {symbol}")
                return pd.DataFrame(cache_data.get('data', []))

        except Exception as e:
            logger.error(f"Error loading cached option data: {e}")

        return None

    def _save_option_data_to_cache(self, symbol, option_data, expiry_date=None):
        """Save option data to cache."""
        if option_data.empty:
            return

        cache_path = self._get_option_cache_path(symbol, expiry_date)

        try:
            # Convert DataFrame to dict with date handling
            data_records = []
            for _, row in option_data.iterrows():
                record = {}
                for column, value in row.items():
                    # Convert datetime/date objects to ISO format strings
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        record[column] = value.isoformat()
                    else:
                        record[column] = value
                data_records.append(record)

            cache_data = {
                'timestamp': time.time(),
                'data': data_records
            }

            # Convert expiry_date if it's a datetime object
            if isinstance(expiry_date, (datetime.datetime, datetime.date)):
                expiry_str = expiry_date.isoformat()
                logger.debug(f"Converted expiry date {expiry_date} to string {expiry_str} for caching")

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            logger.info(f"Saved option data to cache for {symbol}")

        except Exception as e:
            logger.error(f"Error saving option data to cache: {e}")

    # Also need to update the _load_cached_option_data method to handle date strings:

    def _load_cached_option_data(self, symbol, expiry_date=None):
        """Load option data from cache if available and fresh."""
        cache_path = self._get_option_cache_path(symbol, expiry_date)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is still valid (less than 1 hour old)
            cache_time = cache_data.get('timestamp', 0)
            if time.time() - cache_time <= 3600:  # 1 hour in seconds
                logger.info(f"Using cached option data for {symbol}")

                # Convert cache data to DataFrame
                df = pd.DataFrame(cache_data.get('data', []))

                # Convert date strings back to datetime objects if needed
                if not df.empty and 'expiry' in df.columns:
                    try:
                        df['expiry'] = pd.to_datetime(df['expiry'])
                    except Exception as e:
                        logger.warning(f"Could not convert expiry to datetime: {e}")

                return df

        except Exception as e:
            logger.error(f"Error loading cached option data: {e}")

        return None

    def get_live_option_chain(self, symbol, expiry_date=None):
        """Get live option chain for a symbol.

        Args:
            symbol: Stock symbol
            expiry_date: Option expiry date (if None, monthly expiry is used)

        Returns:
            DataFrame with option chain data
        """
        # Initialize option_data as an empty list at the beginning to avoid undefined errors
        option_data = []

        # Try to get from cache first
        cached_data = self._load_cached_option_data(symbol, expiry_date)
        if cached_data is not None and not cached_data.empty:
            return cached_data

        # Additional option chain specific rate limiting
        current_time = time.time()
        time_since_last_call = current_time - getattr(self, 'last_option_chain_call', 0)

        # Force at least 3 seconds between option chain requests
        if time_since_last_call < 3:
            sleep_time = 3 - time_since_last_call
            logger.info(f"Rate limiting option chain requests. Waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

        self.last_option_chain_call = time.time()

        try:
            logger.info(f"Fetching option chain for {symbol}")

            # Check rate limits before making API calls
            self._rate_limit_api_call()

            # Get all instruments for the symbol
            instruments = self.kite.instruments("NFO")

            # Filter instruments for the given symbol - more flexible matching
            symbol_instruments = []
            for inst in instruments:
                # Check either the name or the tradingsymbol contains our symbol
                if ((inst.get('name') == symbol) or
                        (symbol in inst.get('tradingsymbol', '')) or
                        (inst.get('tradingsymbol', '').startswith(symbol))):
                    symbol_instruments.append(inst)

            if not symbol_instruments:
                logger.warning(f"No option instruments found for {symbol}")
                return pd.DataFrame()

            # Get expiry dates
            expiry_dates = sorted(list(set([inst['expiry'] for inst in symbol_instruments if inst['expiry']])))

            if not expiry_dates:
                logger.warning(f"No expiry dates found for {symbol}")
                return pd.DataFrame()

            # Log all available expiry dates for debugging
            logger.info(f"Available expiry dates for {symbol}: {expiry_dates}")

            # If expiry date is not provided, use the monthly expiry date
            if not expiry_date:
                # Try to find the monthly expiry (usually the last expiry in the month)
                from datetime import datetime
                current_month = datetime.now().month

                # Find expiries in the current month
                current_month_expiries = [date for date in expiry_dates
                                          if isinstance(date, datetime) and date.month == current_month]

                if current_month_expiries:
                    # Use the last expiry of current month
                    expiry_date = max(current_month_expiries)
                else:
                    # Use the earliest expiry if no current month expiry found
                    expiry_date = expiry_dates[0]

                logger.info(f"Using expiry date: {expiry_date}")

            # Filter instruments for the selected expiry
            expiry_instruments = [
                inst for inst in symbol_instruments
                if inst['expiry'] == expiry_date and inst['instrument_type'] in ['CE', 'PE']
            ]

            if not expiry_instruments:
                # Try to find any instruments for this symbol
                logger.warning(f"No instruments found for {symbol} with expiry {expiry_date}")
                logger.info(f"Attempting to find any options for {symbol}")

                # Use the first available expiry instead
                if expiry_dates:
                    alternative_expiry = expiry_dates[0]
                    logger.info(f"Trying alternative expiry: {alternative_expiry}")
                    expiry_instruments = [
                        inst for inst in symbol_instruments
                        if inst['expiry'] == alternative_expiry and inst['instrument_type'] in ['CE', 'PE']
                    ]

                    if expiry_instruments:
                        logger.info(f"Found {len(expiry_instruments)} options using alternative expiry")
                        expiry_date = alternative_expiry

                if not expiry_instruments:
                    return pd.DataFrame()

            # Get quotes for these instruments
            instrument_tokens = [inst['instrument_token'] for inst in expiry_instruments]
            instrument_symbols = [f"NFO:{inst['tradingsymbol']}" for inst in expiry_instruments]

            # Limit the number of instruments to query to reduce API load
            max_instruments = 10  # Adjust based on needs
            if len(instrument_symbols) > max_instruments:
                # Get at-the-money options and a few around them
                atm_strike = expiry_instruments[len(expiry_instruments) // 2]['strike']
                nearest_instruments = sorted(
                    expiry_instruments,
                    key=lambda x: abs(x['strike'] - atm_strike)
                )[:max_instruments]

                instrument_symbols = [f"NFO:{inst['tradingsymbol']}" for inst in nearest_instruments]
                expiry_instruments = nearest_instruments
                logger.info(f"Limited to {max_instruments} options near ATM for {symbol}")

            # Batch quotes in smaller chunks to avoid rate limiting
            chunk_size = 5  # Smaller chunks to avoid rate limits
            all_quotes = {}

            for i in range(0, len(instrument_symbols), chunk_size):
                # Check rate limits before each chunk
                self._rate_limit_api_call()

                chunk = instrument_symbols[i:i + chunk_size]
                try:
                    quotes_chunk = self.kite.quote(chunk)
                    all_quotes.update(quotes_chunk)

                    # Add significant delay between chunks
                    time.sleep(2)  # 2 seconds between chunks
                except Exception as e:
                    logger.error(f"Error fetching quotes chunk for {symbol}: {e}")
                    # Don't immediately fail - continue with partial data
                    time.sleep(5)  # Longer delay after error

            # Prepare option chain data - ensuring option_data is initialized
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
                        'iv': quote.get('oi', 0) / 1000 if quote.get('oi', 0) > 0 else 0,  # Approximation
                    })

            # Convert to DataFrame
            df = pd.DataFrame(option_data)
            logger.info(f"Found {len(df)} option contracts for {symbol} with expiry {expiry_date}")

            # Cache the data for future use
            self._save_option_data_to_cache(symbol, df, expiry_date)

            return df

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            # Return empty DataFrame if anything fails
            return pd.DataFrame()

    def get_market_status(self):
        """Get current market status.

        Returns:
            String with market status
        """
        try:
            if self.is_market_open():
                return "Open"
            else:
                return "Closed"
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return "Unknown"