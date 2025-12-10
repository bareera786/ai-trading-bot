"""Typed helpers for working with the AI bot runtime context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type-checking helpers only
    from app.runtime.background import BackgroundRuntime
    from app.runtime.persistence import PersistenceRuntime
    from app.runtime.services import ServiceRuntime

ExtensionPayload = dict[str, Any]


@dataclass(frozen=True)
class IndicatorRuntime:
    """Lightweight view over the indicator selection state."""

    selection_manager: Any
    signal_options: Iterable[str]
    dashboard_refresher: Optional[Callable[[], Mapping[str, list[str]]]] = None

    def profiles(self) -> list[str]:  # pragma: no cover - thin wrapper
        if hasattr(self.selection_manager, "profiles"):
            return list(self.selection_manager.profiles())
        return []

    def snapshot(self) -> Mapping[str, list[str]]:
        if hasattr(self.selection_manager, "snapshot"):
            return self.selection_manager.snapshot()
        return {}


@dataclass(frozen=True)
class SymbolRuntime:
    """Aggregate helpers for symbol state management."""

    get_active_universe: Callable[[], list[str]]
    get_all_symbols: Callable[[], list[str]]
    get_disabled_symbols: Callable[[], list[str]]
    disable_symbol: Callable[[Any], bool]
    enable_symbol: Callable[[Any], bool]
    is_symbol_disabled: Callable[[Any], bool]
    refresh_counters: Callable[[], None]
    clear_symbol_dashboards: Callable[[str], None]
    save_state: Callable[[], None]
    normalize_symbol: Callable[[Any], str]
    static_top_symbols: Iterable[str] = field(default_factory=list)
    static_disabled_symbols: Iterable[str] = field(default_factory=list)


@dataclass
class RuntimeContext:
    """Wrapper around the runtime payload plus typed helpers."""

    payload: ExtensionPayload
    indicator_runtime: Optional[IndicatorRuntime] = None
    symbol_runtime: Optional[SymbolRuntime] = None
    persistence_runtime: Optional["PersistenceRuntime"] = None
    background_runtime: Optional["BackgroundRuntime"] = None
    service_runtime: Optional["ServiceRuntime"] = None
    _extension_key: str = field(default="ai_bot_context", init=False, repr=False)

    def as_dict(self) -> ExtensionPayload:
        return self.payload

    def attach_to_app(self, flask_app, *, force: bool = False) -> ExtensionPayload:
        """Merge the payload into the Flask app extensions."""

        if flask_app is None:
            raise RuntimeError("Flask application instance required")

        existing = flask_app.extensions.get(self._extension_key)
        if existing and not force:
            existing.update(self.payload)
            context = existing
        else:
            flask_app.extensions[self._extension_key] = self.payload
            context = self.payload

        scheduler = context.get("live_portfolio_scheduler")
        if scheduler is not None:
            try:  # pragma: no cover - defensive assignment
                scheduler.app = flask_app
            except Exception:
                pass

        runtime = self.background_runtime
        if runtime is not None:
            attach_app = getattr(runtime, "attach_app", None)
            if callable(attach_app):
                try:  # pragma: no cover - defensive attachment
                    attach_app(flask_app)
                except Exception:
                    pass

        return context


def build_runtime_context(payload: ExtensionPayload, **extras: Any) -> RuntimeContext:
    """Factory helper that injects optional typed helpers into the runtime context."""

    indicator_runtime = extras.get("indicator_runtime")
    symbol_runtime = extras.get("symbol_runtime")
    persistence_runtime = extras.get("persistence_runtime")
    background_runtime = extras.get("background_runtime")
    service_runtime = extras.get("service_runtime")
    return RuntimeContext(
        payload=payload,
        indicator_runtime=indicator_runtime,
        symbol_runtime=symbol_runtime,
        persistence_runtime=persistence_runtime,
        background_runtime=background_runtime,
        service_runtime=service_runtime,
    )
