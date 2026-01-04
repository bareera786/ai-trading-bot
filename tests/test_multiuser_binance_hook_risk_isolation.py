class _Safety:
    def __init__(self):
        self.failures = []
        self.clears = 0

    def log_api_failure(self, message=None):
        self.failures.append(message)

    def clear_api_failures(self):
        self.clears += 1


class _Trader:
    def __init__(self):
        self.safety_manager = _Safety()


class _Service:
    def __init__(self, mapping):
        self._user_traders = dict(mapping)


def test_binance_api_hooks_apply_to_user_scoped_traders(monkeypatch):
    import ai_ml_auto_bot_final as bot_module

    u1a, u1b = _Trader(), _Trader()
    u2a, u2b = _Trader(), _Trader()

    monkeypatch.setattr(
        bot_module,
        "market_data_service",
        _Service({1: (u1a, u1b), 2: (u2a, u2b)}),
        raising=False,
    )

    # Guardrail: if hooks mistakenly use globals, fail loudly.
    class _Explode:
        @property
        def safety_manager(self):
            raise AssertionError("global trader should not be used")

    monkeypatch.setattr(bot_module, "ultimate_trader", _Explode(), raising=False)
    monkeypatch.setattr(bot_module, "optimized_trader", _Explode(), raising=False)

    bot_module._binance_api_failure_hook("oops")
    for t in (u1a, u1b, u2a, u2b):
        assert t.safety_manager.failures == ["oops"]
        assert t.safety_manager.clears == 0

    bot_module._binance_api_success_hook()
    for t in (u1a, u1b, u2a, u2b):
        assert t.safety_manager.clears == 1
