import json
import os
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

STATUS_DIR = os.path.join("bot_persistence", "ribs_checkpoints")
STATUS_FILE = os.path.join(STATUS_DIR, "ribs_status.json")


class SimpleWebhookHandler(BaseHTTPRequestHandler):
    received = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            SimpleWebhookHandler.received = json.loads(body)
        except Exception:
            SimpleWebhookHandler.received = body
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return  # silence logs


def _start_server(port):
    httpd = HTTPServer(("127.0.0.1", port), SimpleWebhookHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def _find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr, port = s.getsockname()
    s.close()
    return port


def test_check_ribs_health_posts_to_webhook(tmp_path):
    # prepare status file with stale mtime
    os.makedirs(STATUS_DIR, exist_ok=True)
    status = {
        "latest_checkpoint": {"mtime": 0},
        "iterations": 0,
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)

    port = _find_free_port()
    httpd, thread = _start_server(port)

    env = os.environ.copy()
    env["RIBS_ALERT_WEBHOOK"] = f"http://127.0.0.1:{port}/webhook"

    # Run checker with very small max age so it will be considered stale
    proc = subprocess.run(
        ["python3", "scripts/check_ribs_health.py", "1"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # shutdown server
    httpd.shutdown()

    # script should exit with code 3 when stale (per script behavior)
    assert proc.returncode == 3
    assert SimpleWebhookHandler.received is not None
    if isinstance(SimpleWebhookHandler.received, dict):
        assert "text" in SimpleWebhookHandler.received
        assert "RIBS checkpoint stale" in SimpleWebhookHandler.received["text"]
    else:
        assert "RIBS checkpoint stale" in SimpleWebhookHandler.received


if __name__ == "__main__":
    pytest.main([__file__])
