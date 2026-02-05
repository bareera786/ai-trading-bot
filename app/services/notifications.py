"""
Notification Service for AI Trading Bot
Supports: Telegram, Discord, Email, and In-App notifications
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications"""
    TRADE = "trade"
    ERROR = "error"
    PROFIT = "profit"
    LOSS = "loss"
    SYSTEM = "system"
    WARNING = "warning"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationService:
    """
    Unified notification service for all channels
    """
    
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.email_from = os.getenv("NOTIFICATION_EMAIL_FROM", "bot@trading.ai")
        
        # In-memory storage for in-app notifications (use Redis in production)
        self.in_app_notifications = []
        
    def send_trade_notification(
        self,
        user_id: int,
        trade_data: Dict[str, Any],
        preferences: Optional[Dict[str, bool]] = None
    ) -> Dict[str, bool]:
        """
        Send trade execution notification across all enabled channels
        
        Args:
            user_id: User ID
            trade_data: Trade information
            preferences: User notification preferences
            
        Returns:
            Dict of channel: success status
        """
        if preferences is None:
            preferences = self._get_default_preferences()
        
        # Format message
        message = self._format_trade_message(trade_data)
        
        results = {}
        
        # Send to enabled channels
        if preferences.get("telegram_enabled"):
            chat_id = preferences.get("telegram_chat_id")
            results["telegram"] = self._send_telegram(chat_id, message)
        
        if preferences.get("discord_enabled"):
            results["discord"] = self._send_discord(message)
        
        if preferences.get("email_enabled"):
            email = preferences.get("email")
            results["email"] = self._send_email(
                email,
                "Trade Executed - AI Trading Bot",
                message
            )
        
        # Always send in-app notification
        results["in_app"] = self._send_in_app(user_id, message, NotificationType.TRADE)
        
        return results
    
    def send_error_notification(
        self,
        user_id: int,
        error_message: str,
        preferences: Optional[Dict[str, bool]] = None
    ) -> Dict[str, bool]:
        """Send error notification"""
        if preferences is None:
            preferences = self._get_default_preferences()
        
        if not preferences.get("notify_on_error", True):
            return {}
        
        message = f"⚠️ **Error Alert**\n\n{error_message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {}
        
        if preferences.get("telegram_enabled"):
            chat_id = preferences.get("telegram_chat_id")
            results["telegram"] = self._send_telegram(chat_id, message)
        
        if preferences.get("discord_enabled"):
            results["discord"] = self._send_discord(message, color=0xFF0000)
        
        results["in_app"] = self._send_in_app(user_id, error_message, NotificationType.ERROR)
        
        return results
    
    def send_system_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM
    ) -> Dict[str, bool]:
        """Send system notification (health checks, updates, etc.)"""
        formatted_message = f"🔔 **{title}**\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {
            "in_app": self._send_in_app(user_id, formatted_message, notification_type)
        }
        
        return results
    
    def _format_trade_message(self, trade_data: Dict[str, Any]) -> str:
        """Format trade data into readable message"""
        side = trade_data.get("side", "").upper()
        symbol = trade_data.get("symbol", "")
        price = trade_data.get("price", 0)
        amount = trade_data.get("amount", 0)
        value = price * amount
        strategy = trade_data.get("strategy", "Unknown")
        confidence = trade_data.get("confidence", 0) * 100
        pnl_24h = trade_data.get("pnl_24h", 0)
        
        # Choose emoji based on side
        emoji = "🟢" if side == "BUY" else "🔴"
        
        message = f"""
{emoji} **Trade Executed**

**Symbol:** {symbol}
**Side:** {side}
**Price:** ${price:,.2f}
**Amount:** {amount:.6f}
**Value:** ${value:,.2f}
**Strategy:** {strategy}
**Confidence:** {confidence:.1f}%

**Portfolio (24h):** {"+" if pnl_24h >= 0 else ""}{pnl_24h:,.2f} USD

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        return message.strip()
    
    def _send_telegram(self, chat_id: str, message: str) -> bool:
        """Send message via Telegram"""
        if not self.telegram_token or not chat_id:
            logger.warning("Telegram not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram notification sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    def _send_discord(self, message: str, color: int = 0x00D4AA) -> bool:
        """Send message via Discord webhook"""
        if not self.discord_webhook:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            # Convert markdown to Discord format
            discord_message = message.replace("**", "**").replace("_", "*")
            
            payload = {
                "embeds": [{
                    "description": discord_message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info("Discord notification sent")
                return True
            else:
                logger.error(f"Discord error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, message: str) -> bool:
        """Send email via SendGrid"""
        if not self.sendgrid_key or not to_email:
            logger.warning("Email not configured")
            return False
        
        try:
            # Convert markdown to HTML
            html_message = self._markdown_to_html(message)
            
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "personalizations": [{
                    "to": [{"email": to_email}]
                }],
                "from": {"email": self.email_from},
                "subject": subject,
                "content": [{
                    "type": "text/html",
                    "value": html_message
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 202:
                logger.info(f"Email sent to {to_email}")
                return True
            else:
                logger.error(f"Email error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _send_in_app(self, user_id: int, message: str, notification_type: NotificationType) -> bool:
        """Store in-app notification"""
        try:
            notification = {
                "id": len(self.in_app_notifications) + 1,
                "user_id": user_id,
                "message": message,
                "type": notification_type.value,
                "timestamp": datetime.now().isoformat(),
                "read": False
            }
            
            self.in_app_notifications.append(notification)
            
            # Keep only last 100 notifications per user
            user_notifications = [n for n in self.in_app_notifications if n["user_id"] == user_id]
            if len(user_notifications) > 100:
                # Remove oldest
                oldest = min(user_notifications, key=lambda x: x["timestamp"])
                self.in_app_notifications.remove(oldest)
            
            logger.info(f"In-app notification stored for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"In-app notification failed: {e}")
            return False
    
    def get_in_app_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get in-app notifications for user"""
        notifications = [n for n in self.in_app_notifications if n["user_id"] == user_id]
        
        if unread_only:
            notifications = [n for n in notifications if not n["read"]]
        
        # Sort by timestamp descending
        notifications.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return notifications
    
    def mark_as_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        for notification in self.in_app_notifications:
            if notification["id"] == notification_id:
                notification["read"] = True
                return True
        return False
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Simple markdown to HTML conversion"""
        html = markdown
        
        # Bold
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        
        # Italic
        html = html.replace("_", "<em>").replace("_", "</em>")
        
        # Line breaks
        html = html.replace("\n", "<br>")
        
        # Wrap in basic HTML
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="background: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                {html}
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_default_preferences(self) -> Dict[str, bool]:
        """Get default notification preferences"""
        return {
            "telegram_enabled": False,
            "discord_enabled": False,
            "email_enabled": True,
            "notify_on_trade": True,
            "notify_on_error": True,
            "notify_on_profit": True,
            "notify_on_loss": True
        }


# Global notification service instance
notification_service = NotificationService()
