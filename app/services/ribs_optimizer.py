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
import time
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
        # Track current iteration for progress reporting
        self.current_iteration = 0

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
            threshold = float(self.config.get("threshold_min", -10.0))
            archive = ribs.archives.GridArchive(
                solution_dim=self.config["solution_dim"],
                dims=self.config["archive_dimensions"],
                ranges=self.config["archive_ranges"],
                learning_rate=0.01,
                threshold_min=threshold,
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
            # Defensive: coerce solution to numpy array (log if it's an unexpected type)
            try:
                sol_arr = np.asarray(solution)
            except Exception:
                # If conversion fails, keep original repr for logging and proceed
                sol_arr = solution

            # Decode parameters
            params = self.decode_solution(sol_arr)

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
            # Log full traceback and the offending solution (repr) for easier debugging
            try:
                self.logger.exception(
                    "Evaluation failed",
                    extra={
                        "solution_repr": repr(solution),
                        "solution_type": type(solution).__name__,
                    },
                )
            except Exception:
                self.logger.error(
                    f"Evaluation failed: {e} (also failed to log solution repr)"
                )

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
            # Defensive handling: ensure period is a valid integer >= 1
            try:
                # Coerce to int where sensible (e.g., float -> int)
                period_int = int(period)
            except Exception:
                # This is expected for many malformed candidate values (slice, None, etc.)
                # Use debug level to avoid log noise; fall back to default 14
                self.logger.debug(f"Invalid RSI period {period!r}, falling back to 14")
                period_int = 14

            if period_int < 1:
                # Treat non-positive values as malformed candidates and fall back silently
                self.logger.debug(f"RSI period {period_int} < 1, using 14")
                period_int = 14

            # If not enough data for the given period, return neutral RSI (50)
            if len(prices) < max(1, period_int):
                return pd.Series([50] * len(prices), index=prices.index)

            delta = prices.diff()
            gain = (
                delta.where(delta > 0, 0)
                .rolling(window=period_int, min_periods=period_int)
                .mean()
            )
            loss = (
                (-delta.where(delta < 0, 0))
                .rolling(window=period_int, min_periods=period_int)
                .mean()
            )
            # Avoid division by zero
            rs = gain / (loss.replace(0, np.nan))
            rsi = 100 - (100 / (1 + rs))
            # Where RSI is NaN (due to zero loss/gain windows), fill with 50 (neutral)
            return rsi.fillna(50)
        except (ValueError, TypeError) as e:
            # Often pandas raises ValueError('window must be an integer 0 or greater')
            # for malformed window values; log at warning level and return neutral series.
            self.logger.warning(f"RSI calculation failed (malformed input): {e}")
            return pd.Series([50] * len(prices), index=prices.index)
        except Exception as e:
            # Unexpected exceptions should be logged with full traceback
            self.logger.exception(f"RSI calculation failed unexpectedly: {e}")
            return pd.Series([50] * len(prices), index=prices.index)

    def run_optimization_cycle(self, market_data: Dict, iterations: int = 100):
        """Run one optimization cycle

        Returns a list of elite strategies as tuples: (solution, objective, behavior).
        """
        self.logger.info(
            f"Starting RIBS optimization cycle with {iterations} iterations"
        )

        # Heartbeat: log cycle start time for improved observability
        self.logger.info("RIBS optimization cycle heartbeat: start")

        # cross-process status: write a status file indicating cycle start
        try:
            status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
            status_tmp = status_path + ".tmp"
            status = {
                "running": True,
                "start_time": datetime.now().isoformat(),
                "iterations": iterations,
            }
            # store total for progress percent calculations
            self.current_total = int(iterations)
            with open(status_tmp, "w") as sf:
                json.dump(status, sf)
                try:
                    sf.flush()
                    os.fsync(sf.fileno())
                except Exception:
                    pass
            os.replace(status_tmp, status_path)
        except Exception:
            self.logger.warning("Failed to write ribs_status start file")

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
                        sol = future_to_sol.get(future)
                        try:
                            obj, beh = future.result()
                        except Exception as e:
                            # Log exception with full traceback and offending solution
                            try:
                                self.logger.exception(
                                    "Exception during solution evaluation",
                                    extra={
                                        "solution_repr": repr(sol),
                                        "solution_type": type(sol).__name__,
                                    },
                                )
                            except Exception:
                                self.logger.error(
                                    f"Exception evaluating solution: {e} (failed to log solution repr)"
                                )

                            # Use penalized evaluation result for failed futures and continue
                            obj, beh = -100.0, [0.0, 100.0, 0.0]

                        objectives.append(obj)
                        behaviors.append(beh)

                # Tell results back to scheduler
                # Sanitize objectives and behaviors (defensive) before telling scheduler
                try:
                    sanitized_objectives = []
                    sanitized_behaviors = []
                    for o, b in zip(objectives, behaviors):
                        # coerce objective to float
                        try:
                            o_safe = float(o)
                        except Exception:
                            self.logger.warning(
                                "Non-numeric objective encountered during sanitize; using penalty",
                                extra={"objective_repr": repr(o)},
                            )
                            o_safe = -100.0

                        # coerce behavior to list of floats
                        try:
                            b_iter = list(b)
                            b_safe = [float(x) for x in b_iter]
                        except Exception:
                            self.logger.warning(
                                "Non-iterable or invalid behavior encountered during sanitize; using default",
                                extra={"behavior_repr": repr(b)},
                            )
                            b_safe = [0.0, 100.0, 0.0]

                        sanitized_objectives.append(o_safe)
                        sanitized_behaviors.append(b_safe)

                    self.scheduler.tell(sanitized_objectives, sanitized_behaviors)
                except Exception as e:
                    self.logger.exception(
                        "Failed to tell scheduler after sanitizing results",
                        extra={"error": str(e)},
                    )
                # Progress reporting: configurable interval
                try:
                    progress_interval = int(self.config.get("progress_interval", 10))
                except Exception:
                    progress_interval = 10

                if progress_interval < 1:
                    progress_interval = 1

                if i % progress_interval == 0:
                    # Update current iteration and log progress (also writes status file)
                    self.current_iteration = i
                    self.log_progress(i, total=iterations)

                # Update best solution
                max_obj_idx = np.argmax(objectives)
                if objectives[max_obj_idx] > self.best_objective:
                    self.best_objective = objectives[max_obj_idx]
                    self.best_solution = solutions[max_obj_idx].copy()

                # Save checkpoint periodically
                if i % 50 == 0:
                    self.save_checkpoint()
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception(f"RIBS optimization cycle failed: {exc}")
            # Attempt to write a failure status file
            try:
                status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
                with open(status_path, "w") as sf:
                    json.dump({"running": False, "error": str(exc)}, sf)
            except Exception:
                pass
            return []

        # Post-cycle: log completion, write a final status file, and return elite strategies
        try:
            self.logger.info("RIBS optimization cycle completed")

            # Build elites list (best known solution)
            elites = []
            if self.best_solution is not None:
                elites.append(
                    (
                        self.best_solution.tolist()
                        if hasattr(self.best_solution, "tolist")
                        else self.best_solution,
                        float(self.best_objective),
                        [],
                    )
                )

            # update cross-process status file to indicate completion (best-effort)
            try:
                status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
                status_tmp = status_path + ".tmp"
                status = {
                    "running": False,
                    "last_completed": datetime.now().isoformat(),
                    "iterations": iterations,
                    "archive_stats": self.get_archive_stats(),
                }
                # Include elite strategies and behavior arrays for dashboard visualizations
                try:
                    elites = self.get_elite_strategies(top_n=10) or []
                    status.setdefault("archive_stats", {})["elites"] = elites

                    # Prepare behavior arrays expected by the front-end
                    behaviors_x = [
                        e.get("behavior", [None, None, None])[0] for e in elites
                    ]
                    behaviors_y = [
                        e.get("behavior", [None, None, None])[1] for e in elites
                    ]
                    behaviors_z = [
                        e.get("behavior", [None, None, None])[2] for e in elites
                    ]
                    objectives = [e.get("objective") for e in elites]

                    status["behaviors_x"] = behaviors_x
                    status["behaviors_y"] = behaviors_y
                    status["behaviors_z"] = behaviors_z
                    status["objectives"] = objectives
                    status["elite_strategies"] = elites
                except Exception:
                    # Best-effort only; do not fail the completion write if elites can't be sampled
                    pass
                # ensure progress reflects completion
                try:
                    status["current_iteration"] = int(iterations)
                    status["progress_percent"] = 100
                except Exception:
                    pass
                with open(status_tmp, "w") as sf:
                    json.dump(status, sf)
                    try:
                        sf.flush()
                        os.fsync(sf.fileno())
                    except Exception:
                        pass
                os.replace(status_tmp, status_path)
            except Exception:
                self.logger.warning("Failed to write ribs_status completion file")

            self.logger.info("RIBS optimization cycle heartbeat: completed")
            return elites
        except Exception as e:
            self.logger.error(f"RIBS optimization cycle failed: {e}")
            return []

    def log_progress(self, iteration: int, total: int = 1):
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
            # Also write a lightweight progress status to ribs_status.json for external monitors
            try:
                # Always write a fresh status file rather than relying on reading it first.
                status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
                status_tmp = status_path + ".tmp"

                # Guard total against zero
                total_safe = int(total) if int(total) > 0 else 1
                progress = int(100.0 * (float(iteration) / float(total_safe)))

                status = {
                    "running": True,
                    "current_iteration": int(iteration),
                    "progress_percent": progress,
                    "archive_stats": self.get_archive_stats(),
                }

                # Also include latest_checkpoint metadata if available
                try:
                    files = [
                        os.path.join(self.checkpoints_dir, f)
                        for f in os.listdir(self.checkpoints_dir)
                        if f.endswith(".pkl")
                    ]
                    if files:
                        latest_file = max(files, key=os.path.getmtime)
                        status["latest_checkpoint"] = {
                            "path": latest_file,
                            "mtime": os.path.getmtime(latest_file),
                            "size": os.path.getsize(latest_file),
                        }
                except Exception:
                    pass

                with open(status_tmp, "w") as sf:
                    json.dump(status, sf)
                    try:
                        sf.flush()
                        os.fsync(sf.fileno())
                    except Exception:
                        pass
                os.replace(status_tmp, status_path)
            except Exception:
                self.logger.exception("Failed to update ribs_status progress file")
        except Exception as e:
            self.logger.error(f"Failed to log progress: {e}")

    def save_checkpoint(self):
        """Save optimization checkpoint"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_path = os.path.join(
                self.checkpoints_dir, f"ribs_checkpoint_{timestamp}.pkl"
            )
            tmp_path = checkpoint_path + ".tmp"

            checkpoint = {
                "archive": self.archive,
                "best_solution": self.best_solution,
                "best_objective": self.best_objective,
                "history": self.history,
                "timestamp": timestamp,
            }

            # Write to a temporary file and atomically replace the final file
            try:
                with open(tmp_path, "wb") as f:
                    pickle.dump(checkpoint, f)
                    try:
                        f.flush()
                        os.fsync(f.fileno())
                    except Exception:
                        # fsync may fail on some filesystems; continue but warn
                        self.logger.warning("Failed to fsync checkpoint tmp file")

                # Ensure tmp file is non-empty before replacing final file
                try:
                    tmp_size = os.path.getsize(tmp_path)
                except Exception:
                    tmp_size = 0

                if tmp_size <= 0:
                    # Do not replace with an empty temp file; clean up and warn
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    self.logger.warning(
                        "Checkpoint tmp file was empty; aborting checkpoint save"
                    )
                else:
                    os.replace(tmp_path, checkpoint_path)
                    self.logger.info(
                        f"RIBS checkpoint saved atomically: {checkpoint_path}"
                    )
            finally:
                # Defensive cleanup: ensure no stray tmp file remains
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
            # Post-save cleanup: remove any zero-byte final checkpoints and stray tmp files
            try:
                for fname in os.listdir(self.checkpoints_dir):
                    fpath = os.path.join(self.checkpoints_dir, fname)
                    if fname.endswith(".tmp"):
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
                    if fname.endswith(".pkl"):
                        try:
                            if os.path.getsize(fpath) == 0:
                                os.remove(fpath)
                                self.logger.warning(
                                    "Removed stale zero-byte checkpoint: %s", fpath
                                )
                        except Exception:
                            pass
            except Exception:
                pass

            # update status file with latest checkpoint info (cross-process)
            try:
                status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
                status_tmp = status_path + ".tmp"
                status = {}
                # load existing status if available
                try:
                    with open(status_path, "r") as sf:
                        status = json.load(sf) or {}
                except Exception:
                    status = {}

                status["latest_checkpoint"] = {
                    "path": checkpoint_path,
                    "mtime": os.path.getmtime(checkpoint_path),
                    "size": os.path.getsize(checkpoint_path),
                }
                # Also include current iteration/progress if available
                try:
                    status["current_iteration"] = int(
                        getattr(self, "current_iteration", 0)
                    )
                    status["progress_percent"] = int(
                        100.0
                        * (
                            float(status.get("current_iteration", 0))
                            / float(getattr(self, "current_total", 1))
                        )
                    )
                except Exception:
                    pass

                with open(status_tmp, "w") as sf:
                    json.dump(status, sf)
                    try:
                        sf.flush()
                        os.fsync(sf.fileno())
                    except Exception:
                        pass
                os.replace(status_tmp, status_path)
            except Exception:
                self.logger.warning(
                    "Failed to write latest checkpoint to ribs_status file"
                )

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

            for entry in elites:
                try:
                    # sample_elites may return tuples of variable shape; defensively unpack
                    solution = entry[0]
                    objective = float(entry[1]) if len(entry) > 1 else None
                    behavior = entry[2] if len(entry) > 2 else None
                except Exception:
                    try:
                        solution, objective, behavior = entry
                    except Exception:
                        self.logger.error("Failed to parse elite entry: %r", entry)
                        continue

                # Normalize solution and behavior to serializable forms
                try:
                    solution_list = (
                        solution.tolist()
                        if hasattr(solution, "tolist")
                        else list(solution)
                    )
                except Exception:
                    solution_list = solution

                try:
                    behavior_list = (
                        behavior.tolist()
                        if hasattr(behavior, "tolist")
                        else list(behavior)
                    )
                except Exception:
                    behavior_list = []

                strategy = {
                    "id": f"ribs_elite_{len(elite_strategies)+1}",
                    "solution": solution_list,
                    "objective": objective,
                    "behavior": behavior_list,
                    "params": self.decode_solution(solution),
                }
                elite_strategies.append(strategy)

            return elite_strategies

        except Exception as e:
            self.logger.error(f"Failed to get elite strategies: {e}")
            return []

    def check_checkpoint_freshness(self, max_age_seconds: int = 6 * 3600) -> dict:
        """Check ribs_status.json and latest checkpoint freshness.

        Returns a dict with keys: status (ok/warn/missing), latest_checkpoint (dict or None), age_seconds (int or None)
        """
        status_path = os.path.join(self.checkpoints_dir, "ribs_status.json")
        result = {"status": "missing", "latest_checkpoint": None, "age_seconds": None}
        try:
            if not os.path.exists(status_path):
                self.logger.warning("RIBS status file missing: %s", status_path)
                return result

            with open(status_path, "r") as sf:
                status = json.load(sf) or {}

            latest = status.get("latest_checkpoint")
            if not latest or not latest.get("path"):
                result["status"] = "no_checkpoint"
                return result

            mtime = latest.get("mtime")
            if mtime is None:
                result["status"] = "unknown"
                return result

            age = int(time.time() - float(mtime))
            result["latest_checkpoint"] = latest
            result["age_seconds"] = age
            result["status"] = "ok" if age <= max_age_seconds else "stale"
            if result["status"] == "stale":
                self.logger.warning(
                    "RIBS checkpoint stale: %s seconds old (threshold=%s)",
                    age,
                    max_age_seconds,
                )
            return result
        except Exception as e:
            self.logger.exception("Failed to check RIBS checkpoint freshness: %s", e)
            return result
