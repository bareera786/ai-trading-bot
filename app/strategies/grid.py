"""Grid Trading Strategy Implementation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal

from .base import BaseStrategy

logger = logging.getLogger(__name__)

class GridStrategy(BaseStrategy):
    """
    Grid Trading Bot Strategy.
    
    Places a grid of buy and sell orders within a specified price range.
    Profits from volatility by buying low and selling high.
    """

    def __init__(self, name: str = "grid_bot", config: Dict[str, Any] = None):
        # Initialize parent with proper BaseStrategy signature
        super().__init__(
            name=name,
            description="Grid Trading Bot - Places buy/sell orders in a grid pattern",
            parameters=config or {}
        )
        # Grid-specific configuration
        self.lower_price = self.parameters.get("lower_price", 0.0)
        self.upper_price = self.parameters.get("upper_price", 0.0)
        self.grid_lines = self.parameters.get("grid_lines", 10)
        self.investment = self.parameters.get("investment", 1000.0)
        self.active_orders = [] # Mock open orders
        self.grids = []
        self._initialize_grids()

    def _initialize_grids(self):
        """Calculate grid levels."""
        if self.lower_price >= self.upper_price or self.grid_lines < 2:
            return

        step = (self.upper_price - self.lower_price) / self.grid_lines
        self.grids = [self.lower_price + i * step for i in range(self.grid_lines + 1)]

    def _get_price(self, market_data: Any) -> float:
        """Extract current price from market data."""
        if not market_data:
            return 0.0
        
        # Handle dict format (single ticker/candle)
        if isinstance(market_data, dict):
            return float(market_data.get("close", market_data.get("price", market_data.get("lastPrice", 0))))
        
        # Handle list format (candles/ticks)
        if isinstance(market_data, list) and len(market_data) > 0:
            last_item = market_data[-1]
            if isinstance(last_item, dict):
                return float(last_item.get("close", last_item.get("price", 0)))
            return float(last_item)
        
        return 0.0

    def analyze(self, market_data: Any) -> Dict[str, Any]:
        """
        Check current price against grid levels.
        In a real implementation, this would manage limit orders.
        For simulation/paper, we check crossings.
        """
        current_price = self._get_price(market_data)
        if not current_price:
            return {"signal": "hold", "confidence": 0.0, "reason": "No price data"}

        # Guard: If grids not configured, return HOLD
        if not self.grids:
            return {"signal": "hold", "confidence": 0.0, "reason": "Grid not configured"}

        # Simple logic: If price hits a lower grid line, Signal BUY
        # If price hits an upper grid line, Signal SELL
        # This is a stateless simplification for the "Gap Analysis" demo.
        
        signal = "hold"
        confidence = 0.0
        
        # Determine nearest grid line
        nearest_grid = min(self.grids, key=lambda x: abs(x - current_price))
        distance_pct = abs(current_price - nearest_grid) / current_price

        if distance_pct < 0.001: # Within 0.1% of a grid line
            # If we are at a low grid line relative to middle, BUY
            mid_price = (self.upper_price + self.lower_price) / 2
            if current_price < mid_price:
                signal = "buy"
                confidence = 0.8
            elif current_price > mid_price:
                signal = "sell"
                confidence = 0.8

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": self.name,
            "meta": {
                "nearest_grid": nearest_grid,
                "grids": self.grids
            }
        }

    def update_parameters(self, new_params: Dict[str, Any]):
        """Update grid settings dynamically."""
        super().update_parameters(new_params)
        try:
            if "lower_price" in new_params:
                self.lower_price = float(new_params["lower_price"])
            if "upper_price" in new_params:
                self.upper_price = float(new_params["upper_price"])
            if "grid_lines" in new_params:
                self.grid_lines = int(new_params["grid_lines"])
            
            # Re-calc grids
            self._initialize_grids()
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to update grid parameters: {e}")
            # Keep old values or raise? Better to log and continue with old or partial updates
            pass

    def analyze_market(self, symbol, market_data, indicators=None):
        """
        Interface method required by BaseStrategy.
        Delegates to existing analyze() method.
        """
        return self.analyze(market_data)
