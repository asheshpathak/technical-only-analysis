# src/output/json_formatter.py
import json
import os
import datetime
from pathlib import Path

from config.settings import OUTPUT_DIR
from config.logging_config import logger


class JSONFormatter:
    def __init__(self):
        """Initialize the JSON formatter."""
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_signal(self, signal_data):
        """Format signal data to JSON.

        Args:
            signal_data: Dictionary with signal data

        Returns:
            JSON string
        """
        try:
            # Convert to JSON with proper formatting
            json_str = json.dumps(signal_data, indent=2)
            return json_str
        except Exception as e:
            logger.error(f"Error formatting signal to JSON: {e}")
            return "{}"

    def save_signal(self, signal_data, filename=None):
        """Save signal data to JSON file.

        Args:
            signal_data: Dictionary with signal data
            filename: Output filename (if None, generated from symbol and timestamp)

        Returns:
            Path to saved file
        """
        try:
            # Get symbol and timestamp
            symbol = signal_data.get("basic_info", {}).get("symbol", "unknown")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Generate filename if not provided
            if not filename:
                filename = f"{symbol}_{timestamp}.json"

            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'

            # Create full path
            file_path = self.output_dir / filename

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(signal_data, f, indent=2)

            logger.info(f"Saved signal data to {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"Error saving signal to JSON file: {e}")
            return None

    def save_all_signals(self, signals_data, filename=None):
        """Save all signals data to a single JSON file.

        Args:
            signals_data: Dictionary with signal data for multiple symbols
            filename: Output filename (if None, generated from timestamp)

        Returns:
            Path to saved file
        """
        try:
            # Generate timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Generate filename if not provided
            if not filename:
                filename = f"all_signals_{timestamp}.json"

            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'

            # Create full path
            file_path = self.output_dir / filename

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(signals_data, f, indent=2)

            logger.info(f"Saved all signals data to {file_path}")

            return file_path

        except Exception as e:
            logger.error(f"Error saving all signals to JSON file: {e}")
            return None