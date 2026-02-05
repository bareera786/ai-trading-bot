import json

import pytest

from flask import url_for


def make_fake_worker():
    class FakeOpt:
        def get_elite_strategies(self, top_n=5):
            return [
                {
                    "id": "ribs_elite_1",
                    "solution": [1, 2, 3],
                    "objective": -10.0,
                    "behavior": [0.0, 0.0, 0.0],
                    "params": {"rsi_period": 14},
                }
            ]

    class FakeWorker:
        def __init__(self):
            self.ribs_optimizer = FakeOpt()

        def load_recent_data(self):
            return {"ohlcv": None}

    return FakeWorker()


def test_ribs_analyze_page_renders(monkeypatch):
    # Create app and test client
    from app import create_app
    from app.routes import status as status_mod
    from app.models import User
    from app.extensions import db

    app = create_app()
    client = app.test_client()

    # Ensure admin user exists and log in
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", email="admin@example.com")
            admin.set_password("admin123")
            admin.is_admin = True
            db.session.add(admin)
            db.session.commit()
        else:
            # Ensure existing user is an admin for this test
            if not admin.is_admin:
                admin.is_admin = True
                db.session.commit()

    # Login as admin
    # Perform login and follow redirects so the session cookie is set in the test client
    resp_login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert resp_login.status_code == 200

    # Ensure the test client session reflects a logged-in admin user
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["_user_id"] = str(admin.id)

    # Attach fake service runtime / worker to context
    fake_service = type("S", (), {})()
    fake_service.self_improvement_worker = make_fake_worker()
    monkeypatch.setattr(status_mod, "_ctx", lambda: {"service_runtime": fake_service})

    # Avoid full template rendering in tests (templates extend base.html which isn't available)
    monkeypatch.setattr(
        status_mod,
        "render_template",
        lambda *a, **kw: "<html>RIBS Strategy Analysis ribs_elite_1</html>",
    )

    resp = client.get("/ribs/analyze/ribs_elite_1")
    assert resp.status_code == 200
    assert b"RIBS Strategy Analysis" in resp.data
    assert b"ribs_elite_1" in resp.data
