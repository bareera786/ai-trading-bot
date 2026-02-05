import os
import pytest

pytest.importorskip("flask_mail")

from app.services.binance import BinanceCredentialStore


def test_store_scopes_by_user(tmp_path):
    store = BinanceCredentialStore(storage_dir=str(tmp_path))

    # Save credentials for two different users
    a = store.save_credentials(
        "API1", "SEC1", testnet=True, account_type="spot", user_id=1
    )
    b = store.save_credentials(
        "API2", "SEC2", testnet=False, account_type="spot", user_id=2
    )

    creds1 = store.get_credentials("spot", user_id=1)
    creds2 = store.get_credentials("spot", user_id=2)

    assert creds1["api_key"] == "API1"
    assert creds2["api_key"] == "API2"

    # Ensure clearing one user does not clear the other
    store.clear_credentials(user_id=1)
    creds1_after = store.get_credentials("spot", user_id=1)
    creds2_after = store.get_credentials("spot", user_id=2)

    assert not creds1_after or not creds1_after.get("api_key")
    assert creds2_after["api_key"] == "API2"


def test_store_legacy_global_behavior(tmp_path):
    # When not providing user_id, behaviour should remain legacy (global slot)
    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    store.save_credentials("GAPI", "GSEC", testnet=True, account_type="futures")
    global_creds = store.get_credentials("futures")
    assert global_creds.get("api_key") == "GAPI"
