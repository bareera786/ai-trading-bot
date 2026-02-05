import os
import shutil
import tempfile
import threading
import logging
import time
from typing import Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd
import requests
import joblib
import json
import statistics as statistics_lib

from app.services.pathing import resolve_profile_path, safe_parse_datetime
from app.services import get_real_market_data
try:
    from app.services.timescaledb_service import TimescaleDBService
except ImportError:
    TimescaleDBService = None
from app.runtime.symbols import (
    normalize_symbol as _normalize_symbol,
    is_symbol_disabled,
    enable_symbol,
    is_indicator_enabled,
    MARKET_CAP_WEIGHTS
)
from app.core.logging import log_component_event, log_component_debug
from app.runtime.indicators import BEST_INDICATORS
from app.ml.components.ensemble import UltimateEnsembleSystem
from app.ml.components.parallel import ParallelPredictionEngine
from app.ml.components.crt import CRTSignalGenerator
from app.ml.components.ict import ICTIndicatorModule
from app.ml.components.smc import SMCIndicatorModule
from app.strategies import QuantumFusionMomentumEngine
from app.core.config_trading import TRADING_CONFIG

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

def _format_duration_hours(seconds):
    if not seconds:
        return 0.0
    try:
        return round(float(seconds) / 3600.0, 2)
    except Exception:
        return 0.0

# Setup talib fallback
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
class UltimateMLTrainingSystem:
    def __init__(self, models_dir: Optional[str] = None, profile_key="ultimate"):
        if models_dir is None:
            resolved_dir = resolve_profile_path(
                "ultimate_models", allow_legacy=False, migrate_legacy=True
            )
        elif not os.path.isabs(models_dir):
            resolved_dir = resolve_profile_path(models_dir, allow_legacy=True)
        else:
            resolved_dir = models_dir

        os.makedirs(resolved_dir, exist_ok=True)
        self.models_dir = resolved_dir
        self.models = {}
        self.shadow_models = {}  # NEW: Shadow Model Registry
        self.training_logs = []
        self.training_progress = {}
        self.ensemble_system = UltimateEnsembleSystem()
        self.parallel_engine = ParallelPredictionEngine()
        self.crt_generator = CRTSignalGenerator()  # NEW: CRT Module
        self.ict_module = ICTIndicatorModule()
        self.smc_module = SMCIndicatorModule()
        self.qfm_engine = QuantumFusionMomentumEngine()
        self.model_performance_history = {}
        self._training_cycle_active = False
        self.backtest_results = {}
        self.futures_module = None
        self.futures_integration = None
        self._futures_feature_cache = defaultdict(dict)
        self._model_training_locks = defaultdict(threading.Lock)
        self._ict_feature_cache = defaultdict(dict)
        self._smc_feature_cache = defaultdict(dict)
        self.profile_key = profile_key
        
        # Initialize TimescaleDB Service
        self.timescaledb_service = None
        if TimescaleDBService:
             try:
                 self.timescaledb_service = TimescaleDBService()
                 # print("✅ TimescaleDB Service initialized in ML System")
             except Exception as e:
                 print(f"⚠️ TimescaleDB Service init failed: {e}")

        print(
            "✅ ULTIMATE ML Training System with Parallel Processing & CRT Module Initialized"
        )
        log_component_event(
            "TRAINING",
            "Ultimate ML Training System initialized",
            level=logging.INFO,
            details={"profile_key": profile_key, "models_dir": self.models_dir},
        )

    def log_training(self, symbol, message, progress=None):
        """Log training progress"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "message": message,
            "progress": progress,
        }
        self.training_logs.append(log_entry)

        if len(self.training_logs) > 100:
            self.training_logs.pop(0)

        if symbol and progress is not None:
            self.training_progress[symbol] = progress

        level = logging.INFO
        upper_message = str(message).upper()
        if "❌" in str(message) or "FAILED" in upper_message:
            level = logging.ERROR
        elif "⚠️" in str(message) or "WARN" in upper_message:
            level = logging.WARNING

        details = {"symbol": symbol}
        if progress is not None:
            details["progress"] = progress
        log_component_event(
            "TRAINING",
            f"{symbol}: {message}" if symbol else str(message),
            level=level,
            details=details,
        )

        print(f"🤖 [{symbol}] {message}")

    def get_training_logs(self):
        """Get training logs for API endpoint"""
        return self.training_logs[-50:] if self.training_logs else []

    def add_symbol(self, symbol, train_immediately=False):
        """Add or re-enable a symbol in the trading system."""
        normalized = _normalize_symbol(symbol)
        if not normalized:
            return False

        was_disabled = is_symbol_disabled(normalized)
        enable_symbol(normalized, ensure_listed=True)

        print(
            f"✅ Symbol {normalized} {'re-enabled' if was_disabled else 'added'} to trading list"
        )
        log_component_event(
            "TRAINING",
            "Symbol activated for trading",
            level=logging.INFO,
            details={"symbol": normalized, "re_enabled": was_disabled},
        )

        model_ready = normalized in self.models
        if not model_ready:
            loaded = self.load_models(symbol=normalized)
            model_ready = loaded and normalized in self.models

        if train_immediately or not model_ready:
            action = "retraining" if model_ready else "training"
            print(f"🚀 Starting {action} for {normalized}")
            log_component_event(
                "TRAINING",
                f"{action.title()} requested",
                level=logging.INFO,
                details={"symbol": normalized},
            )
            success = self.train_ultimate_model(normalized, use_real_data=True)
            if success:
                print(f"✅ Model ready for {normalized}")
                log_component_event(
                    "TRAINING",
                    "Symbol training completed",
                    level=logging.INFO,
                    details={"symbol": normalized, "status": "success"},
                )
                return True
            else:
                print(f"❌ Model training failed for {normalized}")
                log_component_event(
                    "TRAINING",
                    "Symbol training failed",
                    level=logging.ERROR,
                    details={"symbol": normalized, "status": "failed"},
                )
                return False

        log_component_debug(
            "TRAINING",
            "Symbol activated without retraining (model already available)",
            {"symbol": normalized},
        )
        return True

    def predict_professional(self, symbol, market_data):
        """Compatibility method for parallel engine"""
        return self.predict_ultimate(symbol, market_data)

    def train_advanced_model(self, symbol, use_real_data=True):
        """Compatibility method for parallel engine"""
        return self.train_ultimate_model(symbol, use_real_data=use_real_data)

    def predict_shadow_async(self, symbol, market_data):
        """
        Run inference on SHADOW models asynchronously.
        Does NOT block the main thread.
        Does NOT return a signal for execution.
        """
        if not self.shadow_models:
            return

        try:
            from flask import current_app
            # Capture real app object to pass to thread
            app = current_app._get_current_object()
        except:
            app = None

        # Dispatch to background thread (simple fire-and-forget)
        threading.Thread(
            target=self._run_shadow_inference,
            args=(symbol, market_data, app),
            daemon=True
        ).start()

    def _run_shadow_inference(self, symbol, market_data, app=None):
        """Actual shadow inference logic running in background thread."""
        # Use context manager for app context if available
        context_manager = app.app_context() if app else None
        
        try:
            if context_manager:
                context_manager.push()

             # Imports inside thread to avoid circular deps
            from app.services.shadow_service import ShadowService
            from datetime import datetime
            import warnings
            from sklearn.exceptions import DataConversionWarning
            
            symbol_shadows = self.shadow_models.get(symbol, {})
            if not symbol_shadows:
                return

            # Helper to normalize signal
            def _get_side(pred_val):
                if pred_val > 0: return "LONG"
                if pred_val < 0: return "SHORT"
                return "FLAT"

            for version, model_info in symbol_shadows.items():
                try:
                    model = model_info.get("ensemble_model")
                    feature_cols = model_info.get("feature_cols", [])
                    if not model: continue

                    # Create features
                    features = self.create_ultimate_feature_vector(
                       market_data, feature_cols, symbol=symbol
                    )
                    if not features: continue
                    
                    with warnings.catch_warnings():
                       warnings.filterwarnings("ignore", category=UserWarning)
                       warnings.filterwarnings("ignore", category=DataConversionWarning)
                       
                       proba = max(model.predict_proba([features])[0])
                       prediction = model.predict([features])[0]
                   
                    side = _get_side(prediction)
                    price = float(market_data.get("close") or 0)
                    
                    ShadowService.record_prediction(
                        timestamp=datetime.utcnow(),
                        symbol=symbol,
                        model_version=version,
                        signal=side,
                        confidence=proba,
                        price=price
                    )
                except Exception:
                    # Granular per-model failure swallow
                    continue

        except Exception as e:
             logging.getLogger("training_system").error(f"Shadow inference failed for {symbol}: {e}")
        finally:
            if context_manager:
                context_manager.pop()


    # NEW: CRT Module Integration
    def generate_crt_signals(self, symbol, market_data, historical_prices):
        """Generate CRT signals for symbol"""
        if not self.is_indicator_enabled("CRT"):
            return {
                "signal": "DISABLED",
                "confidence": 0,
                "timestamp": datetime.now().isoformat(),
                "components": {},
            }
        return self.crt_generator.generate_crt_signals(
            symbol, market_data, historical_prices
        )

    def get_crt_dashboard_data(self, symbol=None):
        """Get CRT data for dashboard"""
        return self.crt_generator.get_crt_dashboard_data(symbol)

    def generate_ict_signals(self, symbol, market_data, historical_prices):
        if not self.is_indicator_enabled("ICT"):
            return {}
        return self.ict_module.generate_signals(symbol, market_data, historical_prices)

    def generate_smc_signals(self, symbol, market_data, historical_prices):
        if not self.is_indicator_enabled("SMC"):
            return {}
        return self.smc_module.generate_signals(symbol, market_data, historical_prices)

    def is_indicator_enabled(self, indicator):
        return is_indicator_enabled(self.profile_key, indicator)

    def create_ultimate_features(self, df):
        """Create feature set using optimized core indicators."""
        try:
            indicator_count = len(BEST_INDICATORS)
            self.log_training(
                "SYSTEM",
                f"🛠️ Creating {indicator_count} core technical indicators...",
                70,
            )

            if df is None or df.empty:
                self.log_training(
                    "SYSTEM", "❌ No market data available for feature creation", 0
                )
                return pd.DataFrame()

            df = df.copy()
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            index = df.index
            zero_series = pd.Series(0.0, index=index)
            one_series = pd.Series(1.0, index=index)

            close = df["close"] if "close" in df.columns else zero_series.copy()
            high = df["high"] if "high" in df.columns else close
            low = df["low"] if "low" in df.columns else close
            open_price = df["open"] if "open" in df.columns else close
            volume = df["volume"] if "volume" in df.columns else one_series.copy()

            close = close.astype(float).ffill().bfill().fillna(0)
            high = high.astype(float).fillna(close)
            low = low.astype(float).fillna(close)
            open_price = open_price.astype(float).fillna(close)
            volume = volume.astype(float).ffill().bfill().fillna(0)

            features = pd.DataFrame(index=index)

            previous_close = close.shift(1).replace(0, np.nan)
            features["price_change"] = (
                close.pct_change().replace([np.inf, -np.inf], 0).fillna(0)
            )
            features["price_momentum"] = (close - close.shift(5)).fillna(0)
            features["log_return"] = (
                np.log(close / previous_close).replace([np.inf, -np.inf], 0).fillna(0)
            )
            features["price_volatility"] = (
                close.rolling(5, min_periods=1).std().fillna(0)
            )

            rolling_mean_20 = close.rolling(20, min_periods=1).mean()
            rolling_std_20 = close.rolling(20, min_periods=1).std().replace(0, np.nan)
            features["price_zscore"] = (
                ((close - rolling_mean_20) / rolling_std_20)
                .replace([np.inf, -np.inf], 0)
                .fillna(0)
            )

            high_10 = high.rolling(10, min_periods=1).max()
            low_10 = low.rolling(10, min_periods=1).min()
            price_range_10 = (high_10 - low_10).replace(0, np.nan)
            price_change_10 = (close - close.shift(10)).abs()
            features["efficiency_ratio"] = (
                (price_change_10 / price_range_10)
                .replace([np.inf, -np.inf], 0)
                .fillna(0)
            )

            try:
                atr_values = talib.ATR(
                    high.values, low.values, close.values, timeperiod=14
                )
                features["average_true_range"] = pd.Series(
                    atr_values, index=index
                ).fillna(0)
            except Exception:
                true_range = (high - low).abs()
                features["average_true_range"] = (
                    true_range.rolling(14, min_periods=1).mean().fillna(0)
                )

            features["volume_change"] = (
                volume.pct_change().replace([np.inf, -np.inf], 0).fillna(0)
            )
            volume_mean_20 = volume.rolling(20, min_periods=1).mean().replace(0, np.nan)
            features["volume_ratio"] = (
                (volume / volume_mean_20).replace([np.inf, -np.inf], 0).fillna(0)
            )

            try:
                obv_values = talib.OBV(close.values, volume.values)
                features["volume_obv"] = pd.Series(obv_values, index=index).fillna(0)
            except Exception:
                price_direction = np.sign(close.diff().fillna(0))
                features["volume_obv"] = (volume * price_direction).cumsum().fillna(0)

            try:
                rsi_values = talib.RSI(close.values, timeperiod=14)
                features["rsi_14"] = pd.Series(rsi_values, index=index).fillna(50)
            except Exception:
                features["rsi_14"] = (
                    close.rolling(14, min_periods=1)
                    .apply(
                        lambda x: 50 + 50 * np.sign(x[-1] - x[0]) if len(x) > 1 else 50
                    )
                    .fillna(50)
                )

            try:
                _, _, macd_hist = talib.MACD(close.values)
                features["macd_hist"] = pd.Series(macd_hist, index=index).fillna(0)
            except Exception:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                features["macd_hist"] = (ema12 - ema26).fillna(0)

            try:
                bb_upper, _, bb_lower = talib.BBANDS(
                    close.values, timeperiod=20, nbdevup=2, nbdevdn=2
                )
                bb_upper = pd.Series(bb_upper, index=index)
                bb_lower = pd.Series(bb_lower, index=index)
                band_range = (bb_upper - bb_lower).replace(0, np.nan)
                features["bb_percent_b"] = (
                    ((close - bb_lower) / band_range)
                    .replace([np.inf, -np.inf], 0.5)
                    .fillna(0.5)
                    .clip(0, 1)
                )
            except Exception:
                rolling_std = close.rolling(20, min_periods=1).std().replace(0, np.nan)
                lower_band = rolling_mean_20 - (2 * rolling_std)
                band_range = (2 * rolling_std).replace(0, np.nan)
                features["bb_percent_b"] = (
                    ((close - lower_band) / band_range)
                    .replace([np.inf, -np.inf], 0.5)
                    .fillna(0.5)
                    .clip(0, 1)
                )

            sma_20 = close.rolling(20, min_periods=1).mean().fillna(close)
            sma_50 = close.rolling(50, min_periods=1).mean().fillna(close)
            features["sma_20"] = sma_20
            features["sma_ratio_20_50"] = (
                (sma_20 / sma_50.replace(0, np.nan))
                .replace([np.inf, -np.inf], 1)
                .fillna(1)
            )

            try:
                ema_12_vals = talib.EMA(close.values, timeperiod=12)
                ema_26_vals = talib.EMA(close.values, timeperiod=26)
                ema_12 = pd.Series(ema_12_vals, index=index).fillna(close)
                ema_26 = pd.Series(ema_26_vals, index=index).fillna(close)
            except Exception:
                ema_12 = close.ewm(span=12, adjust=False).mean().fillna(close)
                ema_26 = close.ewm(span=26, adjust=False).mean().fillna(close)

            features["ema_12"] = ema_12
            features["ema_26"] = ema_26
            features["ema_cross_12_26"] = (ema_12 > ema_26).astype(int)

            try:
                adx_values = talib.ADX(
                    high.values, low.values, close.values, timeperiod=14
                )
                features["adx"] = pd.Series(adx_values, index=index).fillna(25)
            except Exception:
                trending = close.diff().abs().rolling(14, min_periods=1).mean()
                features["adx"] = trending.replace([np.inf, -np.inf], 0).fillna(25)

            try:
                mfi_values = talib.MFI(
                    high.values, low.values, close.values, volume.values, timeperiod=14
                )
                features["mfi"] = pd.Series(mfi_values, index=index).fillna(50)
            except Exception:
                typical_price = (high + low + close) / 3
                money_flow = typical_price * volume
                positive_flow = (
                    money_flow.where(typical_price.diff() > 0, 0)
                    .rolling(14, min_periods=1)
                    .sum()
                )
                negative_flow = (
                    money_flow.where(typical_price.diff() <= 0, 0)
                    .rolling(14, min_periods=1)
                    .sum()
                )
                money_ratio = positive_flow / negative_flow.replace(0, np.nan)
                features["mfi"] = (
                    (100 - 100 / (1 + money_ratio))
                    .replace([np.inf, -np.inf], 50)
                    .fillna(50)
                )

            try:
                slowk, _ = talib.STOCH(high.values, low.values, close.values)
                features["stoch_k"] = pd.Series(slowk, index=index).fillna(50)
            except Exception:
                features["stoch_k"] = pd.Series(50, index=index)

            try:
                cci_values = talib.CCI(
                    high.values, low.values, close.values, timeperiod=20
                )
                features["cci"] = pd.Series(cci_values, index=index).fillna(0)
            except Exception:
                typical_price = (high + low + close) / 3
                mean_dev = typical_price.rolling(20, min_periods=1).apply(
                    lambda x: np.mean(np.abs(x - np.mean(x))) if len(x) > 0 else 0
                )
                features["cci"] = (
                    (
                        (
                            typical_price
                            - typical_price.rolling(20, min_periods=1).mean()
                        )
                        / (0.015 * mean_dev.replace(0, np.nan))
                    )
                    .replace([np.inf, -np.inf], 0)
                    .fillna(0)
                )

            # Olivier Seban's SuperTrend indicator (period=10, multiplier=3) for trend confirmation
            try:
                atr_st = talib.ATR(high.values, low.values, close.values, timeperiod=10)
                atr_supertrend = pd.Series(atr_st, index=index)
            except Exception:
                atr_supertrend = pd.Series(
                    _fallback_atr(high.values, low.values, close.values, timeperiod=10),
                    index=index,
                )

            atr_supertrend = atr_supertrend.ffill().bfill().fillna(0)
            hl2 = (high + low) / 2.0
            multiplier = 3.0
            basic_upper_band = hl2 + multiplier * atr_supertrend
            basic_lower_band = hl2 - multiplier * atr_supertrend

            final_upper_band = basic_upper_band.copy()
            final_lower_band = basic_lower_band.copy()
            supertrend = pd.Series(np.nan, index=index, dtype=float)

            if len(close) > 0:
                final_upper_band.iloc[0] = basic_upper_band.iloc[0]
                final_lower_band.iloc[0] = basic_lower_band.iloc[0]
                supertrend.iloc[0] = (
                    final_lower_band.iloc[0]
                    if close.iloc[0] >= final_lower_band.iloc[0]
                    else final_upper_band.iloc[0]
                )

                for i in range(1, len(close)):
                    prev_close = close.iloc[i - 1]
                    prev_final_upper = final_upper_band.iloc[i - 1]
                    prev_final_lower = final_lower_band.iloc[i - 1]

                    upper_candidate = basic_upper_band.iloc[i]
                    if (
                        upper_candidate < prev_final_upper
                        or prev_close > prev_final_upper
                    ):
                        final_upper_band.iloc[i] = upper_candidate
                    else:
                        final_upper_band.iloc[i] = prev_final_upper

                    lower_candidate = basic_lower_band.iloc[i]
                    if (
                        lower_candidate > prev_final_lower
                        or prev_close < prev_final_lower
                    ):
                        final_lower_band.iloc[i] = lower_candidate
                    else:
                        final_lower_band.iloc[i] = prev_final_lower

                    if supertrend.iloc[i - 1] == prev_final_upper:
                        if close.iloc[i] <= final_upper_band.iloc[i]:
                            supertrend.iloc[i] = final_upper_band.iloc[i]
                        else:
                            supertrend.iloc[i] = final_lower_band.iloc[i]
                    else:
                        if close.iloc[i] >= final_lower_band.iloc[i]:
                            supertrend.iloc[i] = final_lower_band.iloc[i]
                        else:
                            supertrend.iloc[i] = final_upper_band.iloc[i]

            supertrend = supertrend.ffill().bfill().fillna(close)
            features["supertrend_value"] = supertrend
            close_safe = close.replace(0, np.nan)
            features["supertrend_distance"] = (
                ((close - supertrend) / close_safe)
                .replace([np.inf, -np.inf], 0)
                .fillna(0)
            )
            supertrend_signal = pd.Series(
                np.where(close >= supertrend, 1, -1), index=index
            )
            features["supertrend_signal"] = supertrend_signal.fillna(0).astype(int)

            if getattr(self, "qfm_engine", None):
                qfm_training_features = self.qfm_engine.compute_training_features(df)
                if (
                    isinstance(qfm_training_features, pd.DataFrame)
                    and not qfm_training_features.empty
                ):
                    features = pd.concat([features, qfm_training_features], axis=1)

            if TRADING_CONFIG.get("futures_enabled", False):
                features = self._add_futures_features(features, df)

            if self.is_indicator_enabled("ICT"):
                ict_features = self.ict_module.compute_features(df)
                if not ict_features.empty:
                    features = pd.concat([features, ict_features], axis=1)

            if self.is_indicator_enabled("SMC"):
                smc_features = self.smc_module.compute_features(df)
                if not smc_features.empty:
                    features = pd.concat([features, smc_features], axis=1)

            features = features.loc[:, ~features.columns.duplicated(keep="last")]
            for indicator in BEST_INDICATORS:
                if indicator not in features.columns:
                    features[indicator] = 0

            features = features.replace([np.inf, -np.inf], 0).fillna(0)

            targets = pd.DataFrame(index=index)
            if "close" in df.columns:
                close_safe = close.replace(0, np.nan)
                future_return_1 = close.shift(-1).divide(close_safe) - 1
                future_return_5 = close.shift(-5).divide(close_safe) - 1
                future_return_1 = future_return_1.replace([np.inf, -np.inf], 0).fillna(
                    0
                )
                future_return_5 = future_return_5.replace([np.inf, -np.inf], 0).fillna(
                    0
                )

                conditions_1 = [
                    future_return_1 > 0.015,
                    future_return_1 > 0.005,
                    future_return_1 < -0.015,
                    future_return_1 < -0.005,
                ]
                choices_1 = [2, 1, -2, -1]
                conditions_5 = [
                    future_return_5 > 0.04,
                    future_return_5 > 0.012,
                    future_return_5 < -0.04,
                    future_return_5 < -0.012,
                ]
                choices_5 = [2, 1, -2, -1]

                targets["target_1"] = np.select(conditions_1, choices_1, default=0)
                targets["target_5"] = np.select(conditions_5, choices_5, default=0)
                targets["target"] = (
                    (targets["target_1"] * 0.3 + targets["target_5"] * 0.7)
                    .round()
                    .astype(int)
                )
            else:
                targets["target_1"] = zero_series
                targets["target_5"] = zero_series
                targets["target"] = zero_series.astype(int)

            targets = targets.fillna(0)

            result = pd.concat([features, targets], axis=1)
            self.log_training(
                "SYSTEM",
                f"✅ Core indicators created. Features: {len(features.columns)}, Records: {len(result)}",
                80,
            )
            return result

        except Exception as e:
            self.log_training("SYSTEM", f"❌ Core feature creation error: {e}", 0)
            import traceback

            self.log_training("SYSTEM", f"❌ Traceback: {traceback.format_exc()}", 0)
            return self.create_features_basic(df)

    def create_features_basic(self, df):
        """Basic feature creation as fallback"""
        try:
            if "close" in df.columns:
                df["price_change"] = df["close"].pct_change().fillna(0)
                df["price_momentum"] = (df["close"] - df["close"].shift(3)).fillna(0)
                df["target"] = (
                    (df["close"].shift(-1) > df["close"]).astype(int).fillna(0)
                )
            return df.dropna()
        except Exception as e:
            self.log_training("SYSTEM", f"❌ Basic feature creation error: {e}", 0)
            return pd.DataFrame()

    def train_all_ultimate_models(self, symbols=None, use_real_data=True):
        """Train ultimate models for all symbols with optional parallel processing"""
        if symbols is None:
            symbols = get_active_trading_universe()

        self.log_training(
            "SYSTEM",
            f"🚀 Training {len(symbols)} ULTIMATE models with parallel processing...",
            0,
        )

        if TRADING_CONFIG["parallel_processing"]:
            success_count = self.parallel_engine.parallel_train_models(
                symbols, self, use_real_data
            )
        else:
            success_count = 0
            for symbol in symbols:
                self.log_training(symbol, "Starting ultimate training...", 0)
                success = self.train_ultimate_model(symbol, use_real_data=use_real_data)
                if success:
                    success_count += 1
                    self.log_training(
                        symbol, "✅ Ultimate training completed successfully", 100
                    )
                else:
                    self.log_training(symbol, "❌ Ultimate training failed", 0)
                time.sleep(3)

        self.log_training(
            "SYSTEM",
            f"✅ Ultimate training completed: {success_count}/{len(symbols)} models trained",
            100,
        )
        return success_count

    def train_ultimate_model(self, symbol, data=None, use_real_data=True, output_path=None, timeframe="1h", lookback_days=365):
        """Train ultimate model with parallel processing and ensemble - BUG FIXED VERSION"""
        try:
            self.log_training(symbol, "🚀 Starting ULTIMATE model training...", 5)
            self.log_training(symbol, f"Params: timeframe={timeframe}, lookback={lookback_days}d", 5)

            # Get data if not provided
            if data is None:
                if use_real_data:
                    # Convert lookback days to years for the existing API
                    years = max(1, lookback_days / 365.0)
                    data = self.get_real_historical_data(symbol, years=years, interval=timeframe)
                else:
                    data = self.generate_fallback_data(symbol, years=2)

            log_component_debug(
                "TRAINING",
                "Historical dataset prepared",
                {
                    "symbol": symbol,
                    "records": len(data) if data is not None else 0,
                    "use_real_data": bool(use_real_data),
                    "timeframe": timeframe
                },
            )

            if len(data) < 100:
                self.log_training(
                    symbol, f"❌ Not enough data (only {len(data)} records)", 0
                )
                return False

            # Create ultimate features
            df = self.create_ultimate_features(data)
            if df.empty or "target" not in df.columns:
                self.log_training(symbol, "❌ No target variable created", 0)
                return False

            # Select features for training - FIXED: More robust feature selection
            exclude_cols = [
                "date",
                "target",
                "target_1",
                "target_5",
                "timestamp",
                "open_time",
                "close_time",
            ]
            feature_cols = [
                col
                for col in df.columns
                if col not in exclude_cols
                and not col.startswith("future_")
                and not col.startswith("ignore")
            ]

            # Ensure we have numeric features only
            numeric_features = []
            for col in feature_cols:
                try:
                    pd.to_numeric(df[col])
                    numeric_features.append(col)
                except Exception:
                    self.log_training(
                        symbol, f"⚠️ Skipping non-numeric feature: {col}", 0
                    )

            feature_cols = numeric_features

            prioritized_features = [
                col for col in BEST_INDICATORS if col in feature_cols
            ]
            fallback_features = [
                col for col in feature_cols if col not in prioritized_features
            ]
            feature_cols = prioritized_features + fallback_features

            if len(feature_cols) < 10:  # Reduced threshold for basic features
                self.log_training(
                    symbol, f"❌ Not enough features available ({len(feature_cols)})", 0
                )
                return False

            log_component_debug(
                "TRAINING",
                "Feature set prepared",
                {"symbol": symbol, "feature_count": len(feature_cols)},
            )

            X = df[feature_cols]
            y = df["target"]

            # Time series split
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            if len(X_train) == 0:
                self.log_training(symbol, "❌ No training data after split", 0)
                return False

            self.log_training(
                symbol,
                f"📊 Training on {len(X_train)} samples with {len(feature_cols)} features",
                85,
            )

            # Create enhanced ensemble of models with error handling
            models = {}

            try:
                models["random_forest"] = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=15,
                    random_state=42,
                    min_samples_split=5,
                    n_jobs=-1,  # Use all cores
                )
            except Exception:
                models["random_forest"] = RandomForestClassifier(
                    n_estimators=50, random_state=42
                )

            try:
                models["gradient_boosting"] = GradientBoostingClassifier(
                    n_estimators=80, max_depth=8, random_state=42
                )
            except Exception:
                models["gradient_boosting"] = GradientBoostingClassifier(
                    n_estimators=50, random_state=42
                )

            try:
                models["logistic"] = LogisticRegression(
                    random_state=42, max_iter=500, n_jobs=-1, multi_class='ovr'
                )
            except Exception:
                models["logistic"] = LogisticRegression(random_state=42, max_iter=200, multi_class='ovr')

            try:
                models["svc"] = SVC(probability=True, random_state=42, kernel="rbf")
            except Exception:
                models["svc"] = SVC(probability=True, random_state=42, kernel="linear")

            # Train individual models with error handling
            trained_models = {}
            model_performances = {}

            for name, model in models.items():
                try:
                    model.fit(X_train, y_train)
                    score = model.score(X_test, y_test)
                    trained_models[name] = model
                    model_performances[name] = score
                    self.log_training(symbol, f"   {name}: {score:.4f}", 90)
                except Exception as e:
                    self.log_training(symbol, f"❌ {name} training failed: {e}", 0)

            if not trained_models:
                self.log_training(symbol, "❌ All models failed to train", 0)
                return False

            # Create weighted voting classifier
            try:
                voting_clf = VotingClassifier(
                    estimators=[
                        (name, model) for name, model in trained_models.items()
                    ],
                    voting="soft",
                    weights=[
                        model_performances[name] for name in trained_models.keys()
                    ],
                )

                voting_clf.fit(X_train, y_train)
                ensemble_score = voting_clf.score(X_test, y_test)
            except Exception as e:
                self.log_training(symbol, f"❌ Ensemble creation failed: {e}", 0)
                # Fallback to best individual model
                best_model_name = max(
                    model_performances, key=lambda x: model_performances[x]
                )
                voting_clf = trained_models[best_model_name]
                ensemble_score = model_performances[best_model_name]

            # Feature importance from best model
            feature_importance = {}
            if hasattr(voting_clf, "feature_importances_"):
                feature_importance = dict(
                    zip(feature_cols, voting_clf.feature_importances_)  # type: ignore
                )
            else:
                # Equal importance if not available
                feature_importance = {
                    col: 1.0 / len(feature_cols) for col in feature_cols
                }

            # Calculate Risk Metrics (Drawdown, PF) from Test Predictions
            try:
                test_predictions = voting_clf.predict(X_test)
                # Need corresponding prices. df index should align if reset_index(drop=True) was used on df creation from binance data.
                # In create_ultimate_features, we return a DF with index.
                # We need to map X_test index back to df prices.
                test_indices = X_test.index
                test_prices = data.loc[test_indices, "close"]
                
                risk_metrics = self._calculate_risk_metrics(test_predictions, test_prices)
                self.log_training(symbol, f"📉 Risk Profile: DD={risk_metrics.get('max_drawdown')}% PF={risk_metrics.get('profit_factor')}", 95)
            except Exception as e:
                 self.log_training(symbol, f"⚠️ Risk calc failed: {e}", 95)
                 risk_metrics = {}

            # Save ultimate model (Latest)
            if output_path:
                model_path = output_path
            else:
                model_path = os.path.join(self.models_dir, f"{symbol}_ultimate_model.pkl")
            
            model_data = {
                "ensemble_model": voting_clf,
                "individual_models": trained_models,
                "model_performances": model_performances,
                "ensemble_accuracy": ensemble_score,
                "risk_metrics": risk_metrics, # NEW
                "feature_cols": feature_cols,
                "symbol": symbol,
                "feature_importance": feature_importance,
                "training_date": datetime.now().isoformat(),
                "data_points": len(X),
                "feature_count": len(feature_cols),
                "data_source": "BINANCE_REAL" if use_real_data else "SYNTHETIC",
                "model_type": "ULTIMATE_ENSEMBLE",
                "target_classes": "ENHANCED_MULTI_CLASS",
                "version": f"v{int(datetime.now().timestamp())}"
            }

            joblib.dump(model_data, model_path)
            
            # Save Versioned Copy (Minimal Model Versioning)
            try:
                timestamp = int(datetime.now().timestamp())
                version_filename = f"{symbol}_ultimate_model_v{timestamp}.pkl"
                version_path = os.path.join(self.models_dir, version_filename)
                joblib.dump(model_data, version_path)
                self.log_training(symbol, f"Saved model version: {version_filename}", 100)
            except Exception as e:
                self.log_training(symbol, f"⚠️ Failed to save versioned model: {e}", 100)

            self.models[symbol] = model_data
            self._save_training_metrics(
                symbol,
                ensemble_score,
                feature_cols,
                feature_importance,
                model_performances,
                risk_metrics=risk_metrics
            )

            self._print_feature_importance(symbol, feature_importance)

            self.log_training(
                symbol,
                f"✅ ULTIMATE Model trained - Accuracy: {ensemble_score:.4f} - Features: {len(feature_cols)}",
                100,
            )
            log_component_event(
                "TRAINING",
                "Ultimate model persisted",
                level=logging.INFO,
                details={
                    "symbol": symbol,
                    "accuracy": round(float(ensemble_score), 4)
                    if isinstance(ensemble_score, (int, float))
                    else None,
                    "feature_count": len(feature_cols),
                    "data_points": len(X),
                },
            )
            return True

        except Exception as e:
            self.log_training(symbol, f"❌ Ultimate training failed: {e}", 0)
            import traceback

            self.log_training(symbol, f"❌ Traceback: {traceback.format_exc()}", 0)
            logging.exception("Ultimate training failed for symbol %s", symbol)
            return False

    # ==================== CONTINUOUS TRAINING CYCLE - RESTORED FEATURE ====================
    def start_continuous_training_cycle(self):
        """Continuous training cycle - RESTORED FEATURE"""
        if self._training_cycle_active:
            print("🔄 Continuous training cycle already active")
            log_component_event(
                "TRAINING",
                "Continuous training cycle already active",
                level=logging.WARNING,
                details={"profile_key": self.profile_key},
            )
            return

        self._training_cycle_active = True
        log_component_event(
            "TRAINING",
            "Continuous training cycle activated",
            level=logging.INFO,
            details={"profile_key": self.profile_key},
        )

        def training_loop():
            cycle_count = 0
            while self._training_cycle_active:
                try:
                    cycle_count += 1
                    print(f"\n🔄 Continuous Training Cycle #{cycle_count} starting...")
                    log_component_event(
                        "TRAINING",
                        "Continuous training cycle iteration starting",
                        level=logging.INFO,
                        details={"cycle": cycle_count},
                    )

                    # Wait 6 hours between cycles
                    for i in range(6 * 60):  # 6 hours in minutes
                        if not self._training_cycle_active:
                            break
                        time.sleep(60)  # Sleep 1 minute at a time

                    if not self._training_cycle_active:
                        break

                    if self.models:
                        print("🔄 Starting continuous training cycle...")
                        log_component_debug(
                            "TRAINING",
                            "Evaluating models for continuous retraining",
                            {"cycle": cycle_count, "model_count": len(self.models)},
                        )

                        # Retrain underperforming models
                        poor_models = self.identify_underperforming_models()
                        if poor_models:
                            print(
                                f"🔄 Retraining {len(poor_models)} underperforming models..."
                            )
                            log_component_event(
                                "TRAINING",
                                "Retraining underperforming models",
                                level=logging.INFO,
                                details={
                                    "cycle": cycle_count,
                                    "model_count": len(poor_models),
                                },
                            )
                            for symbol in poor_models[:3]:  # Limit to 3 at a time
                                if not self._training_cycle_active:
                                    break
                                self.log_training(
                                    symbol, "🔄 Continuous cycle retraining", 0
                                )
                                self.train_ultimate_model(symbol, use_real_data=True)
                                time.sleep(60)  # 1 minute between trainings

                        # Update ensemble
                        if not self._training_cycle_active:
                            break

                        self.ensemble_system.periodic_ensemble_rebuilding(
                            self.get_historical_predictions(),
                            self.get_actual_movements(),
                        )

                        print(f"✅ Continuous training cycle #{cycle_count} completed")
                        log_component_event(
                            "TRAINING",
                            "Continuous training cycle completed",
                            level=logging.INFO,
                            details={"cycle": cycle_count},
                        )

                except Exception as e:
                    print(f"❌ Continuous training error: {e}")
                    import traceback

                    print(f"❌ Traceback: {traceback.format_exc()}")
                    log_component_event(
                        "TRAINING",
                        f"Continuous training error: {e}",
                        level=logging.ERROR,
                    )
                    logging.exception(
                        "Continuous training error on cycle %s", cycle_count
                    )

        threading.Thread(target=training_loop, daemon=True).start()
        print("✅ Continuous training cycle started! (Runs every 6 hours)")
        log_component_event(
            "TRAINING",
            "Continuous training cycle thread started",
            level=logging.INFO,
            details={"interval_hours": 6, "profile_key": self.profile_key},
        )

    def stop_continuous_training_cycle(self):
        """Stop continuous training cycle"""
        self._training_cycle_active = False
        print("🛑 Continuous training cycle stopped")
        log_component_event(
            "TRAINING",
            "Continuous training cycle stopped",
            level=logging.INFO,
            details={"profile_key": self.profile_key},
        )

    def identify_underperforming_models(self, threshold=0.65):
        """Identify models needing retraining - RESTORED FEATURE"""
        poor_models = []
        for symbol, model_info in self.models.items():
            accuracy = model_info.get("ensemble_accuracy", 0)
            if accuracy < threshold:
                poor_models.append((symbol, accuracy))

        # Sort by worst performance first
        poor_models.sort(key=lambda x: x[1])
        return [symbol for symbol, acc in poor_models]

    def get_historical_predictions(self):
        """Get historical predictions for ensemble rebuilding"""
        # This would be implemented to return historical prediction data
        # For now, return empty dict as placeholder
        return {}

    def get_actual_movements(self):
        """Get actual price movements for ensemble rebuilding"""
        # This would be implemented to return actual price movement data
        # For now, return empty list as placeholder
        return []

    def add_symbol_with_retrain(self, symbol):
        """Add symbol with immediate training - RESTORED FEATURE"""
        normalized = _normalize_symbol(symbol)
        if not normalized:
            return False

        result = self.add_symbol(normalized, train_immediately=True)
        if result:
            print(f"✅ Symbol {normalized} ready for trading")
        return result

    def remove_symbol(self, symbol, *, permanent=False):
        """Disable a symbol from trading or permanently purge its resources."""
        normalized = _normalize_symbol(symbol)
        if not normalized:
            return False

        if not permanent:
            disable_symbol(normalized)
            refresh_symbol_counters()
            # Clear short-lived caches but keep trained models on disk/memory for fast reactivation
            self.training_progress.pop(normalized, None)
            self._futures_feature_cache.pop(normalized, None)
            self._ict_feature_cache.pop(normalized, None)
            self._smc_feature_cache.pop(normalized, None)
            log_component_event(
                "TRAINING",
                "Symbol disabled for trading",
                level=logging.INFO,
                details={"symbol": normalized},
            )
            print(
                f"🚫 Symbol {normalized} disabled from active trading (models preserved)"
            )
            return True

        removed = False

        with SYMBOL_STATE_LOCK:
            if normalized in TOP_SYMBOLS:
                try:
                    TOP_SYMBOLS.remove(normalized)
                    removed = True
                except ValueError:
                    pass
            if normalized in DISABLED_SYMBOLS:
                DISABLED_SYMBOLS.discard(normalized)
                removed = True

        self.training_progress.pop(normalized, None)
        self.model_performance_history.pop(normalized, None)
        self._futures_feature_cache.pop(normalized, None)
        self._ict_feature_cache.pop(normalized, None)
        self._smc_feature_cache.pop(normalized, None)

        if self.models.pop(normalized, None) is not None:
            removed = True

        model_path = os.path.join(self.models_dir, f"{normalized}_ultimate_model.pkl")
        if os.path.exists(model_path):
            try:
                os.remove(model_path)
                removed = True
            except OSError:
                pass

        metrics_file = os.path.join(self.models_dir, "ultimate_training_metrics.json")
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, "r") as f:
                    payload = json.load(f)
                if isinstance(payload, list):
                    filtered = [
                        entry for entry in payload if entry.get("symbol") != normalized
                    ]
                    if len(filtered) != len(payload):
                        removed = True
                        fd, temp_path = tempfile.mkstemp(
                            dir=self.models_dir, prefix="metrics_", suffix=".json"
                        )
                        try:
                            with os.fdopen(fd, "w") as temp_file:
                                json.dump(filtered, temp_file, indent=2)
                            os.replace(temp_path, metrics_file)
                        except Exception as exc:
                            try:
                                os.unlink(temp_path)
                            except OSError:
                                pass
                            log_component_debug(
                                "TRAINING",
                                "Metrics file cleanup failed",
                                {"symbol": normalized, "error": str(exc)},
                            )
            except json.JSONDecodeError:
                pass
            except Exception as exc:
                log_component_debug(
                    "TRAINING",
                    "Metrics removal failed",
                    {"symbol": normalized, "error": str(exc)},
                )

        save_symbol_state()
        refresh_symbol_counters()

        return removed

    # Keep existing methods but enhance with parallel processing
    def get_real_historical_data(self, symbol, years=1, interval="1d"):
        """Get real historical data from Binance - ENHANCED WITH TIMESCALEDB"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)

            # First, try to get data from TimescaleDB
            if (
                getattr(self, "timescaledb_service", None) is not None
                and self.timescaledb_service.is_available()
            ):
                cached_data = self.timescaledb_service.get_candles(
                    symbol, interval, start_date, end_date
                )
                if cached_data is not None and not cached_data.empty:
                    # Check if we have enough data
                    expected_candles = self._estimate_candle_count(years, interval)
                    if (
                        len(cached_data) >= expected_candles * 0.8
                    ):  # 80% of expected data
                        self.log_training(
                            symbol,
                            f"📊 Retrieved {len(cached_data)} candles from TimescaleDB cache",
                            80,
                        )
                        return cached_data

                    # If we have some data but not enough, get the latest timestamp
                    # and only fetch newer data from API
                    latest_time = self.timescaledb_service.get_latest_candle_time(  # type: ignore
                        symbol, interval
                    )
                    if latest_time:
                        start_date = latest_time
                        self.log_training(
                            symbol,
                            f"📊 Found {len(cached_data)} cached candles, fetching from {latest_time}...",
                            20,
                        )

            self.log_training(
                symbol,
                f"📊 Fetching {years} years of {interval} data from Binance...",
                10,
            )

            # Fetch from Binance API
            all_data = self._fetch_binance_data(symbol, interval, start_date, end_date)

            if not all_data:
                self.log_training(symbol, "❌ No data received from Binance", 0)
                return self.generate_fallback_data(symbol, years)

            # Convert to DataFrame
            df = self._convert_binance_to_dataframe(all_data)

            # Store in TimescaleDB for future use
            if (
                getattr(self, "timescaledb_service", None) is not None
                and self.timescaledb_service.is_available()
            ):
                stored_count = self.timescaledb_service.store_historical_data(
                    symbol, interval, df
                )
                if stored_count > 0:
                    self.log_training(
                        symbol,
                        f"💾 Stored {stored_count} candles in TimescaleDB",
                        90,
                    )

            self.log_training(symbol, f"✅ Successfully loaded {len(df)} records", 100)
            return df

        except Exception as e:
            self.log_training(symbol, f"❌ Historical data error: {e}", 0)
            return self.generate_fallback_data(symbol, years)

    def _estimate_candle_count(self, years, interval):
        """Estimate the number of candles expected for given years and interval."""
        intervals_minutes = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "6h": 360,
            "8h": 480,
            "12h": 720,
            "1d": 1440,
            "3d": 4320,
            "1w": 10080,
            "1M": 43200,
        }
        minutes_per_year = 365 * 24 * 60
        candles_per_year = minutes_per_year / intervals_minutes.get(interval, 1440)
        return int(years * candles_per_year)

    def _fetch_binance_data(self, symbol, interval, start_date, end_date):
        """Fetch historical candle data using CCXT with Authentication and Pagination."""
        try:
            # 1. ATTEMPT TO GET CREDENTIALS
            api_key = None
            api_secret = None
            testnet = False
            
            # Try to get credentials from Flask context (best for Production)
            try:
                from flask import current_app
                ctx = current_app.extensions.get("ai_bot_context")
                if ctx:
                    svc = ctx.get("binance_credential_service")
                    if svc:
                         creds = svc.credentials_store.get_credentials("spot")
                         if creds and creds.get("api_key"):
                             api_key = creds.get("api_key")
                             api_secret = creds.get("api_secret")
                             testnet = creds.get("testnet", False)
                             self.log_training(symbol, "🔑 Retrieved authenticated credentials for data fetch", 2)
            except Exception:
                pass
                
            # Fallback to direct file read if no context (e.g. standalone script)
            if not api_key:
                 try:
                     from app.services.binance import BinanceCredentialStore
                     store = BinanceCredentialStore()
                     creds = store.get_credentials("spot")
                     if creds and creds.get("api_key"):
                         api_key = creds.get("api_key")
                         api_secret = creds.get("api_secret")
                         testnet = creds.get("testnet", False)
                         self.log_training(symbol, "🔑 Retrieved authenticated credentials from store", 2)
                 except Exception:
                     pass

            # 2. INITIALIZE EXCHANGE
            try:
                from app.services.ccxt_adapter import CCXTAdapter
                exchange = CCXTAdapter.get_exchange("binance", api_key, api_secret, testnet=testnet)
            except ImportError:
                 import ccxt
                 exchange = ccxt.binance({'apiKey': api_key, 'secret': api_secret})
                 if testnet: exchange.set_sandbox_mode(True)

            if not exchange:
                raise Exception("Could not initialize exchange driver")

            # 3. PAGINATION LOOP
            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)
            all_ohlcv = []
            
            current_since = start_ts
            limit = 1000  # Binance limit
            
            self.log_training(
                symbol, 
                f"🌍 Fetching data via {exchange.id} ({'Authenticated' if api_key else 'Public'})...", 
                12
            )
            
            while current_since < end_ts:
                # Calculate progress for logs
                progress = 10 + int(90 * (current_since - start_ts) / (end_ts - start_ts + 1))
                # Throttle slightly
                time.sleep(exchange.rateLimit / 1000.0) 
                
                ohlcvs = exchange.fetch_ohlcv(symbol, timeframe=interval, since=current_since, limit=limit)
                
                if not ohlcvs:
                    break
                    
                first_ts = ohlcvs[0][0]
                last_ts = ohlcvs[-1][0]
                
                # Check if we moved forward
                if last_ts <= current_since:
                    break
                    
                # Append data (filter out future data if any)
                valid_batch = [c for c in ohlcvs if c[0] <= end_ts]
                all_ohlcv.extend(valid_batch)
                
                # Update pointer
                current_since = last_ts + 1
                
                # Quick progress update every 5 requests
                if len(all_ohlcv) % 5000 == 0:
                    self.log_training(symbol, f"📊 Fetched {len(all_ohlcv)} candles...", progress)
                
                if len(valid_batch) < len(ohlcvs): 
                    # We reached end_ts inside this batch
                    break

            if hasattr(exchange, 'close'):
                try:
                    exchange.close()  # type: ignore
                except Exception:
                    pass
            
            # Convert to Format expected by _convert_binance_to_dataframe
            # [t, o, h, l, c, v] -> need to match expected input dict or list
            # The existing _convert_binance_to_dataframe expects LIST OF LISTS or LIST OF DICTS
            # Binance raw API returns list of lists:
            # [1499040000000, "0.01634790", "0.80000000", "0.01575800", "0.01577100", "148976.11500000", ...]
            # CCXT return list of lists:
            # [1504541580000, 4235.4, 4240.6, 4230.0, 4230.7, 37.72941911]
            
            # NOTE: CCXT returns floats, Binance raw returns strings.
            # _convert_binance_to_dataframe likely handles both if robust, 
            # but let's check it. If it expects specific indices (0=timestamp, 4=close), it works.
            
            return all_ohlcv

        except Exception as e:
            self.log_training(symbol, f"❌ Data fetch error: {e}", 0)
            return []

    def _convert_binance_to_dataframe(self, all_data):
        """Convert raw Binance/CCXT API data to DataFrame."""
        if not all_data:
            return pd.DataFrame()

        # Check column count to distinguish CCXT (6) from Binance raw (12)
        sample = all_data[0]
        if len(sample) == 6:
            # CCXT Format: [timestamp, open, high, low, close, volume]
            df = pd.DataFrame(
                all_data,
                columns=["open_time", "open", "high", "low", "close", "volume"]
            )
        else:
            # Raw Binance Format (12 columns)
            df = pd.DataFrame(
                all_data,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

        # Convert types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["date"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df.dropna().reset_index(drop=True)

        return df[["date", "open", "high", "low", "close", "volume"]]

    def generate_fallback_data(self, symbol, years=1):
        """Generate realistic fallback data when API fails"""
        self.log_training(symbol, "🔄 Generating realistic fallback data...", 30)

        days = years * 365
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        base_prices = {
            "BTCUSDT": 50000,
            "ETHUSDT": 3000,
            "BNBUSDT": 500,
            "ADAUSDT": 0.5,
            "XRPUSDT": 0.6,
            "SOLUSDT": 100,
            "DOTUSDT": 7,
            "DOGEUSDT": 0.15,
            "AVAXUSDT": 40,
            "MATICUSDT": 0.8,
            "LINKUSDT": 15,
            "LTCUSDT": 80,
            "BCHUSDT": 300,
            "XLMUSDT": 0.12,
            "ETCUSDT": 25,
        }

        base_price = base_prices.get(symbol, 100)
        data = []
        price = base_price
        volume = 1000000

        for i, date in enumerate(dates):
            if i < len(dates) * 0.3:
                change = np.random.normal(0.001, 0.03)
            elif i < len(dates) * 0.6:
                change = np.random.normal(-0.0005, 0.04)
            else:
                change = np.random.normal(0.0002, 0.025)

            price = max(0.01, price * (1 + change))

            volatility = abs(change) * 2
            high = price * (1 + abs(np.random.normal(0, volatility)))
            low = price * (1 - abs(np.random.normal(0, volatility)))
            open_price = price * (1 + np.random.normal(0, volatility * 0.5))

            volume_change = np.random.normal(change * 2, 0.1)
            volume = max(100000, volume * (1 + volume_change))

            data.append(
                {
                    "date": date,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": abs(volume),
                }
            )

        self.log_training(symbol, f"✅ Generated {len(data)} fallback records", 60)
        return pd.DataFrame(data)

    def _calculate_risk_metrics(self, predictions, prices):
        """
        Calculate risk metrics from test set predictions.
        
        Args:
            predictions: Array of signals (-1, 0, 1) or target classes.
                         Assuming target classes: 2=Large Up, 1=Small Up, -1=Small Down, -2=Large Down, 0=Flat
                         We need to map them to directional signals: >0 -> Long, <0 -> Short.
            prices: Series of close prices corresponding to predictions.
        
        Returns:
            dict: {max_drawdown, win_loss_ratio, profit_factor, sharpe_ratio}
        """
        try:
            if len(predictions) != len(prices):
                return {}
            
            # 1. Simulate Trades
            balance = 10000.0
            peak = balance
            equity_curve = [balance]
            trades = []
            
            current_pos = 0 # 0=Flat, 1=Long, -1=Short
            entry_price = 0.0
            
            # Align indices
            price_vals = prices.values
            
            for i in range(len(predictions) - 1):
                raw_pred = predictions[i]
                
                # Map target class to signal
                if raw_pred > 0: signal = 1
                elif raw_pred < 0: signal = -1
                else: signal = 0
                
                curr_price = price_vals[i]
                next_price = price_vals[i+1] # Lookahead for simulation of result
                
                # Simple Strategy: Always flip position to match signal
                if signal != current_pos:
                    # Close existing
                    if current_pos != 0:
                        # PnL logic
                        if current_pos == 1:
                            pnl_pct = (curr_price - entry_price) / entry_price
                        else:
                            pnl_pct = (entry_price - curr_price) / entry_price
                            
                        # Apply fee (approx 0.1%)
                        pnl_pct -= 0.001 
                        
                        pnl_amt = balance * pnl_pct
                        balance += pnl_amt
                        trades.append(pnl_amt)
                        
                    # Open new
                    if signal != 0:
                        current_pos = signal
                        entry_price = curr_price
                
                # Update Equity (Mark to Market)
                if current_pos != 0:
                     if current_pos == 1:
                         unrealized = (next_price - entry_price) / entry_price
                     else:
                         unrealized = (entry_price - next_price) / entry_price
                     equity = balance * (1 + unrealized)
                else:
                     equity = balance
                
                equity_curve.append(equity)
                if equity > peak: peak = equity
            
            # Final Stats
            wins = [t for t in trades if t > 0]
            losses = [t for t in trades if t <= 0]
            
            total_wins = sum(wins)
            total_losses = abs(sum(losses)) if losses else 0.0
            
            profit_factor = round(total_wins / total_losses, 2) if total_losses > 0 else 999.0
            win_rate = len(wins) / len(trades) if trades else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = abs(np.mean(losses)) if losses else 0.0
            win_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0
            
            # Max Drawdown
            equity_series = pd.Series(equity_curve)
            rolling_max = equity_series.cummax()
            drawdown = (equity_series - rolling_max) / rolling_max
            max_drawdown = abs(drawdown.min()) * 100 # In percentage
            
            return {
                "max_drawdown": round(max_drawdown, 2),
                "profit_factor": profit_factor,
                "win_loss_ratio": win_loss_ratio,
                "trade_count": len(trades),
                "simulated_return": round((balance - 10000) / 10000 * 100, 2)
            }
            
        except Exception as e:
            self.log_training("SYSTEM", f"⚠️ Risk calculation error: {e}", 0)
            return {
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "win_loss_ratio": 0.0
            }

    def _save_training_metrics(
        self, symbol, accuracy, features, feature_importance, model_performances=None, risk_metrics=None
    ):
        """Save ultimate training metrics"""
        try:
            metrics = {
                "symbol": symbol,
                "accuracy": accuracy,
                "risk_metrics": risk_metrics or {},
                "features": features,
                "feature_importance": feature_importance,
                "model_performances": model_performances or {},
                "training_date": datetime.now().isoformat(),
                "model_type": "ULTIMATE_ENSEMBLE",
                "total_indicators": len(features),
                "max_indicators": len(BEST_INDICATORS),
            }



            metrics_file = os.path.join(
                self.models_dir, "ultimate_training_metrics.json"
            )
            history_limit = 8
            all_metrics = []
            if os.path.exists(metrics_file):
                try:
                    with open(metrics_file, "r") as f:
                        existing_payload = json.load(f)
                        if isinstance(existing_payload, list):
                            all_metrics = existing_payload
                except json.JSONDecodeError:
                    backup_name = f"ultimate_training_metrics.corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                    backup_path = os.path.join(self.models_dir, backup_name)
                    shutil.move(metrics_file, backup_path)
                    self.log_training(
                        symbol, f"⚠️ Metrics store corrupted; moved to {backup_name}", 0
                    )
                    all_metrics = []

            metrics_by_symbol = defaultdict(list)
            for entry in all_metrics:
                sym_key = entry.get("symbol") or "UNKNOWN"
                metrics_by_symbol[sym_key].append(entry)
            metrics_by_symbol[symbol].append(metrics)

            pruned_metrics = []
            for sym_key, entries in metrics_by_symbol.items():
                entries.sort(
                    key=lambda item: item.get("training_date", ""), reverse=True
                )
                pruned_metrics.extend(entries[:history_limit])

            pruned_metrics.sort(
                key=lambda item: item.get("training_date", ""), reverse=True
            )

            perf_history = self.model_performance_history.setdefault(symbol, [])
            perf_history.append(
                {
                    "timestamp": metrics["training_date"],
                    "accuracy": metrics["accuracy"],
                    "risk": risk_metrics or {},
                    "features_used": len(features),
                    "model_performances": model_performances or {},
                    "total_indicators": metrics["max_indicators"],
                }
            )
            if len(perf_history) > history_limit * 3:
                self.model_performance_history[symbol] = perf_history[
                    -history_limit * 3 :
                ]

            fd, temp_path = tempfile.mkstemp(
                dir=self.models_dir, prefix="metrics_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w") as temp_file:
                    json.dump(pruned_metrics, temp_file, indent=2)
                os.replace(temp_path, metrics_file)
            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            self.log_training(symbol, f"❌ Error saving metrics: {e}", 0)

    def _print_feature_importance(self, symbol, feature_importance):
        """Print feature importance"""
        self.log_training(symbol, "📊 Ultimate Feature Importance Analysis:", 95)
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )
        for feature, importance in sorted_features[:10]:
            self.log_training(symbol, f"   {feature}: {importance:.4f}", 95)

    def _load_metrics_history(self):
        metrics_file = os.path.join(self.models_dir, "ultimate_training_metrics.json")
        if not os.path.exists(metrics_file):
            return []
        try:
            with open(metrics_file, "r") as f:
                payload = json.load(f)
                if isinstance(payload, list):
                    return payload
        except json.JSONDecodeError:
            return []
        except Exception as exc:
            log_component_debug(
                "TRAINING",
                "Metrics history read error",
                {"profile": self.profile_key, "error": str(exc)},
            )
        return []

    def get_ml_telemetry(
        self, *, stale_hours=18, low_accuracy=0.65, history_per_symbol=5
    ):
        metrics_history = self._load_metrics_history()
        metrics_by_symbol = defaultdict(list)
        for entry in metrics_history:
            symbol_key = entry.get("symbol") or "UNKNOWN"
            metrics_by_symbol[symbol_key].append(entry)

        now = datetime.now()
        models_payload = []
        history_payload = []
        accuracies = []
        stale_count = 0
        low_accuracy_count = 0
        latest_dt = None
        oldest_dt = None

        for symbol, entries in metrics_by_symbol.items():
            entries.sort(key=lambda item: item.get("training_date", ""), reverse=True)
            trimmed_entries = entries[: max(1, history_per_symbol)]

            latest_entry = trimmed_entries[0]
            accuracy = float(latest_entry.get("accuracy") or 0.0)
            accuracies.append(accuracy)

            training_date = latest_entry.get("training_date")
            train_dt = safe_parse_datetime(training_date)
            age_hours = None
            if train_dt:
                age_hours = max((now - train_dt).total_seconds() / 3600.0, 0.0)
                if latest_dt is None or train_dt > latest_dt:
                    latest_dt = train_dt
                if oldest_dt is None or train_dt < oldest_dt:
                    oldest_dt = train_dt

            stale_flag = age_hours is not None and age_hours > stale_hours
            low_accuracy_flag = accuracy < low_accuracy
            if stale_flag:
                stale_count += 1
            if low_accuracy_flag:
                low_accuracy_count += 1

            trend_value = None
            if len(trimmed_entries) > 1:
                prev_accuracy = float(trimmed_entries[1].get("accuracy") or 0.0)
                trend_value = accuracy - prev_accuracy

            feature_importance = latest_entry.get("feature_importance") or {}
            top_features = sorted(
                feature_importance.items(), key=lambda item: item[1], reverse=True
            )[:3]
            features = latest_entry.get("features") or []
            max_indicators = latest_entry.get("max_indicators") or len(BEST_INDICATORS)
            feature_ratio = (len(features) / max_indicators) if max_indicators else 0.0
            model_meta = self.models.get(symbol, {})
            data_points = model_meta.get("data_points") or latest_entry.get(
                "data_points"
            )

            models_payload.append(
                {
                    "symbol": symbol,
                    "accuracy": round(accuracy, 6),
                    "accuracy_percent": round(accuracy * 100, 2),
                    "trend": round(trend_value, 6) if trend_value is not None else None,
                    "trend_percent": round(trend_value * 100, 2)
                    if trend_value is not None
                    else None,
                    "features_used": len(features),
                    "feature_ratio": round(feature_ratio, 4),
                    "feature_utilization_percent": round(feature_ratio * 100, 2),
                    "top_features": [
                        {"name": name, "importance": value}
                        for name, value in top_features
                    ],
                    "last_trained": training_date,
                    "age_hours": age_hours,
                    "age_display": _format_duration_hours(age_hours)
                    if age_hours is not None
                    else "Unknown",
                    "stale": stale_flag,
                    "low_accuracy": low_accuracy_flag,
                    "data_points": data_points,
                    "model_type": model_meta.get(
                        "model_type", latest_entry.get("model_type", "UNKNOWN")
                    ),
                    "source": model_meta.get(
                        "data_source", latest_entry.get("data_source", "UNKNOWN")
                    ),
                    "ensemble_accuracy": round(
                        float(model_meta.get("ensemble_accuracy", accuracy)), 6
                    ),
                }
            )

            for historic_entry in trimmed_entries:
                history_payload.append(
                    {
                        "symbol": symbol,
                        "training_date": historic_entry.get("training_date"),
                        "accuracy": float(historic_entry.get("accuracy") or 0.0),
                        "accuracy_percent": round(
                            float(historic_entry.get("accuracy") or 0.0) * 100, 2
                        ),
                        "features_used": len(historic_entry.get("features", [])),
                    }
                )

        models_payload.sort(key=lambda item: item["symbol"])
        history_payload.sort(
            key=lambda item: item.get("training_date", ""), reverse=True
        )

        avg_accuracy = (
            round(sum(accuracies) / len(accuracies), 6) if accuracies else None
        )
        median_accuracy = (
            round(statistics_lib.median(accuracies), 6) if accuracies else None
        )

        summary = {
            "profile": self.profile_key,
            "model_count": len(models_payload),
            "avg_accuracy": avg_accuracy,
            "avg_accuracy_percent": round(avg_accuracy * 100, 2)
            if avg_accuracy is not None
            else None,
            "median_accuracy": median_accuracy,
            "median_accuracy_percent": round(median_accuracy * 100, 2)
            if median_accuracy is not None
            else None,
            "stale_models": stale_count,
            "stale_threshold_hours": stale_hours,
            "low_accuracy_models": low_accuracy_count,
            "low_accuracy_threshold": low_accuracy,
            "alerts": [],
        }

        if stale_count:
            summary["alerts"].append(f"{stale_count} models older than {stale_hours}h")
        if low_accuracy_count:
            summary["alerts"].append(
                f"{low_accuracy_count} models below {int(low_accuracy * 100)}% accuracy"
            )

        if accuracies:
            summary["min_accuracy"] = round(min(accuracies), 6)
            summary["min_accuracy_percent"] = round(min(accuracies) * 100, 2)
            summary["max_accuracy"] = round(max(accuracies), 6)
            summary["max_accuracy_percent"] = round(max(accuracies) * 100, 2)

        if latest_dt:
            latest_age_hours = max((now - latest_dt).total_seconds() / 3600.0, 0.0)
            summary["latest_training"] = latest_dt.isoformat()
            summary["latest_training_display"] = latest_dt.strftime("%Y-%m-%d %H:%M")
            summary["latest_training_age_hours"] = latest_age_hours
            summary["latest_training_age_display"] = _format_duration_hours(
                latest_age_hours
            )

        if oldest_dt:
            oldest_age_hours = max((now - oldest_dt).total_seconds() / 3600.0, 0.0)
            summary["oldest_training"] = oldest_dt.isoformat()
            summary["oldest_training_display"] = oldest_dt.strftime("%Y-%m-%d %H:%M")
            summary["oldest_training_age_hours"] = oldest_age_hours
            summary["oldest_training_age_display"] = _format_duration_hours(
                oldest_age_hours
            )

        history_limit_total = max(
            20, history_per_symbol * max(1, len(metrics_by_symbol))
        )
        return {
            "summary": summary,
            "models": models_payload,
            "history": history_payload[:history_limit_total],
        }

    def predict_ultimate(self, symbol, current_data, include_futures=True):
        """Make ultimate prediction with parallel-ready features - FIXED VERSION"""
        try:
            # Trigger Shadow Inference (Async)
            self.predict_shadow_async(symbol, current_data)

            if not self.ensure_model_ready(symbol):
                return None

            model_info = self.models[symbol]
            model = model_info["ensemble_model"]
            feature_cols = model_info["feature_cols"]

            features = self.create_ultimate_feature_vector(
                current_data, feature_cols, symbol=symbol
            )

            if not features:
                return None

            # FIX: Suppress feature name warnings
            import warnings
            from sklearn.exceptions import DataConversionWarning

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", category=DataConversionWarning)

                try:
                    prediction_proba = model.predict_proba([features])[0]
                    prediction = model.predict([features])[0]
                except Exception as e:
                    if "multi_class" in str(e) and "LogisticRegression" in str(e):
                        self.log_training(
                            symbol,
                            f"⚠️ Model prediction failed due to outdated LogisticRegression, retraining...",
                            0,
                        )
                        # Remove the model so it gets retrained
                        if symbol in self.models:
                            del self.models[symbol]
                        return None
                    else:
                        raise

            signal_map = {
                2: "STRONG_BUY",
                1: "BUY",
                0: "HOLD",
                -1: "SELL",
                -2: "STRONG_SELL",
            }
            signal = signal_map.get(prediction, "HOLD")

            confidence = max(prediction_proba)

            ensemble_accuracy = model_info.get("ensemble_accuracy", 0.5)
            indicators_used = model_info.get("feature_count", len(feature_cols))
            model_performances = model_info.get("model_performances", {})

            # Construct explainable reason
            feature_importance = model_info.get("feature_importance", {})
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]
            top_factor_str = ", ".join([f[0] for f in top_features]) if top_features else "Pattern Analysis"
            
            reason = f"ML Confidence: {confidence:.0%}. Factors: {top_factor_str}"

            base_prediction = {
                "ultimate_ensemble": {
                    "signal": signal,
                    "confidence": float(confidence),
                    "reason": reason,
                    "prediction": int(prediction),
                    "accuracy": float(ensemble_accuracy),
                    "features_used": len(feature_cols),
                    "indicators_total": indicators_used,
                    "model_age": self._get_model_age(model_info.get("training_date")),
                    "data_source": model_info.get("data_source", "UNKNOWN"),
                    "model_type": "ULTIMATE_ENSEMBLE",
                    "individual_performances": model_performances,
                }
            }

            if include_futures:
                base_prediction = self._integrate_futures_prediction(
                    symbol, current_data, base_prediction
                )

            return base_prediction

        except Exception as e:
            print(f"❌ Ultimate prediction error for {symbol}: {e}")
            return None

    def ensure_model_ready(self, symbol):
        """Load or train a model on-demand when none is currently available."""
        if not symbol:
            return False

        if symbol in self.models:
            return True

        lock = self._model_training_locks[symbol]
        with lock:
            if symbol in self.models:
                return True

            if self.load_models(symbol):
                return True

            if self.load_models(symbol):
                return True

            self.log_training(
                symbol, "⚠️ No saved model detected. Execution BLOCKED (SaaS Safety Rule).", 0
            )
            # SAAS SAFETY: Implicit fallback training DISABLED
            # We strictly prevent rule-based trade execution without an explicit model.
            return False

            # Attempt to load the freshly trained model into memory
            if self.load_models(symbol):
                return True

            self.log_training(symbol, "❌ Newly trained model could not be loaded", 0)
            return False

    def _integrate_futures_prediction(self, symbol, current_data, base_prediction):
        """Blend futures signals into the main ultimate ensemble when enabled."""
        try:
            if not base_prediction or not TRADING_CONFIG.get("futures_enabled", False):
                return base_prediction

            futures_system = getattr(
                self, "futures_integration", None
            ) or globals().get("futures_ml_system")
            if not futures_system or futures_system is self:
                return base_prediction

            futures_data = self._resolve_futures_market_data(
                symbol, current_data, futures_system
            )
            if not futures_data:
                return base_prediction

            futures_prediction = futures_system.predict_futures(symbol, futures_data)
            if not futures_prediction or "ultimate_ensemble" not in futures_prediction:
                return base_prediction

            base_block = base_prediction.get("ultimate_ensemble", {})
            futures_block = futures_prediction.get("ultimate_ensemble", {})

            if not base_block or not futures_block:
                return base_prediction

            futures_weight = TRADING_CONFIG.get("futures_signal_weight", 0.3)
            futures_weight = max(0.0, min(0.5, float(futures_weight)))

            base_signal_score = self._map_signal_to_score(base_block.get("signal"))
            futures_signal_score = self._map_signal_to_score(
                futures_block.get("signal")
            )

            combined_score = (base_signal_score * (1 - futures_weight)) + (
                futures_signal_score * futures_weight
            )
            combined_prediction = int(max(-2, min(2, round(combined_score))))

            confidence_base = float(base_block.get("confidence", 0.5))
            confidence_futures = float(futures_block.get("confidence", 0.5))
            combined_confidence = (confidence_base * (1 - futures_weight)) + (
                confidence_futures * futures_weight
            )

            # Reduce confidence when signals disagree materially
            if base_signal_score * futures_signal_score < 0:
                combined_confidence *= 0.75

            combined_confidence = float(max(0.05, min(0.99, combined_confidence)))

            signal_map = {
                2: "STRONG_BUY",
                1: "BUY",
                0: "HOLD",
                -1: "SELL",
                -2: "STRONG_SELL",
            }
            combined_signal = signal_map.get(
                combined_prediction, base_block.get("signal", "HOLD")
            )

            base_block.update(
                {
                    "signal": combined_signal,
                    "prediction": combined_prediction,
                    "confidence": combined_confidence,
                    "futures_weight": futures_weight,
                    "futures_signal_score": futures_signal_score,
                    "futures_confidence": confidence_futures,
                }
            )

            base_prediction["ultimate_ensemble"] = base_block
            base_prediction["futures_enhanced"] = True
            base_prediction["futures_component"] = {
                "signal": futures_block.get("signal"),
                "confidence": confidence_futures,
                "prediction": futures_block.get("prediction"),
                "details": deepcopy(futures_prediction.get("futures_signals", [])),
                "market_snapshot": futures_data,
            }

            return base_prediction

        except Exception as e:
            print(f"❌ Futures integration error for {symbol}: {e}")
            return base_prediction

    def _resolve_futures_market_data(self, symbol, current_data, futures_system):
        """Retrieve the richest futures dataset available for the given symbol."""
        futures_data = None

        try:
            if "futures_dashboard_state" in globals():
                if "futures_data_lock" in globals():
                    lock = globals().get("futures_data_lock")
                    if lock:
                        with lock:
                            state = futures_dashboard_state.get("market_data", {})
                            if state:
                                futures_data = deepcopy(state.get(symbol))
                    else:
                        state = futures_dashboard_state.get("market_data", {})
                        if state:
                            futures_data = deepcopy(state.get(symbol))
                else:
                    state = futures_dashboard_state.get("market_data", {})
                    if state:
                        futures_data = deepcopy(state.get(symbol))
        except Exception:
            futures_data = None

        if not futures_data:
            try:
                futures_data = futures_system.get_futures_market_data(symbol)
            except Exception:
                futures_data = None

        if current_data:
            merged = dict(current_data)
            if futures_data:
                merged.update({k: v for k, v in futures_data.items() if v is not None})
            return merged

        return futures_data

    def _map_signal_to_score(self, signal):
        mapping = {
            "STRONG_BUY": 2.0,
            "BUY": 1.0,
            "HOLD": 0.0,
            "SELL": -1.0,
            "STRONG_SELL": -2.0,
        }
        return float(mapping.get(signal, 0.0))

    def _add_futures_features(self, features, df):
        """Augment feature DataFrame with futures-specific indicators when available."""
        try:
            # Ensure we operate on a copy to avoid mutating caller unexpectedly
            futures_features = features.copy()

            if "funding_rate" in df.columns:
                futures_features["funding_rate"] = df["funding_rate"].fillna(0)
                futures_features["funding_rate_ma"] = (
                    df["funding_rate"].rolling(8, min_periods=1).mean().fillna(0)
                )
                futures_features["funding_rate_trend"] = np.sign(
                    df["funding_rate"].diff(4)
                ).fillna(0)

            if "open_interest" in df.columns:
                oi = df["open_interest"].replace(0, np.nan)
                futures_features["open_interest"] = (
                    df["open_interest"].ffill().bfill().fillna(0)
                )
                futures_features["oi_change"] = (
                    df["open_interest"]
                    .pct_change()
                    .replace([np.inf, -np.inf], 0)
                    .fillna(0)
                )
                futures_features["oi_trend"] = np.sign(
                    df["open_interest"].diff(5)
                ).fillna(0)

            if "basis" in df.columns:
                futures_features["basis"] = df["basis"].fillna(0)
                futures_features["basis_ma"] = (
                    df["basis"].rolling(10, min_periods=1).mean().fillna(0)
                )
                futures_features["basis_deviation"] = (
                    futures_features["basis"] - futures_features["basis_ma"]
                )

            if {"volume", "taker_buy_volume"}.issubset(df.columns):
                total_volume = df["volume"].replace(0, np.nan)
                taker_buy_volume = df["taker_buy_volume"].fillna(0)
                taker_sell_volume = (df["volume"] - taker_buy_volume).fillna(0)
                vol_delta = (taker_buy_volume - taker_sell_volume) / total_volume
                vol_delta = vol_delta.replace([np.inf, -np.inf], 0).fillna(0)
                futures_features["volume_delta"] = vol_delta
                futures_features["cumulative_volume_delta"] = (
                    vol_delta.cumsum().ffill().fillna(0)
                )

            if {"long_liquidations", "short_liquidations"}.issubset(df.columns):
                total_liq = (
                    df["long_liquidations"] + df["short_liquidations"]
                ).replace(0, np.nan)
                futures_features["liquidation_ratio"] = (
                    (df["long_liquidations"] / total_liq)
                    .replace([np.inf, -np.inf], 0)
                    .fillna(0.5)
                )
                volume_base = (
                    df["volume"].replace(0, np.nan)
                    if "volume" in df.columns
                    else total_liq
                )
                futures_features["liquidation_volume"] = (
                    ((df["long_liquidations"] + df["short_liquidations"]) / volume_base)
                    .replace([np.inf, -np.inf], 0)
                    .fillna(0)
                )

            return futures_features

        except Exception as e:
            print(f"❌ Futures feature augmentation error: {e}")
            return features

    def _augment_feature_vector_with_futures(self, symbol, current_data, features):
        """Inject futures metrics into the single-sample feature vector."""
        try:
            if not current_data:
                return features

            state = self._futures_feature_cache.setdefault(symbol, {})

            funding_rate = current_data.get("funding_rate")
            if funding_rate is not None:
                funding_rate = float(funding_rate)
                prev_ma = state.get("funding_rate_ma", funding_rate)
                ma = prev_ma * 0.7 + funding_rate * 0.3 if state else funding_rate
                trend = np.sign(funding_rate - prev_ma) if prev_ma is not None else 0
                features["funding_rate"] = funding_rate
                features["funding_rate_ma"] = ma
                features["funding_rate_trend"] = float(trend)
                state["funding_rate_ma"] = ma

            open_interest = current_data.get("open_interest")
            if open_interest is not None:
                open_interest = float(open_interest)
                prev_oi = state.get("open_interest", open_interest)
                oi_change = 0.0
                if prev_oi not in (0, None):
                    oi_change = (open_interest - prev_oi) / max(abs(prev_oi), 1.0)
                features["open_interest"] = open_interest
                features["oi_change"] = float(oi_change)
                features["oi_trend"] = float(np.sign(oi_change))
                state["open_interest"] = open_interest

            basis = current_data.get("basis")
            if basis is not None:
                basis = float(basis)
                prev_basis_ma = state.get("basis_ma", basis)
                basis_ma = prev_basis_ma * 0.6 + basis * 0.4 if state else basis
                features["basis"] = basis
                features["basis_ma"] = basis_ma
                features["basis_deviation"] = basis - basis_ma
                state["basis_ma"] = basis_ma

            taker_buy_volume = current_data.get("taker_buy_volume")
            total_volume = current_data.get("volume")
            if taker_buy_volume is not None and total_volume:
                taker_buy_volume = float(taker_buy_volume)
                total_volume = float(total_volume) if float(total_volume) != 0 else 1.0
                taker_sell_volume = float(total_volume - taker_buy_volume)
                vol_delta = (taker_buy_volume - taker_sell_volume) / total_volume
                features["volume_delta"] = float(vol_delta)
                cumulative = state.get("cumulative_volume_delta", 0.0) + vol_delta
                features["cumulative_volume_delta"] = float(cumulative)
                state["cumulative_volume_delta"] = cumulative

            long_liq = current_data.get("long_liquidations")
            short_liq = current_data.get("short_liquidations")
            if long_liq is not None and short_liq is not None:
                long_liq = float(long_liq)
                short_liq = float(short_liq)
                total_liq = max(long_liq + short_liq, 1.0)
                features["liquidation_ratio"] = long_liq / total_liq
                base_volume = float(total_volume) if total_volume else total_liq
                base_volume = max(base_volume, 1.0)
                features["liquidation_volume"] = (long_liq + short_liq) / base_volume

            return features

        except Exception as e:
            print(f"❌ Futures vector augmentation error for {symbol}: {e}")
            return features

    def create_ultimate_feature_vector(self, current_data, feature_cols, symbol=None):
        """Create ultimate feature vector"""
        try:
            if not current_data:
                return [0 for _ in feature_cols]

            features = {}

            current_price = float(
                current_data.get("close", current_data.get("price", 0)) or 0.0
            )
            raw_price_change = (
                current_data.get("change", current_data.get("price_change", 0)) or 0
            )
            price_change = float(raw_price_change) / 100.0

            volume = float(current_data.get("volume", 1_000_000) or 0.0)
            high = float(current_data.get("high", current_price * 1.01) or 0.0)
            low = float(current_data.get("low", current_price * 0.99) or 0.0)
            open_price = float(current_data.get("open", current_price) or current_price)

            raw_volume_change = current_data.get(
                "volume_change",
                current_data.get("volume_change_pct", price_change * 100),
            )
            if raw_volume_change is None:
                raw_volume_change = price_change * 100
            volume_change = float(raw_volume_change)
            if abs(volume_change) > 1:
                volume_change /= 100.0

            price_range = abs(high - low)
            atr = (
                (price_range / max(current_price, 1)) if current_price else price_range
            )

            features["price_change"] = price_change
            features["price_momentum"] = price_change * 5
            features["log_return"] = np.log1p(price_change) if price_change > -1 else -1
            features["price_volatility"] = abs(price_change) * 2
            features["price_zscore"] = price_change * 10
            features["efficiency_ratio"] = abs(price_change) * 5
            features["average_true_range"] = atr

            features["volume_change"] = volume_change
            features["volume_ratio"] = 1 + volume_change
            features["volume_obv"] = volume * price_change

            features["rsi_14"] = 50 + price_change * 500
            features["macd_hist"] = price_change * 10
            features["bb_percent_b"] = float(min(max(0.5 + price_change * 5, 0), 1))

            features["sma_20"] = current_price * (1 + price_change)
            features["sma_ratio_20_50"] = 1 + price_change * 0.3
            features["ema_12"] = current_price * (1 + price_change * 0.4)
            features["ema_26"] = current_price * (1 + price_change * 0.2)
            features["ema_cross_12_26"] = (
                1 if features["ema_12"] >= features["ema_26"] else 0
            )

            adx_estimate = 25 + abs(price_change) * 500
            features["adx"] = float(max(0, min(adx_estimate, 100)))
            features["mfi"] = float(max(0, min(50 + volume_change * 100, 100)))

            features["stoch_k"] = float(max(0, min(50 + price_change * 500, 100)))
            features["cci"] = price_change * 100

            if TRADING_CONFIG.get("futures_enabled", False):
                features = self._augment_feature_vector_with_futures(
                    symbol or "GLOBAL", current_data, features
                )

            if self.is_indicator_enabled("ICT"):
                features = self._augment_feature_vector_with_ict(
                    symbol or "GLOBAL", current_data, features
                )

            if self.is_indicator_enabled("SMC"):
                features = self._augment_feature_vector_with_smc(
                    symbol or "GLOBAL", current_data, features
                )

            if getattr(self, "qfm_engine", None):
                qfm_metrics = self.qfm_engine.compute_realtime_features(
                    symbol or "GLOBAL", current_data
                )
                if isinstance(qfm_metrics, dict):
                    for key, value in qfm_metrics.items():
                        features[key] = value

            return [float(features.get(col, 0)) for col in feature_cols]

        except Exception as e:
            print(f"❌ Ultimate feature vector error: {e}")
            return None

    def _get_model_age(self, training_date):
        """Calculate model age"""
        if not training_date:
            return "Unknown"
        try:
            train_dt = datetime.fromisoformat(training_date)
            age_days = (datetime.now() - train_dt).days
            return f"{age_days}d"
        except Exception:
            return "Unknown"

    def load_models(self, symbol=None):
        """Load ultimate models"""
        try:
            if symbol:
                # NEW: Prioritize DB-defined Active Model
                model_path = None
                try:
                    from app.models import MLModel
                    active_rec = MLModel.query.filter_by(symbol=symbol, status="active").order_by(MLModel.created_at.desc()).first()
                    if active_rec and active_rec.file_path and os.path.exists(active_rec.file_path):
                         model_path = active_rec.file_path
                         self.log_training(symbol, f"Using Active Model from DB: {active_rec.version}", 10)
                except Exception:
                    pass

                # Fallback to legacy default path (or if not in DB)
                if not model_path:
                    legacy_path = os.path.join(self.models_dir, f"{symbol}_ultimate_model.pkl")
                    if os.path.exists(legacy_path):
                        model_path = legacy_path
                
                if model_path and os.path.exists(model_path):
                    try:
                        model_data = joblib.load(model_path)
                        self.models[symbol] = model_data
                        indicators = model_data.get(
                            "feature_count", len(model_data.get("feature_cols", []))
                        )
                        accuracy = model_data.get("ensemble_accuracy", 0)
                        self.log_training(
                            symbol,
                            f"✅ Ultimate model loaded (Accuracy: {accuracy:.4f}, Indicators: {indicators})",
                            100,
                        )
                        
                        # --- BEGIN SHADOW LOADING ---
                        try:
                            from app.models import MLModel
                            shadows = MLModel.query.filter_by(symbol=symbol, status="shadow").all()
                            
                            if symbol not in self.shadow_models:
                                self.shadow_models[symbol] = {}
                                
                            for s_rec in shadows:
                                # Resolve Path
                                path = s_rec.file_path
                                if not os.path.exists(path):
                                    # Fallback: check in models_dir
                                    alt_path = os.path.join(self.models_dir, os.path.basename(path))
                                    if os.path.exists(alt_path):
                                        path = alt_path
                                
                                if os.path.exists(path):
                                    try:
                                        s_data = joblib.load(path)
                                        self.shadow_models[symbol][s_rec.version] = s_data
                                        self.log_training(symbol, f"👻 Loaded Shadow Model: {s_rec.version}", 10)
                                    except:
                                        pass
                        except Exception:
                            pass
                        # --- END SHADOW LOADING ---

                        return True
                    except Exception as e:
                        error_str = str(e)
                        if "numpy._core" in error_str:
                            self.log_training(
                                symbol,
                                f"⚠️ Model incompatible with current NumPy version (numpy._core issue), skipping",
                                0,
                            )
                        elif "multi_class" in error_str and "LogisticRegression" in error_str:
                            self.log_training(
                                symbol,
                                f"⚠️ Model contains outdated LogisticRegression parameters, retraining...",
                                0,
                            )
                            # Delete the old model file so it gets retrained
                            try:
                                os.remove(model_path)
                            except:
                                pass
                            return False
                        else:
                            self.log_training(symbol, f"❌ Error loading model: {e}", 0)
                        return False
                else:
                    self.log_training(symbol, "⚠️ No ultimate model found", 0)
                    return False
            else:
                models_loaded = 0
                model_files = [
                    f
                    for f in os.listdir(self.models_dir)
                    if f.endswith("_ultimate_model.pkl")
                ]

                if not model_files:
                    self.log_training("SYSTEM", "⚠️ No ultimate model files found", 0)
                    return False

                for file in model_files:
                    try:
                        symbol_name = file.replace("_ultimate_model.pkl", "")
                        model_path = os.path.join(self.models_dir, file)
                        model_data = joblib.load(model_path)
                        self.models[symbol_name] = model_data
                        models_loaded += 1
                        indicators = model_data.get(
                            "feature_count", len(model_data.get("feature_cols", []))
                        )
                        accuracy = model_data.get("ensemble_accuracy", 0)
                        self.log_training(
                            symbol_name,
                            f"✅ Ultimate model loaded (Accuracy: {accuracy:.4f}, Indicators: {indicators})",
                            100,
                        )
                    except Exception as e:
                        if "numpy._core" in str(e):
                            self.log_training(
                                "SYSTEM",
                                f"⚠️ Skipping {file} - incompatible with current NumPy version (numpy._core issue)",
                                0,
                            )
                        else:
                            self.log_training(
                                "SYSTEM", f"❌ Error loading {file}: {e}", 0
                            )

                self.log_training(
                    "SYSTEM", f"📊 Total ultimate models loaded: {models_loaded}", 100
                )
                return models_loaded > 0

        except Exception as e:
            self.log_training(
                symbol or "SYSTEM", f"❌ Error loading ultimate model: {e}", 0
            )
            return False

    def comprehensive_backtest(
        self,
        symbol,
        historical_data=None,
        years=1,
        interval="1d",
        initial_balance=1000.0,
        use_real_data=True,
    ):
        """Run a supervised backtest using the ultimate feature pipeline and ensemble model."""

        result = {
            "symbol": symbol,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "final_balance": float(initial_balance),
            "trades": [],
            "equity_curve": [],
            "start_date": None,
            "end_date": None,
            "accuracy": 0.0,
            "train_samples": 0,
            "test_samples": 0,
            "notes": "insufficient data",
        }

        try:
            if historical_data is None or len(historical_data) == 0:
                historical_data = (
                    self.get_real_historical_data(
                        symbol, years=years, interval=interval
                    )
                    if use_real_data
                    else self.generate_fallback_data(symbol, years=years)
                )

            if historical_data is None or len(historical_data) < 200:
                self.backtest_results[symbol] = result
                return result

            if not isinstance(historical_data, pd.DataFrame):
                historical_data = pd.DataFrame(historical_data)

            data = historical_data.copy()
            if "timestamp" in data.columns:
                data.index = pd.to_datetime(
                    data["timestamp"], unit="ms", errors="coerce"
                )
            elif "open_time" in data.columns:
                data.index = pd.to_datetime(
                    data["open_time"], unit="ms", errors="coerce"
                )
            elif "date" in data.columns:
                data.index = pd.to_datetime(data["date"], errors="coerce")
            else:
                data.index = pd.to_datetime(data.index, errors="coerce")

            data = data.sort_index()
            data = data[~data.index.isna()]

            if "close" not in data.columns:
                self.backtest_results[symbol] = result
                return result

            feature_df = self.create_ultimate_features(data)
            if (
                feature_df is None
                or feature_df.empty
                or "target" not in feature_df.columns
            ):
                self.backtest_results[symbol] = result
                return result

            feature_df = feature_df.replace([np.inf, -np.inf], np.nan).dropna()
            if feature_df.empty:
                self.backtest_results[symbol] = result
                return result

            data = data.loc[feature_df.index]

            exclude_cols = {
                "date",
                "target",
                "target_1",
                "target_5",
                "timestamp",
                "open_time",
                "close_time",
            }
            feature_cols = [
                col
                for col in feature_df.columns
                if col not in exclude_cols
                and np.issubdtype(feature_df[col].dtype, np.number)
            ]

            if not feature_cols:
                self.backtest_results[symbol] = result
                return result

            X = feature_df[feature_cols]
            y = feature_df["target"]

            split_idx = int(len(X) * 0.7)
            if split_idx < 50 or len(X) - split_idx < 50:
                self.backtest_results[symbol] = result
                return result

            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            model = RandomForestClassifier(
                n_estimators=150,
                max_depth=12,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X_train, y_train)
            accuracy = model.score(X_test, y_test)

            predictions = model.predict(X_test)

            equity = float(initial_balance)
            position_qty = 0.0
            entry_price = 0.0
            open_trade = None
            equity_curve = []
            trades = []
            last_price = None
            open_trade = None

            for idx, signal in zip(X_test.index, predictions):
                price = float(data.loc[idx, "close"]) if idx in data.index else None
                if not price or price <= 0:
                    continue

                portfolio_value = equity + (position_qty * price)
                equity_curve.append(float(portfolio_value))

                if signal > 0 and position_qty == 0:
                    qty = equity / price if price > 0 else 0
                    if qty <= 0:
                        continue
                    position_qty = qty
                    equity = 0.0
                    entry_price = price
                    open_trade = {
                        "entry_time": idx,
                        "entry_price": price,
                        "quantity": qty,
                    }
                elif signal < 0 and position_qty > 0:
                    sale_value = position_qty * price
                    pnl = sale_value - (position_qty * entry_price)
                    equity = sale_value
                    trade_record = {
                        "entry_time": open_trade["entry_time"].isoformat()  # type: ignore
                        if hasattr(open_trade["entry_time"], "isoformat")  # type: ignore
                        else str(open_trade["entry_time"]),  # type: ignore
                        "exit_time": idx.isoformat()
                        if hasattr(idx, "isoformat")
                        else str(idx),
                        "entry_price": float(entry_price),
                        "exit_price": float(price),
                        "quantity": float(position_qty),
                        "pnl": float(pnl),
                        "pnl_percent": float(((price / entry_price) - 1) * 100),
                    }
                    trades.append(trade_record)
                    position_qty = 0.0
                    entry_price = 0.0
                    open_trade = None
                    equity_curve[-1] = float(equity)

                last_price = price

            if position_qty > 0 and last_price:
                sale_value = position_qty * last_price
                pnl = sale_value - (position_qty * entry_price)
                equity = sale_value
                trade_record = {
                    "entry_time": open_trade["entry_time"].isoformat()
                    if open_trade and hasattr(open_trade["entry_time"], "isoformat")
                    else str(open_trade["entry_time"])
                    if open_trade
                    else None,
                    "exit_time": str(X_test.index[-1]) if len(X_test.index) else None,
                    "entry_price": float(entry_price),
                    "exit_price": float(last_price),
                    "quantity": float(position_qty),
                    "pnl": float(pnl),
                    "pnl_percent": float(((last_price / entry_price) - 1) * 100),
                }
                trades.append(trade_record)
                position_qty = 0.0
                equity_curve.append(float(equity))

            final_balance = equity
            total_return = (
                (final_balance - initial_balance) / initial_balance
                if initial_balance
                else 0.0
            )

            max_drawdown = 0.0
            peak = None
            for value in equity_curve:
                if peak is None or value > peak:
                    peak = value
                if peak:
                    drawdown = (peak - value) / peak
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

            returns_array = (
                np.diff(equity_curve) / equity_curve[:-1]
                if len(equity_curve) > 1
                else np.array([])
            )
            sharpe_ratio = (
                float(np.mean(returns_array) / np.std(returns_array) * np.sqrt(252))
                if returns_array.size > 0 and np.std(returns_array) > 0
                else 0.0
            )

            if trades:
                wins = len([t for t in trades if t["pnl"] > 0])
                losses = len([t for t in trades if t["pnl"] < 0])
                win_rate = (wins / len(trades)) * 100
                profits_sum = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                losses_sum = sum(t["pnl"] for t in trades if t["pnl"] < 0)
                if losses_sum < 0:
                    profit_factor = (
                        profits_sum / abs(losses_sum) if abs(losses_sum) > 0 else 0.0
                    )
                elif profits_sum > 0:
                    profit_factor = float("inf")
                else:
                    profit_factor = 0.0
            else:
                win_rate = 0.0
                profit_factor = 0.0

            result.update(
                {
                    "total_return": float(total_return),
                    "max_drawdown": float(max_drawdown),
                    "sharpe_ratio": float(sharpe_ratio),
                    "win_rate": float(win_rate),
                    "profit_factor": float(profit_factor)
                    if np.isfinite(profit_factor)
                    else None,
                    "final_balance": float(final_balance),
                    "trades": trades,
                    "equity_curve": [float(v) for v in equity_curve],
                    "start_date": data.index.min().isoformat()
                    if len(data.index)
                    else None,
                    "end_date": data.index.max().isoformat()
                    if len(data.index)
                    else None,
                    "accuracy": float(accuracy),
                    "train_samples": int(len(X_train)),
                    "test_samples": int(len(X_test)),
                    "notes": "success",
                }
            )

        except Exception as e:
            self.log_training(symbol, f"❌ Backtest error: {e}", 0)
            result["notes"] = str(e)

        self.backtest_results[symbol] = result
        return result

    def _augment_feature_vector_with_ict(self, symbol, current_data, features):
        try:
            cache = self._ict_feature_cache.setdefault(symbol, {})

            price = float(current_data.get("price", current_data.get("close", 0)) or 0)
            high = float(current_data.get("high", price) or price)
            low = float(current_data.get("low", price) or price)

            prev_high = cache.get("prev_high", high)
            prev_low = cache.get("prev_low", low)

            range_span = max(high - low, 1e-9)
            liquidity_bias = (price - low) / range_span
            fvg_size = abs(prev_high - prev_low)
            fvg_presence = 1 if fvg_size > price * 0.002 else 0

            rolling_bias = cache.get("rolling_bias", 0)
            bias = 0.7 * rolling_bias + 0.3 * (price - (high + low) / 2)

            features["ict_liquidity_bias"] = float(liquidity_bias)
            features["ict_fvg_size"] = float(fvg_size)
            features["ict_fvg_presence"] = float(fvg_presence)
            features["ict_daily_bias"] = float(bias)
            features["ict_mean_threshold_dev"] = float(price - (high + low) / 2)
            features["ict_session_range"] = float(range_span)

            cache.update({"prev_high": high, "prev_low": low, "rolling_bias": bias})

            return features
        except Exception as e:
            print(f"❌ ICT vector augmentation error for {symbol}: {e}")
            return features

    def enrich_realtime_indicators(self, symbol, market_data, historical_prices=None):
        """Compute realtime ICT/SMC metrics and attach to market data"""
        updates = {}

        if self.is_indicator_enabled("ICT"):
            updates = self._augment_feature_vector_with_ict(
                symbol, market_data, updates
            )

        if self.is_indicator_enabled("SMC"):
            updates = self._augment_feature_vector_with_smc(
                symbol, market_data, updates
            )

        if updates:
            market_data.update(updates)

        return updates

    def _augment_feature_vector_with_smc(self, symbol, current_data, features):
        try:
            cache = self._smc_feature_cache.setdefault(symbol, {})

            price = float(current_data.get("price", current_data.get("close", 0)) or 0)
            high = float(current_data.get("high", price) or price)
            low = float(current_data.get("low", price) or price)

            prev_high = cache.get("prev_high", high)
            prev_low = cache.get("prev_low", low)
            prev_price = cache.get("prev_price", price)

            higher_high = 1 if high > prev_high else 0
            lower_low = 1 if low < prev_low else 0
            structure_bias = cache.get("structure_bias", 0)
            structure_bias = 0.5 * structure_bias + 0.5 * (higher_high - lower_low)

            order_block = cache.get("order_block", price)
            order_block = 0.8 * order_block + 0.2 * price
            order_block_strength = 1 if abs(order_block - price) < price * 0.001 else 0

            range_mid = (high + low) / 2
            premium_discount = (price - range_mid) / max(range_mid, 1e-9)

            bos_signal = 0
            if price > prev_high:
                bos_signal = 1
            elif price < prev_low:
                bos_signal = -1

            liquidity_void = abs(price - prev_price)

            features["smc_structure_bias"] = float(structure_bias)
            features["smc_order_block_strength"] = float(order_block_strength)
            features["smc_premium_discount"] = float(premium_discount)
            features["smc_bos_signal"] = float(bos_signal)
            features["smc_liquidity_void"] = float(liquidity_void)

            cache.update(
                {
                    "prev_high": high,
                    "prev_low": low,
                    "prev_price": price,
                    "structure_bias": structure_bias,
                    "order_block": order_block,
                }
            )

            return features
        except Exception as e:
            print(f"❌ SMC vector augmentation error for {symbol}: {e}")
            return features

        try:
            if historical_data is None or len(historical_data) == 0:
                if use_real_data:
                    historical_data = self.get_real_historical_data(
                        symbol, years=years, interval=interval
                    )
                else:
                    historical_data = self.generate_fallback_data(symbol, years=years)

            if historical_data is None or len(historical_data) < 200:
                self.backtest_results[symbol] = result
                return result

            if not isinstance(historical_data, pd.DataFrame):
                historical_data = pd.DataFrame(historical_data)

            data = historical_data.copy()
            if "timestamp" in data.columns:
                data.index = pd.to_datetime(
                    data["timestamp"], unit="ms", errors="coerce"
                )
            elif "open_time" in data.columns:
                data.index = pd.to_datetime(
                    data["open_time"], unit="ms", errors="coerce"
                )
            else:
                data.index = pd.to_datetime(data.index, errors="coerce")

            data = data.sort_index()
            data = data[~data.index.isna()]

            if "close" not in data.columns:
                self.backtest_results[symbol] = result
                return result

            feature_df = self.create_ultimate_features(data)
            if (
                feature_df is None
                or feature_df.empty
                or "target" not in feature_df.columns
            ):
                self.backtest_results[symbol] = result
                return result

            feature_df = feature_df.replace([np.inf, -np.inf], np.nan).dropna()
            if feature_df.empty:
                self.backtest_results[symbol] = result
                return result

            data = data.loc[feature_df.index]

            exclude_cols = {
                "date",
                "target",
                "target_1",
                "target_5",
                "timestamp",
                "open_time",
                "close_time",
            }
            feature_cols = [
                col
                for col in feature_df.columns
                if col not in exclude_cols
                and np.issubdtype(feature_df[col].dtype, np.number)
            ]

            if not feature_cols:
                self.backtest_results[symbol] = result
                return result

            X = feature_df[feature_cols]
            y = feature_df["target"]

            split_idx = int(len(X) * 0.7)
            if split_idx < 50 or len(X) - split_idx < 50:
                self.backtest_results[symbol] = result
                return result

            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            model = RandomForestClassifier(
                n_estimators=150,
                max_depth=12,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X_train, y_train)
            accuracy = model.score(X_test, y_test)

            predictions = model.predict(X_test)

            equity = float(initial_balance)
            position_qty = 0.0
            entry_price = 0.0
            open_trade = None
            equity_curve = []
            trades = []
            last_price = None

            for idx, signal in zip(X_test.index, predictions):
                price = float(data.loc[idx, "close"]) if idx in data.index else None
                if not price or price <= 0:
                    continue

                portfolio_value = equity + (position_qty * price)
                equity_curve.append(float(portfolio_value))

                if signal > 0 and position_qty == 0:
                    qty = equity / price if price > 0 else 0
                    if qty <= 0:
                        continue
                    position_qty = qty
                    equity = 0.0
                    entry_price = price
                    open_trade = {
                        "entry_time": idx,
                        "entry_price": price,
                        "quantity": qty,
                    }
                elif signal < 0 and position_qty > 0:
                    sale_value = position_qty * price
                    pnl = sale_value - (position_qty * entry_price)
                    equity = sale_value
                    trade_record = {
                        "entry_time": open_trade["entry_time"].isoformat()
                        if hasattr(open_trade["entry_time"], "isoformat")
                        else str(open_trade["entry_time"]),
                        "exit_time": idx.isoformat()
                        if hasattr(idx, "isoformat")
                        else str(idx),
                        "entry_price": float(entry_price),
                        "exit_price": float(price),
                        "quantity": float(position_qty),
                        "pnl": float(pnl),
                        "pnl_percent": float(((price / entry_price) - 1) * 100),
                    }
                    trades.append(trade_record)
                    position_qty = 0.0
                    entry_price = 0.0
                    open_trade = None
                    equity_curve[-1] = float(equity)

                last_price = price

            if position_qty > 0 and last_price:
                sale_value = position_qty * last_price
                pnl = sale_value - (position_qty * entry_price)
                equity = sale_value
                trade_record = {
                    "entry_time": open_trade["entry_time"].isoformat()
                    if open_trade and hasattr(open_trade["entry_time"], "isoformat")
                    else str(open_trade["entry_time"])
                    if open_trade
                    else None,
                    "exit_time": str(X_test.index[-1]) if len(X_test.index) else None,
                    "entry_price": float(entry_price),
                    "exit_price": float(last_price),
                    "quantity": float(position_qty),
                    "pnl": float(pnl),
                    "pnl_percent": float(((last_price / entry_price) - 1) * 100),
                }
                trades.append(trade_record)
                position_qty = 0.0
                equity_curve.append(float(equity))

            final_balance = equity
            total_return = (
                (final_balance - initial_balance) / initial_balance
                if initial_balance
                else 0.0
            )

            max_drawdown = 0.0
            peak = None
            for value in equity_curve:
                if peak is None or value > peak:
                    peak = value
                if peak:
                    drawdown = (peak - value) / peak
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

            returns_array = (
                np.diff(equity_curve) / equity_curve[:-1]
                if len(equity_curve) > 1
                else np.array([])
            )
            sharpe_ratio = (
                float(np.mean(returns_array) / np.std(returns_array) * np.sqrt(252))
                if returns_array.size > 0 and np.std(returns_array) > 0
                else 0.0
            )

            if trades:
                wins = len([t for t in trades if t["pnl"] > 0])
                losses = len([t for t in trades if t["pnl"] < 0])
                win_rate = (wins / len(trades)) * 100
                profits_sum = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                losses_sum = sum(t["pnl"] for t in trades if t["pnl"] < 0)
                if losses_sum < 0:
                    profit_factor = (
                        profits_sum / abs(losses_sum) if abs(losses_sum) > 0 else 0.0
                    )
                elif profits_sum > 0:
                    profit_factor = float("inf")
                else:
                    profit_factor = 0.0
            else:
                win_rate = 0.0
                profit_factor = 0.0

            result.update(
                {
                    "total_return": float(total_return),
                    "max_drawdown": float(max_drawdown),
                    "sharpe_ratio": float(sharpe_ratio),
                    "win_rate": float(win_rate),
                    "profit_factor": float(profit_factor)
                    if np.isfinite(profit_factor)
                    else None,
                    "final_balance": float(final_balance),
                    "trades": trades,
                    "equity_curve": [float(v) for v in equity_curve],
                    "start_date": data.index.min().isoformat()
                    if len(data.index)
                    else None,
                    "end_date": data.index.max().isoformat()
                    if len(data.index)
                    else None,
                    "accuracy": float(accuracy),
                    "train_samples": int(len(X_train)),
                    "test_samples": int(len(X_test)),
                    "notes": "success",
                }
            )

        except Exception as e:
            self.log_training(symbol, f"❌ Backtest error: {e}", 0)
            result["notes"] = str(e)

        self.backtest_results[symbol] = result
        return result

    def get_backtest_results(self, symbol=None):
        if symbol:
            return self.backtest_results.get(symbol)
        return self.backtest_results


# ==================== OPTIMIZED ML TRAINING SYSTEM ====================
class OptimizedMLTrainingSystem(UltimateMLTrainingSystem):
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = resolve_profile_path(
                "optimized_models", allow_legacy=False, migrate_legacy=True
            )
        elif not os.path.isabs(models_dir):
            models_dir = resolve_profile_path(models_dir, allow_legacy=True)
        super().__init__(models_dir=models_dir, profile_key="optimized")
        self.optimized_indicators = BEST_INDICATORS
        print(
            f"✅ OPTIMIZED ML System Initialized with {len(self.optimized_indicators)} Best Indicators"
        )

    # Convenience alias for clarity
    def create_optimized_features(self, df):
        optimized = super().create_ultimate_features(df)
        if optimized is None or optimized.empty:
            return optimized

        keep_cols = [
            col for col in self.optimized_indicators if col in optimized.columns
        ]
        target_cols = [
            col
            for col in ["target", "target_1", "target_5"]
            if col in optimized.columns
        ]
        return optimized[keep_cols + target_cols].copy()

    def train_optimized_model(self, symbol, data=None, use_real_data=True):
        # Delegate to base training (already bound to optimized features)
        trained = super().train_ultimate_model(
            symbol, data=data, use_real_data=use_real_data
        )
        if trained:
            self.models[symbol]["model_type"] = "OPTIMIZED_ENSEMBLE"
            self.models[symbol]["indicators_list"] = self.optimized_indicators
        return trained

    def predict_optimized(self, symbol, current_data):
        base_result = super().predict_ultimate(symbol, current_data)
        if not base_result:
            return None

        ultimate_block = base_result.get("ultimate_ensemble")
        if ultimate_block:
            optimized_block = dict(ultimate_block)
            optimized_block.update(
                {
                    "model_type": "OPTIMIZED_ENSEMBLE",
                    "indicators_total": len(self.optimized_indicators),
                    "indicators_list": self.optimized_indicators,
                }
            )
            base_result["optimized_ensemble"] = optimized_block
        return base_result

    # Ensure parallel utilities call optimized logic
    def train_advanced_model(self, symbol, use_real_data=True):
        return self.train_optimized_model(symbol, use_real_data=use_real_data)

    def predict_professional(self, symbol, market_data):
        return self.predict_optimized(symbol, market_data)

    def train_all_optimized_models(self, symbols=None, use_real_data=True):
        return super().train_all_ultimate_models(
            symbols=symbols, use_real_data=use_real_data
        )

    def comprehensive_backtest(
        self,
        symbol,
        historical_data=None,
        years=1,
        interval="1d",
        initial_balance=1000.0,
        use_real_data=True,
        **kwargs,
    ):
        result = super().comprehensive_backtest(symbol, **kwargs)
        if isinstance(result, dict):
            result["model_type"] = "OPTIMIZED"
            result["indicators"] = self.optimized_indicators
        return result

    def remove_symbol(self, symbol, *, permanent=False):
        return super().remove_symbol(symbol, permanent=permanent)


