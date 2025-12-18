"""Lightweight RIBS progress endpoint (separate blueprint to avoid touching status.py)
"""
from flask import Blueprint, jsonify
import os
import json
import time
import subprocess

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

        progress = {
            "running": status.get("running", False),
            "current_iteration": status.get("current_iteration"),
            "progress_percent": status.get("progress_percent"),
            "archive_stats": status.get("archive_stats", {}),
            "latest_checkpoint": latest_ck,
            "latest_checkpoint_age_seconds": ck_age,
            # Simple health: consider healthy if checkpoint age <= 3600s
            "healthy": (ck_age is not None and ck_age <= 3600),
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

        # Get last 100 lines and filter for RIBS
        result = subprocess.run(
            ["tail", "-100", log_path], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return jsonify({"logs": [], "error": "Failed to read logs"}), 500

        lines = result.stdout.splitlines()
        ribs_logs = [line for line in lines if "ribs" in line.lower() or "RIBS" in line]

        return jsonify({"logs": ribs_logs[-50:]})  # Last 50 RIBS logs
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)}), 500
