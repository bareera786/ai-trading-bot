#!/usr/bin/env python3
"""
Comprehensive Dashboard Endpoint Testing Script
Tests all major dashboard features after deployment
"""

import requests
import time
import json
import sys
import subprocess
import signal
import os
from typing import Dict, List, Tuple

class DashboardTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.server_process = None

    def start_server(self) -> bool:
        """Start the Flask server"""
        try:
            print("Starting Flask server...")
            # Use the virtual environment python
            venv_python = "/Users/tahir/Desktop/ai-bot/.venv/bin/python"
            cmd = [venv_python, "-m", "flask", "run"]

            self.server_process = subprocess.Popen(
                cmd,
                cwd="/Users/tahir/Desktop/ai-bot",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            # Wait for server to start
            time.sleep(5)

            # Check if server is running
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    return True
                else:
                    print(f"❌ Server health check failed: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"❌ Server not responding: {e}")
                return False

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the Flask server"""
        if self.server_process:
            try:
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                self.server_process.wait(timeout=10)
                print("✅ Server stopped")
            except Exception as e:
                print(f"❌ Error stopping server: {e}")

    def login(self, username: str = "admin", password: str = "admin123") -> bool:
        """Login and establish session"""
        try:
            login_data = {"username": username, "password": password}
            response = self.session.post(f"{self.base_url}/login", json=login_data)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ Login successful for user: {username}")
                    return True
                else:
                    print(f"❌ Login failed: {data.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Login request failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None,
                     expected_status: int = 200, description: str = "") -> Tuple[bool, Dict]:
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"

            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": response.status_code == expected_status,
                "description": description
            }

            if response.status_code != expected_status:
                result["error"] = f"Expected {expected_status}, got {response.status_code}"
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_text"] = response.text[:200]

            return result["success"], result

        except requests.exceptions.Timeout:
            return False, {
                "endpoint": endpoint,
                "method": method,
                "error": "Request timeout",
                "success": False,
                "description": description
            }
        except Exception as e:
            return False, {
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "success": False,
                "description": description
            }

    def test_all_endpoints(self) -> Dict:
        """Test all major dashboard endpoints"""
        print("\n🧪 Testing all dashboard endpoints...")

        # Define all endpoints to test
        endpoints_to_test = [
            # Core Dashboard
            ("/api/dashboard", "GET", None, "Main dashboard data"),
            ("/api/status", "GET", None, "System status"),
            ("/api/health", "GET", None, "Health check"),

            # Authentication & User Management
            ("/api/current_user", "GET", None, "Current user info"),
            ("/api/users", "GET", None, "List users"),

            # Market Data
            ("/api/market_data", "GET", None, "Market data"),
            ("/api/realtime/market_data", "GET", None, "Real-time market data"),

            # Symbols Management
            ("/api/symbols", "GET", None, "Symbols list"),

            # Trading
            ("/api/spot/toggle", "POST", {"enabled": False}, "Spot trading toggle"),
            ("/api/futures/toggle", "POST", {"enabled": False}, "Futures trading toggle"),
            ("/api/toggle_trading", "POST", {"enabled": False}, "General trading toggle"),

            # Portfolio & Performance
            ("/api/portfolio", "GET", None, "Portfolio data"),
            ("/api/realtime/portfolio", "GET", None, "Real-time portfolio"),
            ("/api/realtime/pnl", "GET", None, "Real-time PnL"),
            ("/api/performance", "GET", None, "Performance data"),
            ("/api/dashboard_performance", "GET", None, "Dashboard performance"),

            # Strategies
            ("/api/strategies", "GET", None, "Strategies list"),

            # Analytics & Telemetry
            ("/api/ml_telemetry", "GET", None, "ML telemetry"),
            ("/api/qfm", "GET", None, "QFM analytics"),
            ("/api/crt_data", "GET", None, "CRT signals"),

            # Backtesting
            ("/api/backtests", "GET", None, "Backtests list"),

            # Trade History
            ("/api/trades", "GET", None, "Trade history"),

            # Safety & Risk
            ("/api/safety_status", "GET", None, "Safety status"),
            ("/api/real_trading_status", "GET", None, "Real trading status"),

            # API Keys
            ("/api/binance/credentials", "GET", None, "Binance credentials"),

            # Journal
            ("/api/journal", "GET", None, "Trading journal"),

            # Persistence
            ("/api/persistence/status", "GET", None, "Persistence status"),
        ]

        results = {
            "total_tests": len(endpoints_to_test),
            "passed": 0,
            "failed": 0,
            "details": []
        }

        for endpoint, method, data, description in endpoints_to_test:
            print(f"Testing {endpoint} ({method}) - {description}")
            success, result = self.test_endpoint(endpoint, method, data, description=description)
            results["details"].append(result)

            if success:
                results["passed"] += 1
                print(f"  ✅ PASS")
            else:
                results["failed"] += 1
                print(f"  ❌ FAIL - {result.get('error', 'Unknown error')}")

        return results

    def run_comprehensive_test(self) -> Dict:
        """Run the complete test suite"""
        print("🚀 Starting comprehensive dashboard testing...")

        # Start server
        if not self.start_server():
            return {"error": "Failed to start server"}

        try:
            # Login
            if not self.login():
                return {"error": "Failed to login"}

            # Test all endpoints
            results = self.test_all_endpoints()

            success_rate = (results['passed'] / results['total_tests']) * 100
            print("\n📊 Test Results Summary:")
            print(f"Total tests: {results['total_tests']}")
            print(f"Passed: {results['passed']}")
            print(f"Failed: {results['failed']}")
            print(f"Success rate: {success_rate:.1f}%")

            if results['failed'] > 0:
                print("\n❌ Failed endpoints:")
                for result in results['details']:
                    if not result['success']:
                        print(f"  - {result['endpoint']} ({result['method']}) - {result.get('error', 'Unknown')}")

            return results

        finally:
            self.stop_server()

def main():
    tester = DashboardTester()
    results = tester.run_comprehensive_test()

    if "error" in results:
        print(f"\n💥 Test suite failed: {results['error']}")
        sys.exit(1)
    else:
        success_rate = (results['passed'] / results['total_tests']) * 100
        if success_rate >= 95:
            print("\n🎉 All dashboard features are working!")
            sys.exit(0)
        else:
            print(f"\n⚠️  {results['failed']} endpoints need attention")
            sys.exit(1)

if __name__ == "__main__":
    main()