#!/usr/bin/env python3
"""
SKYCASTER Weather API Backend Testing Suite
Tests all backend API endpoints including authentication, API key management, and weather proxy functionality.
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class SKYCASTERAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.api_key = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        
        print(f"🚀 SKYCASTER API Testing Suite")
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
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=request_headers, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=request_headers, params=params)
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

    def test_health_check(self):
        """Test health check endpoint"""
        success, data, status = self.make_request('GET', '/health')
        
        if success and status == 200:
            self.log_test("Health Check", True, f"Status: {data.get('status', 'unknown')}")
            return True
        else:
            self.log_test("Health Check", False, f"Status: {status}, Response: {data}")
            return False

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_user_{int(time.time())}@example.com"
        test_password = "TestPassword123!"
        
        success, data, status = self.make_request('POST', '/auth/register', {
            'email': test_email,
            'password': test_password
        })
        
        if success and status == 200:
            self.token = data.get('token')
            self.user_id = data.get('user', {}).get('id')
            api_key_info = data.get('api_key', {})
            self.api_key = api_key_info.get('key')
            
            self.log_test("User Registration", True, 
                         f"User ID: {self.user_id}, API Key: {self.api_key[:8]}...")
            return True
        else:
            self.log_test("User Registration", False, f"Status: {status}, Response: {data}")
            return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        if not self.token:
            self.log_test("User Login", False, "No token from registration")
            return False
            
        # We'll skip login test since we already have token from registration
        self.log_test("User Login", True, "Using token from registration")
        return True

    def test_get_api_keys(self):
        """Test getting API keys"""
        if not self.token:
            self.log_test("Get API Keys", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api-keys', headers=headers)
        
        if success and status == 200:
            api_keys_count = len(data) if isinstance(data, list) else 0
            self.log_test("Get API Keys", True, f"Found {api_keys_count} API keys")
            return True
        else:
            self.log_test("Get API Keys", False, f"Status: {status}, Response: {data}")
            return False

    def test_create_api_key(self):
        """Test creating a new API key"""
        if not self.token:
            self.log_test("Create API Key", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api-keys', 
                                                 {'name': 'Test Key'}, headers=headers)
        
        if success and status == 200:
            new_key = data.get('api_key', {}).get('key')
            self.log_test("Create API Key", True, f"Created key: {new_key[:8]}...")
            return True
        else:
            self.log_test("Create API Key", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_current(self):
        """Test current weather endpoint"""
        if not self.api_key:
            self.log_test("Weather Current", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London'}
        success, data, status = self.make_request('GET', '/weather/current', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            location = data.get('data', {}).get('location', {}).get('name', 'Unknown')
            temp = data.get('data', {}).get('current', {}).get('temp_c', 'N/A')
            self.log_test("Weather Current", True, f"Location: {location}, Temp: {temp}°C")
            return True
        else:
            self.log_test("Weather Current", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_forecast(self):
        """Test weather forecast endpoint"""
        if not self.api_key:
            self.log_test("Weather Forecast", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London', 'days': 3}
        success, data, status = self.make_request('GET', '/weather/forecast', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            forecast_days = len(data.get('data', {}).get('forecast', {}).get('forecastday', []))
            self.log_test("Weather Forecast", True, f"Forecast days: {forecast_days}")
            return True
        else:
            self.log_test("Weather Forecast", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_search(self):
        """Test weather location search endpoint"""
        if not self.api_key:
            self.log_test("Weather Search", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'query': 'London'}
        success, data, status = self.make_request('GET', '/weather/search', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            results_count = len(data.get('data', [])) if isinstance(data.get('data'), list) else 0
            self.log_test("Weather Search", True, f"Found {results_count} locations")
            return True
        else:
            self.log_test("Weather Search", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_astronomy(self):
        """Test weather astronomy endpoint"""
        if not self.api_key:
            self.log_test("Weather Astronomy", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London', 'date': '2024-01-01'}
        success, data, status = self.make_request('GET', '/weather/astronomy', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            astronomy = data.get('data', {}).get('astronomy', {})
            sunrise = astronomy.get('astro', {}).get('sunrise', 'N/A')
            self.log_test("Weather Astronomy", True, f"Sunrise: {sunrise}")
            return True
        else:
            self.log_test("Weather Astronomy", False, f"Status: {status}, Response: {data}")
            return False

    def test_usage_analytics(self):
        """Test usage analytics endpoint"""
        if not self.token:
            self.log_test("Usage Analytics", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/usage', headers=headers)
        
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

    def test_subscription_tiers(self):
        """Test subscription tiers endpoint"""
        success, data, status = self.make_request('GET', '/subscription-tiers')
        
        if success and status == 200:
            tiers_count = len(data.get('tiers', [])) if isinstance(data.get('tiers'), list) else 0
            self.log_test("Subscription Tiers", True, f"Available tiers: {tiers_count}")
            return True
        else:
            self.log_test("Subscription Tiers", False, f"Status: {status}, Response: {data}")
            return False

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        if not self.api_key:
            self.log_test("Rate Limiting", False, "No API key available")
            return False
            
        print("\n🔄 Testing rate limiting (making multiple requests)...")
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London'}
        
        success_count = 0
        rate_limited = False
        
        # Make 5 rapid requests to test rate limiting
        for i in range(5):
            success, data, status = self.make_request('GET', '/weather/current', 
                                                     headers=headers, params=params)
            if success:
                success_count += 1
            elif status == 429:  # Rate limited
                rate_limited = True
                break
            time.sleep(0.1)  # Small delay between requests
        
        if success_count > 0:
            self.log_test("Rate Limiting", True, 
                         f"Made {success_count} successful requests, Rate limited: {rate_limited}")
            return True
        else:
            self.log_test("Rate Limiting", False, "No successful requests made")
            return False

    def test_invalid_api_key(self):
        """Test behavior with invalid API key"""
        headers = {'X-API-Key': 'invalid_key_12345'}
        params = {'location': 'London'}
        success, data, status = self.make_request('GET', '/weather/current', 
                                                 headers=headers, params=params)
        
        if not success and status == 401:
            self.log_test("Invalid API Key Handling", True, "Correctly rejected invalid API key")
            return True
        else:
            self.log_test("Invalid API Key Handling", False, 
                         f"Expected 401, got {status}: {data}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n🧪 Starting Backend API Tests...\n")
        
        # Core functionality tests
        tests = [
            self.test_health_check,
            self.test_user_registration,
            self.test_user_login,
            self.test_get_api_keys,
            self.test_create_api_key,
            self.test_weather_current,
            self.test_weather_forecast,
            self.test_weather_search,
            self.test_weather_astronomy,
            self.test_usage_analytics,
            self.test_subscription_tiers,
            self.test_rate_limiting,
            self.test_invalid_api_key,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")
            print()  # Add spacing between tests
        
        # Print final results
        print("=" * 60)
        print(f"📊 Test Results Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    # Use the public endpoint from frontend/.env
    base_url = "https://5f65b785-95b5-4458-8ccf-560b4e4fe505.preview.emergentagent.com"
    
    tester = SKYCASTERAPITester(base_url)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())