"""Helpers to persist and load admin overrides for RIBS deploy gating."""
from __future__ import annotations

import json
import os
from typing import Dict, Any

OVERRIDES_PATH = os.path.join("bot_persistence", "ribs_deploy_overrides.json")


def load_overrides() -> Dict[str, Any]:
    if not os.path.exists(OVERRIDES_PATH):
        return {}
    try:
        with open(OVERRIDES_PATH, "r") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def save_overrides(overrides: Dict[str, Any]) -> bool:
    os.makedirs(os.path.dirname(OVERRIDES_PATH), exist_ok=True)
    try:
        with open(OVERRIDES_PATH + ".tmp", "w") as fh:
            json.dump(overrides, fh, indent=2)
            fh.flush()
        os.replace(OVERRIDES_PATH + ".tmp", OVERRIDES_PATH)
        return True
    except Exception:
        return False
