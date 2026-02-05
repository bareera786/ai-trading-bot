"""Signal Publisher Service using Redis Streams."""
from __future__ import annotations

import json
import time
import uuid
import logging
from typing import Optional, Any

from app.extensions import redis_client

logger = logging.getLogger("ai_trading_bot")

class SignalPublisher:
    """Publishes trade signals to a Redis Stream for execution consumers."""

    STREAM_KEY = "trade_signals"
    MAX_STREAM_LEN = 1000  # Keep last 1000 signals

    def __init__(self, redis_conn=None):
        self._redis = redis_conn or redis_client
        if not self._redis:
            logger.warning("SignalPublisher initialized without Redis connection. Signals will be dropped.")

    def publish_signal(
        self,
        symbol: str,
        side: str,
        confidence: float,
        price: float,
        signal_source: str = "brain",
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Publish a trade signal to the Redis stream.
        
        Args:
            symbol: Trading pair (e.g. BTCUSDT)
            side: LONG, SHORT, or FLAT
            confidence: Float 0.0-1.0
            price: Current market price or entry price
            signal_source: Origin of signal (default: brain)
            metadata: Additional context (strategies, user_id context if applicable)
        
        Returns:
            message_id (str) if successful, None otherwise
        """
        if not self._redis:
            logger.error(f"Cannot publish signal for {symbol}: Redis unavailable")
            return None

        # ULTRA-CRITICAL SAFETY CHECK: Global Kill Switch
        try:
            # Check strictly for "1" which means PAUSED
            is_paused_val = self._redis.get("brain:signals:paused")
            is_paused = False
            
            if is_paused_val:
                is_paused = is_paused_val.decode() == "1" if isinstance(is_paused_val, bytes) else is_paused_val == "1"

            # Update Metric
            MetricsService.set_pause_state(is_paused)

            if is_paused:
                 logger.warning(f"🛑 BLOCKED signal for {symbol}: Global Kill Switch (brain:signals:paused) is ACTIVE")
                 return None
                 
        except Exception as e:
            # FAIL SAFE: If we can't check the lock, we DO NOT trade.
            logger.error(f"🛑 BLOCKED signal for {symbol}: Failed to check Global Kill Switch: {e}")
            return None

        signal_id = str(uuid.uuid4())
        timestamp = time.time()
        
        if metadata is None:
            metadata = {}
            
        # SAFETY: Ensure model_version is attached
        if "model_version" not in metadata:
            try:
                # Try to fetch active model from Redis cache
                active_ver = self._redis.get("brain:active_model_version")
                if active_ver:
                    metadata["model_version"] = active_ver.decode() if isinstance(active_ver, bytes) else active_ver
                else:
                    metadata["model_version"] = "unknown_safe_mode"
            except Exception:
                 metadata["model_version"] = "error_fetching"

        payload = {
            "signal_id": signal_id,
            "symbol": symbol.strip().upper(),
            "side": side.upper(),
            "confidence": str(confidence),  # Redis stores strings
            "price": str(price),
            "signal_source": signal_source,
            "timestamp": str(timestamp),
            "metadata": json.dumps(metadata)
        }

        try:
            # XADD trade_signals * key value ...
            message_id = self._redis.xadd(
                self.STREAM_KEY,
                payload,
                maxlen=self.MAX_STREAM_LEN
            )
            # Record Metric
            MetricsService.record_signal_publish()
            logger.info(f"📡 Signal PUBLISHED: {side} {symbol} ({confidence:.2f}) ID:{message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish signal to Redis: {e}")
            return None

# Global Instance
signal_publisher = SignalPublisher()
