"""
Admin Protection Routes

Provides admin endpoints for managing kill switches, user bans, and safety controls.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.protection import ProtectionService
from app.models import requires_role
from app.extensions import db
from app.models import User, UserPortfolio, AuditLog
from datetime import datetime
import logging

logger = logging.getLogger("ai_trading_bot")

admin_protection_bp = Blueprint('admin_protection', __name__, url_prefix='/admin/protection')

@admin_protection_bp.route('/kill-switch/status', methods=['GET'])
@login_required
@requires_role('admin')
def get_kill_switch_status():
    """Get current kill switch status."""
    try:
        is_active = ProtectionService.is_kill_switch_active()
        return jsonify({
            'success': True,
            'active': is_active,
            'status': 'BLOCKED' if is_active else 'ALLOWED'
        })
    except Exception as e:
        logger.error(f"Error getting kill switch status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/kill-switch/set', methods=['POST'])
@login_required
@requires_role('admin')
def set_kill_switch():
    """Set global kill switch."""
    try:
        data = request.get_json()
        active = data.get('active', False)
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({'success': False, 'error': 'Reason is required'}), 400
        
        result = ProtectionService.set_kill_switch(
            active=active,
            user_id=str(current_user.id),
            reason=reason
        )
        
        return jsonify({
            'success': True,
            'active': result,
            'message': f"Kill switch {'activated' if result else 'deactivated'} successfully"
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error setting kill switch: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/user/<user_id>/pause', methods=['POST'])
@login_required
@requires_role('admin')
def pause_user_trading(user_id):
    """Pause trading for a specific user."""
    try:
        data = request.get_json()
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({'success': False, 'error': 'Reason is required'}), 400
        
        result = ProtectionService.pause_user_trading(
            target_user_id=user_id,
            admin_user_id=str(current_user.id),
            reason=reason
        )
        
        return jsonify({
            'success': True,
            'message': f"Trading paused for user {user_id}"
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error pausing user trading: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/user/<user_id>/resume', methods=['POST'])
@login_required
@requires_role('admin')
def resume_user_trading(user_id):
    """Resume trading for a specific user."""
    try:
        data = request.get_json()
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({'success': False, 'error': 'Reason is required'}), 400
        
        result = ProtectionService.resume_user_trading(
            target_user_id=user_id,
            admin_user_id=str(current_user.id),
            reason=reason
        )
        
        return jsonify({
            'success': True,
            'message': f"Trading resumed for user {user_id}"
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error resuming user trading: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/user/<user_id>/status', methods=['GET'])
@login_required
@requires_role('admin')
def get_user_trading_status(user_id):
    """Get trading status for a specific user."""
    try:
        is_paused = ProtectionService.is_user_trading_paused(user_id)
        can_trade, reason = ProtectionService.can_user_trade(user_id)
        
        # Get user's open positions
        open_positions = UserPortfolio.query.filter_by(user_id=user_id).filter(
            UserPortfolio.quantity > 0
        ).all()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'is_paused': is_paused,
            'can_trade': can_trade,
            'reason': reason,
            'open_positions': len(open_positions),
            'positions': [
                {
                    'symbol': p.symbol,
                    'quantity': float(p.quantity) if p.quantity else 0,
                    'pnl': float(p.pnl) if p.pnl else 0
                }
                for p in open_positions
            ]
        })
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/user/<user_id>/ban', methods=['POST'])
@login_required
@requires_role('admin')
def ban_user(user_id):
    """Ban a user (safely checks for open positions)."""
    try:
        data = request.get_json()
        reason = data.get('reason', '')
        force = data.get('force', False)
        
        if not reason:
            return jsonify({'success': False, 'error': 'Reason is required'}), 400
        
        success, message = ProtectionService.safe_ban_user(
            target_user_id=user_id,
            admin_user_id=str(current_user.id),
            reason=reason,
            force=force
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/audit-log', methods=['GET'])
@login_required
@requires_role('admin')
def get_audit_log():
    """Get recent audit log entries."""
    try:
        limit = request.args.get('limit', 50, type=int)
        action_filter = request.args.get('action', None)
        
        query = AuditLog.query.order_by(AuditLog.timestamp.desc())
        
        if action_filter:
            query = query.filter(AuditLog.action.like(f'%{action_filter}%'))
        
        logs = query.limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'logs': [
                {
                    'id': log.id,
                    'user_id': str(log.user_id),
                    'action': log.action,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'details': log.details
                }
                for log in logs
            ]
        })
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_protection_bp.route('/limits/check/<user_id>', methods=['GET'])
@login_required
@requires_role('admin')
def check_user_limits(user_id):
    """Check if user is within position and loss limits."""
    try:
        # Check loss limits
        loss_ok, loss_reason = ProtectionService.check_loss_limits(user_id)
        
        # Get portfolio summary
        portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'loss_limits': {
                'ok': loss_ok,
                'reason': loss_reason,
                'daily_pnl': float(portfolio.daily_pnl) if portfolio and portfolio.daily_pnl else 0,
                'total_balance': float(portfolio.total_balance) if portfolio and portfolio.total_balance else 0
            }
        })
    except Exception as e:
        logger.error(f"Error checking user limits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
