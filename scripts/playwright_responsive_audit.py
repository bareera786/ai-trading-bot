#!/usr/bin/env python3
"""Playwright-based responsive audit.

Logs in using the same approach as the login capture, then visits a set of
key pages and captures screenshots at common viewport sizes (mobile/tablet/desktop).
Saves screenshots under the OUT_DIR and writes metadata to responsive_audit.json.

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("CAPTURE_BASE_URL", "http://127.0.0.1:5001")
OUT_DIR = Path(os.getenv("RESPONSIVE_AUDIT_OUT", "artifacts/responsive_audit"))

VIEWPORTS = {
    "mobile": (375, 812),
    "tablet": (768, 1024),
    "desktop": (1366, 768),
}

PAGES = ["/login", "/dashboard", "/trading"]


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


def slug_for(path: str) -> str:
    return path.strip("/").replace("/", "_") or "root"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict = {"base": BASE, "pages": {}, "ensure_testadmin": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Attempt to create/reset test user if helpers are available
        status, info = try_ensure_testadmin(page)
        meta["ensure_testadmin"] = {"status": status, "info": info}

        # Perform login (re-use form-based approach)
        page.goto(f"{BASE.rstrip('/')}/login", wait_until="networkidle")
        try:
            page.fill("#login-username", os.getenv("CAPTURE_USERNAME", "testadmin"))
            page.fill("#login-password", os.getenv("CAPTURE_PASSWORD", "testpass123"))
            page.click("#login-btn")
        except Exception:
            try:
                page.locator("form").first.evaluate("f => f.submit()")
            except Exception as exc:
                meta["error"] = f"could not submit login form: {exc}"
                browser.close()
                OUT_DIR.joinpath("responsive_audit.json").write_text(json.dumps(meta, indent=2))
                sys.exit(2)

        # Wait a bit for login to complete
        try:
            page.wait_for_timeout(2000)
        except Exception:
            pass

        # Visit each page and capture screenshots for each viewport
        for path in PAGES:
            page_info = {"url": f"{BASE.rstrip('/')}{path}", "screenshots": []}
            for name, (w, h) in VIEWPORTS.items():
                page.set_viewport_size({"width": w, "height": h})
                try:
                    page.goto(page_info["url"])
                except Exception:
                    # Continue to try to capture whatever loads
                    pass
                slug = slug_for(path)
                fname = OUT_DIR.joinpath(f"{slug}-{name}.png")
                try:
                    page.screenshot(path=str(fname), full_page=True)
                    page_info["screenshots"].append(str(fname))
                except Exception as exc:
                    page_info.setdefault("errors", []).append({"viewport": name, "error": str(exc)})

            meta["pages"][path] = page_info

        # Save metadata
        OUT_DIR.joinpath("responsive_audit.json").write_text(json.dumps(meta, indent=2))

        browser.close()

    print("Responsive audit complete; wrote:", OUT_DIR)
    # Heuristic: success if at least one screenshot exists for dashboard
    dash_slug = slug_for("/dashboard")
    mobile = OUT_DIR.joinpath(f"{dash_slug}-mobile.png")
    desktop = OUT_DIR.joinpath(f"{dash_slug}-desktop.png")
    if mobile.exists() or desktop.exists():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
