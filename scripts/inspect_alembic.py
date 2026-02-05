#!/usr/bin/env python3
"""Inspect Alembic script directory heads and DB current revision.
Runs inside the container (project mounted at /app).
"""
from app import create_app


def main():
    app = create_app()
    with app.app_context():
        from flask_migrate import current
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext

        cfg = current.get_config()
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
        engine = current.get_engine()
        mc = MigrationContext.configure(engine.connect())
        current_rev = mc.get_current_revision()

        print("ALEMBIC_HEADS:", heads)
        print("DB_REVISION:", current_rev)


if __name__ == "__main__":
    main()
