# src/utils/helpers.py
import os
import time
from pathlib import Path

from config.settings import STOCKS_LIST_FILE
from config.logging_config import logger


def read_stocks_list(file_path=None):
    """Read list of stocks from a text file.

    Args:
        file_path: Path to the text file (if None, default path is used)

    Returns:
        List of stock symbols
    """
    if file_path is None:
        file_path = STOCKS_LIST_FILE

    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"Stocks list file not found: {file_path}")
        return []

    try:
        with open(file_path, 'r') as f:
            # Read lines and strip whitespace
            stocks = [line.strip() for line in f.readlines()]
            # Filter out empty lines and comments
            stocks = [stock for stock in stocks if stock and not stock.startswith('#')]

        logger.info(f"Read {len(stocks)} stocks from {file_path}")
        return stocks
    except Exception as e:
        logger.error(f"Error reading stocks list: {e}")
        return []


def generate_ssl_cert(cert_path, key_path):
    """Generate self-signed SSL certificate.

    Args:
        cert_path: Path to save certificate
        key_path: Path to save key

    Returns:
        Boolean indicating success
    """
    try:
        from OpenSSL import crypto

        # Create key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)

        # Create self-signed certificate
        cert = crypto.X509()
        cert.get_subject().C = "IN"
        cert.get_subject().ST = "Karnataka"
        cert.get_subject().L = "Bangalore"
        cert.get_subject().O = "Trading System"
        cert.get_subject().OU = "Trading System"
        cert.get_subject().CN = "localhost"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  # 10 years
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        # Create directory if it doesn't exist
        cert_path.parent.mkdir(parents=True, exist_ok=True)

        # Save certificate and key
        with open(cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        with open(key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

        logger.info(f"Generated SSL certificate: {cert_path} and key: {key_path}")

        return True
    except Exception as e:
        logger.error(f"Error generating SSL certificate: {e}")
        return False


def rate_limit_api_calls(func, max_calls=10, time_window=60):
    """Rate limit API calls.

    Args:
        func: Function to rate limit
        max_calls: Maximum number of calls allowed in time window
        time_window: Time window in seconds

    Returns:
        Rate-limited function
    """
    calls = []

    def rate_limited_func(*args, **kwargs):
        now = time.time()

        # Remove calls outside the time window
        calls[:] = [call for call in calls if now - call < time_window]

        # Check if we've reached the limit
        if len(calls) >= max_calls:
            # Calculate time to wait
            wait_time = calls[0] + time_window - now
            logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)

            # Start with a fresh list
            calls.clear()

        # Add current call
        calls.append(time.time())

        # Call the function
        return func(*args, **kwargs)

    return rate_limited_func