import importlib
import types
import pytest

pytest.importorskip("flask_mail")


def test_import_and_basic_calls(tmp_path):
    # Import a set of modules and call small helper functions to exercise code paths
    mods = [
        "app.services.binance",
        "app.services.ribs_optimizer",
        "app.services.trade_history",
        "app.routes.status",
        "app.tasks.self_improvement",
    ]

    for m in mods:
        mod = importlib.import_module(m)
        assert isinstance(mod, types.ModuleType)

    # Call some helpers
    from app.services.binance import _coerce_bool, BinanceCredentialStore

    assert _coerce_bool(True) is True
    assert _coerce_bool("false") is False

    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    assert store.get_credentials() == {}

    # RIBS optimizer basic APIs
    from app.services.ribs_optimizer import TradingRIBSOptimizer
    import pandas as pd

    opt = TradingRIBSOptimizer()
    s = pd.Series([100 + i for i in range(20)])
    rsi = opt.calculate_rsi(s, period=14)
    assert hasattr(rsi, "tolist")

    # SelfImprovement simple init with ribs disabled
    from app.tasks.self_improvement import SelfImprovementWorker

    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=None,
        optimized_ml_system=None,
        dashboard_data={},
        trading_config={"enable_ribs_optimization": False},
        project_root=tmp_path,
        logger=None,
    )
    # call two auto-fixers to exercise their code paths
    worker._fix_memory_cleanup()
    worker._fix_config_reset()
