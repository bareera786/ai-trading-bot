"""ML system orchestration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class MLServiceBundle:
    """Container for the live ML system instances."""

    ultimate_ml_system: Any
    optimized_ml_system: Any
    futures_ml_system: Any


def create_ml_services(
    *,
    ultimate_factory: Callable[[], Any],
    optimized_factory: Callable[[], Any],
    futures_factory: Callable[[], Any],
) -> MLServiceBundle:
    """Instantiate the ML systems used by the trading bot.

    The factories are passed in so the monolith (or future app factory) can
    continue supplying the concrete classes without creating circular imports.
    """

    ultimate_ml = ultimate_factory()
    optimized_ml = optimized_factory()
    futures_ml = futures_factory()
    return MLServiceBundle(
        ultimate_ml_system=ultimate_ml,
        optimized_ml_system=optimized_ml,
        futures_ml_system=futures_ml,
    )
