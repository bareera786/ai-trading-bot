import re
from typing import Optional

import pytest

from app import create_app
from app.extensions import db
from app.models import User


def extract_csrf_from_html(html: str) -> Optional[str]:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


def test_form_login_requires_and_accepts_csrf(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app = create_app()

    with app.app_context():
        db.create_all()
        import uuid

        uniq = uuid.uuid4().hex
        user = User(username=f"testuser_{uniq}", email=f"testuser+{uniq}@example.com", is_active=True, email_verified=True)
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        # GET login form - should include csrf_token
        resp = client.get("/login")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        csrf = extract_csrf_from_html(html)
        assert csrf, "CSRF token should be rendered into the login form"

        # POST without CSRF should be rejected (form submission)
        resp = client.post("/login", data={"username": user.username, "password": "pass123"})
        # Expect a 400 response due to missing CSRF token
        assert resp.status_code == 400

        # POST with CSRF should succeed and redirect to dashboard
        resp = client.post(
            "/login",
            data={"username": user.username, "password": "pass123", "csrf_token": csrf},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        # Should receive a Set-Cookie header for session
        cookies = [h for h in resp.headers.get_all("Set-Cookie")]
        assert any("session=" in c for c in cookies), f"Expected session cookie in {cookies}"


def test_json_login_requires_csrf_header(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    app = create_app()

    with app.app_context():
        db.create_all()
        import uuid

        uniq = uuid.uuid4().hex
        user = User(username=f"jsonuser_{uniq}", email=f"jsonuser+{uniq}@example.com", is_active=True, email_verified=True)
        user.set_password("jsonpass")
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        # JSON post without CSRF header should be rejected
        resp = client.post("/login", json={"username": user.username, "password": "jsonpass"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data and data.get("error") == "Missing CSRF token"

        # Get a valid csrf token from form GET (binds token to session)
        resp = client.get("/login")
        html = resp.get_data(as_text=True)
        csrf = extract_csrf_from_html(html)
        assert csrf

        # Now post JSON with header — accept either a JSON 200 response or a
        # redirect, both indicate a successful login depending on how the
        # request was interpreted by the framework.
        resp = client.post(
            "/login",
            json={"username": user.username, "password": "jsonpass"},
            headers={"X-CSRFToken": csrf},
            follow_redirects=False,
        )
        assert resp.status_code in (200, 302, 303)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data and data.get("success") is True
        else:
            assert "/dashboard" in resp.headers.get("Location", "")
