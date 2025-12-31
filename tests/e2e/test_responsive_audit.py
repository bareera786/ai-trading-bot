import json
import os
import subprocess
import sys
import time

import pytest


pytest.importorskip("playwright")


def start_dev_server():
    proc = subprocess.Popen([sys.executable, "scripts/run_wsgi_port5001.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def wait_for(url, timeout=8.0):
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def test_responsive_audit_produces_screenshots(tmp_path):
    if os.getenv("SKIP_PLAYWRIGHT_E2E", "0") == "1":
        pytest.skip("Playwright E2E disabled via SKIP_PLAYWRIGHT_E2E")

    proc = start_dev_server()
    try:
        assert wait_for("http://127.0.0.1:5001/login", timeout=10), "Dev server did not start in time"

        env = os.environ.copy()
        env["CAPTURE_BASE_URL"] = "http://127.0.0.1:5001"
        env["RESPONSIVE_AUDIT_OUT"] = str(tmp_path / "responsive_audit")

        out = subprocess.run([sys.executable, "scripts/playwright_responsive_audit.py"], env=env, capture_output=True, text=True)

        artifact = tmp_path / "responsive_audit_out.txt"
        artifact.write_text(out.stdout + "\n" + out.stderr)

        assert out.returncode == 0, f"Responsive audit script failed: {out.returncode}\n{artifact}"

        meta_file = tmp_path / "responsive_audit" / "responsive_audit.json"
        assert meta_file.exists(), "responsive_audit.json not produced"
        data = json.load(open(meta_file))
        # Ensure at least dashboard mobile screenshot produced
        dash_mobile = tmp_path / "responsive_audit" / "dashboard-mobile.png"
        dash_desktop = tmp_path / "responsive_audit" / "dashboard-desktop.png"
        assert dash_mobile.exists() or dash_desktop.exists(), "Dashboard screenshots not produced"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
