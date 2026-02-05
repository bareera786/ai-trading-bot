import json
import os
import sys
from pathlib import Path

def inject():
    index = 0
    allocation = 0.10
    risk_tier = "conservative"
    
    status_path = Path("bot_persistence/ribs_checkpoints/ribs_status.json")
    if not status_path.exists():
        print("❌ ribs_status.json not found")
        return False
        
    with open(status_path, "r") as f:
        status = json.load(f)
        
    elites = status.get("elite_strategies", [])
    if not elites or index >= len(elites):
        print(f"❌ Elite index {index} not found")
        return False
        
    elite = elites[index]
    params = elite.get("params", {}).copy()
    
    print(f"Found elite: {elite.get('id')} with objective {elite.get('objective')}")
    
    # Apply user overrides
    params["position_size"] = allocation
    
    if risk_tier == "conservative":
        # Lower risk multiplier if it's high
        params["risk_multiplier"] = min(params.get("risk_multiplier", 1.0), 1.0)
        # Tighter stop loss if it's too wide
        params["stop_loss"] = min(params.get("stop_loss", 2.0), 1.5)
        
    output_path = Path("bot_persistence/active_ribs_strategy.json")
    deploy_config = {
        "id": elite.get("id"),
        "params": params,
        "overrides": {
            "allocation": allocation,
            "risk_tier": risk_tier
        },
        "deployed_at": "2026-02-04T10:16:12"
    }
    
    with open(output_path, "w") as f:
        json.dump(deploy_config, f, indent=4)
        
    print(f"✅ Active RIBS strategy saved to {output_path}")
    return True

if __name__ == "__main__":
    if inject():
        sys.exit(0)
    else:
        sys.exit(1)
