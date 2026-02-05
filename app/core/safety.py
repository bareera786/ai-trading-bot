import threading
from datetime import datetime
from collections import defaultdict
from app.models import UserPortfolio, db

class SafetyManager:
    def __init__(
        self,
        initial_balance=0,
        max_daily_loss=0.10,
        max_position_size=0.15,
        max_consecutive_losses=3,
        volatility_threshold=0.08,
        api_failure_limit=5,
        breaker_cooldown_minutes=60,
        global_breaker_minutes=120,
    ):
        self.initial_balance = initial_balance
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.max_consecutive_losses = max_consecutive_losses
        self.volatility_threshold = volatility_threshold
        self.api_failure_limit = api_failure_limit
        self.breaker_cooldown_minutes = breaker_cooldown_minutes
        self.global_breaker_minutes = global_breaker_minutes

        self.daily_loss = 0.0
        self.daily_profit = 0.0
        self.symbol_loss_streak = defaultdict(int)
        self.circuit_breakers = {}
        self.api_failure_count = 0
        self.global_breaker_active = False
        self.global_breaker_reason = None
        self.global_breaker_release = None
        self.current_day = datetime.utcnow().date()
        self.start_of_day_balance = initial_balance
        self.lock = threading.RLock()

    def _reset_daily_if_needed(self, current_balance):
        today = datetime.utcnow().date()
        if today != self.current_day:
            self.current_day = today
            self.daily_loss = 0.0
            self.daily_profit = 0.0
            self.api_failure_count = 0
            self.symbol_loss_streak.clear()
            self.circuit_breakers.clear()
            self.start_of_day_balance = current_balance

            # Reset UserPortfolio daily_pnl for all users
            try:
                UserPortfolio.query.update({"daily_pnl": 0.0})
                db.session.commit()
                print(f"📊 Daily portfolio metrics reset for all users on {today}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to reset UserPortfolio daily_pnl: {e}")
                db.session.rollback()

    def _cleanup_breakers(self):
        if not self.circuit_breakers:
            return
        now = datetime.utcnow()
        expired = [
            symbol
            for symbol, info in self.circuit_breakers.items()
            if info.get("release_timestamp")
            and now.timestamp() >= info["release_timestamp"]
        ]
        for symbol in expired:
            self.circuit_breakers.pop(symbol, None)

        if self.global_breaker_active and self.global_breaker_release:
            if now.timestamp() >= self.global_breaker_release:
                self.global_breaker_active = False
                self.global_breaker_reason = None
                self.global_breaker_release = None

    def approve_trade(
        self,
        symbol,
        position_value,
        available_balance,
        market_stress=0.0,
        volatility=0.0,
        portfolio_health=1.0,
    ):
        with self.lock:
            self._reset_daily_if_needed(available_balance + position_value)
            self._cleanup_breakers()

            if self.global_breaker_active:
                return (
                    False,
                    f"Global circuit breaker active: {self.global_breaker_reason}",
                )

            breaker = self.circuit_breakers.get(symbol)
            if breaker:
                return (
                    False,
                    f"Circuit breaker active for {symbol}: {breaker.get('reason', 'cooldown')}",
                )

            max_position_allowed = available_balance * self.max_position_size
            if position_value > max_position_allowed:
                return (
                    False,
                    f"Position size ${position_value:.2f} exceeds limit ${max_position_allowed:.2f}",
                )

            max_loss_allowed = (
                self.start_of_day_balance * self.max_daily_loss
                if self.start_of_day_balance
                else available_balance * self.max_daily_loss
            )
            if abs(self.daily_loss) >= max_loss_allowed:
                return False, "Daily loss limit reached"

            if self.symbol_loss_streak[symbol] >= self.max_consecutive_losses:
                return False, f"Loss streak limit reached for {symbol}"

            if volatility > self.volatility_threshold and market_stress > 0.6:
                return False, "High volatility during stressed market"

            if portfolio_health < 0.5:
                return False, "Portfolio health too weak for new exposure"

            if self.api_failure_count >= self.api_failure_limit:
                return False, "API instability detected"

            return True, "approved"

    def register_trade_result(self, symbol, pnl):
        with self.lock:
            self.daily_loss += min(0.0, pnl)
            self.daily_profit += max(0.0, pnl)

            if pnl < 0:
                self.symbol_loss_streak[symbol] += 1
                if self.symbol_loss_streak[symbol] >= self.max_consecutive_losses:
                    self._activate_symbol_breaker(symbol, reason="loss_streak")
            else:
                self.symbol_loss_streak[symbol] = 0

    def _activate_symbol_breaker(self, symbol, reason="volatility"):
        expiry = datetime.utcnow().timestamp() + (self.breaker_cooldown_minutes * 60)
        self.circuit_breakers[symbol] = {
            "reason": reason,
            "release_timestamp": expiry,
            "timestamp": datetime.utcnow().timestamp(),
        }
        print(f"🔌 Circuit breaker activated for {symbol}: {reason}")

    def record_api_failure(self):
        with self.lock:
            self.api_failure_count += 1
            if self.api_failure_count >= self.api_failure_limit:
                self.global_breaker_active = True
                self.global_breaker_reason = "API Instability"
                self.global_breaker_release = (
                    datetime.utcnow().timestamp() + 300
                )  # 5 min cool off

    def get_status_snapshot(self):
        """Return a snapshot of the safety manager's current status."""
        with self.lock:
            return {
                "daily_loss": self.daily_loss,
                "daily_profit": self.daily_profit,
                "max_daily_loss": self.max_daily_loss,
                "api_failure_count": self.api_failure_count,
                "global_breaker_active": self.global_breaker_active,
                "global_breaker_reason": self.global_breaker_reason,
                "active_circuit_breakers": len(self.circuit_breakers),
                "portfolio_health": 1.0,  # Placeholder or calculated if available
            }
