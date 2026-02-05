"""Indicator configuration helpers for the modular runtime layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Iterable, Mapping, MutableMapping

BEST_INDICATORS: list[str] = [
    # Core Price & Momentum
    "price_change",
    "price_momentum",
    "log_return",
    "rsi_14",
    "macd_hist",
    # Trend & Moving Averages
    "sma_20",
    "ema_12",
    "ema_26",
    "ema_cross_12_26",
    # Volatility & Risk
    "price_volatility",
    "average_true_range",
    "bb_percent_b",
    # Volume & Market Strength
    "volume_ratio",
    "volume_obv",
    "adx",
    "mfi",
    # Advanced Momentum & Trend Confirmation
    "stoch_k",
    "cci",
    "supertrend_signal",
    "supertrend_distance",
    # Quantum Fusion Momentum
    "qfm_velocity",
    "qfm_acceleration",
    "qfm_jerk",
    "qfm_volume_pressure",
    "qfm_trend_confidence",
    "qfm_regime_score",
    "qfm_entropy",
]

INDICATOR_SIGNAL_OPTIONS: tuple[str, ...] = ("CRT", "ICT", "SMC")

DEFAULT_INDICATOR_SELECTIONS: Mapping[str, Iterable[str]] = {
    "ultimate": ("CRT", "ICT", "SMC"),
    "optimized": ("CRT",),
    "futures": ("CRT", "ICT", "SMC"),
}


@dataclass
class IndicatorSelectionManager:
    """Thread-safe indicator selection state shared across runtimes."""

    _state: Dict[str, set[str]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple data wiring
        if not self._state:
            self._state = {
                profile: set(values)
                for profile, values in DEFAULT_INDICATOR_SELECTIONS.items()
            }

    # Public helpers -----------------------------------------------------
    def profiles(self) -> list[str]:
        with self._lock:
            return list(self._state.keys())

    def get_selection(self, profile: str) -> list[str]:
        with self._lock:
            return sorted(self._state.get(profile, set()))

    def set_selection(self, profile: str, selections: Iterable[str]) -> list[str]:
        valid = {option for option in selections if option in INDICATOR_SIGNAL_OPTIONS}
        with self._lock:
            self._state[profile] = valid
            return sorted(valid)

    def is_indicator_enabled(self, profile: str, indicator: str) -> bool:
        with self._lock:
            return indicator in self._state.get(profile, set())

    def snapshot(self) -> Dict[str, list[str]]:
        with self._lock:
            return {profile: sorted(values) for profile, values in self._state.items()}


def build_indicator_dashboard_refresher(
    dashboard_data: MutableMapping[str, object],
    selection_manager: IndicatorSelectionManager,
):
    """Return a callable that refreshes dashboard indicator state."""

    def refresh() -> Dict[str, list[str]]:
        selections = selection_manager.snapshot()
        dashboard_data["indicator_selections"] = selections

        system_status = dashboard_data.setdefault("system_status", {})
        system_status["crt_module_active"] = "CRT" in selections.get("ultimate", [])
        system_status["ict_module_active"] = "ICT" in selections.get("ultimate", [])
        system_status["smc_module_active"] = "SMC" in selections.get("ultimate", [])

        optimized_status = dashboard_data.setdefault("optimized_system_status", {})
        optimized_status["crt_module_active"] = "CRT" in selections.get("optimized", [])
        optimized_status["ict_module_active"] = "ICT" in selections.get("optimized", [])
        optimized_status["smc_module_active"] = "SMC" in selections.get("optimized", [])

        futures_dashboard = dashboard_data.setdefault("futures_dashboard", {})
        if isinstance(futures_dashboard, MutableMapping):
            futures_dashboard["indicator_selection"] = selections.get("futures", [])

        return selections

    return refresh
