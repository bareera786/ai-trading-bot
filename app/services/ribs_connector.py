#!/usr/bin/env python3
"""
RIBS Connector Service
Handles communication with the RIBS optimization service
"""

import os
import redis
import requests
import json
from flask import Flask, request, jsonify
import logging
from datetime import datetime
import time
from typing import Optional, cast, List
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis configuration
ribs_base_url = os.getenv("RIBS_BASE_URL", "http://151.243.171.80:5000")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
# Parse Redis URL for explicit client creation
from urllib.parse import urlparse

parsed = urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed.hostname or "localhost", port=parsed.port or 6379, decode_responses=True
)


class RIBSConnector:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # Note: timeout is set per request, not on session

    def optimize_portfolio(self, user_id, portfolio_data):
        """Optimize portfolio using RIBS service"""
        try:
            url = f"{self.base_url}/optimize"
            payload = {
                "user_id": user_id,
                "portfolio": portfolio_data,
                "timestamp": datetime.utcnow().isoformat(),
            }

            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()

            # Cache the result
            cache_key = f"ribs:{user_id}:{hash(str(portfolio_data))}"
            redis_client.setex(cache_key, 3600, json.dumps(result))  # Cache for 1 hour

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"RIBS request failed: {e}")
            # Try to get cached result
            cache_key = f"ribs:{user_id}:{hash(str(portfolio_data))}"
            cached_result = cast(Optional[str], redis_client.get(cache_key))
            if cached_result:
                logger.info("Using cached RIBS result")
                return json.loads(cached_result)
            raise


# Initialize connector
connector = RIBSConnector(ribs_base_url)


@app.route("/optimize", methods=["POST"])
def optimize():
    """Optimize portfolio endpoint"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        portfolio = data.get("portfolio")

        if not user_id or not portfolio:
            return jsonify({"error": "Missing user_id or portfolio"}), 400

        result = connector.optimize_portfolio(user_id, portfolio)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        return jsonify({"status": "healthy", "service": "ribs-connector"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Get cache stats (use SCAN to avoid blocking Redis)
        cache_count = sum(1 for _ in redis_client.scan_iter(match="ribs:*"))

        metrics_output = f"""# HELP ribs_connector_cache_entries Number of cached RIBS responses
# TYPE ribs_connector_cache_entries gauge
ribs_connector_cache_entries {cache_count}
"""

        return metrics_output, 200, {"Content-Type": "text/plain"}

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return "Error generating metrics", 500


# Background task to clean up expired cache entries
def cleanup_cache():
    """Periodically clean up old cache entries"""
    while True:
        try:
            # Remove expired keys (Redis handles expiration automatically)
            # But we can log cache statistics
            cache_count = sum(1 for _ in redis_client.scan_iter(match="ribs:*"))
            logger.info(f"Cache contains {cache_count} RIBS entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

        time.sleep(300)  # Run every 5 minutes


if __name__ == "__main__":
    # Start cache cleanup in background
    import threading

    cleanup_thread = threading.Thread(target=cleanup_cache, daemon=True)
    cleanup_thread.start()

    port = int(os.getenv("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
