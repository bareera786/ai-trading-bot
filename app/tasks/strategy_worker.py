import time
import threading
import logging
from typing import List, Callable
from app.core.system_state import SystemStateManager

class StrategyExecutionWorker:
    """
    Dedicated worker thread that drives the Phase 7 Multi-Strategy Engine.
    Periodically checks Active Universe and triggers strategy cycles.
    """
    
    def __init__(self, ultimate_trader, get_active_universe: Callable[[], List[str]], interval: float = 10.0):
        self.trader = ultimate_trader
        self.get_active_universe = get_active_universe
        self.interval = interval
        self.logger = logging.getLogger("ai_trading_bot.strategy_worker")
        self._stop_event = threading.Event()
        self._thread = None
        
    def start(self):
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="StrategyExecutionWorker", daemon=True)
        self._thread.start()
        self.logger.info(f"🚀 Strategy Execution Worker started (Instance: {id(self)}, Interval: {self.interval}s)")
        
    def stop(self):
        if not self._thread:
            return
        self.logger.info("🛑 Stopping Strategy Execution Worker...")
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None
        
    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                # 0. Heartbeat (Proof of Life)
                SystemStateManager.heartbeat("strategy_worker", {"interval": self.interval, "universe_size": len(symbols) if 'symbols' in locals() else 0})

                # 1. Get Active Universe
                symbols = self.get_active_universe()
                if not symbols:
                    if time.time() % 60 < self.interval: # Log once per minute roughly
                        self.logger.warning("⚠️ Active Trading Universe is EMPTY - No symbols to trade")
                    time.sleep(1)
                    continue
                    
                # 2. Iterate and Execute
                for symbol in symbols:
                    if self._stop_event.is_set():
                        break
                        
                    try:
                        # Invoke Phase 7 Cycle
                        if hasattr(self.trader, "run_strategy_cycle"):
                            self.trader.run_strategy_cycle(symbol)
                    except Exception as e:
                        self.logger.error(f"Error executing strategy cycle for {symbol}: {e}")
                
                # 3. Wait for next tick
                time.sleep(self.interval)
                
            except Exception as e:
                self.logger.error(f"Strategy Worker Loop Error: {e}")
                time.sleep(5)
