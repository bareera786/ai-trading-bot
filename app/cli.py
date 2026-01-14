"""Flask CLI commands for user management."""
from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext

from .extensions import db
from .models import User


def register_cli_commands(app: Flask) -> None:
    """Register CLI commands with the Flask app."""
    app.cli.add_command(create_user_command)
    app.cli.add_command(create_bootstrap_users_command)


@click.command("create-user")
@click.option("--email", required=True, help="User email address")
@click.option("--username", help="Username (defaults to email prefix)")
@click.option("--password", help="User password (will prompt if not provided)")
@click.option("--admin", is_flag=True, help="Make user an admin")
@click.option("--verified", is_flag=True, help="Mark email as verified")
@with_appcontext
def create_user_command(email: str, username: str | None, password: str | None, admin: bool, verified: bool) -> None:
    """Create a new user account."""
    if not username:
        username = email.split("@")[0]

    # Check if user already exists
    existing_user = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()

    if existing_user:
        click.echo(f"❌ User with email '{email}' or username '{username}' already exists!")
        return

    # Get password if not provided
    if not password:
        password = click.prompt("Enter password", hide_input=True, confirmation_prompt=True)
    
    if not password:
        click.echo("❌ Password is required!")
        return

    # Create user
    user = User()
    user.username = username
    user.email = email
    user.is_admin = admin
    user.is_active = True
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    click.echo("✅ User created successfully!")
    click.echo(f"   Username: {username}")
    click.echo(f"   Email: {email}")
    click.echo(f"   Admin: {'Yes' if admin else 'No'}")
    click.echo(f"   Active: Yes")


@click.command("create-bootstrap-users")
@with_appcontext
def create_bootstrap_users_command() -> None:
    """Create bootstrap admin and test users for development/testing."""
    click.echo("🔧 Creating bootstrap users...")

    # Check if any users already exist
    existing_count = User.query.count()
    if existing_count > 0:
        click.echo(f"⚠️  {existing_count} user(s) already exist. Bootstrap users will only be created if they don't exist.")
        click.echo("   Use 'flask create-user' to create additional users.")

    # Create admin user
    admin_user = User.query.filter_by(email="admin@local").first()
    if not admin_user:
        admin_user = User()
        admin_user.username = "admin"
        admin_user.email = "admin@local"
        admin_user.is_admin = True
        admin_user.is_active = True
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        click.echo("✅ Admin user created:")
        click.echo("   Email: admin@local")
        click.echo("   Password: admin123")
    else:
        click.echo("ℹ️  Admin user already exists")

    # Create test user
    test_user = User.query.filter_by(email="test@local").first()
    if not test_user:
        test_user = User()
        test_user.username = "test"
        test_user.email = "test@local"
        test_user.is_admin = False
        test_user.is_active = True
        test_user.set_password("test123")
        db.session.add(test_user)
        click.echo("✅ Test user created:")
        click.echo("   Email: test@local")
        click.echo("   Password: test123")
    else:
        click.echo("ℹ️  Test user already exists")

    db.session.commit()
    click.echo("🎉 Bootstrap users setup complete!")
    click.echo("")
    click.echo("📋 Login Credentials:")
    click.echo("   Admin: admin@local / admin123")
    click.echo("   Test:  test@local / test123")
    click.echo("")
    click.echo("⚠️  IMPORTANT: Change these passwords in production!")