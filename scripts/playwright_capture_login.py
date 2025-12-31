#!/usr/bin/env python3
"""Headless Playwright capture for login -> dashboard flow.

Attempts to ensure a predictable testuser via `/_ensure_testadmin` when
dev helpers are available, then performs a form login and records the
final URL and cookies to `playwright_capture.json`.

Exits 0 on success (session cookie + dashboard access), non-zero on
failure to make it CI-friendly.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("CAPTURE_BASE_URL", "http://127.0.0.1:5001")
OUT = Path(os.getenv("PLAYWRIGHT_CAPTURE_OUT", "playwright_capture.json"))


def try_ensure_testadmin(page):
    token = os.getenv("DEV_HELPER_TOKEN")
    headers = {}
    if token:
        headers["X-DEV-TOKEN"] = token
    try:
        r = page.request.post(f"{BASE.rstrip('/')}/_ensure_testadmin", headers=headers)
        try:
            return r.status, r.json()
        except Exception:
            return r.status, r.text()
    except Exception:
        return None, None


def main():
    out: dict = {"base": BASE, "final_url": None, "cookies": [], "ensure_testadmin": None, "error": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Attempt to create/reset test user if helpers are available
        status, info = try_ensure_testadmin(page)
        out["ensure_testadmin"] = {"status": status, "info": info}

        # Navigate to login
        page.goto(f"{BASE.rstrip('/')}/login", wait_until="networkidle")

        # Fill and submit login form (expects a form with username/password)
        try:
            page.fill("#login-username", os.getenv("CAPTURE_USERNAME", "testadmin"))
            page.fill("#login-password", os.getenv("CAPTURE_PASSWORD", "testpass123"))
            page.click("#login-btn")
        except Exception:
            # Try generic form submission if selectors differ
            try:
                page.locator("form").first.evaluate("f => f.submit()")
            except Exception as exc:
                out["error"] = f"could not submit login form: {exc}"
                browser.close()
                OUT.write_text(json.dumps(out, indent=2))
                sys.exit(2)

        try:
            page.wait_for_url("**/dashboard", timeout=8000)
        except Exception:
            # Not redirected; still check if cookie present
            pass

        out["final_url"] = page.url
        for c in context.cookies():
            out["cookies"].append({"name": c.get("name"), "value": c.get("value"), "domain": c.get("domain")})

        OUT.write_text(json.dumps(out, indent=2))

        # Heuristic success: session cookie and dashboard
        has_session = any(c.get("name") == "session" for c in out["cookies"])
        is_dashboard = "/dashboard" in (out["final_url"] or "")

        browser.close()

        if has_session and is_dashboard:
            print("OK: Playwright captured session and dashboard")
            sys.exit(0)
        else:
            print("FAIL: Playwright capture missing session or dashboard; wrote:", OUT)
            sys.exit(1)


if __name__ == "__main__":
    main()
