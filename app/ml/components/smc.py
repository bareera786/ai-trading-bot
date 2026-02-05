import pandas as pd
from datetime import datetime

class SMCIndicatorModule:
    """Derives smart money concepts including structure shifts and order blocks."""

    def __init__(self):
        self.signal_cache = {}
        print("🎯 SMC Indicator Module Initialized")

    def compute_features(self, df):
        try:
            features = pd.DataFrame(index=df.index)

            high = df["high"].astype(float)
            low = df["low"].astype(float)
            close = df["close"].astype(float)

            # Market structure: higher highs / lower lows
            higher_high = (high > high.shift(1)).astype(int)
            lower_low = (low < low.shift(1)).astype(int)
            features["smc_structure_bias"] = (
                (higher_high - lower_low).rolling(3, min_periods=1).mean().fillna(0)
            )

            # Order block strength (stagnation zones)
            order_block = close.rolling(4, min_periods=2).mean()
            features["smc_order_block_strength"] = (
                (order_block.diff().abs() < close * 0.001)
                .astype(int)
                .rolling(6, min_periods=1)
                .sum()
                .fillna(0)
            )

            # Premium/discount of current price relative to 50% range
            range_mid = (
                high.rolling(10, min_periods=5).max()
                + low.rolling(10, min_periods=5).min()
            ) / 2
            premium_discount = (close - range_mid) / (range_mid + 1e-9)
            features["smc_premium_discount"] = premium_discount.fillna(0)

            # Break of structure detection
            prior_high = high.shift(1)
            prior_low = low.shift(1)
            bos_up = (close > prior_high).astype(int)
            bos_down = (close < prior_low).astype(int)
            features["smc_bos_signal"] = bos_up - bos_down

            # Liquidity void / imbalance measure
            imbalance = (close - close.shift(2)).abs()
            features["smc_liquidity_void"] = imbalance.fillna(0)

            return features
        except Exception as e:
            print(f"❌ SMC feature computation error: {e}")
            return pd.DataFrame(index=df.index)

    def generate_signals(self, symbol, market_data, historical_prices):
        try:
            structure_bias = market_data.get("smc_structure_bias", 0)
            premium_discount = market_data.get("smc_premium_discount", 0)
            bos_signal = market_data.get("smc_bos_signal", 0)

            direction = (
                "BULLISH"
                if structure_bias > 0
                else "BEARISH"
                if structure_bias < 0
                else "NEUTRAL"
            )
            premium_state = "PREMIUM" if premium_discount > 0 else "DISCOUNT"
            bos_state = (
                "BOS_UP" if bos_signal > 0 else "BOS_DOWN" if bos_signal < 0 else "NONE"
            )

            # Get current price and other market data
            current_price = market_data.get("close", market_data.get("price", 0))
            target_price = current_price * (
                1.02 if structure_bias > 0 else 0.98
            )  # 2% target
            stop_loss = current_price * (
                0.98 if structure_bias > 0 else 1.02
            )  # 2% stop

            signal = {
                "symbol": symbol,
                "signal_type": "SMC_STRUCTURE",
                "confidence_score": min(0.9, abs(structure_bias) * 0.5 + 0.4),
                "timestamp": datetime.now().isoformat(),
                "current_price": float(current_price),
                "target_price": float(target_price),
                "stop_loss": float(stop_loss),
                "time_frame": "1D",
                "model_version": "SMC_v1.0",
                "reason_code": f"STRUCTURE_{direction}_BOS_{bos_state}",
                "structure_bias": structure_bias,
                "premium_discount": premium_discount,
                "bos_signal": bos_signal,
                "direction": direction,
                "premium_state": premium_state,
                "bos_state": bos_state,
            }

            self.signal_cache[symbol] = signal
            return signal
        except Exception as e:
            print(f"❌ SMC signal generation error for {symbol}: {e}")
            return self.signal_cache.get(symbol, {})

    def get_dashboard_data(self, symbol=None):
        if symbol:
            return self.signal_cache.get(symbol, {})
        return self.signal_cache
