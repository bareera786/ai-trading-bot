"""Tests for trading strategy modules."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from app.strategies.base import (
    BaseStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    ScalpingStrategy,
    BreakoutStrategy,
    ArbitrageStrategy,
    MLBasedStrategy,
)
from app.strategies.qfm import QuantumFusionMomentumEngine


class TestBaseStrategy:
    """Test the base strategy class."""

    def test_initialization(self):
        """Test base strategy initialization."""
        strategy = BaseStrategy("Test Strategy", "A test strategy")

        assert strategy.name == "Test Strategy"
        assert strategy.description == "A test strategy"
        assert strategy.parameters == {}
        assert strategy.active is True
        assert strategy.qfm_engine is None
        assert "total_trades" in strategy.performance_metrics
        assert strategy.performance_metrics["total_trades"] == 0

    def test_initialization_with_parameters(self):
        """Test initialization with custom parameters."""
        params = {"param1": "value1", "param2": 42}
        strategy = BaseStrategy("Test", "Test", params)

        assert strategy.parameters == params
        assert strategy.default_parameters == params

    def test_set_qfm_engine(self):
        """Test setting QFM engine."""
        strategy = BaseStrategy("Test", "Test")
        qfm_engine = Mock()

        strategy.set_qfm_engine(qfm_engine)
        assert strategy.qfm_engine == qfm_engine

    def test_analyze_market_not_implemented(self):
        """Test that analyze_market raises NotImplementedError."""
        strategy = BaseStrategy("Test", "Test")

        with pytest.raises(NotImplementedError):
            strategy.analyze_market("BTCUSDT", [])

    def test_enhance_with_qfm_no_engine(self):
        """Test QFM enhancement without QFM engine."""
        strategy = BaseStrategy("Test", "Test")
        base_signal = {"signal": "BUY", "confidence": 0.7}

        result = strategy.enhance_with_qfm("BTCUSDT", [], base_signal)
        assert result == base_signal

    def test_enhance_with_qfm_no_data(self):
        """Test QFM enhancement without market data."""
        strategy = BaseStrategy("Test", "Test")
        strategy.qfm_engine = Mock()
        base_signal = {"signal": "BUY", "confidence": 0.7}

        result = strategy.enhance_with_qfm("BTCUSDT", [], base_signal)
        assert result == base_signal

    @patch('app.strategies.base.time')
    def test_update_performance_winning_trade(self, mock_time):
        """Test updating performance with a winning trade."""
        mock_time.time.return_value = 1234567890
        strategy = BaseStrategy("Test", "Test")

        trade_result = {"pnl": 100.0, "symbol": "BTCUSDT"}
        strategy.update_performance(trade_result)

        assert strategy.performance_metrics["total_trades"] == 1
        assert strategy.performance_metrics["winning_trades"] == 1
        assert strategy.performance_metrics["losing_trades"] == 0
        assert strategy.performance_metrics["win_rate"] == 100.0
        assert strategy.performance_metrics["total_pnl"] == 100.0
        assert len(strategy.trade_history) == 1

    @patch('app.strategies.base.time')
    def test_update_performance_losing_trade(self, mock_time):
        """Test updating performance with a losing trade."""
        mock_time.time.return_value = 1234567890
        strategy = BaseStrategy("Test", "Test")

        trade_result = {"pnl": -50.0, "symbol": "BTCUSDT"}
        strategy.update_performance(trade_result)

        assert strategy.performance_metrics["total_trades"] == 1
        assert strategy.performance_metrics["winning_trades"] == 0
        assert strategy.performance_metrics["losing_trades"] == 1
        assert strategy.performance_metrics["win_rate"] == 0.0
        assert strategy.performance_metrics["total_pnl"] == -50.0

    def test_get_performance_summary(self):
        """Test getting performance summary."""
        strategy = BaseStrategy("Test", "Test")
        summary = strategy.get_performance_summary()

        assert summary == strategy.performance_metrics
        assert summary is not strategy.performance_metrics  # Should be a copy

    def test_should_enter_long_default(self):
        """Test default should_enter_long implementation."""
        strategy = BaseStrategy("Test", "Test")
        assert strategy.should_enter_long("BTCUSDT", []) is False

    def test_should_enter_short_default(self):
        """Test default should_enter_short implementation."""
        strategy = BaseStrategy("Test", "Test")
        assert strategy.should_enter_short("BTCUSDT", []) is False

    def test_should_exit_long_default(self):
        """Test default should_exit_long implementation."""
        strategy = BaseStrategy("Test", "Test")
        assert strategy.should_exit_long("BTCUSDT", []) is False

    def test_should_exit_short_default(self):
        """Test default should_exit_short implementation."""
        strategy = BaseStrategy("Test", "Test")
        assert strategy.should_exit_short("BTCUSDT", []) is False

    def test_calculate_position_size_default(self):
        """Test default calculate_position_size implementation."""
        strategy = BaseStrategy("Test", "Test")
        assert strategy.calculate_position_size("BTCUSDT", []) == 0.0


class TestTrendFollowingStrategy:
    """Test the trend following strategy."""

    def test_initialization(self):
        """Test trend following strategy initialization."""
        strategy = TrendFollowingStrategy()

        assert strategy.name == "Trend Following"
        assert "fast_ma_period" in strategy.parameters
        assert "slow_ma_period" in strategy.parameters
        assert strategy.parameters["fast_ma_period"] == 20
        assert strategy.parameters["slow_ma_period"] == 50

    def test_analyze_market_insufficient_data(self):
        """Test analysis with insufficient data."""
        strategy = TrendFollowingStrategy()
        result = strategy.analyze_market("BTCUSDT", [])

        assert result["signal"] == "HOLD"
        assert result["confidence"] == 0.0
        assert "Insufficient data" in result["reason"]

    def test_analyze_market_bullish_trend(self):
        """Test analysis with bullish trend conditions."""
        strategy = TrendFollowingStrategy()

        # Create bullish market data
        market_data = []
        base_price = 50000
        for i in range(100):
            price = base_price + (i * 10)  # Rising trend
            market_data.append({
                "close": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "volume": 1000 + i
            })

        result = strategy.analyze_market("BTCUSDT", market_data)

        assert result["signal"] in ["BUY", "STRONG_BUY", "HOLD"]
        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))

    def test_analyze_market_bearish_trend(self):
        """Test analysis with bearish trend conditions."""
        strategy = TrendFollowingStrategy()

        # Create bearish market data
        market_data = []
        base_price = 50000
        for i in range(100):
            price = base_price - (i * 10)  # Falling trend
            market_data.append({
                "close": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "volume": 1000 + i
            })

        result = strategy.analyze_market("BTCUSDT", market_data)

        assert result["signal"] in ["SELL", "STRONG_SELL", "HOLD"]
        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))


class TestMeanReversionStrategy:
    """Test the mean reversion strategy."""

    def test_initialization(self):
        """Test mean reversion strategy initialization."""
        strategy = MeanReversionStrategy()

        assert strategy.name == "Mean Reversion"
        assert "lookback_period" in strategy.parameters
        assert "entry_threshold" in strategy.parameters

    def test_analyze_market_insufficient_data(self):
        """Test analysis with insufficient data."""
        strategy = MeanReversionStrategy()
        result = strategy.analyze_market("BTCUSDT", [])

        assert result["signal"] == "HOLD"
        assert result["confidence"] == 0.0


class TestMomentumStrategy:
    """Test the momentum strategy."""

    def test_initialization(self):
        """Test momentum strategy initialization."""
        strategy = MomentumStrategy()

        assert strategy.name == "Momentum Trading"
        assert "momentum_period" in strategy.parameters
        assert "momentum_threshold" in strategy.parameters


class TestScalpingStrategy:
    """Test the scalping strategy."""

    def test_initialization(self):
        """Test scalping strategy initialization."""
        strategy = ScalpingStrategy()

        assert strategy.name == "Scalping"
        assert "max_holding_time" in strategy.parameters
        assert "target_pips" in strategy.parameters


class TestBreakoutStrategy:
    """Test the breakout strategy."""

    def test_initialization(self):
        """Test breakout strategy initialization."""
        strategy = BreakoutStrategy()

        assert strategy.name == "Breakout Trading"
        assert "lookback_period" in strategy.parameters
        assert "breakout_threshold" in strategy.parameters


class TestArbitrageStrategy:
    """Test the arbitrage strategy."""

    def test_initialization(self):
        """Test arbitrage strategy initialization."""
        strategy = ArbitrageStrategy()

        assert strategy.name == "Statistical Arbitrage"
        assert "correlation_window" in strategy.parameters


class TestMLBasedStrategy:
    """Test the ML-based strategy."""

    def test_initialization(self):
        """Test ML-based strategy initialization."""
        strategy = MLBasedStrategy()

        assert strategy.name == "ML-Based Strategy"
        assert "confidence_threshold" in strategy.parameters


class TestQuantumFusionMomentumEngine:
    """Test the QFM engine."""

    def test_initialization(self):
        """Test QFM engine initialization."""
        engine = QuantumFusionMomentumEngine()

        assert engine.feature_history == {}
        assert engine.market_regime_history == {}
        assert engine.max_history_size == 1000

    def test_compute_realtime_features_invalid_data(self):
        """Test computing features with invalid data."""
        engine = QuantumFusionMomentumEngine()

        # Test with None data
        result = engine.compute_realtime_features("BTCUSDT", None)
        assert result == {}

        # Test with non-dict data
        result = engine.compute_realtime_features("BTCUSDT", "invalid")
        assert result == {}

        # Test with empty dict
        result = engine.compute_realtime_features("BTCUSDT", {})
        assert result == {}

    def test_compute_realtime_features_valid_data(self):
        """Test computing features with valid market data."""
        engine = QuantumFusionMomentumEngine()

        market_data = {
            "close": 50000.0,
            "volume": 1000.0,
            "high": 51000.0,
            "low": 49000.0
        }

        result = engine.compute_realtime_features("BTCUSDT", market_data)

        # Should return a dict with QFM features
        assert isinstance(result, dict)
        assert len(result) > 0

        # Check for expected QFM features
        expected_features = [
            "velocity", "acceleration", "jerk",
            "volume_pressure", "trend_confidence",
            "regime_score", "entropy"
        ]

        for feature in expected_features:
            assert feature in result

    def test_feature_history_storage(self):
        """Test that features are stored in history."""
        engine = QuantumFusionMomentumEngine()

        market_data = {
            "close": 50000.0,
            "volume": 1000.0,
            "high": 51000.0,
            "low": 49000.0
        }

        # Compute features twice
        engine.compute_realtime_features("BTCUSDT", market_data)
        engine.compute_realtime_features("BTCUSDT", market_data)

        # Check history was created
        assert "BTCUSDT" in engine.feature_history
        assert len(engine.feature_history["BTCUSDT"]) == 2

        # Check cache was created
        assert "BTCUSDT" in engine.velocity_cache
        assert "BTCUSDT" in engine.acceleration_cache
        assert "BTCUSDT" in engine.jerk_cache

    def test_multiple_symbols_isolation(self):
        """Test that different symbols maintain separate histories."""
        engine = QuantumFusionMomentumEngine()

        btc_data = {"close": 50000.0, "volume": 1000.0, "high": 51000.0, "low": 49000.0}
        eth_data = {"close": 3000.0, "volume": 500.0, "high": 3100.0, "low": 2900.0}

        engine.compute_realtime_features("BTCUSDT", btc_data)
        engine.compute_realtime_features("ETHUSDT", eth_data)

        assert "BTCUSDT" in engine.feature_history
        assert "ETHUSDT" in engine.feature_history
        assert len(engine.feature_history["BTCUSDT"]) == 1
        assert len(engine.feature_history["ETHUSDT"]) == 1