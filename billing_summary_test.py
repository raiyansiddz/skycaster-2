#!/usr/bin/env python3
"""
Focused test for billing summary API endpoint and weather health endpoint
Tests specifically requested by user to verify current system state
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class BillingSummaryTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.api_key = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        
        print(f"🎯 BILLING SUMMARY & WEATHER HEALTH API TESTING")
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
            else:
                return False, {"error": f"Unsupported method: {method}"}, 0
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return response.status_code < 400, response_data, response.status_code
            
        except Exception as e:
            return False, {"error": str(e)}, 0

    def setup_test_user(self):
        """Create a test user for authentication"""
        import random
        test_email = f"billing_test_{int(time.time())}_{random.randint(1000,9999)}@example.com"
        test_password = "BillingTest123!"
        
        success, data, status = self.make_request('POST', '/api/v1/auth/register', {
            'email': test_email,
            'password': test_password,
            'first_name': 'Billing',
            'last_name': 'Tester'
        })
        
        if success and status == 200:
            self.token = data.get('access_token')
            self.user_id = data.get('user', {}).get('id')
            api_key_info = data.get('api_key', {})
            self.api_key = api_key_info.get('key')
            
            self.log_test("Test User Setup", True, 
                         f"User ID: {self.user_id}, Token: {'✓' if self.token else '✗'}")
            return True
        else:
            self.log_test("Test User Setup", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_health_endpoint(self):
        """Test weather health endpoint to confirm Skycaster API integration status"""
        print("\n🌤️  TESTING WEATHER HEALTH ENDPOINT")
        print("-" * 40)
        
        success, data, status = self.make_request('GET', '/api/v1/weather/health')
        
        if success and status == 200:
            service_status = data.get('status', 'unknown')
            mock_mode = data.get('mock_mode', None)
            endpoints = data.get('endpoints', {})
            
            # Check if it's in real API mode (not mock mode)
            real_api_mode = mock_mode is False
            
            details = f"Status: {service_status}, Mock Mode: {mock_mode}, Real API: {real_api_mode}, Endpoints: {len(endpoints)}"
            
            if service_status == 'healthy' and real_api_mode:
                self.log_test("Weather Health - Real API Mode", True, details)
                
                # Log endpoint details
                if endpoints:
                    print(f"   Available endpoints: {list(endpoints.keys())}")
                    for endpoint_name, endpoint_vars in endpoints.items():
                        if isinstance(endpoint_vars, list):
                            print(f"     {endpoint_name}: {len(endpoint_vars)} variables")
                
                return True
            else:
                self.log_test("Weather Health - Real API Mode", False, 
                             f"Expected healthy status and real API mode. Got: {details}")
                return False
        else:
            self.log_test("Weather Health - Real API Mode", False, 
                         f"Status: {status}, Response: {data}")
            return False

    def test_billing_summary_endpoint_authenticated(self):
        """Test billing summary endpoint with proper authentication"""
        print("\n💰 TESTING BILLING SUMMARY ENDPOINT")
        print("-" * 40)
        
        if not self.token:
            self.log_test("Billing Summary - Authentication", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/billing/summary', headers=headers)
        
        if success and status == 200:
            # Verify response structure matches BillingService.get_billing_summary
            expected_keys = ['current_subscription', 'recent_invoices', 'total_paid', 'outstanding_balance', 'next_billing_date']
            
            has_all_keys = all(key in data for key in expected_keys)
            
            if has_all_keys:
                current_subscription = data.get('current_subscription')
                recent_invoices = data.get('recent_invoices', [])
                total_paid = data.get('total_paid', 0)
                outstanding_balance = data.get('outstanding_balance', 0)
                next_billing_date = data.get('next_billing_date')
                
                details = f"Subscription: {'✓' if current_subscription else 'None'}, Invoices: {len(recent_invoices)}, Paid: {total_paid}, Outstanding: {outstanding_balance}"
                
                self.log_test("Billing Summary - Structure Valid", True, details)
                
                # Test subscription details if present
                if current_subscription:
                    sub_plan = current_subscription.get('plan')
                    sub_status = current_subscription.get('status')
                    print(f"   Subscription Plan: {sub_plan}, Status: {sub_status}")
                
                # Test invoice details if present
                if recent_invoices:
                    print(f"   Recent invoices: {len(recent_invoices)} found")
                    for i, invoice in enumerate(recent_invoices[:3]):  # Show first 3
                        inv_status = invoice.get('status', 'unknown')
                        inv_total = invoice.get('total', 0)
                        print(f"     Invoice {i+1}: Status={inv_status}, Total={inv_total}")
                
                return True
            else:
                missing_keys = [key for key in expected_keys if key not in data]
                self.log_test("Billing Summary - Structure Valid", False, 
                             f"Missing keys: {missing_keys}")
                return False
        else:
            self.log_test("Billing Summary - Authentication", False, 
                         f"Status: {status}, Response: {data}")
            return False

    def test_billing_summary_edge_cases(self):
        """Test billing summary endpoint edge cases"""
        print("\n🔍 TESTING BILLING SUMMARY EDGE CASES")
        print("-" * 40)
        
        # Test without authentication
        success, data, status = self.make_request('GET', '/api/v1/billing/summary')
        
        if not success and status in [401, 403]:
            self.log_test("Billing Summary - No Auth Rejection", True, 
                         f"Correctly rejected unauthenticated request: {status}")
        else:
            self.log_test("Billing Summary - No Auth Rejection", False, 
                         f"Expected 401/403, got {status}: {data}")
        
        # Test with invalid token
        invalid_headers = {'Authorization': 'Bearer invalid_token_12345'}
        success, data, status = self.make_request('GET', '/api/v1/billing/summary', headers=invalid_headers)
        
        if not success and status in [401, 403]:
            self.log_test("Billing Summary - Invalid Token Rejection", True, 
                         f"Correctly rejected invalid token: {status}")
            return True
        else:
            self.log_test("Billing Summary - Invalid Token Rejection", False, 
                         f"Expected 401/403, got {status}: {data}")
            return False

    def test_billing_summary_response_format(self):
        """Test that billing summary response format matches expected structure"""
        print("\n📋 TESTING BILLING SUMMARY RESPONSE FORMAT")
        print("-" * 40)
        
        if not self.token:
            self.log_test("Billing Summary - Response Format", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/billing/summary', headers=headers)
        
        if success and status == 200:
            # Detailed structure validation
            validation_results = []
            
            # Check current_subscription structure
            current_subscription = data.get('current_subscription')
            if current_subscription is None:
                validation_results.append("✓ current_subscription: None (valid for new user)")
            elif isinstance(current_subscription, dict):
                sub_keys = ['id', 'user_id', 'plan', 'status']
                has_sub_keys = all(key in current_subscription for key in sub_keys)
                validation_results.append(f"✓ current_subscription: dict with required keys: {has_sub_keys}")
            else:
                validation_results.append(f"✗ current_subscription: unexpected type {type(current_subscription)}")
            
            # Check recent_invoices structure
            recent_invoices = data.get('recent_invoices', [])
            if isinstance(recent_invoices, list):
                validation_results.append(f"✓ recent_invoices: list with {len(recent_invoices)} items")
                if recent_invoices:
                    first_invoice = recent_invoices[0]
                    if isinstance(first_invoice, dict):
                        inv_keys = ['id', 'user_id', 'status', 'total', 'amount_due']
                        has_inv_keys = all(key in first_invoice for key in inv_keys)
                        validation_results.append(f"  ✓ invoice structure: {has_inv_keys}")
            else:
                validation_results.append(f"✗ recent_invoices: expected list, got {type(recent_invoices)}")
            
            # Check numeric fields
            total_paid = data.get('total_paid', 0)
            outstanding_balance = data.get('outstanding_balance', 0)
            
            if isinstance(total_paid, (int, float)):
                validation_results.append(f"✓ total_paid: {total_paid} (numeric)")
            else:
                validation_results.append(f"✗ total_paid: expected numeric, got {type(total_paid)}")
            
            if isinstance(outstanding_balance, (int, float)):
                validation_results.append(f"✓ outstanding_balance: {outstanding_balance} (numeric)")
            else:
                validation_results.append(f"✗ outstanding_balance: expected numeric, got {type(outstanding_balance)}")
            
            # Check next_billing_date
            next_billing_date = data.get('next_billing_date')
            if next_billing_date is None:
                validation_results.append("✓ next_billing_date: None (valid for free plan)")
            elif isinstance(next_billing_date, str):
                validation_results.append(f"✓ next_billing_date: {next_billing_date} (string)")
            else:
                validation_results.append(f"✗ next_billing_date: unexpected type {type(next_billing_date)}")
            
            # Print all validation results
            for result in validation_results:
                print(f"   {result}")
            
            # Overall validation
            failed_validations = [r for r in validation_results if r.startswith("✗")]
            if not failed_validations:
                self.log_test("Billing Summary - Response Format", True, 
                             "All structure validations passed")
                return True
            else:
                self.log_test("Billing Summary - Response Format", False, 
                             f"{len(failed_validations)} validation failures")
                return False
        else:
            self.log_test("Billing Summary - Response Format", False, 
                         f"Status: {status}, Response: {data}")
            return False

    def run_all_tests(self):
        """Run all billing summary and weather health tests"""
        print("🚀 Starting Billing Summary & Weather Health API Tests")
        print("=" * 60)
        
        # Setup test user
        if not self.setup_test_user():
            print("❌ Failed to setup test user. Aborting tests.")
            return False
        
        # Run tests
        test_results = []
        
        # Weather Health Tests
        test_results.append(self.test_weather_health_endpoint())
        
        # Billing Summary Tests
        test_results.append(self.test_billing_summary_endpoint_authenticated())
        test_results.append(self.test_billing_summary_edge_cases())
        test_results.append(self.test_billing_summary_response_format())
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            failed_tests = self.tests_run - self.tests_passed
            print(f"⚠️  {failed_tests} TEST(S) FAILED")
            return False

def main():
    # Get backend URL from environment
    import os
    backend_url = os.getenv('REACT_APP_BACKEND_URL', 'https://5edb712d-637c-41b4-837e-2041c1202984.preview.emergentagent.com')
    
    # Ensure API prefix
    if not backend_url.endswith('/api'):
        backend_url = f"{backend_url}/api"
    
    tester = BillingSummaryTester(backend_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()