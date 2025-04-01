#!/usr/bin/env python
# main.py - Trading System Entry Point

import os
import sys
import time
import datetime
import argparse
from pathlib import Path

# Add the project directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import (
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    HISTORICAL_DATA_DIR,
    OUTPUT_DIR,
    STOCKS_LIST_FILE
)
from config.logging_config import logger
from src.auth.zerodha_auth import ZerodhaAuth
from src.data_fetcher.historical_data import HistoricalDataFetcher
from src.data_fetcher.live_data import LiveDataFetcher
from src.signal_generator.trading_signals import TradingSignalGenerator
from src.output.json_formatter import JSONFormatter
from src.output.csv_formatter import CSVFormatter
from src.utils.helpers import read_stocks_list, generate_ssl_cert


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Trading System")

    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update historical data"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of historical data to fetch"
    )

    args = parser.parse_args()

    # Ensure minimum days for technical analysis
    if args.days < 30:
        logger.warning(
            f"Specified days ({args.days}) is too low for reliable technical analysis. Setting to minimum of 30 days.")
        args.days = 30

    return args


def setup_directories():
    """Set up required directories and certificates."""
    # Ensure directories exist
    HISTORICAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create SSL certificates directory if it doesn't exist
    ssl_dir = SSL_CERT_FILE.parent
    ssl_dir.mkdir(parents=True, exist_ok=True)

    # Always generate SSL certificates if they don't exist
    if not SSL_CERT_FILE.exists() or not SSL_KEY_FILE.exists():
        logger.info("SSL certificates not found. Generating...")
        success = generate_ssl_cert(SSL_CERT_FILE, SSL_KEY_FILE)
        if not success:
            logger.error("Failed to generate SSL certificates.")
            sys.exit(1)
        logger.info("SSL certificates generated successfully.")
    else:
        logger.info("Using existing SSL certificates.")


def main():
    """Main entry point for the trading system."""
    # Parse command line arguments
    args = parse_arguments()

    # Setup directories and certificates
    setup_directories()

    # Start time
    start_time = time.time()
    logger.info("Starting trading system...")

    try:
        # Step 1: Authenticate with Zerodha API
        logger.info("Step 1: Authenticating with Zerodha API")
        auth = ZerodhaAuth()
        kite = auth.get_kite_client()

        # Step 2: Read stocks list
        logger.info("Step 2: Reading stocks list")
        stocks = read_stocks_list(STOCKS_LIST_FILE)

        if not stocks:
            logger.error("No stocks found in the stocks list file. Exiting.")
            sys.exit(1)

        logger.info(f"Found {len(stocks)} stocks to analyze")

        # Step 3: Initialize data fetchers
        logger.info("Step 3: Initializing data fetchers")
        historical_data_fetcher = HistoricalDataFetcher(kite)
        live_data_fetcher = LiveDataFetcher(kite)

        # Step 4: Check if market is open
        logger.info("Step 4: Checking market status")
        market_open = live_data_fetcher.is_market_open()

        # Step 5: Fetch historical data for all stocks
        logger.info("Step 5: Fetching historical data")
        historical_data = {}

        for i, symbol in enumerate(stocks, 1):
            logger.info(f"Fetching historical data for {symbol} ({i}/{len(stocks)})")
            df = historical_data_fetcher.get_historical_data(
                symbol=symbol,
                interval='day',
                days=args.days,
                force_update=args.force_update
            )

            if df.empty:
                logger.warning(f"No historical data found for {symbol}")
                continue

            historical_data[symbol] = df

            # Add a small delay to avoid rate limits
            time.sleep(0.5)

        # Step 6: Initialize signal generator
        logger.info("Step 6: Initializing signal generator")
        signal_generator = TradingSignalGenerator(kite, live_data_fetcher)

        # Step 7: Generate signals for each stock
        logger.info("Step 7: Generating signals")
        signals = {}

        for i, symbol in enumerate(stocks, 1):
            if symbol not in historical_data or historical_data[symbol].empty:
                logger.warning(f"Skipping {symbol} due to missing historical data")
                continue

            logger.info(f"Generating signal for {symbol} ({i}/{len(stocks)})")
            signal = signal_generator.generate_signal(symbol, historical_data[symbol])
            signals[symbol] = signal

            # Print signal to console
            logger.info(
                f"{symbol}: {signal['signal_info']['signal']} with {signal['signal_info']['confidence_percent']}% confidence")

            # Add a small delay to avoid rate limits
            time.sleep(0.5)

        # Step 8: Format and save results
        logger.info("Step 8: Formatting and saving results")
        json_formatter = JSONFormatter()
        csv_formatter = CSVFormatter()

        # Save both JSON and CSV with fixed filenames
        json_path = json_formatter.save_all_signals(signals, "trading_signals.json")
        csv_path = csv_formatter.save_all_signals(signals, "trading_signals.csv")

        logger.info(f"Saved signals as JSON to {json_path}")
        logger.info(f"Saved signals as CSV to {csv_path}")

        # Generate timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save both JSON and CSV
        json_path = json_formatter.save_all_signals(signals, f"signals_{timestamp}.json")
        csv_path = csv_formatter.save_all_signals(signals, f"signals_{timestamp}.csv")

        logger.info(f"Saved signals as JSON to {json_path}")
        logger.info(f"Saved signals as CSV to {csv_path}")

        # End time
        end_time = time.time()
        logger.info(f"Trading system completed in {end_time - start_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Error in trading system: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()