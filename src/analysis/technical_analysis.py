# src/analysis/technical_analysis.py
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice, OnBalanceVolumeIndicator

from config.settings import RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, ADX_PERIOD, VOLATILITY_PERIOD
from config.logging_config import logger


class TechnicalAnalysis:
    def __init__(self):
        """Initialize the technical analysis module."""
        pass

    def calculate_indicators(self, df):
        """Calculate technical indicators for a DataFrame.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added technical indicators
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for technical analysis")
            return df

        logger.debug("Calculating technical indicators")

        # Make sure date column is datetime if it exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        # Make a copy to avoid modifying the original
        df_result = df.copy()

        try:
            # Get data size to adapt parameters
            data_size = len(df_result)
            logger.debug(f"Data size: {data_size} data points")

            # Adjust periods based on available data
            rsi_period = min(RSI_PERIOD, max(2, data_size // 3))
            adx_period = min(ADX_PERIOD, max(2, data_size // 3))
            macd_fast = min(MACD_FAST, max(2, data_size // 5))
            macd_slow = min(MACD_SLOW, max(3, data_size // 4))
            macd_signal = min(MACD_SIGNAL, max(2, data_size // 6))

            logger.debug(
                f"Adjusted periods: RSI={rsi_period}, ADX={adx_period}, MACD={macd_fast}/{macd_slow}/{macd_signal}")

            # RSI
            rsi = RSIIndicator(close=df_result['close'], window=rsi_period)
            df_result['rsi'] = rsi.rsi()

            # MACD
            macd = MACD(
                close=df_result['close'],
                window_slow=macd_slow,
                window_fast=macd_fast,
                window_sign=macd_signal
            )
            df_result['macd'] = macd.macd()
            df_result['macd_signal'] = macd.macd_signal()
            df_result['macd_diff'] = macd.macd_diff()

            # ADX
            adx = ADXIndicator(
                high=df_result['high'],
                low=df_result['low'],
                close=df_result['close'],
                window=adx_period
            )
            df_result['adx'] = adx.adx()
            df_result['adx_pos'] = adx.adx_pos()
            df_result['adx_neg'] = adx.adx_neg()

            # Moving Averages
            sma_20_period = min(20, max(2, data_size // 3))
            sma_50_period = min(50, max(3, data_size // 2))
            sma_200_period = min(200, max(5, data_size - 5))

            df_result['sma_20'] = SMAIndicator(close=df_result['close'], window=sma_20_period).sma_indicator()
            df_result['sma_50'] = SMAIndicator(close=df_result['close'], window=sma_50_period).sma_indicator()
            df_result['sma_200'] = SMAIndicator(close=df_result['close'], window=sma_200_period).sma_indicator()

            ema_9_period = min(9, max(2, data_size // 4))
            ema_21_period = min(21, max(3, data_size // 3))

            df_result['ema_9'] = EMAIndicator(close=df_result['close'], window=ema_9_period).ema_indicator()
            df_result['ema_21'] = EMAIndicator(close=df_result['close'], window=ema_21_period).ema_indicator()

            # Bollinger Bands
            bb_period = min(20, max(2, data_size // 3))
            bb = BollingerBands(close=df_result['close'], window=bb_period, window_dev=2)
            df_result['bb_upper'] = bb.bollinger_hband()
            df_result['bb_middle'] = bb.bollinger_mavg()
            df_result['bb_lower'] = bb.bollinger_lband()
            df_result['bb_width'] = (df_result['bb_upper'] - df_result['bb_lower']) / df_result['bb_middle']

            # ATR for volatility
            atr_period = min(VOLATILITY_PERIOD, max(2, data_size // 3))
            atr = AverageTrueRange(
                high=df_result['high'],
                low=df_result['low'],
                close=df_result['close'],
                window=atr_period
            )
            df_result['atr'] = atr.average_true_range()

            # Volatility percentage (ATR/Close)
            df_result['volatility_pct'] = (df_result['atr'] / df_result['close']) * 100

            # Volume analysis
            if 'volume' in df_result.columns:
                # On-Balance Volume
                obv = OnBalanceVolumeIndicator(close=df_result['close'], volume=df_result['volume'])
                df_result['obv'] = obv.on_balance_volume()

                # Volume Moving Average
                vol_sma_period = min(20, max(2, data_size // 3))
                df_result['volume_sma'] = SMAIndicator(close=df_result['volume'], window=vol_sma_period).sma_indicator()

                # Volume change percentage
                df_result['volume_change_pct'] = df_result['volume'].pct_change() * 100

            # Stochastic Oscillator
            stoch_period = min(14, max(2, data_size // 3))
            stoch_smooth = min(3, max(1, data_size // 10))
            stoch = StochasticOscillator(
                high=df_result['high'],
                low=df_result['low'],
                close=df_result['close'],
                window=stoch_period,
                smooth_window=stoch_smooth
            )
            df_result['stoch_k'] = stoch.stoch()
            df_result['stoch_d'] = stoch.stoch_signal()

            # Calculate momentum score (basic implementation)
            df_result['price_change_pct'] = df_result['close'].pct_change() * 100

            mom_1d_period = min(1, max(1, data_size // 20))
            mom_5d_period = min(5, max(1, data_size // 10))
            mom_20d_period = min(20, max(1, data_size // 5))

            df_result['momentum_1d'] = df_result['close'] / df_result['close'].shift(mom_1d_period) - 1
            df_result['momentum_5d'] = df_result['close'] / df_result['close'].shift(mom_5d_period) - 1
            df_result['momentum_20d'] = df_result['close'] / df_result['close'].shift(mom_20d_period) - 1

            # Technical trend score (50% weight to ADX, 30% to MACD, 20% to RSI)
            # Normalize components to 0-100 scale
            df_result['adx_norm'] = df_result['adx']  # ADX is already 0-100
            df_result['macd_norm'] = 50 + (df_result['macd_diff'] / df_result['close'] * 500)  # Normalize MACD
            df_result['macd_norm'] = df_result['macd_norm'].clip(0, 100)
            df_result['rsi_norm'] = df_result['rsi']  # RSI is already 0-100

            # Calculate weighted score
            df_result['technical_trend_score'] = (
                    0.5 * df_result['adx_norm'] +
                    0.3 * df_result['macd_norm'] +
                    0.2 * df_result['rsi_norm']
            )

            # Momentum score (combined indicator from -1 to +1)
            df_result['momentum_score'] = (
                    0.5 * np.sign(df_result['momentum_1d']) * np.abs(df_result['momentum_1d']) ** 0.5 +
                    0.3 * np.sign(df_result['momentum_5d']) * np.abs(df_result['momentum_5d']) ** 0.5 +
                    0.2 * np.sign(df_result['momentum_20d']) * np.abs(df_result['momentum_20d']) ** 0.5
            )

            # Fill NaN values
            df_result = df_result.fillna(method='bfill')

            logger.debug("Technical indicators calculated successfully")

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")

        return df_result

    def generate_signals(self, df):
        """Generate trading signals based on technical analysis.

        Args:
            df: DataFrame with technical indicators

        Returns:
            Tuple containing signal ('BUY', 'SELL', 'HOLD'), confidence (0-100),
            and dataframe with signal indicators
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for signal generation")
            return "HOLD", 0, df

        # Get the latest data point
        latest = df.iloc[-1]

        # Initialize signal strength counters
        buy_signals = 0
        sell_signals = 0
        total_signals = 10  # Total number of signals we're checking

        # Create a new DataFrame for the output
        signal_df = df.copy()
        signal_df['signal'] = 'HOLD'

        # 1. RSI Signal
        if latest['rsi'] < 30:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'rsi_signal'] = 'BUY'
        elif latest['rsi'] > 70:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'rsi_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'rsi_signal'] = 'HOLD'

        # 2. MACD Signal
        if latest['macd'] > latest['macd_signal']:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'macd_signal_indicator'] = 'BUY'
        elif latest['macd'] < latest['macd_signal']:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'macd_signal_indicator'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'macd_signal_indicator'] = 'HOLD'

        # 3. ADX Signal (trend strength)
        if latest['adx'] > 25:
            # Strong trend, check direction
            if latest['adx_pos'] > latest['adx_neg']:
                buy_signals += 1
                signal_df.loc[df.index[-1], 'adx_signal'] = 'BUY'
            else:
                sell_signals += 1
                signal_df.loc[df.index[-1], 'adx_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'adx_signal'] = 'HOLD'

        # 4. Moving Average Signal
        if latest['close'] > latest['sma_50'] and latest['sma_50'] > latest['sma_200']:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'ma_signal'] = 'BUY'
        elif latest['close'] < latest['sma_50'] and latest['sma_50'] < latest['sma_200']:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'ma_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'ma_signal'] = 'HOLD'

        # 5. Bollinger Bands Signal
        if latest['close'] <= latest['bb_lower']:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'bb_signal'] = 'BUY'
        elif latest['close'] >= latest['bb_upper']:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'bb_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'bb_signal'] = 'HOLD'

        # 6. Stochastic Oscillator Signal
        if latest['stoch_k'] < 20 and latest['stoch_d'] < 20:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'stoch_signal'] = 'BUY'
        elif latest['stoch_k'] > 80 and latest['stoch_d'] > 80:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'stoch_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'stoch_signal'] = 'HOLD'

        # 7. Price vs EMA Signal
        if latest['close'] > latest['ema_21']:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'ema_signal'] = 'BUY'
        elif latest['close'] < latest['ema_21']:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'ema_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'ema_signal'] = 'HOLD'

        # 8. Price vs ATR (volatility breakout)
        if len(df) > 1:  # Make sure we have at least 2 data points
            price_change = abs(latest['close'] - df.iloc[-2]['close'])
            if price_change > 1.5 * latest['atr']:
                if latest['close'] > df.iloc[-2]['close']:
                    buy_signals += 1
                    signal_df.loc[df.index[-1], 'volatility_signal'] = 'BUY'
                else:
                    sell_signals += 1
                    signal_df.loc[df.index[-1], 'volatility_signal'] = 'SELL'
            else:
                signal_df.loc[df.index[-1], 'volatility_signal'] = 'HOLD'
        else:
            signal_df.loc[df.index[-1], 'volatility_signal'] = 'HOLD'

        # 9. Volume Signal (if available)
        if 'volume' in df.columns and 'volume_sma' in df.columns:
            if latest['volume'] > 1.5 * latest['volume_sma'] and latest['close'] > df.iloc[-2]['close']:
                buy_signals += 1
                signal_df.loc[df.index[-1], 'volume_signal'] = 'BUY'
            elif latest['volume'] > 1.5 * latest['volume_sma'] and latest['close'] < df.iloc[-2]['close']:
                sell_signals += 1
                signal_df.loc[df.index[-1], 'volume_signal'] = 'SELL'
            else:
                signal_df.loc[df.index[-1], 'volume_signal'] = 'HOLD'
        else:
            # Skip this signal if volume data isn't available
            signal_df.loc[df.index[-1], 'volume_signal'] = 'HOLD'
            total_signals -= 1

        # 10. Technical trend score
        if latest['technical_trend_score'] > 70:
            buy_signals += 1
            signal_df.loc[df.index[-1], 'trend_score_signal'] = 'BUY'
        elif latest['technical_trend_score'] < 30:
            sell_signals += 1
            signal_df.loc[df.index[-1], 'trend_score_signal'] = 'SELL'
        else:
            signal_df.loc[df.index[-1], 'trend_score_signal'] = 'HOLD'

        # Determine overall signal and confidence
        if buy_signals > sell_signals and buy_signals > total_signals * 0.3:
            signal = "BUY"
            confidence = (buy_signals / total_signals) * 100
        elif sell_signals > buy_signals and sell_signals > total_signals * 0.3:
            signal = "SELL"
            confidence = (sell_signals / total_signals) * 100
        else:
            signal = "HOLD"
            confidence = 50  # Neutral confidence

        # Add final signal to DataFrame
        signal_df.loc[df.index[-1], 'signal'] = signal
        signal_df.loc[df.index[-1], 'confidence'] = confidence

        logger.info(f"Generated signal: {signal} with confidence: {confidence:.2f}%")

        return signal, confidence, signal_df

    def analyze(self, df):
        """Perform technical analysis and generate signals.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple containing signal, confidence, and DataFrame with indicators
        """
        # Calculate indicators
        df_indicators = self.calculate_indicators(df)

        # Generate signals
        signal, confidence, signal_df = self.generate_signals(df_indicators)

        return signal, confidence, signal_df