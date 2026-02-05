import os
import tempfile

import pytest

# Enable test-mode early so app bootstrap avoids heavy runtime imports
os.environ["AI_BOT_TEST_MODE"] = "true"

# Provide a minimal fake `psutil` module for environments where it's not installed.
try:
    import psutil  # noqa: F401
except Exception:
    import types
    fake_psutil = types.ModuleType("psutil")

    class _VM:
        percent = 10.0
        available = 4 * 1024 ** 3

    class _DU:
        percent = 10.0

    def cpu_percent(interval=0):
        return 10.0

    def virtual_memory():
        return _VM()

    def disk_usage(path):
        return _DU()

    def disk_io_counters():
        class _IO:
            read_bytes = 0
            write_bytes = 0

        return _IO()

    class _Proc:
        def __init__(self, pid=None):
            pass

        def cpu_affinity(self, cores):
            return True

    def Process(pid=None):
        return _Proc(pid)

    fake_psutil.cpu_percent = cpu_percent
    fake_psutil.virtual_memory = virtual_memory
    fake_psutil.disk_usage = disk_usage
    fake_psutil.disk_io_counters = disk_io_counters
    fake_psutil.Process = Process

    import sys

    sys.modules["psutil"] = fake_psutil

from app import create_app
from app.extensions import db
from app.models import User


def _make_user(username: str, password: str):
    user = User()
    user.username = username
    user.email = f"{username}@example.test"
    user.is_admin = False
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_logout_clears_session():
    # Ensure logout clears authentication so /api/current_user is inaccessible
    db_fd, db_path = tempfile.mkstemp()
    try:
        app = create_app()
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}")

        with app.app_context():
            db.create_all()
            _make_user("testuser", "testpass")

            client = app.test_client()

            # Instead of exercising the full login route (which can vary by config),
            # set the session values directly to simulate an authenticated user.
            user = User.query.filter_by(username="testuser").first()
            assert user is not None

            with client.session_transaction() as sess:
                # flask-login stores the user id under the key returned by
                # current_app.login_manager._user_id_attr or default '_user_id'
                sess["_user_id"] = str(user.id)
                # maintain compatibility with app code that also sets 'user_id'
                sess["user_id"] = user.id

            # Authenticated request should succeed
            r = client.get("/api/current_user")
            assert r.status_code == 200
            j = r.get_json()
            assert j and j.get("username") == "testuser"

            # Perform logout (route uses login_required)
            resp = client.get("/logout")
            assert resp.status_code in (302, 303, 200)

            # After logout, /api/current_user should require auth (401 or redirect)
            r2 = client.get("/api/current_user")
            assert r2.status_code in (401, 302, 303)
    finally:
        try:
            db.session.remove()
            db.drop_all()
        except Exception:
            pass