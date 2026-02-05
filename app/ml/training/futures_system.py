import os
import time
import logging
from typing import Optional
from app.services.pathing import resolve_profile_path
from app.services import get_real_market_data
from app.runtime.indicators import BEST_INDICATORS
from app.ml.training.system import UltimateMLTrainingSystem
from app.trading.futures.module import FuturesTradingModule

class FuturesMLTrainingSystem(UltimateMLTrainingSystem):
    """ML System enhanced with futures-specific features"""

    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = resolve_profile_path(
                "futures_models", allow_legacy=False, migrate_legacy=True
            )
        elif not os.path.isabs(models_dir):
            models_dir = resolve_profile_path(models_dir, allow_legacy=True)
        super().__init__(models_dir=models_dir, profile_key="futures")
        self.futures_module = FuturesTradingModule()
        self.futures_indicators = (
            BEST_INDICATORS + self.futures_module.futures_indicators
        )
        print("✅ Futures ML Training System Initialized")

    def create_futures_features(self, df):
        try:
            features = self.create_ultimate_features(df)
            if features is None or features.empty:
                return features
            features = self._add_futures_features(features, df)
            print(f"✅ Futures features created: {len(features.columns)} indicators")
            return features
        except Exception as e:
            print(f"❌ Futures feature creation error: {e}")
            return self.create_ultimate_features(df)

    def _add_futures_features(self, features, df):
        try:
            futures_features = super()._add_futures_features(features, df)
            return futures_features
        except Exception as e:
            print(f"❌ Adding futures features error: {e}")
            return features

    def get_futures_market_data(self, symbol):
        try:
            standard_data = get_real_market_data(symbol)
            futures_data = self._get_futures_specific_data(symbol)
            enhanced_data = {**standard_data, **futures_data}
            self.futures_module.update_funding_rates(symbol, futures_data)
            return enhanced_data
        except Exception as e:
            print(f"❌ Futures market data error: {e}")
            return get_real_market_data(symbol)

    def _get_futures_specific_data(self, symbol):
        try:
            trader = getattr(self, "futures_trader", None)
            if trader and trader.is_ready():
                metrics = trader.get_market_metrics(symbol)
                if metrics:
                    return metrics
            # Fallback to neutral defaults if live data unavailable
            return {
                "funding_rate": 0.0,
                "open_interest": 0.0,
                "open_interest_change": 0.0,
                "long_liquidations": 0.0,
                "short_liquidations": 0.0,
                "basis": 0.0,
                "long_short_ratio": 1.0,
                "taker_buy_volume": 0.0,
                "estimated_liquidation_price": 0.0,
                "mark_price": None,
                "index_price": None,
                "timestamp": time.time(),
            }
        except Exception as e:
            print(f"❌ Futures specific data error: {e}")
            return {
                "funding_rate": 0.0,
                "open_interest": 0.0,
                "open_interest_change": 0.0,
                "long_liquidations": 0.0,
                "short_liquidations": 0.0,
                "basis": 0.0,
                "long_short_ratio": 1.0,
                "taker_buy_volume": 0.0,
                "estimated_liquidation_price": 0.0,
                "mark_price": None,
                "index_price": None,
                "timestamp": time.time(),
            }

    def predict_futures(self, symbol, market_data):
        try:
            base_prediction = self.predict_ultimate(
                symbol, market_data, include_futures=False
            )
            if not base_prediction:
                return None

            historical_prices = []
            futures_signals = self.futures_module.generate_futures_signals(
                symbol, market_data, historical_prices
            )

            enhanced_prediction = self._enhance_with_futures_signals(
                base_prediction, futures_signals
            )
            return enhanced_prediction
        except Exception as e:
            print(f"❌ Futures prediction error: {e}")
            return self.predict_ultimate(symbol, market_data)

    def _enhance_with_futures_signals(self, base_prediction, futures_signals):
        try:
            if not futures_signals:
                return base_prediction

            futures_buy_strength = 0
            futures_sell_strength = 0
            futures_count = 0

            for signal in futures_signals:
                if signal["signal"] in ["BUY", "STRONG_BUY"]:
                    futures_buy_strength += signal.get("confidence", 0)
                else:
                    futures_sell_strength += signal.get("confidence", 0)
                futures_count += 1

            if futures_count > 0:
                futures_net_strength = (
                    futures_buy_strength - futures_sell_strength
                ) / futures_count
                ensemble_block = base_prediction.get("ultimate_ensemble", {})
                base_confidence = ensemble_block.get("confidence", 0.5)
                adjusted_confidence = min(
                    0.95, base_confidence + (futures_net_strength * 0.2)
                )
                ensemble_block["confidence"] = adjusted_confidence
                ensemble_block["futures_signals_count"] = futures_count
                ensemble_block["futures_net_strength"] = futures_net_strength
                base_prediction["ultimate_ensemble"] = ensemble_block

            base_prediction["futures_signals"] = futures_signals
            return base_prediction
        except Exception as e:
            print(f"❌ Futures signal enhancement error: {e}")
            return base_prediction


