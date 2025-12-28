"""Email utilities for sending notifications."""
from __future__ import annotations

from typing import Optional

from flask import current_app, url_for

try:
    from flask_mail import Message  # type: ignore
except (
    Exception
):  # pragma: no cover - optional dependency may be missing in some test envs
    # Provide a lightweight Message shim so unit tests that import this module
    # don't fail when Flask-Mail isn't installed.
    class Message:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.subject = kwargs.get("subject")
            self.recipients = kwargs.get("recipients")
            self.body = kwargs.get("body")
            self.html = kwargs.get("html")


from app.extensions import mail


def send_email(subject: str, recipients: list[str], body: str, html: Optional[str] = None) -> None:
    """Send a generic email."""
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        html=html if html is not None else None,
    )

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")


def send_password_reset_email(user_email: str, token: str) -> None:
    """Send password reset email."""
    reset_url = url_for("auth.reset_password", token=token, _external=True)

    msg = Message(
        subject="Password Reset Request - AI Trading Bot",
        recipients=[user_email],
        body=f"""Hello,

You have requested to reset your password for your AI Trading Bot account.

Please click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
AI Trading Bot Team
""",
        html=f"""
<html>
<body>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>You have requested to reset your password for your AI Trading Bot account.</p>
    <p>Please click the button below to reset your password:</p>
    <p style="margin: 30px 0;">
        <a href="{reset_url}" style="background-color: #00d4aa; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
    </p>
    <p><strong>This link will expire in 1 hour.</strong></p>
    <p>If you did not request this password reset, please ignore this email.</p>
    <br>
    <p>Best regards,<br>AI Trading Bot Team</p>
</body>
</html>
""",
    )

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")


def send_email_verification_email(user_email: str, token: str) -> None:
    """Send email verification email."""
    verify_url = url_for("auth.verify_email", token=token, _external=True)

    msg = Message(
        subject="Verify Your Email - AI Trading Bot",
        recipients=[user_email],
        body=f"""Hello,

Thank you for registering with AI Trading Bot!

Please click the following link to verify your email address:
{verify_url}

This link will expire in 24 hours.

If you did not create this account, please ignore this email.

Best regards,
AI Trading Bot Team
""",
        html=f"""
<html>
<body>
    <h2>Verify Your Email</h2>
    <p>Hello,</p>
    <p>Thank you for registering with AI Trading Bot!</p>
    <p>Please click the button below to verify your email address:</p>
    <p style="margin: 30px 0;">
        <a href="{verify_url}" style="background-color: #00d4aa; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email</a>
    </p>
    <p><strong>This link will expire in 24 hours.</strong></p>
    <p>If you did not create this account, please ignore this email.</p>
    <br>
    <p>Best regards,<br>AI Trading Bot Team</p>
</body>
</html>
""",
    )

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send email verification email: {e}")
