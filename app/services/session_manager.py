#!/usr/bin/env python3
"""
Session Manager Service
Handles user sessions and authentication for multi-tenant deployment
"""

import os
import redis
import json
from flask import Flask, request, jsonify
from flask_session import Session
import logging
from datetime import datetime
from typing import Optional, cast, List
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis configuration
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
# Parse Redis URL for explicit client creation
from urllib.parse import urlparse

parsed = urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed.hostname or "localhost", port=parsed.port or 6379, decode_responses=True
)

# Session configuration
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis_client
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_USE_SIGNER"] = True
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)

Session(app)


@app.route("/session/create", methods=["POST"])
def create_session():
    """Create a new session"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        tenant = data.get("tenant", "default")
        session_data = data.get("session_data", {})

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # Create session key
        session_key = f"session:{tenant}:{user_id}"
        session_value = {
            "user_id": user_id,
            "tenant": tenant,
            "created_at": datetime.utcnow().isoformat(),
            "data": session_data,
        }

        # Store in Redis with expiration (24 hours)
        redis_client.setex(session_key, 86400, json.dumps(session_value))

        return jsonify({"session_key": session_key, "status": "created"})

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/session/<session_key>", methods=["GET"])
def get_session(session_key):
    """Get session data"""
    try:
        session_data = cast(Optional[str], redis_client.get(session_key))
        if session_data:
            return jsonify(json.loads(session_data))
        else:
            return jsonify({"error": "Session not found"}), 404

    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/session/<session_key>", methods=["DELETE"])
def delete_session(session_key):
    """Delete a session"""
    try:
        result = redis_client.delete(session_key)
        if result:
            return jsonify({"status": "deleted"})
        else:
            return jsonify({"error": "Session not found"}), 404

    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/tenant/<tenant>", methods=["GET"])
def get_tenant_sessions(tenant):
    """Get all active sessions for a tenant"""
    try:
        # Get all session keys for the tenant (use SCAN to avoid blocking Redis)
        pattern = f"session:{tenant}:*"
        keys = list(cast(List[str], redis_client.scan_iter(match=pattern)))

        sessions = []
        for key in keys:
            session_data = cast(Optional[str], redis_client.get(key))
            if session_data is not None:
                sessions.append(json.loads(session_data))

        return jsonify({"sessions": sessions, "count": len(sessions)})

    except Exception as e:
        logger.error(f"Failed to get tenant sessions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        return jsonify({"status": "healthy", "service": "session-manager"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Get session counts (use SCAN to avoid blocking Redis)
        total_sessions = sum(1 for _ in redis_client.scan_iter(match="session:*"))

        metrics_output = f"""# HELP session_manager_active_sessions Total number of active sessions
# TYPE session_manager_active_sessions gauge
session_manager_active_sessions {total_sessions}
"""

        return metrics_output, 200, {"Content-Type": "text/plain"}

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return "Error generating metrics", 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=False)
