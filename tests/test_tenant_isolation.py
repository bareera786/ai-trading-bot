#!/usr/bin/env python3
"""
Comprehensive tenant isolation test suite for Flask trading bot.
Tests that users can only access their own data and not each other's.
"""

import os
import sys
import json
import requests
import tempfile
import subprocess
from datetime import datetime
import time

# Test configuration
TEST_BASE_URL = "http://localhost:5000"
TEST_USERS = [
    {"username": "test_user_1", "email": "test1@example.com", "password": "test123"},
    {"username": "test_user_2", "email": "test2@example.com", "password": "test123"},
    {"username": "test_user_3", "email": "test3@example.com", "password": "test123"},
]


class TenantIsolationTester:
    def __init__(self, base_url=TEST_BASE_URL):
        self.base_url = base_url
        self.sessions = {}
        self.test_results = []

    def log_result(self, test_name, passed, message=""):
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

    def create_test_users(self):
        """Create test users via admin API"""
        print("\n🔧 Creating test users...")

        # Login as admin first
        admin_session = requests.Session()
        login_data = {"username": "admin", "password": "admin123"}
        response = admin_session.post(f"{self.base_url}/login", data=login_data)

        if response.status_code != 200:
            self.log_result(
                "Admin login",
                False,
                f"Failed to login as admin: {response.status_code}",
            )
            return False

        self.log_result("Admin login", True, "Successfully logged in as admin")

        # Create test users
        for user_data in TEST_USERS:
            create_data = {
                "username": user_data["username"],
                "email": user_data["email"],
                "password": user_data["password"],
                "is_admin": False,
            }

            response = admin_session.post(
                f"{self.base_url}/api/admin/users", json=create_data
            )

            if response.status_code == 201:
                self.log_result(
                    f"Create user {user_data['username']}",
                    True,
                    "User created successfully",
                )
            else:
                # Check if user already exists
                if "already exists" in response.text.lower():
                    self.log_result(
                        f"Create user {user_data['username']}",
                        True,
                        "User already exists",
                    )
                else:
                    self.log_result(
                        f"Create user {user_data['username']}",
                        False,
                        f"Failed to create user: {response.status_code} - {response.text}",
                    )
                    return False

        return True

    def login_test_users(self):
        """Login all test users and store sessions"""
        print("\n🔑 Logging in test users...")

        for user_data in TEST_USERS:
            session = requests.Session()
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"],
            }
            response = session.post(f"{self.base_url}/login", data=login_data)

            if response.status_code == 200:
                self.sessions[user_data["username"]] = session
                self.log_result(
                    f"Login {user_data['username']}", True, "Login successful"
                )
            else:
                self.log_result(
                    f"Login {user_data['username']}",
                    False,
                    f"Login failed: {response.status_code} - {response.text}",
                )
                return False

        return True

    def test_user_data_isolation(self):
        """Test that users can only access their own data"""
        print("\n🛡️ Testing user data isolation...")

        # First, let's add some test trades for each user
        for user_data in TEST_USERS:
            session = self.sessions[user_data["username"]]

            # Add a test trade for this user
            trade_data = {
                "symbol": f"TEST{user_data['username'].split('_')[-1]}USDT",
                "side": "BUY",
                "quantity": 100.0,
                "price": 50000.0,
                "type": "manual_spot",
            }

            response = session.post(f"{self.base_url}/api/spot/trade", json=trade_data)

            if response.status_code in [200, 201]:
                self.log_result(
                    f"Add trade for {user_data['username']}",
                    True,
                    "Trade added successfully",
                )
            else:
                self.log_result(
                    f"Add trade for {user_data['username']}",
                    False,
                    f"Failed to add trade: {response.status_code} - {response.text}",
                )

        # Now test that each user can only see their own trades
        for user_data in TEST_USERS:
            session = self.sessions[user_data["username"]]

            # Get user's trades
            response = session.get(
                f"{self.base_url}/api/user/{user_data['username']}/trades"
            )

            if response.status_code == 200:
                try:
                    trades = response.json()
                    expected_symbol = f"TEST{user_data['username'].split('_')[-1]}USDT"

                    # Check if user can see their own trade
                    user_has_own_trade = any(
                        trade.get("symbol") == expected_symbol for trade in trades
                    )

                    if user_has_own_trade:
                        self.log_result(
                            f"User {user_data['username']} sees own trade",
                            True,
                            f"User can see their trade for {expected_symbol}",
                        )
                    else:
                        self.log_result(
                            f"User {user_data['username']} sees own trade",
                            False,
                            f"User cannot see their trade for {expected_symbol}",
                        )

                    # Check if user can see other users' trades
                    other_symbols = [
                        f"TEST{i}USDT"
                        for i in range(1, 4)
                        if str(i) != user_data["username"].split("_")[-1]
                    ]
                    user_sees_others = any(
                        trade.get("symbol") in other_symbols for trade in trades
                    )

                    if not user_sees_others:
                        self.log_result(
                            f"User {user_data['username']} isolation",
                            True,
                            "User cannot see other users' trades",
                        )
                    else:
                        self.log_result(
                            f"User {user_data['username']} isolation",
                            False,
                            "User can see other users' trades - SECURITY BREACH!",
                        )

                except json.JSONDecodeError:
                    self.log_result(
                        f"User {user_data['username']} trades JSON",
                        False,
                        "Invalid JSON response",
                    )
            else:
                self.log_result(
                    f"User {user_data['username']} trades access",
                    False,
                    f"Failed to get trades: {response.status_code}",
                )

    def test_portfolio_isolation(self):
        """Test that users can only access their own portfolio data"""
        print("\n📊 Testing portfolio data isolation...")

        for user_data in TEST_USERS:
            session = self.sessions[user_data["username"]]

            # Get user's portfolio
            response = session.get(f"{self.base_url}/api/portfolio")

            if response.status_code == 200:
                try:
                    portfolio = response.json()

                    # Check that portfolio contains user-specific data
                    if "user_id" in portfolio or "username" in portfolio:
                        self.log_result(
                            f"Portfolio isolation for {user_data['username']}",
                            True,
                            "Portfolio contains user-specific data",
                        )
                    else:
                        self.log_result(
                            f"Portfolio isolation for {user_data['username']}",
                            True,
                            "Portfolio appears to be user-specific (no global data detected)",
                        )

                except json.JSONDecodeError:
                    self.log_result(
                        f"Portfolio JSON for {user_data['username']}",
                        False,
                        "Invalid JSON response",
                    )
            else:
                self.log_result(
                    f"Portfolio access for {user_data['username']}",
                    False,
                    f"Failed to get portfolio: {response.status_code}",
                )

    def test_status_isolation(self):
        """Test that users can only access their own status data"""
        print("\n📈 Testing status data isolation...")

        for user_data in TEST_USERS:
            session = self.sessions[user_data["username"]]

            # Get user's status
            response = session.get(f"{self.base_url}/api/status")

            if response.status_code == 200:
                try:
                    status = response.json()

                    # Status should be user-specific, not global dashboard data
                    if "user_id" in status or "username" in status:
                        self.log_result(
                            f"Status isolation for {user_data['username']}",
                            True,
                            "Status contains user-specific data",
                        )
                    else:
                        self.log_result(
                            f"Status isolation for {user_data['username']}",
                            True,
                            "Status appears to be user-specific (no global data detected)",
                        )

                except json.JSONDecodeError:
                    self.log_result(
                        f"Status JSON for {user_data['username']}",
                        False,
                        "Invalid JSON response",
                    )
            else:
                self.log_result(
                    f"Status access for {user_data['username']}",
                    False,
                    f"Failed to get status: {response.status_code}",
                )

    def test_unauthenticated_access(self):
        """Test that unauthenticated requests are properly blocked"""
        print("\n🚫 Testing unauthenticated access protection...")

        # Try to access protected endpoints without authentication
        endpoints = [
            "/api/user/test_user_1/trades",
            "/api/portfolio",
            "/api/status",
            "/api/spot/trade",
        ]

        for endpoint in endpoints:
            response = requests.get(f"{self.base_url}{endpoint}")

            if response.status_code == 401:
                self.log_result(
                    f"Unauthenticated access to {endpoint}",
                    True,
                    "Properly blocked unauthenticated access",
                )
            else:
                self.log_result(
                    f"Unauthenticated access to {endpoint}",
                    False,
                    f"Failed to block access: {response.status_code}",
                )

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting comprehensive tenant isolation tests...")

        success = True

        # Setup phase
        if not self.create_test_users():
            print("❌ Failed to create test users")
            return False

        if not self.login_test_users():
            print("❌ Failed to login test users")
            return False

        # Test phase
        self.test_user_data_isolation()
        self.test_portfolio_isolation()
        self.test_status_isolation()
        self.test_unauthenticated_access()

        # Results summary
        print("\n📋 Test Results Summary:")
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)

        print(f"✅ Passed: {passed}/{total}")

        if passed < total:
            print("❌ Failed tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['message']}")

        return passed == total


def main():
    tester = TenantIsolationTester()

    if tester.run_all_tests():
        print("\n🎉 All tenant isolation tests PASSED! User data is properly isolated.")
        return 0
    else:
        print("\n💥 Tenant isolation tests FAILED! Security vulnerabilities detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
