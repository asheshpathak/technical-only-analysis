# src/output/csv_formatter.py
import csv
import pandas as pd
import datetime
from pathlib import Path

from config.settings import OUTPUT_DIR
from config.logging_config import logger


class CSVFormatter:
    def __init__(self):
        """Initialize the CSV formatter."""
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_signal(self, signal_data):
        """Format signal data to CSV row.

        Args:
            signal_data: Dictionary with signal data

        Returns:
            Dictionary with flattened data for CSV row
        """
        try:
            # Flatten nested structure
            flat_data = {}

            # Basic info
            basic_info = signal_data.get("basic_info", {})
            for key, value in basic_info.items():
                flat_data[f"basic_{key}"] = value

            # Signal info
            signal_info = signal_data.get("signal_info", {})
            for key, value in signal_info.items():
                flat_data[f"signal_{key}"] = value

            # Price targets
            price_targets = signal_data.get("price_targets", {})
            for key, value in price_targets.items():
                flat_data[f"price_{key}"] = value

            # Technical indicators
            tech_indicators = signal_data.get("technical_indicators", {})
            for key, value in tech_indicators.items():
                flat_data[f"tech_{key}"] = value

            # Support resistance - convert lists to strings
            support_resistance = signal_data.get("support_resistance", {})
            if "support_levels" in support_resistance:
                flat_data["support_levels"] = ",".join([str(x) for x in support_resistance["support_levels"]])
            if "resistance_levels" in support_resistance:
                flat_data["resistance_levels"] = ",".join([str(x) for x in support_resistance["resistance_levels"]])

            # Position sizing
            position_sizing = signal_data.get("position_sizing", {})
            flat_data["position_recommendation"] = position_sizing.get("recommendation", "")

            # Option info
            option_info = signal_data.get("option_info", {})
            for key, value in option_info.items():
                flat_data[f"option_{key}"] = value

            # Option prices
            option_prices = signal_data.get("option_prices", {})
            for key, value in option_prices.items():
                flat_data[f"option_price_{key}"] = value

            # Risk factors
            risk_factors = signal_data.get("risk_factors", {})
            for key, value in risk_factors.items():
                flat_data[f"risk_{key}"] = value

            # Metadata
            metadata = signal_data.get("metadata", {})
            for key, value in metadata.items():
                flat_data[f"meta_{key}"] = value

            return flat_data

        except Exception as e:
            logger.error(f"Error formatting signal to CSV: {e}")
            return {}

    def save_signal(self, signal_data, filename=None):
        """Save signal data to CSV file.

        Args:
            signal_data: Dictionary with signal data
            filename: Output filename (if None, generated from symbol)

        Returns:
            Path to saved file
        """
        try:
            # Get symbol
            symbol = signal_data.get("basic_info", {}).get("symbol", "unknown")

            # Generate filename if not provided
            if not filename:
                filename = f"{symbol}_signal.csv"

            # Ensure .csv extension
            if not filename.endswith('.csv'):
                filename += '.csv'

            # Create full path
            file_path = self.output_dir / filename

            # Format data
            flat_data = self.format_signal(signal_data)

            # Convert to DataFrame
            df = pd.DataFrame([flat_data])

            # Write to file
            df.to_csv(file_path, index=False)

            logger.info(f"Saved signal data to {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"Error saving signal to CSV file: {e}")
            return None

    def save_all_signals(self, signals_data, filename="trading_signals.csv"):
        """Save all signals data to a single CSV file.

        Args:
            signals_data: Dictionary with signal data for multiple symbols
            filename: Output filename (defaults to a fixed name)

        Returns:
            Path to saved file
        """
        try:
            # Create full path
            file_path = self.output_dir / filename

            # Format all signals
            all_flat_data = []
            for symbol, signal_data in signals_data.items():
                flat_data = self.format_signal(signal_data)
                all_flat_data.append(flat_data)

            # Convert to DataFrame
            df = pd.DataFrame(all_flat_data)

            # Write to file
            df.to_csv(file_path, index=False)

            logger.info(f"Saved all signals data to {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"Error saving all signals to CSV file: {e}")
            return None