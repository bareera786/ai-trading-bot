"""Password validation utilities."""
from __future__ import annotations

import re
import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt, hashed = hashed_password.split(":", 1)
        expected_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return secrets.compare_digest(hashed, expected_hash)
    except ValueError:
        return False


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
