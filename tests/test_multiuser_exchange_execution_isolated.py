class _SharedResponseClient:
    def __init__(self, shared_response):
        self._shared = shared_response

    def create_test_order(self, **_kwargs):
        # Simulate a buggy client that returns the SAME dict object every time.
        return self._shared


def _make_ready_trader(shared_client):
    from app.services.trading import RealBinanceTrader

    t = RealBinanceTrader(
        api_key="k",
        api_secret="s",
        testnet=True,
        account_type="spot",
            binance_client_cls=None,  # prevent connect() attempting real client init
        api_exception_cls=Exception,
    )

    # Force ready without touching network.
    t.connected = True
    t.client = shared_client

    # Avoid exchange metadata lookups.
    t._resolve_price = lambda _symbol, _ref=None: 100.0
    t.get_min_notional = lambda _symbol: None
    t._normalize_order_quantity = lambda _symbol, qty: (float(qty), None)

    return t


def test_two_users_do_not_share_order_response_objects():
    from app.services.trading import RealBinanceTrader

    shared_response = {"status": "FILLED", "fills": [{"price": "1", "qty": "1"}]}
    shared_client = _SharedResponseClient(shared_response)

    user1 = _make_ready_trader(shared_client)
    user2 = _make_ready_trader(shared_client)

    r1 = user1.place_real_order("BTCUSDT", "BUY", 0.01, order_type="MARKET")
    r2 = user2.place_real_order("BTCUSDT", "BUY", 0.01, order_type="MARKET")

    # Underlying client returned the same object both times.
    assert r1 is shared_response
    assert r2 is shared_response

    # But each trader must store its own copy in execution cache (order_history).
    e1 = user1.order_history[-1]
    e2 = user2.order_history[-1]

    assert e1["response"] is not shared_response
    assert e2["response"] is not shared_response
    assert e1["response"] is not e2["response"]

    # Mutating user1 stored response must not affect user2.
    e1["response"]["mutated_by"] = "user1"
    assert "mutated_by" not in e2["response"]
