#!/usr/bin/env python3
"""Quick helper script to inspect trader flags without importing the monolith."""

from __future__ import annotations

import json
from pathlib import Path

from app import create_app


def _get_ai_context(app):
    ctx = app.extensions.get("ai_bot_context")
    if ctx is None:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "AI bot context is unavailable; ensure bootstrap_runtime() ran."
        )
    return ctx


def main() -> None:
    app = create_app()
    with app.app_context():
        ctx = _get_ai_context(app)
        ultimate = ctx.get("ultimate_trader")
        optimized = ctx.get("optimized_trader")

        print(
            "ultimate_trader.trading_enabled:",
            getattr(ultimate, "trading_enabled", None),
        )
        print(
            "optimized_trader.trading_enabled:",
            getattr(optimized, "trading_enabled", None),
        )

    state_path = Path("bot_persistence/bot_state.json")
    if state_path.exists():
        with state_path.open("r") as f:
            state = json.load(f)
        print(
            "state file trading_enabled:",
            state.get("trader_state", {}).get("trading_enabled"),
        )
    else:
        print("state file trading_enabled: <bot_state.json not found>")


if __name__ == "__main__":
    main()
