#!/usr/bin/env python3
"""Run a long RIBS optimization cycle for stress testing and logging."""
import logging
import sys
import pandas as pd

from app.services.ribs_optimizer import TradingRIBSOptimizer
import threading
import time
import json
import os


def watch_progress(status_path: str, total: int):
    """Poll the ribs_status.json file and print a simple progress bar until the run completes."""
    try:
        last_print = ""
        while True:
            if os.path.exists(status_path):
                try:
                    with open(status_path, "r") as sf:
                        status = json.load(sf) or {}
                except Exception:
                    status = {}

                running = status.get("running", False)
                current = status.get("current_iteration", 0)
                percent = status.get("progress_percent")
                if percent is None:
                    percent = int(100.0 * (float(current) / float(max(1, total))))

                # Build a small text progress bar
                bar_len = 40
                filled = int(round(bar_len * percent / 100.0))
                bar = "#" * filled + "-" * (bar_len - filled)
                msg = f"[{bar}] {percent:3d}% Iter {current}/{total}"
                if msg != last_print:
                    print(msg, end="\r", flush=True)
                    last_print = msg

                if not running:
                    print()  # newline after completion
                    break
            else:
                # No status file yet; just print a waiting spinner
                print("Waiting for ribs status...", end="\r", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgress watch interrupted by user")


def main(iterations: int = 500):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ribs_stress")

    logger.info("Starting RIBS stress run: iterations=%s", iterations)
    opt = TradingRIBSOptimizer()

    # Construct a simple synthetic market dataset
    prices = pd.Series([100 + i for i in range(2000)])
    market_data = {"ohlcv": pd.DataFrame({"close": prices})}

    # Run optimization in a separate thread so we can watch progress
    # Be defensive: Fake/mock optimizers used in tests may not have a checkpoints_dir
    # attribute, so fall back to the project's default path.
    cp_dir = getattr(opt, "checkpoints_dir", None) or os.path.join(
        "bot_persistence", "ribs_checkpoints"
    )
    status_path = os.path.join(cp_dir, "ribs_status.json")

    def runner():
        opt.run_optimization_cycle(market_data, iterations=iterations)

    th = threading.Thread(target=runner, daemon=True)
    th.start()

    # Show progress bar while the run is active
    watch_progress(status_path, iterations)

    th.join()

    try:
        elites = opt.archive.sample_elites(10)
        logger.info("Stress run completed. Elites returned: %s", len(elites))
    except Exception:
        logger.info("Stress run completed. No elites available.")


if __name__ == "__main__":
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(iters)
