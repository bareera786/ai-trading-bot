import os


class _DummyTrader:
    def __init__(self, initial_balance=10000):
        self.initial_balance = initial_balance


class _DummyCredentialStore:
    def get_credentials(self, *_args, **_kwargs):
        return {}


class _DummyCredentialService:
    def __init__(self):
        self.credentials_store = _DummyCredentialStore()


def _make_market_data_service():
    from app.services.market_data import MarketDataService

    base_ultimate = _DummyTrader(initial_balance=123)
    base_optimized = _DummyTrader(initial_balance=123)

    return MarketDataService(
        dashboard_data={},
        historical_data={},
        trading_config={},
        ultimate_trader=base_ultimate,
        optimized_trader=base_optimized,
        ultimate_ml_system=object(),
        optimized_ml_system=object(),
        parallel_engine=object(),
        futures_manual_settings={},
        binance_credential_service=_DummyCredentialService(),
        get_active_trading_universe=lambda: [],
        get_real_market_data=lambda _symbol: None,
        get_trending_pairs=lambda: [],
        refresh_symbol_counters=lambda: None,
        refresh_indicator_dashboard_state=lambda: None,
        safe_float=lambda v, d=0.0: float(v) if v is not None else d,
        bot_logger=object(),
        auto_user_id_provider=None,
        persistence_manager=None,
        symbols_for_persistence=[],
        futures_safety_service=None,
        sleep_interval=5.0,
    )


def test_invariant_user_trader_identity_and_profile_are_user_scoped():
    svc = _make_market_data_service()

    u1_ult, u1_opt = svc._get_or_create_user_traders(1)
    u2_ult, u2_opt = svc._get_or_create_user_traders(2)

    assert u1_ult is not u2_ult
    assert u1_opt is not u2_opt

    assert getattr(u1_ult, "user_id") == 1
    assert getattr(u1_opt, "user_id") == 1
    assert getattr(u2_ult, "user_id") == 2
    assert getattr(u2_opt, "user_id") == 2

    assert getattr(u1_ult, "persistence_profile") == "user_1"
    assert getattr(u1_opt, "persistence_profile") == "user_1"
    assert getattr(u2_ult, "persistence_profile") == "user_2"
    assert getattr(u2_opt, "persistence_profile") == "user_2"

    # Cached lookup should return the same objects and still satisfy invariants.
    u1_ult2, u1_opt2 = svc._get_or_create_user_traders(1)
    assert u1_ult2 is u1_ult
    assert u1_opt2 is u1_opt


def test_invariant_profile_override_does_not_mutate_global_bot_profile(tmp_path, monkeypatch):
    from app.services import pathing
    from app.services.persistence import ensure_persistence_dirs

    monkeypatch.setenv("BOT_PERSISTENCE_DIR", str(tmp_path))

    before_env = os.environ.get("BOT_PROFILE")
    before_pathing = pathing.BOT_PROFILE

    target = ensure_persistence_dirs("user_999")

    assert os.environ.get("BOT_PROFILE") == before_env
    assert pathing.BOT_PROFILE == before_pathing
    assert str(target).endswith(os.path.join(str(tmp_path), "user_999"))
