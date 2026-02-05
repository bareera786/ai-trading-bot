"""
Add just these 3 functions to your existing bot
"""
import psutil
import os
import time

def limit_training_resources():
    """Call this before any training"""
    # Use only 4 cores for training (cores 4-7)
    import psutil
    p = psutil.Process()
    try:
        p.cpu_affinity([4, 5, 6, 7])  # type: ignore
    except AttributeError:
        # CPU affinity not available on macOS
        pass

    # Limit memory
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 12 * 1024**3))  # 8-12GB
    except ValueError:
        # May fail on some systems
        pass

def should_train_now():
    """Check if it's safe to train"""
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    load = os.getloadavg()[0]

    # Only train if:
    # - CPU < 80%
    # - Memory < 85%
    # - Load < 6
    # - Between 2-5 AM or 2-5 PM UTC
    hour = time.localtime().tm_hour
    good_time = (2 <= hour <= 5) or (14 <= hour <= 17)

    return good_time and cpu < 80 and memory < 85 and load < 6

def send_to_dashboard(metrics):
    """Send metrics to your existing dashboard"""
    # Adapt this to match your dashboard's API
    import requests
    try:
        requests.post('YOUR_DASHBOARD_ENDPOINT', json=metrics, timeout=1)
    except:
        pass  # Fail silently

# Usage in your existing code:
"""
# Before training:
if should_train_now():
    limit_training_resources()
    train_model()
else:
    print("Skipping training - bad time or high load")
"""