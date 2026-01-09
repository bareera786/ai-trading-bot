from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, url_for

from app.assets import asset_url


def _build_test_app(static_root: Path, manifest_data: dict[str, str]) -> Flask:
    app = Flask(__name__, static_folder=str(static_root))
    manifest_path = static_root / "dist" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    app.config["ASSET_MANIFEST_PATH"] = str(manifest_path)
    app.config["ASSET_FALLBACKS"] = {"dashboard.css": "css/dashboard.css"}
    return app


def test_asset_url_falls_back_when_manifest_asset_missing(tmp_path):
    static_root = Path(tmp_path) / "static"
    (static_root / "css").mkdir(parents=True)
    (static_root / "css" / "dashboard.css").write_text(
        "body { color: white; }", encoding="utf-8"
    )

    manifest_data = {"dashboard.css": "dist/missing-dashboard.css"}
    app = _build_test_app(static_root, manifest_data)

    with app.app_context():
        with app.test_request_context("/"):
            resolved = asset_url("dashboard.css", manifest=manifest_data)
            expected = url_for("static", filename="css/dashboard.css")

    assert resolved == expected


def test_asset_url_falls_back_when_manifest_asset_empty(tmp_path):
    static_root = Path(tmp_path) / "static"
    (static_root / "css").mkdir(parents=True)
    (static_root / "css" / "dashboard.css").write_text(
        "body { color: black; }", encoding="utf-8"
    )

    hashed_asset = static_root / "dist" / "dashboard-empty.css"
    hashed_asset.parent.mkdir(parents=True, exist_ok=True)
    hashed_asset.write_text("", encoding="utf-8")

    manifest_data = {"dashboard.css": "dist/dashboard-empty.css"}
    app = _build_test_app(static_root, manifest_data)

    with app.app_context():
        with app.test_request_context("/"):
            resolved = asset_url("dashboard.css", manifest=manifest_data)
            expected = url_for("static", filename="css/dashboard.css")

    assert resolved == expected


def test_asset_url_resolves_hashed_file_minimal(tmp_path):
    """Minimal test that asset_url resolves a manifest-mapped hashed file."""
    static_root = Path(tmp_path) / "static"
    dist = static_root / "dist"
    dist.mkdir(parents=True)
    # Create hashed file and manifest
    (dist / "test-ABC123.js").write_text("// dummy", encoding="utf-8")
    manifest_data = {"test.js": "dist/test-ABC123.js"}
    app = _build_test_app(static_root, manifest_data)

    with app.app_context():
        with app.test_request_context():
            resolved = asset_url("test.js", manifest=manifest_data)
            assert resolved == url_for("static", filename="dist/test-ABC123.js")


def test_asset_url_discovers_hashed_when_manifest_missing(tmp_path):
    """When manifest path is missing, discovery in dist should find hashed file."""
    static_root = Path(tmp_path) / "static"
    dist = static_root / "dist"
    dist.mkdir(parents=True)
    # create hashed file that should be discovered
    (dist / "missing-XYZ.js").write_text("// dummy", encoding="utf-8")

    app = Flask(__name__, static_folder=str(static_root))
    app.config["ASSET_MANIFEST_PATH"] = "/nonexistent/path"

    with app.app_context():
        with app.test_request_context():
            from app.assets import asset_url as av

            resolved = av("missing.js")
            assert resolved.startswith("/static/dist/")
