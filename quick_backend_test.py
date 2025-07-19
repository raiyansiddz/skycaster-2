#!/usr/bin/env python3
"""
Quick Backend API Test - Focused testing of core functionality
"""

import requests
import json
import time
from datetime import datetime

class QuickAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.api_key = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚀 Quick SKYCASTER API Test")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 50)

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

    def make_request(self, method: str, endpoint: str, data=None, headers=None):
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=request_headers)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=request_headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}, 0
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return response.status_code < 400, response_data, response.status_code
            
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_health_check(self):
        """Test health check endpoint"""
        success, data, status = self.make_request('GET', '/v1/weather/health')
        
        if success and status == 200:
            service_status = data.get('status', 'unknown')
            mock_mode = data.get('mock_mode', False)
            self.log_test("Health Check", True, f"Status: {service_status}, Mock: {mock_mode}")
            return True
        else:
            self.log_test("Health Check", False, f"Status: {status}, Response: {data}")
            return False

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_user_{int(time.time())}@example.com"
        test_password = "TestPassword123!"
        
        success, data, status = self.make_request('POST', '/v1/auth/register', {
            'email': test_email,
            'password': test_password
        })
        
        if success and status == 200:
            self.token = data.get('access_token')
            self.user_id = data.get('user', {}).get('id')
            api_key_info = data.get('api_key', {})
            self.api_key = api_key_info.get('key')
            
            self.log_test("User Registration", True, 
                         f"User ID: {self.user_id}, API Key: {self.api_key[:8] if self.api_key else 'None'}...")
            return True
        else:
            self.log_test("User Registration", False, f"Status: {status}, Response: {data}")
            return False

    def test_subscription_tiers(self):
        """Test subscription tiers endpoint"""
        success, data, status = self.make_request('GET', '/v1/subscriptions/plans')
        
        if success and status == 200:
            tiers_count = len(data) if isinstance(data, list) else 0
            self.log_test("Subscription Tiers", True, f"Available tiers: {tiers_count}")
            return True
        else:
            self.log_test("Subscription Tiers", False, f"Status: {status}, Response: {data}")
            return False

    def test_get_api_keys(self):
        """Test getting API keys"""
        if not self.token:
            self.log_test("Get API Keys", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/v1/api-keys/', headers=headers)
        
        if success and status == 200:
            api_keys_count = len(data) if isinstance(data, list) else 0
            self.log_test("Get API Keys", True, f"Found {api_keys_count} API keys")
            return True
        else:
            self.log_test("Get API Keys", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_variables(self):
        """Test weather variables endpoint"""
        if not self.api_key:
            self.log_test("Weather Variables", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        success, data, status = self.make_request('GET', '/v1/weather/variables', headers=headers)
        
        if success and status == 200:
            variables = data.get('variables', [])
            endpoints = data.get('endpoints', {})
            self.log_test("Weather Variables", True, 
                         f"Total variables: {len(variables)}, Endpoints: {len(endpoints)}")
            return True
        else:
            self.log_test("Weather Variables", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_forecast(self):
        """Test weather forecast endpoint"""
        if not self.api_key:
            self.log_test("Weather Forecast", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090]],  # Delhi
            "timestamp": "2025-07-18 14:00:00",
            "variables": ["ambient_temp(K)", "relative_humidity(%)"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if success and status == 200:
            metadata = data.get('metadata', {})
            locations_count = metadata.get('locations_count', 0)
            final_amount = metadata.get('final_amount', '0')
            
            self.log_test("Weather Forecast", True, 
                         f"Locations: {locations_count}, Cost: {final_amount}")
            return True
        else:
            self.log_test("Weather Forecast", False, f"Status: {status}, Response: {data}")
            return False

    def test_usage_analytics(self):
        """Test usage analytics endpoint"""
        if not self.token:
            self.log_test("Usage Analytics", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/v1/usage/stats', headers=headers)
        
        if success and status == 200:
            current_usage = data.get('current_month_usage', 0)
            monthly_limit = data.get('monthly_limit', 0)
            tier = data.get('subscription_tier', 'unknown')
            self.log_test("Usage Analytics", True, 
                         f"Usage: {current_usage}/{monthly_limit}, Tier: {tier}")
            return True
        else:
            self.log_test("Usage Analytics", False, f"Status: {status}, Response: {data}")
            return False

    def run_tests(self):
        """Run all tests"""
        print("\n🧪 Starting Core API Tests...")
        
        # Core functionality tests
        self.test_health_check()
        self.test_subscription_tiers()
        self.test_user_registration()
        
        if self.token and self.api_key:
            self.test_get_api_keys()
            self.test_weather_variables()
            self.test_weather_forecast()
            self.test_usage_analytics()
        
        # Summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://e7d1f414-95d5-4fe9-9fd2-83c0d70b80c2.preview.emergentagent.com/api"
    
    tester = QuickAPITester(base_url)
    tester.run_tests()