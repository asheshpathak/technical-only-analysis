# src/data_fetcher/historical_data.py
import os
import pandas as pd
import datetime
import time
from pathlib import Path
from dateutil.relativedelta import relativedelta
import pytz

from config.settings import HISTORICAL_DATA_DIR
from config.logging_config import logger


class HistoricalDataFetcher:
    def __init__(self, kite_client):
        """Initialize the historical data fetcher.

        Args:
            kite_client: Authenticated KiteConnect client
        """
        self.kite = kite_client
        self.historical_data_dir = HISTORICAL_DATA_DIR
        self.historical_data_dir.mkdir(parents=True, exist_ok=True)
        self.indian_tz = pytz.timezone('Asia/Kolkata')

    def _get_file_path(self, symbol, interval='day'):
        """Get the file path for historical data.

        Args:
            symbol: Stock symbol
            interval: Data interval (day, minute, etc.)

        Returns:
            Path object for the historical data file
        """
        return self.historical_data_dir / f"{symbol}_{interval}.csv"

    def _is_data_up_to_date(self, symbol, interval='day'):
        """Check if historical data is up to date.

        Args:
            symbol: Stock symbol
            interval: Data interval

        Returns:
            Boolean indicating if data is up to date
        """
        file_path = self._get_file_path(symbol, interval)

        if not file_path.exists():
            logger.debug(f"No historical data found for {symbol}")
            return False

        try:
            data = pd.read_csv(file_path)
            if data.empty:
                logger.debug(f"Empty historical data for {symbol}")
                return False

            last_date = pd.to_datetime(data['date'].iloc[-1])
            current_date = datetime.datetime.now(self.indian_tz).date()

            # For daily data, check if last date is recent (considering weekends and holidays)
            if interval == 'day':
                # If today is Monday and we have data from Friday (or weekend), it's up to date
                if current_date.weekday() == 0:  # Monday
                    return (current_date - last_date.date()).days <= 3
                # Otherwise, we should have data from yesterday or today
                return (current_date - last_date.date()).days <= 1

            # For minute data, check if we have today's data
            return last_date.date() == current_date

        except Exception as e:
            logger.error(f"Error checking if data is up to date for {symbol}: {e}")
            return False

    def _fetch_historical_data(self, instrument_token, from_date, to_date, interval='day'):
        """Fetch historical data for a given instrument.

        Args:
            instrument_token: Zerodha instrument token
            from_date: Start date
            to_date: End date
            interval: Data interval

        Returns:
            DataFrame with historical data
        """
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                logger.debug(f"Fetching historical data for token {instrument_token} from {from_date} to {to_date}")
                data = self.kite.historical_data(
                    instrument_token=instrument_token,
                    from_date=from_date,
                    to_date=to_date,
                    interval=interval
                )

                if not data:
                    logger.warning(f"No historical data returned for token {instrument_token}")
                    return pd.DataFrame()

                df = pd.DataFrame(data)
                return df

            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries}: Error fetching historical data: {e}")
                time.sleep(2)  # Wait before retrying to avoid rate limits

        logger.error(f"Failed to fetch historical data after {max_retries} retries")
        return pd.DataFrame()

    def get_instrument_token(self, symbol):
        """Get instrument token for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Instrument token
        """
        try:
            instruments = self.kite.instruments("NSE")
            for instrument in instruments:
                if instrument['tradingsymbol'] == symbol:
                    return instrument['instrument_token']

            logger.error(f"Instrument token not found for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error fetching instrument token for {symbol}: {e}")
            return None

    def update_historical_data(self, symbol, interval='day', days=365):
        """Update historical data for a symbol.

        Args:
            symbol: Stock symbol
            interval: Data interval
            days: Number of days of historical data to fetch

        Returns:
            DataFrame with historical data
        """
        file_path = self._get_file_path(symbol, interval)
        instrument_token = self.get_instrument_token(symbol)

        if not instrument_token:
            logger.error(f"Cannot update historical data without instrument token for {symbol}")
            return pd.DataFrame()

        to_date = datetime.datetime.now(self.indian_tz)
        from_date = to_date - relativedelta(days=days)

        logger.info(f"Updating historical data for {symbol} from {from_date.date()} to {to_date.date()}")

        df = self._fetch_historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )

        if not df.empty:
            df.to_csv(file_path, index=False)
            logger.info(f"Historical data for {symbol} saved to {file_path}")

        return df

    def get_historical_data(self, symbol, interval='day', days=365, force_update=False):
        """Get historical data for a symbol.

        Args:
            symbol: Stock symbol
            interval: Data interval
            days: Number of days of historical data
            force_update: Force update even if data is up to date

        Returns:
            DataFrame with historical data
        """
        file_path = self._get_file_path(symbol, interval)

        # Check if we need to update the data
        if force_update or not self._is_data_up_to_date(symbol, interval):
            logger.info(f"Historical data for {symbol} is not up to date. Updating...")
            return self.update_historical_data(symbol, interval, days)

        # Load existing data
        try:
            logger.debug(f"Loading historical data for {symbol} from {file_path}")
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            logger.error(f"Error loading historical data for {symbol}: {e}")
            return self.update_historical_data(symbol, interval, days)

    def get_historical_data_for_all(self, symbols, interval='day', days=365, force_update=False):
        """Get historical data for all symbols.

        Args:
            symbols: List of stock symbols
            interval: Data interval
            days: Number of days of historical data
            force_update: Force update even if data is up to date

        Returns:
            Dictionary of DataFrame with historical data for each symbol
        """
        result = {}
        total_symbols = len(symbols)

        for index, symbol in enumerate(symbols, 1):
            logger.info(f"Processing {index}/{total_symbols}: {symbol}")
            result[symbol] = self.get_historical_data(symbol, interval, days, force_update)
            time.sleep(0.5)  # Small delay to avoid hitting rate limits

        return result