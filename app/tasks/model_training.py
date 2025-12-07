"""Model training background tasks."""
from __future__ import annotations

import threading
from typing import Any, Callable, Iterable


class ModelTrainingWorker:
    """Handle startup ML model training in background threads."""

    def __init__(
        self,
        *,
        ultimate_ml_system: Any,
        optimized_ml_system: Any,
        dashboard_data: dict[str, Any],
        get_active_trading_universe: Callable[[], Iterable[str]],
        refresh_symbol_counters: Callable[[], None],
        best_indicators: Iterable[str],
        logger: Any | None = None,
    ) -> None:
        self.ultimate_ml_system = ultimate_ml_system
        self.optimized_ml_system = optimized_ml_system
        self.dashboard_data = dashboard_data
        self.get_active_trading_universe = get_active_trading_universe
        self.refresh_symbol_counters = refresh_symbol_counters
        self.best_indicators = list(best_indicators)
        self.logger = logger

    # Public API ----------------------------------------------------------------
    def start_ultimate_startup_training(self) -> None:
        self._start_thread(self.train_ultimate_models_on_startup, name='UltimateModelTraining')

    def start_optimized_startup_training(self) -> None:
        self._start_thread(self.train_optimized_models_on_startup, name='OptimizedModelTraining')

    # Internal helpers ----------------------------------------------------------
    def _start_thread(self, target: Callable[[], None], *, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self._log(f"✅ {name} thread dispatched")

    def train_ultimate_models_on_startup(self) -> None:
        """Train ultimate models with the legacy startup cadence."""
        status = self.dashboard_data['system_status']
        status['total_indicators'] = len(self.best_indicators)
        active_symbols = list(self.get_active_trading_universe())
        self.refresh_symbol_counters()

        self._log("🤖 Initializing ULTIMATE ML models with parallel processing...")
        models_loaded = self.ultimate_ml_system.load_models()
        loaded_active = sum(1 for sym in active_symbols if sym in self.ultimate_ml_system.models)

        if not models_loaded or loaded_active < max(1, len(active_symbols) // 2):
            self._log("📊 Training ULTIMATE ML models with parallel processing...")
            status['models_training'] = True
            success_count = self.ultimate_ml_system.train_all_ultimate_models(
                symbols=active_symbols,
                use_real_data=True,
            )
            self.ultimate_ml_system.load_models()
            status['models_loaded'] = True
            status['models_training'] = False
            self._log(
                f"✅ ULTIMATE models trained and loaded! ({success_count}/{max(1, len(active_symbols))} symbols)"
            )
        else:
            status['models_loaded'] = True
            self._log("✅ Existing ULTIMATE models loaded from storage")

        avg_indicators = self._calculate_average_indicator_usage(self.ultimate_ml_system)
        status['indicators_used'] = avg_indicators
        self._log(f"✅ ULTIMATE models ready! (Avg indicators: {avg_indicators}/{len(self.best_indicators)})")

    def train_optimized_models_on_startup(self) -> None:
        """Train optimized models with the legacy startup cadence."""
        opt_status = self.dashboard_data['optimized_system_status']
        opt_status['total_indicators'] = len(self.best_indicators)
        active_symbols = list(self.get_active_trading_universe())
        self.refresh_symbol_counters()

        self._log("🤖 Initializing OPTIMIZED ML models with parallel processing...")
        models_loaded = self.optimized_ml_system.load_models()
        loaded_active = sum(1 for sym in active_symbols if sym in self.optimized_ml_system.models)

        if not models_loaded or loaded_active < max(1, len(active_symbols) // 2):
            self._log("📊 Training OPTIMIZED ML models with parallel processing...")
            opt_status['models_training'] = True
            success_count = self.optimized_ml_system.train_all_optimized_models(
                symbols=active_symbols,
                use_real_data=True,
            )
            self.optimized_ml_system.load_models()
            opt_status['models_loaded'] = True
            opt_status['models_training'] = False
            self._log(
                f"✅ OPTIMIZED models trained and loaded! ({success_count}/{max(1, len(active_symbols))} symbols)"
            )
        else:
            opt_status['models_loaded'] = True

        avg_indicators = self._calculate_average_indicator_usage(self.optimized_ml_system)
        opt_status['indicators_used'] = avg_indicators
        self._log(f"✅ OPTIMIZED models ready! (Avg indicators: {avg_indicators}/{len(self.best_indicators)})")

    def _calculate_average_indicator_usage(self, ml_system: Any) -> int:
        total_indicators = 0
        model_count = 0
        for model_info in getattr(ml_system, 'models', {}).values():
            indicators = model_info.get('feature_count', len(model_info.get('feature_cols', [])))
            total_indicators += indicators
            model_count += 1
        if model_count == 0:
            return 0
        return total_indicators // model_count

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
                return
            except Exception:
                pass
        print(message)
