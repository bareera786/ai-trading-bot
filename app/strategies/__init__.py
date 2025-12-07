"""Strategy primitives exposed for the Flask app."""

from .base import (
    BaseStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    MomentumStrategy,
    ArbitrageStrategy,
    MLBasedStrategy,
    ScalpingStrategy,
)
from .manager import StrategyManager
from .qfm import QuantumFusionMomentumEngine

__all__ = [
    'BaseStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'MomentumStrategy',
    'ArbitrageStrategy',
    'MLBasedStrategy',
    'ScalpingStrategy',
    'StrategyManager',
    'QuantumFusionMomentumEngine',
]
