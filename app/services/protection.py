"""
Enhanced Protection Service with Per-User Controls

DEPRECATED: Use app.domain.trading.risk.RiskManager instead.
This file is kept for backward compatibility.
"""

from app.domain.trading.risk import RiskManager

# Alias for backward compatibility
ProtectionService = RiskManager

