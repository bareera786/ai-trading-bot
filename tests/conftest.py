"""Pytest configuration helpers for the ai-trading-bot test suite."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_ignore_collect(path, config):
    """Ignore the legacy top-level test that conflicts with the namespaced
    integration copy.

    This is a temporary mitigation to avoid pytest import-file-mismatch
    errors while we consolidate duplicate test files.
    """
    p = str(path)
    # Normalize path separators for cross-platform safety
    if p.replace("\\", "/").endswith("/tests/test_trading_integration.py"):
        return True


@pytest.fixture
def app():
    """Default Flask app fixture for tests relying on pytest-flask's `client`.

    Individual test modules can override this fixture when they need a richer app.
    """
    os.environ.setdefault("AI_BOT_TEST_MODE", "1")

    from app.routes.status import status_bp

    flask_app = Flask(__name__)
    flask_app.config.update(TESTING=True, SECRET_KEY="test-key")
    flask_app.register_blueprint(status_bp)
    return flask_app


@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client
