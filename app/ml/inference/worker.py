import multiprocessing
import logging
import time

class AsyncInferenceWorker(multiprocessing.Process):
    """
    Dedicated worker process for ML inference to prevent blocking the main loop.
    RUNS IN A SEPARATE PROCESS.
    """
    def __init__(self, input_queue, output_queue, models_dir, profile="ultimate", ml_system_class=None):
        """
        Initialize the AsyncInferenceWorker.
        
        Args:
            input_queue: Queue for receiving inference requests
            output_queue: Queue for sending inference results
            models_dir: Directory containing ML models
            profile: Trading profile name
            ml_system_class: The ML system class to instantiate (Dependency Injection)
                             This allows avoiding circular imports or global state reliance.
        """
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.models_dir = models_dir
        self.profile = profile
        self.ml_system_class = ml_system_class
        self.daemon = True  # Ensure worker dies if main process dies

    def run(self):
        """Worker main loop"""
        # Re-initialize ML system execution context within this process
        # We need a fresh ML system instance to ensure thread safety
        try:
            # Import here to avoid circular dependencies if any
            # Initialize ML system
            logging.info(f"🚀 Async Inference Worker ({self.profile}) starting...")
            
            # Using OptimizedMLTrainingSystem as the backend (via Dependency Injection)
            if self.ml_system_class:
                ml_system = self.ml_system_class(models_dir=self.models_dir)
            else:
                logging.warning("⚠️ No ml_system_class provided to AsyncInferenceWorker. Inference disabled.")
                ml_system = None
            
            while True:
                try:
                    # BLOCKING get (CPU idle waiting)
                    task = self.input_queue.get()
                    
                    if task == "STOP":
                        logging.info("Async Inference Worker received STOP signal")
                        break
                        
                    if task == "RELOAD":
                        logging.info("♻️ Async Inference Worker refreshing models...")
                        if ml_system and hasattr(ml_system, "load_models"):
                            try:
                                ml_system.load_models()
                                logging.info("✅ Models reloaded successfully in worker process")
                            except Exception as e:
                                logging.error(f"❌ Failed to reload models: {e}")
                        else:
                            logging.warning("⚠️ ML System does not support hot-reload (no load_models method)")
                        continue
                        
                    request_id, symbol, market_data = task
                    
                    if not ml_system:
                        continue

                    # Perform Blocking Inference
                    start_time = time.time()
                    prediction = ml_system.predict_professional(symbol, market_data)
                    duration = time.time() - start_time
                    
                    # Push result
                    result_payload = {
                        "request_id": request_id,
                        "symbol": symbol,
                        "prediction": prediction,
                        "timestamp": time.time(),
                        "duration": duration
                    }
                    self.output_queue.put(result_payload)
                    
                except Exception as e:
                    logging.error(f"Async Inference Worker Error: {e}")
                    # Don't crash the worker, just log and continue
                    continue
                    
        except Exception as startup_error:
            logging.critical(f"Async Inference Worker Startup Failed: {startup_error}")
