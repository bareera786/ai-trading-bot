#!/usr/bin/env python3
"""Clear trade history (file-based + optional DB rows).

This is a destructive operation.

- File-based trade history lives under `trade_data/` (profile-aware).
- DB-backed trade rows live in Postgres table `user_trade`.

The file clear path is safe-ish: it creates timestamped backups for any JSON
files it touches.

Typical usage inside the production container:

    python scripts/clear_trade_history.py --all-profiles --files --db --all-users --yes

"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class ClearResult:
    backups_created: int
    files_cleared: int
    exports_deleted: int
    db_rows_deleted: Optional[int]


JSON_FILES = ("comprehensive_trades.json", "crt_signals.json", "trading_journal.json")
EXPORT_GLOBS = ("comprehensive_trades_export_*.csv",)


def _utc_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _iter_trade_data_dirs(trade_data_root: Path, *, profile: str, all_profiles: bool) -> list[Path]:
    if not trade_data_root.exists():
        return []

    dirs: list[Path] = []

    # Legacy/default layout: trade_data/ contains files directly.
    legacy_dir = trade_data_root
    if all_profiles:
        dirs.append(legacy_dir)
        for entry in trade_data_root.iterdir():
            if entry.is_dir():
                dirs.append(entry)
        # De-dupe while preserving order
        seen = set()
        uniq: list[Path] = []
        for d in dirs:
            rp = d.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            uniq.append(d)
        return uniq

    # Single profile mode
    profiled_dir = trade_data_root / profile
    if profile == "default":
        # If running in legacy mode, the app may read from trade_data/ directly.
        dirs.append(legacy_dir)
    dirs.append(profiled_dir)
    # Keep only ones that exist.
    return [d for d in dirs if d.exists()]


def _backup_and_remove(path: Path) -> bool:
    if not path.exists():
        return False
    stamp = _utc_stamp()
    backup = path.with_name(f"{path.name}.backup_{stamp}")
    backup.write_bytes(path.read_bytes())
    path.unlink(missing_ok=True)
    return True


def clear_files(
    *,
    project_root: Path,
    profile: str,
    all_profiles: bool,
    delete_exports: bool,
) -> tuple[int, int, int]:
    trade_data_root = project_root / "trade_data"
    dirs = _iter_trade_data_dirs(trade_data_root, profile=profile, all_profiles=all_profiles)

    backups_created = 0
    files_cleared = 0
    exports_deleted = 0

    for data_dir in dirs:
        for filename in JSON_FILES:
            path = data_dir / filename
            if _backup_and_remove(path):
                backups_created += 1
                files_cleared += 1

        if delete_exports:
            for pattern in EXPORT_GLOBS:
                for export_path in data_dir.glob(pattern):
                    try:
                        export_path.unlink(missing_ok=True)
                        exports_deleted += 1
                    except Exception:
                        # best effort
                        pass

    return backups_created, files_cleared, exports_deleted


def clear_db(*, user_id: Optional[int], all_users: bool) -> int:
    # Avoid starting heavy runtime workers.
    os.environ.setdefault("SKIP_RUNTIME_BOOTSTRAP", "1")

    from app import create_app
    from app.extensions import db
    from app.models import UserTrade

    app = create_app()
    with app.app_context():
        query = UserTrade.query
        if user_id is not None:
            query = query.filter(UserTrade.user_id == user_id)
        elif not all_users:
            raise ValueError("Refusing to clear DB trade history without --all-users or --user-id")

        deleted = query.delete(synchronize_session=False)
        db.session.commit()
        return int(deleted or 0)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clear trade history (files and/or DB).")

    parser.add_argument(
        "--profile",
        default=os.getenv("BOT_PROFILE", "default"),
        help="Profile name to clear (default: $BOT_PROFILE or 'default').",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Clear trade_data for all profiles (and legacy root).",
    )

    parser.add_argument(
        "--files",
        action="store_true",
        help="Clear file-based trade history under trade_data/.",
    )
    parser.add_argument(
        "--delete-exports",
        action="store_true",
        help="Also delete CSV exports (comprehensive_trades_export_*.csv).",
    )

    parser.add_argument(
        "--db",
        action="store_true",
        help="Clear DB-backed trade history (table user_trade).",
    )
    parser.add_argument("--user-id", type=int, default=None, help="Only delete DB rows for this user_id.")
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Required to delete DB trade history for ALL users.",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation to perform deletion.",
    )

    args = parser.parse_args(list(argv))

    if not args.files and not args.db:
        parser.error("Choose at least one: --files and/or --db")

    if args.db and args.user_id is None and not args.all_users:
        parser.error("DB deletion requires --user-id or --all-users")

    if not args.yes:
        parser.error("Refusing to run without --yes")

    return args


def run(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    project_root = Path(__file__).resolve().parents[1]
    backups_created = files_cleared = exports_deleted = 0
    db_rows_deleted: Optional[int] = None

    if args.files:
        backups_created, files_cleared, exports_deleted = clear_files(
            project_root=project_root,
            profile=str(args.profile),
            all_profiles=bool(args.all_profiles),
            delete_exports=bool(args.delete_exports),
        )

    if args.db:
        db_rows_deleted = clear_db(user_id=args.user_id, all_users=bool(args.all_users))

    result = ClearResult(
        backups_created=backups_created,
        files_cleared=files_cleared,
        exports_deleted=exports_deleted,
        db_rows_deleted=db_rows_deleted,
    )

    print("✅ Trade history cleared")
    print(f"- File backups created: {result.backups_created}")
    print(f"- File JSON cleared: {result.files_cleared}")
    if args.delete_exports:
        print(f"- CSV exports deleted: {result.exports_deleted}")
    if result.db_rows_deleted is not None:
        print(f"- DB rows deleted: {result.db_rows_deleted}")

    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
