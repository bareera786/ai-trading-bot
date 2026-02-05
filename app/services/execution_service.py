import os
import time
import json
import logging
import signal
import sys
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Adjust path to find app package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app import create_app
import app.extensions as extensions # Dynamic access
from app.extensions import db
from app.models import User, UserPortfolio, ExchangeCredential
from app.services.binance import CredentialCipher
from app.services.trading import RealBinanceTrader
from app.services.trade_history import ComprehensiveTradeHistory

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [EXEC] %(message)s'
)
logger = logging.getLogger("execution_service")

class ExecutionService:
    STREAM_KEY = "trade_signals"
    GROUP_NAME = "execution_group"
    CONSUMER_NAME = f"worker_{os.getpid()}"
    
    MAX_CONSECUTIVE_FAILURES = 5
    MAX_WORKERS = 50 # Concurrency limit for thread pool
    
    def __init__(self):
        self.app = create_app()
        self.running = True
        self.credential_cipher = CredentialCipher(os.getenv("BINANCE_CREDENTIAL_KEY"))
        self.trade_history = ComprehensiveTradeHistory()
        self.failure_counts = {} # UserID -> Count
        self.executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
        self.loop = None
        
        # Setup Redis Consumer Group (Sync init is fine)
        with self.app.app_context():
            try:
                if extensions.redis_client:
                    try:
                        extensions.redis_client.xgroup_create(self.STREAM_KEY, self.GROUP_NAME, id="$", mkstream=True)
                        logger.info(f"Created consumer group '{self.GROUP_NAME}'")
                    except Exception:
                        pass
                else:
                    logger.error("Redis client not available! Execution service cannot run.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Redis setup failed: {e}")

    def start(self):
        """Entry point to start the async loop."""
        logger.info(f"🚀 Execution Service Started ({self.CONSUMER_NAME}) [Mode: AsyncIO + Threads]")
        
        # Setup signals
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.run_async())
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    async def run_async(self):
        """Main Async Event Loop."""
        # We need the app context for DB access in threads, but main loop handles Redis
        # Redis read is sync, so we wrap it or just block briefly
        # Since we want high concurrency, we should ideally use aioredis, but for now 
        # we wrap the blocking redis call in a thread to keep the loop free for trade completion callbacks?
        # Actually, reading from Redis defaults to blocking, so running it in executor is safer to not freeze loop.
        
        while self.running:
            try:
                # Run blocking Redis read in thread pool
                entries = await self.loop.run_in_executor(
                    None, 
                    self.read_redis_sync
                )

                if not entries: 
                    # If timeout/empty, loop continues (read_redis_sync has block=5000)
                    continue

                for stream, messages in entries:
                    for message_id, data in messages:
                        await self.process_signal_async(message_id, data)
                        
                        # Ack asynchronously (or sync, it's fast)
                        extensions.redis_client.xack(self.STREAM_KEY, self.GROUP_NAME, message_id)
                        
            except Exception as e:
                logger.error(f"Global Loop Error: {e}")
                await asyncio.sleep(5)

    def read_redis_sync(self):
        """Helper to call blocking redis command safely."""
        try:
            return extensions.redis_client.xreadgroup(
                self.GROUP_NAME,
                self.CONSUMER_NAME,
                {self.STREAM_KEY: ">"},
                count=1,
                block=2000 # 2s block
            )
        except Exception as e:
            # If redis fails (e.g. restart), return None and log
            # logger.error(f"Redis Read Error: {e}")
            time.sleep(1) # Prevent tight loop on error
            return None

    async def process_signal_async(self, message_id, data):
        """Async process wrapper."""
        # 0. Global Kill Switch Check (Fast redis check, sync is ok or wrap)
        if extensions.redis_client.get("global_trading_lock"):
             logger.warning("⛔ GLOBAL TRADING LOCK ACTIVE. Skipping signal.")
             return

        signal_id = data.get("signal_id", "unknown")
        symbol = data.get("symbol")
        side = data.get("side")
        logger.info(f"🔔 Signal Received: {side} {symbol} (ID: {signal_id})")

        # 1. Fetch Eligible Users (DB call -> Thread)
        users = await self.loop.run_in_executor(None, self.get_eligible_users_sync)
        logger.info(f"👥 Found {len(users)} eligible users. Dispatching tasks...")

        # 2. Execute Parallel (Fan-out)
        start_time = time.time()
        tasks = []
        for user_id in users:
            # submit to executor, receive future, wrap in asyncio.wrap_future NO, better: loop.run_in_executor
            tasks.append(
                self.loop.run_in_executor(self.executor, self.execute_for_user_sync, user_id, symbol, side, data)
            )
        
        if tasks:
            # Wait for all executions to finish (scatter-gather)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # results contains return values or Exceptions
            
            # Optional: Log summary
            failures = [r for r in results if isinstance(r, Exception)]
            duration = time.time() - start_time
            logger.info(f"⚡ Batch processed in {duration:.2f}s. Success: {len(users)-len(failures)}, Failures: {len(failures)}")
            
            for exc in failures:
                logger.error(f"Task Failure: {exc}")

    def get_eligible_users_sync(self):
        """Sync DB call helper."""
        with self.app.app_context():
            # Join UserPortfolio and ExchangeCredential to ensure they can actually trade
            results = db.session.query(UserPortfolio.user_id).join(
                ExchangeCredential, UserPortfolio.user_id == ExchangeCredential.user_id
            ).filter(
                UserPortfolio.auto_trade_enabled == True,
                ExchangeCredential.is_active == True,
                ExchangeCredential.exchange_id == "binance" 
            ).all()
            return [r[0] for r in results]

    def execute_for_user_sync(self, user_id, symbol, side, signal_data):
        """Wrapped Execution Logic (Runs in Thread)."""
        with self.app.app_context():
            try:
                # 1. Decrypt Credentials
                creds = ExchangeCredential.query.filter_by(user_id=user_id, exchange_id="binance").first()
                if not creds: return

                api_key = self.credential_cipher.decrypt(creds.api_key_enc)
                api_secret = self.credential_cipher.decrypt(creds.api_secret_enc)
                
                if not api_key or not api_secret:
                    logger.warning(f"User {user_id} has invalid credentials. Skipping.")
                    return

                # 2. Instantiate Trader
                trader = RealBinanceTrader(api_key=api_key, api_secret=api_secret)
                
                # 3. Determine Sizing
                account = trader.get_account_overview()
                balance = float(account.get("availableBalance", 0))

                if balance < 10: return

                allocation_pct = 0.05 
                usd_amount = balance * allocation_pct
                
                price = float(signal_data.get("price") or 0)
                if price <= 0:
                    logger.error(f"User {user_id}: No price available for {symbol}")
                    return

                quantity = usd_amount / price
                quantity = float(f"{quantity:.3f}")

                # 4. Execute Order
                logger.info(f"User {user_id}: Executing {side} {quantity} {symbol} (Bal: ${balance:.2f})")
                
                order_response = None
                if side in ["LONG", "SHORT"]:
                    order_side = "BUY" if side == "LONG" else "SELL"
                    order_response = trader._submit_futures_order(
                        symbol=symbol,
                        side=order_side,
                        quantity=quantity,
                        leverage=3,
                        reduce_only=False
                    )
                elif side == "FLAT":
                     logger.info(f"User {user_id}: FLAT signal received.")
                     return

                # 5. Log Execution
                if order_response and "orderId" in order_response:
                     self.log_trade(user_id, symbol, side, order_response, signal_data)
                     # SUCCESS - Reset failure count (Need lock? Dict is thread-safe for atomic ops in CPython but safer to be careful)
                     # Pure assignment is atomic enough for this counter usage
                     self.failure_counts[user_id] = 0
                else:
                     raise Exception(f"Order Failed. Response: {order_response}")

            except Exception as e:
                logger.error(f"⚠️ Execution failed for User {user_id}: {e}")
                self.handle_failure_sync(user_id)

    def handle_failure_sync(self, user_id):
        """Thread-safe failure handling."""
        # Simple non-atomic increment is fine for loose circuit breaker
        count = self.failure_counts.get(user_id, 0) + 1
        self.failure_counts[user_id] = count
        
        if count >= self.MAX_CONSECUTIVE_FAILURES:
            logger.critical(f"🚫 CIRCUIT BREAKER TRIGGERED for User {user_id}. Disabling Auto-Trade.")
            try:
                # Need app context? Already in one from execute_for_user_sync
                portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
                if portfolio:
                    portfolio.auto_trade_enabled = False
                    db.session.commit()
                    self.failure_counts[user_id] = 0
            except Exception as db_err:
                logger.error(f"Failed to disable user {user_id}: {db_err}")

    def log_trade(self, user_id, symbol, side, order_resp, signal_data):
        """Push record to ComprehensiveTradeHistory."""
        trade_record = {
            "user_id": str(user_id),
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": order_resp.get("origQty"),
            "price": order_resp.get("avgPrice") or 0,
            "total": float(order_resp.get("cumQuote") or 0),
            "pnl": 0,
            "pnl_percent": 0,
            "signal": "MASTER_NODE",
            "confidence": float(signal_data.get("confidence") or 0),
            "strategy": "AI_MASTER",
            "status": "OPEN",
            "execution_mode": "real",
            "real_order_id": str(order_resp.get("orderId")),
            "timestamp": datetime.now().isoformat()
        }
        self.trade_history.add_trade(trade_record)

    def shutdown_handler(self, signum, frame):
        self.running = False
        logger.info("Shutdown Signal Received... Stopping Async Loop.")
        if self.loop:
             self.loop.stop()

    def shutdown(self):
        logger.info("Cleaning up executor...")
        self.executor.shutdown(wait=False)
        logger.info("Bye.")

if __name__ == "__main__":
    service = ExecutionService()
    service.start()
