from __future__ import annotations
import logging
from app.extensions import db
from app.models import Strategy
from app.services.brain_service import BrainService

logger = logging.getLogger("ai_trading_bot")

class StrategyHealthService:
    """
    Monitors strategy health and triggers auto-containment (Circuit Breaker).
    """
    
    # Circuit Breaker Limits (Can be moved to DB/Config)
    MAX_CONSECUTIVE_LOSSES = 3
    
    @staticmethod
    def record_trade_result(strategy_id: int, pnl: float):
        """
        Update strategy health based on closed trade PnL.
        Triggers pause if limits breached.
        """
        strategy = Strategy.query.get(strategy_id)
        if not strategy:
            return

        if strategy.status != "active":
            return # Already paused or inactive

        if pnl < 0:
            # Loss
            strategy.consecutive_losses += 1
            logger.info(f"📉 Strategy {strategy.name} Loss recorded. Consecutive: {strategy.consecutive_losses}")
        else:
            # Win
            if strategy.consecutive_losses > 0:
                logger.info(f"📈 Strategy {strategy.name} Win recorded. Resetting consecutive losses.")
            strategy.consecutive_losses = 0
            
        # Check Limits
        if strategy.consecutive_losses >= StrategyHealthService.MAX_CONSECUTIVE_LOSSES:
            logger.warning(f"🛑 CIRCUIT BREAKER: Strategy {strategy.name} hit {strategy.consecutive_losses} consecutive losses.")
            BrainService.pause_strategy(strategy.id, reason="consecutive_losses")
            
        # Drawdown check would go here (requires equity snapshotting)
        
        db.session.commit()

    @staticmethod
    def reset_health(strategy_id: int):
        """Manually reset health counters (Admin action)."""
        strategy = Strategy.query.get(strategy_id)
        if strategy:
            strategy.consecutive_losses = 0
            strategy.current_drawdown = 0.0
            if strategy.status == "paused_risk":
                 strategy.status = "active"
            db.session.commit()
