"""
Resource management and system monitoring
"""
import psutil
import os
import signal
import time
from dataclasses import dataclass
from typing import Dict, Optional
import logging


@dataclass
class SystemResources:
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    load_avg_1min: float
    disk_usage_percent: float
    nvme_read_mb: float
    nvme_write_mb: float


class ResourceManager:
    """Manages and monitors VPS resources for AI trading bot"""
    
    def __init__(self, 
                 max_cpu_percent: float = 70.0,
                 max_memory_percent: float = 80.0,
                 max_load_avg: float = 6.0,
                 training_cores: list = None):
        
        self.logger = logging.getLogger(__name__)
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_load_avg = max_load_avg
        
        # Core allocation: cores 0-3 for trading, 4-7 for training
        self.trading_cores = [0, 1, 2, 3]
        self.training_cores = training_cores or [4, 5, 6, 7]
        
        # Configure numpy for optimal performance
        self._configure_environment()
    
    def _configure_environment(self):
        """Set optimal environment variables for ML workloads"""
        os.environ['OMP_NUM_THREADS'] = '4'
        os.environ['MKL_NUM_THREADS'] = '4'
        os.environ['NUMEXPR_NUM_THREADS'] = '4'
        os.environ['TF_NUM_INTEROP_THREADS'] = '4'
        os.environ['TF_NUM_INTRAOP_THREADS'] = '4'
    
    def get_system_resources(self) -> SystemResources:
        """Get current system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        load_avg = os.getloadavg()
        disk = psutil.disk_usage('/')
        
        # Get NVMe stats if available
        try:
            disk_io = psutil.disk_io_counters()
            nvme_read = disk_io.read_bytes / 1024 / 1024
            nvme_write = disk_io.write_bytes / 1024 / 1024
        except Exception:
            nvme_read = nvme_write = 0.0
        
        return SystemResources(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=memory.available / (1024**3),
            load_avg_1min=load_avg[0],
            disk_usage_percent=disk.percent,
            nvme_read_mb=nvme_read,
            nvme_write_mb=nvme_write
        )
    
    def is_safe_for_training(self) -> bool:
        """Check if system can handle training workload"""
        resources = self.get_system_resources()
        
        conditions = [
            resources.cpu_percent < self.max_cpu_percent,
            resources.memory_percent < self.max_memory_percent,
            resources.load_avg_1min < self.max_load_avg,
            resources.memory_available_gb > 2.0,  # At least 2GB free
        ]
        
        safe = all(conditions)
        
        if not safe:
            self.logger.warning(
                f"System not safe for training: "
                f"CPU={resources.cpu_percent:.1f}%, "
                f"Memory={resources.memory_percent:.1f}%, "
                f"Load={resources.load_avg_1min:.2f}"
            )
        
        return safe
    
    def set_cpu_affinity(self, process_id: Optional[int] = None, for_training: bool = True):
        """Set CPU affinity for a process"""
        try:
            if process_id is None:
                process_id = os.getpid()
            
            p = psutil.Process(process_id)
            cores = self.training_cores if for_training else self.trading_cores
            p.cpu_affinity(cores)
            
            self.logger.info(f"Set CPU affinity for PID {process_id} to cores {cores}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set CPU affinity: {e}")
            return False
    
    def get_optimal_batch_size(self, model_complexity: str = "medium") -> int:
        """Calculate optimal batch size based on available memory"""
        resources = self.get_system_resources()
        
        # Adjust batch size based on memory availability
        if resources.memory_available_gb > 8:
            batch_sizes = {"low": 256, "medium": 128, "high": 64}
        elif resources.memory_available_gb > 4:
            batch_sizes = {"low": 128, "medium": 64, "high": 32}
        else:
            batch_sizes = {"low": 64, "medium": 32, "high": 16}
        
        return batch_sizes.get(model_complexity, 64)
    
    def enforce_limits(self, timeout_seconds: int = 300):
        """Decorator to enforce resource limits on training functions"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Check resources before starting
                if not self.is_safe_for_training():
                    raise ResourceError("System resources insufficient for training")
                
                # Set timeout
                signal.signal(signal.SIGALRM, self._timeout_handler)
                signal.alarm(timeout_seconds)
                
                try:
                    # Set CPU affinity for training
                    self.set_cpu_affinity(for_training=True)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Clear alarm
                    signal.alarm(0)
                    
                    return result
                except TimeoutError:
                    self.logger.error(f"Training exceeded {timeout_seconds} second timeout")
                    raise
                finally:
                    signal.alarm(0)
            return wrapper
        return decorator
    
    def _timeout_handler(self, signum, frame):
        raise TimeoutError("Training process timed out")


class ResourceError(Exception):
    pass
