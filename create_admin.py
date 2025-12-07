#!/usr/bin/env python3
"""Utility script for creating or resetting the dashboard admin account."""

from __future__ import annotations

import argparse
import os
from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def _prompt_for_password() -> str:
    while True:
        password = getpass('Admin password: ')
        confirm = getpass('Confirm password: ')
        if not password:
            print('Password cannot be empty. Please try again.')
            continue
        if password != confirm:
            print('Passwords do not match. Please try again.')
            continue
        return password


def create_or_update_admin(username: str, email: str, password: str, reset: bool) -> None:
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username=username).first()

        if admin:
            if reset:
                admin.email = email or admin.email
                admin.set_password(password)
                db.session.commit()
                print(f"🔁 Updated existing admin '{username}' with a new password/email.")
            else:
                print(f"✅ Admin '{username}' already exists. Use --reset-password to rotate credentials.")
            return

        admin = User(username=username, email=email, is_admin=True, is_active=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print('⚠️  Please rotate this password immediately in production!')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Create or update the AI bot admin account.')
    parser.add_argument('--username', default=os.environ.get('ADMIN_USERNAME', 'admin'), help='Admin username (default: admin)')
    parser.add_argument('--email', default=os.environ.get('ADMIN_EMAIL'), help='Admin email (default: <username>@example.com)')
    parser.add_argument('--password', default=os.environ.get('ADMIN_PASSWORD'), help='Optional password to use (otherwise prompted securely)')
    parser.add_argument('--reset-password', action='store_true', help='Update password/email if the user already exists.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    email = args.email or f"{args.username}@example.com"
    password = args.password or _prompt_for_password()
    create_or_update_admin(args.username, email, password, args.reset_password)


if __name__ == '__main__':
    main()