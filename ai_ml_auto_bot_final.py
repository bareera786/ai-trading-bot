#!/usr/bin/env python3
"""
ULTIMATE PROFESSIONAL AI TRADING BOT - COMPREHENSIVE ENTERPRISE VERSION
WITH ALL FEATURES: Parallel Processing, 20 Core Indicators, Cycle Training, Manual Pair Addition
COMPLETE BUG-FIXED VERSION WITH ALL FEATURES RESTORED
ENHANCED WITH COMPREHENSIVE TRADE HISTORY & CRT MODULE
PROFESSIONAL PERSISTENCE SYSTEM ADDED
"""

AI_BOT_VERSION = "ULTIMATE_AI_TRADER_V4.0_CRT_COMPREHENSIVE_PERSISTENCE"

from flask import (
    Flask,
    render_template_string,
    jsonify,
    request,
    send_file,
    redirect,
    url_for,
    flash,
    session,
    make_response,
)
from flask_socketio import SocketIO, emit
import threading
import time
import pandas as pd
import numpy as np
import time
import threading
import os
import sys
import json
import random
import warnings
import logging
import math
import uuid
import subprocess
from decimal import Decimal, ROUND_DOWN
from logging.handlers import RotatingFileHandler
from collections import deque, defaultdict

warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
import requests
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import base64
import io
from io import BytesIO
from types import SimpleNamespace
from typing import Optional

from app.extensions import db, init_extensions, login_manager, socketio
from app.routes import register_blueprints
from app.assets import register_asset_helpers
from app.migrations import migrate_database
from app.services import (
    BOT_PROFILE,
    PROJECT_ROOT,
    BacktestManager,
    BinanceCredentialService,
    BinanceCredentialStore,
    BinanceLogManager,
    BinanceMarketDataHelper,
    BinanceFuturesTrader,
    ComprehensiveTradeHistory,
    FuturesManualService,
    FuturesMarketDataService,
    HealthReportService,
    LivePortfolioScheduler,
    MarketDataService,
    PersistenceScheduler,
    ProfessionalPersistence,
    RealBinanceTrader,
    RealtimeUpdateService,
    evaluate_health_payload,
)
from app.services.binance import _coerce_bool
from app.services.pathing import resolve_profile_path, safe_parse_datetime
from app.tasks import BackgroundTaskManager, ModelTrainingWorker, SelfImprovementWorker
from app.runtime.indicators import (
    BEST_INDICATORS,
    INDICATOR_SIGNAL_OPTIONS,
    IndicatorSelectionManager,
)
from app.runtime.background import build_background_runtime
from app.runtime.factories import (
    build_ml_runtime_services,
    build_trading_runtime_services,
)
from app.runtime.persistence import build_persistence_runtime
from app.runtime.payloads import build_ai_bot_context_payload
from app.runtime.services import build_service_runtime
from app.runtime.system import initialize_runtime_from_context
from app.runtime.symbols import (
    DEFAULT_DISABLED_SYMBOLS,
    DEFAULT_FUTURES_SYMBOLS,
    DEFAULT_HEALTH_SYMBOLS,
    DEFAULT_MARKET_CAP_WEIGHTS,
    DEFAULT_TOP_SYMBOLS,
    DISABLED_SYMBOLS,
    FUTURES_SYMBOLS,
    MARKET_CAP_WEIGHTS,
    SYMBOL_STATE_LOCK,
    TOP_SYMBOLS,
    attach_dashboard_data,
    clear_symbol_from_dashboard,
    disable_symbol,
    enable_symbol,
    get_active_trading_universe,
    get_all_known_symbols,
    get_disabled_symbols,
    get_enabled_symbols,
    is_symbol_disabled,
    load_symbol_state,
    parse_symbol_env,
    refresh_symbol_counters,
    save_symbol_state,
)
from app.runtime.symbols import normalize_symbol as _normalize_symbol

try:
    import talib  # type: ignore

    _TALIB_AVAILABLE = True
    _TALIB_IMPORT_ERROR = None
except ImportError as _talib_exc:
    _TALIB_AVAILABLE = False
    _TALIB_IMPORT_ERROR = str(_talib_exc)
    try:
        import pandas_ta as ta

        # Define fallback functions for common TA-Lib indicators using pandas-ta
        # Note: pandas-ta returns pandas Series; convert to numpy arrays to match TA-Lib behavior
        def _rsi_fallback(prices, timeperiod=14):
            return ta.rsi(pd.Series(prices), length=timeperiod).fillna(0).values

        def _macd_fallback(prices, fastperiod=12, slowperiod=26, signalperiod=9):
            macd_df = ta.macd(
                pd.Series(prices), fast=fastperiod, slow=slowperiod, signal=signalperiod
            )
            return (
                macd_df["MACD"].fillna(0).values,
                macd_df["SIGNAL"].fillna(0).values,
                macd_df["HIST"].fillna(0).values,
            )

        def _sma_fallback(prices, timeperiod=30):
            return ta.sma(pd.Series(prices), length=timeperiod).fillna(0).values

        def _stoch_fallback(
            high, low, close, fastk_period=5, slowk_period=3, slowd_period=3
        ):
            stoch_df = ta.stoch(
                pd.Series(high),
                pd.Series(low),
                pd.Series(close),
                k=fastk_period,
                d=slowk_period,
                smooth_k=slowd_period,
            )
            return (
                stoch_df["STOCHk"].fillna(0).values,
                stoch_df["STOCHd"].fillna(0).values,
            )

        def _adx_fallback(high, low, close, timeperiod=14):
            return (
                ta.adx(
                    pd.Series(high), pd.Series(low), pd.Series(close), length=timeperiod
                )
                .fillna(0)
                .values
            )

        def _atr_fallback(high, low, close, timeperiod=14):
            return (
                ta.atr(
                    pd.Series(high), pd.Series(low), pd.Series(close), length=timeperiod
                )
                .fillna(0)
                .values
            )

        def _obv_fallback(close, volume):
            return ta.obv(pd.Series(close), pd.Series(volume)).fillna(0).values

        def _bbands_fallback(close, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
            bb_df = ta.bbands(pd.Series(close), length=timeperiod, std=nbdevup)
            return (
                bb_df["BBU"].fillna(0).values,
                bb_df["BBM"].fillna(0).values,
                bb_df["BBL"].fillna(0).values,
            )

        def _ema_fallback(close, timeperiod=30):
            return ta.ema(pd.Series(close), length=timeperiod).fillna(0).values

        def _mfi_fallback(high, low, close, volume, timeperiod=14):
            return (
                ta.mfi(
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    pd.Series(volume),
                    length=timeperiod,
                )
                .fillna(0)
                .values
            )

        def _cci_fallback(high, low, close, timeperiod=14):
            return (
                ta.cci(
                    pd.Series(high), pd.Series(low), pd.Series(close), length=timeperiod
                )
                .fillna(0)
                .values
            )

        # Candlestick patterns (return last value as int, matching TA-Lib)
        def _cdlhammer_fallback(open, high, low, close):
            return (
                ta.cdl_pattern(
                    pd.Series(open),
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    name="hammer",
                )
                .fillna(0)
                .astype(int)
                .values
            )

        def _cdlengulfing_fallback(open, high, low, close):
            return (
                ta.cdl_pattern(
                    pd.Series(open),
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    name="engulfing",
                )
                .fillna(0)
                .astype(int)
                .values
            )

        def _cdlmorningstar_fallback(open, high, low, close):
            return (
                ta.cdl_pattern(
                    pd.Series(open),
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    name="morningstar",
                )
                .fillna(0)
                .astype(int)
                .values
            )

        def _cdlhangingman_fallback(open, high, low, close):
            return (
                ta.cdl_pattern(
                    pd.Series(open),
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    name="hangingman",
                )
                .fillna(0)
                .astype(int)
                .values
            )

        def _cdleveningstar_fallback(open, high, low, close):
            return (
                ta.cdl_pattern(
                    pd.Series(open),
                    pd.Series(high),
                    pd.Series(low),
                    pd.Series(close),
                    name="eveningstar",
                )
                .fillna(0)
                .astype(int)
                .values
            )

        # Assign to talib namespace for seamless fallback
        talib = SimpleNamespace()
        talib.RSI = _rsi_fallback
        talib.MACD = _macd_fallback
        talib.SMA = _sma_fallback
        talib.STOCH = _stoch_fallback
        talib.ADX = _adx_fallback
        talib.ATR = _atr_fallback
        talib.OBV = _obv_fallback
        talib.BBANDS = _bbands_fallback
        talib.EMA = _ema_fallback
        talib.MFI = _mfi_fallback
        talib.CCI = _cci_fallback
        talib.CDLHAMMER = _cdlhammer_fallback
        talib.CDLENGULFING = _cdlengulfing_fallback
        talib.CDLMORNINGSTAR = _cdlmorningstar_fallback
        talib.CDLHANGINGMAN = _cdlhangingman_fallback
        talib.CDLEVENINGSTAR = _cdleveningstar_fallback
    except ImportError:
        # pandas-ta not available, create basic fallback implementations
        import warnings

        warnings.warn(
            "pandas-ta not available, using basic TA-Lib fallbacks. Some indicators may be less accurate."
        )

        def _rsi_fallback(prices, timeperiod=14):
            """Basic RSI implementation using pandas"""
            if len(prices) < timeperiod + 1:
                return np.zeros(len(prices))

            prices_series = pd.Series(prices)
            delta = prices_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(0).values

        def _macd_fallback(prices, fastperiod=12, slowperiod=26, signalperiod=9):
            """Basic MACD implementation"""
            prices_series = pd.Series(prices)
            fast_ema = prices_series.ewm(span=fastperiod).mean()
            slow_ema = prices_series.ewm(span=slowperiod).mean()
            macd = fast_ema - slow_ema
            signal = macd.ewm(span=signalperiod).mean()
            hist = macd - signal
            return macd.fillna(0).values, signal.fillna(0).values, hist.fillna(0).values

        def _sma_fallback(prices, timeperiod=30):
            """Simple moving average"""
            return pd.Series(prices).rolling(window=timeperiod).mean().fillna(0).values

        def _stoch_fallback(
            high, low, close, fastk_period=5, slowk_period=3, slowd_period=3
        ):
            """Basic stochastic oscillator"""
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)

            lowest_low = low_series.rolling(window=fastk_period).min()
            highest_high = high_series.rolling(window=fastk_period).max()

            k = 100 * ((close_series - lowest_low) / (highest_high - lowest_low))
            d = k.rolling(window=slowd_period).mean()

            return k.fillna(0).values, d.fillna(0).values

        def _adx_fallback(high, low, close, timeperiod=14):
            """Basic ADX implementation (simplified)"""
            # This is a very basic ADX approximation
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)

            tr = pd.concat(
                [
                    high_series - low_series,
                    (high_series - close_series.shift(1)).abs(),
                    (low_series - close_series.shift(1)).abs(),
                ],
                axis=1,
            ).max(axis=1)

            atr = tr.rolling(window=timeperiod).mean()
            adx = (atr / close_series * 100).rolling(window=timeperiod).mean()
            return adx.fillna(0).values

        def _atr_fallback(high, low, close, timeperiod=14):
            """Average True Range"""
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)

            tr = pd.concat(
                [
                    high_series - low_series,
                    (high_series - close_series.shift(1)).abs(),
                    (low_series - close_series.shift(1)).abs(),
                ],
                axis=1,
            ).max(axis=1)

            return tr.rolling(window=timeperiod).mean().fillna(0).values

        def _obv_fallback(close, volume):
            """On Balance Volume"""
            close_series = pd.Series(close)
            volume_series = pd.Series(volume)

            obv = pd.Series(index=close_series.index, dtype=float)
            obv.iloc[0] = volume_series.iloc[0]

            for i in range(1, len(close_series)):
                if close_series.iloc[i] > close_series.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] + volume_series.iloc[i]
                elif close_series.iloc[i] < close_series.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] - volume_series.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i - 1]

            return obv.fillna(0).values

        def _bbands_fallback(close, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
            """Bollinger Bands"""
            close_series = pd.Series(close)
            sma = close_series.rolling(window=timeperiod).mean()
            std = close_series.rolling(window=timeperiod).std()

            upper = sma + (std * nbdevup)
            lower = sma - (std * nbdevdn)

            return upper.fillna(0).values, sma.fillna(0).values, lower.fillna(0).values

        def _ema_fallback(prices, timeperiod=30):
            """Exponential moving average"""
            return pd.Series(prices).ewm(span=timeperiod).mean().fillna(0).values

        def _mfi_fallback(high, low, close, volume, timeperiod=14):
            """Money Flow Index (simplified)"""
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)
            volume_series = pd.Series(volume)

            typical_price = (high_series + low_series + close_series) / 3
            money_flow = typical_price * volume_series

            # Simplified MFI calculation
            mfi = pd.Series(index=typical_price.index, dtype=float)
            for i in range(timeperiod, len(typical_price)):
                pos_flow = money_flow.iloc[i - timeperiod : i][
                    typical_price.iloc[i - timeperiod : i].diff() > 0
                ].sum()
                neg_flow = money_flow.iloc[i - timeperiod : i][
                    typical_price.iloc[i - timeperiod : i].diff() < 0
                ].sum()
                if neg_flow != 0:
                    mfi.iloc[i] = 100 - (100 / (1 + (pos_flow / neg_flow)))
                else:
                    mfi.iloc[i] = 100

            return mfi.fillna(0).values

        def _cci_fallback(high, low, close, timeperiod=14):
            """Commodity Channel Index (simplified)"""
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)

            typical_price = (high_series + low_series + close_series) / 3
            sma = typical_price.rolling(window=timeperiod).mean()
            mad = (typical_price - sma).abs().rolling(window=timeperiod).mean()

            cci = (typical_price - sma) / (0.015 * mad)
            return cci.fillna(0).values

        # Candlestick patterns (basic implementations)
        def _cdlhammer_fallback(open, high, low, close):
            """Basic hammer pattern detection"""
            open_series = pd.Series(open)
            high_series = pd.Series(high)
            low_series = pd.Series(low)
            close_series = pd.Series(close)

            body = (close_series - open_series).abs()
            lower_shadow = (
                pd.concat([open_series, close_series], axis=1).min(axis=1) - low_series
            )
            upper_shadow = high_series - pd.concat(
                [open_series, close_series], axis=1
            ).max(axis=1)

            hammer = ((lower_shadow > 2 * body) & (upper_shadow < body)).astype(int)
            return hammer.values

        def _cdlengulfing_fallback(open, high, low, close):
            """Basic engulfing pattern detection"""
            open_series = pd.Series(open)
            close_series = pd.Series(close)

            prev_body = (close_series.shift(1) - open_series.shift(1)).abs()
            curr_body = (close_series - open_series).abs()

            bullish_engulfing = (
                (close_series > open_series)
                & (close_series.shift(1) < open_series.shift(1))
                & (close_series > open_series.shift(1))
                & (open_series < close_series.shift(1))
            ).astype(int)
            bearish_engulfing = (
                (close_series < open_series)
                & (close_series.shift(1) > open_series.shift(1))
                & (close_series < open_series.shift(1))
                & (open_series > close_series.shift(1))
            ).astype(int)

            return (bullish_engulfing | bearish_engulfing).astype(int).values

        def _cdlmorningstar_fallback(open, high, low, close):
            """Basic morning star pattern (simplified)"""
            close_series = pd.Series(close)

            # Very basic morning star detection
            star = (
                (close_series.shift(2) < close_series.shift(1))
                & (close_series.shift(1) < close_series)
                & (close_series > close_series.shift(2))
            ).astype(int)
            return star.values

        def _cdlhangingman_fallback(open, high, low, close):
            """Basic hanging man pattern"""
            return _cdlhammer_fallback(open, high, low, close)  # Same logic as hammer

        def _cdleveningstar_fallback(open, high, low, close):
            """Basic evening star pattern (simplified)"""
            close_series = pd.Series(close)

            # Very basic evening star detection
            star = (
                (close_series.shift(2) > close_series.shift(1))
                & (close_series.shift(1) > close_series)
                & (close_series < close_series.shift(2))
            ).astype(int)
            return star.values

        # Assign to talib namespace for seamless fallback
        talib = SimpleNamespace()
        talib.RSI = _rsi_fallback
        talib.MACD = _macd_fallback
        talib.SMA = _sma_fallback
        talib.STOCH = _stoch_fallback
        talib.ADX = _adx_fallback
        talib.ATR = _atr_fallback
        talib.OBV = _obv_fallback
        talib.BBANDS = _bbands_fallback
        talib.EMA = _ema_fallback
        talib.MFI = _mfi_fallback
        talib.CCI = _cci_fallback
        talib.CDLHAMMER = _cdlhammer_fallback
        talib.CDLENGULFING = _cdlengulfing_fallback
        talib.CDLMORNINGSTAR = _cdlmorningstar_fallback
        talib.CDLHANGINGMAN = _cdlhangingman_fallback
        talib.CDLEVENINGSTAR = _cdleveningstar_fallback

from scipy import stats
from sklearn.ensemble import (
    RandomForestClassifier,
    VotingClassifier,
    GradientBoostingClassifier,
)
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
import joblib
from joblib import Parallel, delayed
import multiprocessing
import shutil
import atexit
import signal
from copy import deepcopy
import tempfile
import statistics as statistics_lib
from concurrent.futures import ThreadPoolExecutor

try:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException
except Exception:  # Optional dependency fallback for Binance REST client
    BinanceClient = None

    class BinanceAPIException(Exception):
        """Fallback Binance exception when python-binance is unavailable."""

        def __init__(self, message="python-binance library not installed"):
            super().__init__(message)


try:
    from binance import Client as BinanceFuturesClient
except Exception:  # Optional dependency fallback for dedicated futures client
    BinanceFuturesClient = None


# ==================== TRADING STRATEGIES SYSTEM ====================
class BaseStrategy:
    """Base class for all trading strategies with QFM enhancement"""

    def __init__(self, name, description, parameters=None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}
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

        except Exception as e:
            print(f"QFM enhancement error: {e}")
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

        # Enhance with QFM
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

        # This would integrate with the existing ML systems
        # For now, we'll use a simple rule-based approach enhanced by QFM
        signal = "HOLD"
        confidence = 0.0
        reason = "ML analysis in progress"

        # In a real implementation, this would call the ML prediction systems
        # For demonstration, we'll use a simple rule-based approach
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

        # Enhance with QFM for more sophisticated ML-like analysis
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

        # Calculate micro-trends
        price_changes = []
        for i in range(1, len(recent_prices)):
            change = (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
            price_changes.append(change)

        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0

        signal = "HOLD"
        confidence = 0.0
        reason = "No scalping opportunity"

        # Scalping conditions
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


class StrategyManager:
    def get_all_performance(self):
        """Get performance data for all strategies"""
        return self.get_strategy_performance()

    def initialize_adaptive_risk_management(self):
        """Initialize adaptive risk management system"""
        self.adaptive_risk = {
            "qfm_regime_risk_multipliers": {
                "trending_bull": 1.2,  # Increase risk in strong bull trends
                "trending_bear": 1.1,  # Moderate increase in bear trends
                "sideways": 0.7,  # Reduce risk in sideways markets
                "volatile": 0.6,  # Significantly reduce risk in high volatility
                "calm": 1.0,  # Normal risk in calm markets
            },
            "volatility_adjustments": {
                "low_volatility": 1.1,  # Slightly increase risk when volatility is low
                "normal_volatility": 1.0,  # Normal risk
                "high_volatility": 0.5,  # Reduce risk significantly when volatility is high
                "extreme_volatility": 0.3,  # Minimal risk in extreme volatility
            },
            "momentum_risk_multipliers": {
                "strong_bullish": 1.15,  # Increase risk on strong bullish momentum
                "moderate_bullish": 1.05,  # Slight increase on moderate bullish
                "neutral": 1.0,  # Normal risk
                "moderate_bearish": 0.9,  # Slight decrease on moderate bearish
                "strong_bearish": 0.8,  # Decrease risk on strong bearish momentum
            },
            "current_regime": "neutral",
            "regime_confidence": 0.0,
            "volatility_percentile": 50.0,
            "momentum_strength": 0.0,
            "risk_adjustment_history": [],
            "max_history_size": 1000,
        }

    def calculate_adaptive_position_size(
        self, symbol, base_position_size, market_data=None, strategy_name=None
    ):
        """Calculate position size with adaptive risk management based on QFM analysis"""
        if not market_data:
            return base_position_size

        # Get QFM features for risk assessment
        qfm_features = {}
        if self.qfm_engine:
            qfm_features = self.qfm_engine.compute_realtime_features(
                symbol, market_data[-1] if market_data else {}
            )

        if not qfm_features:
            return base_position_size

        # Determine current market regime
        regime = self._classify_market_regime(qfm_features)
        volatility_level = self._assess_volatility_level(qfm_features, symbol)
        momentum_strength = self._calculate_momentum_strength(qfm_features)

        # Calculate risk multipliers
        regime_multiplier = self.adaptive_risk["qfm_regime_risk_multipliers"].get(
            regime, 1.0
        )
        volatility_multiplier = self._get_volatility_multiplier(volatility_level)
        momentum_multiplier = self._get_momentum_multiplier(momentum_strength)

        # Combine multipliers with weights
        combined_multiplier = (
            regime_multiplier * 0.5
            + volatility_multiplier * 0.3  # 50% weight on regime
            + momentum_multiplier  # 30% weight on volatility
            * 0.2  # 20% weight on momentum
        )

        # Apply strategy-specific adjustments
        if strategy_name:
            strategy_adjustment = self._get_strategy_risk_adjustment(
                strategy_name, regime, volatility_level
            )
            combined_multiplier *= strategy_adjustment

        # Calculate adaptive position size
        adaptive_size = base_position_size * combined_multiplier

        # Apply bounds (prevent excessive risk)
        max_size_multiplier = 2.0  # Maximum 2x base position size
        min_size_multiplier = 0.2  # Minimum 20% of base position size

        adaptive_size = max(
            min_size_multiplier * base_position_size,
            min(max_size_multiplier * base_position_size, adaptive_size),
        )

        # Record adjustment for analytics
        adjustment_record = {
            "timestamp": time.time(),
            "symbol": symbol,
            "strategy": strategy_name,
            "base_size": base_position_size,
            "adaptive_size": adaptive_size,
            "regime": regime,
            "volatility_level": volatility_level,
            "momentum_strength": momentum_strength,
            "regime_multiplier": regime_multiplier,
            "volatility_multiplier": volatility_multiplier,
            "momentum_multiplier": momentum_multiplier,
            "combined_multiplier": combined_multiplier,
            "qfm_features": qfm_features,
        }

        self.adaptive_risk["risk_adjustment_history"].append(adjustment_record)

        # Maintain history size
        if (
            len(self.adaptive_risk["risk_adjustment_history"])
            > self.adaptive_risk["max_history_size"]
        ):
            self.adaptive_risk["risk_adjustment_history"] = self.adaptive_risk[
                "risk_adjustment_history"
            ][-self.adaptive_risk["max_history_size"] :]

        # Update current state
        self.adaptive_risk["current_regime"] = regime
        self.adaptive_risk["regime_confidence"] = qfm_features.get("regime_score", 0.5)
        self.adaptive_risk[
            "volatility_percentile"
        ] = self._calculate_volatility_percentile(qfm_features)
        self.adaptive_risk["momentum_strength"] = momentum_strength

        return adaptive_size

    def _classify_market_regime(self, qfm_features):
        """Classify current market regime based on QFM features"""
        velocity = abs(qfm_features.get("velocity", 0))
        acceleration = abs(qfm_features.get("acceleration", 0))
        jerk = abs(qfm_features.get("jerk", 0))
        regime_score = qfm_features.get("regime_score", 0.5)
        trend_confidence = qfm_features.get("trend_confidence", 0.5)

        # Regime classification logic
        if trend_confidence > 0.7 and velocity > 0.3:
            if qfm_features.get("velocity", 0) > 0:
                return "trending_bull"
            else:
                return "trending_bear"
        elif regime_score < 0.4 and velocity < 0.2:
            return "sideways"
        elif jerk > 0.5:
            return "volatile"
        else:
            return "calm"

    def _assess_volatility_level(self, qfm_features, symbol):
        """Assess volatility level based on QFM jerk and other metrics"""
        jerk = abs(qfm_features.get("jerk", 0))
        volume_pressure = abs(qfm_features.get("volume_pressure", 0))

        # Calculate volatility score
        volatility_score = (jerk * 0.6) + (volume_pressure * 0.4)

        # Classify volatility level
        if volatility_score > 0.7:
            return "extreme_volatility"
        elif volatility_score > 0.4:
            return "high_volatility"
        elif volatility_score > 0.2:
            return "normal_volatility"
        else:
            return "low_volatility"

    def _calculate_momentum_strength(self, qfm_features):
        """Calculate momentum strength from QFM features"""
        velocity = qfm_features.get("velocity", 0)
        acceleration = qfm_features.get("acceleration", 0)

        # Combined momentum score
        momentum_score = abs(velocity) + abs(acceleration)

        return momentum_score

    def _get_volatility_multiplier(self, volatility_level):
        """Get risk multiplier based on volatility level"""
        return self.adaptive_risk["volatility_adjustments"].get(volatility_level, 1.0)

    def _get_momentum_multiplier(self, momentum_strength):
        """Get risk multiplier based on momentum strength"""
        if momentum_strength > 1.0:
            return self.adaptive_risk["momentum_risk_multipliers"]["strong_bullish"]
        elif momentum_strength > 0.5:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bullish"]
        elif momentum_strength > 0.2:
            return self.adaptive_risk["momentum_risk_multipliers"]["neutral"]
        elif momentum_strength > 0.1:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bearish"]
        else:
            return self.adaptive_risk["momentum_risk_multipliers"]["strong_bearish"]

    def _get_strategy_risk_adjustment(self, strategy_name, regime, volatility_level):
        """Get strategy-specific risk adjustment"""
        # Different strategies have different risk profiles
        strategy_adjustments = {
            "scalping": {
                "volatile": 0.8,  # Reduce risk for scalping in volatile markets
                "sideways": 1.2,  # Increase risk for scalping in sideways markets
            },
            "trend_following": {
                "trending_bull": 1.3,  # Increase risk in trending markets
                "trending_bear": 1.3,
                "volatile": 0.7,  # Reduce risk in volatile markets
            },
            "mean_reversion": {
                "sideways": 1.2,  # Increase risk in sideways markets
                "volatile": 0.6,  # Reduce risk in volatile markets
                "trending_bull": 0.8,  # Reduce risk in strong trends
                "trending_bear": 0.8,
            },
            "momentum": {
                "volatile": 0.9,  # Slightly reduce risk in volatile markets
                "calm": 1.1,  # Slightly increase risk in calm markets
            },
        }

        strategy_adjustment = strategy_adjustments.get(strategy_name, {})
        return strategy_adjustment.get(
            regime, strategy_adjustment.get(volatility_level, 1.0)
        )

    def _calculate_volatility_percentile(self, qfm_features):
        """Calculate volatility percentile from QFM features"""
        jerk = abs(qfm_features.get("jerk", 0))

        # Simple percentile estimation based on jerk magnitude
        # In practice, this would use historical data
        if jerk > 0.8:
            return 95.0
        elif jerk > 0.6:
            return 85.0
        elif jerk > 0.4:
            return 70.0
        elif jerk > 0.2:
            return 50.0
        elif jerk > 0.1:
            return 30.0
        else:
            return 10.0

    def get_risk_management_status(self):
        """Get current risk management status and recommendations"""
        status = {
            "current_regime": self.adaptive_risk["current_regime"],
            "regime_confidence": self.adaptive_risk["regime_confidence"],
            "volatility_percentile": self.adaptive_risk["volatility_percentile"],
            "momentum_strength": self.adaptive_risk["momentum_strength"],
            "risk_multipliers": {
                "regime": self.adaptive_risk["qfm_regime_risk_multipliers"].get(
                    self.adaptive_risk["current_regime"], 1.0
                ),
                "volatility": self._get_volatility_multiplier(
                    self._assess_volatility_level_from_current_state()
                ),
                "momentum": self._get_momentum_multiplier(
                    self.adaptive_risk["momentum_strength"]
                ),
            },
            "recent_adjustments": self.adaptive_risk["risk_adjustment_history"][-10:]
            if self.adaptive_risk["risk_adjustment_history"]
            else [],
            "recommendations": self._generate_risk_recommendations(),
        }

        return status

    def _assess_volatility_level_from_current_state(self):
        """Assess volatility level from current state"""
        percentile = self.adaptive_risk["volatility_percentile"]

        if percentile > 90:
            return "extreme_volatility"
        elif percentile > 75:
            return "high_volatility"
        elif percentile > 25:
            return "normal_volatility"
        else:
            return "low_volatility"

    def _generate_risk_recommendations(self):
        """Generate risk management recommendations"""
        recommendations = []

        regime = self.adaptive_risk["current_regime"]
        volatility_percentile = self.adaptive_risk["volatility_percentile"]
        momentum_strength = self.adaptive_risk["momentum_strength"]

        # Regime-based recommendations
        if regime == "volatile":
            recommendations.append(
                {
                    "type": "regime_risk",
                    "priority": "high",
                    "message": "High volatility detected - reducing position sizes by 40%",
                    "action": "reduce_position_sizes",
                }
            )
        elif regime in ["trending_bull", "trending_bear"]:
            recommendations.append(
                {
                    "type": "regime_opportunity",
                    "priority": "medium",
                    "message": f'Strong {regime.split("_")[1]} trend detected - increasing position sizes by 15-20%',
                    "action": "increase_position_sizes",
                }
            )

        # Volatility-based recommendations
        if volatility_percentile > 80:
            recommendations.append(
                {
                    "type": "volatility_alert",
                    "priority": "high",
                    "message": f"Volatility at {volatility_percentile:.1f}th percentile - implement strict risk controls",
                    "action": "implement_strict_risk_controls",
                }
            )

        # Momentum-based recommendations
        if momentum_strength > 1.0:
            recommendations.append(
                {
                    "type": "momentum_opportunity",
                    "priority": "medium",
                    "message": f"Strong momentum detected (strength: {momentum_strength:.2f}) - consider increasing risk",
                    "action": "increase_risk_exposure",
                }
            )

        return recommendations

    def update_strategy_risk_parameters(self, strategy_name, risk_parameters):
        """Update risk parameters for a specific strategy"""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        strategy = self.strategies[strategy_name]

        # Update risk-related parameters
        valid_params = [
            "stop_loss_pct",
            "take_profit_pct",
            "max_position_size",
            "risk_per_trade",
        ]

        for param, value in risk_parameters.items():
            if param in valid_params:
                if param == "stop_loss_pct" and 0.005 <= value <= 0.1:  # 0.5% to 10%
                    strategy.parameters[param] = value
                elif param == "take_profit_pct" and 0.01 <= value <= 0.2:  # 1% to 20%
                    strategy.parameters[param] = value
                elif param == "max_position_size" and 0.01 <= value <= 0.5:  # 1% to 50%
                    strategy.parameters[param] = value
                elif param == "risk_per_trade" and 0.005 <= value <= 0.05:  # 0.5% to 5%
                    strategy.parameters[param] = value

        return {
            "status": "updated",
            "strategy": strategy_name,
            "updated_parameters": {
                k: v for k, v in risk_parameters.items() if k in valid_params
            },
        }

    def get_strategy_risk_profile(self, strategy_name):
        """Get risk profile for a specific strategy"""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        strategy = self.strategies[strategy_name]
        params = strategy.parameters

        risk_profile = {
            "strategy_name": strategy_name,
            "risk_parameters": {
                "stop_loss_pct": params.get("stop_loss_pct", 0.02),
                "take_profit_pct": params.get("take_profit_pct", 0.04),
                "max_position_size": params.get("max_position_size", 0.1),
                "risk_per_trade": params.get("risk_per_trade", 0.01),
                "confidence_threshold": params.get("confidence_threshold", 0.5),
            },
            "risk_category": self._categorize_strategy_risk(strategy_name),
            "recommended_adjustments": self._get_strategy_risk_recommendations(
                strategy_name
            ),
        }

        return risk_profile

    def _categorize_strategy_risk(self, strategy_name):
        """Categorize strategy risk level"""
        risk_categories = {
            "scalping": "high_risk",  # Quick trades, high frequency
            "momentum": "medium_risk",  # Momentum can reverse quickly
            "trend_following": "medium_risk",  # False signals possible
            "breakout": "high_risk",  # Breakouts can fail
            "mean_reversion": "medium_risk",  # Timing critical
            "arbitrage": "low_risk",  # Statistical edge
            "ml_based": "variable_risk",  # Depends on model accuracy
        }

        return risk_categories.get(strategy_name, "medium_risk")

    def _get_strategy_risk_recommendations(self, strategy_name):
        """Get risk management recommendations for a strategy"""
        recommendations = []

        strategy = self.strategies[strategy_name]
        params = strategy.parameters

        # Check stop loss
        stop_loss = params.get("stop_loss_pct", 0.02)
        if stop_loss > 0.05:
            recommendations.append(
                "Consider tightening stop loss for better risk control"
            )
        elif stop_loss < 0.01:
            recommendations.append(
                "Stop loss may be too tight, consider increasing to reduce false exits"
            )

        # Check take profit
        take_profit = params.get("take_profit_pct", 0.04)
        if take_profit > 0.1:
            recommendations.append("Take profit target may be too ambitious")
        elif take_profit < 0.02:
            recommendations.append("Take profit target may be too conservative")

        # Check position size
        max_position = params.get("max_position_size", 0.1)
        if max_position > 0.2:
            recommendations.append(
                "Maximum position size is high, consider reducing for risk control"
            )
        elif max_position < 0.05:
            recommendations.append(
                "Maximum position size is conservative, consider increasing for better returns"
            )

        return recommendations

    def initialize_user_dashboard_features(self):
        """Initialize user-specific dashboard features"""
        self.user_dashboards = {
            "custom_strategies": {},
            "qfm_parameter_profiles": {},
            "performance_dashboards": {},
            "alert_preferences": {},
            "custom_analytics": {},
        }

    def create_user_strategy_profile(
        self, user_id, strategy_name, custom_parameters=None
    ):
        """Create a user-specific strategy profile with custom parameters"""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        base_strategy = self.strategies[strategy_name]

        # Create user profile
        user_profile = {
            "user_id": user_id,
            "base_strategy": strategy_name,
            "custom_parameters": custom_parameters or base_strategy.parameters.copy(),
            "qfm_enhancements": {
                "velocity_weight": 1.0,
                "acceleration_weight": 1.0,
                "jerk_weight": 1.0,
                "regime_sensitivity": 1.0,
                "trend_confidence_threshold": 0.6,
            },
            "performance_targets": {
                "target_win_rate": 60.0,
                "target_daily_pnl": 100.0,
                "max_drawdown_limit": 0.05,
                "risk_per_trade": 0.02,
            },
            "created_at": time.time(),
            "last_modified": time.time(),
            "is_active": True,
        }

        # Store user profile
        if user_id not in self.user_dashboards["custom_strategies"]:
            self.user_dashboards["custom_strategies"][user_id] = {}

        self.user_dashboards["custom_strategies"][user_id][strategy_name] = user_profile

        return {"status": "created", "profile": user_profile}

    def update_user_strategy_parameters(
        self, user_id, strategy_name, parameter_updates
    ):
        """Update user-specific strategy parameters"""
        if user_id not in self.user_dashboards["custom_strategies"]:
            return {"error": f"No custom strategies found for user {user_id}"}

        user_strategies = self.user_dashboards["custom_strategies"][user_id]

        if strategy_name not in user_strategies:
            return {
                "error": f"Custom strategy {strategy_name} not found for user {user_id}"
            }

        profile = user_strategies[strategy_name]

        # Validate parameter updates
        validated_updates = {}
        for param, value in parameter_updates.items():
            if self._validate_strategy_parameter(param, value):
                validated_updates[param] = value
            else:
                return {"error": f"Invalid parameter value for {param}: {value}"}

        # Apply updates
        profile["custom_parameters"].update(validated_updates)
        profile["last_modified"] = time.time()

        return {"status": "updated", "updated_parameters": validated_updates}

    def _validate_strategy_parameter(self, parameter_name, value):
        """Validate strategy parameter values"""
        parameter_bounds = {
            "confidence_threshold": (0.1, 0.9),
            "risk_multiplier": (0.1, 3.0),
            "trend_strength_threshold": (0.1, 0.9),
            "short_period": (5, 50),
            "long_period": (20, 200),
            "deviation_threshold": (1.0, 4.0),
            "momentum_period": (5, 50),
            "reversion_speed": (0.5, 2.0),
        }

        if parameter_name not in parameter_bounds:
            return isinstance(value, (int, float)) and value > 0

        min_val, max_val = parameter_bounds[parameter_name]
        return isinstance(value, (int, float)) and min_val <= value <= max_val

    def create_qfm_parameter_profile(self, user_id, profile_name, qfm_parameters):
        """Create a user-specific QFM parameter profile"""
        profile = {
            "profile_name": profile_name,
            "user_id": user_id,
            "parameters": {
                "velocity_sensitivity": qfm_parameters.get("velocity_sensitivity", 1.0),
                "acceleration_sensitivity": qfm_parameters.get(
                    "acceleration_sensitivity", 1.0
                ),
                "jerk_sensitivity": qfm_parameters.get("jerk_sensitivity", 1.0),
                "volume_pressure_weight": qfm_parameters.get(
                    "volume_pressure_weight", 1.0
                ),
                "trend_confidence_weight": qfm_parameters.get(
                    "trend_confidence_weight", 1.0
                ),
                "regime_score_threshold": qfm_parameters.get(
                    "regime_score_threshold", 0.5
                ),
                "entropy_threshold": qfm_parameters.get("entropy_threshold", 0.7),
                "adaptive_learning_rate": qfm_parameters.get(
                    "adaptive_learning_rate", 0.01
                ),
            },
            "performance_history": [],
            "created_at": time.time(),
            "last_used": time.time(),
        }

        if user_id not in self.user_dashboards["qfm_parameter_profiles"]:
            self.user_dashboards["qfm_parameter_profiles"][user_id] = {}

        self.user_dashboards["qfm_parameter_profiles"][user_id][profile_name] = profile

        return {"status": "created", "profile": profile}

    def get_user_dashboard_data(self, user_id, dashboard_type="overview"):
        """Get personalized dashboard data for a user"""
        dashboard_data = {
            "user_id": user_id,
            "timestamp": time.time(),
            "dashboard_type": dashboard_type,
        }

        # Custom strategies
        user_strategies = self.user_dashboards["custom_strategies"].get(user_id, {})
        dashboard_data["custom_strategies"] = {}

        for strategy_name, profile in user_strategies.items():
            if profile["is_active"]:
                # Get current performance
                base_perf = self.strategy_performance.get(strategy_name, {})
                custom_perf = self._calculate_custom_strategy_performance(
                    user_id, strategy_name
                )

                dashboard_data["custom_strategies"][strategy_name] = {
                    "parameters": profile["custom_parameters"],
                    "qfm_enhancements": profile["qfm_enhancements"],
                    "performance": custom_perf,
                    "base_performance": base_perf,
                    "performance_targets": profile["performance_targets"],
                    "last_modified": profile["last_modified"],
                }

        # QFM parameter profiles
        qfm_profiles = self.user_dashboards["qfm_parameter_profiles"].get(user_id, {})
        dashboard_data["qfm_profiles"] = list(qfm_profiles.keys())

        # Performance analytics
        if dashboard_type in ["overview", "performance"]:
            dashboard_data[
                "performance_analytics"
            ] = self._generate_user_performance_analytics(user_id)

        # Recommendations
        if dashboard_type in ["overview", "recommendations"]:
            dashboard_data["recommendations"] = self._generate_user_recommendations(
                user_id
            )

        # Alerts
        dashboard_data["alerts"] = self._get_user_alerts(user_id)

        return dashboard_data

    def _calculate_custom_strategy_performance(self, user_id, strategy_name):
        """Calculate performance for user's custom strategy"""
        # This would track performance of user's custom parameter settings
        # For now, return base strategy performance with custom adjustments
        base_perf = self.strategy_performance.get(strategy_name, {}).copy()

        # Apply custom adjustments based on user parameters
        user_profile = (
            self.user_dashboards["custom_strategies"]
            .get(user_id, {})
            .get(strategy_name)
        )
        if user_profile:
            # Simulate performance adjustment based on parameter optimization
            param_score = self._calculate_parameter_optimization_score(
                user_profile["custom_parameters"]
            )
            adjustment_factor = 1 + (param_score - 0.5) * 0.2  # ±20% adjustment

            base_perf["adjusted_win_rate"] = min(
                100, base_perf.get("win_rate", 0) * adjustment_factor
            )
            base_perf["parameter_score"] = param_score

        return base_perf

    def _calculate_parameter_optimization_score(self, parameters):
        """Calculate how optimal the parameter settings are"""
        # Simple heuristic scoring based on parameter values
        score = 0
        total_params = 0

        # Confidence threshold scoring (optimal around 0.6-0.7)
        if "confidence_threshold" in parameters:
            threshold = parameters["confidence_threshold"]
            optimal_score = 1 - abs(threshold - 0.65) / 0.35  # Peak at 0.65
            score += optimal_score
            total_params += 1

        # Risk multiplier scoring (optimal around 1.0-1.5)
        if "risk_multiplier" in parameters:
            risk_mult = parameters["risk_multiplier"]
            optimal_score = 1 - abs(risk_mult - 1.25) / 0.75
            score += optimal_score
            total_params += 1

        # Trend strength threshold scoring (optimal around 0.6-0.7)
        if "trend_strength_threshold" in parameters:
            trend_thresh = parameters["trend_strength_threshold"]
            optimal_score = 1 - abs(trend_thresh - 0.65) / 0.35
            score += optimal_score
            total_params += 1

        return score / total_params if total_params > 0 else 0.5

    def _generate_user_performance_analytics(self, user_id):
        """Generate personalized performance analytics for user"""
        analytics = {
            "portfolio_overview": {},
            "strategy_performance": {},
            "qfm_effectiveness": {},
            "risk_metrics": {},
        }

        user_strategies = self.user_dashboards["custom_strategies"].get(user_id, {})

        if user_strategies:
            total_pnl = 0
            total_trades = 0
            winning_trades = 0

            for strategy_name, profile in user_strategies.items():
                if profile["is_active"]:
                    perf = self._calculate_custom_strategy_performance(
                        user_id, strategy_name
                    )
                    analytics["strategy_performance"][strategy_name] = perf

                    total_pnl += perf.get("total_pnl", 0)
                    total_trades += perf.get("total_trades", 0)
                    winning_trades += int(
                        (perf.get("adjusted_win_rate", perf.get("win_rate", 0)) / 100)
                        * perf.get("total_trades", 0)
                    )

            analytics["portfolio_overview"] = {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "win_rate": (winning_trades / total_trades * 100)
                if total_trades > 0
                else 0,
                "active_strategies": len(
                    [s for s in user_strategies.values() if s["is_active"]]
                ),
            }

        # QFM effectiveness analysis
        qfm_profiles = self.user_dashboards["qfm_parameter_profiles"].get(user_id, {})
        if qfm_profiles:
            analytics["qfm_effectiveness"] = self._analyze_qfm_profile_effectiveness(
                qfm_profiles
            )

        return analytics

    def _analyze_qfm_profile_effectiveness(self, qfm_profiles):
        """Analyze effectiveness of user's QFM parameter profiles"""
        effectiveness = {}

        for profile_name, profile in qfm_profiles.items():
            # Calculate effectiveness based on parameter balance
            params = profile["parameters"]
            balance_score = 1 - np.std(
                list(params.values())
            )  # Lower variance = better balance
            sensitivity_score = np.mean(
                [
                    params.get("velocity_sensitivity", 1.0),
                    params.get("acceleration_sensitivity", 1.0),
                    params.get("jerk_sensitivity", 1.0),
                ]
            )

            effectiveness[profile_name] = {
                "balance_score": balance_score,
                "sensitivity_score": sensitivity_score,
                "overall_effectiveness": (balance_score + sensitivity_score) / 2,
                "last_used": profile["last_used"],
            }

        return effectiveness

    def _generate_user_recommendations(self, user_id):
        """Generate personalized recommendations for user"""
        recommendations = []

        user_strategies = self.user_dashboards["custom_strategies"].get(user_id, {})

        for strategy_name, profile in user_strategies.items():
            if not profile["is_active"]:
                continue

            perf = self._calculate_custom_strategy_performance(user_id, strategy_name)

            # Parameter optimization recommendations
            param_score = perf.get("parameter_score", 0.5)
            if param_score < 0.6:
                recommendations.append(
                    {
                        "type": "parameter_optimization",
                        "strategy": strategy_name,
                        "message": f"Consider optimizing parameters for {strategy_name} (current score: {param_score:.2f})",
                        "priority": "medium",
                    }
                )

            # Performance-based recommendations
            adjusted_win_rate = perf.get("adjusted_win_rate", perf.get("win_rate", 0))
            if adjusted_win_rate < 50:
                recommendations.append(
                    {
                        "type": "performance_improvement",
                        "strategy": strategy_name,
                        "message": f"{strategy_name} win rate could be improved with QFM tuning",
                        "priority": "high",
                    }
                )

        # QFM profile recommendations
        qfm_profiles = self.user_dashboards["qfm_parameter_profiles"].get(user_id, {})
        if len(qfm_profiles) < 2:
            recommendations.append(
                {
                    "type": "qfm_profiles",
                    "message": "Consider creating multiple QFM parameter profiles for different market conditions",
                    "priority": "low",
                }
            )

        return recommendations

    def _get_user_alerts(self, user_id):
        """Get alerts for user based on their preferences and strategy performance"""
        alerts = []

        user_strategies = self.user_dashboards["custom_strategies"].get(user_id, {})

        for strategy_name, profile in user_strategies.items():
            if not profile["is_active"]:
                continue

            perf = self._calculate_custom_strategy_performance(user_id, strategy_name)
            targets = profile["performance_targets"]

            # Check performance targets
            current_win_rate = perf.get("adjusted_win_rate", perf.get("win_rate", 0))
            if current_win_rate < targets["target_win_rate"] * 0.8:  # 20% below target
                alerts.append(
                    {
                        "type": "performance_alert",
                        "strategy": strategy_name,
                        "message": f"{strategy_name} win rate ({current_win_rate:.1f}%) significantly below target",
                        "severity": "high",
                    }
                )

            # Check drawdown limits
            # This would require tracking actual drawdown
            max_drawdown = perf.get("max_drawdown", 0)
            if max_drawdown > targets["max_drawdown_limit"]:
                alerts.append(
                    {
                        "type": "risk_alert",
                        "strategy": strategy_name,
                        "message": f"{strategy_name} drawdown ({max_drawdown:.1%}) exceeds limit",
                        "severity": "critical",
                    }
                )

        return alerts

    def export_user_dashboard_config(self, user_id):
        """Export user's dashboard configuration for backup/sharing"""
        config = {
            "user_id": user_id,
            "export_timestamp": time.time(),
            "custom_strategies": self.user_dashboards["custom_strategies"].get(
                user_id, {}
            ),
            "qfm_parameter_profiles": self.user_dashboards[
                "qfm_parameter_profiles"
            ].get(user_id, {}),
            "alert_preferences": self.user_dashboards["alert_preferences"].get(
                user_id, {}
            ),
            "custom_analytics": self.user_dashboards["custom_analytics"].get(
                user_id, {}
            ),
        }

        return config

    def import_user_dashboard_config(self, user_id, config):
        """Import user's dashboard configuration"""
        if config.get("user_id") != user_id:
            return {"error": "Configuration user_id mismatch"}

        # Import custom strategies
        if "custom_strategies" in config:
            self.user_dashboards["custom_strategies"][user_id] = config[
                "custom_strategies"
            ]

        # Import QFM profiles
        if "qfm_parameter_profiles" in config:
            self.user_dashboards["qfm_parameter_profiles"][user_id] = config[
                "qfm_parameter_profiles"
            ]

        # Import other settings
        for key in ["alert_preferences", "custom_analytics"]:
            if key in config:
                self.user_dashboards[key][user_id] = config[key]

        return {"status": "imported", "imported_keys": list(config.keys())}

    def initialize_ml_feedback_system(self):
        """Initialize ML feedback system for continuous strategy improvement"""
        self.ml_feedback = {
            "performance_history": [],
            "parameter_history": {},
            "qfm_correlations": {},
            "learning_rate": 0.01,
            "adaptation_threshold": 0.05,  # Minimum improvement threshold
            "max_history_size": 1000,
            "feature_importance": {},
            "last_adaptation": {},
        }

        # Initialize parameter history for each strategy
        for strategy_name in self.strategies:
            self.ml_feedback["parameter_history"][strategy_name] = []

    def update_ml_feedback(self, strategy_name, trade_result, qfm_features=None):
        """Update ML feedback system with trade results and QFM features"""
        if strategy_name not in self.strategies:
            return

        strategy = self.strategies[strategy_name]

        # Record performance data
        performance_entry = {
            "timestamp": time.time(),
            "strategy": strategy_name,
            "pnl": trade_result.get("pnl", 0),
            "win": trade_result.get("pnl", 0) > 0,
            "confidence": trade_result.get("confidence", 0),
            "parameters": strategy.parameters.copy(),
            "qfm_features": qfm_features or {},
        }

        self.ml_feedback["performance_history"].append(performance_entry)

        # Maintain history size limit
        if (
            len(self.ml_feedback["performance_history"])
            > self.ml_feedback["max_history_size"]
        ):
            self.ml_feedback["performance_history"] = self.ml_feedback[
                "performance_history"
            ][-self.ml_feedback["max_history_size"] :]

        # Update parameter history
        param_entry = {
            "timestamp": time.time(),
            "parameters": strategy.parameters.copy(),
            "performance_score": self._calculate_performance_score(strategy_name),
        }
        self.ml_feedback["parameter_history"][strategy_name].append(param_entry)

        # Keep only recent parameter history
        if len(self.ml_feedback["parameter_history"][strategy_name]) > 50:
            self.ml_feedback["parameter_history"][strategy_name] = self.ml_feedback[
                "parameter_history"
            ][strategy_name][-50:]

        # Update QFM correlations
        if qfm_features:
            self._update_qfm_correlations(strategy_name, trade_result, qfm_features)

        # Check if adaptation is needed
        if self._should_adapt_parameters(strategy_name):
            self._adapt_strategy_parameters(strategy_name)

    def _calculate_performance_score(self, strategy_name, window=20):
        """Calculate performance score for a strategy over recent trades"""
        history = self.ml_feedback["performance_history"]
        recent_trades = [h for h in history if h["strategy"] == strategy_name][-window:]

        if not recent_trades:
            return 0.0

        # Calculate win rate
        wins = sum(1 for t in recent_trades if t["win"])
        win_rate = wins / len(recent_trades)

        # Calculate average P&L
        avg_pnl = np.mean([t["pnl"] for t in recent_trades])

        # Calculate Sharpe-like ratio (risk-adjusted returns)
        pnl_std = np.std([t["pnl"] for t in recent_trades])
        sharpe_ratio = avg_pnl / pnl_std if pnl_std > 0 else 0

        # Composite score
        score = win_rate * 0.4 + sharpe_ratio * 0.4 + (avg_pnl / 100) * 0.2
        return max(0, min(1, score))  # Normalize to [0,1]

    def _update_qfm_correlations(self, strategy_name, trade_result, qfm_features):
        """Update correlations between QFM features and trading performance"""
        pnl = trade_result.get("pnl", 0)

        for feature_name, feature_value in qfm_features.items():
            if feature_name not in self.ml_feedback["qfm_correlations"]:
                self.ml_feedback["qfm_correlations"][feature_name] = []

            self.ml_feedback["qfm_correlations"][feature_name].append(
                {
                    "strategy": strategy_name,
                    "feature_value": feature_value,
                    "pnl": pnl,
                    "timestamp": time.time(),
                }
            )

            # Keep only recent correlations
            if len(self.ml_feedback["qfm_correlations"][feature_name]) > 200:
                self.ml_feedback["qfm_correlations"][feature_name] = self.ml_feedback[
                    "qfm_correlations"
                ][feature_name][-200:]

    def _should_adapt_parameters(self, strategy_name):
        """Determine if strategy parameters should be adapted based on performance"""
        current_score = self._calculate_performance_score(strategy_name)
        last_adaptation = self.ml_feedback["last_adaptation"].get(strategy_name, 0)
        time_since_adaptation = time.time() - last_adaptation

        # Adapt if performance is poor and enough time has passed (at least 1 hour)
        if current_score < 0.4 and time_since_adaptation > 3600:
            return True

        # Adapt if performance has declined significantly from recent peak
        param_history = self.ml_feedback["parameter_history"].get(strategy_name, [])
        if len(param_history) >= 5:
            recent_scores = [p["performance_score"] for p in param_history[-5:]]
            peak_score = max(recent_scores)
            if peak_score - current_score > self.ml_feedback["adaptation_threshold"]:
                return True

        return False

    def _adapt_strategy_parameters(self, strategy_name):
        """Adapt strategy parameters using ML feedback"""
        strategy = self.strategies[strategy_name]
        param_history = self.ml_feedback["parameter_history"].get(strategy_name, [])

        if len(param_history) < 3:
            return  # Need minimum history for adaptation

        # Find best performing parameter sets
        scored_params = [
            (p["performance_score"], p["parameters"]) for p in param_history
        ]
        scored_params.sort(reverse=True)  # Best first

        # Use weighted average of top 3 parameter sets
        top_params = scored_params[:3]
        total_score = sum(score for score, _ in top_params)

        if total_score == 0:
            return

        # Calculate weighted average parameters
        adapted_params = {}
        param_keys = set()
        for _, params in top_params:
            param_keys.update(params.keys())

        for param_key in param_keys:
            weighted_sum = 0
            total_weight = 0

            for score, params in top_params:
                if param_key in params:
                    weight = score / total_score
                    weighted_sum += params[param_key] * weight
                    total_weight += weight

            if total_weight > 0:
                adapted_params[param_key] = weighted_sum / total_weight

        # Apply adapted parameters with learning rate
        learning_rate = self.ml_feedback["learning_rate"]
        for param_key, new_value in adapted_params.items():
            current_value = strategy.parameters.get(param_key, new_value)
            adapted_value = current_value + (new_value - current_value) * learning_rate

            # Apply bounds based on parameter type
            if "threshold" in param_key:
                adapted_value = max(0.1, min(0.9, adapted_value))
            elif "multiplier" in param_key or "risk" in param_key:
                adapted_value = max(0.1, min(3.0, adapted_value))
            elif "period" in param_key:
                adapted_value = max(5, min(100, int(adapted_value)))

            strategy.parameters[param_key] = adapted_value

        self.ml_feedback["last_adaptation"][strategy_name] = time.time()

        log_component_event(
            "STRATEGY_ADAPTATION",
            f"Adapted parameters for {strategy_name}",
            details={"adapted_params": adapted_params},
        )

    def get_ml_feedback_insights(self, strategy_name=None):
        """Get ML feedback insights and recommendations"""
        insights = {}

        if strategy_name:
            strategies = [strategy_name]
        else:
            strategies = list(self.strategies.keys())

        for strat_name in strategies:
            if strat_name not in self.ml_feedback["parameter_history"]:
                continue

            param_history = self.ml_feedback["parameter_history"][strat_name]
            performance_history = [
                h
                for h in self.ml_feedback["performance_history"]
                if h["strategy"] == strat_name
            ]

            if not param_history or not performance_history:
                continue

            # Calculate trends
            recent_scores = [p["performance_score"] for p in param_history[-10:]]
            score_trend = (
                np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                if len(recent_scores) > 1
                else 0
            )

            # Find best parameters
            best_params = max(param_history, key=lambda x: x["performance_score"])[
                "parameters"
            ]

            # Calculate QFM feature importance
            qfm_importance = self._calculate_qfm_feature_importance(strat_name)

            insights[strat_name] = {
                "current_performance_score": self._calculate_performance_score(
                    strat_name
                ),
                "performance_trend": score_trend,
                "best_parameters": best_params,
                "total_trades_analyzed": len(performance_history),
                "qfm_feature_importance": qfm_importance,
                "last_adaptation": self.ml_feedback["last_adaptation"].get(
                    strat_name, 0
                ),
                "recommendations": self._generate_ml_recommendations(
                    strat_name, score_trend, qfm_importance
                ),
            }

        return insights

    def _calculate_qfm_feature_importance(self, strategy_name):
        """Calculate importance of QFM features for strategy performance"""
        feature_importance = {}

        for feature_name, correlations in self.ml_feedback["qfm_correlations"].items():
            strategy_correlations = [
                c for c in correlations if c["strategy"] == strategy_name
            ]

            if len(strategy_correlations) < 10:
                continue

            # Calculate correlation between feature value and P&L
            feature_values = [c["feature_value"] for c in strategy_correlations]
            pnl_values = [c["pnl"] for c in strategy_correlations]

            try:
                correlation = np.corrcoef(feature_values, pnl_values)[0, 1]
                if not np.isnan(correlation):
                    feature_importance[feature_name] = abs(correlation)
            except:
                continue

        # Sort by importance
        return dict(
            sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        )

    def _generate_ml_recommendations(self, strategy_name, score_trend, qfm_importance):
        """Generate ML-based recommendations for strategy improvement"""
        recommendations = []

        # Performance trend analysis
        if score_trend < -0.01:
            recommendations.append(
                "Performance declining - consider parameter adaptation"
            )
        elif score_trend > 0.01:
            recommendations.append(
                "Performance improving - current parameters working well"
            )

        # QFM feature analysis
        if qfm_importance:
            top_features = list(qfm_importance.keys())[:3]
            if top_features:
                recommendations.append(
                    f"Focus on QFM features: {', '.join(top_features)}"
                )

        # Strategy-specific recommendations
        strategy = self.strategies[strategy_name]
        current_win_rate = self.strategy_performance.get(strategy_name, {}).get(
            "win_rate", 0
        )

        if current_win_rate < 40:
            recommendations.append(
                "Low win rate - consider increasing confidence thresholds"
            )
        elif current_win_rate > 70:
            recommendations.append(
                "High win rate - consider optimizing for higher returns"
            )

        return recommendations

    def run_continuous_improvement(self):
        """Run continuous improvement cycle for all strategies"""
        improvement_results = {}

        for strategy_name in self.strategies:
            try:
                # Check if improvement is needed
                current_score = self._calculate_performance_score(strategy_name)
                last_improvement = self.ml_feedback.get("last_improvement", {}).get(
                    strategy_name, 0
                )
                time_since_improvement = time.time() - last_improvement

                if current_score < 0.5 and time_since_improvement > 7200:  # 2 hours
                    # Run optimization
                    optimization_result = self.optimize_strategies_with_qfm()
                    if (
                        strategy_name in optimization_result
                        and optimization_result[strategy_name]["status"] == "optimized"
                    ):
                        improvement_results[strategy_name] = {
                            "action": "optimized",
                            "result": optimization_result[strategy_name],
                        }
                        self.ml_feedback.setdefault("last_improvement", {})[
                            strategy_name
                        ] = time.time()

                    # Run A/B test if no recent tests
                    last_ab_test = self.ml_feedback.get("last_ab_test", {}).get(
                        strategy_name, 0
                    )
                    if time.time() - last_ab_test > 86400:  # 24 hours
                        ab_result = self.run_ab_testing(strategy_name)
                        if "test_id" in ab_result:
                            improvement_results[strategy_name] = {
                                "action": "ab_test_started",
                                "result": ab_result,
                            }
                            self.ml_feedback.setdefault("last_ab_test", {})[
                                strategy_name
                            ] = time.time()

                else:
                    improvement_results[strategy_name] = {
                        "action": "no_action",
                        "reason": "performance_satisfactory"
                        if current_score >= 0.5
                        else "recently_improved",
                    }

            except Exception as e:
                improvement_results[strategy_name] = {
                    "action": "error",
                    "error": str(e),
                }

        return improvement_results

    def optimize_strategies_with_qfm(self, market_data=None, performance_window=100):
        """Optimize strategy parameters using QFM analytics and performance feedback"""
        optimization_results = {}

        for strategy_name, strategy in self.strategies.items():
            try:
                # Get current performance metrics
                perf_data = self.strategy_performance.get(strategy_name, {})
                win_rate = perf_data.get("win_rate", 0)
                total_trades = perf_data.get("total_trades", 0)

                # Skip optimization if insufficient data
                if total_trades < 10:
                    optimization_results[strategy_name] = {
                        "status": "insufficient_data",
                        "message": f"Need at least 10 trades, currently has {total_trades}",
                    }
                    continue

                # Get QFM features for optimization
                qfm_features = {}
                if market_data and self.qfm_engine:
                    for symbol in market_data.keys():
                        features = self.qfm_engine.compute_realtime_features(
                            symbol,
                            market_data[symbol][-1] if market_data[symbol] else {},
                        )
                        qfm_features[symbol] = features

                # Perform QFM-based parameter optimization
                optimized_params = self._qfm_parameter_optimization(
                    strategy, strategy_name, qfm_features, win_rate, total_trades
                )

                # Apply optimized parameters
                if optimized_params:
                    strategy.parameters.update(optimized_params)
                    optimization_results[strategy_name] = {
                        "status": "optimized",
                        "old_parameters": strategy.parameters.copy(),
                        "new_parameters": optimized_params,
                        "expected_improvement": self._calculate_expected_improvement(
                            strategy, optimized_params
                        ),
                    }
                else:
                    optimization_results[strategy_name] = {
                        "status": "no_improvement",
                        "message": "Current parameters are optimal",
                    }

            except Exception as e:
                optimization_results[strategy_name] = {
                    "status": "error",
                    "message": str(e),
                }

        return optimization_results

    def _qfm_parameter_optimization(
        self, strategy, strategy_name, qfm_features, win_rate, total_trades
    ):
        """Perform QFM-based parameter optimization for a specific strategy"""
        optimized_params = {}

        # Base optimization parameters for all strategies
        base_params = {
            "confidence_threshold": strategy.parameters.get(
                "confidence_threshold", 0.5
            ),
            "risk_multiplier": strategy.parameters.get("risk_multiplier", 1.0),
            "trend_strength_threshold": strategy.parameters.get(
                "trend_strength_threshold", 0.6
            ),
        }

        # QFM-enhanced optimization logic
        if qfm_features:
            # Calculate average QFM metrics across symbols
            avg_velocity = np.mean(
                [f.get("velocity", 0) for f in qfm_features.values()]
            )
            avg_acceleration = np.mean(
                [f.get("acceleration", 0) for f in qfm_features.values()]
            )
            avg_jerk = np.mean([f.get("jerk", 0) for f in qfm_features.values()])
            avg_regime_score = np.mean(
                [f.get("regime_score", 0.5) for f in qfm_features.values()]
            )

            # Adjust confidence threshold based on QFM regime
            if avg_regime_score > 0.7:  # High confidence regime
                optimized_params["confidence_threshold"] = min(
                    0.8, base_params["confidence_threshold"] * 1.2
                )
            elif avg_regime_score < 0.3:  # Low confidence regime
                optimized_params["confidence_threshold"] = max(
                    0.3, base_params["confidence_threshold"] * 0.8
                )

            # Adjust risk multiplier based on QFM volatility (jerk)
            if abs(avg_jerk) > 0.5:  # High volatility
                optimized_params["risk_multiplier"] = max(
                    0.5, base_params["risk_multiplier"] * 0.8
                )
            elif abs(avg_jerk) < 0.2:  # Low volatility
                optimized_params["risk_multiplier"] = min(
                    2.0, base_params["risk_multiplier"] * 1.1
                )

            # Adjust trend strength threshold based on momentum
            momentum_strength = abs(avg_velocity) + abs(avg_acceleration)
            if momentum_strength > 1.0:  # Strong momentum
                optimized_params["trend_strength_threshold"] = min(
                    0.8, base_params["trend_strength_threshold"] * 1.1
                )
            elif momentum_strength < 0.3:  # Weak momentum
                optimized_params["trend_strength_threshold"] = max(
                    0.4, base_params["trend_strength_threshold"] * 0.9
                )

        # Strategy-specific optimizations
        if strategy_name == "trend_following":
            optimized_params.update(
                self._optimize_trend_following(strategy, qfm_features, win_rate)
            )
        elif strategy_name == "mean_reversion":
            optimized_params.update(
                self._optimize_mean_reversion(strategy, qfm_features, win_rate)
            )
        elif strategy_name == "momentum":
            optimized_params.update(
                self._optimize_momentum(strategy, qfm_features, win_rate)
            )

        return optimized_params

    def _optimize_trend_following(self, strategy, qfm_features, win_rate):
        """Optimize Trend Following strategy parameters"""
        params = {}

        # Adjust lookback periods based on QFM acceleration
        if qfm_features:
            avg_acceleration = np.mean(
                [f.get("acceleration", 0) for f in qfm_features.values()]
            )
            current_short_period = strategy.parameters.get("short_period", 20)
            current_long_period = strategy.parameters.get("long_period", 50)

            if abs(avg_acceleration) > 0.3:  # High acceleration - shorter periods
                params["short_period"] = max(10, int(current_short_period * 0.9))
                params["long_period"] = max(20, int(current_long_period * 0.9))
            elif abs(avg_acceleration) < 0.1:  # Low acceleration - longer periods
                params["short_period"] = min(50, int(current_short_period * 1.1))
                params["long_period"] = min(100, int(current_long_period * 1.1))

        # Adjust trend threshold based on win rate
        if win_rate < 40:
            params["trend_threshold"] = (
                strategy.parameters.get("trend_threshold", 0.02) * 1.2
            )
        elif win_rate > 60:
            params["trend_threshold"] = (
                strategy.parameters.get("trend_threshold", 0.02) * 0.9
            )

        return params

    def _optimize_mean_reversion(self, strategy, qfm_features, win_rate):
        """Optimize Mean Reversion strategy parameters"""
        params = {}

        # Adjust deviation thresholds based on QFM jerk (volatility)
        if qfm_features:
            avg_jerk = np.mean([f.get("jerk", 0) for f in qfm_features.values()])
            current_deviation = strategy.parameters.get("deviation_threshold", 2.0)

            if abs(avg_jerk) > 0.4:  # High volatility - wider thresholds
                params["deviation_threshold"] = min(3.5, current_deviation * 1.2)
            elif abs(avg_jerk) < 0.2:  # Low volatility - tighter thresholds
                params["deviation_threshold"] = max(1.5, current_deviation * 0.9)

        # Adjust reversion speed based on win rate
        if win_rate < 45:
            params["reversion_speed"] = (
                strategy.parameters.get("reversion_speed", 0.8) * 0.9
            )
        elif win_rate > 65:
            params["reversion_speed"] = (
                strategy.parameters.get("reversion_speed", 0.8) * 1.1
            )

        return params

    def _optimize_momentum(self, strategy, qfm_features, win_rate):
        """Optimize Momentum strategy parameters"""
        params = {}

        # Adjust momentum periods based on QFM velocity
        if qfm_features:
            avg_velocity = np.mean(
                [f.get("velocity", 0) for f in qfm_features.values()]
            )
            current_period = strategy.parameters.get("momentum_period", 14)

            if abs(avg_velocity) > 0.4:  # Strong momentum - shorter periods
                params["momentum_period"] = max(7, int(current_period * 0.8))
            elif abs(avg_velocity) < 0.2:  # Weak momentum - longer periods
                params["momentum_period"] = min(28, int(current_period * 1.2))

        # Adjust momentum threshold based on win rate
        if win_rate < 50:
            params["momentum_threshold"] = (
                strategy.parameters.get("momentum_threshold", 0.05) * 1.1
            )
        elif win_rate > 70:
            params["momentum_threshold"] = (
                strategy.parameters.get("momentum_threshold", 0.05) * 0.95
            )

        return params

    def _calculate_expected_improvement(self, strategy, optimized_params):
        """Calculate expected performance improvement from parameter changes"""
        # Simple heuristic-based improvement calculation
        improvement_factors = {
            "confidence_threshold": 0.05,  # 5% improvement per 0.1 threshold change
            "risk_multiplier": 0.03,  # 3% improvement per 0.1 risk change
            "trend_strength_threshold": 0.04,  # 4% improvement per 0.1 threshold change
        }

        expected_improvement = 0.0
        for param, new_value in optimized_params.items():
            old_value = strategy.parameters.get(param, new_value)
            if param in improvement_factors:
                change = abs(new_value - old_value)
                if param in ["confidence_threshold", "trend_strength_threshold"]:
                    # For thresholds, smaller changes are better
                    change = min(change, 0.2)  # Cap at 0.2 for reasonable improvements
                expected_improvement += change * improvement_factors[param]

        return min(expected_improvement, 0.25)  # Cap at 25% expected improvement

    def run_ab_testing(self, strategy_name, variants=None, test_duration_hours=24):
        """Run A/B testing for strategy variants with different QFM parameters"""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        strategy = self.strategies[strategy_name]

        # Default variants if none provided
        if not variants:
            variants = self._generate_strategy_variants(strategy, strategy_name)

        # Initialize A/B test
        test_id = f"{strategy_name}_ab_test_{int(time.time())}"
        ab_test = {
            "test_id": test_id,
            "strategy_name": strategy_name,
            "variants": variants,
            "start_time": time.time(),
            "duration_hours": test_duration_hours,
            "results": {
                variant["name"]: {"trades": 0, "wins": 0, "pnl": 0.0}
                for variant in variants
            },
            "active": True,
        }

        # Store test configuration (would be persisted in production)
        if not hasattr(self, "ab_tests"):
            self.ab_tests = {}
        self.ab_tests[test_id] = ab_test

        return {
            "test_id": test_id,
            "variants": len(variants),
            "duration_hours": test_duration_hours,
            "status": "started",
        }

    def _generate_strategy_variants(self, strategy, strategy_name):
        """Generate strategy variants for A/B testing"""
        base_params = strategy.parameters.copy()
        variants = []

        # Variant 1: Conservative QFM tuning
        conservative = base_params.copy()
        conservative.update(
            {
                "confidence_threshold": min(
                    0.8, base_params.get("confidence_threshold", 0.5) * 1.1
                ),
                "risk_multiplier": max(
                    0.7, base_params.get("risk_multiplier", 1.0) * 0.9
                ),
                "qfm_sensitivity": 0.8,
            }
        )
        variants.append(
            {
                "name": "conservative_qfm",
                "parameters": conservative,
                "description": "Conservative QFM-enhanced parameters",
            }
        )

        # Variant 2: Aggressive QFM tuning
        aggressive = base_params.copy()
        aggressive.update(
            {
                "confidence_threshold": max(
                    0.3, base_params.get("confidence_threshold", 0.5) * 0.9
                ),
                "risk_multiplier": min(
                    1.5, base_params.get("risk_multiplier", 1.0) * 1.2
                ),
                "qfm_sensitivity": 1.2,
            }
        )
        variants.append(
            {
                "name": "aggressive_qfm",
                "parameters": aggressive,
                "description": "Aggressive QFM-enhanced parameters",
            }
        )

        # Variant 3: Balanced QFM tuning (baseline)
        balanced = base_params.copy()
        balanced["qfm_sensitivity"] = 1.0
        variants.append(
            {
                "name": "balanced_qfm",
                "parameters": balanced,
                "description": "Balanced QFM-enhanced parameters",
            }
        )

        return variants

    def get_ab_test_results(self, test_id):
        """Get results from an A/B test"""
        if not hasattr(self, "ab_tests") or test_id not in self.ab_tests:
            return {"error": f"A/B test {test_id} not found"}

        test = self.ab_tests[test_id]

        # Check if test should be completed
        elapsed_hours = (time.time() - test["start_time"]) / 3600
        if elapsed_hours >= test["duration_hours"]:
            test["active"] = False
            test["completed_at"] = time.time()

        # Calculate performance metrics for each variant
        results = {}
        for variant_name, variant_results in test["results"].items():
            trades = variant_results["trades"]
            if trades > 0:
                win_rate = (variant_results["wins"] / trades) * 100
                avg_pnl = variant_results["pnl"] / trades
                results[variant_name] = {
                    "trades": trades,
                    "win_rate": win_rate,
                    "total_pnl": variant_results["pnl"],
                    "avg_pnl": avg_pnl,
                    "score": win_rate * 0.6 + (avg_pnl * 100) * 0.4,  # Composite score
                }
            else:
                results[variant_name] = {
                    "trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "avg_pnl": 0,
                    "score": 0,
                }

        # Determine winner
        if results:
            winner = max(results.items(), key=lambda x: x[1]["score"])
            test["winner"] = winner[0]

        return {
            "test_id": test_id,
            "active": test["active"],
            "elapsed_hours": elapsed_hours,
            "duration_hours": test["duration_hours"],
            "results": results,
            "winner": test.get("winner"),
            "variants": test["variants"],
        }

    def apply_ab_test_winner(self, test_id):
        """Apply the winning variant from an A/B test to the main strategy"""
        test_results = self.get_ab_test_results(test_id)
        if "error" in test_results:
            return test_results

        if not test_results.get("winner"):
            return {"error": "No winner determined yet"}

        winner_variant = None
        for variant in test_results["variants"]:
            if variant["name"] == test_results["winner"]:
                winner_variant = variant
                break

        if not winner_variant:
            return {"error": "Winner variant not found"}

        strategy_name = test_results.get("strategy_name")
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        # Apply winning parameters
        self.strategies[strategy_name].parameters.update(winner_variant["parameters"])

        return {
            "status": "applied",
            "strategy": strategy_name,
            "winner_variant": test_results["winner"],
            "new_parameters": winner_variant["parameters"],
        }


# ==================== QUANTUM FUSION MOMENTUM ANALYTICS ENGINE ====================
class QuantumFusionMomentumEngine:
    """Advanced Quantum Fusion Momentum Analytics Engine for market analysis"""

    def __init__(self):
        self.feature_history = {}
        self.market_regime_history = {}
        self.velocity_cache = {}
        self.acceleration_cache = {}
        self.jerk_cache = {}
        self.max_history_size = 1000

    def compute_realtime_features(self, symbol, market_data):
        """Compute real-time QFM features for a symbol"""
        if not market_data or not isinstance(market_data, dict):
            return {}

        # Extract price data
        close_price = market_data.get("close", market_data.get("price", 0))
        volume = market_data.get("volume", 0)
        high = market_data.get("high", close_price)
        low = market_data.get("low", close_price)

        # Initialize symbol history if needed
        if symbol not in self.feature_history:
            self.feature_history[symbol] = deque(maxlen=self.max_history_size)
            self.velocity_cache[symbol] = deque(maxlen=self.max_history_size)
            self.acceleration_cache[symbol] = deque(maxlen=self.max_history_size)
            self.jerk_cache[symbol] = deque(maxlen=self.max_history_size)

        # Calculate QFM features
        features = self._calculate_qfm_features(symbol, close_price, volume, high, low)

        # Store in history
        self.feature_history[symbol].append(
            {
                "timestamp": time.time(),
                "features": features.copy(),
                "price": close_price,
                "volume": volume,
            }
        )

        return features

    def _calculate_qfm_features(self, symbol, price, volume, high, low):
        """Calculate comprehensive QFM features"""
        features = {}

        # Basic momentum calculations
        features["price"] = price
        features["volume"] = volume

        # Calculate velocity (rate of price change)
        velocity = self._calculate_velocity(symbol, price)
        features["velocity"] = velocity

        # Calculate acceleration (rate of velocity change)
        acceleration = self._calculate_acceleration(symbol, velocity)
        features["acceleration"] = acceleration

        # Calculate jerk (rate of acceleration change)
        jerk = self._calculate_jerk(symbol, acceleration)
        features["jerk"] = jerk

        # Volume pressure analysis
        volume_pressure = self._calculate_volume_pressure(symbol, volume, price)
        features["volume_pressure"] = volume_pressure

        # Trend confidence based on momentum consistency
        trend_confidence = self._calculate_trend_confidence(symbol)
        features["trend_confidence"] = trend_confidence

        # Market regime score (0-1, higher = more trending)
        regime_score = self._calculate_regime_score(features)
        features["regime_score"] = regime_score

        # Entropy measure for market randomness
        entropy = self._calculate_market_entropy(symbol)
        features["entropy"] = entropy

        # Volatility measure
        volatility = self._calculate_volatility(symbol, high, low)
        features["volatility"] = volatility

        return features

    def _calculate_velocity(self, symbol, current_price):
        """Calculate price velocity (momentum)"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 2:
            return 0.0

        # Use exponential moving average for smoother velocity
        prices = [h["price"] for h in history[-10:]]  # Last 10 points

        if len(prices) < 2:
            return 0.0

        # Calculate rate of change
        recent_change = (
            (current_price - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        )

        # Store velocity
        self.velocity_cache[symbol].append(recent_change)

        return recent_change

    def _calculate_acceleration(self, symbol, current_velocity):
        """Calculate acceleration (change in momentum)"""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 2:
            return 0.0

        # Rate of change of velocity
        acceleration = current_velocity - velocities[-2]

        # Store acceleration
        self.acceleration_cache[symbol].append(acceleration)

        return acceleration

    def _calculate_jerk(self, symbol, current_acceleration):
        """Calculate jerk (change in acceleration)"""
        accelerations = list(self.acceleration_cache.get(symbol, []))

        if len(accelerations) < 2:
            return 0.0

        # Rate of change of acceleration
        jerk = current_acceleration - accelerations[-2]

        # Store jerk
        self.jerk_cache[symbol].append(jerk)

        return jerk

    def _calculate_volume_pressure(self, symbol, volume, price):
        """Calculate volume pressure indicator"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 5:
            return 0.0

        # Average volume over last 5 periods
        avg_volume = np.mean([h["volume"] for h in history[-5:]])

        if avg_volume == 0:
            return 0.0

        # Volume pressure: current volume relative to average
        volume_pressure = (volume - avg_volume) / avg_volume

        # Weight by price movement direction
        price_change = 0
        if len(history) >= 2:
            price_change = (price - history[-2]["price"]) / history[-2]["price"]

        # Positive pressure when volume increases with price movement
        volume_pressure *= 1 + abs(price_change)

        return volume_pressure

    def _calculate_trend_confidence(self, symbol):
        """Calculate trend confidence based on momentum consistency"""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 5:
            return 0.5

        # Check consistency of directional movement
        recent_velocities = velocities[-10:]

        # Count directional consistency
        positive_count = sum(1 for v in recent_velocities if v > 0)
        negative_count = sum(1 for v in recent_velocities if v < 0)

        # Confidence based on directional dominance
        total_directional = positive_count + negative_count
        if total_directional == 0:
            return 0.5

        confidence = max(positive_count, negative_count) / total_directional

        return confidence

    def _calculate_regime_score(self, features):
        """Calculate market regime score (0-1, higher = trending)"""
        velocity = abs(features.get("velocity", 0))
        acceleration = abs(features.get("acceleration", 0))
        trend_confidence = features.get("trend_confidence", 0.5)
        entropy = features.get("entropy", 0.5)

        # Regime score combines momentum strength and trend consistency
        momentum_strength = min(1.0, (velocity + acceleration) * 10)  # Scale and cap

        # Lower entropy = more ordered (trending) market
        order_factor = 1.0 - entropy

        # Combine factors
        regime_score = (
            momentum_strength * 0.4 + trend_confidence * 0.4 + order_factor * 0.2
        )

        return min(1.0, max(0.0, regime_score))

    def _calculate_market_entropy(self, symbol):
        """Calculate market entropy (randomness measure)"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 10:
            return 0.5

        # Calculate price return distribution
        prices = [h["price"] for h in history[-20:]]
        returns = []

        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.5

        # Calculate entropy of return distribution
        try:
            # Discretize returns into bins
            bins = np.histogram(returns, bins=10)[0]
            bins = bins[bins > 0]  # Remove zero bins
            probs = bins / np.sum(bins)

            # Shannon entropy
            entropy = -np.sum(probs * np.log2(probs))

            # Normalize to 0-1 scale
            max_entropy = np.log2(len(bins))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.5

            return normalized_entropy

        except:
            return 0.5

    def _calculate_volatility(self, symbol, high, low):
        """Calculate price volatility"""
        if high == low:
            return 0.0

        # Range-based volatility
        range_volatility = (high - low) / ((high + low) / 2)

        # Historical volatility
        history = self.feature_history.get(symbol, [])
        if len(history) >= 5:
            recent_prices = [h["price"] for h in history[-5:]]
            price_std = np.std(recent_prices)
            price_mean = np.mean(recent_prices)

            if price_mean != 0:
                hist_volatility = price_std / price_mean
                # Combine range and historical volatility
                return (range_volatility + hist_volatility) / 2

        return range_volatility

    def get_market_regime(self, symbol):
        """Get current market regime classification"""
        features = self.get_latest_features(symbol)

        if not features:
            return "unknown"

        regime_score = features.get("regime_score", 0.5)
        trend_confidence = features.get("trend_confidence", 0.5)
        jerk = abs(features.get("jerk", 0))

        # Classify regime
        if regime_score > 0.7 and trend_confidence > 0.6:
            velocity = features.get("velocity", 0)
            return "trending_bull" if velocity > 0 else "trending_bear"
        elif jerk > 0.5:
            return "volatile"
        elif regime_score < 0.4:
            return "sideways"
        else:
            return "calm"

    def get_latest_features(self, symbol):
        """Get latest QFM features for a symbol"""
        history = self.feature_history.get(symbol, [])

        if not history:
            return {}

        return history[-1]["features"]

    def get_feature_history(self, symbol, limit=100):
        """Get historical QFM features for analysis"""
        history = self.feature_history.get(symbol, [])

        return list(history)[-limit:] if history else []

    def analyze_market_cycles(self, symbol):
        """Analyze market cycles using QFM features"""
        history = self.get_feature_history(symbol, 200)

        if len(history) < 20:
            return {"error": "Insufficient data for cycle analysis"}

        # Extract features over time
        timestamps = [h["timestamp"] for h in history]
        velocities = [h["features"]["velocity"] for h in history]
        accelerations = [h["features"]["acceleration"] for h in history]
        regime_scores = [h["features"]["regime_score"] for h in history]

        # Detect cycles using acceleration changes
        cycle_analysis = {
            "cycle_length_avg": self._calculate_average_cycle_length(accelerations),
            "current_phase": self._determine_current_cycle_phase(accelerations),
            "cycle_strength": np.std(accelerations),
            "regime_transitions": self._count_regime_transitions(regime_scores),
            "momentum_cycles": self._analyze_momentum_cycles(velocities),
        }

        return cycle_analysis

    def _calculate_average_cycle_length(self, accelerations):
        """Calculate average cycle length from acceleration data"""
        if len(accelerations) < 10:
            return 0

        # Find zero crossings in acceleration (cycle boundaries)
        zero_crossings = []
        for i in range(1, len(accelerations)):
            if accelerations[i - 1] * accelerations[i] < 0:  # Sign change
                zero_crossings.append(i)

        if len(zero_crossings) < 2:
            return len(accelerations)  # Default to full period

        # Calculate cycle lengths
        cycle_lengths = []
        for i in range(1, len(zero_crossings)):
            cycle_lengths.append(zero_crossings[i] - zero_crossings[i - 1])

        return np.mean(cycle_lengths) if cycle_lengths else len(accelerations)

    def _determine_current_cycle_phase(self, accelerations):
        """Determine current position in market cycle"""
        if len(accelerations) < 5:
            return "unknown"

        recent_acc = accelerations[-5:]

        # Analyze recent acceleration trend
        if all(a > 0 for a in recent_acc):
            return "acceleration_phase"
        elif all(a < 0 for a in recent_acc):
            return "deceleration_phase"
        else:
            return "transition_phase"

    def _count_regime_transitions(self, regime_scores):
        """Count regime transitions over time"""
        if len(regime_scores) < 2:
            return 0

        transitions = 0
        threshold_high = 0.6
        threshold_low = 0.4

        for i in range(1, len(regime_scores)):
            prev_regime = (
                "high"
                if regime_scores[i - 1] > threshold_high
                else ("low" if regime_scores[i - 1] < threshold_low else "neutral")
            )
            curr_regime = (
                "high"
                if regime_scores[i] > threshold_high
                else ("low" if regime_scores[i] < threshold_low else "neutral")
            )

            if prev_regime != curr_regime:
                transitions += 1

        return transitions

    def _analyze_momentum_cycles(self, velocities):
        """Analyze momentum cycles"""
        if len(velocities) < 10:
            return {"cycles": 0, "strength": 0}

        # Find momentum cycles (direction changes)
        direction_changes = []
        for i in range(1, len(velocities)):
            if velocities[i - 1] * velocities[i] < 0:  # Direction change
                direction_changes.append(i)

        cycle_info = {
            "cycles": len(direction_changes),
            "average_length": np.mean(np.diff(direction_changes))
            if len(direction_changes) > 1
            else 0,
            "strength": np.std(velocities),
        }

        return cycle_info


# ==================== STRATEGY MANAGER ====================
class StrategyManager:
    """Manages multiple trading strategies with QFM enhancement"""

    def __init__(self):
        self.strategies = {}
        self.active_strategies = {}
        self.strategy_performance = {}
        self.qfm_engine = QuantumFusionMomentumEngine()  # Initialize QFM engine
        self.initialize_strategies()
        self.initialize_ml_feedback_system()
        self.initialize_performance_analytics()
        self.initialize_user_dashboard_features()
        self.initialize_adaptive_risk_management()
        self.initialize_continuous_improvement_pipeline()

    def initialize_adaptive_risk_management(self):
        """Initialize adaptive risk management system"""
        print("DEBUG: initialize_adaptive_risk_management called")
        self.adaptive_risk = {
            "qfm_regime_risk_multipliers": {
                "trending_bull": 1.2,  # Increase risk in strong bull trends
                "trending_bear": 1.1,  # Moderate increase in bear trends
                "sideways": 0.7,  # Reduce risk in sideways markets
                "volatile": 0.6,  # Significantly reduce risk in high volatility
                "calm": 1.0,  # Normal risk in calm markets
            },
            "volatility_adjustments": {
                "low_volatility": 1.1,  # Slightly increase risk when volatility is low
                "normal_volatility": 1.0,  # Normal risk
                "high_volatility": 0.5,  # Reduce risk significantly when volatility is high
                "extreme_volatility": 0.3,  # Minimal risk in extreme volatility
            },
            "momentum_risk_multipliers": {
                "strong_bullish": 1.15,  # Increase risk on strong bullish momentum
                "moderate_bullish": 1.05,  # Slight increase on moderate bullish
                "neutral": 1.0,  # Normal risk
                "moderate_bearish": 0.9,  # Slight decrease on moderate bearish
                "strong_bearish": 0.8,  # Decrease risk on strong bearish momentum
            },
            "current_regime": "neutral",
            "regime_confidence": 0.0,
            "volatility_percentile": 50.0,
            "momentum_strength": 0.0,
            "risk_adjustment_history": [],
            "max_history_size": 1000,
        }
        print(
            "DEBUG: adaptive_risk initialized, keys:", list(self.adaptive_risk.keys())
        )

    def get_risk_management_status(self):
        """Get current risk management status and recommendations"""
        status = {
            "current_regime": self.adaptive_risk["current_regime"],
            "regime_confidence": self.adaptive_risk["regime_confidence"],
            "volatility_percentile": self.adaptive_risk["volatility_percentile"],
            "momentum_strength": self.adaptive_risk["momentum_strength"],
            "risk_multipliers": {
                "regime": self.adaptive_risk["qfm_regime_risk_multipliers"].get(
                    self.adaptive_risk["current_regime"], 1.0
                ),
                "volatility": self._get_volatility_multiplier(
                    self._assess_volatility_level_from_current_state()
                ),
                "momentum": self._get_momentum_multiplier(
                    self.adaptive_risk["momentum_strength"]
                ),
            },
            "recent_adjustments": self.adaptive_risk["risk_adjustment_history"][-10:]
            if self.adaptive_risk["risk_adjustment_history"]
            else [],
            "recommendations": self._generate_risk_recommendations(),
        }

        return status

    def _get_volatility_multiplier(self, volatility_level):
        """Get risk multiplier based on volatility level"""
        return self.adaptive_risk["volatility_adjustments"].get(volatility_level, 1.0)

    def _get_momentum_multiplier(self, momentum_strength):
        """Get risk multiplier based on momentum strength"""
        if momentum_strength > 1.0:
            return self.adaptive_risk["momentum_risk_multipliers"]["strong_bullish"]
        elif momentum_strength > 0.5:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bullish"]
        elif momentum_strength > 0.2:
            return self.adaptive_risk["momentum_risk_multipliers"]["neutral"]
        elif momentum_strength > 0.1:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bearish"]
        else:
            return self.adaptive_risk["momentum_risk_multipliers"]["strong_bearish"]

    def _assess_volatility_level_from_current_state(self):
        """Assess volatility level from current state"""
        percentile = self.adaptive_risk["volatility_percentile"]

        if percentile > 90:
            return "extreme_volatility"
        elif percentile > 75:
            return "high_volatility"
        elif percentile > 25:
            return "normal_volatility"
        else:
            return "low_volatility"

    def _generate_risk_recommendations(self):
        """Generate risk management recommendations"""
        recommendations = []

        regime = self.adaptive_risk["current_regime"]
        volatility_percentile = self.adaptive_risk["volatility_percentile"]
        momentum_strength = self.adaptive_risk["momentum_strength"]

        # Regime-based recommendations
        if regime == "volatile":
            recommendations.append(
                {
                    "type": "regime_risk",
                    "priority": "high",
                    "message": "High volatility detected - reducing position sizes by 40%",
                    "action": "reduce_position_sizes",
                }
            )
        elif regime in ["trending_bull", "trending_bear"]:
            recommendations.append(
                {
                    "type": "regime_opportunity",
                    "priority": "medium",
                    "message": f'Strong {regime.split("_")[1]} trend detected - increasing position sizes by 15-20%',
                    "action": "increase_position_sizes",
                }
            )

        # Volatility-based recommendations
        if volatility_percentile > 80:
            recommendations.append(
                {
                    "type": "volatility_alert",
                    "priority": "high",
                    "message": f"Volatility at {volatility_percentile:.1f}th percentile - implement strict risk controls",
                    "action": "implement_strict_risk_controls",
                }
            )

        # Momentum-based recommendations
        if momentum_strength > 1.0:
            recommendations.append(
                {
                    "type": "momentum_opportunity",
                    "priority": "medium",
                    "message": f"Strong momentum detected (strength: {momentum_strength:.2f}) - consider increasing risk",
                    "action": "increase_risk_exposure",
                }
            )

        return recommendations

    def initialize_ml_feedback_system(self):
        """Initialize ML feedback system for strategy optimization"""
        self.ml_feedback = {
            "performance_history": [],
            "correlation_matrix": {},
            "feature_importance": {},
            "model_accuracy": {},
            "feedback_enabled": True,
            "learning_rate": 0.01,
            "max_history_size": 10000,
        }

    def initialize_performance_analytics(self):
        """Initialize performance analytics system"""
        self.performance_analytics = {
            "risk_adjusted_metrics": {},
            "strategy_correlations": {},
            "market_regime_performance": {},
            "time_based_performance": {},
            "alert_thresholds": {
                "max_drawdown": 0.1,
                "sharpe_ratio_min": 1.0,
                "win_rate_min": 0.55,
                "max_consecutive_losses": 5,
            },
            "analytics_enabled": True,
        }

    def initialize_user_dashboard_features(self):
        """Initialize user dashboard features"""
        self.user_dashboard = {
            "personalized_strategies": {},
            "risk_profiles": {},
            "performance_goals": {},
            "notification_preferences": {},
            "custom_indicators": {},
            "dashboard_enabled": True,
        }

    def initialize_continuous_improvement_pipeline(self):
        """Initialize continuous improvement pipeline"""
        self.continuous_improvement = {
            "optimization_schedule": {"daily": True, "weekly": True, "monthly": True},
            "parameter_ranges": {},
            "optimization_methods": ["bayesian", "grid", "random"],
            "performance_thresholds": {},
            "auto_optimization_enabled": True,
            "last_optimization": None,
            "improvement_history": [],
        }

    def initialize_strategies(self):
        """Initialize all available strategies with QFM enhancement"""
        self.strategies = {
            "trend_following": TrendFollowingStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "breakout": BreakoutStrategy(),
            "momentum": MomentumStrategy(),
            "arbitrage": ArbitrageStrategy(),
            "ml_based": MLBasedStrategy(),
            "scalping": ScalpingStrategy(),
        }

        # Set QFM engine for all strategies
        for strategy in self.strategies.values():
            strategy.set_qfm_engine(self.qfm_engine)

        # Initialize performance tracking
        for strategy_name in self.strategies:
            self.strategy_performance[strategy_name] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "last_updated": time.time(),
            }

    def get_strategy(self, strategy_name):
        """Get a strategy instance"""
        return self.strategies.get(strategy_name)

    def get_all_strategies(self):
        """Get all available strategies with details"""
        strategies = []
        for name, strategy in self.strategies.items():
            strategies.append(
                {
                    "name": strategy.name,
                    "type": name,
                    "active": True,  # All strategies are available/active
                    "description": strategy.description,
                    "parameters": strategy.parameters,
                }
            )
        return strategies

    def analyze_with_strategy(
        self, strategy_name, symbol, market_data, indicators=None
    ):
        """Analyze market using specific strategy with QFM enhancement"""
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return {"error": f"Strategy {strategy_name} not found"}

        # Update QFM engine with latest market data for this symbol
        if self.qfm_engine and market_data:
            self.qfm_engine.compute_realtime_features(
                symbol, market_data[-1] if market_data else {}
            )

        return strategy.analyze_market(symbol, market_data, indicators)

    def get_strategy_performance(self, strategy_name=None):
        """Get performance metrics for strategies"""
        if strategy_name:
            strategy = self.get_strategy(strategy_name)
            if strategy:
                perf = strategy.get_performance_summary()
                perf.update(self.strategy_performance.get(strategy_name, {}))
                return perf
            return {}

        # Return all strategies performance
        performance = {}
        for name, strategy in self.strategies.items():
            perf = strategy.get_performance_summary()
            perf.update(self.strategy_performance.get(name, {}))
            performance[name] = perf

        return performance

    def update_strategy_performance(self, strategy_name, trade_result):
        """Update performance metrics after a trade"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update_performance(trade_result)

            # Update aggregate performance
            perf = self.strategy_performance[strategy_name]
            perf["total_trades"] += 1
            perf["total_pnl"] += trade_result.get("pnl", 0)

            if trade_result.get("pnl", 0) > 0:
                perf["winning_trades"] += 1

            if perf["total_trades"] > 0:
                perf["win_rate"] = (perf["winning_trades"] / perf["total_trades"]) * 100

            perf["last_updated"] = time.time()

    def get_all_performance(self):
        """Get performance data for all strategies"""
        return self.get_strategy_performance()


# Initialize strategy manager with all new features
strategy_manager = StrategyManager()

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "app", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "app", "static"),
)

# ==================== DATABASE CONFIGURATION ====================
from flask_login import current_user
import os

# Database configuration
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    if os.getenv("FLASK_ENV") == "production":
        raise ValueError("SECRET_KEY environment variable is required in production!")
    else:
        # Generate a secure random key for development
        import secrets

        secret_key = secrets.token_hex(32)
        print(
            "⚠️  WARNING: Using auto-generated SECRET_KEY for development. Set SECRET_KEY in production!"
        )

app.config["SECRET_KEY"] = secret_key
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///trading_bot.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config.setdefault(
    "SOCKETIO_CORS_ALLOWED_ORIGINS", os.getenv("SOCKETIO_CORS_ALLOWED_ORIGINS", "*")
)
app.config.setdefault(
    "SOCKETIO_ASYNC_MODE", os.getenv("SOCKETIO_ASYNC_MODE", "threading")
)

init_extensions(app)
register_blueprints(app)
register_asset_helpers(app)

from app.models import (
    Lead,
    SubscriptionPlan,
    User,
    UserPortfolio,
    UserSubscription,
    UserTrade,
)

# ==================== DATABASE MODELS ====================
# Models are sourced from app.models to ensure a single SQLAlchemy registry.

# Create database tables and ensure schema is migrated before any background threads
with app.app_context():
    db.create_all()
    # Run migration inside the app context so the engine/session are available
    migrate_database()


def _format_duration_hours(hours):
    if hours is None:
        return "Unknown"
    if hours < 1:
        minutes = max(1, int(round(hours * 60)))
        return f"{minutes}m"
    if hours < 48:
        return f"{hours:.1f}h"
    days = hours / 24
    if days < 365:
        return f"{days:.1f}d"
    years = days / 365
    return f"{years:.1f}y"


MISSING_TALIB_FUNCTIONS = []


def _ensure_float_array(data):
    try:
        arr = np.asarray(data, dtype=float)
    except Exception:
        arr = np.asarray(list(data), dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def _ensure_series(data):
    return pd.Series(_ensure_float_array(data))


def _register_talib_fallback(name, func):
    existing = getattr(talib, name, None)
    if callable(existing):
        return
    setattr(talib, name, func)
    MISSING_TALIB_FUNCTIONS.append(name)


def _fallback_sma(data, timeperiod=30):
    series = _ensure_series(data)
    return (
        series.rolling(window=int(max(1, timeperiod)), min_periods=1).mean().to_numpy()
    )


def _fallback_rsi(data, timeperiod=14):
    period = int(max(1, timeperiod))
    series = _ensure_series(data)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0).to_numpy()


def _fallback_macd(data, fastperiod=12, slowperiod=26, signalperiod=9):
    fast = int(max(1, fastperiod))
    slow = int(max(fast + 1, slowperiod))
    signal = int(max(1, signalperiod))
    series = _ensure_series(data)
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line.to_numpy(), signal_line.to_numpy(), hist.to_numpy()


def _fallback_stoch(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3):
    fast_k_period = int(max(1, fastk_period))
    slow_k_period = int(max(1, slowk_period))
    slow_d_period = int(max(1, slowd_period))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    lowest_low = low_s.rolling(window=fast_k_period, min_periods=1).min()
    highest_high = high_s.rolling(window=fast_k_period, min_periods=1).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    fast_k = ((close_s - lowest_low) / denom) * 100
    fast_k = fast_k.fillna(0)
    slow_k = fast_k.rolling(window=slow_k_period, min_periods=1).mean()
    slow_d = slow_k.rolling(window=slow_d_period, min_periods=1).mean()
    return slow_k.fillna(0).to_numpy(), slow_d.fillna(0).to_numpy()


def _fallback_true_range(high_s, low_s, close_s):
    prev_close = close_s.shift(1)
    ranges = pd.concat(
        [
            (high_s - low_s).abs(),
            (high_s - prev_close).abs(),
            (low_s - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _fallback_atr(high, low, close, timeperiod=14):
    period = int(max(1, timeperiod))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    tr = _fallback_true_range(high_s, low_s, close_s)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr.fillna(0).to_numpy()


def _fallback_adx(high, low, close, timeperiod=14):
    period = int(max(1, timeperiod))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    up_move = high_s.diff()
    down_move = low_s.shift(1) - low_s
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = _fallback_true_range(high_s, low_s, close_s)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = (
        plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    ) * 100
    minus_di = (
        minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    ) * 100
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx.fillna(0).to_numpy()


def _fallback_obv(close, volume):
    close_arr = _ensure_float_array(close)
    volume_arr = _ensure_float_array(volume)
    if close_arr.size == 0:
        return np.array([])
    obv = np.zeros_like(close_arr)
    for idx in range(1, len(close_arr)):
        if close_arr[idx] > close_arr[idx - 1]:
            obv[idx] = obv[idx - 1] + volume_arr[idx]
        elif close_arr[idx] < close_arr[idx - 1]:
            obv[idx] = obv[idx - 1] - volume_arr[idx]
        else:
            obv[idx] = obv[idx - 1]
    return obv


def _fallback_bbands(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0):
    period = int(max(1, timeperiod))
    series = _ensure_series(close)
    mid = series.rolling(window=period, min_periods=1).mean()
    std = series.rolling(window=period, min_periods=1).std(ddof=0).fillna(0)
    upper = mid + nbdevup * std
    lower = mid - nbdevdn * std
    return upper.to_numpy(), mid.to_numpy(), lower.to_numpy()


def _zero_pattern(*args, **kwargs):
    first = args[0] if args else []
    length = len(_ensure_float_array(first))
    return np.zeros(length)


_register_talib_fallback("SMA", _fallback_sma)
_register_talib_fallback("RSI", _fallback_rsi)
_register_talib_fallback("MACD", _fallback_macd)
_register_talib_fallback("STOCH", _fallback_stoch)
_register_talib_fallback("ADX", _fallback_adx)
_register_talib_fallback("ATR", _fallback_atr)
_register_talib_fallback("OBV", _fallback_obv)
_register_talib_fallback("BBANDS", _fallback_bbands)

for _pattern_name in [
    "CDLHAMMER",
    "CDLENGULFING",
    "CDLMORNINGSTAR",
    "CDLHANGINGMAN",
    "CDLEVENINGSTAR",
]:
    _register_talib_fallback(_pattern_name, _zero_pattern)


def _directional_entropy(values):
    """Return entropy of directional moves (0 = uniform, 1 = balanced)."""
    try:
        arr = np.asarray(values, dtype=float)
    except Exception:
        arr = np.array(values, dtype=float)
    if arr.size == 0:
        return 0.0
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return 0.0
    positives = np.sum(arr > 0)
    negatives = np.sum(arr < 0)
    total = positives + negatives
    if total == 0:
        return 0.0
    probs = np.array([positives / total, negatives / total], dtype=float)
    probs = probs[probs > 0]
    if probs.size == 0:
        return 0.0
    return float(stats.entropy(probs, base=2))


BINANCE_MIN_NOTIONAL_OVERRIDES = {
    "BTCUSDT": 10.0,
    "ETHUSDT": 10.0,
    "BNBUSDT": 10.0,
    "ADAUSDT": 10.0,
    "XRPUSDT": 10.0,
    "SOLUSDT": 10.0,
    "DOTUSDT": 10.0,
    "DOGEUSDT": 10.0,
    "AVAXUSDT": 10.0,
    "MATICUSDT": 10.0,
    "LINKUSDT": 10.0,
    "LTCUSDT": 10.0,
    "BCHUSDT": 10.0,
    "XLMUSDT": 10.0,
    "ETCUSDT": 10.0,
}

HEALTH_CHECK_CONFIG = {
    "report_path": os.path.join(PROJECT_ROOT, "reports", "backtest_top10.json"),
    "min_total_return_pct": float(os.getenv("HEALTH_MIN_RETURN_PCT", "0.0")),
    "min_sharpe_ratio": float(os.getenv("HEALTH_MIN_SHARPE", "0.0")),
    "max_drawdown_pct": float(os.getenv("HEALTH_MAX_DRAWDOWN_PCT", "30.0")),
    "refresh_seconds": int(os.getenv("HEALTH_REFRESH_SECONDS", "3600")),
    "auto_run_backtests": os.getenv("HEALTH_AUTO_BACKTEST", "0") == "1",
    "symbols": parse_symbol_env(os.getenv("HEALTH_SYMBOLS"), DEFAULT_HEALTH_SYMBOLS),
    "backtest_years": os.getenv("HEALTH_BACKTEST_YEARS", "1"),
    "backtest_interval": os.getenv("HEALTH_BACKTEST_INTERVAL", "1d"),
}

# ==================== LOGGING CONFIGURATION ====================
LOGGING_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
LOGGING_MAX_BYTES = int(os.getenv("BOT_LOG_MAX_BYTES", 5 * 1024 * 1024))
LOGGING_BACKUP_COUNT = int(os.getenv("BOT_LOG_BACKUPS", 5))
LOGGING_ENABLE_CONSOLE = os.getenv("BOT_LOG_CONSOLE", "1").lower() not in {
    "0",
    "false",
    "no",
}
LOGGING_COMPONENT_FILTER = {
    comp.strip().upper()
    for comp in os.getenv("BOT_LOG_COMPONENTS", "").split(",")
    if comp.strip()
}

BINANCE_WARNING_COOLDOWN = float(os.getenv("BOT_BINANCE_WARNING_COOLDOWN", 180))
_binance_warning_registry = {}


class _StdoutTee(io.TextIOBase):
    """Mirror stdout/stderr to the bot logger without stacking wrappers."""

    def __init__(self, original_stream, logger_instance, level=logging.INFO):
        self.original_stream = original_stream
        self.logger_instance = logger_instance
        self.level = level

    def configure(self, logger_instance, level=logging.INFO):
        self.logger_instance = logger_instance
        self.level = level

    def write(self, message):
        if not isinstance(message, str):
            message = str(message)
        self.original_stream.write(message)
        stripped = message.strip()
        if stripped and self.logger_instance:
            self.logger_instance.log(self.level, stripped)
        return len(message)

    def flush(self):  # pragma: no cover - passthrough
        try:
            self.original_stream.flush()
        except Exception:
            pass


def setup_application_logging(log_dir):
    """Configure rotating file logging with optional console output and stdout capture."""
    if not log_dir:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "bot.log")
    debug_path = os.path.join(log_dir, "bot.debug.log")

    root_logger = logging.getLogger()
    # Prevent duplicate handlers when reinitialising
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            continue

    resolved_level = getattr(logging, LOGGING_LEVEL, logging.INFO)
    root_logger.setLevel(min(resolved_level, logging.DEBUG))

    # Structured JSON formatter for better log analysis
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            # Add structured fields
            if not hasattr(record, "component"):
                record.component = getattr(record, "name", "unknown").split(".")[-1]

            # Create base log entry
            log_entry = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                "level": record.levelname,
                "component": record.component,
                "message": record.getMessage(),
                "logger": record.name,
            }

            # Add extra fields if present
            if hasattr(record, "extra") and record.extra:
                log_entry.update(record.extra)

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_entry, default=str)

    # Human-readable formatter for console
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Use structured formatter for files
    structured_formatter = StructuredFormatter()

    info_handler = RotatingFileHandler(
        log_path, maxBytes=LOGGING_MAX_BYTES, backupCount=LOGGING_BACKUP_COUNT
    )
    info_handler.setLevel(resolved_level)
    info_handler.setFormatter(structured_formatter)
    root_logger.addHandler(info_handler)

    debug_handler = RotatingFileHandler(
        debug_path, maxBytes=LOGGING_MAX_BYTES, backupCount=LOGGING_BACKUP_COUNT
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(structured_formatter)
    root_logger.addHandler(debug_handler)

    if LOGGING_ENABLE_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(resolved_level)
        console_handler.setFormatter(console_formatter)  # Human-readable for console
        root_logger.addHandler(console_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    logger_instance = logging.getLogger("ai_trading_bot")

    if isinstance(sys.stdout, _StdoutTee):
        sys.stdout.configure(logger_instance, resolved_level)
    else:
        sys.stdout = _StdoutTee(sys.stdout, logger_instance, level=resolved_level)

    if isinstance(sys.stderr, _StdoutTee):
        sys.stderr.configure(logger_instance, logging.ERROR)
    else:
        sys.stderr = _StdoutTee(sys.stderr, logger_instance, level=logging.ERROR)

    logger_instance.info(
        "Logging initialized",
        extra={
            "level": LOGGING_LEVEL,
            "log_dir": log_dir,
            "structured_logging": True,
            "console_enabled": LOGGING_ENABLE_CONSOLE,
        },
    )
    return logger_instance


bot_logger = logging.getLogger("ai_trading_bot")


def _should_emit_component(component):
    if not LOGGING_COMPONENT_FILTER:
        return True
    component_key = str(component or "GENERAL").upper()
    return (
        "ALL" in LOGGING_COMPONENT_FILTER or component_key in LOGGING_COMPONENT_FILTER
    )


def log_component_event(component, message, level=logging.INFO, details=None):
    if not _should_emit_component(component):
        return

    component_key = str(component or "GENERAL").upper()
    if details is not None:
        try:
            serialized_details = json.dumps(details, default=str)
        except TypeError:
            serialized_details = str(details)
        bot_logger.log(
            level, "[%s] %s | details=%s", component_key, message, serialized_details
        )
    else:
        bot_logger.log(level, "[%s] %s", component_key, message)


def log_component_debug(component, message, details=None):
    log_component_event(component, message, level=logging.DEBUG, details=details)


_ONCE_LOGGED_WARNINGS = set()


def log_warning_once(component, key, message, details=None):
    identifier = f"{component}:{key}"
    if identifier in _ONCE_LOGGED_WARNINGS:
        return
    _ONCE_LOGGED_WARNINGS.add(identifier)
    log_component_event(component, message, level=logging.WARNING, details=details)


BINANCE_MIN_NOTIONAL_OVERRIDES = dict(BINANCE_MIN_NOTIONAL_OVERRIDES)

# ==================== ULTIMATE CONFIGURATION ====================
TRADING_CONFIG = {
    "confidence_threshold": 0.58,
    "max_positions": 3,
    "take_profit": 0.08,
    "stop_loss": 0.03,
    "min_confidence_diff": 0.12,
    "risk_per_trade": 0.01,
    "max_position_size": 0.08,
    "use_ensemble": True,
    "ensemble_min_agreement": 0.75,
    "correlation_threshold": 0.6,
    "market_regime_aware": True,
    "dynamic_position_sizing": True,
    "parallel_processing": True,
    "advanced_stop_loss": True,
    "periodic_rebuilding": True,
    "adaptive_risk_management": True,
    "continuous_training": True,
    "optimized_indicators": BEST_INDICATORS,
    "dynamic_threshold_floor": 0.4,
    "dynamic_threshold_ceiling": 0.6,
    "default_min_notional": 10.0,
    "min_notional_buffer": 1.1,
    "min_notional_overrides": BINANCE_MIN_NOTIONAL_OVERRIDES.copy(),
    "balance_cash_buffer": 1.01,
    "auto_take_profit_percent": 0.05,
    "auto_take_profit_time_in_force": "GTC",
    "auto_take_profit_adjust_interval": 30,
    "auto_take_profit_reprice_threshold": 0.002,
    "auto_take_profit_spread_margin": 0.0005,
    # RIBS Quality Diversity Optimization
    "enable_ribs_optimization": True,
    "ribs_optimization_interval_hours": 6,
    "ribs_iterations_per_cycle": 200,
    "ribs_max_elite_strategies": 5,
    "ribs_auto_deploy_elites": True,
    "ribs_checkpoint_interval": 50,
}

OPTIMIZED_TRADING_CONFIG = {
    "confidence_threshold": 0.58,
    "max_positions": 3,
    "take_profit": 0.08,
    "stop_loss": 0.03,
    "min_confidence_diff": 0.12,
    "risk_per_trade": 0.01,
    "max_position_size": 0.08,
    "use_ensemble": True,
    "ensemble_min_agreement": 0.75,
    "optimized_indicators": BEST_INDICATORS,
    "market_regime_aware": True,
    "dynamic_position_sizing": True,
    "parallel_processing": True,
    "advanced_stop_loss": True,
    "periodic_rebuilding": True,
    "adaptive_risk_management": True,
    "continuous_training": True,
    "futures_enabled": False,
    "futures_initial_balance": 1000,
    "futures_max_leverage": 10,
    "futures_default_leverage": 3,
    "futures_risk_mode": "conservative",
    "futures_update_interval": 30,
    "futures_signal_weight": 0.3,
    "futures_manual_mode": True,
    "futures_selected_symbol": "BTCUSDT",
    "futures_manual_auto_trade": False,
    "futures_manual_leverage": 3,
    "futures_manual_default_notional": 50.0,
    "dynamic_threshold_floor": 0.4,
    "dynamic_threshold_ceiling": 0.6,
    "default_min_notional": 10.0,
    "min_notional_buffer": 1.1,
    "min_notional_overrides": BINANCE_MIN_NOTIONAL_OVERRIDES.copy(),
    "balance_cash_buffer": 1.01,
    "auto_take_profit_percent": 0.05,
    "auto_take_profit_time_in_force": "GTC",
    "auto_take_profit_adjust_interval": 30,
    "auto_take_profit_reprice_threshold": 0.002,
    "auto_take_profit_spread_margin": 0.0005,
}

TRADING_CONFIG.update(OPTIMIZED_TRADING_CONFIG)

# Override configuration from environment variables
import os

TRADING_CONFIG["futures_enabled"] = os.getenv(
    "ENABLE_FUTURES_TRADING", "0"
).lower() in ("1", "true", "yes")
TRADING_CONFIG["auto_trade_enabled"] = os.getenv(
    "ENABLE_AUTO_TRADING", "0"
).lower() in ("1", "true", "yes")
TRADING_CONFIG["futures_manual_auto_trade"] = os.getenv(
    "ENABLE_AUTO_TRADING", "0"
).lower() in ("1", "true", "yes")

# Set testnet mode from environment
testnet_override = os.getenv("USE_TESTNET", "").lower()
if testnet_override in ("0", "false", "no"):
    # Force live trading
    pass  # Keep default testnet=True for safety, but this will be overridden in trader initialization

indicator_selection_manager = IndicatorSelectionManager()


def get_indicator_selection(profile):
    return indicator_selection_manager.get_selection(profile)


def set_indicator_selection(profile, selections):
    return indicator_selection_manager.set_selection(profile, selections)


def is_indicator_enabled(profile, indicator):
    return indicator_selection_manager.is_indicator_enabled(profile, indicator)


def get_all_indicator_selections():
    return indicator_selection_manager.snapshot()


# ==================== SAFETY MANAGEMENT SYSTEM ====================
class SafetyManager:
    def __init__(
        self,
        initial_balance=0,
        max_daily_loss=0.10,
        max_position_size=0.15,
        max_consecutive_losses=3,
        volatility_threshold=0.08,
        api_failure_limit=5,
        breaker_cooldown_minutes=60,
        global_breaker_minutes=120,
    ):
        self.initial_balance = initial_balance
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.max_consecutive_losses = max_consecutive_losses
        self.volatility_threshold = volatility_threshold
        self.api_failure_limit = api_failure_limit
        self.breaker_cooldown_minutes = breaker_cooldown_minutes
        self.global_breaker_minutes = global_breaker_minutes

        self.daily_loss = 0.0
        self.daily_profit = 0.0
        self.symbol_loss_streak = defaultdict(int)
        self.circuit_breakers = {}
        self.api_failure_count = 0
        self.global_breaker_active = False
        self.global_breaker_reason = None
        self.global_breaker_release = None
        self.current_day = datetime.utcnow().date()
        self.start_of_day_balance = initial_balance
        self.lock = threading.RLock()

    def _reset_daily_if_needed(self, current_balance):
        today = datetime.utcnow().date()
        if today != self.current_day:
            self.current_day = today
            self.daily_loss = 0.0
            self.daily_profit = 0.0
            self.api_failure_count = 0
            self.symbol_loss_streak.clear()
            self.circuit_breakers.clear()
            self.start_of_day_balance = current_balance

            # Reset UserPortfolio daily_pnl for all users
            try:
                UserPortfolio.query.update({"daily_pnl": 0.0})
                db.session.commit()
                print(f"📊 Daily portfolio metrics reset for all users on {today}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to reset UserPortfolio daily_pnl: {e}")
                db.session.rollback()

    def _cleanup_breakers(self):
        if not self.circuit_breakers:
            return
        now = datetime.utcnow()
        expired = [
            symbol
            for symbol, info in self.circuit_breakers.items()
            if info.get("release_timestamp")
            and now.timestamp() >= info["release_timestamp"]
        ]
        for symbol in expired:
            self.circuit_breakers.pop(symbol, None)

        if self.global_breaker_active and self.global_breaker_release:
            if now.timestamp() >= self.global_breaker_release:
                self.global_breaker_active = False
                self.global_breaker_reason = None
                self.global_breaker_release = None

    def approve_trade(
        self,
        symbol,
        position_value,
        available_balance,
        market_stress=0.0,
        volatility=0.0,
        portfolio_health=1.0,
    ):
        with self.lock:
            self._reset_daily_if_needed(available_balance + position_value)
            self._cleanup_breakers()

            if self.global_breaker_active:
                return (
                    False,
                    f"Global circuit breaker active: {self.global_breaker_reason}",
                )

            breaker = self.circuit_breakers.get(symbol)
            if breaker:
                return (
                    False,
                    f"Circuit breaker active for {symbol}: {breaker.get('reason', 'cooldown')}",
                )

            max_position_allowed = available_balance * self.max_position_size
            if position_value > max_position_allowed:
                return (
                    False,
                    f"Position size ${position_value:.2f} exceeds limit ${max_position_allowed:.2f}",
                )

            max_loss_allowed = (
                self.start_of_day_balance * self.max_daily_loss
                if self.start_of_day_balance
                else available_balance * self.max_daily_loss
            )
            if abs(self.daily_loss) >= max_loss_allowed:
                return False, "Daily loss limit reached"

            if self.symbol_loss_streak[symbol] >= self.max_consecutive_losses:
                return False, f"Loss streak limit reached for {symbol}"

            if volatility > self.volatility_threshold and market_stress > 0.6:
                return False, "High volatility during stressed market"

            if portfolio_health < 0.5:
                return False, "Portfolio health too weak for new exposure"

            if self.api_failure_count >= self.api_failure_limit:
                return False, "API instability detected"

            return True, "approved"

    def register_trade_result(self, symbol, pnl):
        with self.lock:
            self.daily_loss += min(0.0, pnl)
            self.daily_profit += max(0.0, pnl)

            if pnl < 0:
                self.symbol_loss_streak[symbol] += 1
                if self.symbol_loss_streak[symbol] >= self.max_consecutive_losses:
                    self._activate_symbol_breaker(symbol, reason="loss_streak")
            else:
                self.symbol_loss_streak[symbol] = 0

    def _activate_symbol_breaker(self, symbol, reason="manual"):
        release_time = datetime.utcnow() + timedelta(
            minutes=self.breaker_cooldown_minutes
        )
        self.circuit_breakers[symbol] = {
            "reason": reason,
            "activated": datetime.utcnow().isoformat(),
            "release_time": release_time.isoformat(),
            "release_timestamp": release_time.timestamp(),
        }

    def trigger_global_breaker(self, reason="safety_violation"):
        with self.lock:
            self.global_breaker_active = True
            self.global_breaker_reason = reason
            release_time = datetime.utcnow() + timedelta(
                minutes=self.global_breaker_minutes
            )
            self.global_breaker_release = release_time.timestamp()

    def log_api_failure(self, error_message=None):
        with self.lock:
            self.api_failure_count += 1
            if self.api_failure_count >= self.api_failure_limit:
                self.trigger_global_breaker(
                    reason=error_message or "API failure limit reached"
                )

    def clear_api_failures(self):
        with self.lock:
            self.api_failure_count = 0

    def emergency_stop(self, trader, reason="safety_stop", current_prices=None):
        with self.lock:
            self.trigger_global_breaker(reason=reason)
        if hasattr(trader, "force_close_all_positions"):
            trader.force_close_all_positions(
                reason=reason, current_prices=current_prices
            )
        trader.trading_enabled = False
        trader.disable_real_trading(reason=reason)

    def get_status_snapshot(self):
        with self.lock:
            self._cleanup_breakers()
            return {
                "current_day": self.current_day.isoformat()
                if hasattr(self.current_day, "isoformat")
                else str(self.current_day),
                "daily_loss": self.daily_loss,
                "daily_profit": self.daily_profit,
                "max_daily_loss": self.max_daily_loss,
                "max_position_size": self.max_position_size,
                "max_consecutive_losses": self.max_consecutive_losses,
                "symbol_loss_streak": dict(self.symbol_loss_streak),
                "circuit_breakers": self.circuit_breakers,
                "api_failure_count": self.api_failure_count,
                "api_failure_limit": self.api_failure_limit,
                "global_breaker_active": self.global_breaker_active,
                "global_breaker_reason": self.global_breaker_reason,
                "global_breaker_release": self.global_breaker_release,
                "volatility_threshold": self.volatility_threshold,
            }


# ==================== CRT (Composite Rhythm Trading) MODULE ====================
class CRTSignalGenerator:
    """
    Composite Rhythm Trading (CRT) Module
    Advanced multi-timeframe, multi-indicator signal generation system
    """

    def __init__(self):
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
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)

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


# ==================== ICT (INNER CIRCLE TRADER) MODULE ====================
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


# ==================== SMC (SMART MONEY CONCEPTS) MODULE ====================
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


# ==================== QUANTUM FUSION MOMENTUM ANALYTICS ENGINE ====================
class QuantumFusionMomentumEngine:
    """Advanced Quantum Fusion Momentum Analytics Engine for market analysis"""

    def __init__(self):
        self.feature_history = {}
        self.market_regime_history = {}
        self.velocity_cache = {}
        self.acceleration_cache = {}
        self.jerk_cache = {}
        self.max_history_size = 1000

    def compute_realtime_features(self, symbol, market_data):
        """Compute real-time QFM features for a symbol"""
        if not market_data or not isinstance(market_data, dict):
            return {}

        # Extract price data
        close_price = market_data.get("close", market_data.get("price", 0))
        volume = market_data.get("volume", 0)
        high = market_data.get("high", close_price)
        low = market_data.get("low", close_price)

        # Initialize symbol history if needed
        if symbol not in self.feature_history:
            self.feature_history[symbol] = deque(maxlen=self.max_history_size)
            self.velocity_cache[symbol] = deque(maxlen=self.max_history_size)
            self.acceleration_cache[symbol] = deque(maxlen=self.max_history_size)
            self.jerk_cache[symbol] = deque(maxlen=self.max_history_size)

        # Calculate QFM features
        features = self._calculate_qfm_features(symbol, close_price, volume, high, low)

        # Store in history
        self.feature_history[symbol].append(
            {
                "timestamp": time.time(),
                "features": features.copy(),
                "price": close_price,
                "volume": volume,
            }
        )

        return features

    def _calculate_qfm_features(self, symbol, price, volume, high, low):
        """Calculate comprehensive QFM features"""
        features = {}

        # Basic momentum calculations
        features["price"] = price
        features["volume"] = volume

        # Calculate velocity (rate of price change)
        velocity = self._calculate_velocity(symbol, price)
        features["velocity"] = velocity

        # Calculate acceleration (rate of velocity change)
        acceleration = self._calculate_acceleration(symbol, velocity)
        features["acceleration"] = acceleration

        # Calculate jerk (rate of acceleration change)
        jerk = self._calculate_jerk(symbol, acceleration)
        features["jerk"] = jerk

        # Volume pressure analysis
        volume_pressure = self._calculate_volume_pressure(symbol, volume, price)
        features["volume_pressure"] = volume_pressure

        # Trend confidence based on momentum consistency
        trend_confidence = self._calculate_trend_confidence(symbol)
        features["trend_confidence"] = trend_confidence

        # Market regime score (0-1, higher = more trending)
        regime_score = self._calculate_regime_score(features)
        features["regime_score"] = regime_score

        # Entropy measure for market randomness
        entropy = self._calculate_market_entropy(symbol)
        features["entropy"] = entropy

        # Volatility measure
        volatility = self._calculate_volatility(symbol, high, low)
        features["volatility"] = volatility

        return features

    def _calculate_velocity(self, symbol, current_price):
        """Calculate price velocity (momentum)"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 2:
            return 0.0

        # Use exponential moving average for smoother velocity
        prices = [h["price"] for h in history[-10:]]  # Last 10 points

        if len(prices) < 2:
            return 0.0

        # Calculate rate of change
        recent_change = (
            (current_price - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        )

        # Store velocity
        self.velocity_cache[symbol].append(recent_change)

        return recent_change

    def _calculate_acceleration(self, symbol, current_velocity):
        """Calculate acceleration (change in momentum)"""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 2:
            return 0.0

        # Rate of change of velocity
        acceleration = current_velocity - velocities[-2]

        # Store acceleration
        self.acceleration_cache[symbol].append(acceleration)

        return acceleration

    def _calculate_jerk(self, symbol, current_acceleration):
        """Calculate jerk (change in acceleration)"""
        accelerations = list(self.acceleration_cache.get(symbol, []))

        if len(accelerations) < 2:
            return 0.0

        # Rate of change of acceleration
        jerk = current_acceleration - accelerations[-2]

        # Store jerk
        self.jerk_cache[symbol].append(jerk)

        return jerk

    def _calculate_volume_pressure(self, symbol, volume, price):
        """Calculate volume pressure indicator"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 5:
            return 0.0

        # Average volume over last 5 periods
        avg_volume = np.mean([h["volume"] for h in history[-5:]])

        if avg_volume == 0:
            return 0.0

        # Volume pressure: current volume relative to average
        volume_pressure = (volume - avg_volume) / avg_volume

        # Weight by price movement direction
        price_change = 0
        if len(history) >= 2:
            price_change = (price - history[-2]["price"]) / history[-2]["price"]

        # Positive pressure when volume increases with price movement
        volume_pressure *= 1 + abs(price_change)

        return volume_pressure

    def _calculate_trend_confidence(self, symbol):
        """Calculate trend confidence based on momentum consistency"""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 5:
            return 0.5

        # Check consistency of directional movement
        recent_velocities = velocities[-10:]

        # Count directional consistency
        positive_count = sum(1 for v in recent_velocities if v > 0)
        negative_count = sum(1 for v in recent_velocities if v < 0)

        # Confidence based on directional dominance
        total_directional = positive_count + negative_count
        if total_directional == 0:
            return 0.5

        confidence = max(positive_count, negative_count) / total_directional

        return confidence

    def _calculate_regime_score(self, features):
        """Calculate market regime score (0-1, higher = trending)"""
        velocity = abs(features.get("velocity", 0))
        acceleration = abs(features.get("acceleration", 0))
        trend_confidence = features.get("trend_confidence", 0.5)
        entropy = features.get("entropy", 0.5)

        # Regime score combines momentum strength and trend consistency
        momentum_strength = min(1.0, (velocity + acceleration) * 10)  # Scale and cap

        # Lower entropy = more ordered (trending) market
        order_factor = 1.0 - entropy

        # Combine factors
        regime_score = (
            momentum_strength * 0.4 + trend_confidence * 0.4 + order_factor * 0.2
        )

        return min(1.0, max(0.0, regime_score))

    def _calculate_market_entropy(self, symbol):
        """Calculate market entropy (randomness measure)"""
        history = self.feature_history.get(symbol, [])

        if len(history) < 10:
            return 0.5

        # Calculate price return distribution
        prices = [h["price"] for h in history[-20:]]
        returns = []

        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.5

        # Calculate entropy of return distribution
        try:
            # Discretize returns into bins
            bins = np.histogram(returns, bins=10)[0]
            bins = bins[bins > 0]  # Remove zero bins
            probs = bins / np.sum(bins)

            # Shannon entropy
            entropy = -np.sum(probs * np.log2(probs))

            # Normalize to 0-1 scale
            max_entropy = np.log2(len(bins))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.5

            return normalized_entropy

        except:
            return 0.5

    def _calculate_volatility(self, symbol, high, low):
        """Calculate price volatility"""
        if high == low:
            return 0.0

        # Range-based volatility
        range_volatility = (high - low) / ((high + low) / 2)

        # Historical volatility
        history = self.feature_history.get(symbol, [])
        if len(history) >= 5:
            recent_prices = [h["price"] for h in history[-5:]]
            price_std = np.std(recent_prices)
            price_mean = np.mean(recent_prices)

            if price_mean != 0:
                hist_volatility = price_std / price_mean
                # Combine range and historical volatility
                return (range_volatility + hist_volatility) / 2

        return range_volatility

    def get_market_regime(self, symbol):
        """Get current market regime classification"""
        features = self.get_latest_features(symbol)

        if not features:
            return "unknown"

        regime_score = features.get("regime_score", 0.5)
        trend_confidence = features.get("trend_confidence", 0.5)
        jerk = abs(features.get("jerk", 0))

        # Classify regime
        if regime_score > 0.7 and trend_confidence > 0.6:
            velocity = features.get("velocity", 0)
            return "trending_bull" if velocity > 0 else "trending_bear"
        elif jerk > 0.5:
            return "volatile"
        elif regime_score < 0.4:
            return "sideways"
        else:
            return "calm"

    def get_latest_features(self, symbol):
        """Get latest QFM features for a symbol"""
        history = self.feature_history.get(symbol, [])

        if not history:
            return {}

        return history[-1]["features"]

    def get_feature_history(self, symbol, limit=100):
        """Get historical QFM features for analysis"""
        history = self.feature_history.get(symbol, [])

        return list(history)[-limit:] if history else []

    def analyze_market_cycles(self, symbol):
        """Analyze market cycles using QFM features"""
        history = self.get_feature_history(symbol, 200)

        if len(history) < 20:
            return {"error": "Insufficient data for cycle analysis"}

        # Extract features over time
        timestamps = [h["timestamp"] for h in history]
        velocities = [h["features"]["velocity"] for h in history]
        accelerations = [h["features"]["acceleration"] for h in history]
        regime_scores = [h["features"]["regime_score"] for h in history]

        # Detect cycles using acceleration changes
        cycle_analysis = {
            "cycle_length_avg": self._calculate_average_cycle_length(accelerations),
            "current_phase": self._determine_current_cycle_phase(accelerations),
            "cycle_strength": np.std(accelerations),
            "regime_transitions": self._count_regime_transitions(regime_scores),
            "momentum_cycles": self._analyze_momentum_cycles(velocities),
        }

        return cycle_analysis

    def _calculate_average_cycle_length(self, accelerations):
        """Calculate average cycle length from acceleration data"""
        if len(accelerations) < 10:
            return 0

        # Find zero crossings in acceleration (cycle boundaries)
        zero_crossings = []
        for i in range(1, len(accelerations)):
            if accelerations[i - 1] * accelerations[i] < 0:  # Sign change
                zero_crossings.append(i)

        if len(zero_crossings) < 2:
            return len(accelerations)  # Default to full period

        # Calculate cycle lengths
        cycle_lengths = []
        for i in range(1, len(zero_crossings)):
            cycle_lengths.append(zero_crossings[i] - zero_crossings[i - 1])

        return np.mean(cycle_lengths) if cycle_lengths else len(accelerations)

    def _determine_current_cycle_phase(self, accelerations):
        """Determine current position in market cycle"""
        if len(accelerations) < 5:
            return "unknown"

        recent_acc = accelerations[-5:]

        # Analyze recent acceleration trend
        if all(a > 0 for a in recent_acc):
            return "acceleration_phase"
        elif all(a < 0 for a in recent_acc):
            return "deceleration_phase"
        else:
            return "transition_phase"

    def _count_regime_transitions(self, regime_scores):
        """Count regime transitions over time"""
        if len(regime_scores) < 2:
            return 0

        transitions = 0
        threshold_high = 0.6
        threshold_low = 0.4

        for i in range(1, len(regime_scores)):
            prev_regime = (
                "high"
                if regime_scores[i - 1] > threshold_high
                else ("low" if regime_scores[i - 1] < threshold_low else "neutral")
            )
            curr_regime = (
                "high"
                if regime_scores[i] > threshold_high
                else ("low" if regime_scores[i] < threshold_low else "neutral")
            )

            if prev_regime != curr_regime:
                transitions += 1

        return transitions

    def _analyze_momentum_cycles(self, velocities):
        """Analyze momentum cycles"""
        if len(velocities) < 10:
            return {"cycles": 0, "strength": 0}

        # Find momentum cycles (direction changes)
        direction_changes = []
        for i in range(1, len(velocities)):
            if velocities[i - 1] * velocities[i] < 0:  # Direction change
                direction_changes.append(i)

        cycle_info = {
            "cycles": len(direction_changes),
            "average_length": np.mean(np.diff(direction_changes))
            if len(direction_changes) > 1
            else 0,
            "strength": np.std(velocities),
        }

        return cycle_info

    # ==================== STRATEGY MANAGER ====================
    """Generates Quantum Fusion Momentum features and discretionary signals."""

    def __init__(self, history_length=64):
        self.history_length = max(16, int(history_length))
        self.fast_span = 8
        self.slow_span = 21
        self.state = defaultdict(self._new_state)
        print("⚡ Quantum Fusion Momentum Engine Initialized")

    def _new_state(self):
        return {
            "prices": deque(maxlen=self.history_length),
            "volumes": deque(maxlen=self.history_length),
            "velocity": 0.0,
            "acceleration": 0.0,
            "jerk": 0.0,
            "ema_fast": None,
            "ema_slow": None,
            "metrics": {},
        }

    def _zero_metrics(self):
        return {
            "qfm_velocity": 0.0,
            "qfm_acceleration": 0.0,
            "qfm_jerk": 0.0,
            "qfm_volume_pressure": 0.0,
            "qfm_trend_confidence": 0.0,
            "qfm_regime_score": 0.0,
            "qfm_entropy": 0.0,
        }

    def reset_symbol(self, symbol):
        if symbol in self.state:
            self.state.pop(symbol, None)

    def compute_training_features(self, df):
        features = pd.DataFrame(index=df.index if df is not None else [])
        if df is None or df.empty:
            return features

        work = df.copy()
        for col in ["close", "volume"]:
            if col in work.columns:
                work[col] = pd.to_numeric(work[col], errors="coerce")

        close = (
            work["close"]
            .astype(float)
            .fillna(method="ffill")
            .fillna(method="bfill")
            .fillna(0)
        )
        volume = (
            work["volume"]
            .astype(float)
            .fillna(method="ffill")
            .fillna(method="bfill")
            .fillna(1.0)
            if "volume" in work.columns
            else pd.Series(1.0, index=close.index)
        )

        returns_1 = close.pct_change().replace([np.inf, -np.inf], 0).fillna(0)
        returns_3 = close.pct_change(periods=3).replace([np.inf, -np.inf], 0).fillna(0)
        returns_7 = close.pct_change(periods=7).replace([np.inf, -np.inf], 0).fillna(0)
        returns_14 = (
            close.pct_change(periods=14).replace([np.inf, -np.inf], 0).fillna(0)
        )

        velocity = (
            returns_1 * 0.45 + returns_3 * 0.30 + returns_7 * 0.15 + returns_14 * 0.10
        ).fillna(0)
        acceleration = velocity.diff().fillna(0)
        jerk = acceleration.diff().fillna(0)

        volume_ma = volume.rolling(12, min_periods=1).mean().replace(0, np.nan)
        volume_ratio = (volume / volume_ma).replace([np.inf, -np.inf], 1).fillna(1)
        price_direction = np.sign(close.diff().fillna(0))
        volume_pressure = ((volume_ratio - 1).clip(-3, 3) * price_direction).fillna(0)

        ema_fast = close.ewm(span=self.fast_span, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_span, adjust=False).mean()
        trend_delta = (ema_fast - ema_slow) / close.replace(0, np.nan)
        trend_confidence = np.tanh(trend_delta.fillna(0))

        returns_series = returns_1
        volatility = (
            returns_series.rolling(10, min_periods=2)
            .std()
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )
        entropy = (
            returns_series.rolling(10, min_periods=3)
            .apply(_directional_entropy, raw=True)
            .replace([np.inf, -np.inf], 0)
            .fillna(0)
        )

        regime_input = (
            (velocity * 50)
            - (volatility * 30)
            + (trend_confidence * 20)
            + (volume_pressure * 10)
        )
        regime_score = np.tanh(regime_input.fillna(0))

        features["qfm_velocity"] = velocity
        features["qfm_acceleration"] = acceleration
        features["qfm_jerk"] = jerk
        features["qfm_volume_pressure"] = volume_pressure
        features["qfm_trend_confidence"] = trend_confidence
        features["qfm_regime_score"] = regime_score
        features["qfm_entropy"] = entropy

        return features.fillna(0)

    def compute_realtime_features(self, symbol, current_data, historical_prices=None):
        symbol_key = symbol or "GLOBAL"
        state = self.state[symbol_key]

        price = None
        for key in ("price", "close"):
            if key in current_data and current_data[key] not in (None, ""):
                try:
                    price = float(current_data[key])
                    break
                except Exception:
                    continue

        volume = current_data.get("volume")
        try:
            volume = float(volume) if volume is not None else None
        except Exception:
            volume = None

        if historical_prices and not state["prices"]:
            for value in list(historical_prices)[-self.history_length :]:
                try:
                    seeded_price = float(value)
                except Exception:
                    continue
                if seeded_price > 0:
                    state["prices"].append(seeded_price)

        if price and price > 0:
            if not state["prices"] or price != state["prices"][-1]:
                state["prices"].append(price)
        elif not state["prices"] and price is not None:
            state["prices"].append(price)

        if volume is not None:
            state["volumes"].append(max(volume, 0.0))
        elif not state["volumes"]:
            state["volumes"].append(0.0)

        metrics = self._compute_metrics(state)
        state["metrics"] = metrics
        return metrics

    def generate_signal(self, symbol):
        state = self.state.get(symbol or "GLOBAL")
        if not state:
            return None
        metrics = state.get("metrics") or {}
        if not metrics:
            return None

        velocity = metrics["qfm_velocity"]
        acceleration = metrics["qfm_acceleration"]
        jerk = metrics["qfm_jerk"]
        volume_pressure = metrics["qfm_volume_pressure"]
        trend_confidence = metrics["qfm_trend_confidence"]
        regime_score = metrics["qfm_regime_score"]
        entropy = metrics["qfm_entropy"]

        bias = (
            (velocity * 120)
            + (acceleration * 80)
            + (trend_confidence * 40)
            + (volume_pressure * 25)
            + (regime_score * 35)
            + ((entropy - 0.5) * 20)
            - (abs(jerk) * 40)
        )

        strong_threshold = 0.8
        base_threshold = 0.35
        signal = "HOLD"

        if bias > strong_threshold and trend_confidence > 0 and volume_pressure > -0.1:
            signal = "STRONG_BUY"
        elif bias > base_threshold:
            signal = "BUY"
        elif bias < -strong_threshold and trend_confidence < 0 and volume_pressure < 0:
            signal = "STRONG_SELL"
        elif bias < -base_threshold:
            signal = "SELL"

        confidence = min(0.95, max(0.55, 0.55 + min(0.35, abs(bias))))
        if signal == "HOLD":
            confidence = min(confidence, 0.6)

        # Get current price from state
        current_price = state.get("prices", [0])[-1] if state.get("prices") else 0
        target_price = current_price * (
            1.02
            if signal in ["BUY", "STRONG_BUY"]
            else 0.98
            if signal in ["SELL", "STRONG_SELL"]
            else 1.0
        )
        stop_loss = current_price * (
            0.98
            if signal in ["BUY", "STRONG_BUY"]
            else 1.02
            if signal in ["SELL", "STRONG_SELL"]
            else 1.0
        )

        return {
            "symbol": symbol,
            "signal_type": "QFM",
            "confidence_score": float(confidence),
            "timestamp": datetime.now().isoformat(),
            "current_price": float(current_price),
            "target_price": float(target_price),
            "stop_loss": float(stop_loss),
            "time_frame": "MULTI_TIMEFRAME",
            "model_version": "QFM_v1.0",
            "reason_code": f"QFM_{signal}_{confidence:.2f}",
            "strategy": "QUANTUM_FUSION_MOMENTUM",
            "signal": signal,
            "confidence": float(round(confidence, 3)),
            "score": float(round(bias, 4)),
            "metrics": {k: float(round(v, 6)) for k, v in metrics.items()},
        }

    def _compute_metrics(self, state):
        prices = np.array(state["prices"], dtype=float)
        if prices.size < 2:
            metrics = self._zero_metrics()
            state["velocity"] = 0.0
            state["acceleration"] = 0.0
            state["jerk"] = 0.0
            return metrics

        returns = np.diff(prices) / np.where(prices[:-1] == 0, 1, prices[:-1])
        r1 = returns[-1] if returns.size else 0.0
        r3 = self._calc_return(prices, 3)
        r7 = self._calc_return(prices, 7)
        r14 = self._calc_return(prices, 14)
        velocity = (0.45 * r1) + (0.30 * r3) + (0.15 * r7) + (0.10 * r14)

        prev_velocity = state["velocity"]
        prev_acceleration = state["acceleration"]
        acceleration = velocity - prev_velocity
        jerk = acceleration - prev_acceleration

        alpha_fast = 2 / (self.fast_span + 1)
        alpha_slow = 2 / (self.slow_span + 1)
        price = prices[-1]
        state["ema_fast"] = (
            price
            if state["ema_fast"] is None
            else ((1 - alpha_fast) * state["ema_fast"] + alpha_fast * price)
        )
        state["ema_slow"] = (
            price
            if state["ema_slow"] is None
            else ((1 - alpha_slow) * state["ema_slow"] + alpha_slow * price)
        )

        ema_fast = state["ema_fast"]
        ema_slow = state["ema_slow"]
        trend_confidence = np.tanh(((ema_fast - ema_slow) / price) if price else 0.0)

        volumes = np.array(state["volumes"], dtype=float)
        if volumes.size >= 3:
            reference = np.mean(volumes[-min(10, volumes.size) :])
            volume_ratio = (volumes[-1] / reference) if reference else 1.0
        else:
            volume_ratio = 1.0
        volume_ratio = float(np.clip(volume_ratio, 0.1, 10.0))
        base_direction = r1 if r1 != 0 else velocity
        volume_pressure = float(
            np.clip((volume_ratio - 1.0) * np.sign(base_direction), -3.0, 3.0)
        )

        volatility = (
            float(np.std(returns[-min(10, returns.size) :])) if returns.size else 0.0
        )
        entropy = (
            float(_directional_entropy(returns[-min(10, returns.size) :]))
            if returns.size
            else 0.0
        )

        regime_input = (
            (velocity * 50)
            - (volatility * 30)
            + (trend_confidence * 20)
            + (volume_pressure * 10)
        )
        regime_score = float(np.tanh(regime_input))

        state["velocity"] = velocity
        state["acceleration"] = acceleration
        state["jerk"] = jerk

        metrics = {
            "qfm_velocity": float(velocity),
            "qfm_acceleration": float(acceleration),
            "qfm_jerk": float(jerk),
            "qfm_volume_pressure": float(volume_pressure),
            "qfm_trend_confidence": float(trend_confidence),
            "qfm_regime_score": float(regime_score),
            "qfm_entropy": float(entropy),
        }
        return metrics

    def _calc_return(self, prices, lookback):
        if prices.size <= 1:
            return 0.0
        idx = lookback + 1
        if prices.size >= idx:
            previous = prices[-idx]
            if previous:
                return (prices[-1] / previous) - 1
        previous = prices[-2]
        if not previous:
            return 0.0
        return (prices[-1] / previous) - 1


# ==================== PARALLEL PROCESSING SYSTEM ====================
strategy_manager = (
    StrategyManager()
)  # Initialize after QuantumFusionMomentumEngine class definition


class ParallelPredictionEngine:
    def __init__(self):
        self.num_cores = multiprocessing.cpu_count()
        self.max_workers = max(1, min(self.num_cores, 4))
        self.parallel_backend = "threading"
        print(
            f"🚀 Parallel Prediction Engine Initialized with {self.num_cores} cores"
            f" (using up to {self.max_workers} {self.parallel_backend} workers)"
        )

    def parallel_predict(self, symbols, market_data, ml_system):
        """Parallel prediction for all symbols using joblib"""
        try:

            def predict_single(symbol):
                try:
                    if symbol in market_data:
                        prediction = ml_system.predict_professional(
                            symbol, market_data[symbol]
                        )
                        return symbol, prediction
                    else:
                        self.logger.warning(f"Symbol {symbol} not found in market data")
                        return symbol, None
                except Exception as e:
                    self.logger.error(
                        f"Prediction failed for {symbol}: {str(e)}",
                        extra={
                            "symbol": symbol,
                            "error_type": type(e).__name__,
                            "market_data_available": symbol in market_data,
                        },
                    )
                    return symbol, None

            results = Parallel(n_jobs=self.max_workers, backend=self.parallel_backend)(
                delayed(predict_single)(symbol) for symbol in symbols
            )

            # Convert to dictionary
            predictions = {symbol: pred for symbol, pred in results if pred is not None}
            successful_predictions = len(predictions)
            total_symbols = len(symbols)

            self.logger.info(
                f"Parallel predictions completed: {successful_predictions}/{total_symbols} symbols successful"
            )

            if successful_predictions == 0:
                self.logger.warning("No successful predictions in parallel batch")

            return predictions

        except Exception as e:
            self.logger.error(
                f"Parallel prediction system failed: {str(e)}",
                extra={"total_symbols": len(symbols), "error_type": type(e).__name__},
            )
            # Fallback to sequential processing
            return self.sequential_predict(symbols, market_data, ml_system)

    def sequential_predict(self, symbols, market_data, ml_system):
        """Sequential fallback prediction"""
        predictions = {}
        for symbol in symbols:
            if symbol in market_data:
                pred = ml_system.predict_professional(symbol, market_data[symbol])
                if pred:
                    predictions[symbol] = pred
        return predictions

    def parallel_train_models(self, symbols, ml_system, use_real_data=True):
        """Parallel model training for multiple symbols"""
        try:

            def train_single(symbol):
                try:
                    success = ml_system.train_advanced_model(
                        symbol, use_real_data=use_real_data
                    )
                    return symbol, success
                except Exception as e:
                    print(f"❌ Training failed for {symbol}: {e}")
                    return symbol, False

            results = Parallel(n_jobs=self.max_workers, backend=self.parallel_backend)(
                delayed(train_single)(symbol) for symbol in symbols
            )

            success_count = sum(1 for _, success in results if success)
            print(
                f"✅ Parallel training completed: {success_count}/{len(symbols)} successful"
            )
            return success_count

        except Exception as e:
            print(
                f"❌ Parallel training error: {e} — falling back to sequential training"
            )
            return self._sequential_train_models(symbols, ml_system, use_real_data)

    def _sequential_train_models(self, symbols, ml_system, use_real_data):
        """Sequential fallback for training when parallel execution fails"""
        success_count = 0
        for symbol in symbols:
            try:
                success = ml_system.train_advanced_model(
                    symbol, use_real_data=use_real_data
                )
                if success:
                    success_count += 1
            except Exception as e:
                print(f"❌ Sequential training failed for {symbol}: {e}")
        print(
            f"✅ Sequential training completed: {success_count}/{len(symbols)} successful"
        )
        return success_count


# ==================== ADVANCED RISK MANAGEMENT SYSTEM ====================
class AdaptiveRiskManager:
    def __init__(self):
        self.risk_levels = {"conservative": 0.7, "moderate": 1.0, "aggressive": 1.3}
        self.current_risk_profile = "moderate"
        self.risk_adjustment_history = []
        self.volatility_regime = "NORMAL"
        self.market_stress_indicator = 0.0

    def calculate_market_stress(self, market_data, historical_data):
        """Calculate market stress indicator based on multiple factors"""
        try:
            stress_factors = []

            # Factor 1: Overall market volatility
            if historical_data:
                recent_prices = []
                # Support both dict-of-lists (multi-symbol) and single list/array inputs
                if isinstance(historical_data, dict):
                    for series in historical_data.values():
                        if series:
                            recent_prices.extend(
                                series[-10:]
                            )  # Last 10 prices per symbol
                elif isinstance(historical_data, (list, tuple, np.ndarray)):
                    recent_prices.extend(list(historical_data)[-10:])
                else:
                    # Gracefully handle unexpected types by attempting list() conversion
                    try:
                        recent_prices.extend(list(historical_data)[-10:])
                    except TypeError:
                        recent_prices = []

                if len(recent_prices) > 5:
                    returns = np.diff(np.log(recent_prices))
                    market_volatility = np.std(returns) if len(returns) > 1 else 0
                    stress_factors.append(min(market_volatility * 100, 1.0))

            # Factor 2: Correlation breakdown (during stress, correlations increase)
            correlation_stress = self.calculate_correlation_stress(market_data)
            stress_factors.append(correlation_stress)

            # Factor 3: Volume stress (unusual volume patterns)
            volume_stress = self.calculate_volume_stress(market_data)
            stress_factors.append(volume_stress)

            if stress_factors:
                self.market_stress_indicator = np.mean(stress_factors)
            else:
                self.market_stress_indicator = 0.0

            # Update volatility regime
            if self.market_stress_indicator > 0.7:
                self.volatility_regime = "HIGH_STRESS"
            elif self.market_stress_indicator > 0.4:
                self.volatility_regime = "ELEVATED"
            else:
                self.volatility_regime = "NORMAL"

            return self.market_stress_indicator

        except Exception as e:
            print(f"❌ Market stress calculation error: {e}")
            return 0.0

    def calculate_correlation_stress(self, market_data):
        """Calculate correlation stress - during market stress, correlations tend to 1"""
        try:
            if len(market_data) < 3:
                return 0.0

            price_changes = {}
            for symbol, data in market_data.items():
                if "change" in data:
                    price_changes[symbol] = (
                        data["change"] / 100
                    )  # Convert percentage to decimal

            if len(price_changes) < 3:
                return 0.0

            # Create correlation matrix
            symbols = list(price_changes.keys())
            changes_matrix = np.array([price_changes[sym] for sym in symbols])

            # Calculate average correlation
            if len(symbols) > 1:
                correlation_matrix = np.corrcoef(changes_matrix)
                avg_correlation = np.mean(np.abs(correlation_matrix))
                # High average correlation indicates stress
                return min(max(avg_correlation - 0.5, 0), 1.0) * 2

        except Exception as e:
            print(f"❌ Correlation stress calculation error: {e}")

        return 0.0

    def calculate_volume_stress(self, market_data):
        """Calculate volume-based stress indicator"""
        try:
            volume_changes = []
            for symbol, data in market_data.items():
                if "volume" in data and "volume_change" in data:
                    # Large volume changes indicate stress
                    vol_change = abs(data.get("volume_change", 0)) / 100
                    volume_changes.append(min(vol_change, 1.0))

            if volume_changes:
                return np.mean(volume_changes)
        except Exception as e:
            print(f"❌ Volume stress calculation error: {e}")

        return 0.0

    def adjust_risk_profile(
        self, portfolio_performance, market_volatility, economic_indicators=None
    ):
        """Dynamically adjust risk profile based on conditions"""
        previous_profile = self.current_risk_profile

        # Factor 1: Portfolio performance
        if portfolio_performance < -0.08:  # 8% drawdown
            self.current_risk_profile = "conservative"
        elif (
            portfolio_performance > 0.15 and market_volatility < 0.03
        ):  # Good performance, low volatility
            self.current_risk_profile = "aggressive"
        else:
            self.current_risk_profile = "moderate"

        # Factor 2: Market stress
        if self.market_stress_indicator > 0.6:
            self.current_risk_profile = "conservative"

        # Factor 3: Volatility regime
        if self.volatility_regime == "HIGH_STRESS":
            self.current_risk_profile = "conservative"

        if previous_profile != self.current_risk_profile:
            print(
                f"🔄 Risk profile changed: {previous_profile} -> {self.current_risk_profile}"
            )

        # Log adjustment
        self.risk_adjustment_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "previous_profile": previous_profile,
                "new_profile": self.current_risk_profile,
                "stress_indicator": self.market_stress_indicator,
                "portfolio_performance": portfolio_performance,
            }
        )

        # Keep only last 50 adjustments
        if len(self.risk_adjustment_history) > 50:
            self.risk_adjustment_history.pop(0)

        return (
            self.risk_adjustment_history[-1] if self.risk_adjustment_history else None
        )

    def get_risk_multiplier(self):
        """Get current risk multiplier based on risk profile"""
        return self.risk_levels.get(self.current_risk_profile, 1.0)


# ==================== ADVANCED STOP-LOSS SYSTEM ====================
class AdvancedStopLossSystem:
    def __init__(self):
        self.stop_loss_types = ["FIXED", "ATR", "TRAILING", "TIME", "VOLATILITY"]
        self.position_metrics = {}

    def calculate_multiple_stop_losses(
        self, symbol, entry_price, current_price, historical_prices, atr_value=None
    ):
        """Calculate multiple stop-loss levels"""
        stops = {}

        # 1. Fixed percentage stop-loss
        stops["fixed"] = entry_price * (1 - TRADING_CONFIG["stop_loss"])

        # 2. ATR-based stop-loss (2 ATR)
        if atr_value and atr_value > 0:
            stops["atr"] = current_price - (atr_value * 2)
        else:
            stops["atr"] = entry_price * 0.95  # Fallback

        # 3. Trailing stop-loss (5% from peak)
        if symbol in self.position_metrics:
            peak_price = self.position_metrics[symbol].get("peak_price", entry_price)
            stops["trailing"] = peak_price * 0.95
            # Update peak price
            if current_price > peak_price:
                self.position_metrics[symbol]["peak_price"] = current_price
        else:
            stops["trailing"] = entry_price * 0.95
            self.position_metrics[symbol] = {
                "peak_price": entry_price,
                "entry_time": datetime.now(),
            }

        # 4. Time-based stop-loss (7 days)
        if symbol in self.position_metrics:
            entry_time = self.position_metrics[symbol].get("entry_time", datetime.now())
            days_held = (datetime.now() - entry_time).days
            if days_held >= 7:
                stops["time"] = current_price * 0.99  # Very tight stop after 7 days
            else:
                stops["time"] = 0  # No time-based stop yet
        else:
            stops["time"] = 0

        # 5. Volatility-based stop-loss
        if len(historical_prices) >= 20:
            volatility = np.std(np.diff(np.log(historical_prices[-20:]))) * np.sqrt(365)
            vol_stop = current_price * (1 - (volatility * 3))  # 3x volatility
            stops["volatility"] = max(vol_stop, entry_price * 0.90)  # Cap at 10% loss
        else:
            stops["volatility"] = entry_price * 0.95

        return stops

    def should_trigger_stop_loss(self, symbol, current_price, position, stops):
        """Check if any stop-loss should be triggered"""
        triggered_stops = []

        # Fixed stop-loss
        if current_price <= stops["fixed"]:
            triggered_stops.append(("FIXED", stops["fixed"]))

        # ATR stop-loss
        if current_price <= stops["atr"]:
            triggered_stops.append(("ATR", stops["atr"]))

        # Trailing stop-loss
        if stops["trailing"] > 0 and current_price <= stops["trailing"]:
            triggered_stops.append(("TRAILING", stops["trailing"]))

        # Time stop-loss
        if stops["time"] > 0 and current_price <= stops["time"]:
            triggered_stops.append(("TIME", stops["time"]))

        # Volatility stop-loss
        if current_price <= stops["volatility"]:
            triggered_stops.append(("VOLATILITY", stops["volatility"]))

        if triggered_stops:
            # Return the most conservative (lowest) stop-loss
            triggered_stops.sort(key=lambda x: x[1])
            return triggered_stops[0]

        return None


# ==================== ULTIMATE ENSEMBLE SYSTEM ====================
class UltimateEnsembleSystem:
    def __init__(self, models_dir="ultimate_models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        self.ensemble_models = {}
        self.meta_model = None
        self.correlation_matrix = {}
        self.market_regime = "NEUTRAL"
        self.ensemble_logs = []
        self.last_rebuild_time = None
        self.rebuild_interval_hours = 24  # Daily rebuilding

    def log_ensemble(self, message, level="INFO"):
        """Log ensemble activities"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        self.ensemble_logs.append(log_entry)
        level_upper = str(level).upper()
        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_component_event(
            "ENSEMBLE", message, level=level_mapping.get(level_upper, logging.INFO)
        )
        if level_mapping.get(level_upper, logging.INFO) <= logging.INFO:
            print(f"🎯 ULTIMATE ENSEMBLE [{level_upper}]: {message}")

        # Keep only last 50 logs
        if len(self.ensemble_logs) > 50:
            self.ensemble_logs.pop(0)

    def should_rebuild_ensemble(self):
        """Check if ensemble should be rebuilt based on time"""
        if not self.last_rebuild_time:
            return True

        hours_since_rebuild = (
            datetime.now() - self.last_rebuild_time
        ).total_seconds() / 3600
        return hours_since_rebuild >= self.rebuild_interval_hours

    def periodic_ensemble_rebuilding(self, historical_predictions, actual_movements):
        """Periodic ensemble rebuilding system"""
        if not self.should_rebuild_ensemble():
            return False

        self.log_ensemble("Starting periodic ensemble rebuilding...")

        try:
            success = self.build_meta_model(historical_predictions, actual_movements)
            if success:
                self.last_rebuild_time = datetime.now()
                self.log_ensemble(
                    "✅ Periodic ensemble rebuilding completed successfully"
                )
                return True
            else:
                self.log_ensemble("❌ Periodic ensemble rebuilding failed", "ERROR")
                return False

        except Exception as e:
            self.log_ensemble(f"❌ Ensemble rebuilding error: {e}", "ERROR")
            return False

    def build_meta_model(self, historical_predictions, actual_movements):
        """Build meta-model that learns from ensemble predictions"""
        try:
            if len(historical_predictions) < 50:
                return False

            # Prepare features from historical predictions
            X = []
            y = []

            for i in range(len(historical_predictions) - 1):
                features = []

                # Aggregate prediction features
                pred_data = historical_predictions[i]
                actual_move = actual_movements[i + 1]

                # Feature engineering
                buy_signals = sum(
                    1
                    for p in pred_data.values()
                    if p.get("signal") in ["BUY", "STRONG_BUY"]
                )
                total_signals = len(pred_data)
                buy_ratio = buy_signals / total_signals if total_signals > 0 else 0.5
                features.append(buy_ratio)

                avg_confidence = np.mean(
                    [p.get("confidence", 0.5) for p in pred_data.values()]
                )
                features.append(avg_confidence)

                confidences = [p.get("confidence", 0.5) for p in pred_data.values()]
                conf_variance = np.var(confidences) if len(confidences) > 1 else 0
                features.append(conf_variance)

                strong_signals = sum(
                    1 for p in pred_data.values() if p.get("confidence", 0) > 0.7
                )
                strong_ratio = (
                    strong_signals / total_signals if total_signals > 0 else 0
                )
                features.append(strong_ratio)

                aligned = (
                    sum(
                        1
                        for p in pred_data.values()
                        if p.get("signal") in ["BUY", "STRONG_BUY"]
                    )
                    / total_signals
                )
                consensus_strength = abs(aligned - 0.5) * 2
                features.append(consensus_strength)

                X.append(features)
                y.append(1 if actual_move > 0 else 0)

            if len(X) < 20:
                return False

            # Train meta-model with cross-validation
            meta_model = RandomForestClassifier(n_estimators=100, random_state=42)
            scores = cross_val_score(meta_model, X, y, cv=5)
            avg_score = np.mean(scores)

            meta_model.fit(X, y)
            self.meta_model = meta_model

            self.log_ensemble(
                f"Meta-model rebuilt with CV accuracy: {avg_score:.4f} on {len(X)} samples"
            )
            return True

        except Exception as e:
            self.log_ensemble(f"Meta-model training error: {e}", "ERROR")
            return False

    def create_correlation_matrix(self, predictions_data):
        """Enhanced correlation matrix with parallel processing"""
        try:
            prediction_frames = []
            signal_score_map = {
                "STRONG_BUY": 2,
                "BUY": 1,
                "HOLD": 0,
                "SELL": -1,
                "STRONG_SELL": -2,
            }

            for symbol, predictions in predictions_data.items():
                if not isinstance(predictions, dict):
                    continue

                pred_block = None
                for key in (
                    "ultimate_ensemble",
                    "optimized_ensemble",
                    "professional_ensemble",
                ):
                    block = predictions.get(key)
                    if isinstance(block, dict) and block.get("signal"):
                        pred_block = block
                        break

                if not pred_block:
                    continue

                signal = pred_block.get("signal", "HOLD")
                confidence = float(pred_block.get("confidence", 0.0) or 0.0)
                signal_strength = signal_score_map.get(signal, 0) * confidence

                if signal_strength == 0 and confidence <= 0:
                    continue

                prediction_frames.append(
                    {
                        "symbol": symbol,
                        "signal_strength": signal_strength,
                        "confidence": confidence,
                    }
                )

            if len(prediction_frames) > 3:
                df = pd.DataFrame(prediction_frames)
                correlation_data = {}

                for _, row1 in df.iterrows():
                    symbol1 = row1["symbol"]
                    correlation_data[symbol1] = {}
                    for _, row2 in df.iterrows():
                        symbol2 = row2["symbol"]
                        if symbol1 == symbol2:
                            continue
                        corr = row1["signal_strength"] * row2["signal_strength"]
                        correlation_data[symbol1][symbol2] = corr

                self.correlation_matrix = correlation_data
                self.log_ensemble(
                    f"Correlation matrix updated with {len(correlation_data)} symbols"
                )
                return True

            # Clear correlation matrix if insufficient data so status reflects reality
            if prediction_frames:
                self.log_ensemble(
                    f"Correlation matrix skipped — need >=4 predictions, received {len(prediction_frames)}",
                    "DEBUG",
                )
            self.correlation_matrix = {}

        except Exception as e:
            self.correlation_matrix = {}
            self.log_ensemble(f"Correlation matrix error: {e}", "ERROR")

        return False

    def get_ensemble_prediction(self, current_predictions, market_data):
        """Ultimate ensemble prediction combining all models"""
        try:
            if not current_predictions:
                return None

            # Calculate ensemble metrics with parallel processing
            buy_votes = 0
            sell_votes = 0
            total_confidence = 0
            weighted_buy = 0
            weighted_sell = 0
            total_weight = 0

            for symbol, predictions in current_predictions.items():
                if predictions and "professional_ensemble" in predictions:
                    pred_data = predictions["professional_ensemble"]
                    signal = pred_data["signal"]
                    confidence = pred_data["confidence"]
                    weight = MARKET_CAP_WEIGHTS.get(symbol, 0.5)

                    if signal in ["BUY", "STRONG_BUY"]:
                        buy_votes += 1
                        weighted_buy += confidence * weight
                    else:
                        sell_votes += 1
                        weighted_sell += confidence * weight

                    total_confidence += confidence
                    total_weight += weight

            total_votes = buy_votes + sell_votes
            if total_votes == 0:
                return None

            # Enhanced ensemble calculation
            buy_ratio = buy_votes / total_votes
            sell_ratio = sell_votes / total_votes
            avg_confidence = total_confidence / total_votes if total_votes > 0 else 0.5

            weighted_consensus = (
                (weighted_buy - weighted_sell) / total_weight if total_weight > 0 else 0
            )

            # Advanced signal determination
            if weighted_consensus > 0.15 and buy_ratio > 0.7:
                ensemble_signal = "STRONG_BUY"
                ensemble_confidence = min(0.95, (weighted_consensus + 1) / 2)
            elif weighted_consensus > 0.08 and buy_ratio > 0.6:
                ensemble_signal = "BUY"
                ensemble_confidence = min(0.85, (weighted_consensus + 1) / 2)
            elif weighted_consensus < -0.15 and sell_ratio > 0.7:
                ensemble_signal = "STRONG_SELL"
                ensemble_confidence = min(0.95, (-weighted_consensus + 1) / 2)
            elif weighted_consensus < -0.08 and sell_ratio > 0.6:
                ensemble_signal = "SELL"
                ensemble_confidence = min(0.85, (-weighted_consensus + 1) / 2)
            else:
                ensemble_signal = "HOLD"
                ensemble_confidence = 0.5

            # Meta-model boost
            meta_boost = 0
            if self.meta_model and len(current_predictions) >= 3:
                try:
                    features = []
                    buy_signals = sum(
                        1
                        for p in current_predictions.values()
                        if p
                        and p.get("professional_ensemble", {}).get("signal")
                        in ["BUY", "STRONG_BUY"]
                    )
                    total_signals = len(current_predictions)
                    buy_ratio = buy_signals / total_signals
                    features.append(buy_ratio)

                    confidences = [
                        p.get("professional_ensemble", {}).get("confidence", 0.5)
                        for p in current_predictions.values()
                        if p
                    ]
                    avg_conf = np.mean(confidences) if confidences else 0.5
                    features.append(avg_conf)

                    conf_var = np.var(confidences) if len(confidences) > 1 else 0
                    features.append(conf_var)

                    strong_signals = sum(1 for c in confidences if c > 0.7)
                    strong_ratio = (
                        strong_signals / total_signals if total_signals > 0 else 0
                    )
                    features.append(strong_ratio)

                    consensus = abs(buy_ratio - 0.5) * 2
                    features.append(consensus)

                    meta_pred = self.meta_model.predict_proba([features])[0]
                    meta_confidence = max(meta_pred)
                    meta_boost = (meta_confidence - 0.5) * 0.3

                except Exception as e:
                    self.log_ensemble(f"Meta-model prediction error: {e}", "WARNING")

            final_confidence = min(0.95, ensemble_confidence + meta_boost)

            ensemble_result = {
                "signal": ensemble_signal,
                "confidence": final_confidence,
                "buy_ratio": buy_ratio,
                "sell_ratio": sell_ratio,
                "weighted_consensus": weighted_consensus,
                "total_models": total_votes,
                "meta_boost": meta_boost,
                "market_regime": self.market_regime,
                "correlation_strength": len(self.correlation_matrix)
                / len(current_predictions)
                if current_predictions
                else 0,
            }

            self.log_ensemble(
                f"Ensemble: {ensemble_signal} (Conf: {final_confidence:.3f}, "
                f"Buy%: {buy_ratio:.1%}, Consensus: {weighted_consensus:.3f})"
            )

            return ensemble_result

        except Exception as e:
            self.log_ensemble(f"Ensemble prediction error: {e}", "ERROR")
            return None

    def analyze_market_regime_advanced(self, market_data, historical_data):
        """Ultimate market regime analysis"""
        try:
            if not historical_data:
                return "NEUTRAL"

            if isinstance(historical_data, list):
                if historical_data and isinstance(historical_data[0], dict):
                    converted = {}
                    for entry in historical_data:
                        symbol = entry.get("symbol")
                        price = entry.get("close")
                        if price is None:
                            price = entry.get("price")
                        if symbol and price is not None:
                            converted.setdefault(symbol, []).append(float(price))
                    historical_data = converted
                else:
                    self.log_ensemble(
                        "Market regime analysis skipped: unsupported historical list format",
                        "WARNING",
                    )
                    return "NEUTRAL"
            elif not isinstance(historical_data, dict):
                self.log_ensemble(
                    "Market regime analysis skipped: unsupported historical data type",
                    "WARNING",
                )
                return "NEUTRAL"

            if len(historical_data) == 0:
                return "NEUTRAL"

            # Multi-timeframe analysis
            regimes = []

            for symbol in list(historical_data.keys())[:5]:  # Analyze top 5 symbols
                if symbol in historical_data and len(historical_data[symbol]) >= 50:
                    prices = np.array(historical_data[symbol][-50:])

                    # Trend analysis
                    x = np.arange(len(prices))
                    slope, _, r_value, _, _ = stats.linregress(x, prices)
                    trend_strength = abs(r_value)

                    if trend_strength > 0.7:
                        regime = (
                            "STRONG_TREND_BULL" if slope > 0 else "STRONG_TREND_BEAR"
                        )
                    elif trend_strength > 0.4:
                        regime = "WEAK_TREND_BULL" if slope > 0 else "WEAK_TREND_BEAR"
                    else:
                        regime = "SIDEWAYS"

                    regimes.append(regime)

            if not regimes:
                return "NEUTRAL"

            # Determine overall regime
            strong_bull_count = regimes.count("STRONG_TREND_BULL")
            strong_bear_count = regimes.count("STRONG_TREND_BEAR")

            if strong_bull_count >= 3:
                self.market_regime = "STRONG_BULL"
            elif strong_bear_count >= 3:
                self.market_regime = "STRONG_BEAR"
            elif "SIDEWAYS" in regimes and regimes.count("SIDEWAYS") >= 3:
                self.market_regime = "CONSOLIDATION"
            else:
                self.market_regime = "MIXED"

            return self.market_regime

        except Exception as e:
            self.log_ensemble(f"Market regime analysis error: {e}", "ERROR")
            return "NEUTRAL"


# ==================== PROFESSIONAL PERSISTENCE SYSTEM ====================


# ==================== ULTIMATE ML TRAINING SYSTEM ====================
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

            close = (
                close.astype(float)
                .fillna(method="ffill")
                .fillna(method="bfill")
                .fillna(0)
            )
            high = high.astype(float).fillna(close)
            low = low.astype(float).fillna(close)
            open_price = open_price.astype(float).fillna(close)
            volume = (
                volume.astype(float)
                .fillna(method="ffill")
                .fillna(method="bfill")
                .fillna(0)
            )

            features = pd.DataFrame(index=index)

            previous_close = close.shift(1).replace(0, np.nan)
            features["price_change"] = (
                close.pct_change().replace([np.inf, -np.inf], 0).fillna(0)
            )
            features["price_momentum"] = (close - close.shift(5)).fillna(0)
            features["log_return"] = (
                np.log(close.divide(previous_close))
                .replace([np.inf, -np.inf], 0)
                .fillna(0)
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

            atr_supertrend = (
                atr_supertrend.fillna(method="ffill").fillna(method="bfill").fillna(0)
            )
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

            supertrend = (
                supertrend.fillna(method="ffill").fillna(method="bfill").fillna(close)
            )
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

    def train_ultimate_model(self, symbol, data=None, use_real_data=True):
        """Train ultimate model with parallel processing and ensemble - BUG FIXED VERSION"""
        try:
            self.log_training(symbol, "🚀 Starting ULTIMATE model training...", 5)

            # Get data if not provided
            if data is None:
                if use_real_data:
                    data = self.get_real_historical_data(symbol, years=2, interval="1d")
                else:
                    data = self.generate_fallback_data(symbol, years=2)

            log_component_debug(
                "TRAINING",
                "Historical dataset prepared",
                {
                    "symbol": symbol,
                    "records": len(data) if data is not None else 0,
                    "use_real_data": bool(use_real_data),
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
                except:
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
            except:
                models["random_forest"] = RandomForestClassifier(
                    n_estimators=50, random_state=42
                )

            try:
                models["gradient_boosting"] = GradientBoostingClassifier(
                    n_estimators=80, max_depth=8, random_state=42
                )
            except:
                models["gradient_boosting"] = GradientBoostingClassifier(
                    n_estimators=50, random_state=42
                )

            try:
                models["logistic"] = LogisticRegression(
                    random_state=42, max_iter=500, n_jobs=-1
                )
            except:
                models["logistic"] = LogisticRegression(random_state=42, max_iter=200)

            try:
                models["svc"] = SVC(probability=True, random_state=42, kernel="rbf")
            except:
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
                best_model_name = max(model_performances, key=model_performances.get)
                voting_clf = trained_models[best_model_name]
                ensemble_score = model_performances[best_model_name]

            # Feature importance from best model
            feature_importance = {}
            if hasattr(voting_clf, "feature_importances_"):
                feature_importance = dict(
                    zip(feature_cols, voting_clf.feature_importances_)
                )
            else:
                # Equal importance if not available
                feature_importance = {
                    col: 1.0 / len(feature_cols) for col in feature_cols
                }

            # Save ultimate model
            model_path = os.path.join(self.models_dir, f"{symbol}_ultimate_model.pkl")
            model_data = {
                "ensemble_model": voting_clf,
                "individual_models": trained_models,
                "model_performances": model_performances,
                "ensemble_accuracy": ensemble_score,
                "feature_cols": feature_cols,
                "symbol": symbol,
                "feature_importance": feature_importance,
                "training_date": datetime.now().isoformat(),
                "data_points": len(X),
                "feature_count": len(feature_cols),
                "data_source": "BINANCE_REAL" if use_real_data else "SYNTHETIC",
                "model_type": "ULTIMATE_ENSEMBLE",
                "target_classes": "ENHANCED_MULTI_CLASS",
            }

            joblib.dump(model_data, model_path)

            self.models[symbol] = model_data
            self._save_training_metrics(
                symbol,
                ensemble_score,
                feature_cols,
                feature_importance,
                model_performances,
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
            bot_logger.exception("Ultimate training failed for symbol %s", symbol)
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
                    bot_logger.exception(
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
        """Get real historical data from Binance - ULTIMATE VERSION"""
        try:
            self.log_training(
                symbol,
                f"📊 Fetching {years} years of {interval} data from Binance...",
                10,
            )

            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)

            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)

            url = "https://api.binance.com/api/v3/klines"
            all_data = []
            current_start = start_ts

            while current_start < end_ts:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_ts,
                    "limit": 1000,
                }

                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code != 200:
                        self.log_training(
                            symbol, f"❌ API Error: {response.status_code}", 0
                        )
                        break

                    data = response.json()
                    if not data:
                        break

                    all_data.extend(data)

                    current_start = data[-1][0] + 1

                    progress = min(50, 10 + (len(all_data) / 1000) * 40)
                    self.log_training(
                        symbol, f"📥 Downloaded {len(all_data)} candles...", progress
                    )

                    if len(data) < 1000:
                        break

                    time.sleep(0.2)

                except Exception as e:
                    self.log_training(symbol, f"❌ Request error: {e}", 0)
                    break

            if not all_data:
                self.log_training(symbol, "❌ No data received from Binance", 0)
                return self.generate_fallback_data(symbol, years)

            # Convert to DataFrame
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

            self.log_training(symbol, f"✅ Successfully loaded {len(df)} records", 60)
            return df[["date", "open", "high", "low", "close", "volume"]]

        except Exception as e:
            self.log_training(symbol, f"❌ Historical data error: {e}", 0)
            return self.generate_fallback_data(symbol, years)

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

    def _save_training_metrics(
        self, symbol, accuracy, features, feature_importance, model_performances=None
    ):
        """Save ultimate training metrics"""
        try:
            metrics = {
                "symbol": symbol,
                "accuracy": accuracy,
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

                prediction_proba = model.predict_proba([features])[0]
                prediction = model.predict([features])[0]

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

            base_prediction = {
                "ultimate_ensemble": {
                    "signal": signal,
                    "confidence": float(confidence),
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

            self.log_training(
                symbol, "⚠️ No saved model detected, generating fallback model...", 0
            )
            trained = self.train_ultimate_model(symbol, use_real_data=False)
            if not trained:
                self.log_training(symbol, "❌ Fallback model training failed", 0)
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
                    df["open_interest"]
                    .fillna(method="ffill")
                    .fillna(method="bfill")
                    .fillna(0)
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
                    vol_delta.cumsum().fillna(method="ffill").fillna(0)
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
        except:
            return "Unknown"

    def load_models(self, symbol=None):
        """Load ultimate models"""
        try:
            if symbol:
                model_path = os.path.join(
                    self.models_dir, f"{symbol}_ultimate_model.pkl"
                )
                if os.path.exists(model_path):
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
                        return True
                    except Exception as e:
                        if "numpy._core" in str(e):
                            self.log_training(
                                symbol,
                                f"⚠️ Model incompatible with current NumPy version (numpy._core issue), skipping",
                                0,
                            )
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

    def comprehensive_backtest(self, symbol, **kwargs):
        result = super().comprehensive_backtest(symbol, **kwargs)
        if isinstance(result, dict):
            result["model_type"] = "OPTIMIZED"
            result["indicators"] = self.optimized_indicators
        return result

    def remove_symbol(self, symbol, *, permanent=False):
        return super().remove_symbol(symbol, permanent=permanent)


# ==================== FUTURES TRADING MODULE ====================
class FuturesTradingModule:
    """
    Comprehensive Futures Trading Module
    Supports perpetual futures with leverage management, funding rates, and futures-specific indicators
    """

    def __init__(self, max_leverage=10, default_leverage=3, risk_mode="conservative"):
        self.max_leverage = max_leverage
        self.default_leverage = default_leverage
        self.risk_mode = risk_mode
        self.positions = {}
        self.leverage_settings = {}
        self.funding_rates = {}
        self.liquidation_buffer = 0.05
        self.futures_indicators = [
            "funding_rate",
            "open_interest",
            "liquidations",
            "basis",
            "long_short_ratio",
            "cumulative_volume_delta",
            "futures_basis",
        ]

        self.futures_config = {
            "max_leverage": max_leverage,
            "default_leverage": default_leverage,
            "auto_leverage_adjustment": True,
            "funding_rate_aware": True,
            "liquidation_protection": True,
            "position_mode": "HEDGE",
            "margin_mode": "ISOLATED",
            "enable_auto_margin": True,
        }

        print(f"🎯 Futures Trading Module Initialized (Max Leverage: {max_leverage}x)")

    def calculate_futures_leverage(
        self, symbol, volatility, signal_confidence, market_regime
    ):
        """Dynamic leverage calculation based on multiple factors"""
        try:
            base_leverage = self.default_leverage
            vol_factor = self._calculate_volatility_factor(volatility)
            confidence_factor = min(signal_confidence * 2, 1.5)
            regime_factor = self._calculate_regime_factor(market_regime)
            funding_factor = self._calculate_funding_factor(symbol)

            final_leverage = (
                base_leverage
                * vol_factor
                * confidence_factor
                * regime_factor
                * funding_factor
            )
            final_leverage = max(1, min(final_leverage, self.max_leverage))
            final_leverage = round(final_leverage * 2) / 2

            self.leverage_settings[symbol] = final_leverage
            return final_leverage

        except Exception as e:
            print(f"❌ Leverage calculation error for {symbol}: {e}")
            return self.default_leverage

    def _calculate_volatility_factor(self, volatility):
        if volatility > 0.08:
            return 0.5
        elif volatility > 0.05:
            return 0.7
        elif volatility > 0.03:
            return 0.9
        return 1.1

    def _calculate_regime_factor(self, market_regime):
        regime_factors = {
            "STRONG_BULL": 1.2,
            "STRONG_BEAR": 1.1,
            "BULL": 1.1,
            "BEAR": 1.0,
            "SIDEWAYS": 0.8,
            "HIGH_VOL_SIDEWAYS": 0.6,
            "OVERBOUGHT": 0.7,
            "OVERSOLD": 0.9,
        }
        return regime_factors.get(market_regime, 1.0)

    def _calculate_funding_factor(self, symbol):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)
            if abs(funding_rate) > 0.0005:
                return 0.8
            if abs(funding_rate) > 0.0002:
                return 0.9
            return 1.0
        except Exception:
            return 1.0

    def calculate_futures_position_size(
        self,
        symbol,
        account_balance,
        leverage,
        entry_price,
        stop_loss_price,
        risk_per_trade=0.02,
    ):
        try:
            risk_amount = account_balance * risk_per_trade
            price_diff = abs(entry_price - stop_loss_price)

            if price_diff == 0:
                return 0, 0, 0

            position_size = (risk_amount / price_diff) * entry_price
            leveraged_size = position_size * leverage
            margin_required = leveraged_size / leverage

            if margin_required > account_balance * 0.8:
                margin_required = account_balance * 0.8
                leveraged_size = margin_required * leverage

            quantity = leveraged_size / entry_price

            return quantity, margin_required, leveraged_size

        except Exception as e:
            print(f"❌ Futures position sizing error: {e}")
            return 0, 0, 0

    def calculate_liquidation_price(
        self, symbol, entry_price, quantity, leverage, side
    ):
        try:
            if side.upper() == "LONG":
                liquidation_price = entry_price * (1 - (1 / leverage) + 0.005)
            else:
                liquidation_price = entry_price * (1 + (1 / leverage) - 0.005)
            return max(0, liquidation_price)
        except Exception as e:
            print(f"❌ Liquidation price calculation error: {e}")
            return entry_price * 0.5

    def update_funding_rates(self, symbol, funding_data):
        try:
            self.funding_rates[symbol] = funding_data.get("funding_rate", 0)
            print(f"💰 {symbol} Funding Rate: {self.funding_rates[symbol]:.6f}")
        except Exception as e:
            print(f"❌ Funding rate update error: {e}")

    def should_avoid_funding_period(self, symbol, hours_to_funding=1):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)
            if abs(funding_rate) > 0.0005:
                return True
            return False
        except Exception:
            return False

    def generate_futures_signals(self, symbol, market_data, historical_data):
        try:
            signals = []
            if historical_data is None or len(historical_data) < 50:
                return signals

            funding_signal = self._analyze_funding_rate(symbol)
            if funding_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_FUNDING",
                        "confidence_score": funding_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.05 if funding_signal["signal"] == "BUY" else 0.95),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.95 if funding_signal["signal"] == "BUY" else 1.05),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": funding_signal["strategy"],
                        "strategy": funding_signal["strategy"],
                        "signal": funding_signal["signal"],
                        "confidence": funding_signal["confidence"],
                    }
                )

            oi_signal = self._analyze_open_interest(market_data)
            if oi_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_OPEN_INTEREST",
                        "confidence_score": oi_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.03 if oi_signal["signal"] == "BUY" else 0.97),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.97 if oi_signal["signal"] == "BUY" else 1.03),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": oi_signal["strategy"],
                        "strategy": oi_signal["strategy"],
                        "signal": oi_signal["signal"],
                        "confidence": oi_signal["confidence"],
                    }
                )

            liq_signal = self._analyze_liquidations(market_data)
            if liq_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_LIQUIDATIONS",
                        "confidence_score": liq_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.02 if liq_signal["signal"] == "BUY" else 0.98),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.98 if liq_signal["signal"] == "BUY" else 1.02),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": liq_signal["strategy"],
                        "strategy": liq_signal["strategy"],
                        "signal": liq_signal["signal"],
                        "confidence": liq_signal["confidence"],
                    }
                )

            basis_signal = self._analyze_basis(market_data)
            if basis_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_BASIS",
                        "confidence_score": basis_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.025 if basis_signal["signal"] == "BUY" else 0.975),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.975 if basis_signal["signal"] == "BUY" else 1.025),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": basis_signal["strategy"],
                        "strategy": basis_signal["strategy"],
                        "signal": basis_signal["signal"],
                        "confidence": basis_signal["confidence"],
                    }
                )

            ls_signal = self._analyze_long_short_ratio(market_data)
            if ls_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_LS_RATIO",
                        "confidence_score": ls_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.015 if ls_signal["signal"] == "BUY" else 0.985),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.985 if ls_signal["signal"] == "BUY" else 1.015),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": ls_signal["strategy"],
                        "strategy": ls_signal["strategy"],
                        "signal": ls_signal["signal"],
                        "confidence": ls_signal["confidence"],
                    }
                )

            return signals

        except Exception as e:
            print(f"❌ Futures signal generation error: {e}")
            return []

    def _analyze_funding_rate(self, symbol):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)

            if funding_rate < -0.0003:
                return {
                    "strategy": "FUNDING_RATE_LONG_BIAS",
                    "signal": "BUY",
                    "confidence": 0.7,
                    "reason": f"Negative funding rate: {funding_rate:.4%}",
                }
            if funding_rate > 0.0003:
                return {
                    "strategy": "FUNDING_RATE_SHORT_BIAS",
                    "signal": "SELL",
                    "confidence": 0.7,
                    "reason": f"Positive funding rate: {funding_rate:.4%}",
                }
        except Exception:
            pass
        return None

    def _analyze_open_interest(self, market_data):
        try:
            oi_change = market_data.get("open_interest_change", 0)
            oi_value = market_data.get("open_interest", 0)

            if oi_change > 0.1 and oi_value > 1_000_000:
                return {
                    "strategy": "OPEN_INTEREST_BULLISH",
                    "signal": "BUY",
                    "confidence": 0.65,
                    "reason": f"Open interest rising: +{oi_change:.1%}",
                }
            if oi_change < -0.1 and oi_value > 1_000_000:
                return {
                    "strategy": "OPEN_INTEREST_BEARISH",
                    "signal": "SELL",
                    "confidence": 0.65,
                    "reason": f"Open interest falling: {oi_change:.1%}",
                }
        except Exception:
            pass
        return None

    def _analyze_liquidations(self, market_data):
        try:
            long_liq = market_data.get("long_liquidations", 0)
            short_liq = market_data.get("short_liquidations", 0)

            if long_liq > short_liq * 2:
                return {
                    "strategy": "LIQUIDATION_SHORT_SQUEEZE_POTENTIAL",
                    "signal": "BUY",
                    "confidence": 0.6,
                    "reason": f"Long liquidations dominant: {long_liq:.0f} vs {short_liq:.0f}",
                }
            if short_liq > long_liq * 2:
                return {
                    "strategy": "LIQUIDATION_LONG_SQUEEZE_POTENTIAL",
                    "signal": "SELL",
                    "confidence": 0.6,
                    "reason": f"Short liquidations dominant: {short_liq:.0f} vs {long_liq:.0f}",
                }
        except Exception:
            pass
        return None

    def _analyze_basis(self, market_data):
        try:
            basis = market_data.get("basis", 0)
            if basis > 0.002:
                return {
                    "strategy": "POSITIVE_BASIS_LONG",
                    "signal": "BUY",
                    "confidence": 0.65,
                    "reason": f"Positive basis: {basis:.3%}",
                }
            if basis < -0.002:
                return {
                    "strategy": "NEGATIVE_BASIS_SHORT",
                    "signal": "SELL",
                    "confidence": 0.65,
                    "reason": f"Negative basis: {basis:.3%}",
                }
        except Exception:
            pass
        return None

    def _analyze_long_short_ratio(self, market_data):
        try:
            ls_ratio = market_data.get("long_short_ratio", 1.0)
            if ls_ratio < 0.8:
                return {
                    "strategy": "LOW_LS_RATIO_LONG",
                    "signal": "BUY",
                    "confidence": 0.6,
                    "reason": f"Low L/S ratio: {ls_ratio:.2f}",
                }
            if ls_ratio > 1.2:
                return {
                    "strategy": "HIGH_LS_RATIO_SHORT",
                    "signal": "SELL",
                    "confidence": 0.6,
                    "reason": f"High L/S ratio: {ls_ratio:.2f}",
                }
        except Exception:
            pass
        return None

    def get_futures_dashboard_data(self, symbol=None):
        try:
            data = {
                "leverage_settings": self.leverage_settings,
                "funding_rates": self.funding_rates,
                "positions": self.positions,
                "config": self.futures_config,
            }

            if symbol:
                return {
                    "leverage": self.leverage_settings.get(
                        symbol, self.default_leverage
                    ),
                    "funding_rate": self.funding_rates.get(symbol, 0),
                    "position": self.positions.get(symbol),
                }

            return data
        except Exception as e:
            print(f"❌ Futures dashboard data error: {e}")
            return {}


# ==================== ENHANCED FUTURES ML SYSTEM ====================
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


# ==================== ULTIMATE AI TRADER ====================
class UltimateAIAutoTrader:
    def initialize_performance_analytics(self):
        """Initialize comprehensive performance analytics system"""
        self.performance_analytics = {
            "qfm_performance_correlation": {},
            "strategy_qfm_sensitivity": {},
            "market_regime_performance": {},
            "time_based_performance": {},
            "risk_adjusted_metrics": {},
            "predictive_analytics": {},
            "analytics_cache": {},
            "last_update": 0,
        }

    def analyze_qfm_strategy_performance(
        self, symbol=None, timeframe="1d", analysis_window=30
    ):
        """Analyze performance correlation between QFM metrics and strategy results"""
        analytics = {}

        # Get performance data
        performance_data = []
        for strategy_name in self.strategies:
            perf = self.strategy_performance.get(strategy_name, {})
            if perf.get("total_trades", 0) > 0:
                performance_data.append(
                    {
                        "strategy": strategy_name,
                        "win_rate": perf.get("win_rate", 0),
                        "total_pnl": perf.get("total_pnl", 0),
                        "total_trades": perf.get("total_trades", 0),
                        "avg_pnl": perf.get("total_pnl", 0)
                        / perf.get("total_trades", 0),
                    }
                )

        if not performance_data:
            return {"error": "Insufficient performance data"}

        # Analyze QFM correlations if QFM engine available
        if self.qfm_engine and hasattr(self.qfm_engine, "get_historical_features"):
            try:
                qfm_history = self.qfm_engine.get_historical_features(
                    symbol, timeframe, analysis_window
                )

                for strategy_data in performance_data:
                    strategy_name = strategy_data["strategy"]
                    correlations = self._calculate_qfm_performance_correlations(
                        qfm_history, strategy_name, analysis_window
                    )
                    analytics[f"{strategy_name}_qfm_correlation"] = correlations

            except Exception as e:
                analytics["qfm_analysis_error"] = str(e)

        # Calculate strategy comparisons
        analytics["strategy_comparison"] = self._compare_strategy_performance(
            performance_data
        )

        # Calculate risk-adjusted metrics
        analytics["risk_adjusted_metrics"] = self._calculate_risk_adjusted_metrics(
            performance_data
        )

        # Market regime analysis
        analytics["market_regime_analysis"] = self._analyze_market_regime_performance()

        return analytics

    def _calculate_qfm_performance_correlations(
        self, qfm_history, strategy_name, window
    ):
        """Calculate correlations between QFM features and strategy performance"""
        correlations = {}

        if not qfm_history:
            return correlations

        # Get strategy performance history
        strategy_trades = []
        for entry in self.ml_feedback.get("performance_history", []):
            if entry["strategy"] == strategy_name:
                strategy_trades.append(entry)

        if len(strategy_trades) < 10:
            return correlations

        # Calculate correlations for each QFM feature
        qfm_features = [
            "velocity",
            "acceleration",
            "jerk",
            "volume_pressure",
            "trend_confidence",
            "regime_score",
        ]

        for feature in qfm_features:
            feature_values = []
            pnl_values = []

            # Match QFM features with trade results by time
            for trade in strategy_trades[-window:]:
                trade_time = trade["timestamp"]
                # Find closest QFM feature data
                closest_feature = None
                min_time_diff = float("inf")

                for qfm_entry in qfm_history:
                    if "timestamp" in qfm_entry:
                        time_diff = abs(qfm_entry["timestamp"] - trade_time)
                        if (
                            time_diff < min_time_diff and time_diff < 3600
                        ):  # Within 1 hour
                            min_time_diff = time_diff
                            closest_feature = qfm_entry

                if closest_feature and feature in closest_feature:
                    feature_values.append(closest_feature[feature])
                    pnl_values.append(trade["pnl"])

            # Calculate correlation
            if len(feature_values) >= 5:
                try:
                    correlation = np.corrcoef(feature_values, pnl_values)[0, 1]
                    if not np.isnan(correlation):
                        correlations[feature] = {
                            "correlation": correlation,
                            "strength": abs(correlation),
                            "direction": "positive" if correlation > 0 else "negative",
                            "sample_size": len(feature_values),
                        }
                except:
                    continue

        return correlations

    def _compare_strategy_performance(self, performance_data):
        """Compare performance across different strategies"""
        if not performance_data:
            return {}

        # Sort by win rate
        by_win_rate = sorted(
            performance_data, key=lambda x: x["win_rate"], reverse=True
        )

        # Sort by total P&L
        by_pnl = sorted(performance_data, key=lambda x: x["total_pnl"], reverse=True)

        # Sort by average P&L
        by_avg_pnl = sorted(performance_data, key=lambda x: x["avg_pnl"], reverse=True)

        # Calculate performance rankings
        rankings = {}
        for i, strategy in enumerate(performance_data):
            strategy_name = strategy["strategy"]
            rankings[strategy_name] = {
                "win_rate_rank": next(
                    (
                        j + 1
                        for j, s in enumerate(by_win_rate)
                        if s["strategy"] == strategy_name
                    ),
                    0,
                ),
                "pnl_rank": next(
                    (
                        j + 1
                        for j, s in enumerate(by_pnl)
                        if s["strategy"] == strategy_name
                    ),
                    0,
                ),
                "avg_pnl_rank": next(
                    (
                        j + 1
                        for j, s in enumerate(by_avg_pnl)
                        if s["strategy"] == strategy_name
                    ),
                    0,
                ),
                "composite_score": (
                    strategy["win_rate"] * 0.4
                    + strategy["avg_pnl"] * 100 * 0.4
                    + strategy["total_pnl"] * 0.2
                ),
            }

        return {
            "rankings": rankings,
            "best_by_win_rate": by_win_rate[0]["strategy"] if by_win_rate else None,
            "best_by_pnl": by_pnl[0]["strategy"] if by_pnl else None,
            "best_by_avg_pnl": by_avg_pnl[0]["strategy"] if by_avg_pnl else None,
            "total_strategies": len(performance_data),
        }

    def _calculate_risk_adjusted_metrics(self, performance_data):
        """Calculate risk-adjusted performance metrics"""
        risk_metrics = {}

        for strategy_data in performance_data:
            strategy_name = strategy_data["strategy"]
            total_pnl = strategy_data["total_pnl"]
            total_trades = strategy_data["total_trades"]

            if total_trades == 0:
                continue

            # Get P&L history for volatility calculation
            pnl_history = []
            for entry in self.ml_feedback.get("performance_history", []):
                if entry["strategy"] == strategy_name:
                    pnl_history.append(entry["pnl"])

            if len(pnl_history) < 5:
                continue

            # Calculate risk metrics
            pnl_array = np.array(pnl_history)
            volatility = np.std(pnl_array)
            avg_pnl = np.mean(pnl_array)
            max_drawdown = self._calculate_max_drawdown(pnl_history)

            # Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = avg_pnl / volatility if volatility > 0 else 0

            # Sortino ratio (downside deviation)
            downside_returns = pnl_array[pnl_array < 0]
            downside_deviation = (
                np.std(downside_returns) if len(downside_returns) > 0 else 0
            )
            sortino_ratio = (
                avg_pnl / downside_deviation if downside_deviation > 0 else 0
            )

            # Calmar ratio
            calmar_ratio = avg_pnl / abs(max_drawdown) if max_drawdown != 0 else 0

            risk_metrics[strategy_name] = {
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "volatility": volatility,
                "max_drawdown": max_drawdown,
                "win_loss_ratio": strategy_data["win_rate"]
                / (100 - strategy_data["win_rate"])
                if strategy_data["win_rate"] < 100
                else float("inf"),
                "profit_factor": abs(total_pnl / sum(p for p in pnl_history if p < 0))
                if any(p < 0 for p in pnl_history)
                else float("inf"),
            }

        return risk_metrics

    def _calculate_max_drawdown(self, pnl_history):
        """Calculate maximum drawdown from P&L history"""
        if not pnl_history:
            return 0

        cumulative = np.cumsum(pnl_history)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown)

        return max_drawdown

    def _analyze_market_regime_performance(self):
        """Analyze strategy performance across different market regimes"""
        regime_analysis = {}

        # Define regime categories based on QFM features
        regime_categories = {
            "trending_bull": lambda f: f.get("velocity", 0) > 0.3
            and f.get("trend_confidence", 0) > 0.7,
            "trending_bear": lambda f: f.get("velocity", 0) < -0.3
            and f.get("trend_confidence", 0) > 0.7,
            "sideways": lambda f: abs(f.get("velocity", 0)) < 0.2
            and f.get("regime_score", 0.5) < 0.4,
            "volatile": lambda f: abs(f.get("jerk", 0)) > 0.5,
            "calm": lambda f: abs(f.get("jerk", 0)) < 0.2,
        }

        for regime_name, regime_condition in regime_categories.items():
            regime_performance = {}

            for strategy_name in self.strategies:
                regime_trades = []

                # Find trades in this regime
                for entry in self.ml_feedback.get("performance_history", []):
                    if entry["strategy"] == strategy_name and entry.get("qfm_features"):
                        if regime_condition(entry["qfm_features"]):
                            regime_trades.append(entry)

                if len(regime_trades) >= 5:
                    wins = sum(1 for t in regime_trades if t["win"])
                    total_pnl = sum(t["pnl"] for t in regime_trades)

                    regime_performance[strategy_name] = {
                        "trades": len(regime_trades),
                        "win_rate": (wins / len(regime_trades)) * 100,
                        "total_pnl": total_pnl,
                        "avg_pnl": total_pnl / len(regime_trades),
                    }

            if regime_performance:
                regime_analysis[regime_name] = regime_performance

        return regime_analysis

    def get_strategy_recommendations(self):
        """Get AI-powered strategy recommendations based on analytics"""
        analytics = self.analyze_qfm_strategy_performance()

        if "error" in analytics:
            return {"error": analytics["error"]}

        recommendations = {}

        # Strategy comparison recommendations
        comparison = analytics.get("strategy_comparison", {})
        rankings = comparison.get("rankings", {})

        if rankings:
            # Find best overall strategy
            best_strategy = max(
                rankings.items(), key=lambda x: x[1]["composite_score"]
            )[0]
            recommendations["best_overall_strategy"] = best_strategy

            # Find strategies that perform well in specific conditions
            regime_analysis = analytics.get("market_regime_analysis", {})
            for regime, regime_perf in regime_analysis.items():
                if regime_perf:
                    best_in_regime = max(
                        regime_perf.items(), key=lambda x: x[1]["win_rate"]
                    )[0]
                    recommendations[f"best_in_{regime}"] = best_in_regime

        # Risk-adjusted recommendations
        risk_metrics = analytics.get("risk_adjusted_metrics", {})
        if risk_metrics:
            # Find strategy with best Sharpe ratio
            best_sharpe = max(risk_metrics.items(), key=lambda x: x[1]["sharpe_ratio"])[
                0
            ]
            recommendations["best_risk_adjusted"] = best_sharpe

            # Find strategy with lowest volatility
            lowest_volatility = min(
                risk_metrics.items(), key=lambda x: x[1]["volatility"]
            )[0]
            recommendations["lowest_volatility"] = lowest_volatility

        # QFM correlation recommendations
        qfm_correlations = {}
        for key, correlation_data in analytics.items():
            if "qfm_correlation" in key:
                strategy_name = key.replace("_qfm_correlation", "")
                qfm_correlations[strategy_name] = correlation_data

        if qfm_correlations:
            for strategy_name, correlations in qfm_correlations.items():
                if correlations:
                    # Find most important QFM features for this strategy
                    important_features = sorted(
                        correlations.items(),
                        key=lambda x: x[1]["strength"],
                        reverse=True,
                    )[:3]
                    recommendations[f"{strategy_name}_key_qfm_features"] = [
                        f[0] for f in important_features
                    ]

        return recommendations

    def generate_performance_report(self, report_type="comprehensive"):
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": report_type,
            "summary": {},
            "strategies": {},
            "analytics": {},
            "recommendations": {},
        }

        # Basic summary
        total_strategies = len(self.strategies)
        active_strategies = sum(
            1
            for s in self.strategy_performance.values()
            if s.get("total_trades", 0) > 0
        )

        report["summary"] = {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "total_trades": sum(
                s.get("total_trades", 0) for s in self.strategy_performance.values()
            ),
            "total_pnl": sum(
                s.get("total_pnl", 0) for s in self.strategy_performance.values()
            ),
        }

        # Individual strategy performance
        for strategy_name, perf in self.strategy_performance.items():
            report["strategies"][strategy_name] = {
                "performance": perf,
                "parameters": self.strategies[strategy_name].parameters,
                "last_updated": perf.get("last_updated", 0),
            }

        # Analytics
        if report_type in ["comprehensive", "analytics"]:
            report["analytics"] = self.analyze_qfm_strategy_performance()

        # Recommendations
        if report_type in ["comprehensive", "recommendations"]:
            report["recommendations"] = self.get_strategy_recommendations()

        # ML insights
        if hasattr(self, "ml_feedback"):
            report["ml_insights"] = self.get_ml_feedback_insights()

        return report

    def __init__(self, initial_balance=10000):
        self.profile_prefix = getattr(self, "profile_prefix", "ULTIMATE")
        self.trade_type_label = getattr(self, "trade_type_label", "ULTIMATE_TRADE")
        self.strategy_label = getattr(self, "strategy_label", "50_INDICATORS_ULTIMATE")
        self.indicator_block_key = getattr(
            self, "indicator_block_key", "ultimate_ensemble"
        )
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        # NEW: Use ComprehensiveTradeHistory instead of EnhancedTradeHistory
        self.trade_history = ComprehensiveTradeHistory(log_callback=log_component_event)
        self.trading_enabled = TRADING_CONFIG.get("auto_trade_enabled", False)
        self.paper_trading = False
        self.real_trader = RealBinanceTrader(
            account_type="spot",
            testnet=_coerce_bool(os.getenv("USE_TESTNET", "1"), default=True),
            binance_client_cls=BinanceClient,
            api_exception_cls=BinanceAPIException,
            binance_log_manager=globals().get("binance_log_manager"),
            logger=bot_logger,
            coerce_bool=_coerce_bool,
        )
        self.real_trading_enabled = False
        self.last_real_order = None
        self.last_futures_order = None
        self.latest_market_data = {}
        self.daily_pnl = 0
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        self.ensemble_system = UltimateEnsembleSystem()
        self.risk_manager = AdaptiveRiskManager()
        self.safety_manager = SafetyManager(initial_balance=initial_balance)
        self.stop_loss_system = AdvancedStopLossSystem()
        self.parallel_engine = ParallelPredictionEngine()
        self.qfm_engine = QuantumFusionMomentumEngine()
        # NEW: CRT Module
        self.crt_generator = CRTSignalGenerator()
        self.symbol_min_notional_cache = {}
        self.real_equity_baseline = None
        self.auto_take_profit_state = {}
        self.futures_trader = None
        self.futures_trading_enabled = False

        self.bot_efficiency = {
            "total_trades": 0,
            "successful_trades": 0,
            "total_profit": 0,
            "learning_cycles": 0,
            "last_improvement": None,
            "ensemble_accuracy": 0.5,
            "risk_adjustment_history": [],
            "market_stress_history": [],
        }

        print(
            f"🚀 {self.profile_prefix} AI Trader with All Advanced Systems & CRT Module Initialized"
        )

    def get_training_logs(self):
        """Get training logs from ML system"""
        return []

    def _reset_virtual_positions_for_real_trading(self):
        """Drop any paper-only positions before activating live trading."""
        if not self.positions:
            return

        summary = {
            "symbol_count": len(self.positions),
            "symbols": list(self.positions.keys()),
            "total_virtual_value": sum(
                _safe_float(pos.get("quantity"), 0.0)
                * _safe_float(pos.get("avg_price"), 0.0)
                for pos in self.positions.values()
            ),
        }

        self.positions.clear()
        self.auto_take_profit_state.clear()

        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_TRADING_POSITION_RESET", summary)

        try:
            bot_logger.info(
                "Cleared %d paper positions before enabling real trading (virtual value %.2f)",
                summary["symbol_count"],
                summary["total_virtual_value"],
            )
        except Exception:
            pass

    # ==================== REAL TRADING CONTROL ====================
    def enable_real_trading(
        self, api_key=None, api_secret=None, testnet=True, force=False
    ):
        """Configure the Binance trader and disable paper trading if successful.

        Safety: enabling real trading is gated by the FINAL_HAMMER environment flag
        (set FINAL_HAMMER=1/true/yes) or by explicitly passing force=True. This
        prevents accidental activation of live trading in deployments where the
        environment variable is not set.
        """
        testnet = _coerce_bool(testnet, default=True)

        # Final hammer safety guard: require explicit env flag or force parameter
        final_hammer = os.getenv("FINAL_HAMMER", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not final_hammer and not force:
            try:
                bot_logger.warning(
                    "Blocked enable_real_trading: FINAL_HAMMER not set and force not provided."
                )
            except Exception:
                print(
                    "Blocked enable_real_trading: FINAL_HAMMER not set and force not provided."
                )
            return False

        was_paper_mode = self.paper_trading
        if not self.real_trader:
            self.real_trader = RealBinanceTrader(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                account_type="spot",
                binance_client_cls=BinanceClient,
                api_exception_cls=BinanceAPIException,
                binance_log_manager=globals().get("binance_log_manager"),
                logger=bot_logger,
                coerce_bool=_coerce_bool,
            )
        else:
            self.real_trader.set_testnet(testnet)
            self.real_trader.set_credentials(
                api_key=api_key, api_secret=api_secret, auto_connect=True
            )

        self.real_trading_enabled = self.real_trader.is_ready()
        self.paper_trading = not self.real_trading_enabled

        if self.real_trading_enabled and was_paper_mode:
            self._reset_virtual_positions_for_real_trading()

        status = self.get_real_trading_status()
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event(
                "REAL_TRADING_TOGGLED",
                {
                    "enabled": self.real_trading_enabled,
                    "testnet": status.get("testnet"),
                    "reason": status.get("last_error")
                    if not self.real_trading_enabled
                    else "connected",
                },
            )

        if self.real_trading_enabled:
            # Reset baseline so the next portfolio snapshot seeds it from live equity
            self.real_equity_baseline = None

        return self.real_trading_enabled

    def disable_real_trading(self, reason="manual"):
        self.real_trading_enabled = False
        self.paper_trading = True
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event(
                "REAL_TRADING_DISABLED", {"reason": reason}
            )
        self.real_equity_baseline = None
        return True

    def get_real_trading_status(self):
        base_status = {
            "enabled": self.real_trading_enabled,
            "paper_trading": self.paper_trading,
            "last_order": self.last_real_order,
        }
        if self.real_trader:
            base_status.update(self.real_trader.get_status())
        return base_status

    # ==================== FUTURES TRADING CONTROL ====================
    def enable_futures_trading(
        self, api_key=None, api_secret=None, testnet=True, force=False
    ):
        if not (BinanceFuturesClient or BinanceClient):
            print(
                "❌ Futures trading unavailable: python-binance client libraries not installed"
            )
            return False

        testnet = _coerce_bool(os.getenv("USE_TESTNET", "1"), default=True)

        # Safety guard for futures: require FINAL_HAMMER env or explicit force
        final_hammer = os.getenv("FINAL_HAMMER", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not final_hammer and not force:
            try:
                bot_logger.warning(
                    "Blocked enable_futures_trading: FINAL_HAMMER not set and force not provided."
                )
            except Exception:
                print(
                    "Blocked enable_futures_trading: FINAL_HAMMER not set and force not provided."
                )
            return False
        if not self.futures_trader:
            self.futures_trader = BinanceFuturesTrader(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                binance_um_futures_cls=BinanceFuturesClient,
                binance_rest_client_cls=BinanceClient,
                binance_log_manager=globals().get("binance_log_manager"),
                logger=bot_logger,
                coerce_bool=_coerce_bool,
                safe_float=_safe_float,
            )
        else:
            self.futures_trader.set_testnet(testnet)
            self.futures_trader.set_credentials(
                api_key=api_key, api_secret=api_secret, auto_connect=True
            )

        self.futures_trading_enabled = self.futures_trader.is_ready()
        return self.futures_trading_enabled

    def disable_futures_trading(self, reason="manual"):
        if self.futures_trader:
            self.futures_trading_enabled = False
            if hasattr(self.trade_history, "log_journal_event"):
                self.trade_history.log_journal_event(
                    "FUTURES_TRADING_DISABLED", {"reason": reason}
                )
        return True

    def get_futures_trading_status(self):
        status = {
            "enabled": self.futures_trading_enabled,
            "last_order": getattr(self, "last_futures_order", None),
        }
        if self.futures_trader:
            status.update(self.futures_trader.get_status())
        return status

    def _submit_futures_order(
        self, symbol, side, quantity, leverage=None, reduce_only=False
    ):
        if not self.futures_trading_enabled or not self.futures_trader:
            return None

        qty = _safe_float(quantity, 0.0)
        if qty <= 0:
            return None

        leverage_to_use = leverage or TRADING_CONFIG.get("futures_manual_leverage", 3)
        self.futures_trader.ensure_leverage(symbol, leverage_to_use)

        response = self.futures_trader.place_market_order(
            symbol, side, qty, reduce_only=reduce_only
        )
        journal_payload = {
            "symbol": symbol,
            "side": side,
            "quantity": qty,
            "leverage": leverage_to_use,
            "reduce_only": reduce_only,
            "status": "SUCCESS" if response else "FAILED",
            "testnet": self.futures_trader.testnet,
            "raw_response": response,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("FUTURES_ORDER", journal_payload)
        self.last_futures_order = journal_payload
        return response

    def _submit_real_order(
        self, symbol, side, quantity, price=None, order_type="MARKET"
    ):
        if not self.real_trading_enabled or not self.real_trader:
            return None

        try:
            qty = _safe_float(quantity, 0.0)
        except Exception:
            return None

        if qty <= 0:
            return None

        normalized_side = str(side).upper()
        resolved_price = self._resolve_market_price(symbol, price)
        min_notional = (
            self._get_symbol_min_notional(symbol) if normalized_side == "SELL" else None
        )

        if normalized_side == "SELL":
            qty = self._prepare_sell_quantity(symbol, qty)
            if qty <= 0:
                reason_details = {
                    "reason": "insufficient_quantity",
                    "message": "No sellable quantity available on exchange",
                    "resolved_price": resolved_price,
                    "attempted_quantity": _safe_float(quantity, 0.0),
                }
                return self._record_skipped_real_order(
                    symbol, normalized_side, quantity, resolved_price, reason_details
                )

            if min_notional and resolved_price:
                order_value = qty * resolved_price
                if order_value < min_notional:
                    reason_details = {
                        "reason": "min_notional",
                        "message": f"Order value {order_value:.2f} below Binance minNotional {min_notional:.2f}",
                        "min_notional": float(min_notional),
                        "resolved_price": resolved_price,
                        "attempted_quantity": qty,
                    }
                    return self._record_skipped_real_order(
                        symbol,
                        normalized_side,
                        quantity,
                        resolved_price,
                        reason_details,
                    )
        else:
            qty = round(qty, 6)

        if qty <= 0:
            return None

        response = self.real_trader.place_real_order(
            symbol, normalized_side, qty, price=price, order_type=order_type
        )
        status = "SUCCESS" if response else "FAILED"
        journal_payload = {
            "symbol": symbol,
            "side": normalized_side,
            "quantity": round(float(qty), 6) if isinstance(qty, (int, float)) else qty,
            "price": price,
            "resolved_price": resolved_price,
            "order_type": order_type,
            "status": status,
            "testnet": self.real_trader.testnet,
            "api_error": self.real_trader.last_error if not response else None,
        }
        # If we have a response, extract fills/commission metrics for the journal
        if response and isinstance(response, dict):
            try:
                executed_qty = self._extract_filled_quantity(response, qty)
                quote_received = self._calculate_quote_spent(
                    response, executed_qty, price or 0
                )
                commissions = self._extract_commissions(response)
                journal_payload.update(
                    {
                        "executed_qty": executed_qty,
                        "quote_received": quote_received,
                        "commissions": commissions,
                    }
                )
            except Exception:
                pass
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_ORDER", journal_payload)

        self.last_real_order = {
            "timestamp": datetime.now().isoformat(),
            **journal_payload,
            "raw_response": response,
        }
        return response

    def _record_skipped_real_order(
        self, symbol, side, requested_quantity, price_reference, reason_details
    ):
        payload = {
            "status": "SKIPPED",
            "symbol": symbol,
            "side": side,
            "requested_quantity": _safe_float(requested_quantity, 0.0),
            "price_reference": _safe_float(price_reference, 0.0)
            if price_reference is not None
            else None,
            "reason": (reason_details or {}).get("reason")
            if isinstance(reason_details, dict)
            else str(reason_details),
            "details": reason_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        message = None
        if isinstance(reason_details, dict):
            message = reason_details.get("message")
            if message:
                payload["message"] = message

        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_ORDER_SKIPPED", payload)

        try:
            bot_logger.warning(
                "Skipping real %s order for %s reason=%s",
                side,
                symbol,
                payload["reason"],
            )
        except Exception:
            pass

        self.last_real_order = payload
        return payload

    def _get_symbol_min_notional(self, symbol):
        if not symbol:
            return None

        symbol_key = str(symbol).upper()
        cached = self.symbol_min_notional_cache.get(symbol_key)
        if cached is not None:
            return cached

        overrides = TRADING_CONFIG.get("min_notional_overrides") or {}
        if symbol_key in overrides:
            try:
                value = float(overrides[symbol_key])
                self.symbol_min_notional_cache[symbol_key] = value
                return value
            except (TypeError, ValueError):
                pass

        if self.real_trader and self.real_trader.is_ready():
            min_notional = self.real_trader.get_min_notional(symbol_key)
            if min_notional:
                try:
                    value = float(min_notional)
                    self.symbol_min_notional_cache[symbol_key] = value
                    return value
                except (TypeError, ValueError):
                    pass

        default_min = TRADING_CONFIG.get("default_min_notional")
        if default_min:
            try:
                value = float(default_min)
                self.symbol_min_notional_cache[symbol_key] = value
                return value
            except (TypeError, ValueError):
                pass

        return None

    def _get_real_account_snapshot(self, current_prices):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return None

        try:
            account = (
                self.real_trader.account_status
                or self.real_trader.refresh_account_status()
            )
            if not account:
                return None

            balances = account.get("balances", []) or []
            tracked_assets = {
                sym[:-4]: sym
                for sym in get_active_trading_universe()
                if sym.endswith("USDT")
            }
            stable_suffixes = ("USDT", "BUSD", "USDC", "FDUSD", "DAI", "TUSD")

            cash_total = 0.0
            cash_breakdown = []
            holdings = []
            asset_value_total = 0.0

            for bal in balances:
                asset = str(bal.get("asset") or "").upper()
                free_qty = _safe_float(bal.get("free"), 0.0)
                locked_qty = _safe_float(bal.get("locked"), 0.0)
                total_qty = free_qty + locked_qty
                if total_qty <= 0:
                    continue

                if asset.endswith(stable_suffixes):
                    cash_total += total_qty
                    cash_breakdown.append(
                        {
                            "asset": asset,
                            "free": free_qty,
                            "locked": locked_qty,
                            "total": total_qty,
                        }
                    )
                    continue

                # Skip leveraged tokens and synthetic prefixes that don't map to spot symbols
                normalized_asset = asset
                if normalized_asset.startswith("LD"):
                    normalized_asset = normalized_asset[2:]

                symbol = (
                    tracked_assets.get(normalized_asset) or f"{normalized_asset}USDT"
                )
                price = current_prices.get(symbol)
                if not price:
                    continue

                current_value = total_qty * price
                asset_value_total += current_value
                holdings.append(
                    {
                        "asset": asset,
                        "symbol": symbol,
                        "quantity": total_qty,
                        "free": free_qty,
                        "locked": locked_qty,
                        "price": price,
                        "current_value": current_value,
                    }
                )

            total_equity = cash_total + asset_value_total
            return {
                "cash": cash_total,
                "cash_breakdown": cash_breakdown,
                "asset_value": asset_value_total,
                "holdings": holdings,
                "total_equity": total_equity,
                "updated_at": account.get("update_time"),
                "can_trade": account.get("can_trade"),
            }
        except Exception as exc:
            bot_logger.warning("Failed to build real account snapshot error=%s", exc)
            return None

    def _resolve_market_price(self, symbol, reference_price=None):
        try:
            if reference_price is not None:
                candidate = float(reference_price)
                if candidate > 0:
                    return candidate
        except Exception:
            pass

        latest = (
            self.latest_market_data.get(symbol)
            if isinstance(self.latest_market_data, dict)
            else None
        )
        if isinstance(latest, dict):
            for key in ("price", "last_price", "close", "current_price"):
                value = latest.get(key)
                if value is None:
                    continue
                try:
                    price_val = float(value)
                    if price_val > 0:
                        return price_val
                except Exception:
                    continue

        if self.real_trader and self.real_trader.is_ready():
            resolved = self.real_trader._resolve_price(symbol, reference_price)
            try:
                if resolved is not None and float(resolved) > 0:
                    return float(resolved)
            except Exception:
                pass

        return None

    def _determine_quote_asset(self, symbol):
        if not symbol:
            return "USDT"
        symbol_key = str(symbol).upper()
        known_quotes = sorted(
            ["USDT", "BUSD", "USDC", "FDUSD", "TUSD", "DAI"], key=len, reverse=True
        )
        for quote in known_quotes:
            if symbol_key.endswith(quote):
                return quote
        return "USDT"

    def _get_real_free_balance(self, asset, *, refresh=False):
        if not asset or not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return None

        account = None
        if refresh or not getattr(self.real_trader, "account_status", None):
            account = self.real_trader.refresh_account_status()
        else:
            account = self.real_trader.account_status

        if not account:
            return None

        target = str(asset).upper()
        total_free = 0.0
        for bal in account.get("balances", []) or []:
            asset_code = str(bal.get("asset") or "").upper()
            normalized = asset_code[2:] if asset_code.startswith("LD") else asset_code
            if normalized == target:
                total_free += _safe_float(bal.get("free"), 0.0)
        return total_free

    def _determine_base_asset(self, symbol):
        symbol_key = str(symbol or "").upper()
        if not symbol_key:
            return ""
        quote_asset = self._determine_quote_asset(symbol_key)
        if quote_asset and symbol_key.endswith(quote_asset):
            return symbol_key[: -len(quote_asset)]
        return symbol_key

    def _calculate_net_filled_quantity(
        self, symbol, filled_quantity, order_response=None
    ):
        quantity = _safe_float(filled_quantity, 0.0)
        if quantity <= 0 or not order_response or not isinstance(order_response, dict):
            return max(quantity, 0.0)

        fills = order_response.get("fills") or []
        if not fills:
            return max(quantity, 0.0)

        base_asset = self._determine_base_asset(symbol)
        if not base_asset:
            return max(quantity, 0.0)

        base_commission = 0.0
        for fill in fills:
            commission_asset = str(fill.get("commissionAsset") or "").upper()
            if commission_asset == base_asset:
                base_commission += _safe_float(fill.get("commission"), 0.0)

        net_quantity = quantity - base_commission
        return max(net_quantity, 0.0)

    def _calculate_quote_spent(self, order_response, filled_quantity, fallback_price):
        fallback_value = _safe_float(filled_quantity, 0.0) * _safe_float(
            fallback_price, 0.0
        )
        if not order_response or not isinstance(order_response, dict):
            return fallback_value

        cumulative = order_response.get("cummulativeQuoteQty")
        if cumulative is not None:
            value = _safe_float(cumulative, fallback_value)
            if value > 0:
                return value

        fills = order_response.get("fills") or []
        if fills:
            total = 0.0
            for fill in fills:
                price = _safe_float(fill.get("price"), fallback_price)
                qty = _safe_float(fill.get("qty"), 0.0)
                total += price * qty
            if total > 0:
                return total

        return fallback_value

    def _extract_commissions(self, order_response):
        """Return a dict of commission amounts keyed by asset from an order response."""
        result = {}
        if not order_response or not isinstance(order_response, dict):
            return result
        fills = order_response.get("fills") or []
        for fill in fills:
            try:
                comm = _safe_float(fill.get("commission"), 0.0)
                asset = str(fill.get("commissionAsset") or "").upper()
                if not asset:
                    continue
                result[asset] = result.get(asset, 0.0) + comm
            except Exception:
                continue
        return result

    def _prepare_sell_quantity(self, symbol, desired_quantity):
        quantity = _safe_float(desired_quantity, 0.0)
        if quantity <= 0:
            return 0.0

        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return quantity

        base_asset = self._determine_base_asset(symbol)
        if not base_asset:
            return quantity

        available = self._get_real_free_balance(base_asset, refresh=True)
        if available is not None and available > 0:
            quantity = min(quantity, _safe_float(available, quantity))

        return max(quantity, 0.0)

    def _has_sufficient_real_balance(self, symbol, required_quote_value):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return True, {"reason": "real_trading_disabled"}

        quote_asset = self._determine_quote_asset(symbol)
        available = self._get_real_free_balance(quote_asset, refresh=True)
        if available is None:
            return False, {
                "reason": "balance_unavailable",
                "message": f"Unable to determine available {quote_asset} balance",
                "quote_asset": quote_asset,
            }

        buffer = TRADING_CONFIG.get("balance_cash_buffer") or 1.0
        try:
            required_value = float(required_quote_value) * float(buffer)
        except Exception:
            required_value = float(required_quote_value)

        if available < required_value:
            return False, {
                "reason": "insufficient_balance",
                "message": f"Insufficient {quote_asset} balance ({available:.2f} < {required_value:.2f})",
                "quote_asset": quote_asset,
                "available": available,
                "required": required_value,
                "buffer": buffer,
            }

        return True, {
            "reason": "sufficient_balance",
            "quote_asset": quote_asset,
            "available": available,
            "required": required_value,
            "buffer": buffer,
        }

    def _extract_filled_quantity(self, response, fallback_quantity):
        try:
            if isinstance(response, dict):
                executed = response.get("executedQty")
                if executed is not None:
                    executed_qty = float(executed)
                    if executed_qty > 0:
                        return executed_qty
                fills = response.get("fills")
                if isinstance(fills, list) and fills:
                    total = 0.0
                    for fill in fills:
                        try:
                            total += float(fill.get("qty", 0))
                        except Exception:
                            continue
                    if total > 0:
                        return total
        except Exception:
            pass
        try:
            return float(fallback_quantity)
        except Exception:
            return fallback_quantity

    def _handle_auto_take_profit(
        self, symbol, entry_price, quantity, order_response=None
    ):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return

        config = TRADING_CONFIG
        percent = config.get("auto_take_profit_percent", 0.0)
        if not percent or percent <= 0:
            return

        # Cancel any existing take-profit for this symbol to prevent duplicates
        if symbol in self.auto_take_profit_state:
            self._cancel_auto_take_profit(symbol)

        adjusted_quantity = quantity
        if (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            adjusted_quantity = self._prepare_sell_quantity(symbol, quantity)

        normalized_qty, _ = self.real_trader._normalize_order_quantity(
            symbol, adjusted_quantity
        )
        if not normalized_qty or normalized_qty <= 0:
            return

        desired_price = entry_price * (1 + percent)
        order_book = self.real_trader.get_order_book(symbol, limit=5)
        spread_margin = config.get("auto_take_profit_spread_margin", 0.0) or 0.0
        if order_book and isinstance(order_book, dict):
            asks = order_book.get("asks") or []
            if asks:
                try:
                    best_ask = float(asks[0][0])
                    desired_price = max(desired_price, best_ask * (1 + spread_margin))
                except Exception:
                    pass

        tif = config.get("auto_take_profit_time_in_force", "GTC")
        response = self.real_trader.place_limit_order(
            symbol, "SELL", normalized_qty, price=desired_price, time_in_force=tif
        )

        if not response:
            log_component_event(
                "AUTO_TAKE_PROFIT",
                "Failed to place take-profit order",
                level=logging.WARNING,
                details={
                    "symbol": symbol,
                    "target_price": desired_price,
                    "quantity": normalized_qty,
                },
            )
            return

        self.auto_take_profit_state[symbol] = {
            "order_id": response.get("orderId") if isinstance(response, dict) else None,
            "client_order_id": response.get("clientOrderId")
            if isinstance(response, dict)
            else None,
            "target_price": float(response.get("price", desired_price))
            if isinstance(response, dict)
            else desired_price,
            "entry_price": entry_price,
            "quantity": normalized_qty,
            "created_at": datetime.utcnow().isoformat(),
            "last_checked": time.time(),
            "percent": percent,
        }

        log_component_event(
            "AUTO_TAKE_PROFIT",
            "Take-profit order placed",
            level=logging.INFO,
            details={
                "symbol": symbol,
                "entry_price": entry_price,
                "target_price": self.auto_take_profit_state[symbol]["target_price"],
                "quantity": normalized_qty,
                "order_id": self.auto_take_profit_state[symbol]["order_id"],
            },
        )

    def _cancel_auto_take_profit(self, symbol):
        state = self.auto_take_profit_state.pop(symbol, None)
        if not state:
            return
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return
        self.real_trader.cancel_order(
            symbol,
            order_id=state.get("order_id"),
            client_order_id=state.get("client_order_id"),
        )

    def update_auto_take_profit_orders(self, market_data=None):
        if not self.auto_take_profit_state:
            return
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return

        config = TRADING_CONFIG
        interval = config.get("auto_take_profit_adjust_interval", 30)
        reprice_threshold = config.get("auto_take_profit_reprice_threshold", 0.003)
        spread_margin = config.get("auto_take_profit_spread_margin", 0.0) or 0.0

        for symbol in list(self.auto_take_profit_state.keys()):
            state = self.auto_take_profit_state.get(symbol)
            if not state:
                continue

            last_checked = state.get("last_checked")
            if last_checked and (time.time() - last_checked) < interval:
                continue

            state["last_checked"] = time.time()

            order_info = self.real_trader.get_order(
                symbol,
                order_id=state.get("order_id"),
                client_order_id=state.get("client_order_id"),
            )

            if not order_info:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            status = str(order_info.get("status", "")).upper()
            if status in {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            try:
                orig_qty = float(order_info.get("origQty", state.get("quantity", 0)))
                executed_qty = float(order_info.get("executedQty", 0))
            except Exception:
                orig_qty = state.get("quantity", 0)
                executed_qty = 0

            remaining_qty = max(0.0, orig_qty - executed_qty)
            if remaining_qty <= 0:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            current_order_price = None
            try:
                current_order_price = float(order_info.get("price"))
            except Exception:
                current_order_price = state.get("target_price")

            market_price = None
            if (
                market_data
                and symbol in market_data
                and isinstance(market_data[symbol], dict)
            ):
                market_price = market_data[symbol].get("price")

            entry_price = state.get("entry_price") or market_price
            if not entry_price:
                continue

            desired_price = entry_price * (
                1 + state.get("percent", config.get("auto_take_profit_percent", 0.05))
            )
            order_book = self.real_trader.get_order_book(symbol, limit=5)
            if order_book and isinstance(order_book, dict):
                asks = order_book.get("asks") or []
                if asks:
                    try:
                        best_ask = float(asks[0][0])
                        desired_price = max(
                            desired_price, best_ask * (1 + spread_margin)
                        )
                    except Exception:
                        pass

            desired_price = self.real_trader.normalize_price(symbol, desired_price)
            if not current_order_price:
                current_order_price = desired_price

            price_diff = abs(desired_price - current_order_price)
            price_diff_pct = (
                price_diff / current_order_price if current_order_price else 0
            )

            if price_diff_pct < reprice_threshold:
                continue

            cancel_result = self.real_trader.cancel_order(
                symbol,
                order_id=state.get("order_id"),
                client_order_id=state.get("client_order_id"),
            )

            if cancel_result is None:
                continue

            new_order = self.real_trader.place_limit_order(
                symbol,
                "SELL",
                remaining_qty,
                price=desired_price,
                time_in_force=config.get("auto_take_profit_time_in_force", "GTC"),
            )

            if new_order:
                state["order_id"] = (
                    new_order.get("orderId") if isinstance(new_order, dict) else None
                )
                state["client_order_id"] = (
                    new_order.get("clientOrderId")
                    if isinstance(new_order, dict)
                    else None
                )
                state["target_price"] = (
                    float(new_order.get("price", desired_price))
                    if isinstance(new_order, dict)
                    else desired_price
                )
                state["quantity"] = remaining_qty
                state["entry_price"] = entry_price
                state["last_checked"] = time.time()
                log_component_event(
                    "AUTO_TAKE_PROFIT",
                    "Take-profit order repriced",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "new_price": state["target_price"],
                        "remaining_qty": remaining_qty,
                        "previous_price": current_order_price,
                    },
                )
            else:
                self.auto_take_profit_state.pop(symbol, None)

    def calculate_ultimate_position_size(
        self,
        symbol,
        current_price,
        signal_confidence,
        volatility=0.02,
        ensemble_signal=None,
        portfolio_health=1.0,
    ):
        """Ultimate position sizing with all advanced factors"""
        base_risk = (
            TRADING_CONFIG["risk_per_trade"] * self.risk_manager.get_risk_multiplier()
        )

        # Confidence multiplier
        confidence_multiplier = min(signal_confidence * 1.5, 1.2)

        # Ensemble signal boost
        ensemble_boost = 1.0
        if ensemble_signal:
            if ensemble_signal.get("signal") in ["STRONG_BUY", "STRONG_SELL"]:
                ensemble_boost = 1.3
            elif ensemble_signal.get("signal") in ["BUY", "SELL"]:
                ensemble_boost = 1.15

        # Volatility adjustment
        vol_adjustment = 1.0
        if volatility > 0.06:
            vol_adjustment = 0.6
        elif volatility > 0.03:
            vol_adjustment = 0.8
        elif volatility < 0.01:
            vol_adjustment = 1.2

        # Market regime adjustment
        regime_adjustment = 1.0
        if self.ensemble_system.market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
            regime_adjustment = 1.2
        elif self.ensemble_system.market_regime in [
            "HIGH_VOL_SIDEWAYS",
            "OVERBOUGHT",
            "OVERSOLD",
        ]:
            regime_adjustment = 0.7

        # Portfolio health adjustment
        health_factor = max(0.5, min(1.5, portfolio_health))

        # Market stress adjustment
        stress_factor = 1.0 - (
            self.risk_manager.market_stress_indicator * 0.5
        )  # Reduce size during stress

        # Calculate final position size
        position_value = (
            self.balance
            * base_risk
            * confidence_multiplier
            * ensemble_boost
            * vol_adjustment
            * regime_adjustment
            * health_factor
            * stress_factor
        )

        max_position_value = self.balance * TRADING_CONFIG["max_position_size"]
        position_value = min(position_value, max_position_value)

        min_notional = self._get_symbol_min_notional(symbol)
        buffer = TRADING_CONFIG.get("min_notional_buffer", 1.0)

        if min_notional and current_price:
            try:
                min_value = float(min_notional) * float(buffer if buffer else 1.0)
                if position_value < min_value:
                    log_component_event(
                        "POSITION_SIZING",
                        "Position value raised to min notional",
                        level=logging.INFO,
                        details={
                            "symbol": symbol,
                            "original_value": round(float(position_value), 4)
                            if isinstance(position_value, (int, float))
                            else position_value,
                            "min_notional": min_notional,
                            "buffer": buffer,
                            "target_value": min_value,
                        },
                    )
                    position_value = min(min_value, max_position_value)
            except Exception as exc:
                bot_logger.warning(
                    "Failed to enforce min notional for %s error=%s", symbol, exc
                )

        quantity = position_value / current_price if current_price else 0

        # Log ultimate position sizing
        print(f"🎯 {self.profile_prefix} Position Sizing for {symbol}:")
        print(
            f"   Base: ${base_risk*self.balance:.2f}, Confidence: {confidence_multiplier:.2f}"
        )
        print(f"   Ensemble: {ensemble_boost:.2f}, Vol: {vol_adjustment:.2f}")
        print(
            f"   Regime: {regime_adjustment:.2f}, Health: {health_factor:.2f}, Stress: {stress_factor:.2f}"
        )
        print(f"   Final: ${position_value:.2f} ({quantity:.4f} units)")

        return quantity, position_value

    def should_execute_ultimate_trade(
        self,
        symbol,
        ml_predictions,
        technical_signals,
        current_positions,
        market_regime,
        ensemble_signal,
        market_stress,
        market_data=None,
        historical_prices=None,
    ):
        """Ultimate trading decision with all advanced factors"""
        log_component_debug(
            "TRADE_DECISION",
            "Evaluating trade decision",
            {
                "symbol": symbol,
                "open_positions": len(current_positions)
                if isinstance(current_positions, dict)
                else len(current_positions or []),
                "ml_signal_count": len(ml_predictions)
                if isinstance(ml_predictions, dict)
                else 0,
                "technical_signal_count": len(technical_signals)
                if technical_signals
                else 0,
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 4)
                if isinstance(market_stress, (int, float))
                else market_stress,
            },
        )
        if len(current_positions) >= TRADING_CONFIG["max_positions"]:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: max positions reached",
                level=logging.INFO,
                details={"symbol": symbol, "open_positions": len(current_positions)},
            )
            return False, "Max positions reached"

        if not ml_predictions and not technical_signals:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: no predictions available",
                level=logging.INFO,
                details={"symbol": symbol},
            )
            return False, "No predictions available"

        # Generate CRT signals for decision making
        crt_signal = None
        if market_data and historical_prices and hasattr(self, "crt_generator"):
            try:
                crt_signal = self.crt_generator.generate_crt_signals(
                    symbol, market_data, historical_prices
                )
                log_component_debug(
                    "TRADE_DECISION",
                    "CRT signals generated",
                    {
                        "symbol": symbol,
                        "crt_signal": crt_signal.get("signal") if crt_signal else None,
                        "crt_confidence": crt_signal.get("confidence")
                        if crt_signal
                        else None,
                    },
                )
            except Exception as e:
                log_component_event(
                    "TRADE_DECISION",
                    f"CRT signal generation error: {e}",
                    level=logging.WARNING,
                    details={"symbol": symbol},
                )

        # Combine all signals
        all_signals = []

        # Add ML predictions
        if ml_predictions:
            for model_name, prediction in ml_predictions.items():
                if not isinstance(prediction, dict):
                    continue

                signal_value = prediction.get("signal")
                if not signal_value:
                    continue

                confidence_value = prediction.get("confidence")
                if confidence_value is None:
                    confidence_value = prediction.get("probability")
                if confidence_value is None:
                    confidence_value = 0.5

                signal_type = "ML"
                if isinstance(model_name, str):
                    lower_name = model_name.lower()
                    if "ensemble" in lower_name:
                        signal_type = "ENSEMBLE"
                    elif "futures" in lower_name:
                        signal_type = "ENSEMBLE"

                all_signals.append(
                    {
                        "signal": signal_value,
                        "confidence": float(confidence_value),
                        "type": signal_type,
                        "model": model_name,
                        "indicators": prediction.get("indicators_total", 0),
                        "data_source": prediction.get("data_source", "UNKNOWN"),
                    }
                )

        # Add technical signals
        for tech_signal in technical_signals:
            all_signals.append(
                {
                    "signal": tech_signal["signal"],
                    "confidence": tech_signal["confidence"],
                    "type": "TECHNICAL",
                    "strategy": tech_signal["strategy"],
                }
            )

        # Add ensemble signal
        if ensemble_signal:
            all_signals.append(
                {
                    "signal": ensemble_signal["signal"],
                    "confidence": ensemble_signal["confidence"],
                    "type": "ENSEMBLE",
                    "buy_ratio": ensemble_signal.get("buy_ratio", 0.5),
                    "consensus": ensemble_signal.get("weighted_consensus", 0),
                }
            )

        # Add CRT signal
        if crt_signal:
            all_signals.append(
                {
                    "signal": crt_signal.get("signal", "HOLD"),
                    "confidence": crt_signal.get("confidence", 0.5),
                    "type": "CRT",
                    "composite_score": crt_signal.get("composite_score", 0),
                    "components": crt_signal.get("components", {}),
                }
            )

        if not all_signals:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: aggregated signal list empty",
                level=logging.INFO,
                details={"symbol": symbol},
            )
            return False, "No signals available"
        else:
            log_component_debug(
                "TRADE_DECISION",
                "Aggregated signals prepared",
                {"symbol": symbol, "total_signals": len(all_signals)},
            )

        # Apply signal prioritization and conflict resolution
        prioritized_signals = self._prioritize_signals(
            all_signals, market_regime, market_stress
        )

        # Calculate weighted signals with ultimate factors
        buy_strength = 0
        sell_strength = 0
        total_weight = 0

        for signal in prioritized_signals:
            # Ultimate weight assignment
            if signal["type"] == "ENSEMBLE":
                weight = 2.5
            elif signal["type"] == "CRT":
                weight = 2.0  # High weight for comprehensive CRT signals
            elif signal["type"] == "QFM":
                weight = 1.8  # High weight for Quantum Fusion Momentum signals
            elif signal["type"] == "ML" and signal.get("data_source") == "BINANCE_REAL":
                if signal.get("indicators", 0) >= 20:
                    weight = 1.8
                else:
                    weight = 1.3
            elif signal["type"] == "ML":
                weight = 1.2
            else:
                weight = 1.0

            # Strong signal bonus
            if signal["signal"] in ["STRONG_BUY", "STRONG_SELL"]:
                weight *= 1.3

            # Market stress penalty
            if market_stress > 0.6:
                weight *= 0.7

            if signal["signal"] in ["BUY", "STRONG_BUY"]:
                buy_strength += signal["confidence"] * weight
            elif signal["signal"] in ["SELL", "STRONG_SELL"]:
                sell_strength += signal["confidence"] * weight

            total_weight += weight

        buy_power = buy_strength / total_weight if total_weight > 0 else 0
        sell_power = sell_strength / total_weight if total_weight > 0 else 0

        # Dynamic threshold with all factors
        dynamic_threshold = TRADING_CONFIG["confidence_threshold"]

        # Market stress adjustment
        if market_stress > 0.7:
            dynamic_threshold += 0.08
        elif market_stress > 0.4:
            dynamic_threshold += 0.04

        # Ensemble-based adjustments
        if ensemble_signal:
            ensemble_confidence = ensemble_signal.get("confidence", 0.5)
            if ensemble_confidence > 0.7:
                dynamic_threshold -= 0.03
            elif ensemble_confidence < 0.4:
                dynamic_threshold += 0.05

        # Market regime adjustments
        if market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
            dynamic_threshold -= 0.015
        elif market_regime in ["HIGH_VOL_SIDEWAYS"]:
            dynamic_threshold += 0.025

        # Clamp dynamic threshold to configured bounds
        threshold_floor = TRADING_CONFIG.get("dynamic_threshold_floor", 0.35)
        threshold_ceiling = TRADING_CONFIG.get("dynamic_threshold_ceiling", 0.55)
        dynamic_threshold = max(
            threshold_floor, min(dynamic_threshold, threshold_ceiling)
        )

        strength_diff = abs(buy_power - sell_power)
        min_diff_required = TRADING_CONFIG.get("min_confidence_diff", 0.05)

        log_component_debug(
            "TRADE_DECISION",
            "Threshold evaluation",
            {
                "symbol": symbol,
                "buy_power": round(float(buy_power), 3),
                "sell_power": round(float(sell_power), 3),
                "strength_diff": round(float(strength_diff), 3),
                "dynamic_threshold": round(float(dynamic_threshold), 3),
                "min_diff_required": round(float(min_diff_required), 3),
                "market_stress": round(float(market_stress), 3),
                "regime": market_regime,
            },
        )

        # Enhanced ensemble consensus requirement
        if ensemble_signal and TRADING_CONFIG["use_ensemble"]:
            ensemble_agreement = (
                ensemble_signal.get("buy_ratio", 0.5)
                if buy_power > sell_power
                else (1 - ensemble_signal.get("buy_ratio", 0.5))
            )
            min_agreement = TRADING_CONFIG.get("ensemble_min_agreement", 0.6)

            if ensemble_agreement < min_agreement:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision blocked: ensemble agreement too low",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "ensemble_agreement": round(float(ensemble_agreement), 3),
                        "min_required": round(float(min_agreement), 3),
                    },
                )
                return (
                    False,
                    f"Ensemble agreement too low: {ensemble_agreement:.2f} < {min_agreement:.2f}",
                )

        # Market stress override
        if market_stress > 0.8 and strength_diff < 0.2:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: market stress override triggered",
                level=logging.WARNING,
                details={
                    "symbol": symbol,
                    "market_stress": round(float(market_stress), 3),
                    "strength_diff": round(float(strength_diff), 3),
                },
            )
            return False, f"Market stress too high: {market_stress:.2f}"

        # Final ultimate decision
        if (
            buy_power > sell_power
            and buy_power >= dynamic_threshold
            and strength_diff >= min_diff_required
        ):
            strong_buy_count = sum(
                1 for s in all_signals if s["signal"] == "STRONG_BUY"
            )
            if strong_buy_count >= 2:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: STRONG_BUY approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "STRONG_BUY"
            else:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: BUY approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "BUY"

        elif (
            sell_power > buy_power
            and symbol in current_positions
            and sell_power >= dynamic_threshold
            and strength_diff >= min_diff_required
        ):
            strong_sell_count = sum(
                1 for s in all_signals if s["signal"] == "STRONG_SELL"
            )
            if strong_sell_count >= 2:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: STRONG_SELL approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "STRONG_SELL"
            else:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: SELL approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "SELL"

        log_component_debug(
            "TRADE_DECISION",
            "Decision: No trade (insufficient strength)",
            {
                "symbol": symbol,
                "buy_power": round(float(buy_power), 3),
                "sell_power": round(float(sell_power), 3),
                "strength_diff": round(float(strength_diff), 3),
                "dynamic_threshold": round(float(dynamic_threshold), 3),
                "market_stress": round(float(market_stress), 3),
            },
        )
        return (
            False,
            f"Signal weak (buy: {buy_power:.2f}, sell: {sell_power:.2f}, diff: {strength_diff:.2f}, stress: {market_stress:.2f})",
        )

    def _prioritize_signals(self, all_signals, market_regime, market_stress):
        """Prioritize signals to prevent conflicts and ensure fool-proof trading"""
        if not all_signals:
            return []

        # Signal priority hierarchy (higher = more important)
        priority_map = {
            "ENSEMBLE": 10,  # Highest priority - meta-analysis
            "CRT": 9,  # Comprehensive multi-timeframe analysis
            "ML": 7,  # Machine learning predictions
            "TECHNICAL": 5,  # Individual technical indicators
        }

        # Quality scoring for each signal
        scored_signals = []
        for signal in all_signals:
            base_priority = priority_map.get(signal["type"], 1)

            # Quality modifiers
            quality_score = 0

            # Confidence modifier
            confidence = signal.get("confidence", 0.5)
            if confidence > 0.8:
                quality_score += 2
            elif confidence > 0.6:
                quality_score += 1

            # Signal strength modifier
            signal_type = signal.get("signal", "")
            if signal_type in ["STRONG_BUY", "STRONG_SELL"]:
                quality_score += 1

            # Type-specific quality checks
            if signal["type"] == "CRT":
                # CRT quality based on composite score and component alignment
                composite_score = abs(signal.get("composite_score", 0))
                components = signal.get("components", {})
                aligned_components = sum(
                    1 for comp_score in components.values() if abs(comp_score) > 0.1
                )
                if composite_score > 0.2 and aligned_components >= 3:
                    quality_score += 2
            elif signal["type"] == "ML":
                # ML quality based on indicator count and data source
                indicators = signal.get("indicators", 0)
                data_source = signal.get("data_source", "")
                if indicators >= 20:
                    quality_score += 1
                if data_source == "BINANCE_REAL":
                    quality_score += 1
            elif signal["type"] == "ENSEMBLE":
                # Ensemble quality based on agreement and consensus
                buy_ratio = signal.get("buy_ratio", 0.5)
                consensus = abs(signal.get("consensus", 0))
                if consensus > 0.3 and (buy_ratio > 0.7 or buy_ratio < 0.3):
                    quality_score += 2

            # Market condition modifiers
            if market_stress > 0.6:
                # In high stress, prefer conservative signals
                if signal["type"] in ["ENSEMBLE", "CRT"]:
                    quality_score += 1
                elif signal["type"] == "TECHNICAL" and confidence < 0.7:
                    quality_score -= 1

            # Regime-specific adjustments
            if market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
                if signal["type"] == "CRT":  # CRT handles trends well
                    quality_score += 1
            elif market_regime == "HIGH_VOL_SIDEWAYS":
                if signal["type"] == "ENSEMBLE":  # Ensemble handles uncertainty well
                    quality_score += 1

            total_priority = base_priority + quality_score
            scored_signals.append(
                {
                    **signal,
                    "priority_score": total_priority,
                    "quality_score": quality_score,
                }
            )

        # Sort by priority (highest first)
        scored_signals.sort(key=lambda x: x["priority_score"], reverse=True)

        # Conflict resolution: remove conflicting signals from lower priority sources
        filtered_signals = []
        buy_signals = []
        sell_signals = []

        for signal in scored_signals:
            signal_type = signal.get("signal", "")
            signal_priority = signal["priority_score"]

            if signal_type in ["BUY", "STRONG_BUY"]:
                # Check for conflicts with existing sell signals
                conflicting_sells = [
                    s
                    for s in sell_signals
                    if s["priority_score"] >= signal_priority - 2
                ]
                if not conflicting_sells:
                    buy_signals.append(signal)
                    filtered_signals.append(signal)
            elif signal_type in ["SELL", "STRONG_SELL"]:
                # Check for conflicts with existing buy signals
                conflicting_buys = [
                    s for s in buy_signals if s["priority_score"] >= signal_priority - 2
                ]
                if not conflicting_buys:
                    sell_signals.append(signal)
                    filtered_signals.append(signal)
            else:
                # HOLD signals don't conflict
                filtered_signals.append(signal)

        log_component_debug(
            "SIGNAL_PRIORITIZATION",
            "Signals prioritized and filtered",
            {
                "original_count": len(all_signals),
                "filtered_count": len(filtered_signals),
                "buy_signals": len(buy_signals),
                "sell_signals": len(sell_signals),
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 3),
            },
        )

        return filtered_signals

    def execute_ultimate_trade(
        self,
        symbol,
        ml_predictions,
        market_data,
        historical_prices,
        ensemble_signal=None,
    ):
        """Execute ultimate trade with all advanced systems"""
        log_component_event(
            "TRADE_EXECUTION",
            "Trade execution requested",
            level=logging.DEBUG,
            details={
                "symbol": symbol,
                "trading_enabled": bool(self.trading_enabled),
                "real_trading_enabled": bool(
                    getattr(self, "real_trading_enabled", False)
                ),
                "open_positions": len(self.positions),
                "has_ml_predictions": bool(ml_predictions),
            },
        )
        if not self.trading_enabled:
            log_component_event(
                "TRADE_EXECUTION",
                "Trade execution denied: trading disabled",
                level=logging.WARNING,
                details={"symbol": symbol},
            )
            return False, "Trading disabled"

        self.latest_market_data[symbol] = market_data

        # Generate technical signals
        technical_signals = self.generate_technical_signals(
            symbol, market_data, historical_prices
        )
        log_component_debug(
            "TRADE_EXECUTION",
            "Signals assembled for execution",
            {
                "symbol": symbol,
                "technical_signal_count": len(technical_signals),
                "ml_signal_count": len(ml_predictions)
                if isinstance(ml_predictions, dict)
                else 0,
            },
        )

        # Analyze market regime
        market_regime = self.ensemble_system.analyze_market_regime_advanced(
            market_data, historical_prices
        )

        # Calculate market stress
        market_stress = self.risk_manager.calculate_market_stress(
            {symbol: market_data}, historical_prices
        )
        log_component_debug(
            "TRADE_EXECUTION",
            "Market context evaluated",
            {
                "symbol": symbol,
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 4)
                if isinstance(market_stress, (int, float))
                else market_stress,
            },
        )

        # NEW: Generate CRT signals
        crt_signal = self.crt_generator.generate_crt_signals(
            symbol, market_data, historical_prices
        )

        # Make ultimate trading decision
        should_trade, trade_signal = self.should_execute_ultimate_trade(
            symbol,
            ml_predictions,
            technical_signals,
            self.positions,
            market_regime,
            ensemble_signal,
            market_stress,
            market_data,
            historical_prices,
        )

        if not should_trade:
            log_component_event(
                "TRADE_EXECUTION",
                "Trade aborted by decision engine",
                level=logging.INFO,
                details={"symbol": symbol, "reason": trade_signal},
            )
            return False, trade_signal

        # Calculate enhanced confidence
        all_confidence = []
        if ml_predictions:
            all_confidence.extend(
                [pred["confidence"] for pred in ml_predictions.values()]
            )
        all_confidence.extend([sig["confidence"] for sig in technical_signals])
        if ensemble_signal:
            all_confidence.append(ensemble_signal["confidence"])
        if crt_signal:
            all_confidence.append(crt_signal["confidence"])

        avg_confidence = np.mean(all_confidence) if all_confidence else 0.5

        # Get volatility for position sizing
        volatility = self.calculate_volatility(historical_prices)

        # Calculate portfolio health
        portfolio_health = self.calculate_portfolio_health()

        if trade_signal in ["BUY", "STRONG_BUY"]:
            quantity, position_value = self.calculate_ultimate_position_size(
                symbol,
                market_data["price"],
                avg_confidence,
                volatility,
                ensemble_signal,
                portfolio_health,
            )
            min_notional = self._get_symbol_min_notional(symbol)
            if min_notional and market_data.get("price"):
                try:
                    notional = float(position_value)
                    min_value = float(min_notional) * float(
                        TRADING_CONFIG.get("min_notional_buffer", 1.0) or 1.0
                    )
                    if notional < min_value:
                        message = f"Position value {notional:.2f} below Binance minNotional {min_value:.2f}"
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Trade blocked: below min notional",
                            level=logging.WARNING,
                            details={
                                "symbol": symbol,
                                "notional": notional,
                                "min_value": min_value,
                            },
                        )
                        if hasattr(self.trade_history, "log_journal_event"):
                            self.trade_history.log_journal_event(
                                "MIN_NOTIONAL_BLOCK",
                                {
                                    "symbol": symbol,
                                    "desired_notional": notional,
                                    "min_value": min_value,
                                    "price": market_data["price"],
                                },
                            )
                        return False, message
                except Exception as exc:
                    bot_logger.warning(
                        "Unable to verify notional for %s error=%s", symbol, exc
                    )
            approved, reason = self.safety_manager.approve_trade(
                symbol,
                position_value,
                self.balance,
                market_stress=market_stress,
                volatility=volatility,
                portfolio_health=portfolio_health,
            )
            if not approved:
                log_component_event(
                    "TRADE_EXECUTION",
                    "Trade blocked by safety manager",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "reason": reason,
                        "position_value": round(float(position_value), 2)
                        if isinstance(position_value, (int, float))
                        else position_value,
                    },
                )
                if hasattr(self.trade_history, "log_journal_event"):
                    self.trade_history.log_journal_event(
                        "SAFETY_BLOCK",
                        {
                            "symbol": symbol,
                            "reason": reason,
                            "position_value": position_value,
                            "market_stress": market_stress,
                            "volatility": volatility,
                        },
                    )
                return False, f"Safety block: {reason}"

            if self.balance >= position_value and quantity > 0:
                pre_trade_balance = self.balance
                existing_position = symbol in self.positions
                previous_position_snapshot = (
                    deepcopy(self.positions.get(symbol)) if existing_position else None
                )

                self.balance -= position_value
                entry_price = market_data["price"]

                # Enhanced position management with advanced stop-loss
                if existing_position:
                    old_pos = self.positions[symbol]
                    new_qty = old_pos["quantity"] + quantity
                    new_avg = (
                        (old_pos["quantity"] * old_pos["avg_price"])
                        + (quantity * entry_price)
                    ) / new_qty

                    # Calculate advanced stop-loss levels
                    atr_value = self.calculate_atr(historical_prices)
                    stops = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, new_avg, entry_price, historical_prices, atr_value
                    )

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965

                    self.positions[symbol] = {
                        "quantity": new_qty,
                        "avg_price": new_avg,
                        "entry_time": datetime.now(),
                        "take_profit": new_avg * tp_multiplier,
                        "stop_loss": new_avg * sl_multiplier,
                        "signal_strength": trade_signal,
                        "advanced_stops": stops,
                    }
                else:
                    # New position with ultimate parameters
                    atr_value = self.calculate_atr(historical_prices)
                    stops = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, entry_price, entry_price, historical_prices, atr_value
                    )

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965

                    self.positions[symbol] = {
                        "quantity": quantity,
                        "avg_price": entry_price,
                        "entry_time": datetime.now(),
                        "take_profit": entry_price * tp_multiplier,
                        "stop_loss": entry_price * sl_multiplier,
                        "signal_strength": trade_signal,
                        "advanced_stops": stops,
                    }

                ensemble_block = {}
                if isinstance(ml_predictions, dict):
                    ensemble_block = (
                        ml_predictions.get(
                            self.indicator_block_key,
                            ml_predictions.get("ultimate_ensemble", {}),
                        )
                        or {}
                    )

                # NEW: Enhanced trade recording with comprehensive data
                trade_data = {
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": quantity,
                    "price": entry_price,
                    "total": position_value,
                    "pnl": 0,
                    "pnl_percent": 0,
                    "signal": trade_signal,
                    "confidence": avg_confidence,
                    "type": self.trade_type_label,
                    "strategy": self.strategy_label,
                    "market_regime": market_regime,
                    "indicators_used": ensemble_block.get("indicators_total", 0),
                    "data_source": ensemble_block.get("data_source", "UNKNOWN"),
                    "ensemble_agreement": ensemble_signal.get("buy_ratio", 0)
                    if ensemble_signal
                    else 0,
                    "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                    "market_stress": market_stress,
                    "advanced_stops_used": True,
                    "crt_signal": crt_signal,  # NEW: Include CRT signal data
                    "position_size_percent": (position_value / self.initial_balance)
                    * 100,
                    "profile": self.profile_prefix,
                }

                execution_mode = "paper"
                real_order_id = None
                real_response = None

                log_component_event(
                    "TRADE_EXECUTION",
                    "Executing BUY trade",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                        "price": round(float(entry_price), 4)
                        if isinstance(entry_price, (int, float))
                        else entry_price,
                        "signal": trade_signal,
                        "confidence": round(float(avg_confidence), 3)
                        if isinstance(avg_confidence, (int, float))
                        else avg_confidence,
                    },
                )

                if self.real_trading_enabled:
                    real_response = self._submit_real_order(
                        symbol, "BUY", quantity, price=entry_price
                    )
                    if real_response is None:
                        self.balance = pre_trade_balance
                        if existing_position:
                            if previous_position_snapshot is not None:
                                self.positions[symbol] = previous_position_snapshot
                            else:
                                self.positions.pop(symbol, None)
                        else:
                            self.positions.pop(symbol, None)
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Real BUY order failed, reverting trade",
                            level=logging.WARNING,
                            details={
                                "symbol": symbol,
                                "quantity": round(float(quantity), 6)
                                if isinstance(quantity, (int, float))
                                else quantity,
                            },
                        )
                        return False, "Real BUY order failed"

                    execution_mode = "real"
                    real_order_id = (
                        real_response.get("orderId")
                        if isinstance(real_response, dict)
                        else None
                    )
                    filled_qty = self._extract_filled_quantity(real_response, quantity)
                    net_qty = self._calculate_net_filled_quantity(
                        symbol, filled_qty, order_response=real_response
                    )
                    if net_qty <= 0:
                        self.balance = pre_trade_balance
                        if existing_position:
                            if previous_position_snapshot is not None:
                                self.positions[symbol] = previous_position_snapshot
                            else:
                                self.positions.pop(symbol, None)
                        else:
                            self.positions.pop(symbol, None)
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Real BUY order resulted in zero net quantity",
                            level=logging.WARNING,
                            details={"symbol": symbol, "filled_qty": filled_qty},
                        )
                        return False, "Real BUY order failed"

                    quote_spent = self._calculate_quote_spent(
                        real_response, filled_qty, entry_price
                    )
                    if quote_spent <= 0:
                        quote_spent = filled_qty * entry_price

                    commissions = self._extract_commissions(real_response)
                    quote_asset = self._determine_quote_asset(symbol)
                    base_asset = self._determine_base_asset(symbol)
                    quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                    base_commission = _safe_float(commissions.get(base_asset), 0.0)

                    actual_total_spent = quote_spent + quote_commission

                    # Deduct actual spent (including quote commission) from cash balance
                    self.balance = pre_trade_balance - actual_total_spent

                    prev_qty = (
                        previous_position_snapshot["quantity"]
                        if (existing_position and previous_position_snapshot)
                        else 0.0
                    )
                    prev_avg = (
                        previous_position_snapshot["avg_price"]
                        if (existing_position and previous_position_snapshot)
                        else entry_price
                    )
                    total_qty = prev_qty + net_qty

                    position_record = self.positions.get(symbol, {})
                    position_record["quantity"] = total_qty
                    if total_qty > 0:
                        total_cost = (prev_qty * prev_avg) + actual_total_spent
                        avg_price = total_cost / total_qty
                    else:
                        avg_price = entry_price
                    position_record["avg_price"] = avg_price
                    if existing_position and previous_position_snapshot:
                        position_record["entry_time"] = previous_position_snapshot.get(
                            "entry_time",
                            position_record.get("entry_time", datetime.now()),
                        )
                    else:
                        position_record["entry_time"] = datetime.now()

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965
                    position_record["take_profit"] = avg_price * tp_multiplier
                    position_record["stop_loss"] = avg_price * sl_multiplier

                    atr_value = self.calculate_atr(historical_prices)
                    position_record[
                        "advanced_stops"
                    ] = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, avg_price, avg_price, historical_prices, atr_value
                    )
                    self.positions[symbol] = position_record

                    trade_data["quantity"] = net_qty
                    trade_data["total"] = quote_spent
                    trade_data["quote_spent"] = quote_spent
                    trade_data["quote_commission"] = quote_commission
                    trade_data["base_commission"] = base_commission
                    trade_data["base_received"] = net_qty
                    trade_data["commissions"] = commissions
                    if self.initial_balance:
                        trade_data["position_size_percent"] = (
                            actual_total_spent / self.initial_balance
                        ) * 100

                    self._handle_auto_take_profit(
                        symbol, avg_price, total_qty, order_response=real_response
                    )

                trade_data["execution_mode"] = execution_mode
                if real_order_id:
                    trade_data["real_order_id"] = real_order_id

                self.trade_history.add_trade(trade_data)
                self.bot_efficiency["total_trades"] += 1

                action_msg = (
                    f"🎯 {self.profile_prefix} BUY"
                    if trade_signal == "BUY"
                    else f"🎯💥 {self.profile_prefix} STRONG BUY"
                )
                return (
                    True,
                    f"{action_msg}: {quantity:.4f} {symbol} at ${entry_price:.2f}",
                )

        elif trade_signal in ["SELL", "STRONG_SELL"] and symbol in self.positions:
            position = self.positions[symbol]
            quantity = position["quantity"]
            sale_price = market_data["price"]
            sale_value = quantity * sale_price

            pnl = sale_value - (quantity * position["avg_price"])
            pnl_percent = (
                (pnl / (quantity * position["avg_price"])) * 100
                if position["avg_price"] > 0
                else 0
            )

            pre_trade_balance = self.balance
            position_snapshot = deepcopy(position)

            ensemble_block = {}
            if isinstance(ml_predictions, dict):
                ensemble_block = (
                    ml_predictions.get(
                        self.indicator_block_key,
                        ml_predictions.get("ultimate_ensemble", {}),
                    )
                    or {}
                )

            trade_data = {
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": sale_price,
                "total": sale_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "signal": trade_signal,
                "confidence": avg_confidence,
                "type": self.trade_type_label,
                "strategy": self.strategy_label,
                "market_regime": market_regime,
                "indicators_used": ensemble_block.get("indicators_total", 0),
                "data_source": ensemble_block.get("data_source", "UNKNOWN"),
                "ensemble_agreement": ensemble_signal.get("sell_ratio", 0)
                if ensemble_signal
                else 0,
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": market_stress,
                "advanced_stops_used": True,
                "crt_signal": crt_signal,  # NEW: Include CRT signal data
                "position_size_percent": (
                    position["quantity"] * position["avg_price"] / self.initial_balance
                )
                * 100,
                "profile": self.profile_prefix,
            }

            execution_mode = "paper"
            real_order_id = None
            real_response = None

            log_component_event(
                "TRADE_EXECUTION",
                "Executing SELL trade",
                level=logging.INFO,
                details={
                    "symbol": symbol,
                    "quantity": round(float(quantity), 6)
                    if isinstance(quantity, (int, float))
                    else quantity,
                    "price": round(float(sale_price), 4)
                    if isinstance(sale_price, (int, float))
                    else sale_price,
                    "signal": trade_signal,
                    "pnl_percent": round(float(pnl_percent), 3)
                    if isinstance(pnl_percent, (int, float))
                    else pnl_percent,
                },
            )

            if self.real_trading_enabled:
                self._cancel_auto_take_profit(symbol)
                real_response = self._submit_real_order(
                    symbol, "SELL", quantity, price=sale_price
                )
                if (
                    isinstance(real_response, dict)
                    and real_response.get("status") == "SKIPPED"
                ):
                    skip_reason = real_response.get("reason")
                    skip_message = (
                        real_response.get("message") or skip_reason or "Skipped"
                    )
                    log_component_event(
                        "TRADE_EXECUTION",
                        "Real SELL skipped",
                        level=logging.WARNING,
                        details={
                            "symbol": symbol,
                            "reason": skip_reason,
                            "details": real_response,
                        },
                    )
                    if skip_reason in {"min_notional", "insufficient_quantity"}:
                        self.positions.pop(symbol, None)
                    else:
                        self.positions[symbol] = position_snapshot
                    return False, f"Real SELL skipped: {skip_message}"
                if real_response is None:
                    self.balance = pre_trade_balance
                    self.positions[symbol] = position_snapshot
                    failure_reason = getattr(self.real_trader, "last_error", "unknown")
                    log_component_event(
                        "TRADE_EXECUTION",
                        "Real SELL order failed, reverting trade",
                        level=logging.WARNING,
                        details={
                            "symbol": symbol,
                            "quantity": round(float(quantity), 6)
                            if isinstance(quantity, (int, float))
                            else quantity,
                            "reason": failure_reason,
                        },
                    )
                    return False, f"Real SELL order failed: {failure_reason}"

                execution_mode = "real"
                real_order_id = (
                    real_response.get("orderId")
                    if isinstance(real_response, dict)
                    else None
                )
                # compute actual quote received and commissions
                executed_qty = self._extract_filled_quantity(real_response, quantity)
                quote_received = self._calculate_quote_spent(
                    real_response, executed_qty, sale_price
                )
                commissions = self._extract_commissions(real_response)
                quote_asset = self._determine_quote_asset(symbol)
                quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                net_credit = quote_received - quote_commission
                # apply net credit to balance
                self.balance = pre_trade_balance + net_credit
                # update recorded sale_value to actual received for reporting
                sale_value = quote_received
                trade_data["commissions"] = commissions
                trade_data["quote_received"] = quote_received
                trade_data["quote_commission"] = quote_commission
            else:
                # paper trading: apply theoretical sale_value
                self.balance += sale_value

            self.safety_manager.register_trade_result(symbol, pnl)

            # Update performance tracking
            self.daily_pnl += pnl
            current_total = self.balance + sum(
                pos["quantity"] * market_data["price"]
                for pos in self.positions.values()
            )
            self.peak_balance = max(self.peak_balance, current_total)
            drawdown = (
                (self.peak_balance - current_total) / self.peak_balance
                if self.peak_balance > 0
                else 0
            )
            self.max_drawdown = max(self.max_drawdown, drawdown)

            # Update bot efficiency
            self.bot_efficiency["total_trades"] += 1
            if pnl > 0:
                self.bot_efficiency["successful_trades"] += 1
            self.bot_efficiency["total_profit"] += pnl

            trade_data["execution_mode"] = execution_mode
            if real_order_id:
                trade_data["real_order_id"] = real_order_id
            self.trade_history.add_trade(trade_data)

            action_msg = (
                f"🎯 {self.profile_prefix} SELL"
                if trade_signal == "SELL"
                else f"🎯💥 {self.profile_prefix} STRONG SELL"
            )
            return (
                True,
                f"{action_msg}: {quantity:.4f} {symbol} at ${sale_price:.2f} (P&L: {pnl_percent:+.2f}%)",
            )

        log_component_debug(
            "TRADE_EXECUTION",
            "No execution action taken",
            {"symbol": symbol, "trade_signal": trade_signal},
        )
        return False, f"No action: {trade_signal}"

    def calculate_volatility(self, prices, period=20):
        """Calculate volatility from price data"""
        if len(prices) < period:
            return 0.02

        returns = np.diff(np.log(prices[-period:]))
        return np.std(returns) if len(returns) > 0 else 0.02

    def calculate_atr(self, prices, period=14):
        """Calculate Average True Range"""
        if len(prices) < period:
            return 0.02

        # Simplified ATR calculation
        price_changes = np.diff(prices[-period:])
        return np.mean(np.abs(price_changes)) if len(price_changes) > 0 else 0.02

    def calculate_portfolio_health(self):
        """Calculate portfolio health indicator"""
        try:
            # Factor 1: Drawdown
            drawdown_penalty = min(self.max_drawdown * 3, 0.5)

            # Factor 2: Concentration
            if self.positions:
                position_values = [
                    pos["quantity"] * pos["avg_price"]
                    for pos in self.positions.values()
                ]
                concentration = (
                    max(position_values) / sum(position_values)
                    if sum(position_values) > 0
                    else 0
                )
                concentration_penalty = concentration * 0.3
            else:
                concentration_penalty = 0

            # Factor 3: Recent performance
            recent_trades = [
                t
                for t in self.trade_history.get_trade_history()[-10:]
                if "pnl_percent" in t
            ]
            if recent_trades:
                recent_performance = (
                    np.mean([t["pnl_percent"] for t in recent_trades]) / 100
                )
                performance_penalty = max(-recent_performance, 0) * 2
            else:
                performance_penalty = 0

            health = (
                1.0 - drawdown_penalty - concentration_penalty - performance_penalty
            )
            return max(0.3, min(1.5, health))

        except Exception as e:
            print(f"❌ Portfolio health calculation error: {e}")
            log_component_event(
                "PORTFOLIO",
                f"Portfolio health calculation error: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("Portfolio health calculation error")
            return 1.0

    def generate_technical_signals(self, symbol, market_data, historical_prices):
        """Enhanced technical signals with multiple timeframes"""
        signals = []

        if len(historical_prices) < 20:
            return signals

        prices = np.array(historical_prices)
        current_price = market_data["price"]

        try:
            # Multi-timeframe RSI
            for period in [7, 14, 21]:
                rsi = talib.RSI(prices, timeperiod=period)
                if len(rsi) > 0 and not np.isnan(rsi[-1]):
                    current_rsi = rsi[-1]

                    if current_rsi < 20:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.80,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.20),
                                "stop_loss": float(current_price * 0.95),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_EXTREME_OVERSOLD",
                                "strategy": f"RSI_{period}_EXTREME_OVERSOLD",
                                "signal": "STRONG_BUY",
                                "confidence": 0.80,
                                "price_target": current_price * 1.20,
                            }
                        )
                    elif current_rsi < 25:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.75,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.15),
                                "stop_loss": float(current_price * 0.96),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_STRONG_OVERSOLD",
                                "strategy": f"RSI_{period}_STRONG_OVERSOLD",
                                "signal": "STRONG_BUY",
                                "confidence": 0.75,
                                "price_target": current_price * 1.15,
                            }
                        )
                    elif current_rsi < 30:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.65,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.08),
                                "stop_loss": float(current_price * 0.97),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_OVERSOLD",
                                "strategy": f"RSI_{period}_OVERSOLD",
                                "signal": "BUY",
                                "confidence": 0.65,
                                "price_target": current_price * 1.08,
                            }
                        )
                    elif current_rsi > 80:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.80,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.82),
                                "stop_loss": float(current_price * 1.05),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_EXTREME_OVERBOUGHT",
                                "strategy": f"RSI_{period}_EXTREME_OVERBOUGHT",
                                "signal": "STRONG_SELL",
                                "confidence": 0.80,
                                "price_target": current_price * 0.82,
                            }
                        )
                    elif current_rsi > 75:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.75,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.85),
                                "stop_loss": float(current_price * 1.04),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_STRONG_OVERBOUGHT",
                                "strategy": f"RSI_{period}_STRONG_OVERBOUGHT",
                                "signal": "STRONG_SELL",
                                "confidence": 0.75,
                                "price_target": current_price * 0.85,
                            }
                        )
                    elif current_rsi > 70:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.65,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.92),
                                "stop_loss": float(current_price * 1.03),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_OVERBOUGHT",
                                "strategy": f"RSI_{period}_OVERBOUGHT",
                                "signal": "SELL",
                                "confidence": 0.65,
                                "price_target": current_price * 0.92,
                            }
                        )
        except Exception as e:
            print(f"❌ RSI calculation error for {symbol}: {e}")
            log_component_event(
                "SIGNALS",
                f"RSI calculation error for {symbol}: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("RSI calculation error for %s", symbol)

        try:
            # Enhanced MACD with histogram analysis
            macd, macd_signal, macd_hist = talib.MACD(prices)
            if len(macd_hist) > 0:
                current_hist = macd_hist[-1]
                prev_hist = macd_hist[-2] if len(macd_hist) > 1 else 0
                prev_prev_hist = macd_hist[-3] if len(macd_hist) > 2 else 0

                # Strong bullish: histogram positive and accelerating
                if (
                    current_hist > 0
                    and current_hist > prev_hist
                    and prev_hist > prev_prev_hist
                ):
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.75,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 1.05),
                            "stop_loss": float(current_price * 0.97),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_STRONG_BULLISH_ACCEL",
                            "strategy": "MACD_STRONG_BULLISH_ACCEL",
                            "signal": "STRONG_BUY",
                            "confidence": 0.75,
                        }
                    )
                elif current_hist > 0 and current_hist > prev_hist:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.65,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 1.03),
                            "stop_loss": float(current_price * 0.98),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_BULLISH",
                            "strategy": "MACD_BULLISH",
                            "signal": "BUY",
                            "confidence": 0.65,
                        }
                    )
                # Strong bearish: histogram negative and accelerating
                elif (
                    current_hist < 0
                    and current_hist < prev_hist
                    and prev_hist < prev_prev_hist
                ):
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.75,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 0.95),
                            "stop_loss": float(current_price * 1.03),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_STRONG_BEARISH_ACCEL",
                            "strategy": "MACD_STRONG_BEARISH_ACCEL",
                            "signal": "STRONG_SELL",
                            "confidence": 0.75,
                        }
                    )
                elif current_hist < 0 and current_hist < prev_hist:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.65,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 0.97),
                            "stop_loss": float(current_price * 1.02),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_BEARISH",
                            "strategy": "MACD_BEARISH",
                            "signal": "SELL",
                            "confidence": 0.65,
                        }
                    )
        except Exception as e:
            print(f"❌ MACD calculation error for {symbol}: {e}")
            log_component_event(
                "SIGNALS",
                f"MACD calculation error for {symbol}: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("MACD calculation error for %s", symbol)

        if getattr(self, "qfm_engine", None):
            try:
                self.qfm_engine.compute_realtime_features(
                    symbol, market_data, historical_prices
                )
                qfm_signal = self.qfm_engine.generate_signal(symbol)
                if qfm_signal:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "QFM",
                            "confidence_score": qfm_signal.get("confidence", 0.6),
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": qfm_signal.get(
                                "target_price", float(current_price * 1.02)
                            ),
                            "stop_loss": qfm_signal.get(
                                "stop_loss", float(current_price * 0.98)
                            ),
                            "time_frame": "MULTI_TIMEFRAME",
                            "model_version": "QFM_v1.0",
                            "reason_code": qfm_signal.get(
                                "reason_code", f'QFM_{qfm_signal.get("signal", "HOLD")}'
                            ),
                            "strategy": qfm_signal.get(
                                "strategy", "QUANTUM_FUSION_MOMENTUM"
                            ),
                            "signal": qfm_signal.get("signal", "HOLD"),
                            "confidence": qfm_signal.get("confidence", 0.6),
                            "score": qfm_signal.get("score"),
                            "metrics": qfm_signal.get("metrics"),
                            "type": "QFM",  # Add type field for proper weighting
                        }
                    )
                    try:
                        if "dashboard_data" in globals():
                            profile_key = (
                                "optimized_qfm_signals"
                                if str(getattr(self, "profile_prefix", ""))
                                .upper()
                                .startswith("OPTIMIZED")
                                else "qfm_signals"
                            )
                            dashboard_data.setdefault(profile_key, {})
                            dashboard_data[profile_key][symbol] = {
                                "symbol": symbol,
                                "signal": qfm_signal.get("signal", "HOLD"),
                                "confidence": float(
                                    qfm_signal.get("confidence", 0.0) or 0.0
                                ),
                                "score": float(qfm_signal.get("score", 0.0) or 0.0),
                                "metrics": qfm_signal.get("metrics", {}),
                                "price": _safe_float(market_data.get("price"))
                                if isinstance(market_data, dict)
                                else None,
                                "updated_at": datetime.utcnow().isoformat(),
                            }
                    except Exception as dash_exc:
                        bot_logger.warning(
                            "Failed to update QFM dashboard data for %s: %s",
                            symbol,
                            dash_exc,
                        )
            except Exception as e:
                print(f"❌ QFM signal generation error for {symbol}: {e}")
                log_component_event(
                    "SIGNALS",
                    f"QFM signal generation error for {symbol}: {e}",
                    level=logging.ERROR,
                )
                bot_logger.exception("QFM signal generation error for %s", symbol)

        return signals

    def check_advanced_stop_loss(self, current_prices):
        """Check and execute advanced stop-loss mechanisms"""
        closed_positions = []
        for symbol, position in list(self.positions.items()):
            if symbol in current_prices:
                current_price = current_prices[symbol]

                # Check traditional stop-loss first
                if current_price <= position.get("stop_loss", 0):
                    self.execute_stop_loss(
                        symbol,
                        position,
                        current_price,
                        "TRADITIONAL_SL",
                        closed_positions,
                    )
                    continue

                # Check take profit
                if current_price >= position.get("take_profit", 0):
                    self.execute_take_profit(
                        symbol, position, current_price, closed_positions
                    )
                    continue

                # Check advanced stop-loss if enabled
                if (
                    TRADING_CONFIG["advanced_stop_loss"]
                    and "advanced_stops" in position
                ):
                    stops = position["advanced_stops"]
                    triggered_stop = self.stop_loss_system.should_trigger_stop_loss(
                        symbol, current_price, position, stops
                    )

                    if triggered_stop:
                        stop_type, stop_price = triggered_stop
                        self.execute_stop_loss(
                            symbol,
                            position,
                            current_price,
                            f"ADVANCED_{stop_type}",
                            closed_positions,
                        )

        return closed_positions

    def execute_stop_loss(
        self, symbol, position, current_price, stop_type, closed_positions
    ):
        """Execute stop-loss trade"""
        quantity = position["quantity"]
        sale_value = quantity * current_price
        pre_trade_balance = self.balance

        pnl = sale_value - (quantity * position["avg_price"])
        pnl_percent = (
            (pnl / (quantity * position["avg_price"])) * 100
            if position["avg_price"] > 0
            else 0
        )

        del self.positions[symbol]

        # NEW: Enhanced trade recording
        trade_data = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": current_price,
            "total": sale_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "signal": stop_type,
            "confidence": 1.0,
            "type": f"ADVANCED_{stop_type}",
            "strategy": "STOP_LOSS",
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "advanced_stops_used": True,
            "position_size_percent": (
                position["quantity"] * position["avg_price"] / self.initial_balance
            )
            * 100,
            "profile": self.profile_prefix,
        }
        execution_mode = "paper"
        real_order_id = None

        if self.real_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            response = self._submit_real_order(
                symbol, "SELL", quantity, price=current_price
            )
            if response is None:
                self.positions[symbol] = position
                log_component_event(
                    "STOP_LOSS",
                    "Real SELL order failed, stop-loss reverted",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                    },
                )
                return
            execution_mode = "real"
            if isinstance(response, dict):
                real_order_id = response.get("orderId")
            executed_qty = self._extract_filled_quantity(response, quantity)
            quote_received = self._calculate_quote_spent(
                response, executed_qty, current_price
            )
            commissions = self._extract_commissions(response)
            quote_asset = self._determine_quote_asset(symbol)
            quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
            net_credit = quote_received - quote_commission
            self.balance = pre_trade_balance + net_credit
            trade_data["commissions"] = commissions
            trade_data["quote_received"] = quote_received
            trade_data["quote_commission"] = quote_commission
        else:
            self.balance += sale_value

        trade_data["execution_mode"] = execution_mode
        if real_order_id:
            trade_data["real_order_id"] = real_order_id
        self.trade_history.add_trade(trade_data)

        self.safety_manager.register_trade_result(symbol, pnl)

        closed_positions.append(
            f"🛑 {stop_type}: {symbol} at ${current_price:.2f} (P&L: {pnl_percent:+.2f}%)"
        )

        # Update efficiency
        self.bot_efficiency["total_trades"] += 1
        if pnl > 0:
            self.bot_efficiency["successful_trades"] += 1
        self.bot_efficiency["total_profit"] += pnl

    def execute_take_profit(self, symbol, position, current_price, closed_positions):
        """Execute take profit trade"""
        quantity = position["quantity"]
        sale_value = quantity * current_price
        pre_trade_balance = self.balance

        pnl = sale_value - (quantity * position["avg_price"])
        pnl_percent = (
            (pnl / (quantity * position["avg_price"])) * 100
            if position["avg_price"] > 0
            else 0
        )

        del self.positions[symbol]

        # NEW: Enhanced trade recording
        trade_data = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": current_price,
            "total": sale_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "signal": "TAKE_PROFIT",
            "confidence": 1.0,
            "type": "ADVANCED_TAKE_PROFIT",
            "strategy": "TAKE_PROFIT",
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "advanced_stops_used": True,
            "position_size_percent": (
                position["quantity"] * position["avg_price"] / self.initial_balance
            )
            * 100,
            "profile": self.profile_prefix,
        }
        execution_mode = "paper"
        real_order_id = None

        if self.real_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            response = self._submit_real_order(
                symbol, "SELL", quantity, price=current_price
            )
            if response is None:
                self.positions[symbol] = position
                log_component_event(
                    "TAKE_PROFIT",
                    "Real SELL order failed, take-profit reverted",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                    },
                )
                return
            execution_mode = "real"
            if isinstance(response, dict):
                real_order_id = response.get("orderId")
            executed_qty = self._extract_filled_quantity(response, quantity)
            quote_received = self._calculate_quote_spent(
                response, executed_qty, current_price
            )
            commissions = self._extract_commissions(response)
            quote_asset = self._determine_quote_asset(symbol)
            quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
            net_credit = quote_received - quote_commission
            self.balance = pre_trade_balance + net_credit
            trade_data["commissions"] = commissions
            trade_data["quote_received"] = quote_received
            trade_data["quote_commission"] = quote_commission
        else:
            self.balance += sale_value

        trade_data["execution_mode"] = execution_mode
        if real_order_id:
            trade_data["real_order_id"] = real_order_id
        self.trade_history.add_trade(trade_data)

        self.safety_manager.register_trade_result(symbol, pnl)

        closed_positions.append(
            f"✅ ADVANCED TP: {symbol} at ${current_price:.2f} (P&L: {pnl_percent:+.2f}%)"
        )

        # Update efficiency
        self.bot_efficiency["total_trades"] += 1
        if pnl > 0:
            self.bot_efficiency["successful_trades"] += 1
        self.bot_efficiency["total_profit"] += pnl

    def force_close_all_positions(self, reason="EMERGENCY", current_prices=None):
        """Liquidate all open positions immediately."""
        if current_prices is None:
            current_prices = {}
        if not current_prices and self.latest_market_data:
            current_prices = {
                sym: data.get("price")
                for sym, data in self.latest_market_data.items()
                if isinstance(data, dict)
            }

        closed = []
        for symbol, position in list(self.positions.items()):
            sale_price = current_prices.get(symbol, position["avg_price"])
            quantity = position["quantity"]
            sale_value = quantity * sale_price
            invested = quantity * position["avg_price"]
            pnl = sale_value - invested
            pnl_percent = (pnl / invested) * 100 if invested > 0 else 0

            trade_data = {
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": sale_price,
                "total": sale_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "signal": reason,
                "confidence": 1.0,
                "type": "EMERGENCY_EXIT",
                "strategy": "EMERGENCY_STOP",
                "market_regime": self.ensemble_system.market_regime,
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": self.risk_manager.market_stress_indicator,
                "advanced_stops_used": False,
                "position_size_percent": (invested / self.initial_balance) * 100
                if self.initial_balance
                else 0,
                "profile": self.profile_prefix,
            }
            execution_mode = "paper"
            real_order_id = None

            if self.real_trading_enabled:
                self._cancel_auto_take_profit(symbol)
                response = self._submit_real_order(
                    symbol, "SELL", quantity, price=sale_price
                )
                if response is None:
                    log_component_event(
                        "EMERGENCY_EXIT",
                        "Real emergency SELL failed, skipping trade",
                        level=logging.ERROR,
                        details={
                            "symbol": symbol,
                            "quantity": round(float(quantity), 6)
                            if isinstance(quantity, (int, float))
                            else quantity,
                        },
                    )
                    continue
                execution_mode = "real"
                if isinstance(response, dict):
                    real_order_id = response.get("orderId")
                executed_qty = self._extract_filled_quantity(response, quantity)
                quote_received = self._calculate_quote_spent(
                    response, executed_qty, sale_price
                )
                commissions = self._extract_commissions(response)
                quote_asset = self._determine_quote_asset(symbol)
                quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                net_credit = quote_received - quote_commission
                self.balance += net_credit
            self.safety_manager.register_trade_result(symbol, pnl)
            trade_data["execution_mode"] = execution_mode
            if real_order_id:
                trade_data["real_order_id"] = real_order_id
            self.trade_history.add_trade(trade_data)

            closed.append(
                f"⚠️ Emergency exit {symbol}: {quantity:.4f} @ ${sale_price:.2f} (P&L: {pnl_percent:+.2f}%)"
            )
            del self.positions[symbol]

        if hasattr(self.trade_history, "log_journal_event") and closed:
            self.trade_history.log_journal_event(
                "EMERGENCY_EXIT",
                {
                    "reason": reason,
                    "closed_positions": closed,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return closed

    def improve_bot_efficiency_ultimate(self):
        """Ultimate self-improvement with all systems"""
        self.bot_efficiency["learning_cycles"] += 1
        self.bot_efficiency["last_improvement"] = datetime.now().isoformat()

        # Calculate current performance
        trades = self.trade_history.get_trade_history()
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
        if closed_trades:
            success_rate = (
                len([t for t in closed_trades if t.get("pnl", 0) > 0])
                / len(closed_trades)
            ) * 100
        else:
            success_rate = 0

        # Update risk manager
        portfolio_performance = (
            self.balance
            + sum(pos["quantity"] * 100 for pos in self.positions.values())
            - self.initial_balance
        ) / self.initial_balance

        risk_adjustment = self.risk_manager.adjust_risk_profile(
            portfolio_performance,
            self.max_drawdown,
            {"market_stress": self.risk_manager.market_stress_indicator},
        )

        # Store market stress history
        self.bot_efficiency["market_stress_history"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "stress_level": self.risk_manager.market_stress_indicator,
                "risk_profile": self.risk_manager.current_risk_profile,
            }
        )

        # Keep only last 50 entries
        if len(self.bot_efficiency["market_stress_history"]) > 50:
            self.bot_efficiency["market_stress_history"].pop(0)

        # Advanced strategy adjustment
        if success_rate < 30:
            TRADING_CONFIG["confidence_threshold"] = max(
                0.45, TRADING_CONFIG["confidence_threshold"] - 0.04
            )
            print(
                f"🤖 {self.profile_prefix} Learning: Lowering confidence to {TRADING_CONFIG['confidence_threshold']}"
            )

        elif success_rate > 70:
            TRADING_CONFIG["risk_per_trade"] = min(
                0.025, TRADING_CONFIG["risk_per_trade"] + 0.004
            )
            print(
                f"🤖 {self.profile_prefix} Learning: Increasing risk to {TRADING_CONFIG['risk_per_trade']}"
            )

        print(
            f"🤖 {self.profile_prefix} Learning: Success Rate: {success_rate:.1f}%, Risk Profile: {self.risk_manager.current_risk_profile}"
        )
        return success_rate

    def get_portfolio_summary(self, current_prices):
        """Ultimate portfolio summary"""
        positions = []
        total_invested = 0
        total_current = 0

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                quantity = position["quantity"]
                avg_price = position["avg_price"]
                invested = quantity * avg_price
                current_value = quantity * current_price
                pnl = current_value - invested
                pnl_percent = (pnl / invested) * 100 if invested > 0 else 0

                tp_price = position.get("take_profit", current_price)
                sl_price = position.get("stop_loss", current_price)
                tp_percent = ((tp_price / avg_price) - 1) * 100
                sl_percent = ((sl_price / avg_price) - 1) * 100

                positions.append(
                    {
                        "symbol": symbol,
                        "quantity": quantity,
                        "avg_price": avg_price,
                        "current_price": current_price,
                        "invested": invested,
                        "current_value": current_value,
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "take_profit_percent": tp_percent,
                        "stop_loss_percent": sl_percent,
                        "entry_time": position["entry_time"],
                        "signal_strength": position.get("signal_strength", "BUY"),
                        "advanced_stops": position.get("advanced_stops", {}),
                    }
                )
                total_invested += invested
                total_current += current_value

        paper_total_value = self.balance + total_current
        total_pnl = paper_total_value - self.initial_balance
        total_return_percent = (
            (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        )

        paper_snapshot = {
            "balance": self.balance,
            "total_invested": total_invested,
            "total_current_value": total_current,
            "total_value": paper_total_value,
            "total_pnl": total_pnl,
            "total_return_percent": total_return_percent,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Calculate ultimate efficiency metrics
        trades = self.trade_history.get_trade_history()
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
        if closed_trades:
            efficiency = (
                len([t for t in closed_trades if t.get("pnl", 0) > 0])
                / len(closed_trades)
            ) * 100
        else:
            efficiency = 0

        summary = {
            "balance": self.balance,
            "paper_balance": self.balance,
            "total_invested": total_invested,
            "total_current_value": total_current,
            "paper_total_value": paper_total_value,
            "total_portfolio_value": paper_total_value,
            "total_pnl": total_pnl,
            "total_return_percent": total_return_percent,
            "positions": positions,
            "initial_balance": self.initial_balance,
            "trading_enabled": self.trading_enabled,
            "max_drawdown": self.max_drawdown,
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "risk_profile": self.risk_manager.current_risk_profile,
            "portfolio_health": self.calculate_portfolio_health(),
            "mode": "paper",
            "data_source": "paper_simulated",
            "real_holdings": [],
            "real_cash": None,
            "cash_breakdown": [],
            "real_equity": None,
            "bot_efficiency": {
                "success_rate": efficiency,
                "total_trades": self.bot_efficiency["total_trades"],
                "successful_trades": self.bot_efficiency["successful_trades"],
                "total_profit": self.bot_efficiency["total_profit"],
                "learning_cycles": self.bot_efficiency["learning_cycles"],
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": self.risk_manager.market_stress_indicator,
                "last_improvement": self.bot_efficiency["last_improvement"],
            },
            "paper_snapshot": paper_snapshot,
            "real_account_snapshot": None,
        }
        real_snapshot = self._get_real_account_snapshot(current_prices)
        summary["real_account_snapshot"] = real_snapshot
        if real_snapshot and real_snapshot.get("total_equity") is not None:
            if self.real_equity_baseline is None:
                self.real_equity_baseline = real_snapshot["total_equity"]

            baseline = self.real_equity_baseline or 0.0
            real_pnl = 0.0
            real_return = 0.0
            if baseline:
                real_pnl = real_snapshot["total_equity"] - baseline
                real_return = (real_pnl / baseline) * 100 if baseline else 0.0

            summary.update(
                {
                    "balance": real_snapshot["cash"],
                    "total_invested": real_snapshot["asset_value"],
                    "total_current_value": real_snapshot["asset_value"],
                    "total_portfolio_value": real_snapshot["total_equity"],
                    "total_pnl": real_pnl,
                    "total_return_percent": real_return,
                    "mode": "real",
                    "data_source": "binance_spot",
                    "real_holdings": real_snapshot["holdings"],
                    "real_cash": real_snapshot["cash"],
                    "cash_breakdown": real_snapshot["cash_breakdown"],
                    "real_equity": real_snapshot["total_equity"],
                    "real_equity_baseline": baseline,
                    "real_account_can_trade": real_snapshot.get("can_trade"),
                    "real_account_updated_at": real_snapshot.get("updated_at"),
                    "paper_balance": None,
                    "paper_total_value": None,
                }
            )

        return summary

    # NEW: Get comprehensive trade statistics
    def get_trade_statistics(self):
        """Get comprehensive trade statistics"""
        return self.trade_history.get_trade_statistics()


# ==================== OPTIMIZED AI TRADER ====================
class OptimizedAIAutoTrader(UltimateAIAutoTrader):
    def __init__(self, initial_balance=10000):
        self.profile_prefix = "OPTIMIZED"
        self.trade_type_label = "OPTIMIZED_TRADE"
        self.strategy_label = "20_INDICATORS_OPTIMIZED"
        self.indicator_block_key = "optimized_ensemble"
        super().__init__(initial_balance=initial_balance)
        self.trade_history = ComprehensiveTradeHistory(
            data_dir="optimized_trade_data",
            log_callback=log_component_event,
        )
        self.optimized_config = OPTIMIZED_TRADING_CONFIG.copy()
        print(
            f"🧠 {self.profile_prefix} Trader configured with curated indicator blueprint"
        )


# ==================== ENHANCED TRADE HISTORY WITH CLEAR HISTORY ====================
# Note: This class is now replaced by ComprehensiveTradeHistory but kept for compatibility
class EnhancedTradeHistory:
    def __init__(self, data_dir="trade_data"):
        self.comprehensive_history = ComprehensiveTradeHistory(
            data_dir,
            log_callback=log_component_event,
        )

    def add_trade(self, trade_data):
        """Add trade - compatibility method"""
        return self.comprehensive_history.add_trade(trade_data)

    def load_trades(self):
        """Load trades - compatibility method"""
        return self.comprehensive_history.load_trades()

    def save_trades(self, trades):
        """Save trades - compatibility method"""
        return self.comprehensive_history.save_trades(trades)

    def clear_history(self):
        """Clear history - compatibility method"""
        return self.comprehensive_history.clear_history()

    def get_trades(self, days=None, symbol=None, page=1, per_page=20):
        """Get trades with pagination - compatibility method"""
        filters = {}
        if days:
            filters["days"] = days
        if symbol:
            filters["symbol"] = symbol

        trades = self.comprehensive_history.get_trade_history(filters)

        # Pagination
        total_trades = len(trades)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_trades = trades[start_idx:end_idx]

        return {
            "trades": paginated_trades,
            "total_trades": total_trades,
            "current_page": page,
            "total_pages": (total_trades + per_page - 1) // per_page,
            "per_page": per_page,
        }

    def get_performance_summary(self):
        """Get performance summary - compatibility method"""
        stats = self.comprehensive_history.get_trade_statistics()
        return (
            stats["summary"]
            if "summary" in stats
            else {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
            }
        )

    def create_performance_chart(self, days=30):
        """Create performance chart - compatibility method"""
        # Implementation would go here
        return None

    def export_to_csv(self):
        """Export to CSV - compatibility method"""
        return self.comprehensive_history.export_to_csv()


# ==================== MARKET DATA FUNCTIONS ====================

_binance_market_helper: Optional[BinanceMarketDataHelper] = None


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ensure_binance_market_helper() -> BinanceMarketDataHelper:
    if _binance_market_helper is None:
        raise RuntimeError("Binance market data helper not initialized yet")
    return _binance_market_helper


def fetch_binance_24hr_ticker(symbol=None, timeout=10):
    """Compatibility wrapper for legacy callers."""
    helper = _ensure_binance_market_helper()
    return helper.fetch_24hr_ticker(symbol=symbol, timeout=timeout)


def get_trending_pairs():
    helper = _ensure_binance_market_helper()
    return helper.get_trending_pairs()


def get_real_market_data(symbol):
    helper = _ensure_binance_market_helper()
    return helper.get_real_market_data(symbol)


def get_emergency_predictions(symbol, market_data):
    """Emergency fallback predictions"""
    if not market_data:
        return None
    price_change = market_data.get("change", 0)
    if price_change > 2:
        signal, confidence = "BUY", 0.65
    elif price_change < -2:
        signal, confidence = "SELL", 0.65
    elif price_change > 0:
        signal, confidence = "BUY", 0.55
    elif price_change < 0:
        signal, confidence = "SELL", 0.55
    else:
        signal, confidence = "HOLD", 0.5
    return {
        "emergency_model": {
            "signal": signal,
            "confidence": confidence,
            "prediction": 2 if signal == "BUY" else 0,
        }
    }


def _detect_testnet_exchange_session() -> bool:
    try:
        for trader_name in ("ultimate_trader", "optimized_trader"):
            trader = globals().get(trader_name)
            if not trader:
                continue
            for attr in ("real_trader", "futures_trader"):
                client = getattr(trader, attr, None)
                if client and getattr(client, "testnet", False):
                    return True
    except Exception:
        pass
    return False


def _binance_api_success_hook() -> None:
    for trader_name in ("ultimate_trader", "optimized_trader"):
        trader = globals().get(trader_name)
        safety_manager = getattr(trader, "safety_manager", None)
        clear_api_failures = getattr(safety_manager, "clear_api_failures", None)
        if callable(clear_api_failures):
            try:
                clear_api_failures()
            except Exception:
                continue


def _binance_api_failure_hook(message: str) -> None:
    for trader_name in ("ultimate_trader", "optimized_trader"):
        trader = globals().get(trader_name)
        safety_manager = getattr(trader, "safety_manager", None)
        log_api_failure = getattr(safety_manager, "log_api_failure", None)
        if callable(log_api_failure):
            try:
                log_api_failure(message)
            except Exception:
                continue


def _initialize_binance_market_helper() -> None:
    global _binance_market_helper
    _binance_market_helper = BinanceMarketDataHelper(
        bot_logger=bot_logger,
        safe_float=_safe_float,
        testnet_detector=_detect_testnet_exchange_session,
        binance_log_manager=binance_log_manager,
        warning_cooldown=BINANCE_WARNING_COOLDOWN,
        api_success_hooks=[_binance_api_success_hook],
        api_failure_hooks=[_binance_api_failure_hook],
    )


# ==================== INITIALIZE ULTIMATE COMPONENTS ====================
ml_services = build_ml_runtime_services(
    ultimate_factory=UltimateMLTrainingSystem,
    optimized_factory=OptimizedMLTrainingSystem,
    futures_factory=FuturesMLTrainingSystem,
)


trading_runtime = build_trading_runtime_services(
    ml_bundle=ml_services,
    trade_history_factory=lambda: ComprehensiveTradeHistory(
        log_callback=log_component_event
    ),
    ultimate_trader_factory=lambda: UltimateAIAutoTrader(initial_balance=1000),
    optimized_trader_factory=lambda: OptimizedAIAutoTrader(initial_balance=1000),
    parallel_engine_factory=ParallelPredictionEngine,
)
trading_services = trading_runtime.trading_services

trade_history = trading_services.trade_history  # NEW: Use ComprehensiveTradeHistory
ultimate_trader = trading_services.ultimate_trader
optimized_trader = trading_services.optimized_trader
parallel_engine = trading_services.parallel_engine

ultimate_ml_system = ml_services.ultimate_ml_system
optimized_ml_system = ml_services.optimized_ml_system
futures_ml_system = ml_services.futures_ml_system

get_user_trader = trading_runtime.get_user_trader

indicator_snapshot = get_all_indicator_selections()

futures_dashboard_state = {
    "enabled": TRADING_CONFIG.get("futures_enabled", False),
    "last_update": None,
    "market_data": {},
    "predictions": {},
    "signals": {},
    "recommended_leverage": {},
    "position_sizing": {},
    "positions": {},
    "portfolio": {
        "balance": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "equity": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "used_margin": 0.0,
        "available_margin": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "unrealized_pnl": 0.0,
        "positions": [],
    },
    "metrics": {
        "average_funding_rate": 0.0,
        "high_risk_symbols": [],
        "funding_alerts": [],
    },
    "config": {},
    "indicator_selection": indicator_snapshot.get("futures", []),
}

futures_data_lock = threading.Lock()

futures_dashboard_state["config"] = dict(
    futures_ml_system.futures_module.futures_config
)

_default_futures_symbol = TRADING_CONFIG.get("futures_selected_symbol")
if _default_futures_symbol and _default_futures_symbol not in FUTURES_SYMBOLS:
    _default_futures_symbol = FUTURES_SYMBOLS[0] if FUTURES_SYMBOLS else None
    TRADING_CONFIG["futures_selected_symbol"] = _default_futures_symbol

futures_manual_service = FuturesManualService(
    trading_config=TRADING_CONFIG,
    initial_selected_symbol=_default_futures_symbol,
    futures_symbols_provider=lambda: list(FUTURES_SYMBOLS),
    top_symbols_provider=lambda: list(TOP_SYMBOLS),
    dashboard_data_provider=lambda: globals().get("dashboard_data"),
    safe_float=_safe_float,
)
futures_manual_lock = futures_manual_service.lock
futures_manual_settings = futures_manual_service.settings


def _ensure_futures_manual_defaults(update_dashboard=False):
    return futures_manual_service.ensure_defaults(update_dashboard=update_dashboard)


_ensure_futures_manual_defaults(update_dashboard=False)


def _get_futures_manual_settings():
    return futures_manual_service.ensure_defaults(update_dashboard=False)


def _set_futures_manual_settings(settings):
    futures_manual_service.apply_restored_settings(settings)


def _handle_manual_futures_trading(symbol, market_data, prediction, sizing):
    try:
        futures_manual_service.handle_manual_trading(
            symbol,
            market_data,
            prediction,
            sizing,
            ultimate_trader,
        )
    except Exception as exc:
        print(f"❌ Manual futures trading error for {symbol}: {exc}")


def _ensure_logger_handlers_open(logger):
    try:
        handlers = list(getattr(logger, "handlers", []))
    except Exception:
        return
    for handler in handlers:
        stream = getattr(handler, "stream", None)
        if stream is not None and getattr(stream, "closed", False):
            try:
                logger.removeHandler(handler)
            except Exception:
                continue


def _disable_logger(logger):
    try:
        if logger is None:
            return
        logger.disabled = True
    except Exception:
        pass


persistence_runtime = build_persistence_runtime(
    market_cap_weights_provider=lambda: MARKET_CAP_WEIGHTS,
    futures_settings_getter=_get_futures_manual_settings,
    futures_settings_setter=_set_futures_manual_settings,
    ultimate_trader=ultimate_trader,
    optimized_trader=optimized_trader,
    futures_manual_lock=futures_manual_lock,
    futures_manual_settings=futures_manual_settings,
    coerce_bool=_coerce_bool,
    log_event=log_component_event,
    log_debug=log_component_debug,
    logger_factory=setup_application_logging,
    bot_profile=BOT_PROFILE,
)
persistence_manager = persistence_runtime.persistence_manager
persistence_scheduler = persistence_runtime.persistence_scheduler
bot_logger = persistence_runtime.bot_logger
binance_credentials_store = persistence_runtime.binance_credentials_store
binance_credential_service = persistence_runtime.binance_credential_service
binance_log_manager = persistence_runtime.binance_log_manager
live_portfolio_scheduler = None
_initialize_binance_market_helper()

if _TALIB_IMPORT_ERROR is not None:
    bot_logger.warning(
        "TA-Lib import failed; using fallback indicator implementations (error: %s)",
        _TALIB_IMPORT_ERROR,
    )
elif MISSING_TALIB_FUNCTIONS:
    bot_logger.warning(
        "TA-Lib missing functions %s; using fallback implementations",
        ", ".join(sorted(set(MISSING_TALIB_FUNCTIONS))),
    )
backtest_manager = BacktestManager(
    symbol_normalizer=_normalize_symbol,
    active_universe_provider=lambda: get_active_trading_universe(),
    top_symbols_provider=lambda: list(TOP_SYMBOLS),
    resolve_profile_path=resolve_profile_path,
    ultimate_system_factory=UltimateMLTrainingSystem,
    optimized_system_factory=OptimizedMLTrainingSystem,
    ultimate_live_system=ultimate_ml_system,
    optimized_live_system=optimized_ml_system,
)

binance_credential_service.initialize_all()
binance_credential_snapshot = persistence_runtime.snapshot_credentials(
    include_connection=True,
    include_logs=True,
)

health_data_lock = threading.Lock()
health_report_service = None

# Ultimate dashboard data
dashboard_data = {
    "market_data": {},
    "ml_predictions": {},
    "ai_signals": {},
    "portfolio": {},
    "optimized_ml_predictions": {},
    "optimized_ai_signals": {},
    "optimized_portfolio": {},
    "trending_pairs": [],
    "ensemble_predictions": {},
    "optimized_ensemble_predictions": {},
    "performance": {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": 0,
        "win_rate": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
    },
    "system_status": {
        "trading_enabled": False,
        "last_trade": None,
        "models_loaded": False,
        "ml_system_available": True,
        "paper_trading": True,
        "total_symbols": len(get_all_known_symbols()),
        "active_symbols": len(get_active_trading_universe()),
        "performance_tracking": True,
        "models_training": False,
        "total_indicators": len(BEST_INDICATORS),
        "indicators_used": 0,
        "bot_efficiency": 0,
        "learning_cycles": 0,
        "ensemble_active": True,
        "market_regime": "NEUTRAL",
        "risk_adjustment": 1.0,
        "professional_mode": True,
        "parallel_processing": True,
        "advanced_stop_loss": True,
        "adaptive_risk_management": True,
        "periodic_rebuilding": True,
        "continuous_training": True,
        "market_stress": 0.0,
        "risk_profile": "moderate",
        "crt_module_active": "CRT"
        in indicator_snapshot.get("ultimate", []),  # NEW: CRT module status
        "ict_module_active": "ICT" in indicator_snapshot.get("ultimate", []),
        "smc_module_active": "SMC" in indicator_snapshot.get("ultimate", []),
        "comprehensive_history": True,  # NEW: Comprehensive history status
        "persistence_enabled": True,  # NEW: Persistence status
        "futures_enabled": TRADING_CONFIG.get("futures_enabled", False),
        "real_trading_ready": False,
        "futures_trading_ready": False,
        "futures_manual_auto_trade": TRADING_CONFIG.get(
            "futures_manual_auto_trade", False
        ),
    },
    "optimized_system_status": {
        "trading_enabled": False,
        "models_loaded": False,
        "models_training": False,
        "total_indicators": len(BEST_INDICATORS),
        "indicators_used": 0,
        "bot_efficiency": 0,
        "learning_cycles": 0,
        "market_regime": "NEUTRAL",
        "risk_adjustment": 1.0,
        "market_stress": 0.0,
        "risk_profile": "moderate",
        "ensemble_active": False,
        "crt_module_active": "CRT" in indicator_snapshot.get("optimized", []),
        "ict_module_active": "ICT" in indicator_snapshot.get("optimized", []),
        "smc_module_active": "SMC" in indicator_snapshot.get("optimized", []),
        "paper_trading": True,
        "real_trading_ready": False,
    },
    "last_update": time.time(),
    "optimized_last_update": time.time(),
    "crt_signals": {},  # NEW: CRT signals data
    "optimized_crt_signals": {},
    "qfm_signals": {},
    "optimized_qfm_signals": {},
    "trade_statistics": {},  # NEW: Trade statistics
    "optimized_trade_statistics": {},
    "binance_credentials": binance_credential_snapshot,
    "binance_logs": binance_credential_snapshot.get("logs", []),
    "optimized_performance": {},
    "safety_status": {},
    "optimized_safety_status": {},
    "real_trading_status": {},
    "optimized_real_trading_status": {},
    "ml_telemetry": {
        "ultimate": {"summary": {}, "models": [], "history": []},
        "optimized": {"summary": {}, "models": [], "history": []},
    },
    "journal_events": [],
    "backtest_results": {},
    "backtest_jobs": {"active": None, "history": []},
    "health_report": {
        "status": "unknown",
        "last_refresh": None,
        "generated_at": None,
        "thresholds": {
            "min_total_return_pct": HEALTH_CHECK_CONFIG["min_total_return_pct"],
            "min_sharpe_ratio": HEALTH_CHECK_CONFIG["min_sharpe_ratio"],
            "max_drawdown_pct": HEALTH_CHECK_CONFIG["max_drawdown_pct"],
        },
        "aggregate": {},
        "symbols": [],
        "breaches": [],
        "top_by_return": [],
        "top_by_sharpe": [],
        "errors": [],
        "source": HEALTH_CHECK_CONFIG["report_path"],
    },
    "futures_dashboard": futures_dashboard_state,
    "futures_manual": futures_manual_settings,
    "indicator_selections": indicator_snapshot,
}

attach_dashboard_data(dashboard_data)

persistence_runtime.attach_dashboard_data(lambda: dashboard_data)

dashboard_data["system_status"][
    "futures_manual_auto_trade"
] = futures_manual_settings.get("auto_trade_enabled", False)
dashboard_data["system_status"]["futures_trading_ready"] = bool(
    getattr(ultimate_trader, "futures_trading_enabled", False)
)

# Auto-enable futures trading if environment variables are set
if TRADING_CONFIG.get("futures_enabled", False):
    final_hammer = os.getenv("FINAL_HAMMER", "false").lower() in ("1", "true", "yes")
    if final_hammer:
        try:
            print(
                "🔄 Auto-enabling futures trading based on environment configuration..."
            )
            ultimate_trader.futures_trading_enabled = True
            optimized_trader.futures_trading_enabled = True
            dashboard_data["system_status"]["futures_trading_enabled"] = True
            dashboard_data["system_status"]["futures_trading_ready"] = True
            dashboard_data["optimized_system_status"]["futures_trading_enabled"] = True
            dashboard_data["optimized_system_status"]["futures_trading_ready"] = True
            print("✅ Futures trading auto-enabled successfully")
        except Exception as exc:
            print(f"⚠️ Failed to auto-enable futures trading: {exc}")
    else:
        print(
            "⚠️ Futures trading not auto-enabled: FINAL_HAMMER environment variable not set"
        )

# Add circuit breaker status to system status
if hasattr(ultimate_trader, "get_circuit_breaker_status"):
    dashboard_data["system_status"][
        "circuit_breaker"
    ] = ultimate_trader.get_circuit_breaker_status()
else:
    dashboard_data["system_status"]["circuit_breaker"] = {
        "state": "UNKNOWN",
        "is_open": False,
    }

health_report_service = HealthReportService(
    config=HEALTH_CHECK_CONFIG,
    project_root=PROJECT_ROOT,
    dashboard_data=dashboard_data,
    summary_evaluator=evaluate_health_payload,
    lock=health_data_lock,
)

service_runtime = build_service_runtime(
    dashboard_data=dashboard_data,
    indicator_selection_manager=indicator_selection_manager,
    trading_config=TRADING_CONFIG,
    ultimate_trader=ultimate_trader,
    optimized_trader=optimized_trader,
    ultimate_ml_system=ultimate_ml_system,
    optimized_ml_system=optimized_ml_system,
    futures_ml_system=futures_ml_system,
    parallel_engine=parallel_engine,
    futures_manual_settings=futures_manual_settings,
    binance_credential_service=binance_credential_service,
    get_active_trading_universe=get_active_trading_universe,
    get_real_market_data=get_real_market_data,
    get_trending_pairs=get_trending_pairs,
    refresh_symbol_counters=refresh_symbol_counters,
    handle_manual_futures_trading=_handle_manual_futures_trading,
    futures_dashboard_state=futures_dashboard_state,
    futures_symbols=FUTURES_SYMBOLS,
    futures_data_lock=futures_data_lock,
    socketio=socketio,
    safe_float=_safe_float,
    bot_logger=bot_logger,
)

historical_data = service_runtime.historical_data
refresh_indicator_dashboard_state = service_runtime.refresh_indicator_dashboard_state
market_data_service = service_runtime.market_data_service
futures_market_data_service = service_runtime.futures_market_data_service
realtime_update_service = service_runtime.realtime_update_service
model_training_worker = service_runtime.model_training_worker
self_improvement_worker = service_runtime.self_improvement_worker

refresh_indicator_dashboard_state()


# ==================== GRACEFUL SHUTDOWN HANDLING ====================
def graceful_shutdown():
    """Save state on application shutdown"""
    print("\n🛑 Shutdown detected - saving bot state...")
    _ensure_logger_handlers_open(bot_logger)
    _disable_logger(bot_logger)
    try:
        background_task_manager.stop_background_tasks()
    except Exception as exc:
        print(f"⚠️ Failed to stop background tasks cleanly: {exc}")
    try:
        background_task_manager.stop_live_portfolio_updates()
    except Exception as exc:
        print(f"⚠️ Failed to stop live portfolio scheduler cleanly: {exc}")
    _ensure_logger_handlers_open(bot_logger)
    persistence_scheduler.manual_save(
        ultimate_trader,
        ultimate_ml_system,
        TRADING_CONFIG,
        TOP_SYMBOLS,
        historical_data,
    )
    print("✅ Bot state saved. Goodbye!")


# Register shutdown handler
atexit.register(graceful_shutdown)

# Global shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle termination signals"""
    global shutdown_requested
    print(f"\n📡 Received signal {signum} - initiating graceful shutdown...")
    shutdown_requested = True


# Signal handlers will be registered after initialization to prevent premature shutdown
# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)


# ==================== AUTHENTICATION TEMPLATES ====================
# ==================== FLASK ROUTES ====================
# ==================== USER PORTFOLIO MANAGEMENT ====================
def record_user_trade(
    user_id,
    symbol,
    side,
    quantity,
    price,
    trade_type="manual_spot",
    signal_source=None,
    confidence_score=None,
):
    """Record a user trade and update portfolio"""
    try:
        # Create trade record
        trade = UserTrade(
            user_id=user_id,
            symbol=symbol,
            trade_type=trade_type,
            side=side,
            quantity=quantity,
            entry_price=price,
            status="open" if side == "BUY" else "closed",
            signal_source=signal_source,
            confidence_score=confidence_score,
        )
        db.session.add(trade)

        # Update or create user portfolio
        portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        if not portfolio:
            portfolio = UserPortfolio(user_id=user_id)
            db.session.add(portfolio)

        # Update portfolio based on trade
        if side == "BUY":
            # Calculate cost
            cost = quantity * price
            if portfolio.available_balance >= cost:
                portfolio.available_balance -= cost
                # Update open positions
                positions = portfolio.open_positions or {}
                if symbol not in positions:
                    positions[symbol] = {
                        "quantity": 0,
                        "entry_price": 0,
                        "current_pnl": 0,
                    }
                # Simple average price calculation
                current_qty = positions[symbol]["quantity"]
                current_avg = positions[symbol]["entry_price"]
                new_qty = current_qty + quantity
                new_avg = (
                    ((current_qty * current_avg) + (quantity * price)) / new_qty
                    if new_qty > 0
                    else 0
                )
                positions[symbol]["quantity"] = new_qty
                positions[symbol]["entry_price"] = new_avg
                portfolio.open_positions = positions
            else:
                db.session.rollback()
                return False
        elif side == "SELL":
            # Handle sell logic - simplified for now
            positions = portfolio.open_positions or {}
            if symbol in positions and positions[symbol]["quantity"] >= quantity:
                # Calculate P&L
                entry_price = positions[symbol]["entry_price"]
                pnl = (price - entry_price) * quantity
                portfolio.total_profit_loss += pnl
                portfolio.available_balance += quantity * price
                # Update position
                positions[symbol]["quantity"] -= quantity
                if positions[symbol]["quantity"] <= 0:
                    del positions[symbol]
                portfolio.open_positions = positions
                # Update trade with exit info
                trade.exit_price = price
                trade.pnl = pnl
                trade.status = "closed"
            else:
                db.session.rollback()
                return False

        # Update totals
        portfolio.total_balance = portfolio.available_balance + sum(
            pos["quantity"] * pos["entry_price"] for pos in positions.values()
        )
        portfolio.updated_at = datetime.utcnow()

        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        print(f"Error recording user trade: {e}")
        return False


def update_portfolio_daily_pnl(user_id=None):
    """Update UserPortfolio daily_pnl from trader daily_pnl accumulation"""
    try:
        # Get all users or specific user
        if user_id:
            users = User.query.filter_by(id=user_id).all()
        else:
            users = User.query.all()

        updated_users = []

        for user in users:
            try:
                # Get user's current portfolio daily_pnl
                user_portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
                if not user_portfolio:
                    continue

                # Get trader daily_pnl (sum from both ultimate and optimized traders)
                ultimate_daily_pnl = getattr(ultimate_trader, "daily_pnl", 0)
                optimized_daily_pnl = getattr(optimized_trader, "daily_pnl", 0)
                total_daily_pnl = ultimate_daily_pnl + optimized_daily_pnl

                # Update portfolio daily_pnl
                user_portfolio.daily_pnl = total_daily_pnl
                user_portfolio.updated_at = datetime.utcnow()

                updated_users.append(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "daily_pnl": total_daily_pnl,
                        "ultimate_daily_pnl": ultimate_daily_pnl,
                        "optimized_daily_pnl": optimized_daily_pnl,
                    }
                )

            except Exception as e:
                print(f"Error updating daily P&L for user {user.id}: {e}")
                continue

        db.session.commit()

        return {
            "success": True,
            "updated_users": len(updated_users),
            "user_details": updated_users,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error updating portfolio daily P&L: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def update_live_portfolio_pnl(user_id=None):
    """Update live portfolio P&L calculations for all users or specific user"""
    try:
        # Get market data for current prices
        market_data = dashboard_data.get("market_data", {})

        # Query users to update
        if user_id:
            users = User.query.filter_by(id=user_id).all()
        else:
            users = User.query.all()

        updated_users = []

        for user in users:
            try:
                # Get user's portfolio positions
                user_portfolios = UserPortfolio.query.filter_by(user_id=user.id).all()

                total_portfolio_value = 0
                total_pnl = 0
                total_cost_basis = 0

                for position in user_portfolios:
                    symbol = position.symbol
                    quantity = position.quantity or 0

                    if quantity == 0:
                        continue

                    # Get current price from market data or use last known price
                    current_price = None
                    if symbol in market_data:
                        current_price = market_data[symbol].get("price") or market_data[
                            symbol
                        ].get("close")

                    if current_price is None or current_price <= 0:
                        current_price = position.current_price or position.avg_price

                    if current_price and current_price > 0:
                        # Update current price
                        position.current_price = current_price

                        # Calculate P&L for this position
                        cost_basis = quantity * (position.avg_price or 0)
                        current_value = quantity * current_price
                        position_pnl = current_value - cost_basis
                        position_pnl_percent = (
                            (position_pnl / cost_basis * 100) if cost_basis > 0 else 0
                        )

                        # Update position P&L
                        position.pnl = position_pnl
                        position.pnl_percent = position_pnl_percent

                        total_portfolio_value += current_value
                        total_pnl += position_pnl
                        total_cost_basis += cost_basis

                # Update user's total portfolio metrics
                if user_portfolios:
                    # Calculate overall portfolio P&L percentage
                    total_pnl_percent = (
                        (total_pnl / total_cost_basis * 100)
                        if total_cost_basis > 0
                        else 0
                    )

                    # Update portfolio totals
                    for portfolio in user_portfolios:
                        if hasattr(portfolio, "total_balance"):
                            portfolio.total_balance = total_portfolio_value
                        portfolio.updated_at = datetime.utcnow()

                    updated_users.append(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "total_value": total_portfolio_value,
                            "total_pnl": total_pnl,
                            "total_pnl_percent": total_pnl_percent,
                            "positions_count": len(
                                [
                                    p
                                    for p in user_portfolios
                                    if p.quantity and p.quantity > 0
                                ]
                            ),
                        }
                    )

            except Exception as e:
                print(f"Error updating portfolio for user {user.id}: {e}")
                continue

        # Update daily P&L for all users
        update_portfolio_daily_pnl()

        db.session.commit()

        return {
            "success": True,
            "updated_users": len(updated_users),
            "user_details": updated_users,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error updating live portfolio P&L: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


background_runtime = build_background_runtime(
    update_callback=update_live_portfolio_pnl,
    bot_logger=bot_logger,
    market_data_service=market_data_service,
    futures_market_data_service=futures_market_data_service,
    realtime_update_service=realtime_update_service,
    persistence_scheduler=persistence_scheduler,
    self_improvement_worker=self_improvement_worker,
    model_training_worker=model_training_worker,
    trading_config=TRADING_CONFIG,
    flask_app=app,
    update_interval_seconds=30,
    tick_interval_seconds=10,
)
live_portfolio_scheduler = background_runtime.live_portfolio_scheduler
background_task_manager = background_runtime.background_task_manager


# ==================== SOCKETIO ENDPOINTS FOR REAL-TIME DASHBOARD ====================
@socketio.on("connect")
def handle_connect():
    """Handle client connection for real-time updates"""
    print(f"Client connected: {request.sid}")
    emit(
        "connected",
        {"status": "success", "message": "Connected to real-time dashboard"},
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on("subscribe_portfolio")
def handle_portfolio_subscription():
    """Subscribe to real-time portfolio updates"""
    emit(
        "portfolio_update",
        {
            "portfolio": dashboard_data.get("portfolio", {}),
            "user_portfolio": get_user_portfolio_data(
                current_user.id if current_user else None
            ),
            "timestamp": time.time(),
        },
    )


@socketio.on("subscribe_market_data")
def handle_market_data_subscription():
    """Subscribe to real-time market data updates"""
    active_symbols = get_active_trading_universe()
    market_data = {}
    for symbol in active_symbols:
        if symbol in dashboard_data.get("market_data", {}):
            market_data[symbol] = dashboard_data["market_data"][symbol]

    emit("market_data_update", {"market_data": market_data, "timestamp": time.time()})


@socketio.on("subscribe_pnl")
def handle_pnl_subscription():
    """Subscribe to real-time P&L updates"""
    portfolio = dashboard_data.get("portfolio", {})
    pnl_data = {
        "total_pnl": portfolio.get("total_pnl", 0),
        "daily_pnl": portfolio.get("daily_pnl", 0),
        "open_positions_pnl": sum(
            pos.get("pnl", 0) for pos in portfolio.get("positions", [])
        ),
        "timestamp": time.time(),
    }
    emit("pnl_update", pnl_data)


@socketio.on("subscribe_performance")
def handle_performance_subscription():
    """Subscribe to real-time performance metrics"""
    performance = dashboard_data.get("performance", {})
    emit("performance_update", {"performance": performance, "timestamp": time.time()})


def get_user_portfolio_data(user_id):
    """Get user-specific portfolio data for real-time updates"""
    if not user_id:
        return {}

    try:
        # Get user portfolio from database
        user_portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        if not user_portfolio:
            return {}

        # Get recent trades
        recent_trades = (
            UserTrade.query.filter_by(user_id=user_id)
            .order_by(UserTrade.timestamp.desc())
            .limit(10)
            .all()
        )
        trades_data = []
        for trade in recent_trades:
            trades_data.append(
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "pnl": trade.pnl,
                    "status": trade.status,
                    "timestamp": trade.timestamp.isoformat()
                    if trade.timestamp
                    else None,
                }
            )

        return {
            "total_balance": user_portfolio.total_balance,
            "available_balance": user_portfolio.available_balance,
            "total_pnl": user_portfolio.total_profit_loss,
            "daily_pnl": user_portfolio.daily_pnl,
            "open_positions": user_portfolio.open_positions or {},
            "recent_trades": trades_data,
            "last_updated": user_portfolio.updated_at.isoformat()
            if user_portfolio.updated_at
            else None,
        }
    except Exception as e:
        print(f"Error getting user portfolio data: {e}")
        return {}


# ==================== POLLING FALLBACK ENDPOINTS ====================
# REST API endpoints for browsers that don't support WebSocket


# ==================== INITIALIZE ULTIMATE SYSTEM WITH PERSISTENCE ====================
def initialize_ultimate_system():
    """Initialize the complete ultimate trading system with persistence."""
    context = None
    flask_app = globals().get("app")
    if flask_app is not None:
        context = flask_app.extensions.get("ai_bot_context")
    if context is None:
        context = _build_ai_bot_context()
    initialize_runtime_from_context(context)


# ==================== DASHBOARD TEMPLATE ====================
# Template moved to app/templates/dashboard.html


def _build_ai_bot_context():
    indicator_profiles = indicator_selection_manager.profiles()
    return build_ai_bot_context_payload(
        dashboard_data=dashboard_data,
        health_data_lock=health_data_lock,
        health_report_service=health_report_service,
        indicator_signal_options=INDICATOR_SIGNAL_OPTIONS,
        indicator_profiles=indicator_profiles,
        get_indicator_selection=get_indicator_selection,
        get_all_indicator_selections=get_all_indicator_selections,
        set_indicator_selection=set_indicator_selection,
        refresh_indicator_dashboard_state=refresh_indicator_dashboard_state,
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=optimized_ml_system,
        futures_ml_system=futures_ml_system,
        parallel_engine=parallel_engine,
        strategy_manager=strategy_manager,
        backtest_manager=backtest_manager,
        get_active_trading_universe=get_active_trading_universe,
        get_real_market_data=get_real_market_data,
        get_trending_pairs=get_trending_pairs,
        get_user_trader=get_user_trader,
        get_user_portfolio_data=get_user_portfolio_data,
        update_live_portfolio_pnl=update_live_portfolio_pnl,
        trade_history=trade_history,
        apply_binance_credentials=binance_credential_service.apply_credentials,
        get_binance_credential_status=binance_credential_service.get_status,
        binance_credentials_store=binance_credentials_store,
        binance_credential_service=binance_credential_service,
        binance_log_manager=binance_log_manager,
        futures_dashboard_state=futures_dashboard_state,
        futures_manual_service=futures_manual_service,
        futures_manual_settings=futures_manual_settings,
        futures_manual_lock=futures_manual_lock,
        futures_data_lock=futures_data_lock,
        futures_symbols=FUTURES_SYMBOLS,
        ensure_futures_manual_defaults=_ensure_futures_manual_defaults,
        trading_config=TRADING_CONFIG,
        coerce_bool=_coerce_bool,
        qfm_engine=getattr(ultimate_ml_system, "qfm_engine", None),
        persistence_manager=persistence_manager,
        persistence_scheduler=persistence_scheduler,
        persistence_runtime=persistence_runtime,
        background_runtime=background_runtime,
        background_task_manager=background_task_manager,
        service_runtime=service_runtime,
        realtime_update_service=realtime_update_service,
        market_data_service=market_data_service,
        futures_market_data_service=futures_market_data_service,
        live_portfolio_scheduler=live_portfolio_scheduler,
        historical_data=historical_data,
        top_symbols=TOP_SYMBOLS,
        disabled_symbols=DISABLED_SYMBOLS,
        get_all_known_symbols=get_all_known_symbols,
        get_disabled_symbols=get_disabled_symbols,
        refresh_symbol_counters=refresh_symbol_counters,
        clear_symbol_from_dashboard=clear_symbol_from_dashboard,
        is_symbol_disabled=is_symbol_disabled,
        disable_symbol=disable_symbol,
        enable_symbol=enable_symbol,
        save_symbol_state=save_symbol_state,
        normalize_symbol=_normalize_symbol,
        signal_handler=signal_handler,
        version_label=AI_BOT_VERSION,
    )


def register_ai_bot_context(flask_app=None, force=False):
    """Attach the AI bot runtime context to the provided Flask app."""
    flask_app = flask_app or app
    if flask_app is None:
        raise RuntimeError(
            "Flask application instance is required to register ai_bot_context"
        )

    new_context = _build_ai_bot_context()
    existing = flask_app.extensions.get("ai_bot_context")
    if existing and not force:
        existing.update(new_context)
        context = existing
    else:
        flask_app.extensions["ai_bot_context"] = new_context
        context = new_context

    scheduler = context.get("live_portfolio_scheduler")
    if scheduler is not None:
        try:
            scheduler.app = flask_app
        except Exception:
            pass
    background_runtime = context.get("background_runtime")
    if background_runtime is not None:
        attach = getattr(background_runtime, "attach_app", None)
        if callable(attach):
            try:
                attach(flask_app)
            except Exception:
                pass
    return context


# Initialize AI bot context for Flask routes (needed for WSGI deployment)
print("🔧 Initializing AI bot context for Flask routes...")
try:
    print("  📋 Registering AI bot context...")
    ai_bot_context = register_ai_bot_context(app, force=True)
    print("  ⚙️  Initializing ultimate system...")
    initialize_runtime_from_context(ai_bot_context)
    print("✅ AI bot context initialized successfully for Flask routes")
except Exception as e:
    import traceback

    print(f"❌ Failed to initialize AI bot context: {e}")
    print("Full traceback:")
    traceback.print_exc()
    print("⚠️  Continuing without AI bot context - some features may not work")
    # Continue anyway - don't crash the app startup


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    try:
        # Only initialize context if not already done (for direct execution)
        if not app.extensions.get("ai_bot_context"):
            ai_bot_context = register_ai_bot_context(app, force=True)
            # Initialize the ultimate system
            initialize_runtime_from_context(ai_bot_context)

        # Start the Flask web server
        host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
        port = int(os.environ.get("FLASK_RUN_PORT", 5000))
        print(f"🌐 Starting Flask web server on {host}:{port}...")
        from werkzeug.serving import make_server

        # Create server
        server = make_server(host, port, app, threaded=True)

        # Start server in a separate thread
        import threading

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()  # Remove daemon=True to keep server alive

        print(f"✅ Flask server started successfully on http://{host}:{port}")
        print(f"🎯 Dashboard available at: http://{host}:{port}")

        # Start all background tasks including self-improvement worker
        background_task_manager.start_background_tasks(
            start_ultimate_training=True,
            start_optimized_training=True,
            persistence_inputs={
                "trader": ultimate_trader,
                "ml_system": ultimate_ml_system,
                "config": TRADING_CONFIG,
                "symbols": list(get_active_trading_universe() or []),
                "historical_data": historical_data,
            },
        )

        # Start live portfolio scheduler
        background_task_manager.start_live_portfolio_updates()

        # Keep the main thread alive and handle server shutdown
        try:
            while server_thread.is_alive() and not shutdown_requested:
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Received keyboard interrupt - shutting down gracefully...")
            shutdown_requested = True

        # Shutdown server if it's still running
        if server_thread.is_alive():
            print("🛑 Shutting down Flask server...")
            server.shutdown()
            server_thread.join(timeout=5.0)

        graceful_shutdown()

    except Exception as e:
        print(f"\n❌ Fatal error during startup: {e}")
        graceful_shutdown()
        sys.exit(1)
