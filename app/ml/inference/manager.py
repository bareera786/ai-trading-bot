import multiprocessing
import logging
import time
import hashlib
import random
import queue
from app.ml.inference.worker import AsyncInferenceWorker

class AsyncInferenceManager:
    """
    Manages communication with the AsyncInferenceWorker.
    NON-BLOCKING INTERFACE for the Main Loop.
    """
    def __init__(self, models_dir=None, ml_system_class=None):
        """
        Initialize the AsyncInferenceManager.
        
        Args:
            models_dir: Directory containing ML models.
            ml_system_class: Class reference for the ML system to be instantiated within the worker.
                             (e.g., OptimizedMLTrainingSystem)
        """
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.ml_system_class = ml_system_class
        self.models_dir = models_dir
        
        # Instantiate worker BUT do not start it yet.
        # We pass the class reference for DI.
        self.worker = AsyncInferenceWorker(
            self.input_queue, 
            self.output_queue, 
            self.models_dir,
            ml_system_class=self.ml_system_class
        )
        self.pending_requests = {} # symbol -> {request_id, timestamp}
        self.result_cache = {}     # symbol -> {prediction, timestamp}
        self.cache_ttl = 15.0      # Seconds to keep a prediction valid
        self.running = False

    def start(self):
        if not self.running:
            self.worker.start()
            self.running = True
            logging.info("AsyncInferenceManager started")

    def stop(self):
        if self.running:
            self.input_queue.put("STOP")
            self.worker.join(timeout=2)
            if self.worker.is_alive():
                self.worker.terminate()
            self.running = False
            logging.info("AsyncInferenceManager stopped")

    def reload_models(self):
        """
        Signal the worker to reload models from disk (Hot Reload).
        Useful when Brain Dashboard activates a new strategy.
        """
        if self.running:
            self.input_queue.put("RELOAD")
            logging.info("Sent RELOAD command to Inference Worker")

    def request_inference(self, symbol, market_data):
        """
        Submit an inference request. 
        NON-BLOCKING.
        Returns request_id if submitted, None if pending request is fresh enough.
        """
        # Drain updated results first
        self._drain_results()

        now = time.time()
        
        # Check if we have a pending request that isn't timed out (e.g. < 5s old)
        if symbol in self.pending_requests:
            req = self.pending_requests[symbol]
            if now - req['timestamp'] < 5.0:
                # Already waiting for a fresh result
                return None
        
        # Check if we have a fresh cached result (optional optimization, but we usually request per tick)
        # If cache is very fresh (<2s), maybe skip request? 
        # For now, we allow request to ensure freshest data, but rate limit by pending check.
        
        request_id = hashlib.md5(f"{symbol}_{now}_{random.random()}".encode()).hexdigest()
        self.pending_requests[symbol] = {
            "request_id": request_id,
            "timestamp": now
        }
        
        try:
            self.input_queue.put_nowait((request_id, symbol, market_data))
            return request_id
        except queue.Full:
            logging.warning("Async Inference Queue is Full! Skipping request.")
            return None

    def get_result(self, symbol):
        """
        Get the latest valid prediction for a symbol.
        NON-BLOCKING.
        Returns prediction dict or None if not ready/stale.
        """
        self._drain_results()
        
        if symbol in self.result_cache:
            entry = self.result_cache[symbol]
            age = time.time() - entry['timestamp']
            
            if age <= self.cache_ttl:
                return entry['prediction']
            else:
                # Stale
                return None
        return None

    def _drain_results(self):
        """Consume all available results from output queue without blocking"""
        while True:
            try:
                result = self.output_queue.get_nowait()
                symbol = result['symbol']
                self.result_cache[symbol] = {
                    "prediction": result['prediction'],
                    "timestamp": result['timestamp'] # inference time
                }
                # Cleanup pending
                if symbol in self.pending_requests:
                    if self.pending_requests[symbol]['request_id'] == result['request_id']:
                        del self.pending_requests[symbol]
            except queue.Empty:
                break
