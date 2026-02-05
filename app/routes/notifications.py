"""
Notification API Routes
Handles notification preferences and sending test notifications
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.services.notifications import notification_service, NotificationType
from app.models import db
import logging

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """Get user notification preferences"""
    try:
        # TODO: Get from database
        # For now, return defaults
        preferences = {
            "telegram_enabled": False,
            "telegram_chat_id": "",
            "discord_enabled": False,
            "email_enabled": True,
            "email": current_user.email if hasattr(current_user, 'email') else "",
            "notify_on_trade": True,
            "notify_on_error": True,
            "notify_on_profit": True,
            "notify_on_loss": True
        }
        
        return jsonify({
            "success": True,
            "preferences": preferences
        })
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@notifications_bp.route('/preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update user notification preferences"""
    try:
        data = request.get_json()
        
        # TODO: Save to database
        # For now, just validate and return success
        
        required_fields = [
            "telegram_enabled", "discord_enabled", "email_enabled",
            "notify_on_trade", "notify_on_error", "notify_on_profit", "notify_on_loss"
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing field: {field}"
                }), 400
        
        logger.info(f"Updated notification preferences for user {current_user.id}")
        
        return jsonify({
            "success": True,
            "message": "Preferences updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@notifications_bp.route('/test/<channel>', methods=['POST'])
@login_required
def send_test_notification(channel):
    """Send test notification to specific channel"""
    try:
        # Get user preferences
        # TODO: Get from database
        preferences = {
            "telegram_enabled": True,
            "telegram_chat_id": request.json.get("telegram_chat_id", ""),
            "discord_enabled": True,
            "email_enabled": True,
            "email": current_user.email if hasattr(current_user, 'email') else "",
        }
        
        test_trade_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 42350.00,
            "amount": 0.05,
            "strategy": "ML-Based",
            "confidence": 0.78,
            "pnl_24h": 127.50
        }
        
        if channel == "telegram":
            if not preferences.get("telegram_chat_id"):
                return jsonify({
                    "success": False,
                    "error": "Telegram chat ID not configured"
                }), 400
            
            result = notification_service.send_trade_notification(
                current_user.id,
                test_trade_data,
                preferences
            )
            
            return jsonify({
                "success": result.get("telegram", False),
                "message": "Test notification sent" if result.get("telegram") else "Failed to send"
            })
        
        elif channel == "discord":
            result = notification_service.send_trade_notification(
                current_user.id,
                test_trade_data,
                preferences
            )
            
            return jsonify({
                "success": result.get("discord", False),
                "message": "Test notification sent" if result.get("discord") else "Failed to send"
            })
        
        elif channel == "email":
            result = notification_service.send_trade_notification(
                current_user.id,
                test_trade_data,
                preferences
            )
            
            return jsonify({
                "success": result.get("email", False),
                "message": "Test notification sent" if result.get("email") else "Failed to send"
            })
        
        else:
            return jsonify({
                "success": False,
                "error": f"Unknown channel: {channel}"
            }), 400
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@notifications_bp.route('/in-app', methods=['GET'])
@login_required
def get_in_app_notifications():
    """Get in-app notifications for current user"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications = notification_service.get_in_app_notifications(
            current_user.id,
            unread_only=unread_only
        )
        
        return jsonify({
            "success": True,
            "notifications": notifications,
            "count": len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error getting in-app notifications: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@notifications_bp.route('/in-app/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        success = notification_service.mark_as_read(notification_id)
        
        return jsonify({
            "success": success,
            "message": "Notification marked as read" if success else "Notification not found"
        })
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@notifications_bp.route('/telegram/register', methods=['POST'])
@login_required
def register_telegram():
    """Register Telegram chat ID for user"""
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return jsonify({
                "success": False,
                "error": "Chat ID is required"
            }), 400
        
        # TODO: Save to database
        logger.info(f"Registered Telegram chat ID {chat_id} for user {current_user.id}")
        
        return jsonify({
            "success": True,
            "message": "Telegram registered successfully"
        })
        
    except Exception as e:
        logger.error(f"Error registering Telegram: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
