"""Lightweight RIBS progress endpoint (separate blueprint to avoid touching status.py)
"""
from flask import Blueprint, jsonify, current_app
import os
import json
import time
import asyncio

from app.services.pathing import resolve_profile_path
try:
    from app.integrations.ribs_connector import RIBSConnector
except Exception:
    # Optional integration - provide a safe fallback so the app can start
    class RIBSConnector:
        def __init__(self, *args, **kwargs):
            pass

        async def connect(self):
            raise RuntimeError("RIBS connector unavailable in this environment")

        async def disconnect(self):
            return None

        async def get_market_regime(self):
            return None

        async def get_behavioral_analytics(self, user_id):
            return []

        async def get_user_risk_score(self, user_id):
            return None

        async def get_user_risk_adjustments(self, user_id):
            return {}

ribs_progress_bp = Blueprint("ribs_progress", __name__)



def _get_control_path():
    """Get path to the RIBS control file."""
    return os.path.join(
        resolve_profile_path("bot_persistence"), "ribs_checkpoints", "ribs_control.json"
    )


def _write_control_state(command: str):
    """Write control state to file."""
    path = _get_control_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            "command": command,
            "timestamp": time.time(),
            "active": command == "START"
        }, f)


@ribs_progress_bp.route("/api/ribs/start", methods=["POST"])
def api_ribs_start():
    """Start the RIBS optimization process."""
    try:
        _write_control_state("START")
        return jsonify({"success": True, "message": "RIBS optimization started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ribs_progress_bp.route("/api/ribs/pause", methods=["POST"])
def api_ribs_pause():
    """Pause the RIBS optimization process."""
    try:
        _write_control_state("PAUSE")
        return jsonify({"success": True, "message": "RIBS optimization paused"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ribs_progress_bp.route("/api/ribs/reset", methods=["POST"])
def api_ribs_reset():
    """Reset the RIBS archive and optimization state."""
    try:
        _write_control_state("RESET")
        return jsonify({"success": True, "message": "Reset command queued"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@ribs_progress_bp.route("/api/ribs/progress", methods=["GET"])
def api_ribs_progress():
    """Return lightweight RIBS progress information read from ribs_status.json"""
    status_path = os.path.join(
        resolve_profile_path("bot_persistence"), "ribs_checkpoints", "ribs_status.json"
    )
    if not os.path.exists(status_path):
        # Fallback: Check if control file says we started
        control_path = _get_control_path()
        is_starting = False
        if os.path.exists(control_path):
            try:
                with open(control_path, "r") as cf:
                    control = json.load(cf)
                    if control.get("action") == "start":
                        is_starting = True
            except Exception:
                pass
        
        if is_starting:
            return jsonify({
                "running": True, 
                "progress_percent": 0, 
                "message": "Initializing worker..."
            })
            
        return (
            jsonify({"status": "missing", "message": "RIBS status file not found"}),
            404,
        )

    try:
        with open(status_path, "r") as sf:
            status = json.load(sf)
        # Compute checkpoint age (seconds) for frontend health indicators
        latest_ck = status.get("latest_checkpoint") or {}
        ck_mtime = latest_ck.get("mtime")
        ck_age = None
        try:
            if ck_mtime is not None:
                ck_age = int(time.time() - float(ck_mtime))
        except Exception:
            ck_age = None

        # Try to get behavior data from status file first
        behaviors_x = status.get("behaviors_x", [])
        behaviors_y = status.get("behaviors_y", [])
        behaviors_z = status.get("behaviors_z", [])
        objectives = status.get("objectives", [])

        # If behavior data is empty, try to get it from the checkpoint
        if not behaviors_x:
            try:
                # Try to load the latest checkpoint and extract elite strategies
                checkpoint_path = status.get("latest_checkpoint", {}).get("path")
                if checkpoint_path and os.path.exists(checkpoint_path):
                    # Import here to avoid circular imports
                    from app.services.ribs_optimizer import TradingRIBSOptimizer

                    # Create a temporary optimizer instance just to load the checkpoint
                    temp_optimizer = TradingRIBSOptimizer()
                    temp_optimizer.load_checkpoint(checkpoint_path)

                    # Get elite strategies
                    elites = temp_optimizer.get_elite_strategies(top_n=10) or []
                    if elites:
                        behaviors_x = [
                            e.get("behavior", [None, None, None])[0] for e in elites
                        ]
                        behaviors_y = [
                            e.get("behavior", [None, None, None])[1] for e in elites
                        ]
                        behaviors_z = [
                            e.get("behavior", [None, None, None])[2] for e in elites
                        ]
                        objectives = [e.get("objective") for e in elites]
                        print(f"DEBUG: Extracted {len(elites)} elites from checkpoint")
                    else:
                        print("DEBUG: No elites returned from get_elite_strategies")
                else:
                    print(f"DEBUG: Checkpoint path not found: {checkpoint_path}")
            except Exception as e:
                # Silently fail, use empty arrays
                print(f"DEBUG: Failed to extract behavior data: {e}")
                pass

        progress = {
            "running": status.get("running", False),
            "current_iteration": status.get("current_iteration"),
            "progress_percent": status.get("progress_percent"),
            "archive_stats": status.get("archive_stats", {}),
            "latest_checkpoint": latest_ck,
            "latest_checkpoint_age_seconds": ck_age,
            # Simple health: consider healthy if checkpoint age <= 3600s
            "healthy": (ck_age is not None and ck_age <= 3600),
            # Include behavior data for 3D visualization
            "behaviors_x": behaviors_x,
            "behaviors_y": behaviors_y,
            "behaviors_z": behaviors_z,
            "objectives": objectives,
        }
        return jsonify(progress)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500




@ribs_progress_bp.route("/api/ribs/connector/status", methods=["GET"])
def api_ribs_connector_status():
    """Return RIBS connector status and health information"""
    try:
        connector = RIBSConnector()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_status():
            try:
                await connector.connect()
                # Test connection by getting market regime
                regime = await connector.get_market_regime()
                await connector.disconnect()

                return {
                    "connected": True,
                    "market_regime": regime,
                    "last_check": int(time.time()),
                    "healthy": True
                }
            except Exception as e:
                return {
                    "connected": False,
                    "error": str(e),
                    "last_check": int(time.time()),
                    "healthy": False
                }

        status = loop.run_until_complete(get_status())
        loop.close()

        return jsonify(status)
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e),
            "last_check": int(time.time()),
            "healthy": False
        }), 500


@ribs_progress_bp.route("/api/ribs/connector/analytics/<user_id>", methods=["GET"])
def api_ribs_connector_analytics(user_id):
    """Return behavioral analytics for a specific user"""
    try:
        connector = RIBSConnector()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_analytics():
            try:
                await connector.connect()
                analytics = await connector.get_behavioral_analytics(user_id)
                risk_score = await connector.get_user_risk_score(user_id)
                risk_adjustments = await connector.get_user_risk_adjustments(user_id)
                await connector.disconnect()

                return {
                    "user_id": user_id,
                    "behavioral_analytics": analytics,
                    "risk_score": risk_score,
                    "risk_adjustments": risk_adjustments,
                    "last_updated": int(time.time())
                }
            except Exception as e:
                return {
                    "user_id": user_id,
                    "error": str(e),
                    "last_updated": int(time.time())
                }

        analytics = loop.run_until_complete(get_analytics())
        loop.close()

        return jsonify(analytics)
    except Exception as e:
        return jsonify({
            "user_id": user_id,
            "error": str(e),
            "last_updated": int(time.time())
        }), 500


@ribs_progress_bp.route("/api/ribs/connector/market-regime", methods=["GET"])
def api_ribs_connector_market_regime():
    """Return current market regime from RIBS connector"""
    try:
        connector = RIBSConnector()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_regime():
            try:
                await connector.connect()
                regime = await connector.get_market_regime()
                correlation = await connector.get_correlation_matrix()
                await connector.disconnect()

                return {
                    "current_regime": regime,
                    "correlation_matrix": correlation,
                    "last_updated": int(time.time())
                }
            except Exception as e:
                return {
                    "current_regime": "unknown",
                    "error": str(e),
                    "last_updated": int(time.time())
                }

        regime_data = loop.run_until_complete(get_regime())
        loop.close()

        return jsonify(regime_data)
    except Exception as e:
        return jsonify({
            "current_regime": "unknown",
            "error": str(e),
            "last_updated": int(time.time())
        }), 500


@ribs_progress_bp.route("/api/ribs/logs", methods=["GET"])
def api_ribs_logs():
    """Return recent RIBS-related logs."""
    try:
        # Correct path for container environment: /app/logs/default/bot.log
        log_file = os.path.join(os.getcwd(), "logs", "default", "bot.log")
        if not os.path.exists(log_file):
            # Fallback for local dev or different structure
            log_file = os.path.join(os.getcwd(), "bot.log")
            if not os.path.exists(log_file):
                 return jsonify({"logs": [f"Log file not found at {log_file}"]})

        logs = []
        # Read last 1000 lines and filter for RIBS context
        # Check if we can use 'tail' command for efficiency or read in python
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                # Seek to end and read backwards efficiently would be better, but for now:
                # Read all lines is too slow for 60MB.
                # Let's simple seek to near end.
                f.seek(0, 2)
                size = f.tell()
                # Read last 100KB
                read_size = min(size, 100 * 1024)
                f.seek(size - read_size)
                content = f.read()
                lines = content.splitlines()
                
                # Filter for relevant keywords
                keywords = ["RIBS", "SelfImprovement", "Optimizer", "WalkForward"]
                
                for line in lines:
                    if any(k in line for k in keywords):
                        logs.append(line)
        except Exception as e:
            logs.append(f"Error reading logs: {str(e)}")

        # Return last 100 matches
        return jsonify({"logs": logs[-100:]})
    except Exception as e:
        return jsonify({"logs": [f"System Error: {str(e)}"]}), 500
