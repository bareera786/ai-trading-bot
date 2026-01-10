"""Asset helper utilities for hashed static bundles.

This module provides `asset_url` which resolves logical asset names
to their built (hashed) filenames using a `manifest.json` produced
by the frontend build. It implements manifest caching, graceful
error handling, and a smart fallback strategy:

  1. Check manifest mapping (preferred)
  2. Check `static/dist/{logical_name}` exists
  3. Fallback to `static/{logical_name}` (last resort)

Register using `register_asset_helpers(app)` to expose `asset_url`
to Jinja templates (templates call it as `{{ asset_url('dashboard.js') }}`).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from flask import current_app, url_for

logger = logging.getLogger(__name__)

# Cache manifests per absolute manifest path: {str(manifest_path): manifest_dict}
_manifest_cache: dict[str, dict] = {}


def _load_manifest(manifest_path: Path) -> dict:
    """Load and cache the manifest file for `manifest_path`.

    Returns an empty dict if the manifest is missing or invalid. Caches
    the parsed JSON in `_manifest_cache` keyed by the manifest absolute path.
    """
    manifest_path = manifest_path.resolve()
    key = str(manifest_path)
    if key in _manifest_cache:
        logger.debug("Using cached asset manifest: %s", manifest_path)
        return _manifest_cache[key]

    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            manifest = json.load(fh)
            if not isinstance(manifest, dict):
                logger.warning("Asset manifest %s did not contain a JSON object", manifest_path)
                manifest = {}
            _manifest_cache[key] = manifest
            logger.debug("Loaded asset manifest from %s", manifest_path)
            return manifest
    except FileNotFoundError:
        logger.info("Asset manifest not found at %s", manifest_path)
    except json.JSONDecodeError as exc:
        logger.warning("Asset manifest JSON decode error at %s: %s", manifest_path, exc)
    except Exception as exc:  # defensive: do not crash the app due to manifest issues
        logger.exception("Unexpected error loading asset manifest %s: %s", manifest_path, exc)

    _manifest_cache[key] = {}
    return {}


def _asset_is_usable(asset_path: str) -> bool:
    """Return True if `asset_path` exists under the Flask `static_folder`.

    `asset_path` may be relative with or without a leading 'dist/'. We
    normalize by stripping leading slashes so `Path` joining behaves
    consistently on Windows and Unix.
    """
    static_folder = Path(current_app.static_folder or "")
    # Normalize
    clean = asset_path.lstrip("/\\")
    candidate = static_folder / clean
    exists = candidate.exists()
    size_ok = False
    try:
        size_ok = candidate.stat().st_size > 0
    except Exception:
        # If we cannot stat the file, treat it as not usable
        size_ok = False

    usable = exists and size_ok
    logger.debug(
        "Checking asset file: %s -> exists=%s, size_ok=%s, usable=%s",
        candidate,
        exists,
        size_ok,
        usable,
    )
    return usable


def _find_hashed_in_dist(logical_name: str) -> Optional[str]:
    """Search `static/dist` for a hashed filename matching `logical_name`.

    Returns a path relative to the static folder (e.g. 'dist/dashboard-XYZ.js')
    or `None` if no candidate is found. Prefers the most recently modified file
    when multiple matches exist.
    """
    static_folder = Path(current_app.static_folder or "")
    dist_folder = static_folder / "dist"
    if not dist_folder.exists():
        logger.debug("Dist folder not found: %s", dist_folder)
        return None

    p = Path(logical_name)
    base = p.stem  # 'dashboard' from 'dashboard.js'
    ext = p.suffix  # '.js'

    # Build a glob pattern like 'dashboard-*.js'
    if ext:
        pattern = f"{base}-*{ext}"
    else:
        pattern = f"{base}-*"

    candidates = list(dist_folder.glob(pattern))
    if not candidates:
        logger.debug("No hashed candidates in dist for %s (pattern=%s)", logical_name, pattern)
        return None

    # Choose the most recently modified candidate
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    chosen = candidates[0]
    rel = chosen.relative_to(static_folder)
    logger.debug("Found hashed candidate for %s -> %s", logical_name, rel)
    return str(rel)


def asset_url(logical_name: str, manifest: Optional[dict] = None) -> str:
    """Resolve a public URL for a logical asset name.

    The returned value is suitable for use in templates and will be
    generated via `url_for('static', filename=...)` so Flask will serve
    it from the `static` folder.
    """
    manifest = manifest or {}

    # 1) Try manifest mapping first
    mapped = manifest.get(logical_name)
    if mapped:
        # manifest entries may contain 'dist/...' or similar
        if _asset_is_usable(mapped):
            logger.debug("Asset resolved from manifest: %s -> %s", logical_name, mapped)
            return url_for("static", filename=mapped)
        else:
            logger.debug("Manifest entry present but file missing on disk: %s -> %s", logical_name, mapped)

    else:
        logger.debug("No manifest entry for asset: %s", logical_name)

    # 2) Check static/dist/{logical_name}
    dist_candidate = f"dist/{logical_name}"
    if _asset_is_usable(dist_candidate):
        logger.debug("Asset resolved via dist path: %s", dist_candidate)
        return url_for("static", filename=dist_candidate)

    # 2b) If manifest missing or dist candidate missing, try to find a hashed
    # filename in the dist directory (e.g. dashboard-<hash>.js) and use it.
    hashed = _find_hashed_in_dist(logical_name)
    if hashed and _asset_is_usable(hashed):
        logger.debug("Asset resolved via hashed discovery in dist: %s -> %s", logical_name, hashed)
        return url_for("static", filename=hashed)

    # 3) Try configured fallbacks (e.g. map logical 'dashboard.css' -> 'css/dashboard.css')
    fallbacks = current_app.config.get("ASSET_FALLBACKS") or {}
    fallback = fallbacks.get(logical_name)
    if fallback:
        if _asset_is_usable(fallback):
            logger.debug("Asset resolved via configured fallback: %s -> %s", logical_name, fallback)
            return url_for("static", filename=fallback)
        else:
            logger.debug(
                "Configured fallback present but file missing or empty: %s -> %s",
                logical_name,
                fallback,
            )

    # 4) Last resort: static/{logical_name}
    logger.debug("Falling back to static/%s for asset (last resort)", logical_name)
    return url_for("static", filename=logical_name)


def register_asset_helpers(app) -> None:
    """Register `asset_url` as a Jinja global and ensure manifest is loaded.

    Usage (two lines) inside your Flask app factory:
      from app.assets import register_asset_helpers
      register_asset_helpers(app)
    """
    manifest_setting = app.config.get("ASSET_MANIFEST_PATH")

    # If the configured manifest path is relative, resolve it relative to app.root_path
    if manifest_setting:
        manifest_path = Path(manifest_setting)
        if not manifest_path.is_absolute():
            manifest_path = Path(app.root_path) / manifest_path
    else:
        # Default to {static_folder}/dist/manifest.json
        static_folder = Path(app.static_folder or "")
        manifest_path = static_folder / "dist" / "manifest.json"

    # Pre-load manifest (cached) so templates can use it immediately
    manifest = _load_manifest(manifest_path)

    # Expose as a Jinja global for convenience and backwards compatibility
    def _asset_url(logical_name: str) -> str:
        return asset_url(logical_name, manifest=manifest)

    app.jinja_env.globals["asset_url"] = _asset_url
    # Also keep a context processor to preserve prior behaviour
    @app.context_processor
    def _inject():
        return {"asset_url": _asset_url}
