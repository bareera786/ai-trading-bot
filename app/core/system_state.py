import json
import time
from datetime import datetime, timezone
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SystemStateManager:
    """
    SINGLE SOURCE OF TRUTH for the AI Bot System State.
    
    Rules:
    1. State is ephemeral (Redis backed with TTL).
    2. If the Heartbeat stops, the System is OFFLINE.
    3. No hardcoded statuses allowed in API responses.
    """
    
    REDIS_KEY_STATE = "brain:system_state"
    REDIS_KEY_HEARTBEAT = "brain:heartbeat"
    TTL_SECONDS = 30  # System is dead if no heartbeat for 30s
    
    @staticmethod
    def _get_redis():
        # Lazy import to ensure we get the initialized client
        from app.extensions import redis_client
        return redis_client
    
    @staticmethod
    def heartbeat(component: str = "core_loop", meta: Dict = None):
        """
        Call this every loop cycle to prove the system is alive.
        """
        redis_client = SystemStateManager._get_redis()
        if not redis_client:
            logger.warning("Redis not available for heartbeat")
            return
            
        try:
            now = datetime.now(timezone.utc)
            timestamp = now.timestamp()
            
            # 1. Update simple timestamp
            redis_client.set(SystemStateManager.REDIS_KEY_HEARTBEAT, str(timestamp), ex=SystemStateManager.TTL_SECONDS)
            
            # 2. Update rich state
            state = {
                "status": "ONLINE",
                "timestamp": now.isoformat(),
                "last_component": component,
                "meta": meta or {}
            }
            redis_client.set(
                SystemStateManager.REDIS_KEY_STATE, 
                json.dumps(state), 
                ex=SystemStateManager.TTL_SECONDS
            )
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    @staticmethod
    def get_status() -> Dict:
        """
        Retrieve strict system status. 
        If Redis key is missing (TTL expired), returns OFFLINE.
        """
        offline_response = {
            "status": "OFFLINE",
            "trading_enabled": False,
            "message": "System heartbeat expired. Process may be down."
        }

        redis_client = SystemStateManager._get_redis()
        if not redis_client:
            return {**offline_response, "message": "Redis connection failed"}

        try:
            raw_state = redis_client.get(SystemStateManager.REDIS_KEY_STATE)
            if not raw_state:
                return offline_response
                
            state = json.loads(raw_state)
            
            # Double check freshness (redundant with TTL but safe)
            last_ts = datetime.fromisoformat(state["timestamp"])
            age = (datetime.now(timezone.utc) - last_ts).total_seconds()
            
            if age > SystemStateManager.TTL_SECONDS:
                return offline_response
                
            return {
                "status": "ONLINE",
                "trading_enabled": True, # TODO: Link to real config
                "last_seen": state["timestamp"],
                "component": state.get("last_component"),
                "meta": state.get("meta")
            }
            
        except Exception as e:
            logger.error(f"Error reading system state: {e}")
            return offline_response
