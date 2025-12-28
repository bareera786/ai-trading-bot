"""Lightweight RIBS progress endpoint (separate blueprint to avoid touching status.py)
"""
from flask import Blueprint, jsonify
import os
import json
import time

ribs_progress_bp = Blueprint("ribs_progress", __name__)


@ribs_progress_bp.route("/api/ribs/progress", methods=["GET"])
def api_ribs_progress():
    """Return lightweight RIBS progress information read from ribs_status.json"""
    status_path = os.path.join(
        "bot_persistence", "ribs_checkpoints", "ribs_status.json"
    )
    if not os.path.exists(status_path):
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


@ribs_progress_bp.route("/api/ribs/logs", methods=["GET"])
def api_ribs_logs():
    """Return recent RIBS-related logs from bot.log"""
    try:
        log_path = os.path.join("logs", "default", "bot.log")
        if not os.path.exists(log_path):
            return jsonify({"logs": [], "message": "Log file not found"}), 404

        # Read last 1000 lines and filter for RIBS
        with open(log_path, "r") as f:
            lines = f.readlines()[-1000:]  # Last 1000 lines

        ribs_logs = [
            line.strip() for line in lines if "ribs" in line.lower() or "RIBS" in line
        ]

        return jsonify({"logs": ribs_logs[-50:]})  # Last 50 RIBS logs
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)}), 500
