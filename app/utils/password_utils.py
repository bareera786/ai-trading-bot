"""Password validation utilities."""
from __future__ import annotations

import re


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength requirements.

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character."

    # Check for common weak passwords
    common_passwords = [
        "password",
        "123456",
        "123456789",
        "qwerty",
        "abc123",
        "password123",
        "admin",
        "letmein",
        "welcome",
        "monkey",
    ]

    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a stronger password."

    return True, ""
