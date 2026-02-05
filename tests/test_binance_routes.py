import os
import tempfile
import pytest

pytest.importorskip("flask_mail")

from app import create_app
from app.extensions import db
from app.models import User


def test_binance_credentials_crud_flow():
    """Integration test: login as admin and exercise GET/POST/DELETE /api/binance/credentials"""

    # Use a temporary database to avoid touching real data
    # Test-mode to avoid full initialization and external calls
    os.environ["AI_BOT_TEST_MODE"] = "true"
    db_fd, db_path = tempfile.mkstemp()
    try:
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

        with app.app_context():
            db.create_all()

            # Create an admin user
            admin = User(username="admin_test", email="admin@test", is_admin=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

            with app.test_client() as client:
                # Unauthenticated GET should redirect to login (302)
                r = client.get("/api/binance/credentials")
                assert r.status_code in (302, 401)

                # Login as admin
                login_resp = client.post(
                    "/login", json={"username": "admin_test", "password": "admin123"}
                )
                assert login_resp.status_code == 200

                # POST: save credentials
                payload = {
                    "apiKey": "TESTKEY",
                    "apiSecret": "TESTSECRET",
                    "testnet": True,
                    "accountType": "spot",
                    "note": "integration-test",
                }
                post_resp = client.post("/api/binance/credentials", json=payload)
                assert post_resp.status_code == 200
                js = post_resp.get_json()
                assert js is not None
                assert js.get("saved") is True

                # GET should now return status info (dict)
                get_resp = client.get("/api/binance/credentials")
                assert get_resp.status_code == 200
                status = get_resp.get_json()
                assert isinstance(status, dict)

                # DELETE: clear spot credentials
                del_resp = client.delete(
                    "/api/binance/credentials", json={"accountType": "spot"}
                )
                assert del_resp.status_code == 200
                del_js = del_resp.get_json()
                assert del_js.get("cleared") is True

    finally:
        os.close(db_fd)
        os.unlink(db_path)
