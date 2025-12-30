"""Persistence, logging, and credential runtime helpers."""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional, Union

from app.services.binance import (
    BinanceCredentialService,
    BinanceCredentialStore,
    BinanceLogManager,
)
from app.services.pathing import (
    BOT_PROFILE as DEFAULT_BOT_PROFILE,
    resolve_profile_path,
)
from app.services.persistence import ProfessionalPersistence, PersistenceScheduler

DashboardProvider = Union[
    Callable[[], MutableMapping[str, Any]], MutableMapping[str, Any]
]


@dataclass
class PersistenceRuntime:
    """Bundle of persistence/logging dependencies shared across the runtime."""

    persistence_manager: ProfessionalPersistence
    persistence_scheduler: PersistenceScheduler
    bot_logger: logging.Logger
    binance_credentials_store: BinanceCredentialStore
    binance_credential_service: BinanceCredentialService
    binance_log_manager: BinanceLogManager
    credential_vault_dir: str
    credential_vault_file: str

    def attach_dashboard_data(self, provider: Optional[DashboardProvider]) -> None:
        if provider is None:
            return
        if callable(provider):
            accessor = provider
        else:
            accessor = lambda: provider  # type: ignore[assignment]
        self.binance_log_manager.attach_dashboard_data(accessor)
        self.binance_credential_service.attach_dashboard_data(accessor)

    def snapshot_credentials(
        self,
        *,
        include_connection: bool = False,
        include_logs: bool = False,
    ) -> dict[str, Any]:
        return self.binance_credential_service.get_status(
            include_connection=include_connection,
            include_logs=include_logs,
        )


def build_persistence_runtime(
    *,
    market_cap_weights_provider: Callable[[], Mapping[str, float]],
    futures_settings_getter: Callable[[], Mapping[str, Any]],
    futures_settings_setter: Callable[[Mapping[str, Any]], None],
    ultimate_trader: Any,
    optimized_trader: Any,
    futures_manual_lock: Optional[Union[threading.Lock, threading.RLock]],
    futures_manual_settings: Optional[dict[str, Any]],
    coerce_bool: Callable[[Any, bool], bool],
    log_event: Callable[..., Any],
    log_debug: Callable[..., Any],
    logger_factory: Callable[[str], logging.Logger],
    bot_profile: Optional[str] = None,
    save_interval_minutes: int = 5,
) -> PersistenceRuntime:
    """Construct persistence/logging services for the AI runtime."""
    
    # Ensure all required directories exist before setting up logging
    from app.services.persistence import ensure_persistence_dirs
    ensure_persistence_dirs()

    profile_name = bot_profile or DEFAULT_BOT_PROFILE

    persistence_root = resolve_profile_path(
        "bot_persistence", allow_legacy=False, migrate_legacy=True
    )
    persistence_manager = ProfessionalPersistence(
        persistence_dir=persistence_root,
        market_cap_weights_provider=market_cap_weights_provider,
        futures_settings_getter=futures_settings_getter,
        futures_settings_setter=futures_settings_setter,
    )
    print("💾 Professional Persistence System Initialized")

    log_dir = resolve_profile_path("logs", allow_legacy=False, migrate_legacy=True)
    bot_logger = logger_factory(log_dir)
    bot_logger.info("Active bot profile: %s", profile_name)

    persistence_scheduler = PersistenceScheduler(
        persistence_manager,
        save_interval_minutes=save_interval_minutes,
        log_event=log_event,
        log_debug=log_debug,
        bot_logger=bot_logger,
    )

    credential_vault_dir = resolve_profile_path(
        "credentials", allow_legacy=False, migrate_legacy=True
    )
    credential_vault_file = os.path.join(credential_vault_dir, f"{profile_name}.json")
    binance_credentials_store = BinanceCredentialStore(
        storage_dir=credential_vault_dir,
        credential_file=credential_vault_file,
    )

    binance_log_manager = BinanceLogManager()
    for trader in filter(None, (ultimate_trader, optimized_trader)):
        real_trader = getattr(trader, "real_trader", None)
        if real_trader is None:
            continue
        real_trader.binance_log_manager = binance_log_manager
        real_trader.logger = bot_logger

    binance_credential_service = BinanceCredentialService(
        binance_credentials_store,
        ultimate_trader,
        optimized_trader,
        futures_manual_lock=futures_manual_lock,
        futures_manual_settings=futures_manual_settings,
        binance_log_manager=binance_log_manager,
        coerce_bool=coerce_bool,
    )
    binance_credential_service.initialize_all()

    return PersistenceRuntime(
        persistence_manager=persistence_manager,
        persistence_scheduler=persistence_scheduler,
        bot_logger=bot_logger,
        binance_credentials_store=binance_credentials_store,
        binance_credential_service=binance_credential_service,
        binance_log_manager=binance_log_manager,
        credential_vault_dir=credential_vault_dir,
        credential_vault_file=credential_vault_file,
    )


__all__ = ["PersistenceRuntime", "build_persistence_runtime"]
