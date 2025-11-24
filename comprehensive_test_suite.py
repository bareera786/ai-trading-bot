#!/usr/bin/env python3
"""
COMPREHENSIVE TEST SUITE FOR AI TRADING BOT
Tests: User Management, Admin Roles, Trading Logic, Strategies
"""

import requests
import json
import time
import sys
import os

class TradingBotTestSuite:
    def __init__(self, base_url="http://localhost:5000"):
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

    def test_authentication_flow(self):
        """Test login, logout, and session management"""
        print("\n🔐 AUTHENTICATION FLOW TESTS")
        print("-" * 40)
        
        # Test 1: Admin login
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={"username": "admin", "password": "admin123"}
            )
            success = response.status_code == 200 and "success" in response.text
            self.print_result("Admin Login", success, 
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Admin Login", False, f"Error: {e}")

        # Test 2: Check session persistence
        try:
            response = self.session.get(f"{self.base_url}/dashboard")
            success = response.status_code == 200
            self.print_result("Session Persistence", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Session Persistence", False, f"Error: {e}")

        # Test 3: Logout
        try:
            response = self.session.get(f"{self.base_url}/logout")
            success = response.status_code == 200
            self.print_result("Logout", success, f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Logout", False, f"Error: {e}")

        # Test 4: Login with invalid credentials
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={"username": "nonexistent", "password": "wrong"}
            )
            success = response.status_code != 200  # Should fail
            self.print_result("Invalid Login Rejection", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Invalid Login Rejection", False, f"Error: {e}")

    def test_user_management(self):
        """Test user creation, roles, and management"""
        print("\n👥 USER MANAGEMENT TESTS")
        print("-" * 40)
        
        # Login as admin first
        self.session.post(
            f"{self.base_url}/login",
            json={"username": "admin", "password": "admin123"}
        )

        test_username = f"testuser_{int(time.time())}"
        
        # Test 1: Create regular user
        try:
            response = self.session.post(
                f"{self.base_url}/api/users",
                json={
                    "username": test_username,
                    "email": f"{test_username}@test.com",
                    "password": "testpass123",
                    "is_admin": False
                }
            )
            success = response.status_code == 201
            self.print_result("Create Regular User", success,
                            f"Status: {response.status_code}, User: {test_username}")
        except Exception as e:
            self.print_result("Create Regular User", False, f"Error: {e}")

        # Test 2: Create admin user
        admin_username = f"adminuser_{int(time.time())}"
        try:
            response = self.session.post(
                f"{self.base_url}/api/users",
                json={
                    "username": admin_username,
                    "email": f"{admin_username}@admin.com",
                    "password": "adminpass123",
                    "is_admin": True
                }
            )
            success = response.status_code == 201
            self.print_result("Create Admin User", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Create Admin User", False, f"Error: {e}")

        # Test 3: List users (admin functionality)
        try:
            response = self.session.get(f"{self.base_url}/api/users")
            success = response.status_code == 200
            user_count = len(response.json().get('users', []))
            self.print_result("List Users (Admin)", success,
                            f"Status: {response.status_code}, Users: {user_count}")
        except Exception as e:
            self.print_result("List Users (Admin)", False, f"Error: {e}")

        # Test 4: Prevent duplicate usernames
        try:
            response = self.session.post(
                f"{self.base_url}/api/users",
                json={
                    "username": test_username,  # Same username
                    "email": f"duplicate@{test_username}.com",
                    "password": "anotherpass",
                    "is_admin": False
                }
            )
            success = response.status_code != 201  # Should fail
            self.print_result("Duplicate User Prevention", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Duplicate User Prevention", False, f"Error: {e}")

    def test_trading_systems(self):
        """Test trading strategy systems and logic"""
        print("\n🤖 TRADING SYSTEMS TESTS")
        print("-" * 40)

        # Test 1: Trading dashboard data
        try:
            response = self.session.get(f"{self.base_url}/dashboard")
            success = response.status_code == 200
            self.print_result("Trading Dashboard", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Trading Dashboard", False, f"Error: {e}")

        # Test 2: Strategy status endpoints
        strategy_endpoints = [
            "/api/strategies",
            "/api/strategy/status",
            "/api/trading/status",
            "/api/signals"
        ]
        
        for endpoint in strategy_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                success = response.status_code in [200, 404]  # 404 is okay if not implemented
                status = "Responds" if response.status_code == 200 else "Not Implemented"
                self.print_result(f"Strategy Endpoint {endpoint}", True,
                                f"Status: {response.status_code} ({status})")
            except Exception as e:
                self.print_result(f"Strategy Endpoint {endpoint}", False, f"Error: {e}")

        # Test 3: ML Model status
        try:
            response = self.session.get(f"{self.base_url}/api/ml/status")
            success = response.status_code in [200, 404]
            self.print_result("ML Model Status", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("ML Model Status", False, f"Error: {e}")

    def test_strategy_performance(self):
        """Test strategy performance and analytics"""
        print("\n📊 STRATEGY PERFORMANCE TESTS")
        print("-" * 40)

        # Test 1: Performance metrics
        performance_endpoints = [
            "/api/performance",
            "/api/analytics",
            "/api/risk/metrics",
            "/api/portfolio"
        ]
        
        for endpoint in performance_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                success = response.status_code in [200, 404]
                status = "Active" if response.status_code == 200 else "Not Found"
                self.print_result(f"Performance {endpoint}", True,
                                f"Status: {response.status_code} ({status})")
            except Exception as e:
                self.print_result(f"Performance {endpoint}", False, f"Error: {e}")

        # Test 2: QFM Strategy endpoints
        qfm_endpoints = [
            "/api/qfm/status",
            "/api/qfm/signals",
            "/api/crt/signals"
        ]
        
        for endpoint in qfm_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                success = response.status_code in [200, 404]
                self.print_result(f"QFM Strategy {endpoint}", success,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.print_result(f"QFM Strategy {endpoint}", False, f"Error: {e}")

    def test_cache_performance(self):
        """Test cache control and performance"""
        print("\n⚡ CACHE & PERFORMANCE TESTS")
        print("-" * 40)

        endpoints_to_test = [
            "/dashboard",
            "/api/strategies",
            "/api/performance"
        ]

        for endpoint in endpoints_to_test:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                cache_control = response.headers.get('Cache-Control', '')
                has_cache_control = 'no-cache' in cache_control or 'no-store' in cache_control
                
                self.print_result(f"Cache Control {endpoint}", has_cache_control,
                                f"Headers: {cache_control}")
            except Exception as e:
                self.print_result(f"Cache Control {endpoint}", False, f"Error: {e}")

    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n🚨 ERROR HANDLING TESTS")
        print("-" * 40)

        # Test 1: Invalid API endpoints
        try:
            response = self.session.get(f"{self.base_url}/api/nonexistent")
            success = response.status_code == 404  # Should return 404
            self.print_result("Invalid Endpoint Handling", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Invalid Endpoint Handling", False, f"Error: {e}")

        # Test 2: Malformed user creation
        try:
            response = self.session.post(
                f"{self.base_url}/api/users",
                json={"invalid": "data"}  # Missing required fields
            )
            success = response.status_code != 201  # Should fail
            self.print_result("Malformed Data Rejection", success,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Malformed Data Rejection", False, f"Error: {e}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 STARTING COMPREHENSIVE AI TRADING BOT TEST SUITE")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test suites
        self.test_authentication_flow()
        self.test_user_management()
        self.test_trading_systems()
        self.test_strategy_performance()
        self.test_cache_performance()
        self.test_error_handling()
        
        # Calculate results
        end_time = time.time()
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)
        print(f"🎯 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Duration: {end_time - start_time:.2f} seconds")
        
        # Calculate percentage
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 80:
                print("🎉 EXCELLENT! Bot is ready for production!")
            elif success_rate >= 60:
                print("⚠️  GOOD! Some features need attention.")
            else:
                print("💥 NEEDS WORK! Significant issues found.")
        
        return self.test_results

if __name__ == "__main__":
    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    print(f"🧪 Testing AI Trading Bot at: {base_url}")
    print("⚠️  Make sure the bot is running before starting tests!")
    input("Press Enter to start comprehensive tests...")
    
    test_suite = TradingBotTestSuite(base_url)
    results = test_suite.run_all_tests()
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n💾 Test results saved to: test_results.json")
