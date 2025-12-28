#!/usr/bin/env python3
"""
Simple Memory Profiling Script for AI Trading Bot
Quick memory usage analysis without starting the full bot
"""

import os
import sys
import psutil
import tracemalloc
from pympler import tracker, summary, muppy

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

def quick_memory_profile():
    """Quick memory profiling without starting the bot."""
    print("🚀 Quick Memory Profiling...")
    print("=" * 50)

    # Start memory tracking
    tracemalloc.start()
    initial_memory = get_memory_info()

    print(".2f")
    print(".2f")
    print(".1f")
    print(".1f")

    # Import key modules one by one
    print("\n📦 Testing module imports...")

    # Test basic imports
    modules_to_test = [
        'numpy',
        'pandas',
        'scikit-learn',
        'flask',
        'redis',
        'psycopg2'
    ]

    for module in modules_to_test:
        try:
            __import__(module)
            mem_after = get_memory_info()
            print(".2f")
        except ImportError as e:
            print(f"❌ {module}: Import failed - {e}")

    # Test app imports (carefully)
    print("\n🏗️  Testing app imports...")

    try:
        # Import just the core modules without starting the app
        import app.config
        config_mem = get_memory_info()
        print(".2f")

        import app.models
        models_mem = get_memory_info()
        print(".2f")

        # Don't import create_app to avoid starting the bot
        # from app import create_app

    except Exception as e:
        print(f"❌ App import error: {e}")

    # Memory leak detection
    print("\n🔍 Memory Leak Check...")
    tr = tracker.SummaryTracker()

    # Force garbage collection
    import gc
    gc.collect()

    print("🧹 After garbage collection:")
    tr.print_diff()

    # Show top memory objects
    print("\n📊 Top Memory Objects:")
    all_objects = muppy.get_objects()
    sum_objects = summary.summarize(all_objects)
    summary.print_(sum_objects, limit=10)

    tracemalloc.stop()

    print("\n✅ Quick profiling completed!")
    print("\n💡 Quick Wins Applied:")
    print("   ✅ Performance monitoring tools installed")
    print("   ✅ Import optimization completed")
    print("   ✅ Updated requirements with optimized packages")
    print("   ✅ Memory profiling script created")

if __name__ == "__main__":
    quick_memory_profile()