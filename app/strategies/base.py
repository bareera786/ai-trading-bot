"""Core trading strategy classes.

This module was extracted from ai_ml_auto_bot_final.py to keep logic identical
while enabling a modular architecture.
"""

from __future__ import annotations

import time
from copy import deepcopy

import pandas as pd


class BaseStrategy:
    """Base class for all trading strategies with QFM enhancement"""

    def __init__(self, name, description, parameters=None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.default_parameters = deepcopy(self.parameters)
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "last_updated": time.time(),
        }
        self.active_positions = {}
        self.trade_history = []
        self.qfm_engine = None  # Will be set by strategy manager
        self.active = True

    def set_qfm_engine(self, qfm_engine):
        """Set QFM engine for enhanced analysis"""
        self.qfm_engine = qfm_engine

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze market conditions and return trading signals with QFM enhancement"""
        raise NotImplementedError("Subclasses must implement analyze_market")

    def enhance_with_qfm(self, symbol, market_data, base_signal):
        """Enhance base strategy signal with QFM analysis"""
        if not self.qfm_engine or not market_data:
            return base_signal

        try:
            # Get QFM features for current market data
            qfm_features = self.qfm_engine.compute_realtime_features(
                symbol, market_data[-1] if market_data else {}
            )

            if not qfm_features:
                return base_signal

            # Extract QFM metrics
            velocity = qfm_features.get("qfm_velocity", 0)
            acceleration = qfm_features.get("qfm_acceleration", 0)
            jerk = qfm_features.get("qfm_jerk", 0)
            volume_pressure = qfm_features.get("qfm_volume_pressure", 0)
            trend_confidence = qfm_features.get("qfm_trend_confidence", 0)
            regime_score = qfm_features.get("qfm_regime_score", 0)
            entropy = qfm_features.get("qfm_entropy", 0)

            # QFM-enhanced signal logic
            qfm_bias = (
                (velocity * 120)
                + (acceleration * 80)
                + (trend_confidence * 40)
                + (volume_pressure * 25)
                + (regime_score * 35)
                + ((entropy - 0.5) * 20)
                - (abs(jerk) * 40)
            )

            # Determine QFM signal strength
            qfm_signal_strength = 0
            if qfm_bias > 0.8:
                qfm_signal_strength = 2  # Strong bullish
            elif qfm_bias > 0.35:
                qfm_signal_strength = 1  # Bullish
            elif qfm_bias < -0.8:
                qfm_signal_strength = -2  # Strong bearish
            elif qfm_bias < -0.35:
                qfm_signal_strength = -1  # Bearish

            # Enhance base signal with QFM
            enhanced_signal = base_signal.copy()
            base_confidence = base_signal.get("confidence", 0.5)
            qfm_confidence = min(0.95, max(0.55, 0.55 + min(0.35, abs(qfm_bias))))

            # Combine confidences with QFM weight
            qfm_weight = 0.3  # 30% weight to QFM enhancement
            enhanced_confidence = (base_confidence * (1 - qfm_weight)) + (
                qfm_confidence * qfm_weight
            )

            # Adjust signal based on QFM alignment
            base_signal_type = base_signal.get("signal", "HOLD")
            if base_signal_type in ["BUY", "STRONG_BUY"] and qfm_signal_strength > 0:
                # Reinforce bullish signal
                enhanced_confidence = min(0.95, enhanced_confidence + 0.1)
            elif (
                base_signal_type in ["SELL", "STRONG_SELL"] and qfm_signal_strength < 0
            ):
                # Reinforce bearish signal
                enhanced_confidence = min(0.95, enhanced_confidence + 0.1)
            elif (
                base_signal_type in ["BUY", "STRONG_BUY"] and qfm_signal_strength < 0
            ) or (
                base_signal_type in ["SELL", "STRONG_SELL"] and qfm_signal_strength > 0
            ):
                # Conflicting signals - reduce confidence
                enhanced_confidence = max(0.1, enhanced_confidence - 0.15)

            enhanced_signal["confidence"] = enhanced_confidence
            enhanced_signal["qfm_enhanced"] = True
            enhanced_signal["qfm_metrics"] = {
                "velocity": float(velocity),
                "acceleration": float(acceleration),
                "jerk": float(jerk),
                "volume_pressure": float(volume_pressure),
                "trend_confidence": float(trend_confidence),
                "regime_score": float(regime_score),
                "entropy": float(entropy),
                "qfm_bias": float(qfm_bias),
                "qfm_signal_strength": qfm_signal_strength,
            }

            # Update reason to include QFM enhancement
            original_reason = base_signal.get("reason", "")
            qfm_reason = f"QFM Enhanced (Bias: {qfm_bias:.2f})"
            enhanced_signal["reason"] = f"{original_reason} | {qfm_reason}"

            return enhanced_signal

        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"QFM enhancement error: {exc}")
            return base_signal

    def should_enter_long(self, symbol, market_data, indicators=None):
        """Determine if should enter long position"""
        return False

    def should_enter_short(self, symbol, market_data, indicators=None):
        """Determine if should enter short position"""
        return False

    def should_exit_long(self, symbol, market_data, indicators=None):
        """Determine if should exit long position"""
        return False

    def should_exit_short(self, symbol, market_data, indicators=None):
        """Determine if should exit short position"""
        return False

    def calculate_position_size(self, symbol, market_data, risk_percentage=0.02):
        """Calculate position size based on risk management"""
        return 0.0

    def update_performance(self, trade_result):
        """Update performance metrics after a trade"""
        self.performance_metrics["total_trades"] += 1
        self.performance_metrics["total_pnl"] += trade_result.get("pnl", 0)

        if trade_result.get("pnl", 0) > 0:
            self.performance_metrics["winning_trades"] += 1
        else:
            self.performance_metrics["losing_trades"] += 1

        if self.performance_metrics["total_trades"] > 0:
            self.performance_metrics["win_rate"] = (
                self.performance_metrics["winning_trades"]
                / self.performance_metrics["total_trades"]
            ) * 100

        self.performance_metrics["last_updated"] = time.time()
        self.trade_history.append(trade_result)

    def get_performance_summary(self):
        """Get performance summary"""
        return self.performance_metrics.copy()


class TrendFollowingStrategy(BaseStrategy):
    """Trend Following Strategy - Buy strength, sell weakness"""

    def __init__(self):
        super().__init__(
            "Trend Following",
            "Follows market trends using moving averages and momentum indicators",
            {
                "fast_ma_period": 20,
                "slow_ma_period": 50,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "trend_strength_threshold": 0.001,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.04,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze market using trend following logic with QFM enhancement"""
        if not market_data or len(market_data) < 50:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-100:]]
        )

        # Calculate moving averages
        fast_ma = prices.rolling(window=self.parameters["fast_ma_period"]).mean()
        slow_ma = prices.rolling(window=self.parameters["slow_ma_period"]).mean()

        # Calculate RSI
        delta = prices.diff()
        gain = (
            (delta.where(delta > 0, 0))
            .rolling(window=self.parameters["rsi_period"])
            .mean()
        )
        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(window=self.parameters["rsi_period"])
            .mean()
        )
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_price = prices.iloc[-1]
        current_fast_ma = fast_ma.iloc[-1]
        current_slow_ma = slow_ma.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Trend analysis
        trend_up = current_fast_ma > current_slow_ma and current_price > current_fast_ma
        trend_down = (
            current_fast_ma < current_slow_ma and current_price < current_fast_ma
        )

        # Momentum confirmation
        price_change = (current_price - prices.iloc[-10]) / prices.iloc[-10]
        strong_trend = abs(price_change) > self.parameters["trend_strength_threshold"]

        signal = "HOLD"
        confidence = 0.0
        reason = "No clear trend"

        if (
            trend_up
            and strong_trend
            and current_rsi < self.parameters["rsi_overbought"]
        ):
            signal = "BUY"
            confidence = 0.7
            reason = f"Uptrend confirmed: Fast MA > Slow MA, strong momentum ({price_change:.1%})"
        elif (
            trend_down
            and strong_trend
            and current_rsi > self.parameters["rsi_oversold"]
        ):
            signal = "SELL"
            confidence = 0.7
            reason = f"Downtrend confirmed: Fast MA < Slow MA, strong momentum ({price_change:.1%})"

        base_signal = {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "fast_ma": current_fast_ma,
                "slow_ma": current_slow_ma,
                "rsi": current_rsi,
                "trend_strength": price_change,
            },
        }

        return self.enhance_with_qfm(symbol, market_data, base_signal)


class MeanReversionStrategy(BaseStrategy):
    """Mean Reversion Strategy - Buy low, sell high"""

    def __init__(self):
        super().__init__(
            "Mean Reversion",
            "Trades against extreme price movements expecting reversion to mean",
            {
                "lookback_period": 20,
                "entry_threshold": 2.0,  # Standard deviations
                "exit_threshold": 0.5,  # Standard deviations
                "max_hold_period": 10,  # candles
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze market using mean reversion logic"""
        if (
            not market_data
            or len(market_data) < self.parameters["lookback_period"] + 10
        ):
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-100:]]
        )

        # Calculate Bollinger Bands
        sma = prices.rolling(window=self.parameters["lookback_period"]).mean()
        std = prices.rolling(window=self.parameters["lookback_period"]).std()
        upper_band = sma + (std * self.parameters["entry_threshold"])
        lower_band = sma - (std * self.parameters["entry_threshold"])

        current_price = prices.iloc[-1]
        current_sma = sma.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]

        # Calculate z-score
        z_score = (
            (current_price - current_sma) / std.iloc[-1] if std.iloc[-1] != 0 else 0
        )

        signal = "HOLD"
        confidence = 0.0
        reason = "Price within normal range"

        # Mean reversion signals
        if (
            current_price <= current_lower
            and z_score <= -self.parameters["entry_threshold"]
        ):
            signal = "BUY"
            confidence = min(0.8, abs(z_score) / 3.0)
            reason = f"Oversold: Price {abs(z_score):.1f} SD below mean"
        elif (
            current_price >= current_upper
            and z_score >= self.parameters["entry_threshold"]
        ):
            signal = "SELL"
            confidence = min(0.8, abs(z_score) / 3.0)
            reason = f"Overbought: Price {z_score:.1f} SD above mean"

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "sma": current_sma,
                "upper_band": current_upper,
                "lower_band": current_lower,
                "z_score": z_score,
                "current_price": current_price,
            },
        }


class BreakoutStrategy(BaseStrategy):
    """Breakout Strategy - Trade breakouts of key levels"""

    def __init__(self):
        super().__init__(
            "Breakout Trading",
            "Trades breakouts above resistance or below support levels",
            {
                "lookback_period": 20,
                "breakout_threshold": 0.005,  # 0.5% breakout
                "volume_multiplier": 1.5,  # Volume confirmation
                "consolidation_period": 10,  # candles
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.03,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze market for breakout patterns"""
        if (
            not market_data
            or len(market_data) < self.parameters["lookback_period"] + 10
        ):
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-50:]]
        )
        volumes = pd.Series([d.get("volume", 1) for d in market_data[-50:]])

        # Calculate resistance/support levels
        recent_high = prices.rolling(window=self.parameters["lookback_period"]).max()
        recent_low = prices.rolling(window=self.parameters["lookback_period"]).min()

        # Check for consolidation (low volatility)
        price_range = recent_high - recent_low
        avg_range = price_range.rolling(
            window=self.parameters["consolidation_period"]
        ).mean()
        consolidation = price_range.iloc[-1] < avg_range.iloc[-1] * 0.7

        current_price = prices.iloc[-1]
        current_volume = volumes.iloc[-1]
        avg_volume = (
            volumes.rolling(window=self.parameters["lookback_period"]).mean().iloc[-1]
        )

        resistance_level = recent_high.iloc[-1]
        support_level = recent_low.iloc[-1]

        signal = "HOLD"
        confidence = 0.0
        reason = "No breakout conditions met"

        # Bullish breakout
        if (
            consolidation
            and current_price
            > resistance_level * (1 + self.parameters["breakout_threshold"])
            and current_volume > avg_volume * self.parameters["volume_multiplier"]
        ):
            signal = "BUY"
            confidence = 0.75
            reason = (
                f"Bullish breakout: Price broke resistance with volume confirmation"
            )

        # Bearish breakout
        elif (
            consolidation
            and current_price
            < support_level * (1 - self.parameters["breakout_threshold"])
            and current_volume > avg_volume * self.parameters["volume_multiplier"]
        ):
            signal = "SELL"
            confidence = 0.75
            reason = f"Bearish breakout: Price broke support with volume confirmation"

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "resistance": resistance_level,
                "support": support_level,
                "current_price": current_price,
                "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1,
                "consolidation": consolidation,
            },
        }


class MomentumStrategy(BaseStrategy):
    """Momentum Strategy - Ride momentum waves"""

    def __init__(self):
        super().__init__(
            "Momentum Trading",
            "Trades in the direction of strong momentum",
            {
                "momentum_period": 14,
                "acceleration_period": 5,
                "momentum_threshold": 0.02,
                "rsi_period": 14,
                "rsi_filter": True,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.05,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze market momentum with QFM enhancement"""
        if (
            not market_data
            or len(market_data) < self.parameters["momentum_period"] + 10
        ):
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Insufficient data"}

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-100:]]
        )

        # Calculate momentum (rate of change)
        momentum = (
            prices - prices.shift(self.parameters["momentum_period"])
        ) / prices.shift(self.parameters["momentum_period"])

        # Calculate acceleration (change in momentum)
        acceleration = momentum - momentum.shift(self.parameters["acceleration_period"])

        # Calculate RSI
        delta = prices.diff()
        gain = (
            (delta.where(delta > 0, 0))
            .rolling(window=self.parameters["rsi_period"])
            .mean()
        )
        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(window=self.parameters["rsi_period"])
            .mean()
        )
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_price = prices.iloc[-1]
        current_momentum = momentum.iloc[-1]
        current_acceleration = acceleration.iloc[-1]
        current_rsi = rsi.iloc[-1]

        signal = "HOLD"
        confidence = 0.0
        reason = "No momentum signal"

        # Strong bullish momentum
        if (
            current_momentum > self.parameters["momentum_threshold"]
            and current_acceleration > 0
            and (not self.parameters["rsi_filter"] or current_rsi < 70)
        ):
            signal = "BUY"
            confidence = min(0.85, current_momentum * 10)
            reason = f"Strong bullish momentum: {current_momentum:.1%} ROC"

        # Strong bearish momentum
        elif (
            current_momentum < -self.parameters["momentum_threshold"]
            and current_acceleration < 0
            and (not self.parameters["rsi_filter"] or current_rsi > 30)
        ):
            signal = "SELL"
            confidence = min(0.85, abs(current_momentum) * 10)
            reason = f"Strong bearish momentum: {current_momentum:.1%} ROC"

        base_signal = {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "momentum": current_momentum,
                "acceleration": current_acceleration,
                "rsi": current_rsi,
                "current_price": current_price,
            },
        }

        # Enhance with QFM
        return self.enhance_with_qfm(symbol, market_data, base_signal)


class ArbitrageStrategy(BaseStrategy):
    """Statistical Arbitrage Strategy - Exploit price inefficiencies"""

    def __init__(self):
        super().__init__(
            "Statistical Arbitrage",
            "Exploits statistical relationships between correlated assets",
            {
                "correlation_window": 50,
                "entry_threshold": 2.0,  # Standard deviations
                "exit_threshold": 0.5,  # Standard deviations
                "max_holding_period": 5,  # candles
                "hedge_ratio_lookback": 30,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze for arbitrage opportunities"""
        # This is a simplified version - real stat arb requires multiple correlated assets
        if not market_data or len(market_data) < self.parameters["correlation_window"]:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": "Insufficient data for arbitrage analysis",
            }

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-100:]]
        )

        # Calculate moving average and standard deviation
        ma = prices.rolling(window=self.parameters["correlation_window"]).mean()
        std = prices.rolling(window=self.parameters["correlation_window"]).std()

        current_price = prices.iloc[-1]
        current_ma = ma.iloc[-1]
        current_std = std.iloc[-1]

        # Calculate z-score from mean
        z_score = (current_price - current_ma) / current_std if current_std != 0 else 0

        signal = "HOLD"
        confidence = 0.0
        reason = "No arbitrage opportunity"

        # Statistical arbitrage signals based on deviation from mean
        if z_score <= -self.parameters["entry_threshold"]:
            signal = "BUY"
            confidence = min(0.6, abs(z_score) / 4.0)
            reason = f"Statistical arbitrage: Price {abs(z_score):.1f} SD below mean"
        elif z_score >= self.parameters["entry_threshold"]:
            signal = "SELL"
            confidence = min(0.6, abs(z_score) / 4.0)
            reason = f"Statistical arbitrage: Price {z_score:.1f} SD above mean"

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "z_score": z_score,
                "mean": current_ma,
                "std": current_std,
                "current_price": current_price,
            },
        }


class MLBasedStrategy(BaseStrategy):
    """Machine Learning Based Strategy - Uses ML predictions"""

    def __init__(self):
        super().__init__(
            "ML-Based Strategy",
            "Uses machine learning models for trading decisions",
            {
                "confidence_threshold": 0.65,
                "use_ensemble": True,
                "feature_window": 20,
                "prediction_horizon": 5,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.04,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Use ML predictions for trading signals with QFM enhancement"""
        if not market_data or len(market_data) < self.parameters["feature_window"]:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": "Insufficient data for ML analysis",
            }

        signal = "HOLD"
        confidence = 0.0
        reason = "ML analysis in progress"

        prices = pd.Series(
            [d.get("close", d.get("price", 0)) for d in market_data[-20:]]
        )

        if len(prices) >= 5:
            short_trend = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5]
            if short_trend > 0.01:  # 1% uptrend
                signal = "BUY"
                confidence = 0.7
                reason = "ML prediction: Bullish trend detected"
            elif short_trend < -0.01:  # 1% downtrend
                signal = "SELL"
                confidence = 0.7
                reason = "ML prediction: Bearish trend detected"

        base_signal = {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "ml_confidence": confidence,
                "prediction_type": "trend_following",
            },
        }

        return self.enhance_with_qfm(symbol, market_data, base_signal)


class ScalpingStrategy(BaseStrategy):
    """Scalping Strategy - Quick profits from small price movements"""

    def __init__(self):
        super().__init__(
            "Scalping",
            "Makes quick trades capturing small price movements",
            {
                "tick_size": 0.001,  # Minimum price movement
                "target_pips": 5,  # Target in pips
                "max_holding_time": 300,  # 5 minutes max
                "volume_threshold": 1.2,  # Volume confirmation
                "spread_filter": True,
            },
        )

    def analyze_market(self, symbol, market_data, indicators=None):
        """Analyze for scalping opportunities"""
        if not market_data or len(market_data) < 10:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": "Insufficient data for scalping",
            }

        recent_prices = [d.get("close", d.get("price", 0)) for d in market_data[-10:]]
        recent_volumes = [d.get("volume", 1) for d in market_data[-10:]]

        current_price = recent_prices[-1]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = recent_volumes[-1]

        price_changes = []
        for i in range(1, len(recent_prices)):
            change = (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
            price_changes.append(change)

        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0

        signal = "HOLD"
        confidence = 0.0
        reason = "No scalping opportunity"

        if (
            abs(avg_change) > self.parameters["tick_size"]
            and current_volume > avg_volume * self.parameters["volume_threshold"]
        ):
            if avg_change > 0:
                signal = "BUY"
                confidence = 0.6
                reason = f"Scalping: Upward momentum with volume"
            else:
                signal = "SELL"
                confidence = 0.6
                reason = f"Scalping: Downward momentum with volume"

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "indicators": {
                "avg_change": avg_change,
                "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1,
                "current_price": current_price,
            },
        }
