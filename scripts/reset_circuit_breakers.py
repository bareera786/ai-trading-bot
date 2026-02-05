#!/usr/bin/env python3
"""Reset all circuit breakers to allow trading."""
import redis
import json
import os

# Connect to Redis
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', '6379'))
r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

print("🔄 Resetting all circuit breakers...")

# Clear any circuit breaker data in Redis
keys_to_clear = [
    "circuit_breaker:*",
    "safety:circuit_breakers",
    "safety:symbol_loss_streak"
]

for pattern in keys_to_clear:
    keys = r.keys(pattern)
    if keys:
        r.delete(*keys)
        print(f"✅ Cleared {len(keys)} keys matching '{pattern}'")

# Reset trading settings to ensure no blocks
settings = r.get("trading:settings")
if settings:
    config = json.loads(settings)
    config["circuit_breaker_active"] = False
    r.set("trading:settings", json.dumps(config))
    print("✅ Reset circuit breaker flag in trading:settings")

print("\n✅ All circuit breakers reset successfully!")
print("🚀 Bot is ready for aggressive trading with optimized thresholds")
