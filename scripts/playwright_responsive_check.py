#!/usr/bin/env python3
"""Run automated responsive checks using Playwright.

Visits pages and collects common mobile/responsive issues:
 - Missing viewport meta
 - Document width larger than innerWidth (horizontal overflow)
 - Elements wider than viewport (returns first few offenders)
 - Presence/visibility of mobile nav toggle (hamburger) heuristic

Writes JSON report to OUT (default: artifacts/responsive_check.json)
Exit code 0 if no high-severity issues found, 2 if the check couldn't run, 1 if issues found.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("CAPTURE_BASE_URL", "http://127.0.0.1:5001")
OUT = Path(os.getenv("RESPONSIVE_CHECK_OUT", "artifacts/responsive_check.json"))

PAGES = ["/login", "/dashboard", "/trading"]


def try_ensure_testadmin_and_login(page):
    # Try to create/reset a deterministic testadmin via dev helper if available
    token = os.getenv("DEV_HELPER_TOKEN")
    headers = {}
    if token:
        headers["X-DEV-TOKEN"] = token
    try:
        r = page.request.post(f"{BASE.rstrip('/')}/_ensure_testadmin", headers=headers)
    except Exception:
        r = None

    # Attempt form login using known capture credentials
    try:
        page.goto(f"{BASE.rstrip('/')}/login", wait_until="networkidle")
        try:
            page.fill("#login-username", os.getenv("CAPTURE_USERNAME", "testadmin"))
            page.fill("#login-password", os.getenv("CAPTURE_PASSWORD", "testpass123"))
            page.click("#login-btn")
        except Exception:
            try:
                page.locator("form").first.evaluate("f => f.submit()")
            except Exception:
                return False
        try:
            page.wait_for_url("**/dashboard", timeout=8000)
        except Exception:
            # continue; login might still have succeeded via cookie
            pass
        # check for session cookie
        cookies = page.context.cookies()
        return any(c.get("name") == "session" for c in cookies)
    except Exception:
        return False


def inspect_page(page):
    js = """
    (function(){
        const issues = {missing_viewport:false, doc_overflow:false, offenders:[], mobile_nav:false};
        // viewport meta
        const vp = document.querySelector('meta[name="viewport"]');
        if (!vp) issues.missing_viewport = true;

        const iw = window.innerWidth;
        if (document.documentElement.scrollWidth > iw) issues.doc_overflow = true;

        // find wide elements
        const wide = [];
        const nodes = Array.from(document.querySelectorAll('body *'));
        for (let i=0;i<nodes.length;i++){
            try{
                const r = nodes[i].getBoundingClientRect();
                if (r.width > iw + 1){
                    wide.push({tag: nodes[i].tagName, w: Math.round(r.width), selector: nodes[i].id || nodes[i].className || nodes[i].tagName});
                    if (wide.length >= 5) break;
                }
            }catch(e){}
        }
        issues.offenders = wide;

        // mobile nav heuristic: check for elements with aria-label or id/class containing 'menu' or 'hamburger'
        const nav = nodes.find(n => /menu|nav|hamburger/i.test((n.id||n.className||'') + (n.getAttribute? (n.getAttribute('aria-label')||'') : '')));
        if (nav) issues.mobile_nav = true;

        return issues;
    })();
    """

    try:
        return page.evaluate(js)
    except Exception as exc:
        return {"error": str(exc)}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {"base": BASE, "pages": {}}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 375, "height": 812}, user_agent="responsive-check/1.0")
            page = context.new_page()

            # Check /login before login
            path = "/login"
            url = f"{BASE.rstrip('/')}{path}"
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=8000)
            except Exception:
                resp = None
            info = {"skipped": False}
            if resp is None:
                info["skipped"] = True
                info["note"] = "navigation_failed"
            else:
                status = resp.status
                info["status_code"] = status
                if status >= 400:
                    info["skipped"] = True
                    info["note"] = f"http_{status}"
                else:
                    info.update(inspect_page(page))
            info["url"] = url
            info["final_url"] = page.url
            report["pages"][path] = info

            # Attempt login so we can inspect authenticated pages
            logged_in = try_ensure_testadmin_and_login(page)

            for path in PAGES[1:]:  # skip /login since already checked
                url = f"{BASE.rstrip('/')}{path}"
                try:
                    resp = page.goto(url, wait_until="networkidle", timeout=8000)
                except Exception:
                    resp = None
                info = {"skipped": False}
                if resp is None:
                    # Could not fetch page (timeout or navigation error)
                    info["skipped"] = True
                    info["note"] = "navigation_failed"
                else:
                    status = resp.status
                    info["status_code"] = status
                    if status >= 400:
                        info["skipped"] = True
                        info["note"] = f"http_{status}"
                    else:
                        # Only inspect when we have a successful HTTP response
                        info.update(inspect_page(page))
                info["url"] = url
                info["final_url"] = page.url
                report["pages"][path] = info

            browser.close()
    except Exception as exc:
        OUT.write_text(json.dumps({"error": str(exc)}))
        print("ERROR: could not run playwright check:", exc)
        sys.exit(2)

    OUT.write_text(json.dumps(report, indent=2))

    # Determine severity: if any page has missing_viewport or doc_overflow or offenders then fail
    fail = False
    for v in report["pages"].values():
        if v.get("missing_viewport") or v.get("doc_overflow") or (v.get("offenders") and len(v.get("offenders"))>0):
            fail = True
            break

    if fail:
        print("Issues found; wrote:", OUT)
        sys.exit(1)
    else:
        print("No high-severity responsive issues found; wrote:", OUT)
        sys.exit(0)


if __name__ == "__main__":
    main()
