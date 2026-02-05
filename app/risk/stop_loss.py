import numpy as np
from datetime import datetime
from app.core.config_trading import TRADING_CONFIG

class AdvancedStopLossSystem:
    def __init__(self):
        self.stop_loss_types = ["FIXED", "ATR", "TRAILING", "TIME", "VOLATILITY"]
        self.position_metrics = {}

    def calculate_multiple_stop_losses(
        self, symbol, entry_price, current_price, historical_prices, atr_value=None
    ):
        """Calculate multiple stop-loss levels"""
        stops = {}

        # 1. Fixed percentage stop-loss
        stops["fixed"] = entry_price * (1 - TRADING_CONFIG["stop_loss"])

        # 2. ATR-based stop-loss (Aggressive: 1.2 ATR instead of 2.0)
        if atr_value and atr_value > 0:
            stops["atr"] = current_price - (atr_value * 1.2)
        else:
            stops["atr"] = entry_price * 0.985  # Fallback

        # 3. Trailing stop-loss (Aggressive: 2% from peak instead of 5%)
        if symbol in self.position_metrics:
            peak_price = self.position_metrics[symbol].get("peak_price", entry_price)
            stops["trailing"] = peak_price * 0.98
            # Update peak price
            if current_price > peak_price:
                self.position_metrics[symbol]["peak_price"] = current_price
        else:
            stops["trailing"] = entry_price * 0.98
            self.position_metrics[symbol] = {
                "peak_price": entry_price,
                "entry_time": datetime.now(),
            }

        # 4. Time-based stop-loss (Aggressive: 3 days instead of 7)
        if symbol in self.position_metrics:
            entry_time = self.position_metrics[symbol].get("entry_time", datetime.now())
            days_held = (datetime.now() - entry_time).days
            if days_held >= 3:
                stops["time"] = current_price * 0.995  # Tight stop after 3 days
            else:
                stops["time"] = 0
        else:
            stops["time"] = 0

        # 5. Volatility-based stop-loss (Aggressive: 2x std dev instead of 3x)
        if len(historical_prices) >= 20:
            volatility = np.std(np.diff(np.log(historical_prices[-20:]))) * np.sqrt(365)
            vol_stop = current_price * (1 - (volatility * 2))  # 2x volatility
            stops["volatility"] = max(vol_stop, entry_price * 0.95)  # Cap at 5% loss
        else:
            stops["volatility"] = entry_price * 0.98

        return stops

    def should_trigger_stop_loss(self, symbol, current_price, position, stops):
        """Check if any stop-loss should be triggered"""
        triggered_stops = []

        # Fixed stop-loss
        if current_price <= stops["fixed"]:
            triggered_stops.append(("FIXED", stops["fixed"]))

        # ATR stop-loss
        if current_price <= stops["atr"]:
            triggered_stops.append(("ATR", stops["atr"]))

        # Trailing stop-loss
        if stops["trailing"] > 0 and current_price <= stops["trailing"]:
            triggered_stops.append(("TRAILING", stops["trailing"]))

        # Time stop-loss
        if stops["time"] > 0 and current_price <= stops["time"]:
            triggered_stops.append(("TIME", stops["time"]))

        # Volatility stop-loss
        if current_price <= stops["volatility"]:
            triggered_stops.append(("VOLATILITY", stops["volatility"]))

        if triggered_stops:
            # Return the most conservative (lowest) stop-loss
            triggered_stops.sort(key=lambda x: x[1])
            return triggered_stops[0]

        return None


# ==================== ULTIMATE ENSEMBLE SYSTEM ====================
# [MODULARIZATION] Moved to app.ml.components.ensemble
from app.ml.components.ensemble import UltimateEnsembleSystem

# ==================== PROFESSIONAL PERSISTENCE SYSTEM ====================


# ==================== ULTIMATE ML TRAINING SYSTEM ====================
# ==================== FUTURES TRADING MODULE ====================
# [MODULARIZATION] Moved to app.trading.futures.module
from app.trading.futures.module import FuturesTradingModule
# ==================== ENHANCED FUTURES ML SYSTEM ====================
# ==================== ULTIMATE AI TRADER ====================
