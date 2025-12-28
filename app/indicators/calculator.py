"""Incremental indicator calculator for efficient real-time updates."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, Optional, Protocol, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class IndicatorCalculator(Protocol):
    """Protocol for indicator calculators."""

    def update(self, new_candle: dict) -> Union[float, Dict[str, float]]:
        """Update indicator with new candle data and return current value(s)."""
        ...

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        ...


class SMACalculator:
    """Simple Moving Average calculator with incremental updates."""

    def __init__(self, period: int):
        self.period = period
        self.values: deque[float] = deque(maxlen=period)
        self.current_sum = 0.0

    def update(self, new_candle: dict) -> float:
        """Update SMA with new price data."""
        price = float(new_candle.get("close", new_candle.get("price", 0)))
        if len(self.values) == self.period:
            # Remove oldest value from sum
            self.current_sum -= self.values[0]

        self.values.append(price)
        self.current_sum += price

        return self.current_sum / len(self.values) if self.values else 0.0

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        self.values.clear()
        self.current_sum = 0.0


class RSICalculator:
    """Relative Strength Index calculator with incremental updates."""

    def __init__(self, period: int = 14):
        self.period = period
        self.gains: deque[float] = deque(maxlen=period)
        self.losses: deque[float] = deque(maxlen=period)
        self.prev_price: Optional[float] = None
        self.avg_gain = 0.0
        self.avg_loss = 0.0

    def update(self, new_candle: dict) -> float:
        """Update RSI with new price data."""
        price = new_candle.get("close", new_candle.get("price", 0))

        if self.prev_price is None:
            self.prev_price = price
            return 50.0  # Neutral RSI for first candle

        # Calculate price change
        change = price - self.prev_price
        gain = max(change, 0)
        loss = max(-change, 0)

        self.prev_price = price

        # Update gain/loss queues
        if len(self.gains) == self.period:
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
        else:
            self.gains.append(gain)
            self.losses.append(loss)
            if len(self.gains) == 1:
                self.avg_gain = gain
                self.avg_loss = loss
            else:
                self.avg_gain = (self.avg_gain * (len(self.gains) - 1) + gain) / len(self.gains)
                self.avg_loss = (self.avg_loss * (len(self.losses) - 1) + loss) / len(self.losses)

        if self.avg_loss == 0:
            return 100.0

        rs = self.avg_gain / self.avg_loss
        return 100 - (100 / (1 + rs))

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        self.gains.clear()
        self.losses.clear()
        self.prev_price = None
        self.avg_gain = 0.0
        self.avg_loss = 0.0


class EMACalculator:
    """Exponential Moving Average calculator with incremental updates."""

    def __init__(self, period: int):
        self.period = period
        self.multiplier = 2 / (period + 1)
        self.current_ema: Optional[float] = None

    def update(self, new_candle: dict) -> float:
        """Update EMA with new price data."""
        price = float(new_candle.get("close", new_candle.get("price", 0)))

        if self.current_ema is None:
            self.current_ema = price
        else:
            self.current_ema = (price * self.multiplier) + (self.current_ema * (1 - self.multiplier))

        return float(self.current_ema)

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        self.current_ema = None


class MACDCalculator:
    """MACD calculator with incremental updates."""

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_ema = EMACalculator(fast_period)
        self.slow_ema = EMACalculator(slow_period)
        self.signal_ema = EMACalculator(signal_period)
        self.histogram_values: deque[float] = deque(maxlen=100)

    def update(self, new_candle: dict) -> Dict[str, float]:
        """Update MACD with new price data."""
        fast_val = self.fast_ema.update(new_candle)
        slow_val = self.slow_ema.update(new_candle)
        macd_line = float(fast_val - slow_val)
        signal_line = float(self.signal_ema.update({"price": macd_line, "close": macd_line}))
        histogram = float(macd_line - signal_line)

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
        }

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        self.fast_ema.reset()
        self.slow_ema.reset()
        self.signal_ema.reset()
        self.histogram_values.clear()


class BollingerBandsCalculator:
    """Bollinger Bands calculator with incremental updates."""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        self.prices: deque[float] = deque(maxlen=period)
        self.sma_calc = SMACalculator(period)

    def update(self, new_candle: dict) -> Dict[str, float]:
        """Update Bollinger Bands with new price data."""
        price = float(new_candle.get("close", new_candle.get("price", 0)))
        self.prices.append(price)

        if len(self.prices) < self.period:
            return {"upper": price, "middle": price, "lower": price, "percent_b": 0.5}

        sma = self.sma_calc.update(new_candle)
        std = float(np.std(list(self.prices)))

        upper = float(sma + (std * self.std_dev))
        lower = float(sma - (std * self.std_dev))
        percent_b = float((price - lower) / (upper - lower) if (upper - lower) != 0 else 0.5)

        return {
            "upper": upper,
            "middle": float(sma),
            "lower": lower,
            "percent_b": percent_b,
        }

    def reset(self) -> None:
        """Reset the calculator to initial state."""
        self.prices.clear()
        self.sma_calc.reset()


class IncrementalIndicatorCalculator:
    """Efficient incremental indicator calculator that updates based on new candles only."""

    def __init__(self):
        self.indicators: Dict[str, IndicatorCalculator] = {}
        self.indicator_values: Dict[str, Any] = {}
        self._initialize_indicators()

    def _initialize_indicators(self):
        """Initialize all indicator calculators."""
        # Moving Averages
        self.indicators["sma_20"] = SMACalculator(20)
        self.indicators["sma_50"] = SMACalculator(50)
        self.indicators["ema_12"] = EMACalculator(12)
        self.indicators["ema_26"] = EMACalculator(26)

        # Momentum Indicators
        self.indicators["rsi_14"] = RSICalculator(14)

        # MACD
        self.indicators["macd"] = MACDCalculator()

        # Bollinger Bands
        self.indicators["bb"] = BollingerBandsCalculator()

    def update_indicators(self, new_candle: dict) -> Dict[str, Any]:
        """
        Update all indicators with new candle data.

        Args:
            new_candle: Dictionary containing OHLCV data

        Returns:
            Dictionary of current indicator values
        """
        try:
            # Update each indicator incrementally
            for indicator_name, calculator in self.indicators.items():
                try:
                    if indicator_name == "macd":
                        macd_result = calculator.update(new_candle)
                        if isinstance(macd_result, dict):
                            macd_data = macd_result
                            self.indicator_values.update({
                                "macd_line": macd_data["macd_line"],
                                "macd_signal": macd_data["signal_line"],
                                "macd_hist": macd_data["histogram"],
                            })
                    elif indicator_name == "bb":
                        bb_result = calculator.update(new_candle)
                        if isinstance(bb_result, dict):
                            bb_data = bb_result
                            self.indicator_values.update({
                                "bb_upper": bb_data["upper"],
                                "bb_middle": bb_data["middle"],
                                "bb_lower": bb_data["lower"],
                                "bb_percent_b": bb_data["percent_b"],
                            })
                    else:
                        value = calculator.update(new_candle)
                        if isinstance(value, float):
                            self.indicator_values[indicator_name] = value

                except Exception as e:
                    logger.warning(f"Failed to update indicator {indicator_name}: {e}")
                    continue

            # Calculate derived indicators
            self._calculate_derived_indicators()

            return self.indicator_values.copy()

        except Exception as e:
            logger.error(f"Error updating indicators: {e}")
            return self.indicator_values.copy()

    def _calculate_derived_indicators(self):
        """Calculate indicators derived from base indicators."""
        try:
            # EMA crossover signal
            ema_12 = self.indicator_values.get("ema_12", 0)
            ema_26 = self.indicator_values.get("ema_26", 0)
            self.indicator_values["ema_cross_12_26"] = 1 if ema_12 > ema_26 else -1

            # Price momentum (simplified)
            sma_20 = self.indicator_values.get("sma_20", 0)
            current_price = self.indicator_values.get("current_price", 0)
            if sma_20 > 0:
                self.indicator_values["price_momentum"] = (current_price - sma_20) / sma_20
            else:
                self.indicator_values["price_momentum"] = 0

        except Exception as e:
            logger.warning(f"Error calculating derived indicators: {e}")

    def get_indicator_value(self, indicator_name: str) -> Any:
        """Get current value of a specific indicator."""
        return self.indicator_values.get(indicator_name)

    def get_all_indicators(self) -> Dict[str, Any]:
        """Get all current indicator values."""
        return self.indicator_values.copy()

    def reset(self):
        """Reset all indicators to initial state."""
        self.indicator_values.clear()
        for calculator in self.indicators.values():
            calculator.reset()

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        LEGACY METHOD: Calculate all indicators on entire DataFrame.
        This is kept for backwards compatibility but is inefficient.
        Use update_indicators() for real-time updates instead.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with indicators added
        """
        logger.warning("Using legacy calculate_all_indicators method. Consider using IncrementalIndicatorCalculator for better performance.")

        # This would be the old inefficient way - recalculating everything
        # Implementation would go here for backwards compatibility
        return df