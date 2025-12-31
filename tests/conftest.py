"""Pytest configuration helpers for the ai-trading-bot test suite."""
from __future__ import annotations

import sys
from pathlib import Path

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
