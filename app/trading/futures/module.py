from datetime import datetime
import logging

class FuturesTradingModule:
    """
    Comprehensive Futures Trading Module
    Supports perpetual futures with leverage management, funding rates, and futures-specific indicators
    """

    def __init__(self, max_leverage=10, default_leverage=3, risk_mode="conservative"):
        self.logger = logging.getLogger(__name__)
        self.max_leverage = max_leverage
        self.default_leverage = default_leverage
        self.risk_mode = risk_mode
        self.positions = {}
        self.leverage_settings = {}
        self.funding_rates = {}
        self.liquidation_buffer = 0.05
        self.futures_indicators = [
            "funding_rate",
            "open_interest",
            "liquidations",
            "basis",
            "long_short_ratio",
            "cumulative_volume_delta",
            "futures_basis",
        ]

        self.futures_config = {
            "max_leverage": max_leverage,
            "default_leverage": default_leverage,
            "auto_leverage_adjustment": True,
            "funding_rate_aware": True,
            "liquidation_protection": True,
            "position_mode": "HEDGE",
            "margin_mode": "ISOLATED",
            "enable_auto_margin": True,
        }

        print(f"🎯 Futures Trading Module Initialized (Max Leverage: {max_leverage}x)")

    def calculate_futures_leverage(
        self, symbol, volatility, signal_confidence, market_regime
    ):
        """Dynamic leverage calculation based on multiple factors"""
        try:
            base_leverage = self.default_leverage
            vol_factor = self._calculate_volatility_factor(volatility)
            confidence_factor = min(signal_confidence * 2, 1.5)
            regime_factor = self._calculate_regime_factor(market_regime)
            funding_factor = self._calculate_funding_factor(symbol)

            final_leverage = (
                base_leverage
                * vol_factor
                * confidence_factor
                * regime_factor
                * funding_factor
            )
            final_leverage = max(1, min(final_leverage, self.max_leverage))
            final_leverage = round(final_leverage * 2) / 2

            self.leverage_settings[symbol] = final_leverage
            return final_leverage

        except Exception as e:
            print(f"❌ Leverage calculation error for {symbol}: {e}")
            return self.default_leverage

    def _calculate_volatility_factor(self, volatility):
        if volatility > 0.08:
            return 0.5
        elif volatility > 0.05:
            return 0.7
        elif volatility > 0.03:
            return 0.9
        return 1.1

    def _calculate_regime_factor(self, market_regime):
        regime_factors = {
            "STRONG_BULL": 1.2,
            "STRONG_BEAR": 1.1,
            "BULL": 1.1,
            "BEAR": 1.0,
            "SIDEWAYS": 0.8,
            "HIGH_VOL_SIDEWAYS": 0.6,
            "OVERBOUGHT": 0.7,
            "OVERSOLD": 0.9,
        }
        return regime_factors.get(market_regime, 1.0)

    def _calculate_funding_factor(self, symbol):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)
            if abs(funding_rate) > 0.0005:
                return 0.8
            if abs(funding_rate) > 0.0002:
                return 0.9
            return 1.0
        except Exception:
            return 1.0

    def calculate_futures_position_size(
        self,
        symbol,
        account_balance,
        leverage,
        entry_price,
        stop_loss_price,
        risk_per_trade=0.02,
    ):
        try:
            risk_amount = account_balance * risk_per_trade
            price_diff = abs(entry_price - stop_loss_price)

            if price_diff == 0:
                return 0, 0, 0

            position_size = (risk_amount / price_diff) * entry_price
            leveraged_size = position_size * leverage
            margin_required = leveraged_size / leverage

            if margin_required > account_balance * 0.8:
                margin_required = account_balance * 0.8
                leveraged_size = margin_required * leverage

            quantity = leveraged_size / entry_price

            return quantity, margin_required, leveraged_size

        except Exception as e:
            print(f"❌ Futures position sizing error: {e}")
            return 0, 0, 0

    def calculate_liquidation_price(
        self, symbol, entry_price, quantity, leverage, side
    ):
        try:
            if side.upper() == "LONG":
                liquidation_price = entry_price * (1 - (1 / leverage) + 0.005)
            else:
                liquidation_price = entry_price * (1 + (1 / leverage) - 0.005)
            return max(0, liquidation_price)
        except Exception as e:
            print(f"❌ Liquidation price calculation error: {e}")
            return entry_price * 0.5

    def update_funding_rates(self, symbol, funding_data):
        try:
            self.funding_rates[symbol] = funding_data.get("funding_rate", 0)
            print(f"💰 {symbol} Funding Rate: {self.funding_rates[symbol]:.6f}")
        except Exception as e:
            print(f"❌ Funding rate update error: {e}")

    def should_avoid_funding_period(self, symbol, hours_to_funding=1):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)
            if abs(funding_rate) > 0.0005:
                return True
            return False
        except Exception:
            return False

    def generate_futures_signals(self, symbol, market_data, historical_data):
        try:
            signals = []
            if historical_data is None or len(historical_data) < 50:
                return signals

            funding_signal = self._analyze_funding_rate(symbol)
            if funding_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_FUNDING",
                        "confidence_score": funding_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.05 if funding_signal["signal"] == "BUY" else 0.95),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.95 if funding_signal["signal"] == "BUY" else 1.05),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": funding_signal["strategy"],
                        "strategy": funding_signal["strategy"],
                        "signal": funding_signal["signal"],
                        "confidence": funding_signal["confidence"],
                    }
                )

            oi_signal = self._analyze_open_interest(market_data)
            if oi_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_OPEN_INTEREST",
                        "confidence_score": oi_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.03 if oi_signal["signal"] == "BUY" else 0.97),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.97 if oi_signal["signal"] == "BUY" else 1.03),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": oi_signal["strategy"],
                        "strategy": oi_signal["strategy"],
                        "signal": oi_signal["signal"],
                        "confidence": oi_signal["confidence"],
                    }
                )

            liq_signal = self._analyze_liquidations(market_data)
            if liq_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_LIQUIDATIONS",
                        "confidence_score": liq_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.02 if liq_signal["signal"] == "BUY" else 0.98),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.98 if liq_signal["signal"] == "BUY" else 1.02),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": liq_signal["strategy"],
                        "strategy": liq_signal["strategy"],
                        "signal": liq_signal["signal"],
                        "confidence": liq_signal["confidence"],
                    }
                )

            basis_signal = self._analyze_basis(market_data)
            if basis_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_BASIS",
                        "confidence_score": basis_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.025 if basis_signal["signal"] == "BUY" else 0.975),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.975 if basis_signal["signal"] == "BUY" else 1.025),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": basis_signal["strategy"],
                        "strategy": basis_signal["strategy"],
                        "signal": basis_signal["signal"],
                        "confidence": basis_signal["confidence"],
                    }
                )

            ls_signal = self._analyze_long_short_ratio(market_data)
            if ls_signal:
                signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": "FUTURES_LS_RATIO",
                        "confidence_score": ls_signal["confidence"],
                        "timestamp": datetime.now().isoformat(),
                        "current_price": float(market_data.get("price", 0)),
                        "target_price": float(market_data.get("price", 0))
                        * (1.015 if ls_signal["signal"] == "BUY" else 0.985),
                        "stop_loss": float(market_data.get("price", 0))
                        * (0.985 if ls_signal["signal"] == "BUY" else 1.015),
                        "time_frame": "1D",
                        "model_version": "FUTURES_v1.0",
                        "reason_code": ls_signal["strategy"],
                        "strategy": ls_signal["strategy"],
                        "signal": ls_signal["signal"],
                        "confidence": ls_signal["confidence"],
                    }
                )

            return signals

        except Exception as e:
            print(f"❌ Futures signal generation error: {e}")
            return []

    def _analyze_funding_rate(self, symbol):
        try:
            funding_rate = self.funding_rates.get(symbol, 0)

            if funding_rate < -0.0003:
                return {
                    "strategy": "FUNDING_RATE_LONG_BIAS",
                    "signal": "BUY",
                    "confidence": 0.7,
                    "reason": f"Negative funding rate: {funding_rate:.4%}",
                }
            if funding_rate > 0.0003:
                return {
                    "strategy": "FUNDING_RATE_SHORT_BIAS",
                    "signal": "SELL",
                    "confidence": 0.7,
                    "reason": f"Positive funding rate: {funding_rate:.4%}",
                }
        except Exception:
            pass
        return None

    def _analyze_open_interest(self, market_data):
        try:
            oi_change = market_data.get("open_interest_change", 0)
            oi_value = market_data.get("open_interest", 0)

            if oi_change > 0.1 and oi_value > 1_000_000:
                return {
                    "strategy": "OPEN_INTEREST_BULLISH",
                    "signal": "BUY",
                    "confidence": 0.65,
                    "reason": f"Open interest rising: +{oi_change:.1%}",
                }
            if oi_change < -0.1 and oi_value > 1_000_000:
                return {
                    "strategy": "OPEN_INTEREST_BEARISH",
                    "signal": "SELL",
                    "confidence": 0.65,
                    "reason": f"Open interest falling: {oi_change:.1%}",
                }
        except Exception:
            pass
        return None

    def _analyze_liquidations(self, market_data):
        try:
            long_liq = market_data.get("long_liquidations", 0)
            short_liq = market_data.get("short_liquidations", 0)

            if long_liq > short_liq * 2:
                return {
                    "strategy": "LIQUIDATION_SHORT_SQUEEZE_POTENTIAL",
                    "signal": "BUY",
                    "confidence": 0.6,
                    "reason": f"Long liquidations dominant: {long_liq:.0f} vs {short_liq:.0f}",
                }
            if short_liq > long_liq * 2:
                return {
                    "strategy": "LIQUIDATION_LONG_SQUEEZE_POTENTIAL",
                    "signal": "SELL",
                    "confidence": 0.6,
                    "reason": f"Short liquidations dominant: {short_liq:.0f} vs {long_liq:.0f}",
                }
        except Exception:
            pass
        return None

    def _analyze_basis(self, market_data):
        try:
            basis = market_data.get("basis", 0)
            if basis > 0.002:
                return {
                    "strategy": "POSITIVE_BASIS_LONG",
                    "signal": "BUY",
                    "confidence": 0.65,
                    "reason": f"Positive basis: {basis:.3%}",
                }
            if basis < -0.002:
                return {
                    "strategy": "NEGATIVE_BASIS_SHORT",
                    "signal": "SELL",
                    "confidence": 0.65,
                    "reason": f"Negative basis: {basis:.3%}",
                }
        except Exception:
            pass
        return None

    def _analyze_long_short_ratio(self, market_data):
        try:
            ls_ratio = market_data.get("long_short_ratio", 1.0)
            if ls_ratio < 0.8:
                return {
                    "strategy": "LOW_LS_RATIO_LONG",
                    "signal": "BUY",
                    "confidence": 0.6,
                    "reason": f"Low L/S ratio: {ls_ratio:.2f}",
                }
            if ls_ratio > 1.2:
                return {
                    "strategy": "HIGH_LS_RATIO_SHORT",
                    "signal": "SELL",
                    "confidence": 0.6,
                    "reason": f"High L/S ratio: {ls_ratio:.2f}",
                }
        except Exception:
            pass
        return None

    def get_futures_dashboard_data(self, symbol=None):
        try:
            data = {
                "leverage_settings": self.leverage_settings,
                "funding_rates": self.funding_rates,
                "positions": self.positions,
                "config": self.futures_config,
            }

            if symbol:
                return {
                    "leverage": self.leverage_settings.get(
                        symbol, self.default_leverage
                    ),
                    "funding_rate": self.funding_rates.get(symbol, 0),
                    "position": self.positions.get(symbol),
                }

            return data
        except Exception as e:
            print(f"❌ Futures dashboard data error: {e}")
            return {}
