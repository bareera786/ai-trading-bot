#!/usr/bin/env python3
"""Migrate legacy global Binance credentials into per-user scoped entries.

Usage:
  python scripts/migrate_credentials_to_users.py --user-id 2

The script will read `bot_persistence/binance_credentials.json` and, if it finds a global
`spot` or `futures` credential entry, move it under a `users` mapping keyed by the provided
user id. This is a non-destructive operation: a backup of the original file will be created.
"""
import argparse
import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PERSIST = os.path.join(ROOT, "bot_persistence")
CREDFILE = os.path.join(PERSIST, "binance_credentials.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="Target user id to migrate creds into",
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create a backup of the credentials file"
    )
    args = parser.parse_args()

    if not os.path.exists(CREDFILE):
        print(f"No credentials file found at {CREDFILE}")
        return

    with open(CREDFILE, "r", encoding="utf-8") as f:
        data = json.load(f) or {}

    # If there is already a 'users' mapping with this id, abort to avoid overwriting
    users = data.get("users") or {}
    if str(args.user_id) in users:
        print(
            f"User {args.user_id} already has credentials. Aborting to avoid overwrite."
        )
        return

    # Move spot/futures into users mapping
    migrated = False
    for key in ("spot", "futures"):
        if key in data and data.get(key):
            users.setdefault(str(args.user_id), {})[key] = data.pop(key)
            migrated = True

    if not migrated:
        print("No legacy global credentials found to migrate.")
        return

    data["users"] = users

    if args.backup:
        bak = CREDFILE + ".bak"
        shutil.copy2(CREDFILE, bak)
        print(f"Backup written to {bak}")

    tmp = CREDFILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CREDFILE)
    print(f"Migration complete. Credentials moved into user {args.user_id}.")


if __name__ == "__main__":
    main()
