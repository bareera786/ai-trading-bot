"""Application package entry point."""
from __future__ import annotations

from typing import Optional

from flask import Flask
from .config import Config
from .extensions import init_extensions
from .routes import register_blueprints
from .bootstrap import bootstrap_runtime


def create_app(config_class: Optional[type[Config]] = None) -> Flask:
    """Application factory used by scripts and WSGI servers."""
    config_cls = config_class or Config

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_cls)

    init_extensions(app)
    register_blueprints(app)

    bootstrap_runtime(app)

    return app
