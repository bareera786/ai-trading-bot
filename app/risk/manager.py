import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AdaptiveRiskManager:
    def __init__(self):
        self.risk_levels = {"conservative": 0.7, "moderate": 1.0, "aggressive": 1.3}
        self.current_risk_profile = "moderate"
        self.risk_adjustment_history = []
        self.volatility_regime = "NORMAL"
        self.market_stress_indicator = 0.0

    def calculate_market_stress(self, market_data, historical_data):
        """Calculate market stress indicator based on multiple factors"""
        try:
            stress_factors = []

            # Factor 1: Overall market volatility
            if historical_data:
                recent_prices = []
                # Support both dict-of-lists (multi-symbol) and single list/array inputs
                if isinstance(historical_data, dict):
                    for series in historical_data.values():
                        if series:
                            recent_prices.extend(
                                series[-10:]
                            )  # Last 10 prices per symbol
                elif isinstance(historical_data, (list, tuple, np.ndarray)):
                    recent_prices.extend(list(historical_data)[-10:])
                else:
                    # Gracefully handle unexpected types by attempting list() conversion
                    try:
                        recent_prices.extend(list(historical_data)[-10:])
                    except TypeError:
                        recent_prices = []

                if len(recent_prices) > 5:
                    returns = np.diff(np.log(recent_prices))
                    market_volatility = np.std(returns) if len(returns) > 1 else 0
                    stress_factors.append(min(market_volatility * 100, 1.0))

            # Factor 2: Correlation breakdown (during stress, correlations increase)
            correlation_stress = self.calculate_correlation_stress(market_data)
            stress_factors.append(correlation_stress)

            # Factor 3: Volume stress (unusual volume patterns)
            volume_stress = self.calculate_volume_stress(market_data)
            stress_factors.append(volume_stress)

            if stress_factors:
                self.market_stress_indicator = np.mean(stress_factors)
            else:
                self.market_stress_indicator = 0.0

            # Update volatility regime
            if self.market_stress_indicator > 0.7:
                self.volatility_regime = "HIGH_STRESS"
            elif self.market_stress_indicator > 0.4:
                self.volatility_regime = "ELEVATED"
            else:
                self.volatility_regime = "NORMAL"

            return self.market_stress_indicator

        except Exception as e:
            logger.exception("Market stress calculation error")
            return 0.0

    def calculate_correlation_stress(self, market_data):
        """Calculate correlation stress - during market stress, correlations tend to 1"""
        try:
            if len(market_data) < 3:
                return 0.0

            price_changes = {}
            for symbol, data in market_data.items():
                if "change" in data:
                    price_changes[symbol] = (
                        data["change"] / 100
                    )  # Convert percentage to decimal

            if len(price_changes) < 3:
                return 0.0

            # Create correlation matrix
            symbols = list(price_changes.keys())
            changes_matrix = np.array([price_changes[sym] for sym in symbols])

            # Calculate average correlation
            if len(symbols) > 1:
                correlation_matrix = np.corrcoef(changes_matrix)
                avg_correlation = np.mean(np.abs(correlation_matrix))
                # High average correlation indicates stress
                return min(max(avg_correlation - 0.5, 0), 1.0) * 2

        except Exception as e:
            logger.exception("Correlation stress calculation error")

        return 0.0

    def calculate_volume_stress(self, market_data):
        """Calculate volume-based stress indicator"""
        try:
            volume_changes = []
            for symbol, data in market_data.items():
                if "volume" in data and "volume_change" in data:
                    # Large volume changes indicate stress
                    vol_change = abs(data.get("volume_change", 0)) / 100
                    volume_changes.append(min(vol_change, 1.0))

            if volume_changes:
                return np.mean(volume_changes)
        except Exception as e:
            logger.exception("Volume stress calculation error")

        return 0.0

    def adjust_risk_profile(
        self, portfolio_performance, market_volatility, economic_indicators=None
    ):
        """Dynamically adjust risk profile based on conditions"""
        previous_profile = self.current_risk_profile

        # Factor 1: Portfolio performance
        if portfolio_performance < -0.08:  # 8% drawdown
            self.current_risk_profile = "conservative"
        elif (
            portfolio_performance > 0.15 and market_volatility < 0.03
        ):  # Good performance, low volatility
            self.current_risk_profile = "aggressive"
        else:
            self.current_risk_profile = "moderate"

        # Factor 2: Market stress
        if self.market_stress_indicator > 0.6:
            self.current_risk_profile = "conservative"

        # Factor 3: Volatility regime
        if self.volatility_regime == "HIGH_STRESS":
            self.current_risk_profile = "conservative"

        if previous_profile != self.current_risk_profile:
            logger.info(
                "Risk profile changed: %s -> %s",
                previous_profile,
                self.current_risk_profile,
            )

        # Log adjustment
        self.risk_adjustment_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "previous_profile": previous_profile,
                "new_profile": self.current_risk_profile,
                "stress_indicator": self.market_stress_indicator,
                "portfolio_performance": portfolio_performance,
            }
        )

        # Keep only last 50 adjustments
        if len(self.risk_adjustment_history) > 50:
            self.risk_adjustment_history.pop(0)

        return (
            self.risk_adjustment_history[-1] if self.risk_adjustment_history else None
        )

    def get_risk_multiplier(self):
        """Get current risk multiplier based on risk profile"""
        return self.risk_levels.get(self.current_risk_profile, 1.0)


