#!/usr/bin/env python3
"""
Performance monitoring for trading bot enhancement
"""
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

class TradingBotMonitor:
    """Monitor trading bot performance metrics"""
    
    def __init__(self, log_file="performance.log"):
        self.start_time = time.time()
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'execution_times': {},
            'error_count': 0,
            'trade_count': 0,
            'success_rate': 0.0
        }
        self.log_file = log_file
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        return {
            'operation': operation,
            'start_time': time.time()
        }
    
    def end_timer(self, timer: Dict) -> float:
        """End timing and record duration"""
        duration = time.time() - timer['start_time']
        operation = timer['operation']
        
        # Record in metrics
        if operation not in self.metrics['execution_times']:
            self.metrics['execution_times'][operation] = []
        
        self.metrics['execution_times'][operation].append(duration)
        
        # Log if operation is slow
        if duration > 1.0:  # More than 1 second
            self.logger.warning(f"Slow operation: {operation} took {duration:.2f}s")
        
        return duration
    
    def record_trade(self, success: bool, details: Optional[Dict] = None):
        """Record a trade execution"""
        self.metrics['trade_count'] += 1
        
        # Calculate success rate
        if success:
            current_success = self.metrics.get('successful_trades', 0) + 1
            self.metrics['successful_trades'] = current_success
            self.metrics['success_rate'] = current_success / self.metrics['trade_count']
        else:
            self.metrics['error_count'] += 1
        
        # Log trade
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'details': details or {},
            'trade_count': self.metrics['trade_count'],
            'success_rate': self.metrics['success_rate']
        }
        
        self.logger.info(f"Trade recorded: {json.dumps(log_entry)}")
    
    def capture_system_metrics(self):
        """Capture current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        self.metrics['cpu_usage'].append(cpu_percent)
        self.metrics['memory_usage'].append(memory_info.percent)
        
        # Alert if resources are high
        if cpu_percent > 80:
            self.logger.warning(f"High CPU usage: {cpu_percent}%")
        if memory_info.percent > 80:
            self.logger.warning(f"High memory usage: {memory_info.percent}%")
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_info.percent,
            'memory_available_gb': memory_info.available / (1024**3)
        }
    
    def generate_performance_report(self) -> Dict:
        """Generate a comprehensive performance report"""
        uptime = time.time() - self.start_time
        
        # Calculate averages
        avg_cpu = sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0
        avg_memory = sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0
        
        # Find slowest operations
        slow_operations = {}
        for op, times in self.metrics['execution_times'].items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > 0.1:  # Operations taking >100ms
                    slow_operations[op] = {
                        'avg_time': avg_time,
                        'max_time': max(times),
                        'count': len(times)
                    }
        
        report = {
            'uptime_hours': uptime / 3600,
            'trade_count': self.metrics['trade_count'],
            'success_rate': self.metrics['success_rate'],
            'error_count': self.metrics['error_count'],
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'slow_operations': slow_operations,
            'recommendations': self._generate_recommendations()
        }
        
        # Save report
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Performance report saved to {report_file}")
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Check success rate
        if self.metrics['trade_count'] > 10 and self.metrics['success_rate'] < 0.5:
            recommendations.append("Low success rate (<50%). Review trading strategy.")
        
        # Check error count
        if self.metrics['error_count'] > self.metrics['trade_count'] * 0.1:  # >10% errors
            recommendations.append("High error rate. Improve error handling and retry logic.")
        
        # Check for slow operations
        for op, data in self.metrics['execution_times'].items():
            if data and (sum(data) / len(data)) > 0.5:  # Avg >500ms
                recommendations.append(f"Optimize slow operation: {op}")
        
        # System resource recommendations
        if self.metrics['cpu_usage'] and sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']) > 70:
            recommendations.append("High CPU usage. Consider optimizing algorithms or scaling resources.")
        
        if not recommendations:
            recommendations.append("Performance is good. Continue monitoring.")
        
        return recommendations
    
    def integrate_with_existing_bot(self, bot_instance):
        """Integrate monitoring with existing bot"""
        # Monkey patch bot methods to add monitoring
        original_methods = {}
        
        def wrap_method(method_name):
            original_method = getattr(bot_instance, method_name, None)
            if original_method and callable(original_method):
                original_methods[method_name] = original_method
                
                def monitored_method(*args, **kwargs):
                    timer = self.start_timer(method_name)
                    try:
                        result = original_method(*args, **kwargs)
                        self.end_timer(timer)
                        return result
                    except Exception as e:
                        self.metrics['error_count'] += 1
                        self.logger.error(f"Error in {method_name}: {e}")
                        raise
                
                setattr(bot_instance, method_name, monitored_method)
        
        # Wrap common trading bot methods
        methods_to_wrap = ['execute_trade', 'analyze_market', 'calculate_signals', 'run_strategy']
        for method in methods_to_wrap:
            wrap_method(method)
        
        self.logger.info(f"Monitoring integrated with {len(methods_to_wrap)} methods")
        return original_methods

# Quick integration example
if __name__ == "__main__":
    print("📊 Trading Bot Performance Monitor")
    print("=" * 50)
    
    monitor = TradingBotMonitor()
    
    # Example usage
    print("1. Starting monitor...")
    monitor.capture_system_metrics()
    
    print("2. Recording sample trade...")
    monitor.record_trade(True, {"symbol": "BTCUSDT", "amount": 0.01})
    
    print("3. Generating report...")
    report = monitor.generate_performance_report()
    
    print(f"\n✅ Monitor ready!")
    print(f"   Log file: {monitor.log_file}")
    print(f"   Trade count: {report['trade_count']}")
    print(f"   Recommendations: {len(report['recommendations'])}")
    
    print("\n💡 To integrate with your bot:")
    print("   from performance_monitor import TradingBotMonitor")
    print("   monitor = TradingBotMonitor()")
    print("   monitor.integrate_with_existing_bot(your_bot_instance)")
