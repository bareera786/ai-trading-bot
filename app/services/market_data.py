"""Market data refresh and performance update helpers."""
from __future__ import annotations

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
        sleep_interval: float = 30.0,
    ) -> None:
        self.dashboard_data = dashboard_data
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

        for symbol in active_symbols:
            cached_data = self._get_cached_market_data(symbol)
            if cached_data:
                real_data = cached_data
            else:
                real_data = self.get_real_market_data(symbol) or {}
                if real_data:
                    self._set_cached_market_data(symbol, real_data)
            if real_data:
                market_data[symbol] = real_data
                history = self.historical_data.setdefault(symbol, [])
                history.append(real_data.get("price"))
                if len(history) > 100:
                    history.pop(0)

        if self.trading_config.get("parallel_processing"):
            if market_data:
                ml_predictions = self.parallel_engine.parallel_predict(
                    active_symbols, market_data, self.ultimate_ml_system
                )
                optimized_ml_predictions = self.parallel_engine.parallel_predict(
                    active_symbols, market_data, self.optimized_ml_system
                )
        else:
            for symbol in active_symbols:
                snapshot = market_data.get(symbol)
                if not snapshot:
                    continue
                pred = self.ultimate_ml_system.predict_ultimate(symbol, snapshot)
                if pred:
                    ml_predictions[symbol] = pred
                opt_pred = self.optimized_ml_system.predict_professional(
                    symbol, snapshot
                )
                if opt_pred:
                    optimized_ml_predictions[symbol] = opt_pred

        if ml_predictions:
            self.ultimate_ml_system.ensemble_system.create_correlation_matrix(
                ml_predictions
            )
        if optimized_ml_predictions:
            self.optimized_ml_system.ensemble_system.create_correlation_matrix(
                optimized_ml_predictions
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
            history = self.historical_data.get(symbol, [])
            market_snapshot = market_data.get(symbol)
            if ultimate_qfm_engine and market_snapshot:
                try:
                    ultimate_qfm_engine.compute_realtime_features(
                        symbol, market_snapshot, history
                    )
                    qfm_signal = ultimate_qfm_engine.generate_signal(symbol)
                    if qfm_signal:
                        qfm_signals[symbol] = self._format_qfm_signal(
                            qfm_signal, market_snapshot, symbol
                        )
                except Exception as exc:
                    self.bot_logger.warning(
                        "Ultimate QFM update failed for %s: %s", symbol, exc
                    )
            if optimized_qfm_engine and market_snapshot:
                try:
                    optimized_qfm_engine.compute_realtime_features(
                        symbol, market_snapshot, history
                    )
                    opt_signal = optimized_qfm_engine.generate_signal(symbol)
                    if opt_signal:
                        optimized_qfm_signals[symbol] = self._format_qfm_signal(
                            opt_signal, market_snapshot, symbol
                        )
                except Exception as exc:
                    self.bot_logger.warning(
                        "Optimized QFM update failed for %s: %s", symbol, exc
                    )

            if market_snapshot and len(history) >= 20:
                crt_signal = self.ultimate_ml_system.generate_crt_signals(
                    symbol, market_snapshot, history
                )
                crt_signals[symbol] = crt_signal
                optimized_crt_signal = self.optimized_ml_system.generate_crt_signals(
                    symbol, market_snapshot, history
                )
                optimized_crt_signals[symbol] = optimized_crt_signal

                success, message = self.ultimate_trader.execute_ultimate_trade(
                    symbol,
                    ml_predictions.get(symbol),
                    market_snapshot,
                    history,
                    ensemble_prediction,
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

                # Execute futures trades if futures trading is enabled
                if (self.trading_config.get("futures_enabled") and
                    getattr(self.ultimate_trader, "futures_trading_enabled", False) and
                    self.ultimate_trader.futures_trader):

                    # Use the same signals as spot trading for futures
                    futures_success = False
                    futures_message = "Futures trading not executed"

                    # Simple futures trading logic: mirror spot trading decisions
                    if success and message and "BUY" in message.upper():
                        # Execute futures long position
                        futures_response = self.ultimate_trader._submit_futures_order(
                            symbol, "BUY", 0.001, leverage=3  # Small test position
                        )
                        if futures_response:
                            futures_success = True
                            futures_message = f"Futures LONG {symbol} executed"
                            print(f"🤖 {futures_message}")
                            self.dashboard_data["system_status"]["last_futures_trade"] = {
                                "symbol": symbol,
                                "message": futures_message,
                                "timestamp": datetime.now(),
                            }
                    elif success and message and "SELL" in message.upper():
                        # Execute futures short position
                        futures_response = self.ultimate_trader._submit_futures_order(
                            symbol, "SELL", 0.001, leverage=3  # Small test position
                        )
                        if futures_response:
                            futures_success = True
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

        self.ultimate_trader.latest_market_data = market_data
        self.optimized_trader.latest_market_data = market_data
        self.ultimate_trader.update_auto_take_profit_orders(market_data)
        current_prices = {
            symbol: data["price"]
            for symbol, data in market_data.items()
            if "price" in data
        }
        for message in self.ultimate_trader.check_advanced_stop_loss(current_prices):
            print(f"🤖 {message}")
        for message in self.optimized_trader.check_advanced_stop_loss(current_prices):
            print(f"🤖 {message}")

        portfolio = self.ultimate_trader.get_portfolio_summary(current_prices)
        optimized_portfolio = self.optimized_trader.get_portfolio_summary(
            current_prices
        )
        self.dashboard_data["portfolio"] = portfolio
        self.dashboard_data["optimized_portfolio"] = optimized_portfolio
        self.dashboard_data[
            "trade_statistics"
        ] = self.ultimate_trader.get_trade_statistics()
        self.dashboard_data[
            "optimized_trade_statistics"
        ] = self.optimized_trader.get_trade_statistics()

        self._update_system_status(portfolio)
        self._update_optimized_status(optimized_portfolio)

        self.dashboard_data[
            "safety_status"
        ] = self.ultimate_trader.safety_manager.get_status_snapshot()
        self.dashboard_data[
            "optimized_safety_status"
        ] = self.optimized_trader.safety_manager.get_status_snapshot()
        self.dashboard_data[
            "real_trading_status"
        ] = self.ultimate_trader.get_real_trading_status()
        self.dashboard_data[
            "optimized_real_trading_status"
        ] = self.optimized_trader.get_real_trading_status()
        self.dashboard_data[
            "binance_credentials"
        ] = self.binance_credential_service.get_status(include_connection=True)

        journal_events = [
            {**event, "_profile": "ultimate"}
            for event in self.ultimate_trader.trade_history.get_journal_events(limit=50)
        ]
        if hasattr(self.optimized_trader.trade_history, "get_journal_events"):
            journal_events.extend(
                {**event, "_profile": "optimized"}
                for event in self.optimized_trader.trade_history.get_journal_events(
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

    def _update_system_status(self, portfolio: dict[str, Any]) -> None:
        status = self.dashboard_data["system_status"]
        status["market_regime"] = self.ultimate_trader.ensemble_system.market_regime
        status[
            "risk_adjustment"
        ] = self.ultimate_trader.risk_manager.get_risk_multiplier()
        status[
            "market_stress"
        ] = self.ultimate_trader.risk_manager.market_stress_indicator
        status["risk_profile"] = self.ultimate_trader.risk_manager.current_risk_profile
        status["trading_enabled"] = self.ultimate_trader.trading_enabled
        status["paper_trading"] = self.ultimate_trader.paper_trading
        status["real_trading_ready"] = bool(self.ultimate_trader.real_trading_enabled)
        status["futures_trading_ready"] = bool(
            getattr(self.ultimate_trader, "futures_trading_enabled", False)
        )
        status["futures_manual_auto_trade"] = self.futures_manual_settings.get(
            "auto_trade_enabled", False
        )
        if "bot_efficiency" in portfolio:
            status["bot_efficiency"] = portfolio["bot_efficiency"]["success_rate"]
            status["learning_cycles"] = portfolio["bot_efficiency"]["learning_cycles"]

    def _update_optimized_status(self, portfolio: dict[str, Any]) -> None:
        status = self.dashboard_data["optimized_system_status"]
        status["market_regime"] = self.optimized_trader.ensemble_system.market_regime
        status[
            "risk_adjustment"
        ] = self.optimized_trader.risk_manager.get_risk_multiplier()
        status[
            "market_stress"
        ] = self.optimized_trader.risk_manager.market_stress_indicator
        status["risk_profile"] = self.optimized_trader.risk_manager.current_risk_profile
        status["trading_enabled"] = self.optimized_trader.trading_enabled
        status["paper_trading"] = self.optimized_trader.paper_trading
        status["real_trading_ready"] = bool(self.optimized_trader.real_trading_enabled)
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
