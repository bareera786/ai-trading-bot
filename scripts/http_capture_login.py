#!/usr/bin/env python3
"""Simple non-browser capture to validate login/session behavior.

This script uses requests to call dev helpers and perform a form login
with `testadmin` and verifies a session cookie + redirect to /dashboard.
Outputs JSON to `scripts/http_capture_output.json`.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import requests

BASE = os.getenv("CAPTURE_BASE_URL", "http://127.0.0.1:5001")
OUTPATH = os.path.join(os.path.dirname(__file__), "http_capture_output.json")

DEFAULT_USER = os.getenv("CAPTURE_USERNAME", "testadmin")
DEFAULT_PASS = os.getenv("CAPTURE_PASSWORD", "testpass123")

session = requests.Session()
requests_log: list[dict[str, Any]] = []


def safe_get(path: str):
    url = BASE.rstrip("/") + path
    r = session.get(url, allow_redirects=False)
    requests_log.append({"url": url, "method": "GET", "status_code": r.status_code})
    return r


def safe_post(path: str, data=None, headers=None):
    url = BASE.rstrip("/") + path
    r = session.post(url, data=data, headers=headers or {}, allow_redirects=False)
    requests_log.append({"url": url, "method": "POST", "status_code": r.status_code})
    return r


def extract_csrf(html: str) -> str | None:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def main():
    out: dict[str, Any] = {"base": BASE, "requests": [], "cookies": [], "whoami": None, "ensure_testadmin": None}

    try:
        r = safe_get("/_whoami")
        try:
            out["whoami"] = r.json()
        except Exception:
            out["whoami"] = {"status": r.status_code, "text": r.text}

        r = safe_post("/_ensure_testadmin")
        try:
            out["ensure_testadmin"] = r.json()
        except Exception:
            out["ensure_testadmin"] = {"status": r.status_code, "text": r.text}

        # Get login form and csrf
        r = safe_get("/login")
        html = r.text
        csrf = extract_csrf(html)
        out["login_csrf"] = bool(csrf)

        # Post login form
        data = {"username": DEFAULT_USER, "password": DEFAULT_PASS}
        if csrf:
            data["csrf_token"] = csrf
        r = safe_post("/login", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        out["post_login_response"] = {"status": r.status_code, "headers": dict(r.headers)}

        # If redirect to dashboard, follow
        if r.status_code in (302, 303) and r.headers.get("Location"):
            loc = r.headers.get("Location")
            out["post_login_response"]["location"] = loc
            r2 = safe_get(loc)
            out["final_url"] = r2.url
            out["final_status"] = r2.status_code
        else:
            out["final_url"] = r.url
            out["final_status"] = r.status_code

        # cookies
        for c in session.cookies:
            out["cookies"].append({"name": c.name, "value": c.value, "domain": c.domain, "path": c.path})

        out["requests"] = requests_log

        with open(OUTPATH, "w") as fh:
            json.dump(out, fh, indent=2)

        # Success heuristics
        has_session = any(c.get("name") == "session" for c in out["cookies"])
        redirected_to_dashboard = "/dashboard" in (out.get("post_login_response", {}).get("headers", {}).get("Location", "") or "")

        if has_session and (redirected_to_dashboard or out.get("final_status") == 200):
            print("OK: login produced session cookie and dashboard access")
            print("Wrote:", OUTPATH)
            sys.exit(0)
        else:
            print("FAIL: login did not yield expected session/redirect. See", OUTPATH)
            sys.exit(2)

    except Exception as exc:
        print("ERROR:", exc)
        sys.exit(3)


if __name__ == "__main__":
    main()
