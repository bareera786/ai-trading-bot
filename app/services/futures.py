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
        self._trading_config = trading_config
        self._get_futures_symbols = futures_symbols_provider
        self._get_top_symbols = top_symbols_provider
        self._dashboard_data_provider = dashboard_data_provider
        self._safe_float = safe_float

        self.lock = threading.RLock()
        self.settings: Dict[str, Any] = {
            'mode': 'manual',
            'selected_symbol': initial_selected_symbol,
            'available_symbols': list(self._get_futures_symbols()),
            'auto_trade_enabled': trading_config.get('futures_manual_auto_trade', False),
            'leverage': trading_config.get(
                'futures_manual_leverage', trading_config.get('futures_default_leverage', 3)
            ),
            'order_size_usdt': trading_config.get('futures_manual_default_notional', 50.0),
            'testnet': True,
            'last_action': None,
            'last_signal': None,
            'last_error': None,
            'position': None,
            'position_notional': 0.0,
            'entry_price': None,
            'pending_order': None,
            'order_history': [],
            'updated_at': None,
        }

        self.ensure_defaults(update_dashboard=False)

    def ensure_defaults(self, update_dashboard: bool = False) -> Dict[str, Any]:
        """Mirror of legacy `_ensure_futures_manual_defaults`."""
        changed = False
        with self.lock:
            provider_symbols = self._resolve_available_symbols()
            available = list(self.settings.get('available_symbols') or [])
            if provider_symbols:
                if provider_symbols != available:
                    self.settings['available_symbols'] = provider_symbols
                    available = provider_symbols
                    changed = True
            elif not available:
                self.settings['available_symbols'] = []

            default_symbol = self._trading_config.get('futures_selected_symbol')
            if not default_symbol and available:
                default_symbol = available[0]
                self._trading_config['futures_selected_symbol'] = default_symbol

            selected_symbol = self.settings.get('selected_symbol')
            if (not selected_symbol or (available and selected_symbol not in available)) and default_symbol:
                self.settings['selected_symbol'] = default_symbol
                changed = True

            order_size = self._safe_float(self.settings.get('order_size_usdt'), 0.0)
            default_notional = self._safe_float(
                self._trading_config.get('futures_manual_default_notional'), 50.0
            ) or 50.0
            if order_size <= 0:
                self.settings['order_size_usdt'] = max(default_notional, 10.0)
                changed = True

            leverage = self._safe_float(self.settings.get('leverage'), 0.0)
            default_leverage = self._safe_float(self._trading_config.get('futures_manual_leverage'), 3) or 3
            if leverage <= 0:
                self.settings['leverage'] = max(default_leverage, 1.0)
                changed = True

            if self.settings.get('mode') not in {'manual', 'analysis'}:
                self.settings['mode'] = 'manual'
                changed = True

            if changed:
                self.settings['updated_at'] = time.time()
                if update_dashboard:
                    self._push_to_dashboard_locked()

            snapshot = deepcopy(self.settings)
        return snapshot

    def get_manual_state(self, *, include_symbols: bool = True, update_dashboard: bool = True) -> Dict[str, Any]:
        """Return an immutable snapshot of the manual futures state."""
        snapshot = self.ensure_defaults(update_dashboard=update_dashboard)
        if include_symbols:
            snapshot['available_symbols'] = self._resolve_available_symbols()
        snapshot['timestamp'] = time.time()
        return snapshot

    def select_symbol(
        self,
        symbol: str,
        *,
        leverage: Optional[Any] = None,
        order_size_usdt: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update manual settings when the operator selects a new symbol."""
        self.ensure_defaults(update_dashboard=False)
        cleaned_symbol = str(symbol or '').strip().upper()
        if not cleaned_symbol:
            raise ValueError('Symbol is required')

        available = self._resolve_available_symbols()
        if cleaned_symbol not in available:
            raise ValueError(f'Symbol {cleaned_symbol} is not in the allowed futures list')

        with self.lock:
            self.settings['selected_symbol'] = cleaned_symbol
            self.settings['available_symbols'] = available
            self.settings['last_error'] = None
            self.settings['updated_at'] = time.time()
            self._trading_config['futures_selected_symbol'] = cleaned_symbol

            if leverage is not None:
                try:
                    max_leverage = self._safe_float(self._trading_config.get('futures_max_leverage'), 20.0) or 20.0
                    leverage_value = max(1.0, min(float(leverage), max_leverage))
                    self.settings['leverage'] = leverage_value
                    self._trading_config['futures_manual_leverage'] = leverage_value
                except (TypeError, ValueError):
                    self.settings['last_error'] = f"Invalid leverage value: {leverage}"

            if order_size_usdt is not None:
                try:
                    order_size_value = max(1.0, float(order_size_usdt))
                    self.settings['order_size_usdt'] = order_size_value
                    self._trading_config['futures_manual_default_notional'] = order_size_value
                except (TypeError, ValueError):
                    self.settings['last_error'] = f"Invalid order size value: {order_size_usdt}"

            self._push_to_dashboard_locked()
            return {
                'selected_symbol': self.settings['selected_symbol'],
                'leverage': self.settings['leverage'],
                'order_size_usdt': self.settings['order_size_usdt'],
                'last_error': self.settings.get('last_error'),
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
        desired_mode = str(mode or self.settings.get('mode') or 'manual').strip().lower()
        if desired_mode not in {'manual', 'analysis'}:
            raise ValueError('Mode must be manual or analysis')

        with self.lock:
            desired_enable = bool(enable) if enable is not None else not bool(self.settings.get('auto_trade_enabled'))
            selected_symbol = self.settings.get('selected_symbol')
            if desired_enable and not selected_symbol:
                raise ValueError('Select a symbol before enabling manual trading')

            self.settings['auto_trade_enabled'] = desired_enable
            self.settings['mode'] = desired_mode
            self.settings['updated_at'] = time.time()
            self._trading_config['futures_manual_auto_trade'] = desired_enable
            self._trading_config['futures_manual_mode'] = desired_mode
            result = {
                'auto_trade_enabled': desired_enable,
                'mode': desired_mode,
                'selected_symbol': selected_symbol,
            }
            self._push_to_dashboard_locked()

        if desired_enable and not getattr(ultimate_trader, 'futures_trading_enabled', False):
            with self.lock:
                self.settings['auto_trade_enabled'] = False
                self.settings['updated_at'] = time.time()
                self._trading_config['futures_manual_auto_trade'] = False
                self._push_to_dashboard_locked()
            self._update_system_status(ultimate_trader)
            raise RuntimeError(
                'Futures trader not connected. Add futures API credentials before enabling auto trading.'
            )

        self._update_system_status(ultimate_trader)
        return result

    def apply_restored_settings(self, restored: Optional[Dict[str, Any]]) -> None:
        if not isinstance(restored, dict):
            return
        with self.lock:
            self.settings.update(restored)
            self.settings['updated_at'] = time.time()
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
            manual_enabled = self.settings.get('auto_trade_enabled', False)
            selected_symbol = self.settings.get('selected_symbol')
            last_action = self.settings.get('last_action') or {}
            order_size_usdt = self.settings.get('order_size_usdt', 50.0)
            leverage = self.settings.get(
                'leverage', self._trading_config.get('futures_manual_leverage', 3)
            )
        if not manual_enabled or not selected_symbol or selected_symbol != symbol:
            return

        trader = getattr(ultimate_trader, 'futures_trader', None)
        if not getattr(ultimate_trader, 'futures_trading_enabled', False) or not trader or not trader.is_ready():
            self._record_error('Futures trader not connected')
            self._update_system_status(ultimate_trader)
            return

        sizing = sizing or {}
        signal_block = (prediction or {}).get('ultimate_ensemble', {})
        signal_name = str(signal_block.get('signal') or 'HOLD').upper()
        confidence = float(signal_block.get('confidence') or 0.0)

        if confidence < 0.55:
            target_side = 'FLAT'
        elif 'SELL' in signal_name:
            target_side = 'SHORT'
        elif 'BUY' in signal_name:
            target_side = 'LONG'
        else:
            target_side = 'FLAT'

        price = self._safe_float(market_data.get('price') or market_data.get('close'), 0)
        if price <= 0:
            price = self._safe_float(market_data.get('mark_price') or market_data.get('markPrice'), 1.0) or 1.0

        target_quantity = self._safe_float(sizing.get('quantity'), 0)
        if target_quantity <= 0:
            target_quantity = order_size_usdt / max(price, 1.0)
        target_quantity = round(max(target_quantity, 0.0), 3)
        if target_quantity <= 0:
            return

        now = time.time()
        cooldown = 10.0
        if target_side == (last_action.get('side')) and (now - float(last_action.get('timestamp', 0))) < cooldown:
            return

        position_info = trader.get_position(symbol)
        position_amt = 0.0
        entry_price = None
        if position_info:
            try:
                position_amt = float(position_info.get('positionAmt') or 0)
                entry_price = float(position_info.get('entryPrice') or 0)
            except (TypeError, ValueError):
                position_amt = 0.0
        if abs(position_amt) < 1e-6:
            current_side = 'FLAT'
        elif position_amt > 0:
            current_side = 'LONG'
        else:
            current_side = 'SHORT'

        actions_taken = []

        if current_side != 'FLAT' and (target_side == 'FLAT' or current_side != target_side):
            close_side = 'SELL' if position_amt > 0 else 'BUY'
            response = ultimate_trader._submit_futures_order(
                symbol,
                close_side,
                abs(position_amt),
                leverage=leverage,
                reduce_only=True,
            )
            if response:
                order_id = response.get('orderId') if isinstance(response, dict) else None
                actions_taken.append(
                    {
                        'action': 'close',
                        'side': current_side,
                        'quantity': abs(position_amt),
                        'order_id': order_id,
                        'timestamp': now,
                    }
                )
                position_amt = 0.0
                current_side = 'FLAT'
            else:
                self._record_error('Failed to close existing futures position')
                return

        if target_side != 'FLAT' and current_side == 'FLAT' and target_quantity > 0:
            order_side = 'BUY' if target_side == 'LONG' else 'SELL'
            response = ultimate_trader._submit_futures_order(
                symbol,
                order_side,
                target_quantity,
                leverage=leverage,
                reduce_only=False,
            )
            if response:
                order_id = response.get('orderId') if isinstance(response, dict) else None
                actions_taken.append(
                    {
                        'action': 'open',
                        'side': target_side,
                        'quantity': target_quantity,
                        'order_id': order_id,
                        'timestamp': now,
                    }
                )
                position_info = trader.get_position(symbol)
                if position_info:
                    try:
                        position_amt = float(position_info.get('positionAmt') or 0)
                        entry_price = float(position_info.get('entryPrice') or 0)
                        current_side = 'LONG' if position_amt > 0 else 'SHORT' if position_amt < 0 else 'FLAT'
                    except (TypeError, ValueError):
                        pass
            else:
                self._record_error(f"Failed to open {target_side} position")
                return

        with self.lock:
            self.settings['last_signal'] = {
                'symbol': symbol,
                'signal': signal_name,
                'confidence': confidence,
                'target_side': target_side,
                'timestamp': now,
            }
            if actions_taken:
                self.settings['last_action'] = {'side': target_side, 'timestamp': now}
                history = self.settings.get('order_history') or []
                self.settings['order_history'] = history[-9:] + actions_taken
                self.settings['last_error'] = None
            self.settings['position'] = current_side if current_side != 'FLAT' else None
            self.settings['position_notional'] = abs(position_amt) * price
            self.settings['entry_price'] = entry_price
            self.settings['updated_at'] = time.time()
            self._push_to_dashboard_locked()
        self._update_system_status(ultimate_trader)

    def _record_error(self, message: str) -> None:
        with self.lock:
            self.settings['last_error'] = message
            self.settings['updated_at'] = time.time()
            self._push_to_dashboard_locked()

    def _update_system_status(self, ultimate_trader) -> None:
        dashboard_data = self._dashboard_data_provider()
        if not isinstance(dashboard_data, dict):
            return
        system_status = dashboard_data.get('system_status') or {}
        system_status['futures_trading_ready'] = bool(getattr(ultimate_trader, 'futures_trading_enabled', False))
        system_status['futures_manual_auto_trade'] = self.settings.get('auto_trade_enabled', False)
        dashboard_data['system_status'] = system_status

    def _push_to_dashboard_locked(self) -> None:
        dashboard_data = self._dashboard_data_provider()
        if isinstance(dashboard_data, dict):
            dashboard_data['futures_manual'] = self.settings

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