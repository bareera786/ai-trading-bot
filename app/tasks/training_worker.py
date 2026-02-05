"""
Isolated Training Worker for AI Bot.
Executes training jobs via Redis Queue (RQ).
"""
import uuid
import time
import logging
import traceback
import os
import shutil
import joblib
from datetime import datetime
from app.extensions import db
from app.models import TrainingJob, MLModel

# Setup logger
logger = logging.getLogger("training_worker")

def execute_training_job(job_id_str, params):
    """
    Standard single-model training job.
    """
    # [Existing code remains unchanged...]
    # For now, we will simply import the logic to keep the file clean
    return _run_standard_training(job_id_str, params)

def execute_auto_training_job(job_id_str, params):
    """
    AutoML / Grid Search Training Job.
    Iterates through multiple configurations to find the best model.
    """
    # Set env var BEFORE creating app
    os.environ["SKIP_RUNTIME_BOOTSTRAP"] = "true"
    
    from app import create_app
    app = create_app(config_class=None)
    
    with app.app_context():
        job = None
        try:
            # 1. INITIALIZE JOB
            job = _get_job(job_id_str)
            if not job: 
                return

            job.status = "running"
            job.progress = 0
            job.logs = f"AutoML Worker started via RQ at {datetime.utcnow().isoformat()}\nPARAMS: {params}\n"
            db.session.commit()
            
            logger.info(f"AutoML Job {job_id_str} status -> RUNNING")

            symbol = params.get("symbol")
            if not symbol:
                raise ValueError("Symbol is required for training")

            # 2. DEFINE GRID
            # Timeframes: 15m (scalping), 1h (swing), 4h (macro)
            timeframes = ["15m", "1h", "4h"]
            # Durations: 180 days (recent), 365 days (1y), 730 days (2y)
            durations = [180, 365, 730]
            
            grid = [(tf, dur) for tf in timeframes for dur in durations]
            total_combinations = len(grid)
            
            _log(job, f"Starting Grid Search for {symbol}")
            _log(job, f"Combinations to test: {total_combinations}")
            _log(job, f"Grid: {grid}")

            # Initialize System
            from app.ml.training.system import UltimateMLTrainingSystem
            system = UltimateMLTrainingSystem(profile_key="production")
            
            # Temporary directory for candidates
            temp_dir = os.path.join(system.models_dir, f"automl_{job_id_str}")
            os.makedirs(temp_dir, exist_ok=True)
            
            candidates = []
            
            # 3. GRID SEARCH LOOP
            for idx, (tf, dur) in enumerate(grid):
                step_progress = (idx / total_combinations) * 90
                _update_progress(job, int(step_progress))
                
                _log(job, f"--- testing {tf} / {dur}d ---")
                
                # Unique candidate ID
                candidate_id = f"cand_{tf}_{dur}"
                candidate_path = os.path.join(temp_dir, f"{symbol}_{candidate_id}.pkl")
                
                # Redirect logging
                def worker_logger(sym, message, progress=None):
                    pass # Silence verbose logs during grid search
                system.log_training = worker_logger

                try:
                    # TRAIN CANDIDATE
                    start_ts = time.time()
                    success = system.train_ultimate_model(
                        symbol, 
                        use_real_data=True, 
                        output_path=candidate_path,
                        timeframe=tf,
                        lookback_days=dur
                    )
                    elapsed = time.time() - start_ts
                    
                    if success and os.path.exists(candidate_path):
                        # Load Metrics
                        model_data = joblib.load(candidate_path)
                        risk = model_data.get("risk_metrics", {})
                        
                        metrics = {
                            "timeframe": tf,
                            "lookback": dur,
                            "profit_factor": risk.get("profit_factor", 0.0),
                            "max_drawdown": risk.get("max_drawdown", 100.0),
                            "win_loss_ratio": risk.get("win_loss_ratio", 0.0),
                            "total_trades": risk.get("total_trades", 0),
                            "accuracy": model_data.get("ensemble_accuracy", 0.0),
                            "path": candidate_path,
                            "train_time": elapsed
                        }
                        candidates.append(metrics)
                        _log(job, f"Result: PF={metrics['profit_factor']:.2f} | DD={metrics['max_drawdown']:.1f}% | Acc={metrics['accuracy']:.1%}")
                    else:
                        _log(job, "Failed to train candidate.")
                        
                except Exception as e:
                    _log(job, f"Error on {tf}/{dur}d: {str(e)}")
                    continue

            # 4. SELECT WINNER
            if not candidates:
                raise Exception("No valid models produced from grid search.")
                
            _log(job, "Evaluated all candidates. Selecting winner...")
            
            # Scoring Algorithm:
            # 1. Filter out unsafe models (DD > 30% or PF < 1.05)
            safe_candidates = [
                c for c in candidates 
                if c["max_drawdown"] < 30.0 and c["profit_factor"] > 1.05 and c["total_trades"] > 10
            ]
            
            if not safe_candidates:
                # Fallback: Best Profit Factor even if unsafe (user can decide)
                _log(job, "WARNING: No candidates met safety criteria (DD<30%, PF>1.05). Picking best available.")
                winner = max(candidates, key=lambda x: x["profit_factor"])
            else:
                # Rank by custom score: PF * (1 - DD/100)
                # This rewards high profit factor but penalizes drawdown heavily
                winner = max(safe_candidates, key=lambda x: x["profit_factor"] * (1 - (x["max_drawdown"]/100)))

            _log(job, f"🏆 WINNER: {winner['timeframe']} / {winner['lookback']}d")
            _log(job, f"Stats: PF={winner['profit_factor']:.2f}, DD={winner['max_drawdown']:.1f}%")

            # 5. PROMOTE WINNER TO SHADOW
            version_id = f"v2.{int(datetime.now().timestamp())}_AUTO"
            final_path = os.path.join(system.models_dir, f"{symbol}_{version_id}.pkl")
            
            # Move winner file to final location
            if os.path.exists(winner["path"]):
                shutil.move(winner["path"], final_path)
            
            # Cleanup temp dir
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            # Register in Database
            final_metrics = {
                "accuracy": winner["accuracy"], 
                "max_drawdown": winner["max_drawdown"],
                "profit_factor": winner["profit_factor"],
                "win_loss_ratio": winner["win_loss_ratio"],
                "timeframe": winner["timeframe"],
                "lookback_days": winner["lookback"],
                "auto_trained": True
            }
            
            job.result_metrics = final_metrics
            job.progress = 100
            
            new_model = MLModel(
                version=version_id,
                symbol=symbol,
                type="Ensemble_AutoML",
                status="shadow",
                metrics=final_metrics,
                file_path=final_path
            )
            db.session.add(new_model)
            
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            _log(job, f"✅ SUCCESS: Winner {version_id} registered as SHADOW.")
            
            db.session.commit()
            logger.info(f"AutoML Job {job_id_str} status -> COMPLETED")
            
        except Exception as e:
            logger.error(f"AutoML failed: {e}")
            logger.error(traceback.format_exc())
            if job:
                job.status = "failed"
                job.logs = (job.logs or "") + f"\n❌ FATAL ERROR: {str(e)}\n"
                job.completed_at = datetime.utcnow()
                db.session.commit()
            raise e

def _get_job(job_id_str):
    try:
        if len(str(job_id_str)) > 30:
            job_id = uuid.UUID(str(job_id_str))
        else:
            job_id = int(job_id_str)
        return db.session.get(TrainingJob, job_id)
    except Exception:
        return None

def _run_standard_training(job_id_str, params):
    """
    Standard single-model training logic (Restored).
    """
    import os
    os.environ["SKIP_RUNTIME_BOOTSTRAP"] = "true"
    
    from app import create_app
    app = create_app(config_class=None)
    
    with app.app_context():
        job = None
        try:
            # 1. INITIALIZE JOB
            start_ts = datetime.utcnow()
            job = _get_job(job_id_str)
            if not job:
                logger.error(f"Job {job_id_str} not found!")
                return

            job.status = "running"
            job.progress = 0
            job.logs = f"Worker started via RQ at {start_ts.isoformat()}\nPARAMS: {params}\n"
            db.session.commit()
            
            logger.info(f"Job {job_id_str} status -> RUNNING")

            # 2. REAL WORK
            symbol = params.get("symbol")
            if not symbol:
                raise ValueError("Symbol is required for training")

            timeframe = params.get("timeframe", "1h")
            lookback_days = params.get("lookback_days", 365)
            
            _log(job, f"Initializing Ultimate ML System for {symbol}...")
            _log(job, f"Config: {timeframe} / {lookback_days}d")
            
            from app.ml.training.system import UltimateMLTrainingSystem
            import joblib
            
            system = UltimateMLTrainingSystem(profile_key="production")
            
            # Monkey Patch Logger
            original_log = system.log_training
            def worker_logger(sym, message, progress=None):
                original_log(sym, message, progress)
                _log(job, f"[System] {message}")
                if progress is not None:
                    _update_progress(job, progress)
            system.log_training = worker_logger

            _log(job, "Starting Ultimate Model Training...")
            
            version_id = f"v2.{int(datetime.now().timestamp())}"
            versioned_filename = f"{symbol}_{version_id}.pkl"
            versioned_path = os.path.join(system.models_dir, versioned_filename)
            
            success = system.train_ultimate_model(
                symbol, 
                use_real_data=True, 
                output_path=versioned_path,
                timeframe=timeframe,
                lookback_days=lookback_days
            )
            
            if not success:
                raise Exception("Training system returned False")

            # 3. FINALIZE
            _log(job, f"Training complete. Registering model {version_id}...")
            
            if not os.path.exists(versioned_path):
                raise Exception(f"Model file missing: {versioned_path}")
                
            final_metrics = {}
            try:
                model_data = joblib.load(versioned_path)
                risk = model_data.get("risk_metrics", {})
                final_metrics = {
                    "accuracy": model_data.get("ensemble_accuracy", 0.0), 
                    "max_drawdown": risk.get("max_drawdown", 0.0),
                    "profit_factor": risk.get("profit_factor", 0.0),
                    "win_loss_ratio": risk.get("win_loss_ratio", 0.0),
                    "total_trades": risk.get("total_trades", 0)
                }
            except Exception as e:
                _log(job, f"Warning: Metrics load failed: {e}")

            job.result_metrics = final_metrics
            job.progress = 100
            
            new_model = MLModel(
                version=version_id,
                symbol=symbol,
                type="Ensemble",
                status="shadow",
                metrics=final_metrics,
                file_path=versioned_path
            )
            db.session.add(new_model)
            
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            _log(job, f"✅ SUCCESS: Model {version_id} registered.")
            
            db.session.commit()
            logger.info(f"Job {job_id_str} status -> COMPLETED")
            
        except Exception as e:
            logger.error(f"Job failed: {e}")
            logger.error(traceback.format_exc())
            if job:
                job.status = "failed"
                job.logs = (job.logs or "") + f"\n❌ FATAL ERROR: {str(e)}\n"
                job.completed_at = datetime.utcnow()
                db.session.commit()
            raise e 

# Helper functions for updating progress/logs
def _update_progress(job, percent):
    if job.progress is None or abs(job.progress - percent) >= 1:
        job.progress = percent
        db.session.commit()

def _log(job, message):
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    job.logs = (job.logs or "") + f"[{timestamp}] {message}\n"
    db.session.commit()
