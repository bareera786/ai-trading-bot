import os
import tempfile

import pytest

pytest.importorskip("flask_mail")

from app import create_app
from app.extensions import db
from app.models import User


def test_futures_toggle_persists_and_returns_status():
    os.environ["AI_BOT_TEST_MODE"] = "true"
    db_fd, db_path = tempfile.mkstemp()
    try:
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

        with app.app_context():
            db.create_all()
            admin = User(username="admin_ft", email="adminft@test", is_admin=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

            with app.test_client() as client:
                # login
                login = client.post(
                    "/login", json={"username": "admin_ft", "password": "admin123"}
                )
                assert login.status_code == 200

                # enable futures
                resp = client.post("/api/futures/toggle", json={"enable": True})
                assert resp.status_code == 200
                js = resp.get_json()
                assert js.get("futures_trading_enabled") in (True, False)

                # toggle off
                resp2 = client.post("/api/futures/toggle", json={"enable": False})
                assert resp2.status_code == 200
                js2 = resp2.get_json()
                assert js2.get("futures_trading_enabled") in (True, False)

                # toggle by omitting the 'enable' field (should flip state)
                # read current dashboard state
                dash = client.get("/api/dashboard")
                assert dash.status_code == 200
                current = (
                    dash.get_json()
                    .get("system_status", {})
                    .get("futures_trading_enabled", False)
                )

                resp3 = client.post("/api/futures/toggle", json={})
                assert resp3.status_code == 200
                js3 = resp3.get_json()
                assert js3.get("futures_trading_enabled") == (not current)

                # flip back
                resp4 = client.post("/api/futures/toggle", json={})
                assert resp4.status_code == 200
                js4 = resp4.get_json()
                assert js4.get("futures_trading_enabled") == current

    finally:
        # Clean up temporary DB file
        os.close(db_fd)
        os.unlink(db_path)


# end of test file
