import json
import os
import subprocess
import sys
import time

import pytest


pytest.importorskip("playwright")


def start_dev_server():
    # Start the local WSGI server on 5001 using the repo's script
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


def test_playwright_capture_runs_and_produces_session(tmp_path):
    # Skip in CI if explicitly disabled
    if os.getenv("SKIP_PLAYWRIGHT_E2E", "0") == "1":
        pytest.skip("Playwright E2E disabled via SKIP_PLAYWRIGHT_E2E")

    proc = start_dev_server()
    try:
        assert wait_for("http://127.0.0.1:5001/login", timeout=10), "Dev server did not start in time"

        env = os.environ.copy()
        env["CAPTURE_BASE_URL"] = "http://127.0.0.1:5001"
        out = subprocess.run([sys.executable, "scripts/playwright_capture_login.py"], env=env, capture_output=True, text=True)

        # Write outputs for debugging in CI artifacts
        artifact = tmp_path / "playwright_out.txt"
        artifact.write_text(out.stdout + "\n" + out.stderr)

        assert out.returncode == 0, f"Playwright script failed: {out.returncode}\n{artifact}"

        # Validate produced JSON
        capture_json = Path = os.path.join(os.getcwd(), "playwright_capture.json")
        assert os.path.exists(capture_json), "playwright_capture.json not produced"
        data = json.load(open(capture_json))
        assert any(c.get("name") == "session" for c in data.get("cookies", [])), "No session cookie present"
        assert "/dashboard" in (data.get("final_url") or ""), "Login did not reach dashboard"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()