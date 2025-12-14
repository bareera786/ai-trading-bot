import ribs
import numpy as np
import logging
from typing import List, Tuple, Dict
import json
import pickle
import yaml
from datetime import datetime
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed


class TradingRIBSOptimizer:
    """RIBS optimizer for trading strategies"""

    def __init__(self, config_path: str = "config/ribs_config.yaml"):
        self.logger = logging.getLogger(__name__)
        self.config = self.load_config(config_path)

        # Initialize RIBS components
        self.archive = self.create_archive()
        self.emitters = self.create_emitters()
        self.scheduler = ribs.schedulers.Scheduler(self.archive, self.emitters)

        # Track optimization history
        self.history = []
        self.best_solution = None
        self.best_objective = -float("inf")

        # Create checkpoints directory
        self.checkpoints_dir = "bot_persistence/ribs_checkpoints"
        os.makedirs(self.checkpoints_dir, exist_ok=True)

        self.logger.info("RIBS Trading Optimizer initialized")

    def load_config(self, config_path: str) -> Dict:
        """Load RIBS configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded RIBS config from {config_path}")
            return config["ribs"]
        except Exception as e:
            self.logger.error(f"Failed to load RIBS config: {e}")
            raise

    def create_archive(self):
        """Create RIBS archive for quality-diversity optimization"""
        try:
            archive = ribs.archives.GridArchive(
                solution_dim=self.config["solution_dim"],
                dims=self.config["archive_dimensions"],
                ranges=self.config["archive_ranges"],
                learning_rate=0.01,
                threshold_min=-10.0,
                qd_score_offset=0.0,
            )
            self.logger.info("RIBS GridArchive created successfully")
            return archive
        except Exception as e:
            self.logger.error(f"Failed to create RIBS archive: {e}")
            raise

    def create_emitters(self):
        """Create multiple emitters for diverse strategy exploration"""
        emitters = []
        try:
            for i in range(self.config["num_emitters"]):
                emitter = ribs.emitters.EvolutionStrategyEmitter(
                    archive=self.archive,
                    x0=np.zeros(self.config["solution_dim"]),
                    sigma0=self.config["sigma0"],
                    batch_size=self.config["batch_size"],
                    seed=42 + i,  # Different seeds for diversity
                )
                emitters.append(emitter)
            self.logger.info(f"Created {len(emitters)} RIBS emitters")
            return emitters
        except Exception as e:
            self.logger.error(f"Failed to create RIBS emitters: {e}")
            raise

    def decode_solution(self, solution: np.ndarray) -> Dict:
        """Decode RIBS solution vector into trading parameters"""
        try:
            params = {
                "rsi_period": int(10 + solution[0] * 20),  # 10-30
                "macd_fast": int(8 + solution[1] * 4),  # 8-12
                "macd_slow": int(21 + solution[2] * 10),  # 21-31
                "bbands_period": int(14 + solution[3] * 10),  # 14-24
                "atr_period": int(7 + solution[4] * 7),  # 7-14
                "risk_multiplier": 0.5 + solution[5] * 1.5,  # 0.5-2.0
                "take_profit": 1.5 + solution[6] * 3.5,  # 1.5-5.0%
                "stop_loss": 0.5 + solution[7] * 2.0,  # 0.5-2.5%
                "position_size": 0.01 + solution[8] * 0.09,  # 1-10%
                "max_positions": int(1 + solution[9] * 4),  # 1-5
            }
            return params
        except Exception as e:
            self.logger.error(f"Failed to decode solution: {e}")
            return {}

    def evaluate_solution(
        self, solution: np.ndarray, market_data: Dict
    ) -> Tuple[float, List]:
        """Evaluate a trading strategy"""
        try:
            # Decode parameters
            params = self.decode_solution(solution)

            # Run backtest with these parameters
            results = self.run_backtest(params, market_data)

            # Extract objective (total return) and behavior characteristics
            objective = results["total_return"]
            behavior = [
                results["sharpe_ratio"],
                results["max_drawdown"],
                results["win_rate"],
            ]

            return objective, behavior

        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}")
            return -100.0, [0.0, 100.0, 0.0]  # Penalize failed evaluations

    def run_backtest(self, params: Dict, market_data: Dict) -> Dict:
        """Run a simplified backtest for strategy evaluation"""
        try:
            # This is a simplified backtest - in production you'd use your full backtesting engine
            df = market_data.get("ohlcv", pd.DataFrame())

            if df.empty:
                return {
                    "total_return": -50.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 50.0,
                    "win_rate": 0.0,
                }

            # Simple RSI-based strategy for demonstration
            rsi_period = params.get("rsi_period", 14)
            df["rsi"] = self.calculate_rsi(df["close"], rsi_period)

            # Generate signals
            df["signal"] = 0
            df.loc[df["rsi"] < 30, "signal"] = 1  # Buy signal
            df.loc[df["rsi"] > 70, "signal"] = -1  # Sell signal

            # Calculate returns (simplified)
            returns = []
            position = 0
            entry_price = 0

            for idx, row in df.iterrows():
                if position == 0 and row["signal"] == 1:  # Enter long
                    position = 1
                    entry_price = row["close"]
                elif position == 1 and row["signal"] == -1:  # Exit long
                    exit_price = row["close"]
                    ret = (exit_price - entry_price) / entry_price * 100
                    returns.append(ret)
                    position = 0
                    entry_price = 0

            # Calculate metrics
            if returns:
                total_return = sum(returns)
                win_rate = len([r for r in returns if r > 0]) / len(returns)
                sharpe_ratio = np.mean(returns) / (
                    np.std(returns) + 1e-8
                )  # Avoid division by zero
                max_drawdown = min(returns) if returns else 0
            else:
                total_return = -10.0  # Penalty for no trades
                win_rate = 0.0
                sharpe_ratio = 0.0
                max_drawdown = 0.0

            return {
                "total_return": total_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": abs(max_drawdown),
                "win_rate": win_rate,
            }

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return {
                "total_return": -100.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 50.0,
                "win_rate": 0.0,
            }

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            self.logger.error(f"RSI calculation failed: {e}")
            return pd.Series([50] * len(prices), index=prices.index)

    def run_optimization_cycle(self, market_data: Dict, iterations: int = 100):
        """Run one optimization cycle"""
        self.logger.info(
            f"Starting RIBS optimization cycle with {iterations} iterations"
        )

        try:
            for i in range(iterations):
                # Ask for new solutions
                solutions = self.scheduler.ask()

                # Evaluate solutions in parallel
                objectives = []
                behaviors = []

                with ThreadPoolExecutor(max_workers=min(8, len(solutions))) as executor:
                    future_to_sol = {
                        executor.submit(self.evaluate_solution, sol, market_data): sol
                        for sol in solutions
                    }

                    for future in as_completed(future_to_sol):
                        obj, beh = future.result()
                        objectives.append(obj)
                        behaviors.append(beh)

                # Tell results back to scheduler
                self.scheduler.tell(objectives, behaviors)  # Track progress
                if i % 10 == 0:
                    self.log_progress(i)

                # Update best solution
                max_obj_idx = np.argmax(objectives)
                if objectives[max_obj_idx] > self.best_objective:
                    self.best_objective = objectives[max_obj_idx]
                    self.best_solution = solutions[max_obj_idx].copy()

                # Save checkpoint periodically
                if i % 50 == 0:
                    self.save_checkpoint()

            self.logger.info("RIBS optimization cycle completed")
            return self.archive.sample_elites(10)  # Return top 10 elites

        except Exception as e:
            self.logger.error(f"RIBS optimization cycle failed: {e}")
            return []

    def log_progress(self, iteration: int):
        """Log optimization progress"""
        try:
            stats = self.archive.stats
            self.logger.info(
                f"RIBS Iteration {iteration}: "
                f"Archive Size={stats.num_elites}, "
                f"Coverage={stats.coverage:.2f}, "
                f"QD Score={stats.qd_score:.2f}, "
                f"Best Objective={self.best_objective:.2f}"
            )
        except Exception as e:
            self.logger.error(f"Failed to log progress: {e}")

    def save_checkpoint(self):
        """Save optimization checkpoint"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_path = os.path.join(
                self.checkpoints_dir, f"ribs_checkpoint_{timestamp}.pkl"
            )

            checkpoint = {
                "archive": self.archive,
                "best_solution": self.best_solution,
                "best_objective": self.best_objective,
                "history": self.history,
                "timestamp": timestamp,
            }

            with open(checkpoint_path, "wb") as f:
                pickle.dump(checkpoint, f)

            self.logger.info(f"RIBS checkpoint saved: {checkpoint_path}")

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, checkpoint_path: str):
        """Load optimization checkpoint"""
        try:
            with open(checkpoint_path, "rb") as f:
                checkpoint = pickle.load(f)

            self.archive = checkpoint["archive"]
            self.best_solution = checkpoint["best_solution"]
            self.best_objective = checkpoint["best_objective"]
            self.history = checkpoint["history"]

            self.logger.info(f"RIBS checkpoint loaded: {checkpoint_path}")

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")

    def get_archive_stats(self) -> Dict:
        """Get current archive statistics"""
        try:
            stats = self.archive.stats
            return {
                "num_elites": stats.num_elites,
                "coverage": stats.coverage,
                "qd_score": stats.qd_score,
                "best_objective": self.best_objective,
            }
        except Exception as e:
            self.logger.error(f"Failed to get archive stats: {e}")
            return {}

    def get_elite_strategies(self, top_n: int = 5) -> List[Dict]:
        """Get top elite strategies from archive"""
        try:
            elites = self.archive.sample_elites(top_n)
            elite_strategies = []

            for solution, objective, behavior in elites:
                strategy = {
                    "id": f"ribs_elite_{len(elite_strategies)+1}",
                    "solution": solution.tolist(),
                    "objective": objective,
                    "behavior": behavior.tolist(),
                    "params": self.decode_solution(solution),
                }
                elite_strategies.append(strategy)

            return elite_strategies

        except Exception as e:
            self.logger.error(f"Failed to get elite strategies: {e}")
            return []
