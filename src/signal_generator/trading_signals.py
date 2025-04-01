# src/signal_generator/trading_signals.py
import datetime
import pandas as pd
import pytz

from config.settings import PORTFOLIO_SIZE, MAX_RISK_PERCENT
from config.logging_config import logger
from src.analysis.technical_analysis import TechnicalAnalysis
from src.analysis.support_resistance import SupportResistanceCalculator
from src.analysis.options_analysis import OptionsAnalysis


class TradingSignalGenerator:
    def __init__(self, kite_client, live_data_fetcher):
        """Initialize the trading signal generator.

        Args:
            kite_client: Authenticated KiteConnect client
            live_data_fetcher: LiveDataFetcher instance
        """
        self.kite = kite_client
        self.live_data_fetcher = live_data_fetcher
        self.technical_analyzer = TechnicalAnalysis()
        self.support_resistance_calculator = SupportResistanceCalculator()
        self.options_analyzer = OptionsAnalysis(kite_client, live_data_fetcher)
        self.indian_tz = pytz.timezone('Asia/Kolkata')

    def generate_signal(self, symbol, historical_data):
        """Generate trading signal for a symbol.

        Args:
            symbol: Stock symbol
            historical_data: DataFrame with historical data

        Returns:
            Dictionary with signal data
        """
        try:
            logger.info(f"Generating signal for {symbol}")

            # Safety check for historical data
            if historical_data is None or historical_data.empty:
                logger.warning(f"No historical data available for {symbol}")
                return self._create_empty_signal(symbol)

            # Get market status safely
            try:
                market_status = self.live_data_fetcher.get_market_status()
            except Exception as e:
                logger.error(f"Error getting market status: {e}")
                market_status = "Unknown"

            # Get latest quote safely
            try:
                quotes = self.live_data_fetcher.get_quote([symbol]) or {}
                symbol_quote = quotes.get(f"NSE:{symbol}", {})
            except Exception as e:
                logger.error(f"Error getting quote for {symbol}: {e}")
                symbol_quote = {}

            # Get current price and previous close with fallbacks
            try:
                current_price = symbol_quote.get("last_price",
                                                 historical_data["close"].iloc[
                                                     -1] if not historical_data.empty else None)
                previous_close = symbol_quote.get("ohlc", {}).get("close",
                                                                  historical_data["close"].iloc[-2] if len(
                                                                      historical_data) > 1 else None)
            except Exception as e:
                logger.error(f"Error getting price data for {symbol}: {e}")
                current_price = None
                previous_close = None

            # Perform technical analysis
            try:
                signal, confidence, df_analyzed = self.technical_analyzer.analyze(historical_data)

                # Safety check for analyzed data
                if df_analyzed is None or df_analyzed.empty:
                    logger.warning(f"Technical analysis failed for {symbol}")
                    return self._create_empty_signal(symbol)

                # Get latest data point with all indicators
                latest_data = df_analyzed.iloc[-1] if not df_analyzed.empty else None

            except Exception as e:
                logger.error(f"Error in technical analysis for {symbol}: {e}")
                return self._create_empty_signal(symbol)

            # Calculate support and resistance levels
            try:
                support_levels, resistance_levels = self.support_resistance_calculator.calculate_support_resistance(
                    df_analyzed)
            except Exception as e:
                logger.error(f"Error calculating support/resistance for {symbol}: {e}")
                support_levels, resistance_levels = [], []

            # Find target and stop loss
            try:
                target_price, stop_loss, risk_reward, days_to_target = self.support_resistance_calculator.find_target_and_stop_loss(
                    df_analyzed, signal, confidence
                )
            except Exception as e:
                logger.error(f"Error finding target/stop loss for {symbol}: {e}")
                target_price, stop_loss, risk_reward, days_to_target = None, None, 0, 1

            # Calculate position size
            try:
                position_size_recommendation = self.support_resistance_calculator.calculate_position_size(
                    current_price, stop_loss, PORTFOLIO_SIZE, MAX_RISK_PERCENT
                ) if current_price and stop_loss else "Unable to calculate position size"
            except Exception as e:
                logger.error(f"Error calculating position size for {symbol}: {e}")
                position_size_recommendation = "Unable to calculate position size"

            # Analyze option
            try:
                option_analysis = self.options_analyzer.analyze_option(
                    symbol, signal, df_analyzed, target_price, stop_loss, confidence
                )

                # Check if option_analysis is None
                if option_analysis is None:
                    logger.warning(f"Option analysis returned None for {symbol}")
                    option_analysis = {}

            except Exception as e:
                logger.error(f"Error in options analysis for {symbol}: {e}")
                option_analysis = {}

            # Calculate profit probability (simplified)
            try:
                profit_probability = min(confidence, 85) if confidence is not None else 0  # Cap at 85%
            except Exception as e:
                logger.error(f"Error calculating profit probability for {symbol}: {e}")
                profit_probability = 0

            # Get option signal from option analysis
            try:
                option_signal = option_analysis.get("option_signal", "HOLD")
            except Exception as e:
                logger.error(f"Error getting option signal for {symbol}: {e}")
                option_signal = "HOLD"

            # Determine direction
            try:
                if signal == "BUY":
                    direction = "UP"
                elif signal == "SELL":
                    direction = "DOWN"
                else:
                    direction = "NEUTRAL"
            except Exception as e:
                logger.error(f"Error determining direction for {symbol}: {e}")
                direction = "NEUTRAL"

            # Create risk factor analysis
            try:
                risk_factors = self._analyze_risk_factors(symbol, df_analyzed)
            except Exception as e:
                logger.error(f"Error analyzing risk factors for {symbol}: {e}")
                risk_factors = {"earnings_impact_risk": "Unknown", "days_to_earnings": None}

            # Create result
            try:
                result = {
                    "basic_info": {
                        "symbol": symbol,
                        "previous_close": round(previous_close, 2) if previous_close else None,
                        "current_price": round(current_price, 2) if current_price else None,
                        "volatility_percent": round(latest_data.get("volatility_pct", 0),
                                                    2) if latest_data is not None else None
                    },
                    "signal_info": {
                        "signal": option_signal,
                        "direction": direction,
                        "confidence_percent": round(confidence, 1) if confidence is not None else 0.0,
                        "profit_probability_percent": round(profit_probability,
                                                            1) if profit_probability is not None else 0.0
                    },
                    "price_targets": {
                        "target_price": round(target_price, 2) if target_price else None,
                        "stop_loss_price": round(stop_loss, 2) if stop_loss else None,
                        "risk_reward_ratio": risk_reward if risk_reward is not None else 0.0,
                        "days_to_target": days_to_target if days_to_target is not None else 1
                    },
                    "technical_indicators": {
                        "technical_trend_score": round(latest_data.get("technical_trend_score", 0),
                                                       1) if latest_data is not None else None,
                        "momentum_score": round(latest_data.get("momentum_score", 0),
                                                2) if latest_data is not None else None,
                        "rsi": round(latest_data.get("rsi", 0), 2) if latest_data is not None else None,
                        "adx": round(latest_data.get("adx", 0), 2) if latest_data is not None else None,
                        "macd": round(latest_data.get("macd", 0), 2) if latest_data is not None else None,
                        "volume_change_percent": round(latest_data.get("volume_change_pct", 0),
                                                       2) if latest_data is not None else None
                    },
                    "support_resistance": {
                        "support_levels": support_levels,
                        "resistance_levels": resistance_levels
                    },
                    "position_sizing": {
                        "recommendation": position_size_recommendation
                    },
                    "option_info": option_analysis.get("option_info", {}) or {},
                    "option_prices": option_analysis.get("option_prices", {}) or {},
                    "risk_factors": risk_factors or {},
                    "metadata": {
                        "trading_symbol": option_analysis.get("trading_symbol"),
                        "expiry_date": option_analysis.get("expiry_date"),
                        "analysis_timestamp": datetime.datetime.now(self.indian_tz).strftime("%Y-%m-%d %H:%M:%S"),
                        "market_status": market_status
                    }
                }

                logger.info(
                    f"Signal generated for {symbol}: {result['signal_info']['signal']} with {result['signal_info']['confidence_percent']}% confidence")

                return result
            except Exception as e:
                logger.error(f"Error creating result for {symbol}: {e}")
                return self._create_empty_signal(symbol)

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return self._create_empty_signal(symbol)

    def _analyze_risk_factors(self, symbol, df):
        """Analyze risk factors for a symbol.

        Args:
            symbol: Stock symbol
            df: DataFrame with historical data

        Returns:
            Dictionary with risk factors
        """
        try:
            # Here we would typically fetch earnings dates, upcoming events, etc.
            # For simplicity, we'll just return dummy data

            # Calculate days to earnings (random for example)
            import random
            days_to_earnings = random.randint(10, 90)

            # Determine earnings impact risk
            if days_to_earnings < 15:
                earnings_impact = "High"
            elif days_to_earnings < 30:
                earnings_impact = "Medium"
            else:
                earnings_impact = "Low"

            return {
                "earnings_impact_risk": earnings_impact,
                "days_to_earnings": days_to_earnings
            }

        except Exception as e:
            logger.error(f"Error analyzing risk factors for {symbol}: {e}")
            return {
                "earnings_impact_risk": "Unknown",
                "days_to_earnings": None
            }

    def _create_empty_signal(self, symbol):
        """Create empty signal data structure.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with empty signal data
        """
        return {
            "basic_info": {
                "symbol": symbol,
                "previous_close": None,
                "current_price": None,
                "volatility_percent": None
            },
            "signal_info": {
                "signal": "HOLD",
                "direction": "NEUTRAL",
                "confidence_percent": 0.0,
                "profit_probability_percent": 0.0
            },
            "price_targets": {
                "target_price": None,
                "stop_loss_price": None,
                "risk_reward_ratio": 0.0,
                "days_to_target": 1
            },
            "technical_indicators": {
                "technical_trend_score": None,
                "momentum_score": None,
                "rsi": None,
                "adx": None,
                "macd": None,
                "volume_change_percent": None
            },
            "support_resistance": {
                "support_levels": [],
                "resistance_levels": []
            },
            "position_sizing": {
                "recommendation": "Unable to calculate position size"
            },
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
            },
            "risk_factors": {
                "earnings_impact_risk": "Unknown",
                "days_to_earnings": None
            },
            "metadata": {
                "trading_symbol": None,
                "expiry_date": None,
                "analysis_timestamp": datetime.datetime.now(self.indian_tz).strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": self.live_data_fetcher.get_market_status() or "Unknown"
            }
        }