import json

import pandas as pd

from app.services.ribs_optimizer import TradingRIBSOptimizer


def make_ohlcv(n=50):
    closes = [100 + i * 0.1 for i in range(n)]
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.05 for c in closes],
            "low": [c - 0.05 for c in closes],
            "close": closes,
            "volume": [1000 + i for i in range(n)],
        }
    )
    return {"ohlcv": df}


def test_ribs_writes_status_file_on_completion(tmp_path):
    opt = TradingRIBSOptimizer()
    # Use a temporary checkpoints dir to isolate
    opt.checkpoints_dir = str(tmp_path)
    tmp_dir = tmp_path
    tmp_dir.mkdir(exist_ok=True)

    market_data = make_ohlcv(120)

    # Run a short optimization cycle
    elites = opt.run_optimization_cycle(market_data, iterations=2)

    # Ensure run returned and status file exists
    status_path = tmp_path / "ribs_status.json"
    assert status_path.exists(), "ribs_status.json was not created"

    # Verify content indicates completion and contains elite information for dashboard rendering
    content = json.loads(status_path.read_text())
    assert content.get("running") is False
    assert content.get("archive_stats") is not None
    assert isinstance(content.get("iterations"), int)
    assert content.get("progress_percent") == 100

    # Completion status should include elite strategies and behavior arrays (best-effort)
    assert "elites" in content.get("archive_stats", {})
    assert "behaviors_x" in content
    assert "behaviors_y" in content
    assert "behaviors_z" in content
    assert "objectives" in content
