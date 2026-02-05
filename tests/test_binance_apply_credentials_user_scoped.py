import pytest

pytest.importorskip("flask_mail")

from app.services.binance import BinanceCredentialService


class _Store:
    SUPPORTED_ACCOUNT_TYPES = ("spot", "futures")

    def _normalize_account_type(self, account_type):
        value = str(account_type or "spot").strip().lower()
        return value if value in self.SUPPORTED_ACCOUNT_TYPES else "spot"

    def get_credentials(self, account_type=None, user_id=None):
        # For these tests we pass creds directly to apply_credentials.
        return {}


class _Trader:
    def __init__(self):
        self.enable_calls = 0
        self.disable_calls = 0

    def enable_real_trading(self, **kwargs):
        self.enable_calls += 1
        return True

    def enable_futures_trading(self, **kwargs):
        self.enable_calls += 1
        return True

    def disable_real_trading(self, **kwargs):
        self.disable_calls += 1
        return True


def test_apply_credentials_user_scoped_does_not_mutate_global_traders():
    ultimate = _Trader()
    optimized = _Trader()

    service = BinanceCredentialService(_Store(), ultimate, optimized)

    # Avoid python-binance dependency in unit test
    service.test_credentials = lambda *args, **kwargs: {"connected": True}

    creds = {"api_key": "K", "api_secret": "S", "testnet": True}

    ok = service.apply_credentials("spot", creds, user_id=123)
    assert ok is True
    assert ultimate.enable_calls == 0
    assert optimized.enable_calls == 0

    ok = service.apply_credentials("spot", creds)
    assert ok is True
    assert ultimate.enable_calls == 1
    assert optimized.enable_calls == 1
