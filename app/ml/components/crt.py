import logging
import numpy as np
from datetime import datetime
from scipy import stats
from app.core.logging import log_warning_once

# TA-Lib setup with fallbacks
try:
    import talib
    _TALIB_AVAILABLE = True
except Exception:
    from types import SimpleNamespace
    talib = SimpleNamespace()
    _TALIB_AVAILABLE = False

from app.indicators.fallbacks import register_fallbacks

if not _TALIB_AVAILABLE:
    register_fallbacks(talib)


class CRTSignalGenerator:
    """
    Comprehensive Resonance Theory (CRT) Signal Generator
    Combines momentum, trend, volume, and multi-timeframe analysis.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signals_history = {}
        self.crt_config = {
            "timeframes": ["1h", "4h", "1d", "1w"],
            "primary_indicators": ["RSI", "MACD", "BBANDS", "STOCH", "ADX", "ICHIMOKU"],
            "momentum_threshold": 0.6,
            "trend_strength_threshold": 0.7,
            "volume_confirmation": True,
            "pattern_recognition": True,
        }
        print("🎯 CRT Signal Generator Initialized")

    def generate_crt_signals(self, symbol, market_data, historical_prices):
        """Generate comprehensive CRT signals"""
        try:
            if len(historical_prices) < 50:
                self.logger.warning(
                    f"Insufficient data for {symbol}: {len(historical_prices)} candles < 50 minimum"
                )
                return self._get_default_signal(symbol)

            signals = {}

            # 1. Multi-timeframe Analysis
            signals["multi_timeframe"] = self._multi_timeframe_analysis(
                historical_prices
            )

            # 2. Momentum Composite
            signals["momentum_composite"] = self._momentum_composite_analysis(
                historical_prices
            )

            # 3. Trend Analysis
            signals["trend_analysis"] = self._trend_analysis(historical_prices)

            # 4. Volume Analysis
            signals["volume_analysis"] = self._volume_analysis(
                market_data, historical_prices
            )

            # 5. Pattern Recognition
            signals["pattern_recognition"] = self._pattern_recognition(
                historical_prices
            )

            # 6. Market Structure
            signals["market_structure"] = self._market_structure_analysis(
                historical_prices
            )

            # 7. Generate Composite Signal
            composite_signal = self._generate_composite_signal(
                symbol, signals, market_data
            )

            # Store in history
            self.signals_history[symbol] = {
                "timestamp": datetime.now().isoformat(),
                "signals": signals,
                "composite_signal": composite_signal,
            }

            return composite_signal

        except Exception as e:
            self.logger.error(
                f"CRT signal generation failed for {symbol}: {str(e)}",
                extra={
                    "symbol": symbol,
                    "data_points": len(historical_prices)
                    if "historical_prices" in locals()
                    else 0,
                    "market_data_keys": list(market_data.keys())
                    if "market_data" in locals()
                    else [],
                    "error_type": type(e).__name__,
                },
            )
            return self._get_default_signal(symbol)

    def _multi_timeframe_analysis(self, prices):
        """Multi-timeframe technical analysis"""
        try:
            analysis = {}

            # Analyze different timeframes using different window sizes
            timeframes = {
                "short_term": 20,  # ~1 month
                "medium_term": 50,  # ~2 months
                "long_term": 100,  # ~4 months
            }

            for tf_name, window in timeframes.items():
                if len(prices) >= window:
                    tf_prices = prices[-window:]

                    # RSI Analysis
                    rsi = talib.RSI(np.array(tf_prices), timeperiod=14)
                    rsi_signal = (
                        "BULLISH"
                        if rsi[-1] > 50
                        else "BEARISH"
                        if rsi[-1] < 50
                        else "NEUTRAL"
                    )

                    # MACD Analysis
                    macd, macd_signal, macd_hist = talib.MACD(np.array(tf_prices))
                    macd_trend = "BULLISH" if macd_hist[-1] > 0 else "BEARISH"

                    # Moving Average Analysis
                    sma_20 = talib.SMA(np.array(tf_prices), timeperiod=20)
                    sma_50 = talib.SMA(np.array(tf_prices), timeperiod=50)
                    ma_trend = "BULLISH" if sma_20[-1] > sma_50[-1] else "BEARISH"

                    analysis[tf_name] = {
                        "rsi": float(rsi[-1]) if not np.isnan(rsi[-1]) else 50,
                        "rsi_signal": rsi_signal,
                        "macd_trend": macd_trend,
                        "ma_trend": ma_trend,
                        "price_trend": "BULLISH"
                        if tf_prices[-1] > tf_prices[0]
                        else "BEARISH",
                    }

            return analysis

        except Exception as e:
            log_warning_once(
                "CRT_ANALYSIS",
                "MULTI_TIMEFRAME",
                f"Multi-timeframe analysis error: {e}",
            )
            return {}

    def _momentum_composite_analysis(self, prices):
        """Composite momentum analysis using multiple indicators"""
        try:
            momentum_score = 0
            total_indicators = 0

            # RSI Momentum
            rsi = talib.RSI(np.array(prices), timeperiod=14)
            if not np.isnan(rsi[-1]):
                rsi_strength = (rsi[-1] - 50) / 50  # -1 to 1
                momentum_score += rsi_strength
                total_indicators += 1

            # MACD Momentum
            macd, macd_signal, macd_hist = talib.MACD(np.array(prices))
            if len(macd_hist) > 0 and not np.isnan(macd_hist[-1]):
                macd_strength = np.tanh(macd_hist[-1] * 10)  # Normalize
                momentum_score += macd_strength
                total_indicators += 1

            # Stochastic Momentum
            slowk, slowd = talib.STOCH(
                np.array(prices), np.array(prices), np.array(prices)
            )
            if not np.isnan(slowk[-1]):
                stoch_strength = (slowk[-1] - 50) / 50
                momentum_score += stoch_strength
                total_indicators += 1

            # Average momentum score
            avg_momentum = (
                momentum_score / total_indicators if total_indicators > 0 else 0
            )

            return {
                "momentum_score": float(avg_momentum),
                "strength": "STRONG"
                if abs(avg_momentum) > 0.3
                else "MODERATE"
                if abs(avg_momentum) > 0.1
                else "WEAK",
                "direction": "BULLISH" if avg_momentum > 0 else "BEARISH",
            }

        except Exception as e:
            print(f"❌ Momentum analysis error: {e}")
            return {"momentum_score": 0, "strength": "NEUTRAL", "direction": "NEUTRAL"}

    def _trend_analysis(self, prices):
        """Comprehensive trend analysis"""
        try:
            if len(prices) < 20:
                return {"trend": "SIDEWAYS", "strength": 0, "direction": 0}

            # Linear regression trend
            x = np.arange(len(prices))
            linreg_result = stats.linregress(x, prices)
            slope = linreg_result.slope  # type: ignore
            r_value = linreg_result.rvalue  # type: ignore

            # ADX for trend strength
            high = np.array(prices) * 1.01  # Simulated high
            low = np.array(prices) * 0.99  # Simulated low
            adx = talib.ADX(high, low, np.array(prices), timeperiod=14)
            adx_strength = adx[-1] / 100 if not np.isnan(adx[-1]) else 0

            # Moving average alignment
            sma_20 = talib.SMA(np.array(prices), timeperiod=20)
            sma_50 = talib.SMA(np.array(prices), timeperiod=50)
            ma_alignment = 1 if sma_20[-1] > sma_50[-1] else -1

            trend_strength = (abs(slope) * 1000 + adx_strength + abs(ma_alignment)) / 3

            return {
                "trend": "UPTREND" if slope > 0 else "DOWNTREND",
                "strength": float(trend_strength),
                "slope": float(slope),
                "r_squared": float(r_value**2),
                "adx_strength": float(adx_strength),
            }

        except Exception as e:
            log_warning_once("CRT_ANALYSIS", "TREND", f"Trend analysis error: {e}")
            return {"trend": "SIDEWAYS", "strength": 0, "direction": 0}

    def _volume_analysis(self, market_data, prices):
        """Volume-based analysis"""
        try:
            volume = market_data.get("volume", 1000000)
            volume_change = market_data.get("volume_change", 0)

            # Simple volume analysis
            volume_trend = "BULLISH" if volume_change > 0 else "BEARISH"
            volume_strength = min(abs(volume_change) / 100, 1.0)

            return {
                "volume_trend": volume_trend,
                "volume_strength": float(volume_strength),
                "volume_change_percent": float(volume_change),
            }

        except Exception as e:
            print(f"❌ Volume analysis error: {e}")
            return {
                "volume_trend": "NEUTRAL",
                "volume_strength": 0,
                "volume_change_percent": 0,
            }

    def _pattern_recognition(self, prices):
        """Candlestick pattern recognition"""
        try:
            patterns = {}

            # Convert to OHLC format (simplified)
            opens = np.array([p * 0.998 for p in prices])  # Simulated open
            highs = np.array([p * 1.005 for p in prices])  # Simulated high
            lows = np.array([p * 0.995 for p in prices])  # Simulated low
            closes = np.array(prices)

            # Detect common patterns
            patterns_found = []

            # Bullish patterns
            if talib.CDLHAMMER(opens, highs, lows, closes)[-1] > 0:
                patterns_found.append("HAMMER")
            if talib.CDLENGULFING(opens, highs, lows, closes)[-1] > 0:
                patterns_found.append("BULLISH_ENGULFING")
            if talib.CDLMORNINGSTAR(opens, highs, lows, closes)[-1] > 0:
                patterns_found.append("MORNING_STAR")

            # Bearish patterns
            if talib.CDLHANGINGMAN(opens, highs, lows, closes)[-1] > 0:
                patterns_found.append("HANGING_MAN")
            if talib.CDLENGULFING(opens, highs, lows, closes)[-1] < 0:
                patterns_found.append("BEARISH_ENGULFING")
            if talib.CDLEVENINGSTAR(opens, highs, lows, closes)[-1] > 0:
                patterns_found.append("EVENING_STAR")

            return {
                "patterns_detected": patterns_found,
                "pattern_count": len(patterns_found),
                "signal": "BULLISH"
                if len([p for p in patterns_found if "BULL" in p])
                > len([p for p in patterns_found if "BEAR" in p])
                else "BEARISH",
            }

        except Exception as e:
            log_warning_once(
                "CRT_ANALYSIS", "PATTERN", f"Pattern recognition error: {e}"
            )
            return {"patterns_detected": [], "pattern_count": 0, "signal": "NEUTRAL"}

    def _market_structure_analysis(self, prices):
        """Market structure and support/resistance analysis"""
        try:
            if len(prices) < 20:
                return {
                    "support_levels": [],
                    "resistance_levels": [],
                    "market_structure": "UNKNOWN",
                }

            # Simple support/resistance detection
            recent_prices = prices[-20:]
            support_levels = []
            resistance_levels = []

            # Find local minima and maxima
            for i in range(2, len(recent_prices) - 2):
                if (
                    recent_prices[i] < recent_prices[i - 1]
                    and recent_prices[i] < recent_prices[i - 2]
                    and recent_prices[i] < recent_prices[i + 1]
                    and recent_prices[i] < recent_prices[i + 2]
                ):
                    support_levels.append(float(recent_prices[i]))

                if (
                    recent_prices[i] > recent_prices[i - 1]
                    and recent_prices[i] > recent_prices[i - 2]
                    and recent_prices[i] > recent_prices[i + 1]
                    and recent_prices[i] > recent_prices[i + 2]
                ):
                    resistance_levels.append(float(recent_prices[i]))

            current_price = prices[-1]
            nearest_support = (
                min(support_levels, key=lambda x: abs(x - current_price))
                if support_levels
                else 0
            )
            nearest_resistance = (
                min(resistance_levels, key=lambda x: abs(x - current_price))
                if resistance_levels
                else 0
            )

            return {
                "support_levels": support_levels[:3],  # Top 3
                "resistance_levels": resistance_levels[:3],  # Top 3
                "nearest_support": float(nearest_support),
                "nearest_resistance": float(nearest_resistance),
                "market_structure": "UPTREND"
                if current_price > nearest_support
                else "DOWNTREND",
            }

        except Exception as e:
            print(f"❌ Market structure analysis error: {e}")
            return {
                "support_levels": [],
                "resistance_levels": [],
                "market_structure": "UNKNOWN",
            }

    def _generate_composite_signal(self, symbol, signals, market_data):
        """Generate composite CRT signal from all analyses"""
        try:
            composite_score = 0
            signal_components = {}

            # Momentum component (30% weight)
            momentum = signals.get("momentum_composite", {})
            momentum_score = momentum.get("momentum_score", 0)
            composite_score += momentum_score * 0.3
            signal_components["momentum"] = momentum_score

            # Trend component (25% weight)
            trend = signals.get("trend_analysis", {})
            trend_strength = trend.get("strength", 0)
            trend_direction = 1 if trend.get("trend") == "UPTREND" else -1
            composite_score += trend_strength * trend_direction * 0.25
            signal_components["trend"] = trend_strength * trend_direction

            # Multi-timeframe component (20% weight)
            mtf = signals.get("multi_timeframe", {})
            mtf_score = self._calculate_mtf_score(mtf)
            composite_score += mtf_score * 0.2
            signal_components["multi_timeframe"] = mtf_score

            # Volume component (15% weight)
            volume = signals.get("volume_analysis", {})
            volume_score = volume.get("volume_strength", 0) * (
                1 if volume.get("volume_trend") == "BULLISH" else -1
            )
            composite_score += volume_score * 0.15
            signal_components["volume"] = volume_score

            # Pattern component (10% weight)
            patterns = signals.get("pattern_recognition", {})
            pattern_score = (
                0.5
                if patterns.get("signal") == "BULLISH"
                else -0.5
                if patterns.get("signal") == "BEARISH"
                else 0
            )
            composite_score += pattern_score * 0.1
            signal_components["patterns"] = pattern_score

            # Generate final signal
            if composite_score > 0.3:
                signal = "STRONG_BUY"
                confidence = min(0.95, (composite_score + 1) / 2)
            elif composite_score > 0.1:
                signal = "BUY"
                confidence = min(0.85, (composite_score + 1) / 2)
            elif composite_score < -0.3:
                signal = "STRONG_SELL"
                confidence = min(0.95, (-composite_score + 1) / 2)
            elif composite_score < -0.1:
                signal = "SELL"
                confidence = min(0.85, (-composite_score + 1) / 2)
            else:
                signal = "HOLD"
                confidence = 0.5

            return {
                "symbol": symbol,  # Add standardized fields
                "signal_type": "COMPOSITE",
                "confidence_score": float(confidence),
                "timestamp": datetime.now().isoformat(),
                "current_price": market_data.get("price", 0),
                "target_price": market_data.get("price", 0)
                * (
                    1.05
                    if signal in ["BUY", "STRONG_BUY"]
                    else 0.95
                    if signal in ["SELL", "STRONG_SELL"]
                    else 1.0
                ),
                "stop_loss": market_data.get("price", 0)
                * (
                    0.97
                    if signal in ["BUY", "STRONG_BUY"]
                    else 1.03
                    if signal in ["SELL", "STRONG_SELL"]
                    else 1.0
                ),
                "time_frame": "MULTI_TIMEFRAME",
                "model_version": "CRT_v1.0",
                "reason_code": f"COMPOSITE_{signal}_{confidence:.2f}",
                "signal": signal,
                "confidence": float(confidence),
                "composite_score": float(composite_score),
                "components": signal_components,
                "market_structure": signals.get("market_structure", {}),
                "momentum_analysis": momentum,
                "trend_analysis": trend,
            }

        except Exception as e:
            print(f"❌ Composite signal generation error: {e}")
            return self._get_default_signal("COMPOSITE_ERROR")

    def _calculate_mtf_score(self, mtf_analysis):
        """Calculate multi-timeframe score"""
        try:
            if not mtf_analysis:
                return 0

            total_score = 0
            timeframe_count = 0

            for tf, analysis in mtf_analysis.items():
                # Score based on alignment of signals
                bullish_signals = 0
                total_signals = 0

                if analysis.get("rsi_signal") == "BULLISH":
                    bullish_signals += 1
                total_signals += 1

                if analysis.get("macd_trend") == "BULLISH":
                    bullish_signals += 1
                total_signals += 1

                if analysis.get("ma_trend") == "BULLISH":
                    bullish_signals += 1
                total_signals += 1

                if analysis.get("price_trend") == "BULLISH":
                    bullish_signals += 1
                total_signals += 1

                tf_score = (bullish_signals / total_signals - 0.5) * 2  # -1 to 1
                total_score += tf_score
                timeframe_count += 1

            return total_score / timeframe_count if timeframe_count > 0 else 0

        except Exception as e:
            print(f"❌ MTF score calculation error: {e}")
            return 0

    def _get_default_signal(self, symbol):
        """Return default signal when analysis fails"""
        return {
            "signal": "HOLD",
            "confidence": 0.5,
            "composite_score": 0,
            "components": {},
            "timestamp": datetime.now().isoformat(),
            "market_structure": {},
            "momentum_analysis": {
                "momentum_score": 0,
                "strength": "NEUTRAL",
                "direction": "NEUTRAL",
            },
            "trend_analysis": {"trend": "SIDEWAYS", "strength": 0},
        }

    def get_crt_dashboard_data(self, symbol=None):
        """Get CRT data for dashboard display"""
        try:
            if symbol:
                return self.signals_history.get(symbol, {})
            else:
                # Return recent signals for all symbols
                recent_signals = {}
                for sym, data in list(self.signals_history.items())[
                    -10:
                ]:  # Last 10 symbols
                    recent_signals[sym] = data
                return recent_signals
        except Exception as e:
            print(f"❌ CRT dashboard data error: {e}")
            return {}
