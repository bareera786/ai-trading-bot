import json
import os

import pytest

pytest.importorskip("flask_mail")

from cryptography.fernet import Fernet
from app.services.binance import BinanceCredentialStore


def test_store_encrypts_when_key_provided(tmp_path):
    key = Fernet.generate_key()
    store = BinanceCredentialStore(storage_dir=str(tmp_path), encryption_key=key)

    # Save credentials for user 1
    store.save_credentials("k1", "s1", user_id=1)

    # Read raw file to ensure encrypted keys are present
    with open(store.credential_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "users" in data
    assert "1" in data["users"]
    user_entry = data["users"]["1"]
    # With encryption enabled, there should be encrypted api key fields
    assert user_entry.get("api_key_encrypted") or user_entry.get("encrypted")
