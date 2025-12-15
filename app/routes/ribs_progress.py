"""Lightweight RIBS progress endpoint (separate blueprint to avoid touching status.py)
"""
from flask import Blueprint, jsonify
import os
import json

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

        progress = {
            "running": status.get("running", False),
            "current_iteration": status.get("current_iteration"),
            "progress_percent": status.get("progress_percent"),
            "archive_stats": status.get("archive_stats", {}),
            "latest_checkpoint": status.get("latest_checkpoint"),
        }
        return jsonify(progress)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
