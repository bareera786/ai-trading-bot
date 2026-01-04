"""Market data refresh and performance update helpers."""
from __future__ import annotations

import copy
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Iterable

import redis


class MarketDataService:
    """Encapsulates the legacy market-data loop and dashboard refresh logic."""

    def __init__(
        self,
        *,
        dashboard_data: dict[str, Any],
        historical_data: dict[str, list[Any]],
        trading_config: dict[str, Any],
        ultimate_trader: Any,
        optimized_trader: Any,
        ultimate_ml_system: Any,
        optimized_ml_system: Any,
        parallel_engine: Any,
        futures_manual_settings: dict[str, Any],
        binance_credential_service: Any,
        get_active_trading_universe: Callable[[], Iterable[str]],
        get_real_market_data: Callable[[str], dict[str, Any] | None],
        get_trending_pairs: Callable[[], Iterable[str]],
        refresh_symbol_counters: Callable[[], Any],
        refresh_indicator_dashboard_state: Callable[[], Any],
        safe_float: Callable[[Any, float], float],
        bot_logger: Any,
        auto_user_id_provider: Callable[[], Iterable[int]] | None = None,
        persistence_manager: Any | None = None,
        symbols_for_persistence: Iterable[str] | None = None,
        sleep_interval: float = 30.0,
    ) -> None:
        self.dashboard_data = dashboard_data
        self.PHASE_ORDER: tuple[str, ...] = (
            "cycle_start",
            "fetch_market_data",
            "cache_market_data",
            "update_history",
            "ml_predict_ultimate",
            "ml_predict_optimized",
            "ensemble_correlation_ultimate",
            "ensemble_correlation_optimized",
            "ensemble_predict_ultimate",
            "ensemble_predict_optimized",
            "qfm_features_ultimate",
            "qfm_signal_ultimate",
            "qfm_features_optimized",
            "qfm_signal_optimized",
            "crt_ultimate",
            "crt_optimized",
            "trade_spot_ultimate",
            "trade_spot_optimized",
            "futures_check",
            "futures_submit",
            "persist_state",
            "dashboard_update",
            "cycle_complete",
        )
        self.historical_data = historical_data
        self.trading_config = trading_config
        self.ultimate_trader = ultimate_trader
        self.optimized_trader = optimized_trader
        self.ultimate_ml_system = ultimate_ml_system
        self.optimized_ml_system = optimized_ml_system
        self.parallel_engine = parallel_engine
        self.futures_manual_settings = futures_manual_settings
        self.binance_credential_service = binance_credential_service
        self.get_active_trading_universe = get_active_trading_universe
        self.get_real_market_data = get_real_market_data
        self.get_trending_pairs = get_trending_pairs
        self.refresh_symbol_counters = refresh_symbol_counters
        self.refresh_indicator_dashboard_state = refresh_indicator_dashboard_state
        self.safe_float = safe_float
        self.bot_logger = bot_logger
        self.auto_user_id_provider = auto_user_id_provider
        self.persistence_manager = persistence_manager
        self.symbols_for_persistence = list(symbols_for_persistence or [])
        self.sleep_interval = max(
            5.0, float(sleep_interval) if sleep_interval else 30.0
        )

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            decode_responses=True
        )

        self._user_traders: dict[int, tuple[Any, Any]] = {}
        self._user_last_save: dict[int, float] = {}

        # Lightweight per-symbol phase tracking for dashboard observability.
        # This is best-effort telemetry only and must never affect trading logic.
        self._phase_state: dict[str, dict[str, Any]] = {}

    def _set_symbol_phase(
        self,
        symbol: str,
        phase: str,
        *,
        status: str = "running",
        progress: int | None = None,
        detail: str | None = None,
    ) -> None:
        if not symbol:
            return
        try:
            now = time.time()
            entry = self._phase_state.setdefault(str(symbol), {})
            entry["current_phase"] = str(phase)
            entry["updated_at"] = now

            phases = entry.setdefault("phases", {})
            if not isinstance(phases, dict):
                phases = {}
                entry["phases"] = phases

            phase_payload = phases.setdefault(str(phase), {})
            if not isinstance(phase_payload, dict):
                phase_payload = {}
                phases[str(phase)] = phase_payload

            phase_payload["status"] = str(status)
            if progress is not None:
                try:
                    phase_payload["progress"] = max(0, min(100, int(progress)))
                except Exception:
                    pass
            if detail is not None:
                phase_payload["detail"] = str(detail)
            phase_payload["updated_at"] = now
        except Exception:
            return

    def get_phase_order(self) -> list[str]:
        return list(self.PHASE_ORDER)

    def get_phase_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a safe snapshot of current phase state."""
        try:
            return copy.deepcopy(self._phase_state)
        except Exception:
            try:
                return {k: dict(v) for k, v in (self._phase_state or {}).items()}
            except Exception:
                return {}

    def _resolve_auto_user_ids(self) -> list[int]:
        if self.auto_user_id_provider:
            try:
                resolved = list(self.auto_user_id_provider() or [])
                return [int(uid) for uid in resolved if str(uid).strip().isdigit()]
            except Exception:
                # Fall back to credential store enumeration.
                pass
        service = self.binance_credential_service
        store = getattr(service, "credentials_store", None)
        list_ids = getattr(store, "list_user_ids", None)
        if callable(list_ids):
            try:
                return list_ids() or []
            except Exception:
                return []
        return []

    def _user_profile_name(self, user_id: int) -> str:
        return f"user_{int(user_id)}"

    def _get_or_create_user_traders(self, user_id: int) -> tuple[Any, Any]:
        cached = self._user_traders.get(user_id)
        if cached is not None:
            cached_ultimate, cached_optimized = cached
            expected_profile = self._user_profile_name(user_id)
            # Invariant: cached traders must remain bound to the same user.
            assert getattr(cached_ultimate, "user_id", None) == int(user_id)
            assert getattr(cached_optimized, "user_id", None) == int(user_id)
            assert getattr(cached_ultimate, "persistence_profile", None) == expected_profile
            assert getattr(cached_optimized, "persistence_profile", None) == expected_profile
            return cached

        base_ultimate = self.ultimate_trader
        base_optimized = self.optimized_trader
        ultimate_cls = type(base_ultimate)
        optimized_cls = type(base_optimized)

        initial_balance = getattr(base_ultimate, "initial_balance", 10000)
        ultimate = ultimate_cls(initial_balance=initial_balance)
        optimized = optimized_cls(initial_balance=initial_balance)

        profile = self._user_profile_name(user_id)
        setattr(ultimate, "persistence_profile", profile)
        setattr(optimized, "persistence_profile", profile)

        # Stamp user_id so trade recording and other user-scoped hooks can
        # attribute state correctly in multi-user mode.
        setattr(ultimate, "user_id", int(user_id))
        setattr(optimized, "user_id", int(user_id))

        # Invariant: multi-user traders must be stamped correctly.
        assert getattr(ultimate, "user_id", None) == int(user_id)
        assert getattr(optimized, "user_id", None) == int(user_id)
        assert getattr(ultimate, "persistence_profile", None) == profile
        assert getattr(optimized, "persistence_profile", None) == profile

        # Apply user credentials (spot) to the user-scoped trader instances.
        store = getattr(self.binance_credential_service, "credentials_store", None)
        if store is not None:
            try:
                spot = store.get_credentials("spot", user_id=user_id)
            except Exception:
                spot = {}
            if isinstance(spot, dict) and spot.get("api_key") and spot.get("api_secret"):
                try:
                    ultimate.enable_real_trading(
                        api_key=spot.get("api_key"),
                        api_secret=spot.get("api_secret"),
                        testnet=spot.get("testnet", True),
                    )
                    optimized.enable_real_trading(
                        api_key=spot.get("api_key"),
                        api_secret=spot.get("api_secret"),
                        testnet=spot.get("testnet", True),
                    )
                except Exception:
                    pass

        # Restore user-scoped trader state from persistence if available.
        if self.persistence_manager and hasattr(self.persistence_manager, "load_complete_state"):
            try:
                self.persistence_manager.load_complete_state(
                    ultimate,
                    self.ultimate_ml_system,
                    profile=profile,
                    restore_ml_state=False,
                    restore_futures_settings=False,
                )
            except TypeError:
                # Older persistence signature - best effort fallback.
                try:
                    self.persistence_manager.load_complete_state(ultimate, self.ultimate_ml_system)
                except Exception:
                    pass
            except Exception:
                pass

        self._user_traders[user_id] = (ultimate, optimized)
        return ultimate, optimized

    def _maybe_persist_user_state(self, user_id: int, user_trader: Any) -> None:
        if not self.persistence_manager or not hasattr(self.persistence_manager, "save_complete_state"):
            return

        now = time.time()
        last = self._user_last_save.get(user_id, 0.0)
        interval_min = float(self.trading_config.get("persistence_interval_minutes", 5) or 5)
        interval_sec = max(60.0, interval_min * 60.0)
        if now - last < interval_sec:
            return

        symbols = self.symbols_for_persistence or list(self.get_active_trading_universe() or [])
        profile = self._user_profile_name(user_id)
        try:
            self.persistence_manager.save_complete_state(
                user_trader,
                self.ultimate_ml_system,
                self.trading_config,
                list(symbols),
                self.historical_data,
                profile=profile,
            )
            self._user_last_save[user_id] = now
        except TypeError:
            # Older persistence signature
            try:
                self.persistence_manager.save_complete_state(
                    user_trader,
                    self.ultimate_ml_system,
                    self.trading_config,
                    list(symbols),
                    self.historical_data,
                )
                self._user_last_save[user_id] = now
            except Exception:
                pass
        except Exception:
            pass

    def _get_cached_market_data(self, symbol: str) -> dict[str, Any] | None:
        """Get market data from cache if available and fresh."""
        cache_key = f"market_data:{symbol}"
        cached = self.redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
        return None

    def _set_cached_market_data(self, symbol: str, data: dict[str, Any], ttl: int = 30) -> None:
        """Cache market data with TTL."""
        cache_key = f"market_data:{symbol}"
        import json
        self.redis_client.setex(cache_key, ttl, json.dumps(data))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="MarketDataServiceLoop", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.sleep_interval)
        self._thread = None

    def run_once(self) -> None:
        system_status = self.dashboard_data.get("system_status", {})
        if system_status.get("models_training"):
            print("⏳ Waiting for ULTIMATE ML models to finish training...")
            time.sleep(5)
            return

        active_symbols = list(self.get_active_trading_universe() or [])
        self.refresh_symbol_counters()
        self.refresh_indicator_dashboard_state()
        print("\n🔄 ULTIMATE Market Data Update with All Advanced Systems...")

        # Reset phase state for symbols no longer active.
        try:
            active_set = set(active_symbols)
            for sym in list(self._phase_state.keys()):
                if sym not in active_set:
                    self._phase_state.pop(sym, None)
        except Exception:
            pass

        market_data: dict[str, Any] = {}
        ml_predictions: dict[str, Any] = {}
        ai_signals: dict[str, Any] = {}
        crt_signals: dict[str, Any] = {}
        qfm_signals: dict[str, Any] = {}
        optimized_ml_predictions: dict[str, Any] = {}
        optimized_ai_signals: dict[str, Any] = {}
        optimized_crt_signals: dict[str, Any] = {}
        optimized_qfm_signals: dict[str, Any] = {}

        trending_pairs = list(self.get_trending_pairs() or [])
        self.dashboard_data["trending_pairs"] = [
            pair for pair in trending_pairs if pair in active_symbols
        ]
        ultimate_qfm_engine = getattr(self.ultimate_trader, "qfm_engine", None)
        optimized_qfm_engine = getattr(self.optimized_trader, "qfm_engine", None)

        user_ids = self._resolve_auto_user_ids()
        primary_user_id = user_ids[0] if user_ids else None

        for symbol in active_symbols:
            self._set_symbol_phase(symbol, "cycle_start", progress=0)
            self._set_symbol_phase(symbol, "fetch_market_data", progress=5)
            cached_data = self._get_cached_market_data(symbol)
            if cached_data:
                self._set_symbol_phase(symbol, "cache_market_data", status="ok", progress=10, detail="redis")
                real_data = cached_data
            else:
                real_data = self.get_real_market_data(symbol) or {}
                if real_data:
                    self._set_symbol_phase(symbol, "cache_market_data", status="ok", progress=10, detail="origin")
                    self._set_cached_market_data(symbol, real_data)
            if real_data:
                market_data[symbol] = real_data
                history = self.historical_data.setdefault(symbol, [])
                history.append(real_data.get("price"))
                if len(history) > 100:
                    history.pop(0)
                self._set_symbol_phase(symbol, "fetch_market_data", status="ok", progress=15)
                self._set_symbol_phase(symbol, "update_history", status="ok", progress=20)
            else:
                self._set_symbol_phase(symbol, "fetch_market_data", status="error", progress=15)
                self._set_symbol_phase(symbol, "update_history", status="error", progress=20)

        if self.trading_config.get("parallel_processing"):
            if market_data:
                for symbol in active_symbols:
                    if symbol in market_data:
                        self._set_symbol_phase(symbol, "ml_predict_ultimate", progress=25)
                        self._set_symbol_phase(symbol, "ml_predict_optimized", progress=25)
                ml_predictions = self.parallel_engine.parallel_predict(
                    active_symbols, market_data, self.ultimate_ml_system
                )
                optimized_ml_predictions = self.parallel_engine.parallel_predict(
                    active_symbols, market_data, self.optimized_ml_system
                )
                for symbol in active_symbols:
                    if symbol in market_data:
                        self._set_symbol_phase(symbol, "ml_predict_ultimate", status="ok", progress=40)
                        self._set_symbol_phase(symbol, "ml_predict_optimized", status="ok", progress=40)
        else:
            for symbol in active_symbols:
                snapshot = market_data.get(symbol)
                if not snapshot:
                    continue
                self._set_symbol_phase(symbol, "ml_predict_ultimate", progress=25)
                pred = self.ultimate_ml_system.predict_ultimate(symbol, snapshot)
                if pred:
                    ml_predictions[symbol] = pred
                self._set_symbol_phase(symbol, "ml_predict_ultimate", status="ok", progress=40)

                self._set_symbol_phase(symbol, "ml_predict_optimized", progress=25)
                opt_pred = self.optimized_ml_system.predict_professional(
                    symbol, snapshot
                )
                if opt_pred:
                    optimized_ml_predictions[symbol] = opt_pred
                self._set_symbol_phase(symbol, "ml_predict_optimized", status="ok", progress=40)

        if ml_predictions:
            for symbol in ml_predictions.keys():
                self._set_symbol_phase(symbol, "ensemble_correlation_ultimate", progress=50)
            self.ultimate_ml_system.ensemble_system.create_correlation_matrix(
                ml_predictions
            )
            for symbol in ml_predictions.keys():
                self._set_symbol_phase(
                    symbol, "ensemble_correlation_ultimate", status="ok", progress=55
                )
        if optimized_ml_predictions:
            for symbol in optimized_ml_predictions.keys():
                self._set_symbol_phase(symbol, "ensemble_correlation_optimized", progress=50)
            self.optimized_ml_system.ensemble_system.create_correlation_matrix(
                optimized_ml_predictions
            )
            for symbol in optimized_ml_predictions.keys():
                self._set_symbol_phase(
                    symbol, "ensemble_correlation_optimized", status="ok", progress=55
                )

        ensemble_prediction = (
            self.ultimate_ml_system.ensemble_system.get_ensemble_prediction(
                ml_predictions, market_data
            )
        )
        optimized_ensemble_prediction = (
            self.optimized_ml_system.ensemble_system.get_ensemble_prediction(
                optimized_ml_predictions, market_data
            )
        )
        self.dashboard_data["ensemble_predictions"] = ensemble_prediction or {}
        self.dashboard_data["optimized_ensemble_predictions"] = (
            optimized_ensemble_prediction or {}
        )

        for symbol in active_symbols:
            if symbol in market_data:
                self._set_symbol_phase(
                    symbol, "ensemble_predict_ultimate", status="ok", progress=60
                )
                self._set_symbol_phase(
                    symbol, "ensemble_predict_optimized", status="ok", progress=60
                )

        for symbol in active_symbols:
            history = self.historical_data.get(symbol, [])
            market_snapshot = market_data.get(symbol)

            if market_snapshot:
                self._set_symbol_phase(symbol, "qfm_features_ultimate", progress=62)
            if ultimate_qfm_engine and market_snapshot:
                try:
                    ultimate_qfm_engine.compute_realtime_features(
                        symbol, market_snapshot, history
                    )
                    self._set_symbol_phase(
                        symbol, "qfm_features_ultimate", status="ok", progress=64
                    )
                    qfm_signal = ultimate_qfm_engine.generate_signal(symbol)
                    self._set_symbol_phase(symbol, "qfm_signal_ultimate", progress=66)
                    if qfm_signal:
                        qfm_signals[symbol] = self._format_qfm_signal(
                            qfm_signal, market_snapshot, symbol
                        )
                    self._set_symbol_phase(
                        symbol, "qfm_signal_ultimate", status="ok", progress=68
                    )
                except Exception as exc:
                    self.bot_logger.warning(
                        "Ultimate QFM update failed for %s: %s", symbol, exc
                    )
            if optimized_qfm_engine and market_snapshot:
                try:
                    self._set_symbol_phase(symbol, "qfm_features_optimized", progress=62)
                    optimized_qfm_engine.compute_realtime_features(
                        symbol, market_snapshot, history
                    )
                    self._set_symbol_phase(
                        symbol, "qfm_features_optimized", status="ok", progress=64
                    )
                    self._set_symbol_phase(symbol, "qfm_signal_optimized", progress=66)
                    opt_signal = optimized_qfm_engine.generate_signal(symbol)
                    if opt_signal:
                        optimized_qfm_signals[symbol] = self._format_qfm_signal(
                            opt_signal, market_snapshot, symbol
                        )
                    self._set_symbol_phase(
                        symbol, "qfm_signal_optimized", status="ok", progress=68
                    )
                except Exception as exc:
                    self.bot_logger.warning(
                        "Optimized QFM update failed for %s: %s", symbol, exc
                    )

            if market_snapshot:
                self._set_symbol_phase(symbol, "qfm", status="ok", progress=70)

            if market_snapshot and len(history) >= 20:
                self._set_symbol_phase(symbol, "crt_ultimate", progress=70)
                crt_signal = self.ultimate_ml_system.generate_crt_signals(
                    symbol, market_snapshot, history
                )
                self._set_symbol_phase(symbol, "crt_ultimate", status="ok", progress=74)

                self._set_symbol_phase(symbol, "crt_optimized", progress=70)
                optimized_crt_signal = self.optimized_ml_system.generate_crt_signals(
                    symbol, market_snapshot, history
                )
                self._set_symbol_phase(symbol, "crt", status="ok", progress=80)

                # Multi-user auto-trading: execute the same shared signals across
                # isolated per-user trader instances.
                if user_ids:
                    for uid in user_ids:
                        user_ultimate, user_optimized = self._get_or_create_user_traders(uid)

                        # Defensive copies: traders must not be able to mutate shared
                        # market snapshots or shared history across users.
                        per_user_snapshot = (
                            dict(market_snapshot)
                            if isinstance(market_snapshot, dict)
                            else market_snapshot
                        )
                        per_user_history = list(history)

                        # Defensive copies: prediction and ensemble objects must not
                        # be mutated across users. Use deep-copy to prevent nested
                        # structures (e.g., RIBS payloads) from being shared.
                        per_user_prediction = ml_predictions.get(symbol)
                        if per_user_prediction is not None:
                            try:
                                per_user_prediction = copy.deepcopy(per_user_prediction)
                            except Exception:
                                if isinstance(per_user_prediction, dict):
                                    per_user_prediction = dict(per_user_prediction)
                                elif isinstance(per_user_prediction, list):
                                    per_user_prediction = list(per_user_prediction)

                        per_user_opt_prediction = optimized_ml_predictions.get(symbol)
                        if per_user_opt_prediction is not None:
                            try:
                                per_user_opt_prediction = copy.deepcopy(per_user_opt_prediction)
                            except Exception:
                                if isinstance(per_user_opt_prediction, dict):
                                    per_user_opt_prediction = dict(per_user_opt_prediction)
                                elif isinstance(per_user_opt_prediction, list):
                                    per_user_opt_prediction = list(per_user_opt_prediction)

                        per_user_ensemble = ensemble_prediction
                        if per_user_ensemble is not None:
                            try:
                                per_user_ensemble = copy.deepcopy(per_user_ensemble)
                            except Exception:
                                if isinstance(per_user_ensemble, dict):
                                    per_user_ensemble = dict(per_user_ensemble)
                                elif isinstance(per_user_ensemble, list):
                                    per_user_ensemble = list(per_user_ensemble)

                        per_user_opt_ensemble = optimized_ensemble_prediction
                        if per_user_opt_ensemble is not None:
                            try:
                                per_user_opt_ensemble = copy.deepcopy(per_user_opt_ensemble)
                            except Exception:
                                if isinstance(per_user_opt_ensemble, dict):
                                    per_user_opt_ensemble = dict(per_user_opt_ensemble)
                                elif isinstance(per_user_opt_ensemble, list):
                                    per_user_opt_ensemble = list(per_user_opt_ensemble)

                        success, message = user_ultimate.execute_ultimate_trade(
                            symbol,
                            per_user_prediction,
                            per_user_snapshot,
                            per_user_history,
                            per_user_ensemble,
                        )
                        opt_success, opt_message = user_optimized.execute_ultimate_trade(
                            symbol,
                            per_user_opt_prediction,
                            per_user_snapshot,
                            per_user_history,
                            per_user_opt_ensemble,
                        )

                        # Track primary user's visible phase as "trade".
                        if primary_user_id is not None and uid == primary_user_id:
                            self._set_symbol_phase(
                                symbol,
                                "trade_spot_ultimate",
                                status="ok" if success or opt_success else "running",
                                progress=95,
                                detail=str(message or opt_message or "")[:200] or None,
                            )
                            self._set_symbol_phase(
                                symbol,
                                "trade_spot_optimized",
                                status="ok" if opt_success else "running",
                                progress=92,
                                detail=str(opt_message or "")[:200] or None,
                            )

                        # Execute futures trades if futures trading is enabled (per-user)
                        if (
                            self.trading_config.get("futures_enabled")
                            and getattr(user_ultimate, "futures_trading_enabled", False)
                            and getattr(user_ultimate, "futures_trader", None)
                        ):
                            if primary_user_id is not None and uid == primary_user_id:
                                self._set_symbol_phase(symbol, "futures_check", status="ok", progress=93)
                            if success and message and "BUY" in str(message).upper():
                                if primary_user_id is not None and uid == primary_user_id:
                                    self._set_symbol_phase(symbol, "futures_submit", progress=94)
                                futures_response = user_ultimate._submit_futures_order(
                                    symbol, "BUY", 0.001, leverage=3
                                )
                                if futures_response and primary_user_id is not None and uid == primary_user_id:
                                    self._set_symbol_phase(symbol, "futures_submit", status="ok", progress=96)
                                    futures_message = f"Futures LONG {symbol} executed"
                                    print(f"🤖 {futures_message}")
                                    self.dashboard_data["system_status"]["last_futures_trade"] = {
                                        "symbol": symbol,
                                        "message": futures_message,
                                        "timestamp": datetime.now(),
                                    }
                            elif success and message and "SELL" in str(message).upper():
                                if primary_user_id is not None and uid == primary_user_id:
                                    self._set_symbol_phase(symbol, "futures_submit", progress=94)
                                futures_response = user_ultimate._submit_futures_order(
                                    symbol, "SELL", 0.001, leverage=3
                                )
                                if futures_response and primary_user_id is not None and uid == primary_user_id:
                                    self._set_symbol_phase(symbol, "futures_submit", status="ok", progress=96)
                                    futures_message = f"Futures SHORT {symbol} executed"
                                    print(f"🤖 {futures_message}")
                                    self.dashboard_data["system_status"]["last_futures_trade"] = {
                                        "symbol": symbol,
                                        "message": futures_message,
                                        "timestamp": datetime.now(),
                                    }

                        # Persist the user-scoped trader state on an interval.
                        if primary_user_id is not None and uid == primary_user_id:
                            self._set_symbol_phase(symbol, "persist_state", progress=97)
                        self._maybe_persist_user_state(uid, user_ultimate)
                        if primary_user_id is not None and uid == primary_user_id:
                            self._set_symbol_phase(symbol, "persist_state", status="ok", progress=98)

                        # Preserve legacy dashboard behaviour by binding
                        # displayed state to a single primary user.
                        if primary_user_id is not None and uid == primary_user_id:
                            self._set_symbol_phase(symbol, "dashboard_update", progress=99)
                            crt_signals[symbol] = crt_signal
                            optimized_crt_signals[symbol] = optimized_crt_signal

                            if success:
                                print(f"🤖 {message}")
                                self.dashboard_data["system_status"]["last_trade"] = {
                                    "symbol": symbol,
                                    "message": message,
                                    "timestamp": datetime.now(),
                                }
                            ai_signals[symbol] = self._build_ai_signal(
                                user_ultimate,
                                ml_predictions.get(symbol),
                                ensemble_prediction,
                                success,
                                message,
                                crt_signal,
                            )

                            if opt_success:
                                print(f"🤖 {opt_message}")
                                self.dashboard_data["optimized_system_status"]["last_trade"] = {
                                    "symbol": symbol,
                                    "message": opt_message,
                                    "timestamp": datetime.now(),
                                }
                            optimized_ai_signals[symbol] = self._build_ai_signal(
                                user_optimized,
                                optimized_ml_predictions.get(symbol),
                                optimized_ensemble_prediction,
                                opt_success,
                                opt_message,
                                optimized_crt_signal,
                            )
                            self._set_symbol_phase(symbol, "dashboard_update", status="ok", progress=100)
                            self._set_symbol_phase(symbol, "cycle_complete", status="ok", progress=100)
                else:
                    # Legacy single-runtime behaviour
                    crt_signals[symbol] = crt_signal
                    optimized_crt_signals[symbol] = optimized_crt_signal

                    success, message = self.ultimate_trader.execute_ultimate_trade(
                        symbol,
                        ml_predictions.get(symbol),
                        market_snapshot,
                        history,
                        ensemble_prediction,
                    )
                    self._set_symbol_phase(
                        symbol,
                        "trade_spot_ultimate",
                        status="ok" if success else "running",
                        progress=90,
                        detail=str(message or "")[:200] or None,
                    )
                    if success:
                        print(f"🤖 {message}")
                        self.dashboard_data["system_status"]["last_trade"] = {
                            "symbol": symbol,
                            "message": message,
                            "timestamp": datetime.now(),
                        }
                    ai_signals[symbol] = self._build_ai_signal(
                        self.ultimate_trader,
                        ml_predictions.get(symbol),
                        ensemble_prediction,
                        success,
                        message,
                        crt_signal,
                    )

                    opt_success, opt_message = self.optimized_trader.execute_ultimate_trade(
                        symbol,
                        optimized_ml_predictions.get(symbol),
                        market_snapshot,
                        history,
                        optimized_ensemble_prediction,
                    )
                    self._set_symbol_phase(
                        symbol,
                        "trade_spot_optimized",
                        status="ok" if opt_success else "running",
                        progress=92,
                        detail=str(opt_message or "")[:200] or None,
                    )
                    self._set_symbol_phase(symbol, "dashboard_update", status="ok", progress=100)
                    self._set_symbol_phase(symbol, "cycle_complete", status="ok", progress=100)
                    if opt_success:
                        print(f"🤖 {opt_message}")
                        self.dashboard_data["optimized_system_status"]["last_trade"] = {
                            "symbol": symbol,
                            "message": opt_message,
                            "timestamp": datetime.now(),
                        }
                    optimized_ai_signals[symbol] = self._build_ai_signal(
                        self.optimized_trader,
                        optimized_ml_predictions.get(symbol),
                        optimized_ensemble_prediction,
                        opt_success,
                        opt_message,
                        optimized_crt_signal,
                    )

                # Execute futures trades if futures trading is enabled (legacy single-runtime)
                if (
                    self.trading_config.get("futures_enabled")
                    and getattr(self.ultimate_trader, "futures_trading_enabled", False)
                    and getattr(self.ultimate_trader, "futures_trader", None)
                ):
                    if success and message and "BUY" in str(message).upper():
                        futures_response = self.ultimate_trader._submit_futures_order(
                            symbol, "BUY", 0.001, leverage=3
                        )
                        if futures_response:
                            futures_message = f"Futures LONG {symbol} executed"
                            print(f"🤖 {futures_message}")
                            self.dashboard_data["system_status"]["last_futures_trade"] = {
                                "symbol": symbol,
                                "message": futures_message,
                                "timestamp": datetime.now(),
                            }
                    elif success and message and "SELL" in str(message).upper():
                        futures_response = self.ultimate_trader._submit_futures_order(
                            symbol, "SELL", 0.001, leverage=3
                        )
                        if futures_response:
                            futures_message = f"Futures SHORT {symbol} executed"
                            print(f"🤖 {futures_message}")
                            self.dashboard_data["system_status"]["last_futures_trade"] = {
                                "symbol": symbol,
                                "message": futures_message,
                                "timestamp": datetime.now(),
                            }
            else:
                ai_signals[symbol] = self._build_default_signal()
                optimized_ai_signals[symbol] = self._build_default_signal()
                optimized_crt_signals[symbol] = {"signal": "HOLD", "confidence": 0.5}

        self.dashboard_data["market_data"] = market_data
        self.dashboard_data["ml_predictions"] = ml_predictions
        self.dashboard_data["ai_signals"] = ai_signals
        self.dashboard_data["crt_signals"] = crt_signals
        self.dashboard_data["qfm_signals"] = qfm_signals
        self.dashboard_data["optimized_ml_predictions"] = optimized_ml_predictions
        self.dashboard_data["optimized_ai_signals"] = optimized_ai_signals
        self.dashboard_data["optimized_crt_signals"] = optimized_crt_signals
        self.dashboard_data["optimized_qfm_signals"] = optimized_qfm_signals

        # Bind dashboard-visible portfolio to the primary user if multi-user.
        if user_ids and primary_user_id is not None:
            primary_ultimate, primary_optimized = self._get_or_create_user_traders(primary_user_id)
            primary_ultimate.latest_market_data = market_data
            primary_optimized.latest_market_data = market_data
            primary_ultimate.update_auto_take_profit_orders(market_data)
            ultimate_for_dashboard = primary_ultimate
            optimized_for_dashboard = primary_optimized
        else:
            self.ultimate_trader.latest_market_data = market_data
            self.optimized_trader.latest_market_data = market_data
            self.ultimate_trader.update_auto_take_profit_orders(market_data)
            ultimate_for_dashboard = self.ultimate_trader
            optimized_for_dashboard = self.optimized_trader
        current_prices = {
            symbol: data["price"]
            for symbol, data in market_data.items()
            if "price" in data
        }
        for message in ultimate_for_dashboard.check_advanced_stop_loss(current_prices):
            print(f"🤖 {message}")
        for message in optimized_for_dashboard.check_advanced_stop_loss(current_prices):
            print(f"🤖 {message}")

        portfolio = ultimate_for_dashboard.get_portfolio_summary(current_prices)
        optimized_portfolio = optimized_for_dashboard.get_portfolio_summary(
            current_prices
        )
        self.dashboard_data["portfolio"] = portfolio
        self.dashboard_data["optimized_portfolio"] = optimized_portfolio
        self.dashboard_data[
            "trade_statistics"
        ] = ultimate_for_dashboard.get_trade_statistics()
        self.dashboard_data[
            "optimized_trade_statistics"
        ] = optimized_for_dashboard.get_trade_statistics()

        self._update_system_status(ultimate_for_dashboard, portfolio)
        self._update_optimized_status(optimized_for_dashboard, optimized_portfolio)

        self.dashboard_data[
            "safety_status"
        ] = ultimate_for_dashboard.safety_manager.get_status_snapshot()
        self.dashboard_data[
            "optimized_safety_status"
        ] = optimized_for_dashboard.safety_manager.get_status_snapshot()
        self.dashboard_data[
            "real_trading_status"
        ] = ultimate_for_dashboard.get_real_trading_status()
        self.dashboard_data[
            "optimized_real_trading_status"
        ] = optimized_for_dashboard.get_real_trading_status()
        self.dashboard_data[
            "binance_credentials"
        ] = (
            self.binance_credential_service.get_status(
                user_id=primary_user_id, include_connection=True
            )
            if user_ids and primary_user_id is not None
            else self.binance_credential_service.get_status(include_connection=True)
        )

        journal_events = [
            {**event, "_profile": "ultimate"}
            for event in ultimate_for_dashboard.trade_history.get_journal_events(limit=50)
        ]
        if hasattr(optimized_for_dashboard.trade_history, "get_journal_events"):
            journal_events.extend(
                {**event, "_profile": "optimized"}
                for event in optimized_for_dashboard.trade_history.get_journal_events(
                    limit=50
                )
            )
            journal_events.sort(key=lambda ev: ev.get("timestamp", ""), reverse=True)
        self.dashboard_data["journal_events"] = journal_events[:50]
        self.dashboard_data["backtest_results"] = {
            "ultimate": self.ultimate_ml_system.get_backtest_results(),
            "optimized": self.optimized_ml_system.get_backtest_results(),
        }

        self._update_portfolio_efficiency(portfolio, optimized_portfolio)
        self.update_performance_metrics()
        now = time.time()
        self.dashboard_data["last_update"] = now
        self.dashboard_data["optimized_last_update"] = now

        self._log_status_summary(
            active_symbols,
            ai_signals,
            optimized_ai_signals,
            portfolio,
            optimized_portfolio,
            crt_signals,
            optimized_crt_signals,
        )

    def update_performance_metrics(self) -> None:
        try:
            performance = self.ultimate_trader.trade_history.get_trade_statistics()[
                "summary"
            ]
            self.dashboard_data["performance"] = performance
            optimized_performance = (
                self.optimized_trader.trade_history.get_trade_statistics()["summary"]
            )
            self.dashboard_data["optimized_performance"] = optimized_performance

            portfolio = self.dashboard_data.get("portfolio", {})
            optimized_portfolio = self.dashboard_data.get("optimized_portfolio", {})
            if "bot_efficiency" in portfolio:
                self.dashboard_data["system_status"]["bot_efficiency"] = portfolio[
                    "bot_efficiency"
                ]["success_rate"]
                self.dashboard_data["system_status"]["learning_cycles"] = portfolio[
                    "bot_efficiency"
                ]["learning_cycles"]
            if "bot_efficiency" in optimized_portfolio:
                self.dashboard_data["optimized_system_status"][
                    "bot_efficiency"
                ] = optimized_portfolio["bot_efficiency"]["success_rate"]
                self.dashboard_data["optimized_system_status"][
                    "learning_cycles"
                ] = optimized_portfolio["bot_efficiency"]["learning_cycles"]

            if self.ultimate_ml_system.models:
                indicators, count = 0, 0
                for model in self.ultimate_ml_system.models.values():
                    indicators += model.get(
                        "feature_count", len(model.get("feature_cols", []))
                    )
                    count += 1
                self.dashboard_data["system_status"]["indicators_used"] = (
                    indicators // count if count else 0
                )
            if self.optimized_ml_system.models:
                indicators, count = 0, 0
                for model in self.optimized_ml_system.models.values():
                    indicators += model.get(
                        "feature_count", len(model.get("feature_cols", []))
                    )
                    count += 1
                self.dashboard_data["optimized_system_status"]["indicators_used"] = (
                    indicators // count if count else 0
                )
                self.dashboard_data["optimized_system_status"]["models_loaded"] = True

            self.dashboard_data["ml_telemetry"][
                "ultimate"
            ] = self.ultimate_ml_system.get_ml_telemetry()
            self.dashboard_data["ml_telemetry"][
                "optimized"
            ] = self.optimized_ml_system.get_ml_telemetry()
            self.dashboard_data["system_status"]["ensemble_active"] = bool(
                self.ultimate_ml_system.ensemble_system.correlation_matrix
            )
            self.dashboard_data["optimized_system_status"]["ensemble_active"] = bool(
                self.optimized_ml_system.ensemble_system.correlation_matrix
            )
        except Exception as exc:
            print(f"❌ Performance metrics error: {exc}")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as exc:
                print(f"❌ Ultimate market update error: {exc}")
            self._stop_event.wait(self.sleep_interval)

    def _format_qfm_signal(
        self, signal: dict[str, Any], snapshot: dict[str, Any], symbol: str
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "signal": signal.get("signal", "HOLD"),
            "confidence": float(signal.get("confidence", 0.0) or 0.0),
            "score": float(signal.get("score", 0.0) or 0.0),
            "metrics": signal.get("metrics", {}),
            "price": self.safe_float(snapshot.get("price")),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _build_ai_signal(
        self, trader, prediction, ensemble_prediction, success, message, crt_signal
    ):
        signal_block = (prediction or {}).get(
            getattr(trader, "indicator_block_key", "ultimate_ensemble"), {}
        )
        return {
            "action_taken": success,
            "message": message,
            "market_regime": trader.ensemble_system.market_regime,
            "indicators_used": signal_block.get("indicators_total", 0),
            "data_source": signal_block.get("data_source", "UNKNOWN"),
            "ensemble_used": ensemble_prediction is not None,
            "market_stress": trader.risk_manager.market_stress_indicator,
            "crt_signal": (crt_signal or {}).get("signal", "HOLD"),
        }

    def _build_default_signal(self):
        return {
            "action_taken": False,
            "message": "Insufficient historical data",
            "market_regime": "NEUTRAL",
            "indicators_used": 0,
            "data_source": "UNKNOWN",
            "ensemble_used": False,
            "market_stress": 0.0,
            "crt_signal": "HOLD",
        }

    def _update_system_status(self, trader: Any, portfolio: dict[str, Any]) -> None:
        status = self.dashboard_data["system_status"]
        status["market_regime"] = trader.ensemble_system.market_regime
        status[
            "risk_adjustment"
        ] = trader.risk_manager.get_risk_multiplier()
        status[
            "market_stress"
        ] = trader.risk_manager.market_stress_indicator
        status["risk_profile"] = trader.risk_manager.current_risk_profile
        status["trading_enabled"] = trader.trading_enabled
        status["paper_trading"] = trader.paper_trading
        status["real_trading_ready"] = bool(trader.real_trading_enabled)
        status["futures_trading_ready"] = bool(
            getattr(trader, "futures_trading_enabled", False)
        )
        status["futures_manual_auto_trade"] = self.futures_manual_settings.get(
            "auto_trade_enabled", False
        )
        if "bot_efficiency" in portfolio:
            status["bot_efficiency"] = portfolio["bot_efficiency"]["success_rate"]
            status["learning_cycles"] = portfolio["bot_efficiency"]["learning_cycles"]

    def _update_optimized_status(self, trader: Any, portfolio: dict[str, Any]) -> None:
        status = self.dashboard_data["optimized_system_status"]
        status["market_regime"] = trader.ensemble_system.market_regime
        status[
            "risk_adjustment"
        ] = trader.risk_manager.get_risk_multiplier()
        status[
            "market_stress"
        ] = trader.risk_manager.market_stress_indicator
        status["risk_profile"] = trader.risk_manager.current_risk_profile
        status["trading_enabled"] = trader.trading_enabled
        status["paper_trading"] = trader.paper_trading
        status["real_trading_ready"] = bool(trader.real_trading_enabled)
        if "bot_efficiency" in portfolio:
            status["bot_efficiency"] = portfolio["bot_efficiency"]["success_rate"]
            status["learning_cycles"] = portfolio["bot_efficiency"]["learning_cycles"]

    def _update_portfolio_efficiency(
        self, ultimate_portfolio: dict[str, Any], optimized_portfolio: dict[str, Any]
    ) -> None:
        if "bot_efficiency" in ultimate_portfolio:
            self.dashboard_data["system_status"]["bot_efficiency"] = ultimate_portfolio[
                "bot_efficiency"
            ]["success_rate"]
            self.dashboard_data["system_status"][
                "learning_cycles"
            ] = ultimate_portfolio["bot_efficiency"]["learning_cycles"]
        if "bot_efficiency" in optimized_portfolio:
            self.dashboard_data["optimized_system_status"][
                "bot_efficiency"
            ] = optimized_portfolio["bot_efficiency"]["success_rate"]
            self.dashboard_data["optimized_system_status"][
                "learning_cycles"
            ] = optimized_portfolio["bot_efficiency"]["learning_cycles"]

    def _log_status_summary(
        self,
        active_symbols,
        ai_signals,
        optimized_ai_signals,
        portfolio,
        optimized_portfolio,
        crt_signals,
        optimized_crt_signals,
    ):
        active_count = len([s for s in ai_signals.values() if s.get("action_taken")])
        sys_status = self.dashboard_data["system_status"]
        summary = (
            f"📊 ULTIMATE Update — symbols={len(active_symbols)} | AI Signals={active_count} | "
            f"ML={'✅' if sys_status.get('models_loaded') else '🔄'} | "
            f"Indicators={sys_status.get('indicators_used', 0)} | "
            f"Efficiency={sys_status.get('bot_efficiency', 0):.1f}% | "
            f"Regime={sys_status.get('market_regime', 'NEUTRAL')} | "
            f"Stress={sys_status.get('market_stress', 0):.2f} | "
            f"Risk={sys_status.get('risk_profile', 'moderate')} | "
            f"Positions={len(portfolio.get('positions', []))} | "
            f"Portfolio=${self.safe_float(portfolio.get('total_portfolio_value'), 0.0):.2f} | "
            f"CRT Signals={len(crt_signals)}"
        )
        self.bot_logger.info(summary)

        opt_active_count = len(
            [s for s in optimized_ai_signals.values() if s.get("action_taken")]
        )
        opt_status = self.dashboard_data["optimized_system_status"]
        opt_summary = (
            f"📊 OPTIMIZED Update — symbols={len(active_symbols)} | AI Signals={opt_active_count} | "
            f"ML={'✅' if opt_status.get('models_loaded') else '🔄'} | "
            f"Indicators={opt_status.get('indicators_used', 0)} | "
            f"Efficiency={opt_status.get('bot_efficiency', 0):.1f}% | "
            f"Regime={opt_status.get('market_regime', 'NEUTRAL')} | "
            f"Stress={opt_status.get('market_stress', 0):.2f} | "
            f"Risk={opt_status.get('risk_profile', 'moderate')} | "
            f"Positions={len(optimized_portfolio.get('positions', []))} | "
            f"Portfolio=${self.safe_float(optimized_portfolio.get('total_portfolio_value'), 0.0):.2f} | "
            f"CRT Signals={len(optimized_crt_signals)}"
        )
        self.bot_logger.info(opt_summary)
