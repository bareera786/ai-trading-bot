"""Tests to ensure persistence logging is resilient during shutdown.

These simulate logger handlers having closed streams and assert that
persistence functions do not raise exceptions when handlers are closed.
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

from app.services import persistence
from app.config import Config


class _FakeStream:
    def __init__(self, closed: bool = True):
        self.closed = closed


class _FakeHandler:
    def __init__(self, stream):
        self.stream = stream


def test_ensure_persistence_dirs_handles_closed_handlers(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_PROFILE", "default")
    monkeypatch.setenv("BOT_DATA_DIR", str(tmp_path))

    # Attach a handler with a closed stream to simulate shutdown
    orig_handlers = persistence.logger.handlers[:]
    try:
        persistence.logger.handlers = [_FakeHandler(_FakeStream(closed=True))]

        out = persistence.ensure_persistence_dirs()
        assert isinstance(out, Path)
        assert out.exists()
    finally:
        persistence.logger.handlers = orig_handlers


def test_save_complete_state_does_not_raise_with_closed_handlers(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_PROFILE", "default")
    monkeypatch.setenv("BOT_DATA_DIR", str(tmp_path))

    # Minimal fake trader and ml_system to satisfy save_complete_state
    class _FakeTradeHistory:
        def get_trade_history(self):
            return []

    class _FakeTrader:
        def __init__(self):
            self.trade_history = _FakeTradeHistory()
            self.trading_enabled = False
            self.paper_trading = False
            self.positions = {}
            self.balance = {}
            self.daily_pnl = 0
            self.max_drawdown = 0
            self.peak_balance = 0
            self.bot_efficiency = 0
            self.risk_manager = types.SimpleNamespace(
                current_risk_profile=None,
                risk_adjustment_history=[],
                volatility_regime=None,
                market_stress_indicator=None,
            )
            self.ensemble_system = types.SimpleNamespace(
                market_regime=None, correlation_matrix=None, last_rebuild_time=None
            )

    class _FakeML:
        def __init__(self):
            self.models = {}
            self.training_progress = {}
            self.training_logs = []
            self.crt_generator = types.SimpleNamespace(signals_history=[])

    orig_handlers = persistence.logger.handlers[:]
    try:
        persistence.logger.handlers = [_FakeHandler(_FakeStream(closed=True))]

        p = persistence.ProfessionalPersistence(persistence_dir=str(tmp_path))
        ok = p.save_complete_state(_FakeTrader(), _FakeML(), {}, [], {})
        assert ok in (True, False)
    finally:
        persistence.logger.handlers = orig_handlers
