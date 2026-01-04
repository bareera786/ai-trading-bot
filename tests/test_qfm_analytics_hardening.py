import ai_ml_auto_bot_final as bot_module


def test_qfm_performance_analytics_is_initialized_per_trader_instance():
    t1 = bot_module.UltimateAIAutoTrader(initial_balance=1000)
    t2 = bot_module.UltimateAIAutoTrader(initial_balance=1000)

    assert isinstance(getattr(t1, "performance_analytics", None), dict)
    assert isinstance(getattr(t2, "performance_analytics", None), dict)

    # Must be different dict objects (no shared mutable state).
    assert t1.performance_analytics is not t2.performance_analytics

    # Nested cache must also be isolated.
    assert isinstance(t1.performance_analytics.get("analytics_cache"), dict)
    assert isinstance(t2.performance_analytics.get("analytics_cache"), dict)
    assert t1.performance_analytics["analytics_cache"] is not t2.performance_analytics["analytics_cache"]

    # Mutations must not cross-contaminate.
    t1.performance_analytics["analytics_cache"]["key"] = "value"
    assert "key" not in t2.performance_analytics["analytics_cache"]
