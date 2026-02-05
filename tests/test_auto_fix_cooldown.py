import time
from pathlib import Path

from app.tasks.self_improvement import SelfImprovementWorker


def make_worker(tmp_path, config_overrides=None):
    cfg = {}
    if config_overrides:
        cfg.update(config_overrides)

    dashboard_data = {"self_improvement": {}}
    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=None,
        optimized_ml_system=None,
        dashboard_data=dashboard_data,
        trading_config=cfg,
        logger=None,
        project_root=Path(tmp_path),
    )
    return worker


def test_execute_auto_fix_action_respects_cooldown(tmp_path):
    worker = make_worker(tmp_path, {"auto_fix_cooldown_seconds": 10})

    called = []

    def dummy_fix():
        called.append(True)

    worker.auto_fix_handlers["dummy_fix"] = dummy_fix

    # First call should start the action
    res1 = worker.execute_auto_fix_action("dummy_fix")
    assert res1["success"] is True

    # Immediately calling again should be rejected due to cooldown
    res2 = worker.execute_auto_fix_action("dummy_fix")
    assert res2["success"] is False
    assert "cooldown" in res2["message"].lower()
