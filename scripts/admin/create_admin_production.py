#!/usr/bin/env python3
"""Utility script for creating the dashboard admin account in production."""

from __future__ import annotations

import argparse
import os
from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import User

# Ensure we're not in test mode and set production database
os.environ.pop('AI_BOT_TEST_MODE', None)
os.environ['DATABASE_URL'] = 'sqlite:///trading_bot.db'

app = create_app()


def create_admin(username: str, email: str, password: str) -> None:
    with app.app_context():
        print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

        db.create_all()  # Ensure tables exist

        # Check if admin already exists
        admin = User.query.filter_by(username=username).first()
        if admin:
            # Update email and password if different
            if admin.email != email:
                admin.email = email
                print(f"Updated admin email to: {email}")
            admin.set_password(password)
            db.session.commit()
            print(f"✅ Admin '{username}' updated with new credentials.")
            return

        admin = User(
            username=username,
            email=email,
            is_admin=True,
            is_active=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the AI bot admin account."
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Admin email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="Admin password (default: admin123)",
    )

    args = parser.parse_args()
    create_admin(args.username, args.email, args.password)


if __name__ == "__main__":
    main()