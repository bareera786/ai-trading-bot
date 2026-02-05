"""
Enhanced Risk Management Service.

Centralized domain logic for trading risk, limit checks, and circuit breakers.
"""

from app.models import SystemSetting, AuditLog, UserPortfolio, User
from app.extensions import db
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger("ai_trading_bot")

class RiskManager:
    KILL_SWITCH_KEY = "global_kill_switch_active"
    USER_PAUSE_PREFIX = "user_pause_"
    
    @classmethod
    def is_kill_switch_active(cls) -> bool:
        """
        Check if the global kill switch is active.
        Returns True if trading should be BLOCKED.
        """
        try:
            val = SystemSetting.get_value(cls.KILL_SWITCH_KEY, default="false")
            return val.lower() == "true"
        except Exception as e:
            # FAIL SAFE: If DB is down, log error but allow trading to continue
            logger.error(
                "Failed to check kill switch status - defaulting to ALLOW trading. "
                "This is a CRITICAL error that needs immediate investigation.",
                exc_info=True,
                extra={"error": str(e)}
            )
            return False

    @classmethod
    def set_kill_switch(cls, active: bool, user_id=None, reason: str = None):
        """
        Enable or disable the global kill switch with full audit logging.
        """
        if user_id is None:
            raise ValueError(
                "user_id is REQUIRED when changing kill switch. "
                "All admin actions must be attributed to a specific user for audit compliance."
            )
        
        if reason is None or not reason.strip():
            raise ValueError(
                "reason is REQUIRED when changing kill switch. "
                "All admin actions must have a documented reason for audit compliance."
            )
        
        try:
            previous_state = cls.is_kill_switch_active()
        except Exception:
            previous_state = None
        
        SystemSetting.set_value(cls.KILL_SWITCH_KEY, str(active).lower(), user_id=user_id)
        
        action_verb = "ACTIVATED" if active else "DEACTIVATED"
        audit_details = {
            "previous_state": previous_state,
            "new_state": active,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        try:
            audit_entry = AuditLog(
                user_id=user_id,
                action=f"KILL_SWITCH_{action_verb}",
                timestamp=datetime.utcnow(),
                details=f"Kill switch {action_verb.lower()} by user {user_id}. Reason: {reason}. Previous: {previous_state}, New: {active}"
            )
            db.session.add(audit_entry)
            db.session.commit()
            
            logger.critical(
                "🚨 KILL SWITCH %s by user_id=%s | Reason: %s",
                action_verb,
                user_id,
                reason,
                extra=audit_details
            )
        except Exception as e:
            logger.error(
                "Failed to create audit log for kill switch change. "
                "Kill switch was changed but audit trail is incomplete!",
                exc_info=True,
                extra={"user_id": user_id, "active": active, "reason": reason}
            )
        
        return active
    
    @classmethod
    def is_user_trading_paused(cls, user_id: str) -> bool:
        try:
            key = f"{cls.USER_PAUSE_PREFIX}{user_id}"
            val = SystemSetting.get_value(key, default="false")
            return val.lower() == "true"
        except Exception as e:
            logger.error(
                f"Failed to check user pause status for user {user_id}",
                exc_info=True
            )
            return False
    
    @classmethod
    def pause_user_trading(cls, target_user_id: str, admin_user_id: str, reason: str):
        if not admin_user_id:
            raise ValueError("admin_user_id is REQUIRED for audit compliance")
        
        if not reason or not reason.strip():
            raise ValueError("reason is REQUIRED for audit compliance")
        
        key = f"{cls.USER_PAUSE_PREFIX}{target_user_id}"
        SystemSetting.set_value(key, "true", user_id=admin_user_id)
        
        try:
            audit_entry = AuditLog(
                user_id=admin_user_id,
                action="USER_TRADING_PAUSED",
                timestamp=datetime.utcnow(),
                details=f"Trading paused for user {target_user_id} by admin {admin_user_id}. Reason: {reason}"
            )
            db.session.add(audit_entry)
            db.session.commit()
            
            logger.warning(
                f"⏸️ User {target_user_id} trading PAUSED by admin {admin_user_id}. Reason: {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to log user trading pause: {e}")
        
        return True
    
    @classmethod
    def resume_user_trading(cls, target_user_id: str, admin_user_id: str, reason: str):
        if not admin_user_id:
            raise ValueError("admin_user_id is REQUIRED for audit compliance")
        
        if not reason or not reason.strip():
            raise ValueError("reason is REQUIRED for audit compliance")
        
        key = f"{cls.USER_PAUSE_PREFIX}{target_user_id}"
        SystemSetting.set_value(key, "false", user_id=admin_user_id)
        
        try:
            audit_entry = AuditLog(
                user_id=admin_user_id,
                action="USER_TRADING_RESUMED",
                timestamp=datetime.utcnow(),
                details=f"Trading resumed for user {target_user_id} by admin {admin_user_id}. Reason: {reason}"
            )
            db.session.add(audit_entry)
            db.session.commit()
            
            logger.info(
                f"▶️ User {target_user_id} trading RESUMED by admin {admin_user_id}. Reason: {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to log user trading resume: {e}")
        
        return True
    
    @classmethod
    def can_user_trade(cls, user_id: str) -> tuple[bool, str]:
        # Check global kill switch first
        if cls.is_kill_switch_active():
            return False, "Global trading is disabled by system administrator"
        
        # Check per-user pause
        if cls.is_user_trading_paused(user_id):
            return False, "Your trading has been paused. Please contact support."
        
        return True, "Trading allowed"
    
    @classmethod
    def check_position_limits(cls, user_id: str, symbol: str, quantity: Decimal) -> tuple[bool, str]:
        try:
            portfolio = UserPortfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
            
            if not portfolio:
                return True, "No position limits exceeded"
            
            # Check max position size
            max_size = portfolio.max_position_size or Decimal('1000.0')
            current_qty = portfolio.quantity or Decimal('0.0')
            new_total = current_qty + quantity
            
            if new_total > max_size:
                return False, f"Position limit exceeded. Max: {max_size}, Attempted: {new_total}"
            
            return True, "Position limits OK"
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return True, "Position check failed (allowed by default)"
    
    @classmethod
    def check_loss_limits(cls, user_id: str) -> tuple[bool, str]:
        try:
            portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
            
            if not portfolio:
                return True, "No loss limits configured"
            
            daily_pnl = portfolio.daily_pnl or Decimal('0.0')
            
            # Default max daily loss: 5% of total balance
            total_balance = portfolio.total_balance or Decimal('10000.0')
            max_daily_loss = total_balance * Decimal('0.05')
            
            if daily_pnl < -max_daily_loss:
                return False, f"Daily loss limit exceeded. Loss: {daily_pnl}, Limit: {max_daily_loss}"
            
            return True, "Loss limits OK"
            
        except Exception as e:
            logger.error(f"Error checking loss limits: {e}")
            return True, "Loss check failed (allowed by default)"
    
    @classmethod
    def safe_ban_user(cls, target_user_id: str, admin_user_id: str, reason: str, force: bool = False) -> tuple[bool, str]:
        if not admin_user_id:
            raise ValueError("admin_user_id is REQUIRED")
        
        if not reason or not reason.strip():
            raise ValueError("reason is REQUIRED")
        
        try:
            # Check for open positions
            open_positions = UserPortfolio.query.filter_by(user_id=target_user_id).filter(
                UserPortfolio.quantity > 0
            ).all()
            
            if open_positions and not force:
                symbols = [p.symbol for p in open_positions]
                return False, f"Cannot ban user with open positions: {', '.join(symbols)}. Close positions first or use force=True"
            
            # Pause trading first
            cls.pause_user_trading(target_user_id, admin_user_id, f"Pre-ban pause: {reason}")
            
            # Ban the user
            user = User.query.get(target_user_id)
            if user:
                user.is_active = False
                db.session.commit()
                
                # Create audit log
                audit_entry = AuditLog(
                    user_id=admin_user_id,
                    action="USER_BANNED",
                    timestamp=datetime.utcnow(),
                    details=f"User {target_user_id} banned by admin {admin_user_id}. Reason: {reason}. Force: {force}. Open positions: {len(open_positions)}"
                )
                db.session.add(audit_entry)
                db.session.commit()
                
                logger.critical(
                    f"🚫 User {target_user_id} BANNED by admin {admin_user_id}. Reason: {reason}"
                )
                
                return True, f"User banned successfully. Open positions: {len(open_positions)}"
            else:
                return False, "User not found"
                
        except Exception as e:
            logger.error(f"Error banning user: {e}", exc_info=True)
            return False, f"Ban failed: {str(e)}"
