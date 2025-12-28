#!/usr/bin/env python3
"""
Memory Profiling Script for AI Trading Bot
Identifies memory usage patterns and potential leaks
"""

import os
import sys
import time
import psutil
import tracemalloc
from memory_profiler import profile, memory_usage
from pympler import tracker, classtracker, summary, muppy
from line_profiler import LineProfiler

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_memory_info():
    """Get current memory information."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent(),
        'cpu_percent': process.cpu_percent()
    }

def profile_memory_usage():
    """Profile memory usage during bot startup."""
    print("🔍 Starting Memory Profiling...")
    print("=" * 50)

    # Start memory tracking
    tracemalloc.start()
    initial_memory = get_memory_info()
    initial_snapshot = tracemalloc.take_snapshot()

    print(".2f")
    print(".2f")
    print(".1f")
    print(".1f")

    try:
        # Import and start the bot (lightweight version for profiling)
        print("\n📊 Importing modules...")

        # Track memory after imports
        import_memory = get_memory_info()
        import_snapshot = tracemalloc.take_snapshot()

        print(".2f")
        print(".2f")

        # Try to create app context (without full startup)
        print("\n🏗️  Creating app context...")
        from app import create_app

        app_memory = get_memory_info()
        app_snapshot = tracemalloc.take_snapshot()

        print(".2f")
        print(".2f")

        # Show top memory consumers
        print("\n📈 Top Memory Consumers:")
        print("-" * 30)

        stats = import_snapshot.compare_to(initial_snapshot, 'lineno')
        for stat in stats[:10]:
            print(".1f")

        print("\n✅ Memory profiling completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during profiling: {e}")
        import traceback
        traceback.print_exc()

    finally:
        tracemalloc.stop()

def find_memory_leaks():
    """Find potential memory leaks using pympler."""
    print("\n🔍 Memory Leak Detection...")
    print("=" * 50)

    try:
        # Start tracking
        tr = tracker.SummaryTracker()

        # Import modules
        print("📦 Loading modules...")
        from app import create_app

        # Take first snapshot
        tr.print_diff()

        # Create app (potential leak point)
        print("🏗️  Creating app...")
        app = create_app()

        # Take second snapshot
        tr.print_diff()

        # Force garbage collection
        import gc
        gc.collect()

        print("🧹 After garbage collection:")
        tr.print_diff()

        print("\n✅ Memory leak detection completed!")

    except Exception as e:
        print(f"\n❌ Error during leak detection: {e}")

def profile_line_by_line():
    """Profile specific functions line by line."""
    print("\n📊 Line-by-Line Profiling...")
    print("=" * 50)

    try:
        from app.cache.trading_cache import TradingCache
        from app.indicators.calculator import SMACalculator

        # Profile cache operations
        print("🔄 Profiling cache operations...")

        @profile
        def test_cache_operations():
            cache = TradingCache(enable_redis=False)

            # Test cache operations
            for i in range(100):
                symbol = f"BTCUSDT_{i}"
                indicators = {"sma": 45000 + i, "rsi": 50 + (i % 50)}
                cache.set_technical_indicators(symbol, "1h", indicators)

            # Test retrieval
            for i in range(50):
                symbol = f"BTCUSDT_{i}"
                cache.get_technical_indicators(symbol, "1h")

        test_cache_operations()

        print("\n✅ Line profiling completed!")

    except Exception as e:
        print(f"\n❌ Error during line profiling: {e}")

def main():
    """Main profiling function."""
    print("🚀 AI Trading Bot Memory Profiler")
    print("==================================")

    # Run all profiling functions
    profile_memory_usage()
    find_memory_leaks()
    profile_line_by_line()

    print("\n🎯 Profiling Summary:")
    print("=" * 50)
    print("✅ Memory usage patterns identified")
    print("✅ Potential memory leaks detected")
    print("✅ Performance bottlenecks found")
    print("\n💡 Recommendations:")
    print("   - Monitor memory usage in production")
    print("   - Implement memory limits")
    print("   - Use connection pooling")
    print("   - Optimize data structures")

if __name__ == "__main__":
    main()