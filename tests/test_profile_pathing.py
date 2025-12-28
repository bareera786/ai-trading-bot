import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture
def profile_paths(tmp_path, monkeypatch):
    """Reload pathing/binance modules against an isolated project root."""

    original_profile = os.environ.get("BOT_PROFILE")
    monkeypatch.setenv("BOT_PROFILE", "default")

    pathing_module = importlib.reload(importlib.import_module("app.services.pathing"))
    original_root = pathing_module.PROJECT_ROOT_PATH
    original_root_str = pathing_module.PROJECT_ROOT
    pathing_module.PROJECT_ROOT_PATH = tmp_path
    pathing_module.PROJECT_ROOT = str(tmp_path)

    binance_module = importlib.reload(importlib.import_module("app.services.binance"))

    try:
        yield pathing_module, binance_module
    finally:
        if original_profile is None:
            monkeypatch.delenv("BOT_PROFILE", raising=False)
        else:
            monkeypatch.setenv("BOT_PROFILE", original_profile)
        pathing_module.PROJECT_ROOT_PATH = original_root
        pathing_module.PROJECT_ROOT = original_root_str
        importlib.reload(pathing_module)
        importlib.reload(binance_module)


def test_resolve_profile_path_migrates_legacy_dir(profile_paths):
    pathing, _ = profile_paths

    legacy_root = pathing.PROJECT_ROOT_PATH / "bot_persistence"
    legacy_root.mkdir(parents=True)
    legacy_file = legacy_root / "bot_state.json"
    legacy_file.write_text("{}")

    resolved = pathing.resolve_profile_path(
        "bot_persistence", allow_legacy=False, migrate_legacy=True
    )
    profiled_dir = Path(resolved)

    assert profiled_dir.name == "default"
    assert profiled_dir.parent.name == "bot_persistence"
    assert (profiled_dir / "bot_state.json").exists()
    assert not legacy_file.exists()


def test_binance_store_migrates_credentials(profile_paths):
    pathing, binance = profile_paths

    legacy_file = (
        pathing.PROJECT_ROOT_PATH / "bot_persistence" / "binance_credentials.json"
    )
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text('{"spot": {"api_key": "abc", "api_secret": "def"}}')

    credentials_dir = pathing.resolve_profile_path(
        "credentials", allow_legacy=False, migrate_legacy=True
    )
    credential_file = os.path.join(credentials_dir, f"{pathing.BOT_PROFILE}.json")

    binance.BinanceCredentialStore(
        storage_dir=credentials_dir, credential_file=credential_file
    )

    assert Path(credential_file).exists()
    assert not legacy_file.exists()


@pytest.fixture
def profile_reloader(tmp_path, monkeypatch):
    """Reload pathing/binance modules for a given BOT_PROFILE backed by an isolated project root."""

    original_profile = os.environ.get("BOT_PROFILE")

    def _reload(profile: str):
        monkeypatch.setenv("BOT_PROFILE", profile)
        pathing_module = importlib.reload(
            importlib.import_module("app.services.pathing")
        )
        pathing_module.PROJECT_ROOT_PATH = tmp_path
        pathing_module.PROJECT_ROOT = str(tmp_path)
        binance_module = importlib.reload(
            importlib.import_module("app.services.binance")
        )
        return pathing_module, binance_module

    yield _reload

    if original_profile is None:
        monkeypatch.delenv("BOT_PROFILE", raising=False)
    else:
        monkeypatch.setenv("BOT_PROFILE", original_profile)
    importlib.reload(importlib.import_module("app.services.pathing"))
    importlib.reload(importlib.import_module("app.services.binance"))


def test_profile_paths_isolate_persistence(profile_reloader):
    # Bootstrap tenant "alpha" and write state into its dedicated directory.
    pathing, _ = profile_reloader("alpha")
    alpha_dir = Path(
        pathing.resolve_profile_path("bot_persistence", allow_legacy=False)
    )
    alpha_state = alpha_dir / "bot_state.json"
    alpha_state.write_text("alpha-only-state")

    # Switch to tenant "bravo" and ensure it gets a different directory without leaking files.
    pathing, _ = profile_reloader("bravo")
    bravo_dir = Path(
        pathing.resolve_profile_path("bot_persistence", allow_legacy=False)
    )
    assert bravo_dir != alpha_dir
    assert not (bravo_dir / "bot_state.json").exists()
    (bravo_dir / "bot_state.json").write_text("bravo-only-state")

    # Reload alpha to ensure its data remains untouched after bravo activity.
    profile_reloader("alpha")
    assert alpha_state.read_text() == "alpha-only-state"
    assert (bravo_dir / "bot_state.json").read_text() == "bravo-only-state"


def test_binance_store_isolates_multiple_profiles(profile_reloader):
    # Save credentials for tenant alpha.
    pathing, binance = profile_reloader("alpha")
    alpha_dir = Path(
        pathing.resolve_profile_path(
            "credentials", allow_legacy=False, migrate_legacy=True
        )
    )
    alpha_file = os.path.join(alpha_dir, f"{pathing.BOT_PROFILE}.json")
    alpha_store = binance.BinanceCredentialStore(
        storage_dir=str(alpha_dir), credential_file=alpha_file
    )
    alpha_store.save_credentials(
        "ALPHA_KEY", "ALPHA_SECRET", testnet=True, account_type="spot"
    )

    # Switch to tenant bravo and write a different credential payload.
    pathing, binance = profile_reloader("bravo")
    bravo_dir = Path(
        pathing.resolve_profile_path(
            "credentials", allow_legacy=False, migrate_legacy=True
        )
    )
    bravo_file = os.path.join(bravo_dir, f"{pathing.BOT_PROFILE}.json")
    bravo_store = binance.BinanceCredentialStore(
        storage_dir=str(bravo_dir), credential_file=bravo_file
    )
    bravo_store.save_credentials(
        "BRAVO_KEY", "BRAVO_SECRET", testnet=False, account_type="futures"
    )

    assert alpha_dir.name == "alpha"
    assert bravo_dir.name == "bravo"
    assert Path(alpha_file).exists()
    assert Path(bravo_file).exists()

    # Reload each tenant context to ensure lookups remain tenant-scoped.
    _, binance = profile_reloader("alpha")
    reloaded_alpha_store = binance.BinanceCredentialStore(
        storage_dir=str(alpha_dir), credential_file=alpha_file
    )
    assert reloaded_alpha_store.get_credentials("spot")["api_key"] == "ALPHA_KEY"
    assert reloaded_alpha_store.get_credentials("futures") == {}

    _, binance = profile_reloader("bravo")
    reloaded_bravo_store = binance.BinanceCredentialStore(
        storage_dir=str(bravo_dir), credential_file=bravo_file
    )
    assert reloaded_bravo_store.get_credentials("futures")["api_key"] == "BRAVO_KEY"
    assert reloaded_bravo_store.get_credentials("spot") == {}
