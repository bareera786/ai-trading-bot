"""Background scheduler/runtime orchestration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.services.live_portfolio import LivePortfolioScheduler
from app.tasks.manager import BackgroundTaskManager


@dataclass
class BackgroundRuntime:
    """Bundle of background orchestration primitives."""

    live_portfolio_scheduler: LivePortfolioScheduler
    background_task_manager: BackgroundTaskManager

    def attach_app(self, flask_app: Any | None) -> None:
        if flask_app is None or self.live_portfolio_scheduler is None:
            return
        try:  # pragma: no cover - defensive setter
            self.live_portfolio_scheduler.app = flask_app
        except Exception:
            pass


def build_background_runtime(
    *,
    update_callback,
    bot_logger: Any | None,
    market_data_service: Any,
    futures_market_data_service: Any | None,
    realtime_update_service: Any | None,
    persistence_scheduler: Any | None,
    self_improvement_worker: Any | None,
    model_training_worker: Any | None,
    trading_config: Mapping[str, Any],
    flask_app: Any | None = None,
    update_interval_seconds: float = 30.0,
    tick_interval_seconds: float = 10.0,
) -> BackgroundRuntime:
    """Construct the shared background task runtime."""

    scheduler = LivePortfolioScheduler(
        app=flask_app,
        update_callback=update_callback,
        update_interval_seconds=update_interval_seconds,
        tick_interval_seconds=tick_interval_seconds,
        logger=bot_logger,
    )

    manager = BackgroundTaskManager(
        market_data_service=market_data_service,
        futures_market_data_service=futures_market_data_service,
        realtime_update_service=realtime_update_service,
        persistence_scheduler=persistence_scheduler,
        self_improvement_worker=self_improvement_worker,
        model_training_worker=model_training_worker,
        live_portfolio_scheduler=scheduler,
        trading_config=trading_config,
        bot_logger=bot_logger,
    )

    return BackgroundRuntime(
        live_portfolio_scheduler=scheduler,
        background_task_manager=manager,
    )


__all__ = ['BackgroundRuntime', 'build_background_runtime']
