"""Diagnostics script for production troubleshooting.

Run this inside the container or on the host with the app env available.

Example:
  docker compose exec -T ai-trading-bot python scripts/diagnose_production.py
"""
from __future__ import annotations

import sys
import json
import platform
import subprocess
from pathlib import Path

from app import create_app
from app.extensions import db


def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as exc:
        return f"ERROR (exit {exc.returncode}): {exc.output}"


def main():
    print("=== Diagnostic Script ===")
    print("Python:", platform.python_version())
    print("Flask:", __import__("flask").__version__)

    app = create_app()
    with app.app_context():
        print("\nApp config (selected):")
        keys = ["SQLALCHEMY_DATABASE_URI", "MIGRATE_DIRECTORY", "ENV", "TESTING", "SKIP_RUNTIME_BOOTSTRAP"]
        for k in keys:
            print(f"  {k}: {app.config.get(k)}")

        url = app.config.get("SQLALCHEMY_DATABASE_URI")
        print("\nDatabase URL:", url)

        # Inspect user table columns
        inspector = __import__("sqlalchemy").inspect(db.engine)
        tables = inspector.get_table_names()
        print("\nTables:", tables)

        if "user" in tables:
            cols = [c.get("name") for c in inspector.get_columns("user")]
            print("\n'user' columns:", cols)

            expected = ["id", "username", "email", "role", "last_login_at", "failed_login_count", "last_ip"]
            missing = [c for c in expected if c not in cols]
            if missing:
                print("MISSING columns:", missing)
            else:
                print("All expected columns present")

            # Check for NULL roles
            try:
                res = db.session.execute("SELECT id, email FROM \"user\" WHERE role IS NULL LIMIT 10").fetchall()
                if res:
                    print("Users with NULL role (up to 10):")
                    for r in res:
                        print(" ", r)
                else:
                    print("No users with NULL role found")
            except Exception as exc:
                print("Could not query users (exception):", exc)

            # If Postgres, print enum labels for role enum
            try:
                dialect = db.engine.dialect.name
                print("DB dialect:", dialect)
                if dialect == "postgresql":
                    enum_q = "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname='roleenum';"
                    try:
                        rows = db.session.execute(enum_q).fetchall()
                        labels = [r[0] for r in rows]
                        print("roleenum labels:", labels)
                    except Exception as exc:
                        print("Could not query role enum labels:", exc)
            except Exception:
                print("Could not determine DB dialect")

        else:
            print("No 'user' table found in DB")

        # Alembic status
        print("\nAlembic revision status:")
        # Try to use flask-migrate via CLI to get consistent output
        current = run_cmd("flask db current")
        heads = run_cmd("flask db heads")
        print("flask db current:\n", current)
        print("flask db heads:\n", heads)

        # alembic_version table
        try:
            ver = db.session.execute("SELECT version_num FROM alembic_version").fetchall()
            print("alembic_version rows:", ver)
        except Exception as exc:
            print("Could not read alembic_version table:", exc)

        # Trading flags from persistence files (on-disk)
        print("\nOn-disk bot persistence (default):")
        base = Path("bot_persistence/default")
        for fname in ("critical_state.json", "bot_state.json"):
            path = base / fname
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    print(f"{fname}: trading_enabled=", data.get("trading_enabled"))
                except Exception as exc:
                    print(f"Could not read {fname}:", exc)
            else:
                print(f"{fname}: MISSING")

    print("\n=== End Diagnostics ===")


if __name__ == "__main__":
    main()
