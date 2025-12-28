#!/usr/bin/env python3
"""Health check for RIBS optimizer.

Checks `bot_persistence/ribs_checkpoints/ribs_status.json` and latest checkpoint
freshness. On failure it optionally POSTs to a webhook defined by environment
variable `RIBS_ALERT_WEBHOOK`.

Exit codes:
 0 - OK
 1 - minor issue (e.g., status missing)
 2 - critical (stale / failed)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

try:
    import requests
except Exception:  # pragma: no cover - requests should be present in env
    requests = None

DEFAULT_STATUS = "bot_persistence/ribs_checkpoints/ribs_status.json"


def send_alert(webhook: str, payload: dict) -> None:
    if not webhook:
        print("ALERT: ", payload)
        return
    if requests is None:
        print("ALERT (no requests):", payload)
        return
    try:
        resp = requests.post(webhook, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as exc:
        print("Failed to POST alert to webhook:", exc)


def check_status(path: str, max_age_seconds: int = 6 * 3600) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"Status file missing: {path}"

    try:
        with open(path, "r") as fh:
            status = json.load(fh) or {}
    except Exception as exc:
        return False, f"Failed to read status file: {exc}"

    # Inspect file modification age
    try:
        mtime = os.path.getmtime(path)
        age = int(time.time() - mtime)
    except Exception:
        age = None

    if age is not None and age > max_age_seconds:
        return False, f"Status file stale: age={age}s > threshold={max_age_seconds}s"

    # Check latest checkpoint metadata if present
    latest = status.get("latest_checkpoint") or {}
    mtime_ck = latest.get("mtime")
    try:
        if mtime_ck is not None:
            age_ck = int(time.time() - float(mtime_ck))
            if age_ck > max_age_seconds:
                return (
                    False,
                    f"Latest checkpoint stale: age={age_ck}s > threshold={max_age_seconds}s",
                )
    except Exception:
        pass

    return True, "OK"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--status-path", default=DEFAULT_STATUS)
    p.add_argument("--max-age-seconds", type=int, default=6 * 3600)
    p.add_argument("--webhook", default=os.getenv("RIBS_ALERT_WEBHOOK", ""))
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    ok, msg = check_status(args.status_path, args.max_age_seconds)
    if ok:
        print("RIBS health check OK:", msg)
        return 0

    # alert and return critical
    payload = {"status": "ribs_unhealthy", "message": msg, "path": args.status_path}
    send_alert(args.webhook, payload)
    print("RIBS health check failed:", msg)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
