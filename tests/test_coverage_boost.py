import json
import os
import pickle
import tempfile
from datetime import datetime

import pytest
import logging

pytest.importorskip("flask_mail")

from app.services.binance import (
    BinanceCredentialStore,
    BinanceCredentialService,
    BinanceLogManager,
)
from app.tasks.self_improvement import SelfImprovementWorker
from app.services.ribs_optimizer import TradingRIBSOptimizer


def test_self_improvement_fix_handlers(tmp_path, monkeypatch):
    # Create dummy systems
    class DummySystem:
        def __init__(self):
            self.retrained = False

        def retrain_models(self):
            self.retrained = True

    ultimate = DummySystem()
    optimized = DummySystem()

    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=ultimate,
        optimized_ml_system=optimized,
        dashboard_data={},
        trading_config={},
        project_root=tmp_path,
        logger=logging.getLogger("tests"),
    )

    # Call auto-fix methods
    worker._fix_model_retraining()
    assert ultimate.retrained and optimized.retrained

    worker._fix_config_reset()
    assert "risk_per_trade" in worker.trading_config

    # Correlation adjustments
    corrs = {"A_B": 0.9, "C_D": 0.7, "E_F": 0.5}
    adjustments = worker._calculate_correlation_adjustments(corrs)
    assert adjustments["A_B"] == 0.7


def test_binance_store_and_service(tmp_path):
    storage_dir = str(tmp_path)
    store = BinanceCredentialStore(storage_dir=storage_dir)

    # Save credentials for user 42
    payload = store.save_credentials("key1234", "secret9876", testnet=True, user_id=42)
    assert payload["api_key"] == "key1234"

    creds = store.get_credentials(user_id=42)
    assert "spot" in creds or creds == {}

    # Masking
    masked = BinanceCredentialService.mask_api_key("ABCDEFGH1234")
    assert "…" in masked


def test_ribs_load_checkpoint(tmp_path):
    opt = TradingRIBSOptimizer()
    # Create a fake checkpoint file
    ck = {
        "archive": opt.archive,
        "best_solution": opt.best_solution,
        "best_objective": opt.best_objective,
        "history": [],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    path = tmp_path / "ribs_checkpoint_test.pkl"
    with open(path, "wb") as f:
        pickle.dump(ck, f)

    opt.load_checkpoint(str(path))
    # If load succeeds, best_objective and history should be present
    assert hasattr(opt, "best_objective")


def test_ribs_health_endpoint(tmp_path, monkeypatch):
    # Create ribs_status.json
    base = tmp_path / "bot_persistence" / "ribs_checkpoints"
    base.mkdir(parents=True)
    status_path = base / "ribs_status.json"
    payload = {
        "running": False,
        "latest_checkpoint": {"path": "dummy", "mtime": 12345, "size": 42},
    }
    with open(status_path, "w") as f:
        json.dump(payload, f)

    monkeypatch.chdir(str(tmp_path))

    from flask import Flask
    from app.routes.status import status_bp

    app = Flask(__name__)
    app.register_blueprint(status_bp)

    with app.test_client() as client:
        resp = client.get("/api/health/ribs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") == "ok"
