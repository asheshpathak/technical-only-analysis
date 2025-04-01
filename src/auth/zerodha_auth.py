# src/auth/zerodha_auth.py
import os
import json
import webbrowser
from flask import Flask, request
from kiteconnect import KiteConnect
from pathlib import Path
import ssl

from config.settings import (
    ZERODHA_API_KEY,
    ZERODHA_API_SECRET,
    ZERODHA_REDIRECT_URL,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    DATA_DIR
)
from config.logging_config import logger


class ZerodhaAuth:
    def __init__(self):
        """Initialize the Zerodha authentication module."""
        self.api_key = ZERODHA_API_KEY
        self.api_secret = ZERODHA_API_SECRET
        self.redirect_url = ZERODHA_REDIRECT_URL
        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None
        self.token_path = DATA_DIR / "access_token.json"
        self.app = Flask(__name__)
        self.setup_routes()
        self.ssl_context = self._create_ssl_context()

    def _create_ssl_context(self):
        """Create SSL context for HTTPS server."""
        if not SSL_CERT_FILE.exists() or not SSL_KEY_FILE.exists():
            logger.error("SSL certificates not found. Please ensure cert.pem and key.pem exist in the certs directory.")
            raise FileNotFoundError("SSL certificate files are missing")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)
        return context

    def setup_routes(self):
        """Set up Flask routes for authentication callback."""

        @self.app.route('/redirect')
        def redirect_url():
            request_token = request.args.get('request_token')
            if not request_token:
                return "Request token not found. Authentication failed."

            try:
                data = self.kite.generate_session(request_token, api_secret=self.api_secret)
                self.access_token = data["access_token"]
                self.save_token()
                logger.info("Authentication successful. Access token received and saved.")
                return "Authentication successful. You can close this window now."
            except Exception as e:
                logger.error(f"Error generating session: {e}")
                return f"Error generating session: {e}"

    def authenticate(self):
        """Authenticate with Zerodha API."""
        if self.load_token():
            logger.info("Using existing access token")
            self.kite.set_access_token(self.access_token)
            return True

        logger.info("No valid access token found. Starting authentication process...")
        login_url = self.kite.login_url()
        logger.info(f"Opening browser for authentication: {login_url}")
        webbrowser.open(login_url)

        # Start the Flask server to handle the redirect
        logger.info("Starting local server to receive authentication callback...")
        self.app.run(host='localhost', port=5000, ssl_context=self.ssl_context)

        return self.access_token is not None

    def save_token(self):
        """Save access token to file."""
        with open(self.token_path, 'w') as f:
            json.dump({
                'access_token': self.access_token,
                'api_key': self.api_key
            }, f)
        logger.debug(f"Access token saved to {self.token_path}")

    def load_token(self):
        """Load access token from file if exists."""
        if not self.token_path.exists():
            logger.debug("Access token file not found")
            return False

        try:
            with open(self.token_path, 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
                if self.access_token:
                    self.kite.set_access_token(self.access_token)
                    logger.debug("Access token loaded successfully")
                    return True
        except Exception as e:
            logger.error(f"Error loading access token: {e}")

        return False

    def get_kite_client(self):
        """Return authenticated KiteConnect client."""
        if not self.access_token:
            success = self.authenticate()
            if not success:
                logger.error("Failed to authenticate with Zerodha")
                raise Exception("Authentication failed")

        return self.kite