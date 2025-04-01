# Trading System

An automated trading system that integrates with Zerodha API to perform technical analysis and generate trading signals for stocks and options.

## Features

- Automated authentication with Zerodha API
- Historical data fetching and caching
- Live market data integration
- Comprehensive technical analysis with multiple indicators
- Support and resistance level calculation
- Option selection and analysis
- Trading signal generation with confidence levels
- Position sizing recommendations
- Output in JSON and CSV formats

## System Requirements

- Python 3.8 or higher
- Zerodha account with API access
- Internet connection

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/trading-system.git
   cd trading-system
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Zerodha API credentials in a `.env` file:
   ```
   # Copy the sample .env file
   cp .env.sample .env
   
   # Edit the .env file with your credentials
   # Replace your_api_key_here and your_api_secret_here with your actual credentials
   ```

## Configuration

The system can be configured by modifying the `config/settings.py` file. Key settings include:

- API credentials and redirect URL
- Market open/close times
- Technical analysis parameters
- Risk management settings
- Data directories

## Usage

1. Prepare a list of stocks to analyze in `data/stocks_list.txt`, one symbol per line.

2. Run the system:
   ```
   python main.py
   ```

3. Command-line options:
   ```
   python main.py --help
   ```

   Available options:
   - `--force-update`: Force update historical data
   - `--days`: Number of days of historical data to fetch

4. Output:
   - The system will generate JSON and/or CSV files in the `data/output/` directory.
   - Each run creates a timestamped file with signals for all analyzed stocks.

## Authentication

The system uses Zerodha's OAuth authentication flow:

1. On first run, it will open a browser window for you to log in to your Zerodha account.
2. After logging in, Zerodha will redirect to `https://localhost:5000/redirect` with the authentication token.
3. The system securely stores the access token for future use.

## SSL Certificates

The system requires HTTPS for the authentication callback. SSL certificates are automatically generated when you first run the script. No manual certificate creation is needed.

## Output Format

The system generates a comprehensive analysis for each stock in JSON format:

```json
{
  "basic_info": {
    "symbol": "AARTIIND",
    "previous_close": 395.5,
    "current_price": 390.75,
    "volatility_percent": 35.72
  },
  "signal_info": {
    "signal": "Buy PUT Option",
    "direction": "DOWN",
    "confidence_percent": 17.0,
    "profit_probability_percent": 17.0
  },
  "price_targets": {
    "target_price": 382.1,
    "stop_loss_price": 406.38,
    "risk_reward_ratio": 0.55,
    "days_to_target": 1
  },
  "technical_indicators": {
    "technical_trend_score": 41.0,
    "momentum_score": 0.45,
    "rsi": 43.66,
    "adx": 20.04,
    "macd": -5.46,
    "volume_change_percent": -21.95
  },
  "support_resistance": {
    "support_levels": [364.15, 367.3, 382.1],
    "resistance_levels": [406.38, 414.2, 414.4]
  },
  "position_sizing": {
    "recommendation": "Max 127 shares (₹49,625.25, 49.6% of portfolio) based on 2.0% max risk per trade"
  },
  "option_info": {
    "underlying_strike": 390,
    "selected_strike": 385,
    "strike_type": "PE",
    "iv_percentile": 65.4,
    "max_pain_price": 390,
    "open_interest_analysis": "OI: 2452, Volume: 1145. Moderate liquidity."
  },
  "option_prices": {
    "current_price": 5.8,
    "target_price": 8.7,
    "stop_loss": 4.06
  },
  "risk_factors": {
    "earnings_impact_risk": "Low",
    "days_to_earnings": 66
  },
  "metadata": {
    "trading_symbol": "AARTIINDAPR385PE",
    "expiry_date": "2025-04-24",
    "analysis_timestamp": "2025-03-30 16:27:09",
    "market_status": "Closed"
  }
}
```

## Project Structure

```
trading_system/
├── config/
│   ├── __init__.py
│   ├── settings.py                # Global configuration settings
│   └── logging_config.py          # Logging configuration
├── data/
│   ├── historical/                # Directory to store historical data
│   ├── processed/                # Directory to store processed data
│   ├── stocks_list.txt            # List of stocks to analyze
│   └── output/                    # Output directory for JSON/CSV files
├── certs/
│   ├── cert.pem                   # SSL certificate
│   └── key.pem                    # SSL key
├── logs/
│   └── trading_system.log         # Log file
├── src/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── zerodha_auth.py        # Zerodha authentication module
│   ├── data_fetcher/
│   │   ├── __init__.py
│   │   ├── historical_data.py     # Historical data fetcher
│   │   └── live_data.py           # Live data fetcher
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── technical_analysis.py  # Technical analysis module
│   │   ├── options_analysis.py    # Options analysis module
│   │   └── support_resistance.py  # Support & resistance calculator
│   ├── signal_generator/
│   │   ├── __init__.py
│   │   └── trading_signals.py     # Trading signal generator
│   ├── output/
│   │   ├── __init__.py
│   │   ├── json_formatter.py      # JSON output formatter
│   │   └── csv_formatter.py       # CSV output formatter
│   └── utils/
│       ├── __init__.py
│       └── helpers.py             # Helper functions
├── main.py                        # Main entry point
├── requirements.txt               # Dependencies
└── README.md                      # Documentation
```

## License

MIT License