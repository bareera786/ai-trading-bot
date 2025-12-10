#!/usr/bin/env python3
"""Manual update utility for the AI trading bot.

Phase 0 tool: fetches latest code from the configured git remote,
optionally applies it, recompiles the main module, and records the
running version inside the profile-specific persistence directory.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from fnmatch import fnmatch
from typing import Iterable, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sanitize_profile(value: str | None) -> str:
    value = (value or "default").strip()
    sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)
    sanitized = sanitized.lower()
    return sanitized or "default"


def resolve_profile_path(
    relative_dir: str, *, ensure_exists: bool = True, allow_legacy: bool = True
) -> str:
    base = os.path.join(PROJECT_ROOT, relative_dir)
    profile = _sanitize_profile(os.getenv("BOT_PROFILE", "default"))
    profiled = os.path.join(base, profile)

    if profile == "default" and allow_legacy:
        legacy_path = base
        if os.path.exists(legacy_path) and not os.path.exists(profiled):
            target = legacy_path
        else:
            target = profiled
    else:
        target = profiled

    if ensure_exists:
        os.makedirs(target, exist_ok=True)
    return target


def run(
    cmd: list[str], *, check: bool = True, capture: bool = True, env: dict | None = None
) -> subprocess.CompletedProcess:
    kwargs = {
        "cwd": PROJECT_ROOT,
        "env": env or os.environ,
    }
    if capture:
        kwargs.update(
            {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
        )
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        stdout = result.stdout if capture else ""
        stderr = result.stderr if capture else ""
        raise RuntimeError(
            f"Command {cmd} failed (code={result.returncode})\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    return result


def parse_channel(channel: str) -> Tuple[str, str]:
    if ":" in channel:
        remote, ref = channel.split(":", 1)
    elif "/" in channel:
        remote, ref = channel.split("/", 1)
    else:
        remote, ref = "origin", channel
    return remote.strip() or "origin", ref.strip() or "main"


def ensure_clean_tree() -> None:
    status = run(["git", "status", "--porcelain"], capture=True)
    if status.stdout.strip():
        raise RuntimeError(
            "Working tree is dirty. Commit or stash changes before updating."
        )


def get_current_commit() -> str:
    return run(["git", "rev-parse", "HEAD"], capture=True).stdout.strip()


def get_remote_commit(remote: str, ref: str) -> str:
    result = run(["git", "ls-remote", remote, ref], capture=True)
    first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not first_line:
        raise RuntimeError(f"Unable to resolve remote ref {remote}/{ref}")
    commit = first_line.split()[0]
    return commit


def write_version_state(commit_hash: str) -> None:
    persistence_root = resolve_profile_path("bot_persistence")
    meta_dir = os.path.join(persistence_root, "meta")
    os.makedirs(meta_dir, exist_ok=True)
    path = os.path.join(meta_dir, "version.json")
    payload = {
        "version": commit_hash,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def perform_compile() -> None:
    run([sys.executable, "-m", "compileall", "ai_ml_auto_bot_final.py"], capture=False)


def restart_service(service: str) -> None:
    run(["systemctl", "restart", service], capture=False)


def tail_journal(service: str, lines: int = 100) -> None:
    run(["journalctl", "-u", service, "-n", str(lines), "-f"], capture=False)


def _as_iterable(value: Iterable[str] | None) -> list[str]:
    if not value:
        return []
    return [item for item in value if item]


def get_changed_files(base: str, target: str) -> list[str]:
    """Return files that differ between base..target."""
    result = run(["git", "diff", "--name-only", f"{base}..{target}"], capture=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def ensure_allowed_changes(changed: list[str], allowed_patterns: Iterable[str]) -> None:
    patterns = _as_iterable(allowed_patterns)
    if not patterns:
        return

    def is_allowed(path: str) -> bool:
        for pattern in patterns:
            # allow both path-prefix and glob-based matching
            normalized = pattern.rstrip("/")
            if path.startswith(normalized + os.sep) or path == normalized:
                return True
            if fnmatch(path, pattern):
                return True
        return False

    disallowed = [item for item in changed if not is_allowed(item)]
    if disallowed:
        joined = "\n".join(disallowed)
        raise RuntimeError(
            "Update aborting: remote changes touch files outside the allowlist.\n"
            "Specify additional --allow patterns if needed.\n"
            f"Disallowed files:\n{joined}"
        )
    run(["journalctl", "-u", service, "-n", str(lines), "-f"], capture=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI bot updater")
    parser.add_argument(
        "--channel",
        default="origin/main",
        help="Remote/branch or remote:ref to deploy (default origin/main)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply the update (default: dry-run)"
    )
    parser.add_argument(
        "--restart", action="store_true", help="Restart systemd service after update"
    )
    parser.add_argument(
        "--service-name",
        default="aibot.service",
        help="Systemd service name to restart",
    )
    parser.add_argument(
        "--tail", action="store_true", help="Tail journal after restart"
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Restrict updates to files matching the given glob or path prefix. "
            "Repeatable; if omitted, all files are allowed."
        ),
    )
    args = parser.parse_args()

    remote, ref = parse_channel(args.channel)

    print(f"📦 Project root: {PROJECT_ROOT}")
    print(f"👤 Active profile: {_sanitize_profile(os.getenv('BOT_PROFILE'))}")
    print(f"🔄 Checking remote {remote}/{ref}...")

    run(["git", "fetch", remote, ref], capture=False)
    remote_commit = get_remote_commit(remote, ref)
    current_commit = get_current_commit()

    print(f"   • current commit: {current_commit}")
    print(f"   • remote  commit: {remote_commit}")

    if remote_commit == current_commit:
        print("✅ Already up to date.")
        return

    changed_files = get_changed_files(current_commit, remote_commit)
    if changed_files:
        print("🗂  Files that will change:")
        for path in changed_files:
            print(f"   • {path}")
    else:
        print("ℹ️ No file-level diffs detected (merge-only update).")

    ensure_allowed_changes(changed_files, args.allow)

    if not args.apply:
        diff = run(
            ["git", "log", "--oneline", f"{current_commit}..{remote_commit}"],
            capture=True,
        )
        print("📌 Updates available (dry run):")
        print(diff.stdout)
        print("Run again with --apply to install.")
        return

    ensure_clean_tree()

    print("⚙️ Applying update...")
    pre_update_commit = current_commit
    run(["git", "pull", "--ff-only", remote, ref], capture=False)

    try:
        perform_compile()
    except Exception:
        print("❌ Compile failed; reverting to previous commit.")
        run(["git", "reset", "--hard", pre_update_commit], capture=False)
        raise

    new_commit = get_current_commit()
    write_version_state(new_commit)
    print(f"✅ Update applied: {new_commit}")

    if args.restart:
        print(f"🔁 Restarting service {args.service_name}...")
        restart_service(args.service_name)
        if args.tail:
            print("📜 Tailing journal (Ctrl+C to exit)...")
            try:
                tail_journal(args.service_name)
            except KeyboardInterrupt:
                pass
    else:
        print("ℹ️ Restart the bot service to load the new code.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Update failed: {exc}")
        sys.exit(1)
