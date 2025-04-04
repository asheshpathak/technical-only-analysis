# src/analysis/options_analysis.py
import pandas as pd
import numpy as np
import datetime
import math
from dateutil.relativedelta import relativedelta

from config.logging_config import logger


class OptionsAnalysis:
    def __init__(self, kite_client, live_data_fetcher):
        """Initialize the options analysis module.

        Args:
            kite_client: Authenticated KiteConnect client
            live_data_fetcher: LiveDataFetcher instance
        """
        self.kite = kite_client
        self.live_data_fetcher = live_data_fetcher

    def get_nearest_expiry(self):
        """Get monthly expiry date for options.

        Returns:
            Datetime object with monthly expiry date (last Thursday of current month)
        """
        try:
            # Get current date
            today = datetime.datetime.now().date()

            # Calculate monthly expiry (last Thursday of the month)
            # First, get the next month's first day
            if today.month == 12:
                next_month = datetime.date(today.year + 1, 1, 1)
            else:
                next_month = datetime.date(today.year, today.month + 1, 1)

            # Go back to the last day of the current month
            last_day = next_month - datetime.timedelta(days=1)

            # Calculate days to subtract to get to the last Thursday
            days_to_subtract = (last_day.weekday() - 3) % 7

            # If today is after the monthly expiry, move to next month
            monthly_expiry = last_day - datetime.timedelta(days=days_to_subtract)
            if today > monthly_expiry:
                # Move to next month's last Thursday
                if next_month.month == 12:
                    next_next_month = datetime.date(next_month.year + 1, 1, 1)
                else:
                    next_next_month = datetime.date(next_month.year, next_month.month + 1, 1)

                last_day_next_month = next_next_month - datetime.timedelta(days=1)
                days_to_subtract = (last_day_next_month.weekday() - 3) % 7
                monthly_expiry = last_day_next_month - datetime.timedelta(days=days_to_subtract)

            logger.info(f"Monthly option expiry: {monthly_expiry}")
            return monthly_expiry

        except Exception as e:
            logger.error(f"Error calculating monthly expiry: {e}")
            # Return a default expiry (last Thursday of current month)
            today = datetime.datetime.now().date()
            if today.month == 12:
                next_month = datetime.date(today.year + 1, 1, 1)
            else:
                next_month = datetime.date(today.year, today.month + 1, 1)
            last_day = next_month - datetime.timedelta(days=1)
            days_to_subtract = (last_day.weekday() - 3) % 7
            return last_day - datetime.timedelta(days=days_to_subtract)

    # Now update the get_option_trading_symbol method to use the monthly format:

    def get_option_trading_symbol(self, symbol, strike, option_type, expiry_date=None):
        """Get option trading symbol for monthly expiry.

        Args:
            symbol: Stock symbol
            strike: Option strike price
            option_type: Option type ('CE' or 'PE')
            expiry_date: Option expiry date (if None, monthly expiry is used)

        Returns:
            Option trading symbol
        """
        try:
            # Safety checks
            if not symbol or not strike or not option_type:
                logger.error("Missing required parameters for option trading symbol")
                return None

            # Get monthly expiry if not provided
            if not expiry_date:
                expiry_date = self.get_nearest_expiry()

            # Format expiry date as month only for monthly expiry (e.g., APR)
            expiry_str = expiry_date.strftime('%b').upper()

            # Add the year - for April 2025, we want "APR25"
            year_str = expiry_date.strftime('%y')

            # Format trading symbol (e.g., INFYAPR251600CE)
            trading_symbol = f"{symbol}{expiry_str}{year_str}{strike}{option_type}"

            logger.debug(f"Formatted option trading symbol for monthly expiry: {trading_symbol}")

            return trading_symbol

        except Exception as e:
            logger.error(f"Error getting option trading symbol: {e}")
            return None

    def find_atm_strike(self, current_price):
        """Find at-the-money (ATM) strike price.

        Args:
            current_price: Current price of the underlying

        Returns:
            ATM strike price
        """
        try:
            if current_price is None:
                logger.error("Current price is None, cannot find ATM strike")
                return None

            # Round to nearest 50 or 100 based on price
            if current_price < 1000:
                # For lower-priced stocks, use 5 point interval
                atm_strike = round(current_price / 5) * 5
            elif current_price < 5000:
                # For medium-priced stocks, use 100 point interval
                atm_strike = round(current_price / 100) * 100
            else:
                # For higher-priced stocks, use 500 point interval
                atm_strike = round(current_price / 500) * 500

            logger.debug(f"ATM strike for price {current_price}: {atm_strike}")

            return atm_strike

        except Exception as e:
            logger.error(f"Error finding ATM strike: {e}")
            # Just round to nearest 100 as fallback
            if current_price:
                return round(current_price / 100) * 100
            return None

    def select_option_strike(self, symbol, current_price, signal, expiry_date=None):
        """Select appropriate option strike based on signal.

        Args:
            symbol: Stock symbol
            current_price: Current price of the underlying
            signal: Trading signal ('BUY', 'SELL', 'HOLD')
            expiry_date: Option expiry date (if None, nearest expiry is used)

        Returns:
            Tuple containing selected strike, option type, and underlying strike
        """
        try:
            if current_price is None:
                logger.error(f"Current price is None for {symbol}, cannot select option strike")
                return None, None, None

            # Get nearest expiry if not provided
            if not expiry_date:
                expiry_date = self.get_nearest_expiry()

            # Find ATM strike
            atm_strike = self.find_atm_strike(current_price)

            if atm_strike is None:
                logger.error(f"Could not determine ATM strike for {symbol}")
                return None, None, None

            # Determine option type based on signal
            if signal == "BUY":
                option_type = "CE"  # Call option for bullish signal
            elif signal == "SELL":
                option_type = "PE"  # Put option for bearish signal
            else:
                # For HOLD, decide based on current trend
                # Here we're using a simple above/below ATM heuristic
                if current_price > atm_strike:
                    option_type = "CE"
                else:
                    option_type = "PE"

            # Select strike based on option type
            if option_type == "CE":
                # For calls, select OTM strike
                selected_strike = atm_strike + (50 if current_price < 1000 else 100)
            else:
                # For puts, select OTM strike
                selected_strike = atm_strike - (50 if current_price < 1000 else 100)

            logger.info(
                f"Selected option: {symbol} {expiry_date.strftime('%d%b%y').upper()} {selected_strike}{option_type}")

            return selected_strike, option_type, atm_strike

        except Exception as e:
            logger.error(f"Error selecting option strike for {symbol}: {e}")
            return None, None, None

    def get_option_trading_symbol(self, symbol, strike, option_type, expiry_date=None):
        """Get option trading symbol.

        Args:
            symbol: Stock symbol
            strike: Option strike price
            option_type: Option type ('CE' or 'PE')
            expiry_date: Option expiry date (if None, nearest expiry is used)

        Returns:
            Option trading symbol
        """
        try:
            # Safety checks
            if not symbol or not strike or not option_type:
                logger.error("Missing required parameters for option trading symbol")
                return None

            # Get nearest expiry if not provided
            if not expiry_date:
                expiry_date = self.get_nearest_expiry()

            # Format expiry date (e.g., 30MAR23)
            expiry_str = expiry_date.strftime('%d%b%y').upper()

            # Format trading symbol (e.g., NIFTY23MAR16300CE)
            trading_symbol = f"{symbol}{expiry_str}{strike}{option_type}"

            logger.debug(f"Formatted option trading symbol: {trading_symbol}")

            return trading_symbol

        except Exception as e:
            logger.error(f"Error getting option trading symbol: {e}")
            return None

    def analyze_option(self, symbol, signal, df_stock, target_price, stop_loss, confidence):
        """Analyze option for a stock.

        Args:
            symbol: Stock symbol
            signal: Trading signal ('BUY', 'SELL', 'HOLD')
            df_stock: DataFrame with stock data
            target_price: Target price
            stop_loss: Stop loss price
            confidence: Signal confidence

        Returns:
            Dictionary with option analysis results
        """
        try:
            # Get current price
            current_price = df_stock['close'].iloc[-1] if not df_stock.empty else None

            if not current_price:
                logger.error(f"No price data available for {symbol}")
                return self._create_empty_option_info()

            # Get nearest expiry
            expiry_date = self.get_nearest_expiry()

            # Select appropriate strike and option type
            selected_strike, option_type, underlying_strike = self.select_option_strike(
                symbol=symbol,
                current_price=current_price,
                signal=signal,
                expiry_date=expiry_date
            )

            if not selected_strike or not option_type:
                logger.error(f"Failed to select option strike for {symbol}")
                return self._create_empty_option_info()

            # Get option trading symbol
            trading_symbol = self.get_option_trading_symbol(
                symbol=symbol,
                strike=selected_strike,
                option_type=option_type,
                expiry_date=expiry_date
            )

            # Initialize option data with basic information we can calculate without API
            option_info = {
                "underlying_strike": underlying_strike,
                "selected_strike": selected_strike,
                "strike_type": option_type,
                "iv_percentile": None,
                "max_pain_price": None,
                "open_interest_analysis": "Option data not available"
            }

            option_prices = {
                "current_price": None,
                "target_price": None,
                "stop_loss": None
            }

            # Try to get option chain data, but don't fail if we can't
            try:
                option_chain = self.live_data_fetcher.get_live_option_chain(
                    symbol=symbol,
                    expiry_date=expiry_date
                )

                # If we have option chain data, enhance the analysis
                if not option_chain.empty:
                    # Filter for the selected option
                    selected_option = option_chain[
                        (option_chain['strike'] == selected_strike) &
                        (option_chain['type'] == option_type)
                        ]

                    if not selected_option.empty:
                        # Get option price
                        option_price = selected_option['last_price'].iloc[0]
                        option_prices["current_price"] = option_price

                        # Calculate target and stop loss prices for the option (simplified)
                        price_change_ratio = abs(
                            target_price - current_price) / current_price if target_price and current_price else 0.05

                        if option_type == "CE":
                            if signal == "BUY":
                                # For call options in bullish scenario
                                option_prices["target_price"] = round(option_price * (1 + price_change_ratio * 2), 2)
                                option_prices["stop_loss"] = round(option_price * 0.7, 2)
                            else:
                                # For call options in bearish scenario
                                option_prices["target_price"] = round(option_price * 0.5, 2)
                                option_prices["stop_loss"] = round(option_price * 1.3, 2)
                        else:
                            if signal == "SELL":
                                # For put options in bearish scenario
                                option_prices["target_price"] = round(option_price * (1 + price_change_ratio * 2), 2)
                                option_prices["stop_loss"] = round(option_price * 0.7, 2)
                            else:
                                # For put options in bullish scenario
                                option_prices["target_price"] = round(option_price * 0.5, 2)
                                option_prices["stop_loss"] = round(option_price * 1.3, 2)

                        # Calculate IV percentile (simplified)
                        option_info["iv_percentile"] = round(selected_option['iv'].iloc[0] * 100,
                                                             2) if 'iv' in selected_option.columns else None

                        # Calculate max pain price (simplified)
                        option_info["max_pain_price"] = underlying_strike

                        # Open interest analysis
                        oi = selected_option['open_interest'].iloc[
                            0] if 'open_interest' in selected_option.columns else 0
                        volume = selected_option['volume'].iloc[0] if 'volume' in selected_option.columns else 0

                        if oi > 0 or volume > 0:
                            option_info["open_interest_analysis"] = (
                                f"OI: {oi}, Volume: {volume}. "
                                f"{'High' if oi > 10000 else 'Moderate' if oi > 1000 else 'Low'} liquidity."
                            )
                        else:
                            option_info["open_interest_analysis"] = "Limited option data available"
            except Exception as e:
                logger.warning(f"Error getting option chain for {symbol}: {e}, using estimated values")
                # Continue with estimated values for option prices if we can't get real data

                # Estimate option price based on underlying price and strike (very simplified)
                if option_type == "CE":
                    estimated_price = max(0, current_price - selected_strike) + (
                                current_price * 0.05)  # intrinsic + 5% premium
                else:
                    estimated_price = max(0, selected_strike - current_price) + (
                                current_price * 0.05)  # intrinsic + 5% premium

                option_prices["current_price"] = round(estimated_price, 2)

                # Calculate target and stop loss based on estimated price
                price_change_ratio = abs(
                    target_price - current_price) / current_price if target_price and current_price else 0.05

                if option_type == "CE":
                    if signal == "BUY":
                        option_prices["target_price"] = round(estimated_price * (1 + price_change_ratio * 2), 2)
                        option_prices["stop_loss"] = round(estimated_price * 0.7, 2)
                    else:
                        option_prices["target_price"] = round(estimated_price * 0.5, 2)
                        option_prices["stop_loss"] = round(estimated_price * 1.3, 2)
                else:
                    if signal == "SELL":
                        option_prices["target_price"] = round(estimated_price * (1 + price_change_ratio * 2), 2)
                        option_prices["stop_loss"] = round(estimated_price * 0.7, 2)
                    else:
                        option_prices["target_price"] = round(estimated_price * 0.5, 2)
                        option_prices["stop_loss"] = round(estimated_price * 1.3, 2)

            # Determine option signal
            option_signal = self._determine_option_signal(signal, option_type)

            return {
                "option_info": option_info,
                "option_prices": option_prices,
                "option_signal": option_signal,
                "trading_symbol": trading_symbol,
                "expiry_date": expiry_date.strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.error(f"Error analyzing option for {symbol}: {e}")
            return {
                "option_info": self._create_empty_option_info()["option_info"],
                "option_prices": self._create_empty_option_info()["option_prices"],
                "option_signal": "HOLD",
                "trading_symbol": None,
                "expiry_date": None
            }

    def _determine_option_signal(self, stock_signal, option_type):
        """Determine option signal based on stock signal and option type.

        Args:
            stock_signal: Stock signal ('BUY', 'SELL', 'HOLD')
            option_type: Option type ('CE' or 'PE')

        Returns:
            Option signal string
        """
        try:
            if not stock_signal or not option_type:
                return "HOLD"

            if stock_signal == "BUY":
                if option_type == "CE":
                    return "Buy CALL Option"
                else:
                    return "Sell PUT Option"
            elif stock_signal == "SELL":
                if option_type == "PE":
                    return "Buy PUT Option"
                else:
                    return "Sell CALL Option"
            else:
                # For HOLD signals, give directional bias based on option type
                if option_type == "CE":
                    return "Buy CALL Option"  # Changed from "HOLD"
                else:
                    return "Buy PUT Option"  # Changed from "HOLD"
        except Exception as e:
            logger.error(f"Error determining option signal: {e}")
            return "HOLD"

    def _create_empty_option_info(self):
        """Create empty option info structure.

        Returns:
            Dictionary with empty option info
        """
        return {
            "option_info": {
                "underlying_strike": None,
                "selected_strike": None,
                "strike_type": None,
                "iv_percentile": None,
                "max_pain_price": None,
                "open_interest_analysis": "Option data not available"
            },
            "option_prices": {
                "current_price": None,
                "target_price": None,
                "stop_loss": None
            }
        }