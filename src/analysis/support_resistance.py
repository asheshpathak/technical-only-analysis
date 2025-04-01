# src/analysis/support_resistance.py
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from config.logging_config import logger


class SupportResistanceCalculator:
    def __init__(self):
        """Initialize the support and resistance calculator."""
        pass

    def find_local_extrema(self, df, window=10):
        """Find local minima and maxima in price data.

        Args:
            df: DataFrame with OHLCV data
            window: Window size for detecting local extrema

        Returns:
            Tuple containing DataFrames with local minima and maxima
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for finding local extrema")
            return pd.DataFrame(), pd.DataFrame()

        try:
            # Make a copy of the dataframe
            df_copy = df.copy()

            # Find local minima and maxima
            df_copy['min_idx'] = df_copy.iloc[argrelextrema(df_copy['low'].values, np.less_equal, order=window)[0]][
                'low']
            df_copy['max_idx'] = df_copy.iloc[argrelextrema(df_copy['high'].values, np.greater_equal, order=window)[0]][
                'high']

            # Get minima and maxima DataFrames
            minima = df_copy[df_copy['min_idx'].notnull()].copy()
            maxima = df_copy[df_copy['max_idx'].notnull()].copy()

            logger.debug(f"Found {len(minima)} minima and {len(maxima)} maxima with window size {window}")

            return minima, maxima

        except Exception as e:
            logger.error(f"Error finding local extrema: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def cluster_levels(self, levels, threshold_pct=1.0):
        """Cluster similar price levels.

        Args:
            levels: List of price levels
            threshold_pct: Threshold percentage for clustering

        Returns:
            List of clustered price levels
        """
        if not levels:
            return []

        # Sort levels
        sorted_levels = sorted(levels)

        # Initialize clusters
        clusters = []
        current_cluster = [sorted_levels[0]]

        # Cluster levels
        for i in range(1, len(sorted_levels)):
            current_level = sorted_levels[i]
            prev_level = current_cluster[-1]

            # Calculate threshold based on previous level
            threshold = prev_level * threshold_pct / 100

            if current_level - prev_level <= threshold:
                # Add to current cluster
                current_cluster.append(current_level)
            else:
                # Create new cluster
                if current_cluster:
                    clusters.append(np.mean(current_cluster))
                current_cluster = [current_level]

        # Add last cluster
        if current_cluster:
            clusters.append(np.mean(current_cluster))

        return clusters

    def calculate_support_resistance(self, df, window=10, min_strength=2, max_levels=3, threshold_pct=1.0):
        """Calculate support and resistance levels.

        Args:
            df: DataFrame with OHLCV data
            window: Window size for detecting local extrema
            min_strength: Minimum strength for a level to be considered
            max_levels: Maximum number of levels to return
            threshold_pct: Threshold percentage for clustering

        Returns:
            Tuple containing lists of support and resistance levels
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for calculating support and resistance")
            return [], []

        try:
            # Find local minima and maxima
            minima, maxima = self.find_local_extrema(df, window)

            # Get most recent data for recency weighting
            recent_df = df.iloc[-20:].copy()

            # Get support and resistance candidates
            support_candidates = minima['low'].tolist()
            resistance_candidates = maxima['high'].tolist()

            # Add recent lows and highs
            recent_lows = recent_df['low'].nsmallest(3).tolist()
            recent_highs = recent_df['high'].nlargest(3).tolist()

            support_candidates.extend(recent_lows)
            resistance_candidates.extend(recent_highs)

            # Add latest price's proximity support/resistance
            latest_price = df['close'].iloc[-1]
            latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]

            support_candidates.append(latest_price - latest_atr)
            support_candidates.append(latest_price - 2 * latest_atr)

            resistance_candidates.append(latest_price + latest_atr)
            resistance_candidates.append(latest_price + 2 * latest_atr)

            # Cluster levels
            support_levels = self.cluster_levels(support_candidates, threshold_pct)
            resistance_levels = self.cluster_levels(resistance_candidates, threshold_pct)

            # Sort levels
            support_levels = sorted([level for level in support_levels if level < latest_price], reverse=True)
            resistance_levels = sorted([level for level in resistance_levels if level > latest_price])

            # Limit the number of levels
            support_levels = support_levels[:max_levels]
            resistance_levels = resistance_levels[:max_levels]

            # Round to 2 decimal places
            support_levels = [round(level, 2) for level in support_levels]
            resistance_levels = [round(level, 2) for level in resistance_levels]

            logger.info(f"Calculated support levels: {support_levels}")
            logger.info(f"Calculated resistance levels: {resistance_levels}")

            return support_levels, resistance_levels

        except Exception as e:
            logger.error(f"Error calculating support and resistance: {e}")
            return [], []

    def find_target_and_stop_loss(self, df, signal, confidence):
        """Find target price and stop loss based on support and resistance levels.

        Args:
            df: DataFrame with OHLCV data and indicators
            signal: Trading signal ('BUY', 'SELL', 'HOLD')
            confidence: Signal confidence

        Returns:
            Tuple containing target price, stop loss, and days to target
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for finding target and stop loss")
            return None, None, 1

        try:
            # Calculate support and resistance levels
            support_levels, resistance_levels = self.calculate_support_resistance(df)

            # Get latest price
            latest_price = df['close'].iloc[-1]

            # Initialize variables
            target_price = None
            stop_loss = None
            days_to_target = 1  # Default

            if signal == "BUY":
                # For buy signal, target is nearest resistance, stop loss is nearest support
                if resistance_levels:
                    target_price = resistance_levels[0]

                if support_levels:
                    stop_loss = support_levels[0]

                # Fallback if levels not found
                if target_price is None:
                    latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]
                    target_price = latest_price + latest_atr

                if stop_loss is None:
                    latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]
                    stop_loss = latest_price - latest_atr

            elif signal == "SELL":
                # For sell signal, target is nearest support, stop loss is nearest resistance
                if support_levels:
                    target_price = support_levels[0]

                if resistance_levels:
                    stop_loss = resistance_levels[0]

                # Fallback if levels not found
                if target_price is None:
                    latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]
                    target_price = latest_price - latest_atr

                if stop_loss is None:
                    latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]
                    stop_loss = latest_price + latest_atr

            else:  # HOLD
                # For hold signal, just use ATR-based levels
                latest_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]
                target_price = latest_price + latest_atr
                stop_loss = latest_price - latest_atr

            # Calculate days to target based on volatility and distance
            price_distance = abs(target_price - latest_price)
            daily_volatility = df['atr'].iloc[-1] if 'atr' in df.columns else df['high'].iloc[-1] - df['low'].iloc[-1]

            if daily_volatility > 0:
                days_to_target = max(round(price_distance / daily_volatility), 1)

            # Calculate risk-reward ratio
            risk = abs(latest_price - stop_loss)
            reward = abs(target_price - latest_price)
            risk_reward = reward / risk if risk > 0 else 0

            # Adjust days based on confidence
            days_to_target = max(days_to_target, round(100 / confidence)) if confidence > 0 else days_to_target

            # Round values
            target_price = round(target_price, 2)
            stop_loss = round(stop_loss, 2)
            risk_reward = round(risk_reward, 2)

            logger.info(f"Target price: {target_price}, Stop loss: {stop_loss}, Days to target: {days_to_target}")

            return target_price, stop_loss, risk_reward, days_to_target

        except Exception as e:
            logger.error(f"Error finding target and stop loss: {e}")
            return None, None, 0, 1

    def calculate_position_size(self, latest_price, stop_loss, portfolio_size, max_risk_percent):
        """Calculate recommended position size based on risk parameters.

        Args:
            latest_price: Current price
            stop_loss: Stop loss price
            portfolio_size: Portfolio size in INR
            max_risk_percent: Maximum risk percentage per trade

        Returns:
            String with position sizing recommendation
        """
        try:
            # Calculate risk per share
            risk_per_share = abs(latest_price - stop_loss)

            # Calculate maximum risk amount
            max_risk_amount = portfolio_size * max_risk_percent / 100

            # Calculate maximum shares
            max_shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0

            # Calculate position size in INR
            position_size = max_shares * latest_price

            # Calculate percentage of portfolio
            portfolio_percent = (position_size / portfolio_size) * 100

            recommendation = (
                f"Max {max_shares} shares (₹{position_size:.2f}, {portfolio_percent:.1f}% of portfolio) "
                f"based on {max_risk_percent:.1f}% max risk per trade"
            )

            logger.info(f"Position sizing recommendation: {recommendation}")

            return recommendation

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return "Position sizing calculation failed"