"""Futures-related helper services."""
from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, Optional


class FuturesManualService:
    """Encapsulates the manual futures control panel state + helpers."""

    def __init__(
        self,
        *,
        trading_config: Dict[str, Any],
        initial_selected_symbol: Optional[str],
        futures_symbols_provider: Callable[[], Iterable[str]],
        top_symbols_provider: Callable[[], Iterable[str]],
        dashboard_data_provider: Callable[[], Dict[str, Any]],
        safe_float: Callable[[Any, float], float],
    ) -> None:
        # Validate required parameters
        if not callable(futures_symbols_provider):
            raise ValueError("futures_symbols_provider must be callable")
        if not callable(dashboard_data_provider):
            raise ValueError("dashboard_data_provider must be callable")

        self._trading_config = trading_config or {}
        self._get_futures_symbols = futures_symbols_provider
        self._get_top_symbols = top_symbols_provider
        self._dashboard_data_provider = dashboard_data_provider
        self._safe_float = safe_float

        self.lock = threading.RLock()
        
        # Initialize with safe defaults
        self.settings: Dict[str, Any] = {
            "mode": "manual",
            "selected_symbol": initial_selected_symbol,
            "available_symbols": [], # Initialize empty, will be populated in ensure_defaults
            "auto_trade_enabled": self._trading_config.get(
                "futures_manual_auto_trade", False
            ),
            "leverage": self._trading_config.get(
                "futures_manual_leverage",
                self._trading_config.get("futures_default_leverage", 3),
            ),
            "order_size_usdt": max(
                self._safe_float(
                    self._trading_config.get("futures_manual_default_notional"), 50.0
                ),
                10.0,
            ),
            "testnet": True,
            "last_action": None,
            "last_signal": None,
            "last_error": None,
            "position": None,
            "position_notional": 0.0,
            "entry_price": None,
            "pending_order": None,
            "order_history": [],
            "updated_at": time.time(),
            "service_started": False,
        }

        # Don't call ensure_defaults here - let start() method handle it

    def start(self) -> bool:
        """Initialize and start the futures service."""
        try:
            with self.lock:
                # Initialize settings
                self.ensure_defaults(update_dashboard=True)
                
                # Reset any stale state
                self.settings["last_error"] = None
                self.settings["pending_order"] = None
                self.settings["updated_at"] = time.time()
                self.settings["service_started"] = True
                
                # Verify we have symbols
                if not self.settings["available_symbols"]:
                    self._record_error("No symbols available for futures trading")
                    # We return True even if no symbols, so user can fix config later
                
                print(f"FuturesManualService started with {len(self.settings.get('available_symbols', []))} symbols")
                return True
        except Exception as e:
            self._record_error(f"Failed to start futures service: {str(e)}")
            return False

    def stop(self) -> None:
        """Clean up and stop the futures service."""
        with self.lock:
            self.settings["auto_trade_enabled"] = False
            self.settings["last_action"] = None
            self.settings["updated_at"] = time.time()
            self.settings["service_started"] = False
            self._push_to_dashboard_locked()

    def get_settings(self) -> Dict[str, Any]:
        """Alias for get_manual_state to satisfy AI bot context interface."""
        return self.get_manual_state()

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Alias for apply_restored_settings to satisfy AI bot context interface."""
        self.apply_restored_settings(settings)

    def get_manual_state(self, include_symbols: bool = False, update_dashboard: bool = False) -> Dict[str, Any]:
        """Backward compatibility alias for fetching state."""
        # include_symbols is ignored as available_symbols is always included in settings/snapshot
        return self.ensure_defaults(update_dashboard=update_dashboard)

    def get_service_status(self) -> Dict[str, Any]:
        """Return the health/status of the futures service."""
        with self.lock:
            return {
                "running": self.settings.get("service_started", False),
                "symbols_available": len(self.settings.get("available_symbols", [])),
                "auto_trade_enabled": self.settings.get("auto_trade_enabled", False),
                "selected_symbol": self.settings.get("selected_symbol"),
                "last_error": self.settings.get("last_error"),
                "last_update": self.settings.get("updated_at"),
                "position_active": self.settings.get("position") is not None,
            }

    def ensure_defaults(self, update_dashboard: bool = False) -> Dict[str, Any]:
        """Mirror of legacy `_ensure_futures_manual_defaults`."""
        with self.lock:  # ENSURE ALL CHANGES ARE IN LOCK
            changed = False
            
            provider_symbols = self._resolve_available_symbols()
            available = list(self.settings.get("available_symbols") or [])
            if provider_symbols:
                if provider_symbols != available:
                    self.settings["available_symbols"] = provider_symbols
                    available = provider_symbols
                    changed = True
            elif not available:
                self.settings["available_symbols"] = []

            default_symbol = self._trading_config.get("futures_selected_symbol")
            if not default_symbol and available:
                default_symbol = available[0]
                self._trading_config["futures_selected_symbol"] = default_symbol

            selected_symbol = self.settings.get("selected_symbol")
            if (
                not selected_symbol or (available and selected_symbol not in available)
            ) and default_symbol:
                self.settings["selected_symbol"] = default_symbol
                changed = True

            order_size = self._safe_float(self.settings.get("order_size_usdt"), 0.0)
            default_notional = (
                self._safe_float(
                    self._trading_config.get("futures_manual_default_notional"), 50.0
                )
                or 50.0
            )
            if order_size <= 0:
                self.settings["order_size_usdt"] = max(default_notional, 10.0)
                changed = True

            leverage = self._safe_float(self.settings.get("leverage"), 0.0)
            default_leverage = (
                self._safe_float(self._trading_config.get("futures_manual_leverage"), 3)
                or 3
            )
            if leverage <= 0:
                self.settings["leverage"] = max(default_leverage, 1.0)
                changed = True

            if self.settings.get("mode") not in {"manual", "analysis"}:
                self.settings["mode"] = "manual"
                changed = True

            if changed:
                self.settings["updated_at"] = time.time()
                if update_dashboard:
                    self._push_to_dashboard_locked()

            snapshot = deepcopy(self.settings)
        return snapshot
        
    def _push_to_dashboard_locked(self) -> None:
        try:
            dashboard_data = self._dashboard_data_provider()
            if isinstance(dashboard_data, dict):
                dashboard_data["futures_manual"] = deepcopy(self.settings)
        except Exception as e:
            # Log but don't crash
            print(f"Warning: Failed to push to dashboard: {e}")

    def _resolve_available_symbols(self) -> list[str]:
        symbols: list[str] = []
        try:
            symbols = list(self._get_futures_symbols()) or []
        except Exception as e:
            self._record_error(f"Error fetching futures symbols: {str(e)}")
            try:
                symbols = list(self._get_top_symbols()) or []
            except Exception as e2:
                # self._record_error(f"Error fetching top symbols: {str(e2)}")
                symbols = []
        
        # Ensure we have valid symbols
        valid_symbols = []
        for symbol in symbols:
            if isinstance(symbol, str) and symbol.strip():
                valid_symbols.append(symbol.strip().upper())
        
        return valid_symbols
        
    def select_symbol(
        self,
        symbol: str,
        *,
        leverage: Optional[Any] = None,
        order_size_usdt: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update manual settings when the operator selects a new symbol."""
        # Note: We call ensure_defaults inside the lock if needed, or rely on it being called before 
        # But for thread safety, let's lock the whole operation
        with self.lock: 
             # ensure_defaults calls lock internally, so we need reentrant lock RLock (Checked in init, it is RLock)
            self.ensure_defaults(update_dashboard=False)
            
            cleaned_symbol = str(symbol or "").strip().upper()
            if not cleaned_symbol:
                raise ValueError("Symbol is required")
    
            available = self.settings.get("available_symbols", [])
            # If available is empty, try to resolve? done in ensure_defaults
            
            if cleaned_symbol not in available:
                 # Soft failure? Or strict? 
                 # User might select a symbol not yet in list?
                 # Let's trust resolve_available_symbols
                 pass
                 # raise ValueError(f"Symbol {cleaned_symbol} is not in the allowed futures list")

            self.settings["selected_symbol"] = cleaned_symbol
            self.settings["last_error"] = None
            self.settings["updated_at"] = time.time()
            self._trading_config["futures_selected_symbol"] = cleaned_symbol

            if leverage is not None:
                try:
                    max_leverage = (
                        self._safe_float(
                            self._trading_config.get("futures_max_leverage"), 20.0
                        )
                        or 20.0
                    )
                    leverage_value = max(1.0, min(float(leverage), max_leverage))
                    self.settings["leverage"] = leverage_value
                    self._trading_config["futures_manual_leverage"] = leverage_value
                except (TypeError, ValueError):
                    self.settings["last_error"] = f"Invalid leverage value: {leverage}"

            if order_size_usdt is not None:
                try:
                    order_size_value = max(1.0, float(order_size_usdt))
                    self.settings["order_size_usdt"] = order_size_value
                    self._trading_config[
                        "futures_manual_default_notional"
                    ] = order_size_value
                except (TypeError, ValueError):
                    self.settings[
                        "last_error"
                    ] = f"Invalid order size value: {order_size_usdt}"

            self._push_to_dashboard_locked()
            return {
                "selected_symbol": self.settings["selected_symbol"],
                "leverage": self.settings["leverage"],
                "order_size_usdt": self.settings["order_size_usdt"],
                "last_error": self.settings.get("last_error"),
            }

    def toggle_auto_trading(
        self,
        *,
        enable: Optional[bool],
        mode: Optional[str],
        ultimate_trader,
    ) -> Dict[str, Any]:
        """Enable/disable manual auto trading and update dashboard/system state."""
        self.ensure_defaults(update_dashboard=False)
        desired_mode = (
            str(mode or self.settings.get("mode") or "manual").strip().lower()
        )
        if desired_mode not in {"manual", "analysis"}:
            raise ValueError("Mode must be manual or analysis")

        with self.lock:
            desired_enable = (
                bool(enable)
                if enable is not None
                else not bool(self.settings.get("auto_trade_enabled"))
            )
            selected_symbol = self.settings.get("selected_symbol")
            if desired_enable and not selected_symbol:
                raise ValueError("Select a symbol before enabling manual trading")

            self.settings["auto_trade_enabled"] = desired_enable
            self.settings["mode"] = desired_mode
            self.settings["updated_at"] = time.time()
            self._trading_config["futures_manual_auto_trade"] = desired_enable
            self._trading_config["futures_manual_mode"] = desired_mode
            result = {
                "auto_trade_enabled": desired_enable,
                "mode": desired_mode,
                "selected_symbol": selected_symbol,
            }
            self._push_to_dashboard_locked()

        if desired_enable:
            # FORCE CONNECT: Always attempt to enable/reconnect
            print("DEBUG: Force-Heal Connection initiated...", flush=True)
            try:
                success = ultimate_trader.enable_futures_trading()
                if not success:
                    raise Exception("Connection failed (returned False)")
                
                # VERIFY READINESS
                trader = getattr(ultimate_trader, "futures_trader", None)
                if not trader or not trader.is_ready():
                    # Give it a second to initialize
                    time.sleep(1.0)
                    if not trader or not trader.is_ready():
                        raise Exception("Trader object not ready after connection")

                print(f"DEBUG: Force-Heal result: {success} (Ready: True)", flush=True)
            except Exception as e:
                print(f"DEBUG: Force-Heal failed: {e}", flush=True)
                with self.lock:
                    self.settings["auto_trade_enabled"] = False
                    self.settings["updated_at"] = time.time()
                    self._trading_config["futures_manual_auto_trade"] = False
                    self._push_to_dashboard_locked()
                self._update_system_status(ultimate_trader)
                raise RuntimeError(
                    f"Futures trader connection failed: {str(e)}"
                )

        self._update_system_status(ultimate_trader)
        return result

    def apply_restored_settings(self, restored: Optional[Dict[str, Any]]) -> None:
        if not isinstance(restored, dict):
            return
        with self.lock:
            self.settings.update(restored)
            self.settings["updated_at"] = time.time()
            self._push_to_dashboard_locked()

    def handle_manual_trading(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        prediction: Optional[Dict[str, Any]],
        sizing: Optional[Dict[str, Any]],
        ultimate_trader,
    ) -> None:
        """Port of `_handle_manual_futures_trading`."""
        self.ensure_defaults(update_dashboard=False)
        with self.lock:
            manual_enabled = self.settings.get("auto_trade_enabled", False)
            selected_symbol = self.settings.get("selected_symbol")
            last_action = self.settings.get("last_action") or {}
            order_size_usdt = self.settings.get("order_size_usdt", 50.0)
            leverage = self.settings.get(
                "leverage", self._trading_config.get("futures_manual_leverage", 3)
            )
        
        # Log skipped iterations for debugging (optional/verbose)
        if not manual_enabled or not selected_symbol or selected_symbol != symbol:
            return

        trader = getattr(ultimate_trader, "futures_trader", None)
        if (
            not getattr(ultimate_trader, "futures_trading_enabled", False)
            or not trader
            or not trader.is_ready()
        ):
            self._record_error("Futures trader not connected (or not ready)")
            self._update_system_status(ultimate_trader)
            return

        sizing = sizing or {}
        signal_block = (prediction or {}).get("ultimate_ensemble", {})
        signal_name = str(signal_block.get("signal") or "HOLD").upper()
        confidence = float(signal_block.get("confidence") or 0.0)

        # Logic: Determine Target Side
        status_reason = "Signal Check"
        if confidence < 0.55:
            target_side = "FLAT"
            status_reason = f"Low Confidence ({confidence:.2f})"
        elif "SELL" in signal_name:
            target_side = "SHORT"
            status_reason = f"Signal: {signal_name}"
        elif "BUY" in signal_name:
            target_side = "LONG"
            status_reason = f"Signal: {signal_name}"
        else:
            target_side = "FLAT"
            status_reason = "Hold Signal"

        price = self._safe_float(
            market_data.get("price") or market_data.get("close"), 0
        )
        if price <= 0:
            price = (
                self._safe_float(
                    market_data.get("mark_price") or market_data.get("markPrice"), 1.0
                )
                or 1.0
            )

        target_quantity = self._safe_float(sizing.get("quantity"), 0)
        if target_quantity <= 0:
            target_quantity = order_size_usdt / max(price, 1.0)
        target_quantity = round(max(target_quantity, 0.0), 3)

        now = time.time()
        cooldown = 10.0
        
        # Check Cooldown
        in_cooldown = False
        if (
            target_side == (last_action.get("side"))
            and (now - float(last_action.get("timestamp", 0))) < cooldown
        ):
            in_cooldown = True
            status_reason = "Cooldown Active"
            # We continue execution ONLY to update dashboard status, but won't trade.
        
        if target_quantity <= 0:
            status_reason = "Invalid Quantity"

        position_info = trader.get_position(symbol)
        position_amt = 0.0
        entry_price = None
        if position_info:
            try:
                position_amt = float(position_info.get("positionAmt") or 0)
                entry_price = float(position_info.get("entryPrice") or 0)
            except (TypeError, ValueError):
                position_amt = 0.0
        
        current_side = "FLAT"
        if position_amt > 1e-6:
            current_side = "LONG"
        elif position_amt < -1e-6:
            current_side = "SHORT"

        actions_taken = []
        
        # EXECUTE TRADES (Only if not in cooldown and valid quantity)
        if not in_cooldown and target_quantity > 0:
            
            # Close Logic
            if current_side != "FLAT" and (target_side == "FLAT" or current_side != target_side):
                close_side = "SELL" if position_amt > 0 else "BUY"
                
                # PHASE 1 SCALING: Publish signal instead of executing
                from app.services.signal_publisher import signal_publisher
                
                msg_id = signal_publisher.publish_signal(
                    symbol=symbol,
                    side="FLAT",  # Closing to Flat
                    confidence=confidence,
                    price=price,
                    signal_source="manual_auto_loop"
                )
                
                if msg_id:
                    # We log it as if it happened, so the UI shows activity
                    actions_taken.append({
                        "action": "signal:close",
                        "side": current_side,
                        "quantity": abs(position_amt),
                        "order_id": f"sig:{msg_id}",
                        "timestamp": now,
                    })
                    # Note: Local position_amt is NOT reset because we didn't trade locally.
                    # This relies on the Executor to close it.
                    # Ideally, we should re-fetch position in next loop to see if Executor did its job.
                    # For now, we leave local state management as is (it will refresh next loop).
                else:
                    self._record_error("Failed to publish CLOSE signal")
                    # return # Don't return, try to open if needed? No, fail safe.
                    return

            # Open Logic
            if target_side != "FLAT" and current_side == "FLAT":
                order_side = "BUY" if target_side == "LONG" else "SELL"
                
                # PHASE 1 SCALING: Publish signal instead of executing
                from app.services.signal_publisher import signal_publisher

                msg_id = signal_publisher.publish_signal(
                    symbol=symbol,
                    side=target_side,
                    confidence=confidence,
                    price=price,
                    signal_source="manual_auto_loop"
                )

                if msg_id:
                    actions_taken.append({
                        "action": "signal:open",
                        "side": target_side,
                        "quantity": target_quantity,
                        "order_id": f"sig:{msg_id}",
                        "timestamp": now,
                    })
                else:
                    self._record_error(f"Failed to publish {target_side} signal")
                    return
                    return

        # UPDATE DASHBOARD WITH SIGNAL REASON
        with self.lock:
            self.settings["last_signal"] = {
                "symbol": symbol,
                "signal": signal_name,
                "confidence": confidence,
                "target_side": target_side,
                "status_reason": status_reason, # NEW FIELD
                "timestamp": now,
            }
            if actions_taken:
                self.settings["last_action"] = {"side": target_side, "timestamp": now}
                history = self.settings.get("order_history") or []
                self.settings["order_history"] = history[-9:] + actions_taken
                self.settings["last_error"] = None
            
            # Calculate P&L if position exists
            unrealized_pnl = 0.0
            if current_side != "FLAT" and position_amt != 0 and entry_price > 0:
                if current_side == "LONG":
                    unrealized_pnl = (price - entry_price) * abs(position_amt)
                else:
                    unrealized_pnl = (entry_price - price) * abs(position_amt)
            
            # Simulated Risk Score (0-100) - Placeholder logic until we have a real risk engine
            # Base risk 10, +5 per 1x leverage, +10 if in position
            risk_score = 10 + (leverage * 5) + (10 if current_side != "FLAT" else 0)
            risk_score = min(100, max(0, int(risk_score)))

            self.settings["position"] = current_side if current_side != "FLAT" else None
            self.settings["position_notional"] = abs(position_amt) * price
            self.settings["entry_price"] = entry_price
            self.settings["unrealized_pnl"] = unrealized_pnl
            self.settings["mark_price"] = price # Useful for UI
            self.settings["risk_score"] = risk_score
            self.settings["updated_at"] = time.time()
            self._push_to_dashboard_locked()
        self._update_system_status(ultimate_trader)

    def _record_error(self, message: str) -> None:
        with self.lock:
            self.settings["last_error"] = message
            self.settings["updated_at"] = time.time()
            self._push_to_dashboard_locked()

    def _update_system_status(self, ultimate_trader) -> None:
        dashboard_data = self._dashboard_data_provider()
        if not isinstance(dashboard_data, dict):
            return
        system_status = dashboard_data.get("system_status") or {}
        system_status["futures_trading_ready"] = bool(
            getattr(ultimate_trader, "futures_trading_enabled", False)
        )
        system_status["futures_manual_auto_trade"] = self.settings.get(
            "auto_trade_enabled", False
        )
        dashboard_data["system_status"] = system_status
# Removed duplicate _push_to_dashboard_locked definition

    def _resolve_available_symbols(self) -> list[str]:
        symbols: list[str] = []
        try:
            symbols = list(self._get_futures_symbols()) or []
        except Exception:
            symbols = []
        if not symbols:
            try:
                symbols = list(self._get_top_symbols()) or []
            except Exception:
                symbols = []
        return symbols
