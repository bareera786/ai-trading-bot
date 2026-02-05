import pandas as pd
from datetime import datetime

class ICTIndicatorModule:
    """Derives ICT-inspired metrics such as liquidity pools and fair value gaps."""

    def __init__(self):
        self.signal_cache = {}
        print("🎯 ICT Indicator Module Initialized")

    def compute_features(self, df):
        try:
            features = pd.DataFrame(index=df.index)

            high = df["high"].astype(float)
            low = df["low"].astype(float)
            close = df["close"].astype(float)

            # Liquidity pools (recent swing highs/lows clustering)
            swing_high = high.rolling(5, min_periods=1).max()
            swing_low = low.rolling(5, min_periods=1).min()
            features["ict_liquidity_bias"] = (
                (close - swing_low) / (swing_high - swing_low + 1e-9)
            ).clip(0, 1)

            # Fair value gap approximation: distance between previous high/low around current close
            prev_high = high.shift(1)
            prev_low = low.shift(1)
            fvg_upper = prev_high
            fvg_lower = prev_low
            gap = (fvg_upper - fvg_lower).abs()
            features["ict_fvg_size"] = gap.fillna(0)
            features["ict_fvg_presence"] = (gap > close * 0.002).astype(int)

            # Session bias (simplified): compare current close to rolling mean
            daily_bias = close - close.rolling(24, min_periods=6).mean()
            features["ict_daily_bias"] = daily_bias.fillna(0)

            # Mean threshold deviation (50% of range)
            threshold = (swing_high + swing_low) / 2
            features["ict_mean_threshold_dev"] = (close - threshold).fillna(0)

            # Session range compression/expansion
            session_range = (
                high.rolling(24, min_periods=6).max()
                - low.rolling(24, min_periods=6).min()
            )
            features["ict_session_range"] = session_range.fillna(0)

            return features
        except Exception as e:
            print(f"❌ ICT feature computation error: {e}")
            return pd.DataFrame(index=df.index)

    def generate_signals(self, symbol, market_data, historical_prices):
        try:
            price = float(market_data.get("price") or market_data.get("close") or 0)
            liquidity_bias = market_data.get("ict_liquidity_bias", 0.5)
            fvg_presence = market_data.get("ict_fvg_presence", 0)
            daily_bias = market_data.get("ict_daily_bias", 0)

            bias_signal = "BULLISH" if daily_bias > 0 else "BEARISH"
            liquidity_signal = (
                "SEEK_PREMIUM" if liquidity_bias > 0.6 else "SEEK_DISCOUNT"
            )
            fvg_signal = "FVG_PRESENT" if fvg_presence else "NO_FVG"

            signal = {
                "symbol": symbol,
                "signal_type": "ICT",
                "confidence_score": 0.7
                if bias_signal == "BULLISH"
                else 0.6
                if bias_signal == "BEARISH"
                else 0.5,
                "timestamp": datetime.now().isoformat(),
                "current_price": price,
                "target_price": price
                * (
                    1.02
                    if bias_signal == "BULLISH"
                    else 0.98
                    if bias_signal == "BEARISH"
                    else 1.0
                ),
                "stop_loss": price
                * (
                    0.98
                    if bias_signal == "BULLISH"
                    else 1.02
                    if bias_signal == "BEARISH"
                    else 1.0
                ),
                "time_frame": "MULTI_TIMEFRAME",
                "model_version": "ICT_v1.0",
                "reason_code": f"ICT_{bias_signal}_{liquidity_signal}",
                "signal": "BUY"
                if bias_signal == "BULLISH"
                else "SELL"
                if bias_signal == "BEARISH"
                else "HOLD",
                "price": price,
                "bias_signal": bias_signal,
                "liquidity_signal": liquidity_signal,
                "fvg_signal": fvg_signal,
                "liquidity_bias": liquidity_bias,
                "daily_bias": daily_bias,
            }

            self.signal_cache[symbol] = signal
            return signal
        except Exception as e:
            print(f"❌ ICT signal generation error for {symbol}: {e}")
            return self.signal_cache.get(symbol, {})

    def get_dashboard_data(self, symbol=None):
        if symbol:
            return self.signal_cache.get(symbol, {})
        return self.signal_cache
