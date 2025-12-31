import json
import os
import subprocess
import sys
import time

import pytest


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


def test_responsive_check_login_overflow(tmp_path):
    proc = start_dev_server()
    try:
        assert wait_for("http://127.0.0.1:5001/login", timeout=10), "Dev server did not start"

        env = os.environ.copy()
        env["CAPTURE_BASE_URL"] = "http://127.0.0.1:5001"
        env["RESPONSIVE_CHECK_OUT"] = str(tmp_path / "responsive_check.json")

        out = subprocess.run([sys.executable, "scripts/playwright_responsive_check.py"], env=env, capture_output=True, text=True)
        artifact = tmp_path / "responsive_check_out.txt"
        artifact.write_text(out.stdout + "\n" + out.stderr)

        assert out.returncode in (0, 1), f"Script failed to run: {out.returncode}\n{artifact}"

        data = json.load(open(env["RESPONSIVE_CHECK_OUT"]))
        # If the /login page was inspected, assert no overflow
        login = data["pages"].get("/login")
        assert login is not None, "/login missing from report"
        # If it was inspected (not skipped) it should not have doc_overflow
        if not login.get("skipped"):
            assert not login.get("doc_overflow", False), "Login page still has horizontal overflow"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


def test_login_template_inline_styles():
    tpl = open('app/templates/auth/login.html').read()
    # Regression assertion: ensure inline large padding removed and box-sizing set
    assert 'padding:3rem 2.2rem' not in tpl
    assert 'box-sizing' in tpl
