from __future__ import annotations

from app.runtime.context import UserScopedProxy


class _DummyStrategyManager:
    def __init__(self):
        self.performance_analytics = {"analytics_cache": {}}
        self.qfm_engine = {"state": {}}


def test_user_scoped_proxy_isolates_mutable_strategy_manager_state():
    current_user_id = None

    def user_id_provider():
        return current_user_id

    base = _DummyStrategyManager()
    proxy = UserScopedProxy(base=base, factory=_DummyStrategyManager, user_id_provider=user_id_provider)

    current_user_id = 101
    proxy.performance_analytics["analytics_cache"]["foo"] = "user101"
    proxy.qfm_engine["state"]["bar"] = "user101"

    current_user_id = 202
    assert proxy.performance_analytics["analytics_cache"].get("foo") is None
    assert proxy.qfm_engine["state"].get("bar") is None

    proxy.performance_analytics["analytics_cache"]["foo"] = "user202"
    proxy.qfm_engine["state"]["bar"] = "user202"

    current_user_id = 101
    assert proxy.performance_analytics["analytics_cache"]["foo"] == "user101"
    assert proxy.qfm_engine["state"]["bar"] == "user101"

    current_user_id = 202
    assert proxy.performance_analytics["analytics_cache"]["foo"] == "user202"
    assert proxy.qfm_engine["state"]["bar"] == "user202"
