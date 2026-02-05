import importlib
import os


def test_database_url_fallback(monkeypatch):
    # Unset -> default used
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import app.config as cfg_mod

    importlib.reload(cfg_mod)
    assert cfg_mod.Config.SQLALCHEMY_DATABASE_URI == "sqlite:///trading_bot.db"

    # Empty string -> should be treated as unset (fallback)
    monkeypatch.setenv("DATABASE_URL", "")
    importlib.reload(cfg_mod)
    assert cfg_mod.Config.SQLALCHEMY_DATABASE_URI == "sqlite:///trading_bot.db"

    # Explicit URL should be used
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    importlib.reload(cfg_mod)
    assert (
        cfg_mod.Config.SQLALCHEMY_DATABASE_URI == "postgresql://user:pass@localhost/db"
    )
