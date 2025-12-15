"""Application route blueprints."""
from .admin_analytics import admin_analytics_bp  # noqa: F401
from .admin_users import admin_users_bp  # noqa: F401
from .auth import auth_bp  # noqa: F401
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
from .admin_user_api import admin_user_api_bp  # noqa: F401

__all__ = [
    "admin_analytics_bp",
    "admin_users_bp",
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
    "admin_user_api_bp",
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
    user_api_bp,
    backtest_bp,
    marketing_bp,
    leads_bp,
    admin_views_bp,
    admin_dashboard_bp,
    admin_user_api_bp,
)


def register_blueprints(app):
    """Attach all application blueprints to the provided Flask app."""
    for blueprint in ROUTE_BLUEPRINTS:
        app.register_blueprint(blueprint)
