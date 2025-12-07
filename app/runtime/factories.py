"""Factory helpers for building ML and trading runtime services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from app.services import (
    attach_trading_ml_dependencies,
    create_ml_services,
    create_trading_services,
    create_user_trader_resolver,
)
from app.services.ml import MLServiceBundle
from app.services.trading import TradingServiceBundle


@dataclass(frozen=True)
class TradingRuntimeBundle:
    """Container that exposes trading services plus user trader resolver."""

    trading_services: TradingServiceBundle
    get_user_trader: Callable[[Optional[str], str], Any]

    @property
    def trade_history(self) -> Any:  # pragma: no cover - simple proxy
        return self.trading_services.trade_history

    @property
    def ultimate_trader(self) -> Any:  # pragma: no cover - simple proxy
        return self.trading_services.ultimate_trader

    @property
    def optimized_trader(self) -> Any:  # pragma: no cover - simple proxy
        return self.trading_services.optimized_trader

    @property
    def parallel_engine(self) -> Any:  # pragma: no cover - simple proxy
        return self.trading_services.parallel_engine


def build_ml_runtime_services(
    *,
    ultimate_factory: Callable[[], Any],
    optimized_factory: Callable[[], Any],
    futures_factory: Callable[[], Any],
) -> MLServiceBundle:
    """Instantiate the ML systems used by the runtime."""

    return create_ml_services(
        ultimate_factory=ultimate_factory,
        optimized_factory=optimized_factory,
        futures_factory=futures_factory,
    )


def build_trading_runtime_services(
    *,
    ml_bundle: MLServiceBundle,
    trade_history_factory: Callable[[], Any],
    ultimate_trader_factory: Callable[[], Any],
    optimized_trader_factory: Callable[[], Any],
    parallel_engine_factory: Callable[[], Any],
    optimized_aliases: Optional[Iterable[str]] = None,
) -> TradingRuntimeBundle:
    """Instantiate trading services and wire them to the provided ML bundle."""

    trading_bundle = create_trading_services(
        trade_history_factory=trade_history_factory,
        ultimate_trader_factory=ultimate_trader_factory,
        optimized_trader_factory=optimized_trader_factory,
        parallel_engine_factory=parallel_engine_factory,
    )
    attach_trading_ml_dependencies(trading_bundle, ml_bundle)
    get_user_trader = create_user_trader_resolver(
        trading_bundle,
        optimized_aliases=optimized_aliases,
    )
    return TradingRuntimeBundle(
        trading_services=trading_bundle,
        get_user_trader=get_user_trader,
    )


__all__ = [
    'TradingRuntimeBundle',
    'build_ml_runtime_services',
    'build_trading_runtime_services',
]
