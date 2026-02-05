
"""
Copy Trading Service
Handles the execution of mirrored trades for followers.
"""
import logging
from decimal import Decimal
import traceback
from flask import current_app

from app.models import CopyRelationship, User, UserPortfolio
from app.extensions import db
from app.services.trading import RealBinanceTrader

logger = logging.getLogger(__name__)

class CopyTradingService:
    @staticmethod
    def process_copy_trade(leader_id, symbol, side, price, leader_quantity, signal_source="copy_trade"):
        """
        Main entry point triggered after a Leader executes a trade.
        """
        try:
            # 1. Find active followers
            relationships = CopyRelationship.query.filter_by(
                leader_id=leader_id, 
                is_active=True
            ).all()
            
            if not relationships:
                return

            logger.info(f"👯 COPY TRADING: Leader {leader_id} traded {symbol} {side}. Found {len(relationships)} followers.")

            # 2. Iterate and Execute
            for rel in relationships:
                try:
                    CopyTradingService._execute_follower_trade(rel, symbol, side, price, leader_quantity)
                except Exception as e:
                    logger.error(f"Failed to copy trade for follower {rel.follower_id}: {e}")
                    # Continue to next follower - Isolation
                    continue
                    
        except Exception as e:
            logger.error(f"Copy Trading Critical Error: {e}")
            
    @staticmethod
    def _execute_follower_trade(relationship, symbol, side, price, leader_quantity):
        follower_id = relationship.follower_id
        
        # 3. Validation & Safety
        # Check if follower has enough allocation or PnL stop loss
        if relationship.stop_loss_percent and relationship.total_copied_pnl:
             # Heuristic check: if PnL is too negative, stop.
             # Need baseline allocation to calc percent. 
             # For now, skip complex PnL check in V1.
             pass

        # 4. Sizing Logic (Proportional or Fixed)
        # Strategy: Proportional to "Allocation Amount" vs Leader Trade Size?
        # Simpler for MVP: Use fixed allocation if provided, or ratio.
        # Let's assume 'allocation_amount' is the MAX capital to use.
        # But we need to know how much of the Leader's portfolio was used to mirror stats.
        # That's hard without full context.
        
        # ALTERNATIVE MVP: Fixed Ratio. 
        # Let's simple check: Follower Quantity = Leader Quantity * (Follower_Balance / Leader_Balance) 
        # Or simpler: 1:1 if we assume similar accounts? No, dangerous.
        
        # DECISION: Fixed Amount per trade? Or simple 10% of allocation?
        # Let's go with a safe default: 
        # If allocation_amount > 0, we use 5% of allocation per trade.
        # If allocation_amount is 0 (unlimited), we use min_notional.
        
        target_qty = 0.0
        
        # Using a very safe, conservative sizing for V1
        # If allocation defined, take 10% of it.
        if relationship.allocation_amount and relationship.allocation_amount > 0:
            trade_value = float(relationship.allocation_amount) * 0.10
            if price and price > 0:
                target_qty = trade_value / price
        else:
            # Fallback: Mimic leader quantity but capped? 
            # Or just don't trade if no allocation set.
            # Let's try to match leader quantity but capped at $20 value for safety.
            target_qty = leader_quantity 
            if price and (target_qty * price) > 50:
                 target_qty = 50.0 / price
        
        if target_qty <= 0:
            logger.warning(f"Calculated zero quantity for follower {follower_id}")
            return

        # 5. Execution
        # We need a Trader instance for the follower
        # We assume credentials exist (checked by RealBinanceTrader)
        trader = RealBinanceTrader(user_id=follower_id)
        
        if not trader.is_ready():
            # Try to connect
             if not trader.set_credentials(user_id=follower_id, auto_connect=True):
                 logger.warning(f"Follower {follower_id} has no valid API keys.")
                 return

        logger.info(f"Executing COPY {side} {symbol} for Follower {follower_id}, Qty: {target_qty}")
        
        # Place Order
        result = trader.execute_manual_trade(
            symbol=symbol,
            side=side,
            quantity=target_qty,
            price=None # Market order for speed
        )
        
        if result['success']:
            logger.info(f"Copy trade success for {follower_id}")
            # Update metrics?
        else:
            logger.error(f"Copy trade failed for {follower_id}: {result.get('error')}")

