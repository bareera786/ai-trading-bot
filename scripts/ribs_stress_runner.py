#!/usr/bin/env python3
"""Run a long RIBS optimization cycle for stress testing and logging."""
import logging
import sys
import pandas as pd

from app.services.ribs_optimizer import TradingRIBSOptimizer


def main(iterations: int = 500):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ribs_stress")

    logger.info("Starting RIBS stress run: iterations=%s", iterations)
    opt = TradingRIBSOptimizer()

    # Construct a simple synthetic market dataset
    prices = pd.Series([100 + i for i in range(2000)])
    market_data = {"ohlcv": pd.DataFrame({"close": prices})}

    elites = opt.run_optimization_cycle(market_data, iterations=iterations)
    logger.info("Stress run completed. Elites returned: %s", len(elites))


if __name__ == "__main__":
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(iters)
