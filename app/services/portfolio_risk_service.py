from __future__ import annotations
import logging
from app.extensions import db, redis_client
from app.models import Strategy, UserPortfolio, SystemSetting, MLModel

logger = logging.getLogger("ai_trading_bot")

class PortfolioRiskService:
    """
    The Capital Firewall. 
    Intercepts signals before publication to enforce portfolio-level safety.
    """
    
    # Hardcoded safety limits (can be moved to DB later)
    MAX_GLOBAL_LEVERAGE = 3.0
    MAX_STRATEGY_ALLOCATION = 0.40 # Max 40% of capital per strategy
    MAX_CORRELATED_POSITIONS = 3 # Max 3 open positions in same direction
    
    @staticmethod
    def validate_signal(symbol: str, side: str, metadata: dict) -> tuple[bool, str]:
        """
        Validate if a signal can be published.
        Returns: (is_allowed, reason)
        """
        try:
            # 1. Global Kill Switch (Redundant but safe)
            if redis_client and redis_client.get("brain:signals:paused") == b"1":
                 return False, "Global Kill Switch Active"

            # 2. Strategy Check
            strategy_id = metadata.get("strategy_id")
            if strategy_id:
                strategy = Strategy.query.get(strategy_id)
                if not strategy:
                    return False, f"Strategy {strategy_id} not found"
                if strategy.status != "active":
                    return False, f"Strategy {strategy.name} is {strategy.status}"
            else:
                # Legacy model (no strategy) -> Treat as "Legacy Strategy"
                # Check if we have too many legacy positions?
                pass
                
            # 3. Portfolio & Strategy Exposure Check
            # We approximate Master Portfolio exposure by looking at the primary Admin portfolio
            # In a real fund, this would aggregate all sub-accounts.
            admin_portfolio = UserPortfolio.query.first() # Simplified for single-tenant/admin bot
            
            if admin_portfolio:
                total_equity = float(admin_portfolio.total_balance or 10000)
                current_global_exposure = PortfolioRiskService._calculate_exposure(admin_portfolio)
                
                # Check Global Max Leverage
                if current_global_exposure / total_equity > PortfolioRiskService.MAX_GLOBAL_LEVERAGE:
                     return False, f"Max Global Leverage Exceeded ({PortfolioRiskService.MAX_GLOBAL_LEVERAGE}x)"
                
                # Check Strategy Allocation (Phase 5.3)
                if strategy_id:
                     strategy_weight = float(strategy.capital_weight or 0.0)
                     current_strat_exposure = PortfolioRiskService._calculate_strategy_exposure(admin_portfolio, strategy_id)
                     
                     # Estimate new trade value (simplified: 10% of equity for now, or per config)
                     # ideally we know position size from signal metadata or position sizing service
                     # FOR NOW: Assume 5% of equity per trade
                     estimated_trade_val = total_equity * 0.05 
                     
                     if (current_strat_exposure + estimated_trade_val) > (total_equity * strategy_weight):
                          return False, f"Strategy Allocation Limit Reached ({strategy_weight*100}%)"

                # Check Directional Correlation (Naive)
                # Count open positions with same logic
                same_side_count = 0
                positions = admin_portfolio.open_positions or {}
                for sym, pos in positions.items():
                    if pos.get("side") == side:
                        same_side_count += 1
                
                if same_side_count >= PortfolioRiskService.MAX_CORRELATED_POSITIONS:
                    return False, f"Max Correlated Positions Limit ({PortfolioRiskService.MAX_CORRELATED_POSITIONS})"

            return True, "Allowed"

        except Exception as e:
            logger.error(f"Risk Check Failed: {e}")
            # FAIL SAFE: Block if we can't verify
            return False, f"Risk Validation Error: {e}"

    @staticmethod
    def _calculate_exposure(portfolio) -> float:
        """Sum of absolute value of all position sizes."""
        exposure = 0.0
        positions = portfolio.open_positions or {}
        for sym, pos in positions.items():
             try:
                 qty = float(pos.get("quantity", 0))
                 price = float(pos.get("current_price", 0))
                 if price == 0: price = float(pos.get("entry_price", 0))
                 exposure += abs(qty * price)
             except:
                 pass
        return exposure

    @staticmethod
    def _calculate_strategy_exposure(portfolio, strategy_id) -> float:
        """Sum of positions belonging to a specific strategy."""
        exposure = 0.0
        positions = portfolio.open_positions or {}
        # strategy_id should be stored in position metadata
        # Assuming position dict has 'strategy_id' or 'signal_source'
        # For MVP, we might rely on signal metadata being persisted to position
        for sym, pos in positions.items():
             try:
                 # Check if position belongs to strategy
                 # If 'strategy' field exists in pos matches strategy name or ID
                 pos_strat = pos.get("strategy_id")
                 if pos_strat and str(pos_strat) == str(strategy_id):
                     qty = float(pos.get("quantity", 0))
                     price = float(pos.get("current_price", 0))
                     if price == 0: price = float(pos.get("entry_price", 0))
                     exposure += abs(qty * price)
             except:
                 pass
        return exposure
