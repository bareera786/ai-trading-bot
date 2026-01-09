import json
import re
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ui_trade_history_does_not_infer_market_type_from_non_explicit_fields():
    """Regression: dashboard trade-history must prefer explicit market_type/exchange.

    This ensures the served hashed bundle (what users actually get) contains logic:
    - Compute marketType from trade.market_type
    - If marketType in {FUTURES, SPOT} then use it (and optionally exchange)
    - Else fall back to execution_mode

    This prevents UI regressions where market type is inferred from other fields.
    """

    repo_root = Path(__file__).resolve().parents[1]
    static_dir = repo_root / "app" / "static"
    manifest_path = static_dir / "dist" / "manifest.json"

    manifest = json.loads(_read_text(manifest_path))
    dashboard_rel = manifest.get("dashboard.js")
    assert dashboard_rel, "manifest.json missing dashboard.js entry"

    dashboard_path = static_dir / dashboard_rel
    assert dashboard_path.exists(), f"dashboard bundle not found: {dashboard_path}"

    bundle = _read_text(dashboard_path)

    # Presence checks: explicit fields are referenced.
    assert "market_type" in bundle
    assert "execution_mode" in bundle

    # Stronger structural checks: market_type is evaluated before execution_mode.
    # The current minified bundle pattern is roughly:
    #   h=String(n.market_type||"").toUpperCase();
    #   if(h==="FUTURES"||h==="SPOT") ... else if(n.execution_mode) ...
    assert re.search(r"market_type\)\|\|\"\"\)\.toUpperCase\(\)", bundle), (
        "dashboard bundle does not normalize market_type via toUpperCase()"
    )
    assert re.search(r"===\"FUTURES\"\|\|[^\n]{0,120}===\"SPOT\"", bundle), (
        "dashboard bundle does not branch on explicit market_type FUTURES/SPOT"
    )

    # Ensure execution_mode fallback exists *within the trade-history rendering chunk*.
    # The bundle contains other occurrences of "execution_mode" (filters, requests, etc), so we
    # scope the ordering check to the block that normalizes market_type.
    anchor = "market_type)||\"\").toUpperCase()"
    start = bundle.find(anchor)
    assert start != -1, "could not locate market_type normalization anchor in bundle"

    window = bundle[start : start + 1500]
    assert "\"FUTURES\"" in window and "\"SPOT\"" in window
    assert "execution_mode" in window, "no execution_mode fallback found near market_type logic"

    futures_idx = window.find('"FUTURES"')
    exec_idx = window.find("execution_mode")
    assert futures_idx != -1 and exec_idx != -1
    assert futures_idx < exec_idx, "execution_mode fallback should occur after FUTURES/SPOT check"
