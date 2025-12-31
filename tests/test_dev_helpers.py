import os
from app import create_app
from app.config import Config


def test_whoami_disabled_by_default():
    # Construct an app with TESTING disabled to simulate production-like behavior
    class ProdConfig(Config):
        TESTING = False
        DEBUG = False

    # Pytest sets PYTEST_CURRENT_TEST in the environment; remove it to
    # simulate a non-testing production-like process for this check.
    saved = os.environ.pop("PYTEST_CURRENT_TEST", None)
    try:
        app = create_app(config_class=ProdConfig)
    finally:
        if saved is not None:
            os.environ["PYTEST_CURRENT_TEST"] = saved
    client = app.test_client()

    resp = client.get("/_whoami")
    assert resp.status_code == 404


def test_whoami_enabled_on_flag_localhost():
    os.environ["ENABLE_DEV_ENDPOINTS"] = "1"
    app = create_app()
    with app.test_client() as client:
        resp = client.get("/_whoami")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "db_uri" in body
        assert "pid" in body
    del os.environ["ENABLE_DEV_ENDPOINTS"]


def test_ensure_testadmin_requires_token_when_not_allowlisted():
    os.environ["ENABLE_DEV_ENDPOINTS"] = "1"
    os.environ["DEV_HELPER_ALLOWLIST_IPS"] = "8.8.8.8"
    os.environ["DEV_HELPER_TOKEN"] = "devtoken123"

    app = create_app()
    with app.test_client() as client:
        # Without token and not in allowlist => 403
        resp = client.post("/_ensure_testadmin")
        assert resp.status_code == 403

        # With correct token => should create or update testadmin
        resp2 = client.post("/_ensure_testadmin", headers={"X-DEV-TOKEN": "devtoken123"})
        assert resp2.status_code == 200
        body = resp2.get_json()
        assert "created" in body or "updated" in body

    del os.environ["ENABLE_DEV_ENDPOINTS"]
    del os.environ["DEV_HELPER_ALLOWLIST_IPS"]
    del os.environ["DEV_HELPER_TOKEN"]
