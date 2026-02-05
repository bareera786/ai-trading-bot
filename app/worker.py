import os
import redis
import logging
import sys
from rq import Worker, Queue

# Ensure app path is in sys.path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("rq_worker")

listen = ['training_jobs']

# DEBUG: Pre-import task module to catch import errors
try:
    import app.tasks.training_worker
    logger.info("✅ Successfully imported app.tasks.training_worker")
except Exception as e:
    logger.critical(f"❌ Failed to import app.tasks.training_worker: {e}")
    import traceback
    traceback.print_exc()

def start_worker():
    """Starts the Redis Queue Worker."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        conn = redis.from_url(redis_url)
        logger.info(f"✅ RQ Worker connected to Redis at {redis_url}")
        
        # Use explicit connection passing instead of Connection context (compatible with RQ 1.x and 2.x)
        # Fix: Queue constructor requires connection in newer RQ versions if not pushed
        queues = [Queue(name, connection=conn) for name in listen]
        worker = Worker(queues, connection=conn)
        logger.info("🚀 RQ Worker listening on queues: " + ", ".join(listen))
        worker.work()
            
    except Exception as e:
        logger.critical(f"❌ RQ Worker failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_worker()
