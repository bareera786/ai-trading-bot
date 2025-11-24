#!/usr/bin/env python3
"""
PERFORMANCE BENCHMARK TESTS FOR AI TRADING BOT
Tests: Response times, concurrent users, system load
"""

import requests
import time
import threading
import statistics
import json

class PerformanceBenchmark:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
        
    def benchmark_endpoint(self, endpoint, num_requests=10):
        """Benchmark a single endpoint"""
        times = []
        
        for i in range(num_requests):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                
                if response.status_code == 200:
                    times.append((end_time - start_time) * 1000)  # Convert to ms
            except Exception as e:
                print(f"  ❌ Error benchmarking {endpoint}: {e}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"  📊 {endpoint}:")
            print(f"     Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            
            self.results[endpoint] = {
                "avg_ms": avg_time,
                "min_ms": min_time, 
                "max_ms": max_time,
                "requests": len(times)
            }
        else:
            print(f"  ❌ No successful requests for {endpoint}")

    def test_concurrent_users(self, num_users=5):
        """Test concurrent user access"""
        print(f"\n👥 CONCURRENT USER TEST ({num_users} users)")
        print("-" * 40)
        
        results = []
        
        def user_simulation(user_id):
            start_time = time.time()
            session = requests.Session()
            
            try:
                # Login
                session.post(f"{self.base_url}/login", 
                           json={"username": "admin", "password": "admin123"})
                
                # Access dashboard
                session.get(f"{self.base_url}/dashboard")
                
                # Access strategies
                session.get(f"{self.base_url}/api/strategies")
                
                end_time = time.time()
                results.append((end_time - start_time) * 1000)
                
                print(f"  ✅ User {user_id}: {results[-1]:.2f}ms")
            except Exception as e:
                print(f"  ❌ User {user_id} failed: {e}")

        threads = []
        for i in range(num_users):
            thread = threading.Thread(target=user_simulation, args=(i+1,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if results:
            avg_time = statistics.mean(results)
            print(f"  📈 Average concurrent user time: {avg_time:.2f}ms")

    def run_benchmarks(self):
        """Run all performance benchmarks"""
        print("🚀 STARTING PERFORMANCE BENCHMARK TESTS")
        print("=" * 60)
        
        endpoints = [
            "/",
            "/dashboard", 
            "/api/strategies",
            "/api/performance",
            "/api/health"
        ]
        
        print("\n⏱️  RESPONSE TIME BENCHMARKS (10 requests each)")
        print("-" * 40)
        
        for endpoint in endpoints:
            self.benchmark_endpoint(endpoint)
        
        self.test_concurrent_users(5)
        
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        for endpoint, metrics in self.results.items():
            print(f"🎯 {endpoint}: {metrics['avg_ms']:.2f}ms avg response time")
        
        # Save results
        with open("performance_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print("💾 Performance results saved to: performance_results.json")

if __name__ == "__main__":
    base_url = "http://localhost:5000"
    print(f"⏱️  Performance Testing: {base_url}")
    
    benchmark = PerformanceBenchmark(base_url)
    benchmark.run_benchmarks()
