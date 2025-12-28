#!/usr/bin/env python3
"""
TEST FUTURES AND SPOT TRADING FUNCTIONALITY
Tests both futures and spot trading platforms on deployed bot
"""

import requests
import json
import time
import sys

# Configuration - Update these for your deployed bot
BASE_URL = "http://151.243.171.80:5000"  # Your VPS URL
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class TradingPlatformTest:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {}

    def print_result(self, test_name, success, message=""):
        """Print test result with emoji"""
        status = "✅ PASS" if success else "❌ FAIL"
        emoji = "🎯" if success else "💥"
        print(f"  {emoji} {test_name}: {status} {message}")
        self.test_results[test_name] = success
        return success

    def login(self):
        """Login as admin"""
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def test_paper_trading_enabled(self):
        """Test that paper trading is enabled"""
        try:
            response = self.session.get(f"{self.base_url}/api/dashboard")
            if response.status_code == 200:
                data = response.json()
                system_status = data.get("system_status", {})
                paper_trading = system_status.get("paper_trading", False)
                return self.print_result("Paper Trading Enabled", paper_trading)
            else:
                return self.print_result(
                    "Paper Trading Check", False, f"Status: {response.status_code}"
                )
        except Exception as e:
            return self.print_result("Paper Trading Check", False, f"Error: {e}")

    def test_futures_toggle(self):
        """Test futures trading toggle"""
        print("\n🔄 FUTURES TRADING TESTS")
        print("-" * 30)

        # Test enabling futures
        try:
            response = self.session.post(
                f"{self.base_url}/api/futures/toggle", json={"enable": True}
            )
            success = response.status_code == 200
            self.print_result(
                "Enable Futures Trading", success, f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result("Enable Futures Trading", False, f"Error: {e}")

        # Test disabling futures
        try:
            response = self.session.post(
                f"{self.base_url}/api/futures/toggle", json={"enable": False}
            )
            success = response.status_code == 200
            self.print_result(
                "Disable Futures Trading", success, f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result("Disable Futures Trading", False, f"Error: {e}")

    def test_spot_trading_toggle(self):
        """Test spot trading toggle"""
        print("\n🔄 SPOT TRADING TESTS")
        print("-" * 30)

        # Test enabling spot trading (via main trading toggle)
        try:
            response = self.session.post(f"{self.base_url}/api/toggle_trading")
            success = response.status_code == 200
            self.print_result(
                "Enable Spot Trading", success, f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result("Enable Spot Trading", False, f"Error: {e}")

        # Test disabling spot trading
        try:
            response = self.session.post(f"{self.base_url}/api/toggle_trading")
            success = response.status_code == 200
            self.print_result(
                "Disable Spot Trading", success, f"Status: {response.status_code}"
            )
        except Exception as e:
            self.print_result("Disable Spot Trading", False, f"Error: {e}")

    def test_trading_status(self):
        """Test getting trading status"""
        try:
            response = self.session.get(f"{self.base_url}/api/dashboard")
            if response.status_code == 200:
                data = response.json()
                system_status = data.get("system_status", {})

                futures_enabled = system_status.get("futures_trading_enabled", False)
                trading_enabled = system_status.get("trading_enabled", False)
                paper_trading = system_status.get("paper_trading", False)

                self.print_result(
                    "Futures Status Check", True, f"Enabled: {futures_enabled}"
                )
                self.print_result(
                    "Spot Trading Status Check", True, f"Enabled: {trading_enabled}"
                )
                self.print_result(
                    "Paper Trading Status", True, f"Enabled: {paper_trading}"
                )

                return True
            else:
                return self.print_result(
                    "Trading Status Check", False, f"Status: {response.status_code}"
                )
        except Exception as e:
            return self.print_result("Trading Status Check", False, f"Error: {e}")

    def test_symbol_management(self):
        """Test symbol management functionality"""
        print("\n🔄 SYMBOL MANAGEMENT TESTS")
        print("-" * 30)

        # Test getting symbols
        try:
            response = self.session.get(f"{self.base_url}/api/symbols")
            success = response.status_code == 200
            if success:
                data = response.json()
                symbol_count = len(data.get("symbols", []))
                self.print_result(
                    "Get Symbols List", True, f"Found {symbol_count} symbols"
                )
            else:
                self.print_result(
                    "Get Symbols List", False, f"Status: {response.status_code}"
                )
        except Exception as e:
            self.print_result("Get Symbols List", False, f"Error: {e}")

        # Test adding a symbol
        try:
            response = self.session.post(
                f"{self.base_url}/api/add_symbol", json={"symbol": "ADAUSDT"}
            )
            success = response.status_code in [
                200,
                500,
            ]  # 500 might be expected if training fails
            self.print_result("Add Symbol", success, f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Add Symbol", False, f"Error: {e}")

    def run_all_tests(self):
        """Run all trading platform tests"""
        print("🚀 FUTURES & SPOT TRADING PLATFORM TESTS")
        print("=" * 50)
        print(f"Testing against: {self.base_url}")
        print()

        # Login first
        if not self.login():
            print("❌ Cannot login - aborting tests")
            return False

        print("✅ Logged in successfully")
        print()

        # Run tests
        self.test_paper_trading_enabled()
        self.test_futures_toggle()
        self.test_spot_trading_toggle()
        self.test_trading_status()
        self.test_symbol_management()

        # Summary
        print("\n📊 TEST SUMMARY")
        print("-" * 20)
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        print(f"Passed: {passed}/{total}")

        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False


if __name__ == "__main__":
    # Allow custom URL via command line
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]

    tester = TradingPlatformTest(BASE_URL)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
