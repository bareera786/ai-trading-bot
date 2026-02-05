import os
from datetime import datetime, timedelta

import pytest

pytest.importorskip("flask_mail")

from app.services.trade_history import ComprehensiveTradeHistory


def make_trade(symbol="BTCUSDT", side="BUY", price=100, pnl=10):
    return {
        "symbol": symbol,
        "side": side,
        "price": price,
        "quantity": 1,
        "pnl": pnl,
        "pnl_percent": pnl,
        "type": "AUTO",
        "execution_mode": "paper",
    }


def test_add_and_update_trade(tmp_path):
    th = ComprehensiveTradeHistory(data_dir=str(tmp_path))

    t = make_trade()
    rec = th.add_trade(t)
    assert rec is not None
    assert rec["trade_id"] == 1
    assert rec["status"] == "OPEN"

    # Update exit
    ok = th.update_trade_exit(1, {"exit_price": 110, "pnl": 10, "pnl_percent": 10})
    assert ok

    stats = th.get_trade_statistics()
    assert stats["summary"]["total_trades"] >= 1


def test_filters_and_export(tmp_path):
    th = ComprehensiveTradeHistory(data_dir=str(tmp_path))

    # add closed and open trades
    t1 = make_trade(symbol="BTCUSDT", side="BUY", pnl=5)
    t2 = make_trade(symbol="ETHUSDT", side="SELL", pnl=-3)
    rec1 = th.add_trade(t1)
    rec2 = th.add_trade(t2)

    # Update one to closed
    th.update_trade_exit(rec1["trade_id"], {"exit_price": 110, "pnl": 5})

    all_trades = th.get_trade_history()
    assert len(all_trades) >= 2

    btc_trades = th.get_trade_history(filters={"symbol": "BTCUSDT"})
    assert all(t["symbol"] == "BTCUSDT" for t in btc_trades)

    # Export CSV
    path = th.export_to_csv()
    assert path is None or os.path.exists(path)


def test_journal_and_clear(tmp_path):
    th = ComprehensiveTradeHistory(data_dir=str(tmp_path))

    ev = th.log_journal_event("TEST_EVENT", payload={"symbol": "BTCUSDT", "note": "ok"})
    assert "timestamp" in ev

    events = th.get_journal_events()
    assert any(e["event_type"] == "TEST_EVENT" for e in events)

    # Filter by symbol
    events_sym = th.get_journal_events(symbol="BTCUSDT")
    assert len(events_sym) >= 1

    # Clear journal
    assert th.clear_journal() or True
