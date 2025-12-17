#!/usr/bin/env python3
"""Check ribs_status.json and optionally POST to webhook when stale."""
import json
import os
import time
import requests


def main(max_age_seconds: int = 6 * 3600):
    status_path = os.path.join(
        "bot_persistence", "ribs_checkpoints", "ribs_status.json"
    )
    if not os.path.exists(status_path):
        print("RIBS status file missing")
        return 2

    with open(status_path, "r") as sf:
        status = json.load(sf)

    # Prefer explicit latest_checkpoint info, but fall back to last_completed
    latest = status.get("latest_checkpoint") or {}
    mtime = latest.get("mtime")

    if mtime is None:
        # Fall back to using last_completed ISO timestamp if available
        last_completed = status.get("last_completed")
        if last_completed:
            try:
                # Parse ISO timestamp and compute seconds since completion
                # Use datetime parsing without introducing new deps
                from datetime import datetime

                comp_ts = datetime.fromisoformat(last_completed)
                mtime = comp_ts.timestamp()
            except Exception:
                print("No checkpoint info in status file")
                return 1
        else:
            print("No checkpoint info in status file")
            return 1

    age = int(time.time() - float(mtime))
    print(f"Latest checkpoint age: {age} seconds")
    if age > max_age_seconds:
        webhook = os.getenv("RIBS_ALERT_WEBHOOK")
        msg = f"RIBS checkpoint stale ({age}s)"
        if webhook:
            try:
                requests.post(webhook, json={"text": msg}, timeout=5)
                print("Alert sent")
            except Exception as e:
                print("Failed to send alert:", e)
        return 3

    return 0


if __name__ == "__main__":
    import sys

    exit_code = main(int(sys.argv[1]) if len(sys.argv) > 1 else 6 * 3600)
    raise SystemExit(exit_code)
