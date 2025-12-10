"""Quantum Fusion Momentum analytics engine extracted from the monolithic app."""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, List

import numpy as np


class QuantumFusionMomentumEngine:
    """Advanced Quantum Fusion Momentum Analytics Engine for market analysis."""

    def __init__(self):
        self.feature_history: Dict[str, Deque[dict]] = {}
        self.market_regime_history: Dict[str, List[dict]] = {}
        self.velocity_cache: Dict[str, Deque[float]] = {}
        self.acceleration_cache: Dict[str, Deque[float]] = {}
        self.jerk_cache: Dict[str, Deque[float]] = {}
        self.max_history_size = 1000

    def compute_realtime_features(self, symbol, market_data):
        """Compute real-time QFM features for a symbol."""
        if not market_data or not isinstance(market_data, dict):
            return {}

        # Extract price data
        close_price = market_data.get("close", market_data.get("price", 0))
        volume = market_data.get("volume", 0)
        high = market_data.get("high", close_price)
        low = market_data.get("low", close_price)

        # Initialize symbol history if needed
        if symbol not in self.feature_history:
            self.feature_history[symbol] = deque(maxlen=self.max_history_size)
            self.velocity_cache[symbol] = deque(maxlen=self.max_history_size)
            self.acceleration_cache[symbol] = deque(maxlen=self.max_history_size)
            self.jerk_cache[symbol] = deque(maxlen=self.max_history_size)

        # Calculate QFM features
        features = self._calculate_qfm_features(symbol, close_price, volume, high, low)

        # Store in history
        self.feature_history[symbol].append(
            {
                "timestamp": time.time(),
                "features": features.copy(),
                "price": close_price,
                "volume": volume,
            }
        )

        return features

    def _calculate_qfm_features(self, symbol, price, volume, high, low):
        """Calculate comprehensive QFM features."""
        features = {}

        # Basic momentum calculations
        features["price"] = price
        features["volume"] = volume

        # Calculate velocity (rate of price change)
        velocity = self._calculate_velocity(symbol, price)
        features["velocity"] = velocity

        # Calculate acceleration (rate of velocity change)
        acceleration = self._calculate_acceleration(symbol, velocity)
        features["acceleration"] = acceleration

        # Calculate jerk (rate of acceleration change)
        jerk = self._calculate_jerk(symbol, acceleration)
        features["jerk"] = jerk

        # Volume pressure analysis
        volume_pressure = self._calculate_volume_pressure(symbol, volume, price)
        features["volume_pressure"] = volume_pressure

        # Trend confidence based on momentum consistency
        trend_confidence = self._calculate_trend_confidence(symbol)
        features["trend_confidence"] = trend_confidence

        # Market regime score (0-1, higher = more trending)
        regime_score = self._calculate_regime_score(features)
        features["regime_score"] = regime_score

        # Entropy measure for market randomness
        entropy = self._calculate_market_entropy(symbol)
        features["entropy"] = entropy

        # Volatility measure
        volatility = self._calculate_volatility(symbol, high, low)
        features["volatility"] = volatility

        return features

    def _calculate_velocity(self, symbol, current_price):
        """Calculate price velocity (momentum)."""
        history = self.feature_history.get(symbol, [])

        if len(history) < 2:
            return 0.0

        # Use exponential moving average for smoother velocity
        prices = [h["price"] for h in history[-10:]]  # Last 10 points

        if len(prices) < 2:
            return 0.0

        # Calculate rate of change
        recent_change = (
            (current_price - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        )

        # Store velocity
        self.velocity_cache[symbol].append(recent_change)

        return recent_change

    def _calculate_acceleration(self, symbol, current_velocity):
        """Calculate acceleration (change in momentum)."""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 2:
            return 0.0

        # Rate of change of velocity
        acceleration = current_velocity - velocities[-2]

        # Store acceleration
        self.acceleration_cache[symbol].append(acceleration)

        return acceleration

    def _calculate_jerk(self, symbol, current_acceleration):
        """Calculate jerk (change in acceleration)."""
        accelerations = list(self.acceleration_cache.get(symbol, []))

        if len(accelerations) < 2:
            return 0.0

        # Rate of change of acceleration
        jerk = current_acceleration - accelerations[-2]

        # Store jerk
        self.jerk_cache[symbol].append(jerk)

        return jerk

    def _calculate_volume_pressure(self, symbol, volume, price):
        """Calculate volume pressure indicator."""
        history = self.feature_history.get(symbol, [])

        if len(history) < 5:
            return 0.0

        # Average volume over last 5 periods
        avg_volume = np.mean([h["volume"] for h in history[-5:]])

        if avg_volume == 0:
            return 0.0

        # Volume pressure: current volume relative to average
        volume_pressure = (volume - avg_volume) / avg_volume

        # Weight by price movement direction
        price_change = 0
        if len(history) >= 2:
            price_change = (price - history[-2]["price"]) / history[-2]["price"]

        # Positive pressure when volume increases with price movement
        volume_pressure *= 1 + abs(price_change)

        return volume_pressure

    def _calculate_trend_confidence(self, symbol):
        """Calculate trend confidence based on momentum consistency."""
        velocities = list(self.velocity_cache.get(symbol, []))

        if len(velocities) < 5:
            return 0.5

        # Check consistency of directional movement
        recent_velocities = velocities[-10:]

        # Count directional consistency
        positive_count = sum(1 for v in recent_velocities if v > 0)
        negative_count = sum(1 for v in recent_velocities if v < 0)

        # Confidence based on directional dominance
        total_directional = positive_count + negative_count
        if total_directional == 0:
            return 0.5

        confidence = max(positive_count, negative_count) / total_directional

        return confidence

    def _calculate_regime_score(self, features):
        """Calculate market regime score (0-1, higher = trending)."""
        velocity = abs(features.get("velocity", 0))
        acceleration = abs(features.get("acceleration", 0))
        trend_confidence = features.get("trend_confidence", 0.5)
        entropy = features.get("entropy", 0.5)

        # Regime score combines momentum strength and trend consistency
        momentum_strength = min(1.0, (velocity + acceleration) * 10)  # Scale and cap

        # Lower entropy = more ordered (trending) market
        order_factor = 1.0 - entropy

        # Combine factors
        regime_score = (
            momentum_strength * 0.4 + trend_confidence * 0.4 + order_factor * 0.2
        )

        return min(1.0, max(0.0, regime_score))

    def _calculate_market_entropy(self, symbol):
        """Calculate market entropy (randomness measure)."""
        history = self.feature_history.get(symbol, [])

        if len(history) < 10:
            return 0.5

        # Calculate price return distribution
        prices = [h["price"] for h in history[-20:]]
        returns = []

        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        if len(returns) < 5:
            return 0.5

        # Calculate entropy of return distribution
        try:
            # Discretize returns into bins
            bins = np.histogram(returns, bins=10)[0]
            bins = bins[bins > 0]  # Remove zero bins
            probs = bins / np.sum(bins)

            # Shannon entropy
            entropy = -np.sum(probs * np.log2(probs))

            # Normalize to 0-1 scale
            max_entropy = np.log2(len(bins))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.5

            return normalized_entropy

        except Exception:
            return 0.5

    def _calculate_volatility(self, symbol, high, low):
        """Calculate price volatility."""
        if high == low:
            return 0.0

        # Range-based volatility
        range_volatility = (high - low) / ((high + low) / 2)

        # Historical volatility
        history = self.feature_history.get(symbol, [])
        if len(history) >= 5:
            recent_prices = [h["price"] for h in history[-5:]]
            price_std = np.std(recent_prices)
            price_mean = np.mean(recent_prices)

            if price_mean != 0:
                hist_volatility = price_std / price_mean
                # Combine range and historical volatility
                return (range_volatility + hist_volatility) / 2

        return range_volatility

    def get_market_regime(self, symbol):
        """Get current market regime classification."""
        features = self.get_latest_features(symbol)

        if not features:
            return "unknown"

        regime_score = features.get("regime_score", 0.5)
        trend_confidence = features.get("trend_confidence", 0.5)
        jerk = abs(features.get("jerk", 0))

        # Classify regime
        if regime_score > 0.7 and trend_confidence > 0.6:
            velocity = features.get("velocity", 0)
            return "trending_bull" if velocity > 0 else "trending_bear"
        elif jerk > 0.5:
            return "volatile"
        elif regime_score < 0.4:
            return "sideways"
        else:
            return "calm"

    def get_latest_features(self, symbol):
        """Get latest QFM features for a symbol."""
        history = self.feature_history.get(symbol, [])

        if not history:
            return {}

        return history[-1]["features"]

    def get_feature_history(self, symbol, limit=100):
        """Get historical QFM features for analysis."""
        history = self.feature_history.get(symbol, [])

        return list(history)[-limit:] if history else []

    def analyze_market_cycles(self, symbol):
        """Analyze market cycles using QFM features."""
        history = self.get_feature_history(symbol, 200)

        if len(history) < 20:
            return {"error": "Insufficient data for cycle analysis"}

        # Extract features over time
        velocities = [h["features"]["velocity"] for h in history]
        accelerations = [h["features"]["acceleration"] for h in history]
        regime_scores = [h["features"]["regime_score"] for h in history]

        # Detect cycles using acceleration changes
        cycle_analysis = {
            "cycle_length_avg": self._calculate_average_cycle_length(accelerations),
            "current_phase": self._determine_current_cycle_phase(accelerations),
            "cycle_strength": np.std(accelerations),
            "regime_transitions": self._count_regime_transitions(regime_scores),
            "momentum_cycles": self._analyze_momentum_cycles(velocities),
        }

        return cycle_analysis

    def _calculate_average_cycle_length(self, accelerations):
        """Calculate average cycle length from acceleration data."""
        if len(accelerations) < 10:
            return 0

        # Find zero crossings in acceleration (cycle boundaries)
        zero_crossings = []
        for i in range(1, len(accelerations)):
            if accelerations[i - 1] * accelerations[i] < 0:  # Sign change
                zero_crossings.append(i)

        if len(zero_crossings) < 2:
            return len(accelerations)  # Default to full period

        # Calculate cycle lengths
        cycle_lengths = []
        for i in range(1, len(zero_crossings)):
            cycle_lengths.append(zero_crossings[i] - zero_crossings[i - 1])

        return float(np.mean(cycle_lengths)) if cycle_lengths else len(accelerations)

    def _determine_current_cycle_phase(self, accelerations):
        """Determine current position in market cycle."""
        if len(accelerations) < 5:
            return "unknown"

        recent_acc = accelerations[-5:]

        # Analyze recent acceleration trend
        if all(a > 0 for a in recent_acc):
            return "acceleration_phase"
        if all(a < 0 for a in recent_acc):
            return "deceleration_phase"
        return "transition_phase"

    def _count_regime_transitions(self, regime_scores):
        """Count regime transitions over time."""
        if len(regime_scores) < 2:
            return 0

        transitions = 0
        threshold_high = 0.6
        threshold_low = 0.4

        for i in range(1, len(regime_scores)):
            prev_regime = (
                "high"
                if regime_scores[i - 1] > threshold_high
                else ("low" if regime_scores[i - 1] < threshold_low else "neutral")
            )
            curr_regime = (
                "high"
                if regime_scores[i] > threshold_high
                else ("low" if regime_scores[i] < threshold_low else "neutral")
            )

            if prev_regime != curr_regime:
                transitions += 1

        return transitions

    def _analyze_momentum_cycles(self, velocities):
        """Analyze momentum cycles."""
        if len(velocities) < 10:
            return {"cycles": 0, "strength": 0}

        # Find momentum cycles (direction changes)
        direction_changes = []
        for i in range(1, len(velocities)):
            if velocities[i - 1] * velocities[i] < 0:  # Direction change
                direction_changes.append(i)

        cycle_info = {
            "cycles": len(direction_changes),
            "average_length": float(np.mean(np.diff(direction_changes)))
            if len(direction_changes) > 1
            else 0,
            "strength": float(np.std(velocities)),
        }

        return cycle_info
