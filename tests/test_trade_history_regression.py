import re
from datetime import datetime

from flask import Flask
from app.services.pathing import safe_parse_datetime
from app.services.trade_history import ComprehensiveTradeHistory
from app.routes.metrics import metrics_bp


def _parse_ts_or_none(value):
    return safe_parse_datetime(value)


def test_api_trades_newest_first():
    """Ensure /api/trades returns trades in newest-first order.

    Use a minimal Flask app with the `metrics` blueprint and a simple
    `ai_bot_context` extension containing an `ultimate_trader` whose
    `trade_history.get_trade_history` delegates to the real service.
    """
    app = Flask(__name__)
    # Minimal context with a trade_history capable object
    ch = ComprehensiveTradeHistory()

    class DummyTrader:
        def __init__(self, trade_history):
            self.trade_history = trade_history

    app.register_blueprint(metrics_bp)
    app.extensions['ai_bot_context'] = {
        'ultimate_trader': DummyTrader(ch),
        'optimized_trader': None,
    }

    with app.test_client() as c:
        resp = c.get('/api/trades')
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        data = resp.get_json() or {}
        trades = data.get('trades') or []

        prev_dt = None
        for idx, trade in enumerate(trades):
            ts = trade.get('timestamp')
            parsed = _parse_ts_or_none(ts)
            assert parsed is not None, f"Trade at index {idx} has unparseable timestamp: {ts!r}"
            if prev_dt is not None:
                assert prev_dt >= parsed, (
                    f"Trades are not newest-first at index {idx-1}->{idx}: {prev_dt.isoformat()} < {parsed.isoformat()}"
                )
            prev_dt = parsed


def test_dashboard_template_has_expected_th_count():
    """Simple regression guard: template header columns should match JS-rendered cells.

    The trade-history JS renders 16 <td> cells per row; ensure the template
    <thead> contains 16 <th> headers so layout/pagination/Actions column align.
    """
    tmpl_path = 'app/templates/dashboard.html'
    with open(tmpl_path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    # Extract the specific table that contains the trade-history tbody and
    # count <th> within that table only.
    # Find the <tbody id="trade-history-table"> first, then locate the
    # nearest enclosing <table> element to avoid matching an earlier table
    # and accidentally counting headers from unrelated tables.
    m = re.search(r"<tbody[^>]*id=[\"']trade-history-table[\"'][\s\S]*?</tbody>", content, flags=re.IGNORECASE)
    assert m, "Could not locate trade history tbody in dashboard template"

    # Find the start of the table that contains this tbody by searching
    # backward for the last '<table' before the tbody, and forward for the
    # next closing '</table>' after the tbody.
    table_start = content.rfind('<table', 0, m.start())
    assert table_start != -1, "Could not locate enclosing <table> for trade-history tbody"
    table_end = content.find('</table>', m.end())
    assert table_end != -1, "Could not locate closing </table> for trade-history table"

    table_html = content[table_start:table_end + len('</table>')]
    th_count = len(re.findall(r'<th\b', table_html, flags=re.IGNORECASE))
    assert th_count == 16, f"Expected 16 <th> headers in trade-history table, found {th_count}"
