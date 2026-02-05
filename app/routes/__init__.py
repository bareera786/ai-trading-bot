"""Application route blueprints."""
from .admin_analytics import admin_analytics_bp  # noqa: F401
from .admin_users import admin_users_bp  # noqa: F401
from .admin_api import admin_api_bp  # noqa: F401
from .admin_protection import admin_protection_bp  # noqa: F401
from .api_endpoints import api_endpoints_bp  # noqa: F401
from .auth import auth_bp #, auth_api_bp, legacy_auth_bp  # noqa: F401
from .backtest import backtest_bp  # noqa: F401
from .dashboard import dashboard_bp  # noqa: F401
from .metrics import metrics_bp  # noqa: F401
from .realtime import realtime_bp  # noqa: F401
from .status import status_bp  # noqa: F401
from .ribs_progress import ribs_progress_bp  # noqa: F401
from .strategies import strategies_bp  # noqa: F401
from .subscriptions import subscription_bp  # noqa: F401
from .system_ops import system_ops_bp  # noqa: F401
from .trading import trading_bp  # noqa: F401
from .user_api import user_api_bp  # noqa: F401
from .marketing import marketing_bp  # noqa: F401
from .leads import leads_bp  # noqa: F401
from .admin_views import admin_views_bp  # noqa: F401
from .admin_dashboard import admin_dashboard_bp  # noqa: F401
from .admin_resellers import admin_resellers_bp # noqa: F401
from .reseller import reseller_bp # noqa: F401
from .marketplace import marketplace_bp # noqa: F401
from .exchange import exchange_bp # noqa: F401
from .notifications import notifications_bp # noqa: F401
from .risk_presets import risk_presets_bp # noqa: F401
from .analytics import analytics_bp # noqa: F401
from .trade_journal import trade_journal_bp # noqa: F401
from .onboarding import onboarding_bp # noqa: F401
from .two_factor import two_factor_bp # noqa: F401
from .arbitrage import arbitrage_bp # noqa: F401
from .admin_audit import admin_audit_bp # noqa: F401
from .copy_trading import copy_trading_bp # noqa: F401
from .brain import brain_bp # noqa: F401
from app.models import requires_role, requires_any_role

__all__ = [
    "admin_analytics_bp",
    "admin_users_bp",
    "admin_protection_bp",
    "api_endpoints_bp",
    "auth_bp",
    "backtest_bp",
    "dashboard_bp",
    "metrics_bp",
    "realtime_bp",
    "status_bp",
    "strategies_bp",
    "subscription_bp",
    "system_ops_bp",
    "trading_bp",
    "user_api_bp",
    "marketing_bp",
    "leads_bp",
    "admin_views_bp",
    "admin_dashboard_bp",
    "register_blueprints",
]


ROUTE_BLUEPRINTS = (
    auth_bp,
    dashboard_bp,
    metrics_bp,
    trading_bp,
    system_ops_bp,
    subscription_bp,
    realtime_bp,
    strategies_bp,
    status_bp,
    ribs_progress_bp,
    admin_users_bp,
    admin_analytics_bp,
    admin_protection_bp,
    api_endpoints_bp,
    user_api_bp,
    backtest_bp,
    marketing_bp,
    leads_bp,
    admin_views_bp,
    admin_dashboard_bp,
    admin_resellers_bp,
    admin_api_bp,
    # auth_api_bp,
    # legacy_auth_bp,
    reseller_bp,
    marketplace_bp,
    exchange_bp,
    notifications_bp,
    risk_presets_bp,
    analytics_bp,
    trade_journal_bp,
    onboarding_bp,
    two_factor_bp,
    arbitrage_bp,
    admin_audit_bp,
    copy_trading_bp,
    brain_bp,
)


def register_blueprints(app):
    """Attach all application blueprints to the provided Flask app."""
    for blueprint in ROUTE_BLUEPRINTS:
        app.register_blueprint(blueprint)
