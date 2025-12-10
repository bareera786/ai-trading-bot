#!/usr/bin/env python3
"""Database migration script for PostgreSQL setup and data migration from SQLite."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from flask_migrate import Migrate
from app import create_app
from app.extensions import db
import subprocess
import shutil


def backup_sqlite_database():
    """Create a backup of the current SQLite database."""
    sqlite_path = project_root / "trading_bot.db"
    if sqlite_path.exists():
        backup_path = project_root / "trading_bot.db.backup"
        print(f"Backing up SQLite database to {backup_path}")
        shutil.copy2(sqlite_path, backup_path)
        return backup_path
    return None


def export_sqlite_data():
    """Export data from SQLite to SQL dump."""
    sqlite_path = project_root / "trading_bot.db"
    if not sqlite_path.exists():
        print("No SQLite database found to migrate")
        return None

    dump_path = project_root / "sqlite_dump.sql"
    print(f"Exporting SQLite data to {dump_path}")

    # Use sqlite3 command to dump data
    try:
        with open(dump_path, 'w') as f:
            subprocess.run([
                'sqlite3', str(sqlite_path), '.dump'
            ], stdout=f, check=True)
        return dump_path
    except subprocess.CalledProcessError as e:
        print(f"Failed to export SQLite data: {e}")
        return None


def convert_sqlite_to_postgresql_dump(sqlite_dump_path, pg_dump_path):
    """Convert SQLite dump to PostgreSQL compatible format."""
    print("Converting SQLite dump to PostgreSQL format...")

    with open(sqlite_dump_path, 'r') as f:
        sqlite_content = f.read()

    # Basic conversions (this is a simplified version)
    # In production, you might want to use a more robust conversion tool
    pg_content = sqlite_content

    # Remove SQLite-specific pragmas
    pg_content = '\n'.join([
        line for line in pg_content.split('\n')
        if not line.strip().startswith('PRAGMA') and not line.strip().startswith('BEGIN TRANSACTION')
    ])

    # Convert AUTOINCREMENT to SERIAL
    pg_content = pg_content.replace('AUTOINCREMENT', '')

    with open(pg_dump_path, 'w') as f:
        f.write(pg_content)

    return pg_dump_path


def setup_postgresql_database(pg_url):
    """Set up PostgreSQL database and run migrations."""
    print(f"Setting up PostgreSQL database: {pg_url}")

    # Set environment variable for database URL
    os.environ['DATABASE_URL'] = pg_url

    # Create Flask app with PostgreSQL config
    app = create_app()

    with app.app_context():
        # Create all tables
        print("Creating tables...")
        db.create_all()

        # Run migrations if they exist
        migrate = Migrate(app, db)
        try:
            from flask_migrate import upgrade
            print("Running database migrations...")
            upgrade()
        except Exception as e:
            print(f"Migration failed (this may be expected if no migrations exist): {e}")

    print("PostgreSQL database setup complete")


def migrate_data_to_postgresql(sqlite_dump_path, pg_url):
    """Migrate data from SQLite dump to PostgreSQL."""
    if not sqlite_dump_path:
        return

    pg_dump_path = project_root / "postgresql_dump.sql"
    convert_sqlite_to_postgresql_dump(sqlite_dump_path, pg_dump_path)

    print("Note: Manual data migration may be required.")
    print(f"PostgreSQL-compatible dump saved to: {pg_dump_path}")
    print("You may need to manually import this data using psql or pg_restore")


def main():
    """Main migration function."""
    print("PostgreSQL Migration Script")
    print("=" * 40)

    # Check for PostgreSQL URL
    pg_url = os.getenv('DATABASE_URL')
    if not pg_url or not pg_url.startswith('postgresql://'):
        print("Error: DATABASE_URL environment variable must be set to a PostgreSQL URL")
        print("Example: DATABASE_URL='postgresql://user:password@localhost/trading_bot'")
        sys.exit(1)

    # Backup SQLite database
    backup_path = backup_sqlite_database()

    # Export SQLite data
    sqlite_dump = export_sqlite_data()

    # Setup PostgreSQL database
    setup_postgresql_database(pg_url)

    # Migrate data
    if sqlite_dump:
        migrate_data_to_postgresql(sqlite_dump, pg_url)

    print("\nMigration Summary:")
    print(f"- SQLite backup: {backup_path}")
    print(f"- SQLite dump: {sqlite_dump}")
    print(f"- PostgreSQL URL: {pg_url}")
    print("\nNext steps:")
    print("1. Verify PostgreSQL database is working")
    print("2. Update your environment variables to use PostgreSQL")
    print("3. Test the application thoroughly")
    print("4. Remove SQLite database if migration is successful")


if __name__ == "__main__":
    main()