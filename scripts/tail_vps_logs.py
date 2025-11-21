#!/usr/bin/env python3
"""Tail remote VPS log files over SSH to verify live trading activity."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


def build_ssh_command(host: str, log_path: str, lines: int, identity: str | None, ssh_port: int) -> list[str]:
    cmd = ["ssh", "-p", str(ssh_port)]
    if identity:
        cmd.extend(["-i", identity])
    cmd.append(host)
    remote_cmd = f"tail -n {lines} {shlex.quote(log_path)}"
    cmd.append(remote_cmd)
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="SSH destination, e.g. user@example.com")
    parser.add_argument(
        "--log-path",
        default="/var/log/ai-trading-bot/trades.log",
        help="Remote log file to tail",
    )
    parser.add_argument("--lines", type=int, default=200, help="Number of log lines to fetch")
    parser.add_argument("--identity", help="Path to SSH private key to use")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default 22)")

    args = parser.parse_args()
    identity = str(Path(args.identity).expanduser()) if args.identity else None
    cmd = build_ssh_command(args.host, args.log_path, args.lines, identity, args.port)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Remote log command failed with exit code {exc.returncode}")
        return exc.returncode
    except FileNotFoundError:
        print("❌ ssh executable not found on this system")
        return 127

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
