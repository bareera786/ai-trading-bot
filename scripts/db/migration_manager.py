
import os
import sys

# Set environment to skip heavy lifting
os.environ["SKIP_RUNTIME_BOOTSTRAP"] = "1"
os.environ["FLASK_DEBUG"] = "1"

from app import create_app
from app.extensions import db, migrate
import app.models  # Register models for Alembic
from flask_migrate import upgrade, migrate as migrate_cmd, init

app = create_app()

if __name__ == "__main__":
    from flask.cli import FlaskGroup
    
    # We need to manually add the 'db' command if not present, but usually FlaskGroup does it if Migrate is init.
    # However, since we are running this script directly, we can just use app.cli
    
    cli = FlaskGroup(create_app=lambda: app)
    cli()
