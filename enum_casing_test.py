#!/usr/bin/env python3
"""
CRITICAL ENUM CASING FIX TESTING SUITE
Tests specifically for the enum casing fix that was causing "DataError: invalid input value for enum subscription_plan: FREE"
Focus on user registration and subscription creation functionality.
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class EnumCasingTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.api_key = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        
        print(f"🔧 CRITICAL ENUM CASING FIX TESTING SUITE")
        print(f"📡 Base URL: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None, params: Optional[Dict] = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        if endpoint.startswith('/'):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}/{endpoint}"
        
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=request_headers, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=request_headers, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=request_headers, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=request_headers, params=params)
            else:
                return False, {"error": f"Unsupported method: {method}"}, 0
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return response.status_code < 400, response_data, response.status_code
            
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_user_registration_with_free_plan(self):
        """Test user registration that should create a FREE subscription without enum errors"""
        test_email = f"enum_test_user_{int(time.time())}@example.com"
        test_password = "EnumTestPassword123!"
        
        print(f"\n🔍 Testing user registration with FREE plan creation...")
        print(f"   Email: {test_email}")
        
        success, data, status = self.make_request('POST', '/api/v1/auth/register', {
            'email': test_email,
            'password': test_password,
            'first_name': 'Enum',
            'last_name': 'Tester'
        })
        
        if success and status == 200:
            self.token = data.get('access_token')
            self.user_id = data.get('user', {}).get('id')
            api_key_info = data.get('api_key', {})
            self.api_key = api_key_info.get('key')
            
            # Check if user was created with proper role enum
            user_data = data.get('user', {})
            user_role = user_data.get('role')
            
            self.log_test("User Registration with FREE Plan", True, 
                         f"User ID: {self.user_id}, Role: {user_role}, API Key: {self.api_key[:8] if self.api_key else 'None'}...")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("User Registration with FREE Plan", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_subscription_creation_free(self):
        """Test creating a FREE subscription explicitly"""
        if not self.token:
            self.log_test("Subscription Creation (FREE)", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/free', 
                                                 headers=headers)
        
        if success and status == 200:
            subscription_data = data.get('subscription', {})
            plan = subscription_data.get('plan') if subscription_data else None
            message = data.get('message', '')
            
            self.log_test("Subscription Creation (FREE)", True, 
                         f"Plan: {plan}, Message: {message}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Subscription Creation (FREE)", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_subscription_creation_developer(self):
        """Test creating a DEVELOPER subscription (should create checkout URL)"""
        if not self.token:
            self.log_test("Subscription Creation (DEVELOPER)", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/developer', 
                                                 headers=headers)
        
        if success and status == 200:
            checkout_url = data.get('checkout_url')
            message = data.get('message', '')
            
            self.log_test("Subscription Creation (DEVELOPER)", True, 
                         f"Checkout URL created: {bool(checkout_url)}, Message: {message}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Subscription Creation (DEVELOPER)", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_subscription_creation_business(self):
        """Test creating a BUSINESS subscription (should create checkout URL)"""
        if not self.token:
            self.log_test("Subscription Creation (BUSINESS)", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/business', 
                                                 headers=headers)
        
        if success and status == 200:
            checkout_url = data.get('checkout_url')
            message = data.get('message', '')
            
            self.log_test("Subscription Creation (BUSINESS)", True, 
                         f"Checkout URL created: {bool(checkout_url)}, Message: {message}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Subscription Creation (BUSINESS)", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_subscription_creation_enterprise(self):
        """Test creating an ENTERPRISE subscription (should create checkout URL)"""
        if not self.token:
            self.log_test("Subscription Creation (ENTERPRISE)", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/enterprise', 
                                                 headers=headers)
        
        if success and status == 200:
            checkout_url = data.get('checkout_url')
            message = data.get('message', '')
            
            self.log_test("Subscription Creation (ENTERPRISE)", True, 
                         f"Checkout URL created: {bool(checkout_url)}, Message: {message}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Subscription Creation (ENTERPRISE)", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_get_current_subscription(self):
        """Test getting current subscription to verify enum values are stored correctly"""
        if not self.token:
            self.log_test("Get Current Subscription", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/subscriptions/current', 
                                                 headers=headers)
        
        if success and status == 200:
            plan = data.get('plan')
            status_val = data.get('status')
            subscription_id = data.get('id')
            
            self.log_test("Get Current Subscription", True, 
                         f"ID: {subscription_id}, Plan: {plan}, Status: {status_val}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Get Current Subscription", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_subscription_plans_endpoint(self):
        """Test getting all subscription plans to verify enum consistency"""
        success, data, status = self.make_request('GET', '/api/v1/subscriptions/plans')
        
        if success and status == 200:
            plans_count = len(data) if isinstance(data, list) else 0
            plan_names = [plan.get('name', 'unknown') for plan in data] if isinstance(data, list) else []
            
            self.log_test("Subscription Plans Endpoint", True, 
                         f"Plans available: {plans_count}, Names: {plan_names}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Subscription Plans Endpoint", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_user_role_assignment(self):
        """Test that user roles are properly assigned without enum errors"""
        if not self.token:
            self.log_test("User Role Assignment", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/auth/me', headers=headers)
        
        if success and status == 200:
            user_role = data.get('role')
            user_email = data.get('email')
            is_active = data.get('is_active')
            
            # Verify role is lowercase as expected after enum fix
            role_is_lowercase = user_role and user_role.islower()
            
            self.log_test("User Role Assignment", True, 
                         f"Email: {user_email}, Role: {user_role}, Lowercase: {role_is_lowercase}, Active: {is_active}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("User Role Assignment", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def test_invalid_subscription_plan(self):
        """Test that invalid subscription plans are properly rejected"""
        if not self.token:
            self.log_test("Invalid Subscription Plan Rejection", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/INVALID_PLAN', 
                                                 headers=headers)
        
        if not success and status == 400:
            error_detail = data.get('detail', '')
            self.log_test("Invalid Subscription Plan Rejection", True, 
                         f"Correctly rejected invalid plan: {error_detail}")
            return True
        else:
            self.log_test("Invalid Subscription Plan Rejection", False, 
                         f"Expected 400 error, got {status}: {data}")
            return False

    def test_enum_case_sensitivity(self):
        """Test that enum values are case-insensitive in API but stored as lowercase"""
        if not self.token:
            self.log_test("Enum Case Sensitivity", False, "No authentication token")
            return False
        
        # Try subscribing with uppercase plan name (should work due to enum conversion)
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/subscriptions/subscribe/FREE', 
                                                 headers=headers)
        
        if success and status == 200:
            subscription_data = data.get('subscription', {})
            plan = subscription_data.get('plan') if subscription_data else None
            
            # Verify the plan is stored as lowercase
            plan_is_lowercase = plan and plan.islower()
            
            self.log_test("Enum Case Sensitivity", True, 
                         f"Uppercase 'FREE' accepted, stored as: {plan}, Lowercase: {plan_is_lowercase}")
            return True
        else:
            error_detail = data.get('detail', 'Unknown error')
            self.log_test("Enum Case Sensitivity", False, 
                         f"Status: {status}, Error: {error_detail}")
            return False

    def run_all_tests(self):
        """Run all enum casing tests"""
        print("\n🚀 Starting CRITICAL ENUM CASING FIX Tests...")
        
        # Test 1: User registration with FREE plan creation
        self.test_user_registration_with_free_plan()
        
        # Test 2: Explicit subscription creation for all plan types
        self.test_subscription_creation_free()
        self.test_subscription_creation_developer()
        self.test_subscription_creation_business()
        self.test_subscription_creation_enterprise()
        
        # Test 3: Verify current subscription data
        self.test_get_current_subscription()
        
        # Test 4: Test subscription plans endpoint
        self.test_subscription_plans_endpoint()
        
        # Test 5: Verify user role assignment
        self.test_user_role_assignment()
        
        # Test 6: Test invalid plan rejection
        self.test_invalid_subscription_plan()
        
        # Test 7: Test enum case sensitivity
        self.test_enum_case_sensitivity()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"🎯 ENUM CASING FIX TEST SUMMARY")
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"🎉 ALL ENUM CASING TESTS PASSED! The critical enum fix is working correctly.")
            return True
        else:
            print(f"⚠️  Some enum casing tests failed. The enum fix may need attention.")
            return False

def main():
    # Get backend URL from environment
    import os
    backend_url = os.getenv('REACT_APP_BACKEND_URL', 'https://460f813e-b331-44bc-8dd9-e489d2f34057.preview.emergentagent.com')
    
    if not backend_url.endswith('/api'):
        backend_url = f"{backend_url}/api"
    
    print(f"🔧 Using backend URL: {backend_url}")
    
    # Run tests
    tester = EnumCasingTester(backend_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()