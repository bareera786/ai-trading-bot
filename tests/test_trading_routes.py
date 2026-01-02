"""Comprehensive tests for trading API routes."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from flask_login import current_user, login_user

import importlib
import app.routes.trading as trading_mod
import app.routes.dashboard as dashboard_mod

# Ensure modules are freshly loaded so decorators (like login_required) are the
# real ones (tests may have previously monkeypatched them in other contexts).
importlib.reload(trading_mod)
importlib.reload(dashboard_mod)

trading_bp = trading_mod.trading_bp
dashboard_bp = dashboard_mod.dashboard_bp


class MockUser:
    """Mock user for testing."""
    def __init__(self, user_id: int = 1):
        self.id = user_id
        self.is_authenticated = True
        self.is_active = True

    def get_id(self):
        return str(self.id)


class MockTrader:
    """Mock trader for testing."""
    def __init__(self, paper_trading: bool = True, real_trading_enabled: bool = False):
        self.paper_trading = paper_trading
        self.real_trading_enabled = real_trading_enabled
        self.trading_enabled = False
        self.futures_trading_enabled = False

    def get_real_trading_status(self):
        return {
            "connected": self.real_trading_enabled,
            "paper_trading": self.paper_trading
        }


class MockUserTrader:
    """Mock user trader for manual trade execution."""
    def __init__(self, success: bool = True):
        self.success = success

    def execute_manual_trade(self, symbol: str, side: str, quantity: float, price: float | None = None):
        if self.success:
            return {
                "success": True,
                "order": {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price or 50000.0,
                    "status": "FILLED"
                },
                "price": price or 50000.0
            }
        return {"success": False, "error": "Trade execution failed"}

    def execute_manual_futures_trade(self, symbol: str, side: str, quantity: float,
                                   leverage: int = 1, price: float | None = None):
        if self.success:
            return {
                "success": True,
                "order": {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "leverage": leverage,
                    "price": price or 50000.0,
                    "status": "FILLED"
                },
                "price": price or 50000.0
            }
        return {"success": False, "error": "Futures trade execution failed"}


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Initialize Flask-Login
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # For API testing, return 401 instead of redirecting
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required"}), 401

    # Add user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return MockUser(int(user_id))

    app.register_blueprint(trading_bp, url_prefix='')
    app.register_blueprint(dashboard_bp, url_prefix='')
    return app


@pytest.fixture
def mock_context():
    """Mock bot context with all required services."""
    return {
        "dashboard_data": {
            "system_status": {},
            "optimized_system_status": {},
            "real_trading_status": {},
            "optimized_real_trading_status": {}
        },
        "ultimate_trader": MockTrader(),
        "optimized_trader": MockTrader(),
        "get_user_trader": lambda user_id, profile: MockUserTrader(),
        "record_user_trade": MagicMock(),
        "binance_credentials_store": MagicMock(),
        "binance_log_manager": MagicMock(),
        "get_binance_credential_status": MagicMock(return_value={
            "ultimate_status": {"connected": False},
            "optimized_status": {"connected": False},
            "logs": []
        }),
        "apply_binance_credentials": MagicMock(return_value=True),
        "futures_data_lock": MagicMock(),
        "futures_dashboard_state": {},
        "futures_manual_service": None,
        "ensure_futures_manual_defaults": None,
        "coerce_bool": lambda value, default=True: bool(value) if value is not None else default,
        "version_label": "TEST_VERSION"
    }


@pytest.fixture
def client(app, mock_context):
    """Test client with mocked context."""
    with app.test_client() as client:
        with app.app_context():
            app.extensions = {"ai_bot_context": mock_context}
        yield client


@pytest.fixture
def login_as(client):
    """Helper to mark the test client as logged in as a MockUser."""
    def _login(user: MockUser | None = None):
        user = user or MockUser()
        with client.session_transaction() as sess:
            sess['_user_id'] = user.get_id()
            sess['_fresh'] = True
        return user

    return _login


class TestTradingStatus:
    """Test cases for main trading status endpoint."""

    def test_trading_status_unauthenticated(self, client):
        """Test trading status endpoint without authentication."""
        response = client.get('/api/trading/status')
        # With real decorators enabled, unauthenticated requests should be 401
        assert response.status_code == 401

    def test_trading_status_authenticated(self, client, login_as):
        """Test trading status endpoint with authentication."""
        # Log in and request status
        login_as()
        response = client.get('/api/trading/status')
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert "mode" in data
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "mode" in data
        assert "open_positions" in data
        assert "total_trades" in data
        assert "success_rate" in data
        assert "daily_pnl" in data


class TestSpotToggle:
    """Test cases for spot trading toggle endpoint."""

    def test_spot_toggle_unauthenticated(self, client):
        """Test spot toggle endpoint without authentication."""
        response = client.post('/api/spot/toggle', json={"enable": True})
        assert response.status_code == 401

    def test_spot_toggle_enable(self, client, mock_context, login_as):
        """Test enabling spot trading."""
        login_as()
        response = client.post('/api/spot/toggle', json={"enable": True})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["trading_enabled"] is True
        assert "enabled" in data["message"]

        # Check that traders were updated
        assert mock_context["ultimate_trader"].trading_enabled is True
        assert mock_context["optimized_trader"].trading_enabled is True

    def test_spot_toggle_disable(self, client, mock_context, login_as):
        """Test disabling spot trading."""
        # First enable trading
        mock_context["ultimate_trader"].trading_enabled = True
        mock_context["optimized_trader"].trading_enabled = True

        login_as()
        response = client.post('/api/spot/toggle', json={"enable": False})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["trading_enabled"] is False
        assert "disabled" in data["message"]

    def test_spot_toggle_toggle_mode(self, client, mock_context, login_as):
        """Test toggle mode (no enable parameter)."""
        login_as()
        # Should enable (currently disabled)
        response = client.post('/api/spot/toggle', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["trading_enabled"] is True

        # Should disable (now enabled)
        response = client.post('/api/spot/toggle', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["trading_enabled"] is False

    def test_spot_toggle_missing_traders(self, client, mock_context, login_as):
        """Test spot toggle with missing traders."""
        # Remove traders from context
        mock_context["ultimate_trader"] = None
        mock_context["optimized_trader"] = None

        login_as()
        response = client.post('/api/spot/toggle', json={"enable": True})
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert "Trading engines unavailable" in data["error"]


class TestFuturesToggle:
    """Test cases for futures trading toggle endpoint."""

    def test_futures_toggle_unauthenticated(self, client):
        """Test futures toggle endpoint without authentication."""
        response = client.post('/api/futures/toggle', json={"enable": True})
        assert response.status_code == 401

    def test_futures_toggle_enable(self, client, mock_context, login_as):
        """Test enabling futures trading."""
        login_as()
        response = client.post('/api/futures/toggle', json={"enable": True})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["futures_trading_enabled"] is True
        assert "enabled" in data["message"]

        # Check that traders were updated
        assert mock_context["ultimate_trader"].futures_trading_enabled is True
        assert mock_context["optimized_trader"].futures_trading_enabled is True

    def test_futures_toggle_disable(self, client, mock_context, login_as):
        """Test disabling futures trading."""
        # First enable futures trading
        mock_context["ultimate_trader"].futures_trading_enabled = True
        mock_context["optimized_trader"].futures_trading_enabled = True

        login_as()
        response = client.post('/api/futures/toggle', json={"enable": False})
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["futures_trading_enabled"] is False
        assert "disabled" in data["message"]

    def test_futures_toggle_missing_traders(self, client, mock_context, login_as):
        """Test futures toggle with missing traders."""
        # Remove traders from context
        mock_context["ultimate_trader"] = None
        mock_context["optimized_trader"] = None

        login_as()
        response = client.post('/api/futures/toggle', json={"enable": True})
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert "Trading engines unavailable" in data["error"]


class TestSpotTrade:
    """Test cases for spot trade execution endpoint."""

    def test_spot_trade_unauthenticated(self, client):
        """Test spot trade endpoint without authentication."""
        response = client.post('/api/spot/trade', json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.001
        })
        assert response.status_code == 401

    def test_spot_trade_success(self, client, mock_context, login_as):
        """Test successful spot trade execution."""
        login_as()
        response = client.post('/api/spot/trade', json={
            "symbol": "BTC",
            "side": "BUY",
            "quantity": 0.001,
            "price": 50000.0,
            "signal_source": "manual",
            "confidence_score": 0.9
        })
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "message" in data
        assert "executed successfully" in data["message"]
        assert data["symbol"] == "BTCUSDT"  # Should add USDT suffix
        assert data["side"] == "BUY"
        assert data["quantity"] == 0.001

        # Check that record_user_trade was called
        mock_context["record_user_trade"].assert_called_once()

    def test_spot_trade_missing_symbol(self, client, mock_context, login_as):
        """Test spot trade with missing symbol."""
        login_as()
        response = client.post('/api/spot/trade', json={
                "side": "BUY",
                "quantity": 0.001
            })
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Symbol, side, and quantity are required" in data["error"]

    def test_spot_trade_invalid_side(self, client, mock_context, login_as):
        """Test spot trade with invalid side."""
        login_as()
        response = client.post('/api/spot/trade', json={
                "symbol": "BTCUSDT",
                "side": "INVALID",
                "quantity": 0.001
            })
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Side must be BUY or SELL" in data["error"]

    def test_spot_trade_execution_failure(self, client, mock_context, login_as):
        """Test spot trade with execution failure."""
        # Make user trader fail
        mock_context["get_user_trader"] = lambda user_id, profile: MockUserTrader(success=False)

        login_as()
        response = client.post('/api/spot/trade', json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.001
            })
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Trade execution failed" in data["error"]


class TestFuturesTrade:
    """Test cases for futures trade execution endpoint."""

    def test_futures_trade_unauthenticated(self, client):
        """Test futures trade endpoint without authentication."""
        response = client.post('/api/futures/trade', json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.001,
            "leverage": 5
        })
        assert response.status_code == 401

    def test_futures_trade_success(self, client, mock_context, login_as):
        """Test successful futures trade execution."""
        login_as()
        response = client.post('/api/futures/trade', json={
                "symbol": "BTC",
                "side": "SELL",
                "quantity": 0.001,
                "leverage": 10,
                "price": 50000.0,
                "signal_source": "manual",
                "confidence_score": 0.8
            })
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "message" in data
        assert "executed successfully" in data["message"]
        assert data["symbol"] == "BTCUSDT"  # Should add USDT suffix
        assert data["side"] == "SELL"
        assert data["quantity"] == 0.001
        assert data["leverage"] == 10

        # Check that record_user_trade was called
        mock_context["record_user_trade"].assert_called_once()

    def test_futures_trade_missing_parameters(self, client, mock_context, login_as):
        """Test futures trade with missing required parameters."""
        login_as()
        response = client.post('/api/futures/trade', json={
                "symbol": "BTCUSDT",
                "side": "BUY"
                # Missing quantity
            })
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Symbol, side, and quantity are required" in data["error"]

    def test_futures_trade_execution_failure(self, client, mock_context, login_as):
        """Test futures trade with execution failure."""
        # Make user trader fail
        mock_context["get_user_trader"] = lambda user_id, profile: MockUserTrader(success=False)

        login_as()
        response = client.post('/api/futures/trade', json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.001,
                "leverage": 5
            })
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "Futures trade execution failed" in data["error"]


class TestBinanceCredentials:
    """Test cases for Binance credentials endpoint."""

    def test_binance_credentials_get_unauthenticated(self, client):
        """Test Binance credentials GET without authentication."""
        response = client.get('/api/binance/credentials')
        assert response.status_code == 401

    def test_binance_credentials_get_success(self, client, mock_context, login_as):
        """Test successful Binance credentials GET."""
        login_as()
        response = client.get('/api/binance/credentials')
        assert response.status_code == 200

        data = json.loads(response.data)
        # Should return status from get_binance_credential_status
        assert isinstance(data, dict)


class TestBinanceLogs:
    """Test cases for Binance logs endpoint."""

    def test_binance_logs_success(self, client, mock_context):
        """Test successful Binance logs retrieval."""
        # Mock binance_log_manager
        mock_log_manager = MagicMock()
        mock_log_manager.get_logs.return_value = [
            {"message": "Test log", "severity": "info"}
        ]
        mock_context["binance_log_manager"] = mock_log_manager

        response = client.get('/api/binance/logs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "logs" in data
        assert "count" in data
        assert data["count"] == 1
        assert len(data["logs"]) == 1

    def test_binance_logs_no_manager(self, client, mock_context):
        """Test Binance logs when manager is not available."""
        mock_context["binance_log_manager"] = None

        response = client.get('/api/binance/logs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["logs"] == []
        assert data["count"] == 0


class TestFuturesDashboard:
    """Test cases for futures dashboard endpoint."""

    def test_futures_dashboard_success(self, client, mock_context, login_as):
        """Test successful futures dashboard retrieval."""
        # Mock futures data lock
        mock_lock = MagicMock()
        mock_context["futures_data_lock"] = mock_lock
        mock_context["dashboard_data"]["futures_dashboard"] = {
            "positions": [],
            "balance": 1000.0
        }

        # Provide a callable to satisfy `ensure_manual_defaults` requirement
        mock_context["ensure_futures_manual_defaults"] = lambda update_dashboard=False: {}

        # This endpoint requires authentication
        login_as()
        response = client.get('/api/futures')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "timestamp" in data
        assert "positions" in data
        assert "balance" in data

    def test_futures_dashboard_unavailable(self, client, mock_context):
        """Test futures dashboard when services unavailable."""
        mock_context["futures_data_lock"] = None

        response = client.get('/api/futures')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data
        assert "Futures data unavailable" in data["error"]