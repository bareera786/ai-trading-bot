#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    c = b.new_context(viewport={"width": 375, "height": 812})
    page = c.new_page()
    page.goto(f"{BASE}/login")
    info = page.evaluate("""
    () => {
      const el = document.querySelector('.login-container');
      if (!el) return {error: 'no element'};
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return {
        width: Math.round(r.width),
        offsetWidth: el.offsetWidth,
        clientWidth: el.clientWidth,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
        boxSizing: cs.boxSizing
      };
    }
    """)
    print(info)
    b.close()
