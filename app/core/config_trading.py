import os
import logging
from app.runtime.indicators import BEST_INDICATORS
from app.runtime.symbols import BINANCE_MIN_NOTIONAL_OVERRIDES
from app.core.logging import log_component_event

# ==================== ULTIMATE CONFIGURATION ====================
TRADING_CONFIG = {
    "confidence_threshold": 0.35,  # REVERTED: Lowered values were too risky
    "max_positions": 3,  # REVERTED: Decreased from 5 to reduce exposure
    "take_profit": 0.08,
    "stop_loss": 0.015,  # AGGRESSIVE: Tightened for protection
    "min_confidence_diff": 0.10,  # REVERTED: Require stronger signals
    "risk_per_trade": 0.01,
    "max_position_size": 0.05,  # REVERTED: Decreased from 0.08
    "use_ensemble": False,  # DISABLED: Reverting to legacy direct strategy signals
    "ensemble_min_agreement": 0.75,
    "correlation_threshold": 0.6,
    "market_regime_aware": True,
    "dynamic_position_sizing": False,  # DISABLED: Using fixed sizing for stability
    "parallel_processing": True,
    "advanced_stop_loss": True,
    "periodic_rebuilding": False,  # DISABLED: Prevent automated logic changes
    "adaptive_risk_management": False,  # DISABLED: Reverting to static risk
    "auto_trade_enabled": True,  # CRITICAL: Master switch for Strategy Worker
    "continuous_training": False,  # DEPRECATED: Use BrainService/RQ for training
    "optimized_indicators": BEST_INDICATORS,
    "dynamic_threshold_floor": 0.3,  # REVERTED: Increased floor
    "dynamic_threshold_ceiling": 0.8,  # REVERTED: Decreased ceiling
    "default_min_notional": 10.0,
    "min_notional_buffer": 1.1,
    "min_notional_overrides": BINANCE_MIN_NOTIONAL_OVERRIDES.copy(),
    "balance_cash_buffer": 1.01,
    "auto_take_profit_percent": 0.05,
    "auto_take_profit_time_in_force": "GTC",
    "auto_take_profit_adjust_interval": 30,
    "auto_take_profit_reprice_threshold": 0.002,
    "auto_take_profit_spread_margin": 0.0005,
    # RIBS Quality Diversity Optimization
    "enable_ribs_optimization": False,  # DISABLED per CLAW_BOT emergency
    "ribs_optimization_interval_hours": 6,
    "ribs_iterations_per_cycle": 200,
    "ribs_max_elite_strategies": 5,
    "ribs_auto_deploy_elites": False,  # DISABLED
    "ribs_checkpoint_interval": 50,
    # Optional: when True, automated/system trades will also be recorded to
    # the database table `user_trade` using `record_user_trade`.
    "record_system_trades_to_db": True,
    # Set `system_trade_user_id` to the user id that should own those trades.
    "system_trade_user_id": None,
}

OPTIMIZED_TRADING_CONFIG = {
    "confidence_threshold": 0.40,  # REVERTED: Stricter gate for legacy mode
    "max_positions": 3,
    "take_profit": 0.05,
    "stop_loss": 0.015,
    "min_confidence_diff": 0.10,
    "risk_per_trade": 0.01,
    "max_position_size": 0.05,
    "use_ensemble": False,
    "ensemble_min_agreement": 0.75,
    "optimized_indicators": BEST_INDICATORS,
    "market_regime_aware": True,
    "dynamic_position_sizing": False,
    "parallel_processing": True,
    "advanced_stop_loss": True,
    "periodic_rebuilding": False,
    "adaptive_risk_management": False,
    "continuous_training": False,
    "futures_enabled": True,
    "futures_initial_balance": 1000,
    "futures_max_leverage": 5,  # REVERTED: Decreased from 10
    "futures_default_leverage": 2,  # REVERTED: Decreased from 3
    "futures_risk_mode": "conservative",
    "futures_update_interval": 30,
    "futures_signal_weight": 0.2,
    "futures_manual_mode": True,
    "futures_selected_symbol": "BTCUSDT",
    "futures_manual_auto_trade": False,
    "futures_manual_leverage": 2,
    "futures_manual_default_notional": 20.0,  # REVERTED: Decreased from 50.0

    # -----------------------------------------------------------------
    # Futures safety defaults (conservative; designed for unattended VPS)
    # -----------------------------------------------------------------
    "futures_safety_min_atr_pct": 0.15,
    "futures_safety_min_adx": 20.0,

    # Rolling 24h backtest gate (5m): must show edge after fees.
    "futures_safety_backtest_refresh_minutes": 5,
    "futures_safety_min_win_rate_pct": 60.0,  # REVERTED: Increased from 55%
    "futures_safety_min_profit_factor": 1.3,  # REVERTED: Increased from 1.15
    "futures_safety_min_backtest_trades": 12,  # REVERTED: Increased from 8

    # Symbol hard-stops (UTC day): stop trading when conditions degrade.
    "futures_safety_max_trades_per_day": 2,  # REVERTED: Decreased from 4
    "futures_safety_max_daily_loss_usdt": 10.0,  # REVERTED: Decreased from 20
    "futures_safety_max_consecutive_losses": 1,  # REVERTED: Decreased from 2
    "dynamic_threshold_floor": 0.35,
    "dynamic_threshold_ceiling": 0.85,
    "default_min_notional": 10.0,
    "min_notional_buffer": 1.1,
    "min_notional_overrides": BINANCE_MIN_NOTIONAL_OVERRIDES.copy(),
    "balance_cash_buffer": 1.01,
    "auto_take_profit_percent": 0.05,
    "auto_take_profit_time_in_force": "GTC",
    "auto_take_profit_adjust_interval": 30,
    "auto_take_profit_reprice_threshold": 0.002,
    "auto_take_profit_spread_margin": 0.0005,
}

TRADING_CONFIG.update(OPTIMIZED_TRADING_CONFIG)

# Override configuration from environment variables
TRADING_CONFIG["futures_enabled"] = os.getenv(
    "ENABLE_FUTURES_TRADING", "1"
).lower() in ("1", "true", "yes")
TRADING_CONFIG["auto_trade_enabled"] = os.getenv(
    "ENABLE_AUTO_TRADING", "1"
).lower() in ("1", "true", "yes")
TRADING_CONFIG["enable_ribs_optimization"] = os.getenv(
    "ENABLE_RIBS_OPTIMIZATION", "1"
).lower() in ("1", "true", "yes")
TRADING_CONFIG["futures_manual_auto_trade"] = os.getenv(
    "ENABLE_AUTO_TRADING", "1"
).lower() in ("1", "true", "yes")

# Allow enabling system trade DB recording via environment variables
if os.getenv("RECORD_SYSTEM_TRADES_TO_DB") is not None:
    TRADING_CONFIG["record_system_trades_to_db"] = (
        os.getenv("RECORD_SYSTEM_TRADES_TO_DB") or ""
    ).lower() in ("1", "true", "yes")

if os.getenv("SYSTEM_TRADE_USER_ID"):
    try:
        system_user_id = os.getenv("SYSTEM_TRADE_USER_ID")
        if system_user_id is not None:
            TRADING_CONFIG["system_trade_user_id"] = int(system_user_id)
    except Exception:
        system_user_id = os.getenv("SYSTEM_TRADE_USER_ID")
        TRADING_CONFIG["system_trade_user_id"] = system_user_id

# Log the effective system trade recording configuration at startup so it's
# easy to find in service logs during deployments and debugging.
try:
    log_component_event(
        "STARTUP",
        f"TRADING_CONFIG.record_system_trades_to_db={TRADING_CONFIG.get('record_system_trades_to_db')} SYSTEM_TRADE_USER_ID={TRADING_CONFIG.get('system_trade_user_id')}",
        level=logging.INFO,
    )
except Exception:
    # Best-effort logging; do not crash startup for logging failures
    pass
