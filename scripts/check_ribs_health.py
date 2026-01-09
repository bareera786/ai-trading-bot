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
from datetime import datetime

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
        # Some tests stub requests without raise_for_status.
        raise_for_status = getattr(resp, "raise_for_status", None)
        if callable(raise_for_status):
            raise_for_status()
    except Exception as exc:
        print("Failed to POST alert to webhook:", exc)


def _parse_last_completed(value: object) -> float | None:
    """Parse an ISO-ish timestamp into epoch seconds."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip()
        if not text:
            return None
        # Handle 'Z' suffix.
        if text.endswith("Z"):
            text = text[:-1]
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return None


def check_status(path: str, max_age_seconds: int = 6 * 3600) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"Status file missing: {path}"

    try:
        with open(path, "r") as fh:
            status = json.load(fh) or {}
    except Exception as exc:
        return False, f"Failed to read status file: {exc}"

    now = time.time()

    # Prefer explicit checkpoint timestamp.
    latest = status.get("latest_checkpoint") or {}
    mtime_ck = latest.get("mtime")
    if mtime_ck is not None:
        try:
            age_ck = int(now - float(mtime_ck))
            if age_ck > max_age_seconds:
                return (
                    False,
                    f"RIBS checkpoint stale: age={age_ck}s > threshold={max_age_seconds}s",
                )
        except Exception:
            # Fall through to other signals.
            pass

    # Fallback: last_completed ISO timestamp.
    last_completed = _parse_last_completed(status.get("last_completed"))
    if last_completed is not None:
        age_lc = int(now - float(last_completed))
        if age_lc > max_age_seconds:
            return (
                False,
                f"RIBS checkpoint stale: age={age_lc}s > threshold={max_age_seconds}s",
            )

    # Final fallback: status file mtime.
    try:
        mtime = os.path.getmtime(path)
        age = int(now - mtime)
        if age > max_age_seconds:
            return (
                False,
                f"RIBS checkpoint stale: age={age}s > threshold={max_age_seconds}s",
            )
    except Exception:
        pass

    return True, "OK"


def main(max_age_seconds: int | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--status-path", default=DEFAULT_STATUS)
    # Backward-compatible positional max age (tests call: check_ribs_health.py 1)
    p.add_argument("max_age_seconds", nargs="?", type=int, default=None)
    p.add_argument("--max-age-seconds", dest="max_age_seconds_flag", type=int, default=None)
    p.add_argument("--webhook", default=os.getenv("RIBS_ALERT_WEBHOOK", ""))
    p.add_argument("--verbose", action="store_true")

    if max_age_seconds is None:
        args = p.parse_args()
        max_age_seconds = (
            args.max_age_seconds_flag
            if args.max_age_seconds_flag is not None
            else (args.max_age_seconds if args.max_age_seconds is not None else 6 * 3600)
        )
    else:
        args = p.parse_args([])

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    ok, msg = check_status(args.status_path, int(max_age_seconds))
    if ok:
        print("RIBS health check OK:", msg)
        return 0

    # alert and return critical
    payload = {"text": msg, "path": args.status_path}
    send_alert(args.webhook, payload)
    print("RIBS health check failed:", msg)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
