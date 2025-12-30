"""Profile-aware path helpers shared across the trading bot."""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

PROJECT_ROOT_PATH = Path(__file__).resolve().parents[2]
PROJECT_ROOT = str(PROJECT_ROOT_PATH)
_LOGGER = logging.getLogger(__name__)


def _sanitize_profile(value: Optional[str]) -> str:
    if not value:
        return "default"
    stripped = value.strip()
    sanitized = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in stripped
    )
    sanitized = sanitized.lower()
    return sanitized or "default"


BOT_PROFILE = _sanitize_profile(os.getenv("BOT_PROFILE", "default"))


def _migrate_legacy_directory(base: Path, profiled: Path) -> None:
    """Move legacy single-tenant data into the profile-specific folder."""

    if BOT_PROFILE != "default":
        return
    if not base.exists():
        return
    if profiled.exists():
        return
    try:
        profiled.mkdir(parents=True, exist_ok=True)
        moved_any = False
        for entry in base.iterdir():
            if entry == profiled:
                continue
            if entry.name == BOT_PROFILE:
                continue
            shutil.move(str(entry), str(profiled / entry.name))
            moved_any = True
        if moved_any:
            _LOGGER.info("Migrated legacy data from %s into %s", base, profiled)
    except Exception as exc:  # pragma: no cover - best effort
        _LOGGER.warning(
            "Legacy migration from %s to %s failed: %s", base, profiled, exc
        )


def migrate_file_to_profile(
    source: Union[str, Path], destination: Union[str, Path]
) -> bool:
    """Move a legacy file into the profile-aware destination if needed."""

    src = Path(source)
    dest = Path(destination)
    if not src.exists() or dest.exists():
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        _LOGGER.info("Migrated legacy file %s -> %s", src, dest)
        return True
    except Exception as exc:  # pragma: no cover - best effort
        _LOGGER.warning("Failed to migrate legacy file %s -> %s: %s", src, dest, exc)
        return False


def resolve_profile_path(
    relative_dir: str,
    *,
    ensure_exists: bool = True,
    allow_legacy: bool = True,
    migrate_legacy: bool = False,
) -> str:
    base = PROJECT_ROOT_PATH / relative_dir
    profiled = base / BOT_PROFILE

    if migrate_legacy:
        try:
            _migrate_legacy_directory(base, profiled)
        except Exception as exc:
            _LOGGER.warning(f"Legacy migration failed: {exc}")

    use_legacy = (
        BOT_PROFILE == "default"
        and allow_legacy
        and base.exists()
        and not profiled.exists()
    )

    target = base if use_legacy else profiled

    if ensure_exists:
        try:
            target.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # In containerized environments, we may not have permission to create directories
            # The application should handle directory creation as needed
            _LOGGER.warning(f"Could not create directory {target}, application will create as needed")
        except Exception as exc:
            _LOGGER.warning(f"Failed to create directory {target}: {exc}")
    return str(target)


def safe_parse_datetime(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None
