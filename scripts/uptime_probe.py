#!/usr/bin/env python3
"""Simple uptime probe for marketing + subscription endpoints."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Callable

import requests


@dataclass
class ProbeResult:
    name: str
    url: str
    ok: bool
    detail: str


def check_text(url: str) -> ProbeResult:
    response = requests.get(url, timeout=8)
    ok = response.status_code == 200 and 'Request White-Glove' in response.text
    detail = f"status={response.status_code}"
    return ProbeResult('Marketing Landing', url, ok, detail)


def check_root(url: str) -> ProbeResult:
    response = requests.get(url, timeout=8, allow_redirects=False)
    location = response.headers.get('Location', '')
    ok = response.status_code in (301, 302) and '/marketing' in location
    detail = f"status={response.status_code} location={location}"
    return ProbeResult('Root Redirect', url, ok, detail)


def check_subscriptions(url: str) -> ProbeResult:
    response = requests.get(url, timeout=8)
    ok = response.status_code == 200 and 'featured_plan' in response.json()
    detail = f"status={response.status_code}"
    return ProbeResult('Subscription API', url, ok, detail)


def run_probes(base_url: str) -> list[ProbeResult]:
    base = base_url.rstrip('/')
    checks: list[tuple[str, Callable[[str], ProbeResult]]] = [
        (f"{base}/marketing", check_text),
        (f"{base}/", check_root),
        (f"{base}/api/subscriptions/plans", check_subscriptions),
    ]
    results = []
    for url, checker in checks:
        try:
            results.append(checker(url))
        except Exception as exc:  # pragma: no cover - network failure path
            results.append(ProbeResult(checker.__name__, url, False, str(exc)))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='AI Bot marketing uptime probe')
    parser.add_argument('--base-url', default='http://localhost:5000', help='Target base URL (default: %(default)s)')
    args = parser.parse_args()

    results = run_probes(args.base_url)
    failed = [result for result in results if not result.ok]

    for result in results:
        status = 'PASS' if result.ok else 'FAIL'
        print(f"[{status}] {result.name} -> {result.url} ({result.detail})")

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
