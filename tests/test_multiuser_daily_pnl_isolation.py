import types


class _FakeUser:
    def __init__(self, user_id: int, username: str):
        self.id = int(user_id)
        self.username = username


class _FakeUserQuery:
    def __init__(self, users, *, filter_id=None):
        self._users = list(users)
        self._filter_id = filter_id

    def filter_by(self, **kwargs):
        return _FakeUserQuery(self._users, filter_id=kwargs.get("id"))

    def all(self):
        if self._filter_id is None:
            return list(self._users)
        return [u for u in self._users if u.id == int(self._filter_id)]


class _FakeUserModel:
    def __init__(self, users):
        self.query = _FakeUserQuery(users)


class _FakePortfolio:
    def __init__(self, user_id: int):
        self.user_id = int(user_id)
        self.daily_pnl = -999.0
        self.updated_at = None


class _FakePortfolioQuery:
    def __init__(self, portfolios, *, filter_user_id=None):
        self._portfolios = dict(portfolios)
        self._filter_user_id = filter_user_id

    def filter_by(self, **kwargs):
        return _FakePortfolioQuery(self._portfolios, filter_user_id=kwargs.get("user_id"))

    def first(self):
        if self._filter_user_id is None:
            return None
        return self._portfolios.get(int(self._filter_user_id))


class _FakePortfolioModel:
    def __init__(self, portfolios):
        self.query = _FakePortfolioQuery(portfolios)


class _FakeTrader:
    def __init__(self, daily_pnl: float):
        self.daily_pnl = float(daily_pnl)


class _FakeMarketDataService:
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def _get_or_create_user_traders(self, user_id: int):
        return self._mapping[int(user_id)]


def test_update_portfolio_daily_pnl_uses_user_scoped_traders(monkeypatch):
    import ai_ml_auto_bot_final as bot_module

    users = [_FakeUser(1, "u1"), _FakeUser(2, "u2")]
    portfolios = {1: _FakePortfolio(1), 2: _FakePortfolio(2)}

    monkeypatch.setattr(bot_module, "User", _FakeUserModel(users))
    monkeypatch.setattr(bot_module, "UserPortfolio", _FakePortfolioModel(portfolios))

    fake_db = types.SimpleNamespace(
        session=types.SimpleNamespace(commit=lambda: None, rollback=lambda: None)
    )
    monkeypatch.setattr(bot_module, "db", fake_db)

    # If the function incorrectly uses the global singletons, this would leak.
    monkeypatch.setattr(bot_module, "ultimate_trader", _FakeTrader(9999.0), raising=False)
    monkeypatch.setattr(bot_module, "optimized_trader", _FakeTrader(9999.0), raising=False)

    market_data_service = _FakeMarketDataService(
        {
            1: (_FakeTrader(10.0), _FakeTrader(5.0)),
            2: (_FakeTrader(-2.5), _FakeTrader(1.0)),
        }
    )
    monkeypatch.setattr(bot_module, "market_data_service", market_data_service, raising=False)

    result = bot_module.update_portfolio_daily_pnl()

    assert result["success"] is True
    assert result["updated_users"] == 2

    assert portfolios[1].daily_pnl == 15.0
    assert portfolios[2].daily_pnl == -1.5
