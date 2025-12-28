"""Asset helper utilities for hashed static bundles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app, url_for

_MANIFEST_CACHE: Dict[str, Any] = {
    "path": None,
    "mtime": None,
    "data": {},
}


def _load_manifest(manifest_path: Path) -> dict[str, str]:
    cache_path = _MANIFEST_CACHE["path"]
    cache_mtime = _MANIFEST_CACHE["mtime"]

    try:
        stat = manifest_path.stat()
    except FileNotFoundError:
        _MANIFEST_CACHE.update({"path": manifest_path, "mtime": None, "data": {}})
        return {}

    if cache_path == manifest_path and cache_mtime == stat.st_mtime:
        return _MANIFEST_CACHE["data"]

    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError:
        data = {}

    _MANIFEST_CACHE.update(
        {"path": manifest_path, "mtime": stat.st_mtime, "data": data}
    )
    return data


def _resolve_default_asset(logical_name: str) -> str:
    """Map logical asset keys to legacy static paths for fallback."""
    normalized = logical_name.strip()
    if not normalized:
        return ""

    if normalized.startswith(("css/", "js/", "dist/")):
        return normalized

    if normalized.endswith(".css"):
        return f"css/{normalized}"
    if normalized.endswith(".js"):
        return f"js/{normalized}"

    return normalized


def _asset_is_usable(asset_path: str) -> bool:
    static_folder = current_app.static_folder
    if not static_folder or not asset_path:
        return False

    candidate = Path(static_folder) / asset_path
    try:
        return candidate.is_file() and candidate.stat().st_size > 0
    except (FileNotFoundError, OSError):
        return False


def asset_url(logical_name: str, manifest: Optional[dict[str, str]] = None) -> str:
    manifest = manifest or {}
    asset_path = manifest.get(logical_name)
    if asset_path and _asset_is_usable(asset_path):
        return url_for("static", filename=asset_path)

    fallbacks = current_app.config.get("ASSET_FALLBACKS", {})
    fallback_path = fallbacks.get(logical_name)
    if fallback_path:
        return url_for("static", filename=fallback_path)

    default_path = _resolve_default_asset(logical_name)
    return url_for("static", filename=default_path)


def register_asset_helpers(app) -> None:
    manifest_setting = app.config.get("ASSET_MANIFEST_PATH")
    static_folder = Path(app.static_folder)
    manifest_path = (
        Path(manifest_setting)
        if manifest_setting
        else static_folder / "dist" / "manifest.json"
    )

    @app.context_processor
    def inject_asset_helpers():  # type: ignore[override]
        manifest = _load_manifest(manifest_path)

        def _asset_url(logical_name: str) -> str:
            return asset_url(logical_name, manifest=manifest)

        return {"asset_url": _asset_url}
