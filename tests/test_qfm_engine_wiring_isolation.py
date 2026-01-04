from __future__ import annotations

from types import SimpleNamespace

from app.services.ml import MLServiceBundle
from app.services.trading import TradingServiceBundle, attach_trading_ml_dependencies


def test_attach_trading_ml_dependencies_does_not_override_existing_qfm_engine():
    existing_ultimate_qfm = object()
    existing_optimized_qfm = object()

    trading_bundle = TradingServiceBundle(
        trade_history=None,
        ultimate_trader=SimpleNamespace(qfm_engine=existing_ultimate_qfm),
        optimized_trader=SimpleNamespace(qfm_engine=existing_optimized_qfm),
        parallel_engine=None,
    )

    ml_bundle = MLServiceBundle(
        ultimate_ml_system=SimpleNamespace(qfm_engine=object()),
        optimized_ml_system=SimpleNamespace(qfm_engine=object()),
        futures_ml_system=SimpleNamespace(),
    )

    attach_trading_ml_dependencies(trading_bundle, ml_bundle)

    assert trading_bundle.ultimate_trader.qfm_engine is existing_ultimate_qfm
    assert trading_bundle.optimized_trader.qfm_engine is existing_optimized_qfm


def test_attach_trading_ml_dependencies_initializes_qfm_engine_when_missing():
    trading_bundle = TradingServiceBundle(
        trade_history=None,
        ultimate_trader=SimpleNamespace(qfm_engine=None),
        optimized_trader=SimpleNamespace(qfm_engine=None),
        parallel_engine=None,
    )

    ml_ultimate_engine = object()
    ml_optimized_engine = object()
    ml_bundle = MLServiceBundle(
        ultimate_ml_system=SimpleNamespace(qfm_engine=ml_ultimate_engine),
        optimized_ml_system=SimpleNamespace(qfm_engine=ml_optimized_engine),
        futures_ml_system=SimpleNamespace(),
    )

    attach_trading_ml_dependencies(trading_bundle, ml_bundle)

    assert trading_bundle.ultimate_trader.qfm_engine is not None
    assert trading_bundle.optimized_trader.qfm_engine is not None

    # Must not alias the ML system engine objects.
    assert trading_bundle.ultimate_trader.qfm_engine is not ml_ultimate_engine
    assert trading_bundle.optimized_trader.qfm_engine is not ml_optimized_engine
