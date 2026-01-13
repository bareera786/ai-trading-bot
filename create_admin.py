#!/usr/bin/env python3
"""Utility script for creating or resetting the dashboard admin account."""

from __future__ import annotations

import argparse
import os
from getpass import getpass

import click

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def _prompt_for_password() -> str:
    while True:
        password = getpass("Admin password: ")
        confirm = getpass("Confirm password: ")
        if not password:
            print("Password cannot be empty. Please try again.")
            continue
        if password != confirm:
            print("Passwords do not match. Please try again.")
            continue
        return password


def create_or_update_admin(
    username: str, email: str, password: str, reset: bool
) -> None:
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username=username).first()

        if admin:
            if reset:
                admin.email = email or admin.email
                admin.set_password(password)
                db.session.commit()
                print(
                    f"🔁 Updated existing admin '{username}' with a new password/email."
                )
            else:
                print(
                    f"✅ Admin '{username}' already exists. Use --reset-password to rotate credentials."
                )
            return

        admin = User(
            username=username,
            email=email,
            role="admin",
            is_active=True,
            email_verified=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print("⚠️  Please rotate this password immediately in production!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update the AI bot admin account."
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("ADMIN_USERNAME", "admin"),
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("ADMIN_EMAIL"),
        help="Admin email (default: <username>@example.com)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("ADMIN_PASSWORD"),
        help="Optional password to use (otherwise prompted securely)",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Update password/email if the user already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    email = args.email or f"{args.username}@example.com"
    password = args.password or _prompt_for_password()
    create_or_update_admin(args.username, email, password, args.reset_password)


@app.cli.command("users-create")
@click.argument("email")
@click.argument("username")
@click.argument("password")
@click.option("--role", default="viewer", help="Role of the user (admin, trader, viewer)")
def create_user(email, username, password, role):
    """Create a new user."""
    with app.app_context():
        if User.query.filter_by(email=email).first():
            click.echo("Error: User with this email already exists.")
            return

        user = User(email=email, username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User {username} created successfully.")


@app.cli.command("users-promote")
@click.argument("email")
def promote_user(email):
    """Promote a user to admin."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("Error: User not found.")
            return

        user.role = "admin"
        db.session.commit()
        click.echo(f"User {user.username} promoted to admin.")


@app.cli.command("users-deactivate")
@click.argument("email")
def deactivate_user(email):
    """Deactivate a user."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("Error: User not found.")
            return

        user.is_active = False
        db.session.commit()
        click.echo(f"User {user.username} deactivated.")


@app.cli.command("users-reset-password")
@click.argument("email")
@click.argument("new_password")
def reset_password(email, new_password):
    """Reset a user's password."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("Error: User not found.")
            return

        user.set_password(new_password)
        db.session.commit()
        click.echo(f"Password for user {user.username} has been reset.")


if __name__ == "__main__":
    main()
