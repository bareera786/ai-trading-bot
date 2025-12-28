import os

from cryptography.fernet import Fernet

from app.services.binance import (
    BinanceCredentialService,
    BinanceCredentialStore,
    BinanceLogManager,
)


class DummyTrader:
    def __init__(self) -> None:
        self.enable_real_calls: list[dict[str, str]] = []
        self.enable_futures_calls: list[dict[str, str]] = []
        self.paper_trading = True
        self.real_trading_enabled = False
        self.futures_trading_enabled = False

    def enable_real_trading(self, **kwargs):
        self.enable_real_calls.append(kwargs)
        self.real_trading_enabled = True
        return True

    def enable_futures_trading(self, **kwargs):
        self.enable_futures_calls.append(kwargs)
        self.futures_trading_enabled = True
        return True

    def get_real_trading_status(self):
        return {"connected": self.real_trading_enabled}

    def get_futures_trading_status(self):
        return {"connected": self.futures_trading_enabled}


def test_store_encrypts_and_decrypts(tmp_path, monkeypatch):
    monkeypatch.delenv("BINANCE_CREDENTIAL_KEY", raising=False)
    key = Fernet.generate_key()
    store = BinanceCredentialStore(storage_dir=str(tmp_path), encryption_key=key)

    saved = store.save_credentials("APIKEY123", "SECRET456", testnet=True, note="spot")
    assert saved["encrypted"] is True

    credential_file = os.path.join(tmp_path, "binance_credentials.json")
    raw_contents = open(credential_file, "r", encoding="utf-8").read()
    assert "APIKEY123" not in raw_contents
    assert "SECRET456" not in raw_contents

    fetched = store.get_credentials("spot")
    assert fetched["api_key"] == "APIKEY123"
    assert fetched["api_secret"] == "SECRET456"
    assert fetched["encrypted"] is True


def test_store_returns_blank_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("BINANCE_CREDENTIAL_KEY", raising=False)
    key = Fernet.generate_key()
    store = BinanceCredentialStore(storage_dir=str(tmp_path), encryption_key=key)
    store.save_credentials("APIKEY321", "SECRET654", testnet=True)

    store_without_key = BinanceCredentialStore(storage_dir=str(tmp_path))
    creds = store_without_key.get_credentials("spot")
    assert creds["api_key"] == ""
    assert creds["api_secret"] == ""
    assert creds["encrypted"] is True


def test_terms_block_live_trading_without_acceptance(tmp_path):
    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    saved = store.save_credentials("API", "SEC", testnet=False)
    trader = DummyTrader()
    log_manager = BinanceLogManager()
    service = BinanceCredentialService(
        store,
        trader,
        trader,
        binance_log_manager=log_manager,
        terms_accepted=False,
    )

    result = service.apply_credentials("spot", saved)
    assert result is False
    assert trader.enable_real_calls == []


def test_terms_allow_live_trading_when_accepted(tmp_path):
    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    saved = store.save_credentials("API", "SEC", testnet=False)
    trader = DummyTrader()
    service = BinanceCredentialService(
        store,
        trader,
        trader,
        terms_accepted=True,
    )

    result = service.apply_credentials("spot", saved)
    assert result is True
    assert trader.enable_real_calls != []
