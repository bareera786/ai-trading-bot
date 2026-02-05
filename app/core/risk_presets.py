"""
Risk Management Presets
Provides pre-configured risk profiles for different trading styles
"""

# Risk Preset Configurations
RISK_PRESETS = {
    "conservative": {
        "name": "Conservative",
        "description": "Low risk, high confidence trades only",
        "icon": "🛡️",
        "risk_per_trade": 0.01,  # 1% of portfolio per trade
        "max_positions": 3,
        "confidence_threshold": 0.40,
        "min_confidence_diff": 0.15,
        "stop_loss": 0.02,  # 2%
        "take_profit": 0.04,  # 4% (2:1 reward/risk)
        "max_daily_loss": 0.03,  # 3% max daily loss
        "use_trailing_stop": True,
        "trailing_stop_distance": 0.015,  # 1.5%
    },
    "moderate": {
        "name": "Moderate",
        "description": "Balanced risk/reward approach",
        "icon": "⚖️",
        "risk_per_trade": 0.02,  # 2% of portfolio per trade
        "max_positions": 5,
        "confidence_threshold": 0.30,
        "min_confidence_diff": 0.08,
        "stop_loss": 0.03,  # 3%
        "take_profit": 0.06,  # 6% (2:1 reward/risk)
        "max_daily_loss": 0.05,  # 5% max daily loss
        "use_trailing_stop": True,
        "trailing_stop_distance": 0.02,  # 2%
    },
    "aggressive": {
        "name": "Aggressive",
        "description": "Higher risk for potentially higher returns",
        "icon": "🚀",
        "risk_per_trade": 0.03,  # 3% of portfolio per trade
        "max_positions": 8,
        "confidence_threshold": 0.25,
        "min_confidence_diff": 0.05,
        "stop_loss": 0.05,  # 5%
        "take_profit": 0.10,  # 10% (2:1 reward/risk)
        "max_daily_loss": 0.08,  # 8% max daily loss
        "use_trailing_stop": True,
        "trailing_stop_distance": 0.03,  # 3%
    },
    "custom": {
        "name": "Custom",
        "description": "Your personalized settings",
        "icon": "⚙️",
        # Custom preset uses current config values
    }
}


def get_preset(preset_name: str) -> dict:
    """Get risk preset configuration by name"""
    return RISK_PRESETS.get(preset_name, RISK_PRESETS["moderate"])


def calculate_risk_metrics(preset: dict, portfolio_value: float = 10000) -> dict:
    """
    Calculate risk metrics for a given preset
    
    Args:
        preset: Risk preset configuration
        portfolio_value: Total portfolio value in USD
        
    Returns:
        Dictionary with calculated risk metrics
    """
    risk_per_trade = preset.get("risk_per_trade", 0.02)
    max_positions = preset.get("max_positions", 5)
    stop_loss = preset.get("stop_loss", 0.03)
    take_profit = preset.get("take_profit", 0.06)
    max_daily_loss = preset.get("max_daily_loss", 0.05)
    
    # Calculate metrics
    max_loss_per_trade = portfolio_value * risk_per_trade
    max_total_exposure = max_loss_per_trade * max_positions
    max_daily_loss_amount = portfolio_value * max_daily_loss
    
    # Position sizing
    position_size = max_loss_per_trade / stop_loss
    
    # Potential profit per trade
    potential_profit = position_size * take_profit
    
    # Risk/Reward ratio
    risk_reward_ratio = take_profit / stop_loss
    
    return {
        "portfolio_value": portfolio_value,
        "max_loss_per_trade": max_loss_per_trade,
        "max_total_exposure": max_total_exposure,
        "max_daily_loss_amount": max_daily_loss_amount,
        "position_size": position_size,
        "potential_profit": potential_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "max_positions": max_positions,
        "stop_loss_pct": stop_loss * 100,
        "take_profit_pct": take_profit * 100,
    }


def apply_preset_to_config(preset_name: str, current_config: dict) -> dict:
    """
    Apply a risk preset to the current trading configuration
    
    Args:
        preset_name: Name of the preset to apply
        current_config: Current trading configuration
        
    Returns:
        Updated configuration with preset values
    """
    preset = get_preset(preset_name)
    
    if preset_name == "custom":
        # Don't modify custom preset
        return current_config
    
    # Update config with preset values
    updated_config = current_config.copy()
    
    # Map preset keys to config keys
    key_mapping = {
        "risk_per_trade": "risk_per_trade",
        "max_positions": "max_positions",
        "confidence_threshold": "confidence_threshold",
        "min_confidence_diff": "min_confidence_diff",
        "stop_loss": "stop_loss_multiplier",
        "take_profit": "take_profit_multiplier",
    }
    
    for preset_key, config_key in key_mapping.items():
        if preset_key in preset:
            updated_config[config_key] = preset[preset_key]
    
    return updated_config
