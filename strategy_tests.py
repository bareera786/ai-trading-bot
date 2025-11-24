#!/usr/bin/env python3
"""
SPECIALIZED STRATEGY TESTS FOR AI TRADING BOT
Tests: QFM, CRT, ICT, SMC Strategies and ML Models
"""

import requests
import json
import time

class StrategyTests:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_qfm_strategy(self):
        """Test Quantum Fusion Momentum Strategy"""
        print("\n⚡ QFM STRATEGY TESTS")
        print("-" * 40)
        
        endpoints = [
            "/api/qfm/status",
            "/api/qfm/signals",
            "/api/qfm/performance",
            "/api/qfm/analytics"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                status = "✅ ACTIVE" if response.status_code == 200 else "⚠️ NOT FOUND"
                print(f"  {status} {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"     Response: {json.dumps(data, indent=2)[:200]}...")
            except Exception as e:
                print(f"  ❌ ERROR {endpoint} - {e}")

    def test_crt_strategy(self):
        """Test Composite Reasoning Technology Strategy"""
        print("\n🎯 CRT STRATEGY TESTS")
        print("-" * 40)
        
        endpoints = [
            "/api/crt/status",
            "/api/crt/signals", 
            "/api/crt/performance"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                status = "✅ ACTIVE" if response.status_code == 200 else "⚠️ NOT FOUND"
                print(f"  {status} {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"  ❌ ERROR {endpoint} - {e}")

    def test_ml_models(self):
        """Test ML Model endpoints"""
        print("\n🧠 ML MODEL TESTS")
        print("-" * 40)
        
        endpoints = [
            "/api/ml/status",
            "/api/ml/models",
            "/api/ml/predictions",
            "/api/ml/performance"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                status = "✅ ACTIVE" if response.status_code == 200 else "⚠️ NOT FOUND"
                print(f"  {status} {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"  ❌ ERROR {endpoint} - {e}")

    def test_trading_operations(self):
        """Test trading operations and execution"""
        print("\n💰 TRADING OPERATIONS TESTS")
        print("-" * 40)
        
        endpoints = [
            "/api/trading/status",
            "/api/trading/positions",
            "/api/trading/orders",
            "/api/trading/history"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                status = "✅ ACTIVE" if response.status_code == 200 else "⚠️ NOT FOUND"
                print(f"  {status} {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"  ❌ ERROR {endpoint} - {e}")

    def run_all_strategy_tests(self):
        """Run all strategy tests"""
        print("🚀 STARTING STRATEGY-SPECIFIC TEST SUITE")
        print("=" * 60)
        
        # Login first
        try:
            self.session.post(
                f"{self.base_url}/login",
                json={"username": "admin", "password": "admin123"}
            )
            print("✅ Logged in as admin")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return
        
        self.test_qfm_strategy()
        self.test_crt_strategy() 
        self.test_ml_models()
        self.test_trading_operations()
        
        print("\n" + "=" * 60)
        print("🎯 STRATEGY TESTING COMPLETE")

if __name__ == "__main__":
    base_url = "http://localhost:5000"
    print(f"🧪 Testing Strategies at: {base_url}")
    
    strategy_tests = StrategyTests(base_url)
    strategy_tests.run_all_strategy_tests()
