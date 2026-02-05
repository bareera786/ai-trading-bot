"""
Risk Preset API Routes
Handles risk preset selection and application
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.core.risk_presets import RISK_PRESETS, get_preset, calculate_risk_metrics, apply_preset_to_config
from app.core.config_trading import TRADING_CONFIG
import logging

logger = logging.getLogger(__name__)

risk_presets_bp = Blueprint('risk_presets', __name__, url_prefix='/api/risk-presets')


@risk_presets_bp.route('/list', methods=['GET'])
@login_required
def list_presets():
    """Get list of available risk presets"""
    try:
        presets = []
        for key, preset in RISK_PRESETS.items():
            presets.append({
                "id": key,
                "name": preset.get("name", key.title()),
                "description": preset.get("description", ""),
                "icon": preset.get("icon", "⚙️"),
                "config": preset
            })
        
        return jsonify({
            "success": True,
            "presets": presets
        })
        
    except Exception as e:
        logger.error(f"Error listing presets: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@risk_presets_bp.route('/calculate', methods=['POST'])
@login_required
def calculate_preset_metrics():
    """Calculate risk metrics for a preset"""
    try:
        data = request.get_json()
        preset_name = data.get('preset_name', 'moderate')
        portfolio_value = float(data.get('portfolio_value', 10000))
        
        preset = get_preset(preset_name)
        metrics = calculate_risk_metrics(preset, portfolio_value)
        
        return jsonify({
            "success": True,
            "metrics": metrics,
            "preset": preset
        })
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@risk_presets_bp.route('/apply', methods=['POST'])
@login_required
def apply_preset():
    """Apply a risk preset to user's configuration"""
    try:
        data = request.get_json()
        preset_name = data.get('preset_name')
        
        if not preset_name:
            return jsonify({
                "success": False,
                "error": "Preset name is required"
            }), 400
        
        if preset_name not in RISK_PRESETS:
            return jsonify({
                "success": False,
                "error": f"Unknown preset: {preset_name}"
            }), 400
        
        # Get current config
        current_config = TRADING_CONFIG.copy()
        
        # Apply preset
        updated_config = apply_preset_to_config(preset_name, current_config)
        
        # TODO: Save to database/Redis for user
        # For now, just return the updated config
        
        logger.info(f"Applied {preset_name} preset for user {current_user.id}")
        
        return jsonify({
            "success": True,
            "message": f"{RISK_PRESETS[preset_name]['name']} preset applied successfully",
            "config": updated_config
        })
        
    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@risk_presets_bp.route('/current', methods=['GET'])
@login_required
def get_current_preset():
    """Get user's current risk preset"""
    try:
        # TODO: Get from database
        # For now, return moderate as default
        
        current_config = TRADING_CONFIG.copy()
        
        # Try to match current config to a preset
        matched_preset = "custom"
        for preset_name, preset in RISK_PRESETS.items():
            if preset_name == "custom":
                continue
            
            # Check if config matches preset
            if (current_config.get("confidence_threshold") == preset.get("confidence_threshold") and
                current_config.get("max_positions") == preset.get("max_positions")):
                matched_preset = preset_name
                break
        
        return jsonify({
            "success": True,
            "current_preset": matched_preset,
            "config": current_config
        })
        
    except Exception as e:
        logger.error(f"Error getting current preset: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
