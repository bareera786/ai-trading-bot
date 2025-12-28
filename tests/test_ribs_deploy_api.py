import json
from flask import Flask

from app.routes.status import status_bp


class DummyWorker:
    def __init__(self, deploy_result=None):
        self.ribs_optimizer = self
        self._elites = [
            {
                "id": "ribs_elite_1",
                "solution": [1, 2, 3],
                "params": {},
                "objective": -10.0,
                "behavior": [0.0, 0.0, 0.0],
            }
        ]
        self._deploy_result = deploy_result or {
            "success": False,
            "message": "Backtest total_return -10.0 < required 0.0",
        }

    def get_elite_strategies(self):
        return self._elites

    def deploy_strategy(self, solution, strategy_id):
        return self._deploy_result


def test_deploy_ribs_strategy_rejected(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(status_bp)

    # Inject a minimal ai_bot_context with a service_runtime that has our DummyWorker
    class SR:
        pass

    sr = SR()
    sr.self_improvement_worker = DummyWorker()

    app.extensions["ai_bot_context"] = {"service_runtime": sr}

    with app.test_client() as client:
        resp = client.post("/api/ribs/deploy/ribs_elite_1")
        assert resp.status_code == 400
        data = resp.get_json() or {}
        assert data.get("success") is False
        assert "Backtest" in data.get("error", "")
