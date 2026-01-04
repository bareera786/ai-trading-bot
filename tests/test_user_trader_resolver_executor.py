import pytest

pytest.importorskip("flask_mail")

from app.services.trading import TradingServiceBundle, create_user_trader_resolver


def test_get_user_trader_returns_executor_for_user_id():
    bundle = TradingServiceBundle(
        trade_history=None,
        ultimate_trader=object(),
        optimized_trader=object(),
        parallel_engine=None,
    )
    resolver = create_user_trader_resolver(bundle)

    user_trader = resolver(1, "ultimate")
    assert hasattr(user_trader, "execute_manual_trade")
    assert hasattr(user_trader, "execute_manual_futures_trade")


def test_get_user_trader_preserves_legacy_behavior_without_user_id():
    ultimate = object()
    optimized = object()
    bundle = TradingServiceBundle(
        trade_history=None,
        ultimate_trader=ultimate,
        optimized_trader=optimized,
        parallel_engine=None,
    )
    resolver = create_user_trader_resolver(bundle)

    assert resolver(None, "ultimate") is ultimate
    assert resolver(None, "optimized") is optimized
