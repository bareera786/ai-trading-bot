import types


class _FakePersistenceManager:
    def __init__(self):
        self.calls = []

    def save_complete_state(self, _trader, _ml_system, _config, _symbols, _historical, *, profile=None):
        self.calls.append(profile)
        return True


class _FakeMarketDataService:
    def __init__(self, mapping):
        self._user_traders = dict(mapping)

    def _user_profile_name(self, user_id: int) -> str:
        return f"user_{int(user_id)}"


class _FakeTrader:
    pass


def test_graceful_shutdown_persists_user_scoped_profiles(monkeypatch):
    import ai_ml_auto_bot_final as bot_module

    persistence_manager = _FakePersistenceManager()
    monkeypatch.setattr(bot_module, "persistence_manager", persistence_manager)

    market_data_service = _FakeMarketDataService(
        {
            1: (_FakeTrader(), _FakeTrader()),
            2: (_FakeTrader(), _FakeTrader()),
        }
    )
    monkeypatch.setattr(bot_module, "market_data_service", market_data_service, raising=False)

    # Avoid dragging real runtime objects into the test.
    monkeypatch.setattr(bot_module, "ultimate_ml_system", object(), raising=False)
    monkeypatch.setattr(bot_module, "TRADING_CONFIG", {}, raising=False)
    monkeypatch.setattr(bot_module, "TOP_SYMBOLS", [], raising=False)
    monkeypatch.setattr(bot_module, "historical_data", {}, raising=False)

    saved = bot_module._persist_multiuser_states_on_shutdown()

    assert saved == 2
    assert persistence_manager.calls == ["user_1", "user_2"]
