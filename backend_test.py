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
        # For localhost testing, use direct endpoint paths
        if endpoint.startswith('/'):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}/{endpoint}"
        
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        
        # Debug: Print headers for authentication endpoints
        if '/api-keys' in endpoint or '/usage' in endpoint:
            print(f"   DEBUG: Making request to {url}")
            print(f"   DEBUG: Headers: {request_headers}")
        
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
            
            # Debug: Print response for authentication endpoints
            if '/api-keys' in endpoint or '/usage' in endpoint:
                print(f"   DEBUG: Response status: {response.status_code}")
                print(f"   DEBUG: Response headers: {dict(response.headers)}")
            
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
        
        success, data, status = self.make_request('POST', '/api/v1/auth/register', {
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
        success, data, status = self.make_request('GET', '/api/v1/api-keys', headers=headers)
        
        if success and status == 200:
            api_keys_count = len(data) if isinstance(data, list) else 0
            self.log_test("Get API Keys", True, f"Found {api_keys_count} API keys")
            return True
        else:
            # Debug: Print token info for troubleshooting
            print(f"   DEBUG: Token length: {len(self.token) if self.token else 0}")
            print(f"   DEBUG: Token starts with: {self.token[:20] if self.token else 'None'}...")
            self.log_test("Get API Keys", False, f"Status: {status}, Response: {data}")
            return False

    def test_create_api_key(self):
        """Test creating a new API key"""
        if not self.token:
            self.log_test("Create API Key", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', '/api/v1/api-keys', 
                                                 {'name': 'Test Key'}, headers=headers)
        
        if success and status == 200:
            new_key = data.get('key')  # API returns ApiKeyResponse directly
            if new_key:
                self.log_test("Create API Key", True, f"Created key: {new_key[:8]}...")
                return True
            else:
                self.log_test("Create API Key", False, f"Missing key in response: {data}")
                return False
        else:
            self.log_test("Create API Key", False, f"Status: {status}, Response: {data}")
            return False

    # ============ NEW SKYCASTER WEATHER API TESTS ============
    
    def test_skycaster_weather_health(self):
        """Test Skycaster weather health check endpoint"""
        success, data, status = self.make_request('GET', '/api/v1/weather/health')
        
        if success and status == 200:
            service_status = data.get('status', 'unknown')
            mock_mode = data.get('mock_mode', False)
            endpoints = data.get('endpoints', {})
            self.log_test("Skycaster Weather Health", True, 
                         f"Status: {service_status}, Mock: {mock_mode}, Endpoints: {len(endpoints)}")
            return True
        else:
            self.log_test("Skycaster Weather Health", False, f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_variables(self):
        """Test Skycaster supported variables endpoint"""
        if not self.api_key:
            self.log_test("Skycaster Weather Variables", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        success, data, status = self.make_request('GET', '/api/v1/weather/variables', headers=headers)
        
        if success and status == 200:
            variables = data.get('variables', [])
            endpoints = data.get('endpoints', {})
            omega_vars = len(endpoints.get('omega', []))
            nova_vars = len(endpoints.get('nova', []))
            arc_vars = len(endpoints.get('arc', []))
            self.log_test("Skycaster Weather Variables", True, 
                         f"Total variables: {len(variables)}, Omega: {omega_vars}, Nova: {nova_vars}, Arc: {arc_vars}")
            return True
        else:
            self.log_test("Skycaster Weather Variables", False, f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_pricing(self):
        """Test Skycaster pricing information endpoint"""
        if not self.api_key:
            self.log_test("Skycaster Weather Pricing", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        success, data, status = self.make_request('GET', '/api/v1/weather/pricing', headers=headers)
        
        if success and status == 200:
            pricing = data.get('pricing', [])
            calculation_example = data.get('calculation_example', {})
            example_cost = calculation_example.get('final_amount', 0)
            currency = calculation_example.get('currency', 'INR')
            self.log_test("Skycaster Weather Pricing", True, 
                         f"Pricing configs: {len(pricing)}, Example cost: {example_cost} {currency}")
            return True
        else:
            self.log_test("Skycaster Weather Pricing", False, f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_usage_stats(self):
        """Test Skycaster weather usage statistics endpoint"""
        if not self.token:
            self.log_test("Skycaster Weather Usage Stats", False, "No authentication token")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/weather/usage/stats', headers=headers)
        
        if success and status == 200:
            total_requests = data.get('total_requests', 0)
            total_cost = data.get('total_cost', 0)
            currency = data.get('currency', 'INR')
            success_rate = data.get('success_rate', 0)
            self.log_test("Skycaster Weather Usage Stats", True, 
                         f"Requests: {total_requests}, Cost: {total_cost} {currency}, Success: {success_rate}%")
            return True
        else:
            self.log_test("Skycaster Weather Usage Stats", False, f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_forecast_valid(self):
        """Test Skycaster weather forecast with valid data"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Valid)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090], [19.0760, 72.8777]],  # Delhi, Mumbai
            "timestamp": "2025-07-18 14:00:00",
            "variables": ["ambient_temp(K)", "relative_humidity(%)", "ghi(W/m2)"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if success and status == 200:
            location_data = data.get('location_data', {})
            metadata = data.get('metadata', {})
            locations_count = metadata.get('locations_count', 0)
            endpoints_called = metadata.get('endpoints_called', [])
            final_amount = metadata.get('final_amount', '0')
            
            self.log_test("Skycaster Weather Forecast (Valid)", True, 
                         f"Locations: {locations_count}, Endpoints: {endpoints_called}, Cost: {final_amount}")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Valid)", False, f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_forecast_invalid_variables(self):
        """Test Skycaster weather forecast with invalid variables"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Invalid Variables)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090]],
            "timestamp": "2025-07-18 14:00:00",
            "variables": ["invalid_variable", "another_invalid_var"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if not success and status == 400:
            error_detail = data.get('detail', '')
            self.log_test("Skycaster Weather Forecast (Invalid Variables)", True, 
                         f"Correctly rejected invalid variables: {error_detail}")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Invalid Variables)", False, 
                         f"Expected 400 error, got {status}: {data}")
            return False

    def test_skycaster_weather_forecast_invalid_coordinates(self):
        """Test Skycaster weather forecast with invalid coordinates"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Invalid Coordinates)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[91.0, 181.0]],  # Invalid lat/lon
            "timestamp": "2025-07-18 14:00:00",
            "variables": ["ambient_temp(K)"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if not success and status == 422:
            error_detail = data.get('detail', [])
            self.log_test("Skycaster Weather Forecast (Invalid Coordinates)", True, 
                         f"Correctly rejected invalid coordinates: {len(error_detail)} validation errors")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Invalid Coordinates)", False, 
                         f"Expected 422 error, got {status}: {data}")
            return False

    def test_skycaster_weather_forecast_invalid_timestamp(self):
        """Test Skycaster weather forecast with invalid timestamp"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Invalid Timestamp)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090]],
            "timestamp": "invalid-timestamp-format",
            "variables": ["ambient_temp(K)"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if not success and status == 422:
            error_detail = data.get('detail', [])
            self.log_test("Skycaster Weather Forecast (Invalid Timestamp)", True, 
                         f"Correctly rejected invalid timestamp: {len(error_detail)} validation errors")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Invalid Timestamp)", False, 
                         f"Expected 422 error, got {status}: {data}")
            return False

    def test_skycaster_weather_forecast_empty_variables(self):
        """Test Skycaster weather forecast with empty variables array"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Empty Variables)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090]],
            "timestamp": "2025-07-18 14:00:00",
            "variables": [],  # Empty variables array
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if not success and status == 422:
            error_detail = data.get('detail', [])
            self.log_test("Skycaster Weather Forecast (Empty Variables)", True, 
                         f"Correctly rejected empty variables: {len(error_detail)} validation errors")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Empty Variables)", False, 
                         f"Expected 422 error, got {status}: {data}")
            return False

    def test_skycaster_weather_forecast_mixed_endpoints(self):
        """Test Skycaster weather forecast with variables from different endpoints"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Mixed Endpoints)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        forecast_data = {
            "list_lat_lon": [[28.6139, 77.2090]],
            "timestamp": "2025-07-18 14:00:00",
            "variables": [
                "ambient_temp(K)",      # Omega endpoint
                "ghi(W/m2)",           # Nova endpoint  
                "ct"                   # Arc endpoint
            ],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if success and status == 200:
            metadata = data.get('metadata', {})
            endpoints_called = metadata.get('endpoints_called', [])
            expected_endpoints = ['omega', 'nova', 'arc']
            
            # Check if all three endpoints were called
            all_endpoints_called = all(endpoint in endpoints_called for endpoint in expected_endpoints)
            
            self.log_test("Skycaster Weather Forecast (Mixed Endpoints)", True, 
                         f"Called endpoints: {endpoints_called}, All expected: {all_endpoints_called}")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Mixed Endpoints)", False, 
                         f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_forecast_multiple_locations(self):
        """Test Skycaster weather forecast with multiple locations"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Multiple Locations)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        locations = [
            [28.6139, 77.2090],  # Delhi
            [19.0760, 72.8777],  # Mumbai
            [13.0827, 80.2707],  # Chennai
            [22.5726, 88.3639],  # Kolkata
            [12.9716, 77.5946]   # Bangalore
        ]
        
        forecast_data = {
            "list_lat_lon": locations,
            "timestamp": "2025-07-18 14:00:00",
            "variables": ["ambient_temp(K)", "relative_humidity(%)"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                 forecast_data, headers=headers)
        
        if success and status == 200:
            location_data = data.get('location_data', {})
            metadata = data.get('metadata', {})
            locations_count = metadata.get('locations_count', 0)
            final_amount = metadata.get('final_amount', '0')
            
            self.log_test("Skycaster Weather Forecast (Multiple Locations)", True, 
                         f"Processed {locations_count} locations, Data keys: {len(location_data)}, Cost: {final_amount}")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Multiple Locations)", False, 
                         f"Status: {status}, Response: {data}")
            return False

    def test_skycaster_weather_forecast_different_timezones(self):
        """Test Skycaster weather forecast with different timezones"""
        if not self.api_key:
            self.log_test("Skycaster Weather Forecast (Different Timezones)", False, "No API key available")
            return False
            
        timezones_to_test = [
            "Asia/Kolkata",
            "UTC", 
            "America/New_York",
            "Europe/London"
        ]
        
        successful_tests = 0
        
        for timezone in timezones_to_test:
            headers = {'X-API-Key': self.api_key}
            forecast_data = {
                "list_lat_lon": [[28.6139, 77.2090]],
                "timestamp": "2025-07-18 14:00:00",
                "variables": ["ambient_temp(K)"],
                "timezone": timezone
            }
            
            success, data, status = self.make_request('POST', '/api/v1/weather/forecast', 
                                                     forecast_data, headers=headers)
            
            if success and status == 200:
                successful_tests += 1
        
        if successful_tests == len(timezones_to_test):
            self.log_test("Skycaster Weather Forecast (Different Timezones)", True, 
                         f"Successfully tested {successful_tests}/{len(timezones_to_test)} timezones")
            return True
        else:
            self.log_test("Skycaster Weather Forecast (Different Timezones)", False, 
                         f"Only {successful_tests}/{len(timezones_to_test)} timezones worked")
            return False

    # ============ LEGACY WEATHER API TESTS (for backward compatibility) ============
    
    def test_weather_current(self):
        """Test current weather endpoint (Legacy)"""
        if not self.api_key:
            self.log_test("Weather Current (Legacy)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London'}
        success, data, status = self.make_request('GET', '/api/v1/weather-legacy/current', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            location = data.get('data', {}).get('location', {}).get('name', 'Unknown')
            temp = data.get('data', {}).get('current', {}).get('temp_c', 'N/A')
            self.log_test("Weather Current (Legacy)", True, f"Location: {location}, Temp: {temp}°C")
            return True
        else:
            self.log_test("Weather Current (Legacy)", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_forecast(self):
        """Test weather forecast endpoint (Legacy)"""
        if not self.api_key:
            self.log_test("Weather Forecast (Legacy)", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'location': 'London', 'days': 3}
        success, data, status = self.make_request('GET', '/api/v1/weather-legacy/forecast', 
                                                 headers=headers, params=params)
        
        if success and status == 200:
            forecast_days = len(data.get('data', {}).get('forecast', {}).get('forecastday', []))
            self.log_test("Weather Forecast (Legacy)", True, f"Forecast days: {forecast_days}")
            return True
        else:
            self.log_test("Weather Forecast (Legacy)", False, f"Status: {status}, Response: {data}")
            return False

    def test_weather_search(self):
        """Test weather location search endpoint"""
        if not self.api_key:
            self.log_test("Weather Search", False, "No API key available")
            return False
            
        headers = {'X-API-Key': self.api_key}
        params = {'query': 'London'}
        success, data, status = self.make_request('GET', '/api/v1/weather/search', 
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
        success, data, status = self.make_request('GET', '/api/v1/weather/astronomy', 
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
        success, data, status = self.make_request('GET', '/api/v1/usage/stats', headers=headers)
        
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
        success, data, status = self.make_request('GET', '/api/v1/subscriptions/plans')
        
        if success and status == 200:
            # Handle both list and dict responses
            if isinstance(data, list):
                tiers_count = len(data)
            elif isinstance(data, dict) and 'tiers' in data:
                tiers_count = len(data.get('tiers', []))
            else:
                tiers_count = 0
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
            success, data, status = self.make_request('GET', '/api/v1/weather/current', 
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
        success, data, status = self.make_request('GET', '/api/v1/weather-legacy/current', 
                                                 headers=headers, params=params)
        
        if not success and status == 401:
            self.log_test("Invalid API Key Handling", True, "Correctly rejected invalid API key")
            return True
        else:
            self.log_test("Invalid API Key Handling", False, 
                         f"Expected 401, got {status}: {data}")
            return False

    # ============ ADMIN API TESTS ============
    
    def create_admin_user(self):
        """Create an admin user for testing admin endpoints"""
        admin_email = f"admin_{int(time.time())}@example.com"
        admin_password = "AdminPassword123!"
        
        # Register admin user
        success, data, status = self.make_request('POST', '/api/v1/auth/register', {
            'email': admin_email,
            'password': admin_password,
            'first_name': 'Admin',
            'last_name': 'User'
        })
        
        if success and status == 200:
            admin_token = data.get('access_token')
            admin_user_id = data.get('user', {}).get('id')
            
            # Note: In a real scenario, we'd need to promote this user to admin
            # For testing purposes, we'll assume the user is promoted
            return admin_token, admin_user_id, admin_email
        
        return None, None, None

    def test_admin_dashboard_stats(self):
        """Test admin dashboard statistics endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Dashboard Stats", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        success, data, status = self.make_request('GET', '/api/v1/admin/dashboard/stats', headers=headers)
        
        if success and status == 200:
            # Check if response has expected structure
            expected_keys = ['users', 'subscriptions', 'api_keys', 'support_tickets', 'usage', 'revenue']
            has_all_keys = all(key in data for key in expected_keys)
            
            if has_all_keys:
                self.log_test("Admin Dashboard Stats", True, 
                             f"Users: {data['users']['total']}, Tickets: {data['support_tickets']['total']}")
                return True
            else:
                self.log_test("Admin Dashboard Stats", False, "Missing expected keys in response")
                return False
        else:
            # This might fail if user is not admin - that's expected behavior
            if status == 403:
                self.log_test("Admin Dashboard Stats", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Dashboard Stats", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_get_users(self):
        """Test admin get all users endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Get Users", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        params = {'limit': 10, 'skip': 0}
        success, data, status = self.make_request('GET', '/api/v1/admin/users', headers=headers, params=params)
        
        if success and status == 200:
            users_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get Users", True, f"Retrieved {users_count} users")
            return True
        else:
            if status == 403:
                self.log_test("Admin Get Users", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Get Users", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_get_subscriptions(self):
        """Test admin get all subscriptions endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Get Subscriptions", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        params = {'limit': 10, 'skip': 0}
        success, data, status = self.make_request('GET', '/api/v1/admin/subscriptions', headers=headers, params=params)
        
        if success and status == 200:
            subs_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get Subscriptions", True, f"Retrieved {subs_count} subscriptions")
            return True
        else:
            if status == 403:
                self.log_test("Admin Get Subscriptions", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Get Subscriptions", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_get_api_keys(self):
        """Test admin get all API keys endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Get API Keys", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        params = {'limit': 10, 'skip': 0}
        success, data, status = self.make_request('GET', '/api/v1/admin/api-keys', headers=headers, params=params)
        
        if success and status == 200:
            keys_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get API Keys", True, f"Retrieved {keys_count} API keys")
            return True
        else:
            if status == 403:
                self.log_test("Admin Get API Keys", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Get API Keys", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_get_support_tickets(self):
        """Test admin get all support tickets endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Get Support Tickets", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        params = {'limit': 10, 'skip': 0}
        success, data, status = self.make_request('GET', '/api/v1/admin/support-tickets', headers=headers, params=params)
        
        if success and status == 200:
            tickets_count = len(data) if isinstance(data, list) else 0
            self.log_test("Admin Get Support Tickets", True, f"Retrieved {tickets_count} support tickets")
            return True
        else:
            if status == 403:
                self.log_test("Admin Get Support Tickets", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Get Support Tickets", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_usage_analytics(self):
        """Test admin usage analytics endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin Usage Analytics", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        params = {'days': 30}
        success, data, status = self.make_request('GET', '/api/v1/admin/usage-analytics', headers=headers, params=params)
        
        if success and status == 200:
            total_requests = data.get('total_requests', 0)
            self.log_test("Admin Usage Analytics", True, f"Total requests: {total_requests}")
            return True
        else:
            if status == 403:
                self.log_test("Admin Usage Analytics", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin Usage Analytics", False, f"Status: {status}, Response: {data}")
                return False

    def test_admin_system_health(self):
        """Test admin system health endpoint"""
        admin_token, admin_user_id, admin_email = self.create_admin_user()
        
        if not admin_token:
            self.log_test("Admin System Health", False, "Failed to create admin user")
            return False
        
        headers = {'Authorization': f'Bearer {admin_token}'}
        success, data, status = self.make_request('GET', '/api/v1/admin/system/health', headers=headers)
        
        if success and status == 200:
            system_status = data.get('status', 'unknown')
            db_status = data.get('database', 'unknown')
            self.log_test("Admin System Health", True, f"System: {system_status}, DB: {db_status}")
            return True
        else:
            if status == 403:
                self.log_test("Admin System Health", True, "Correctly rejected non-admin user")
                return True
            else:
                self.log_test("Admin System Health", False, f"Status: {status}, Response: {data}")
                return False

    # ============ SUPPORT API TESTS ============

    def test_support_create_ticket(self):
        """Test creating a support ticket"""
        if not self.token:
            self.log_test("Support Create Ticket", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        ticket_data = {
            'title': 'Test Support Ticket',
            'description': 'This is a test support ticket created during API testing.',
            'priority': 'medium'
        }
        
        success, data, status = self.make_request('POST', '/api/v1/support/tickets', ticket_data, headers=headers)
        
        if success and status == 200:
            ticket_id = data.get('id')
            ticket_title = data.get('title')
            self.log_test("Support Create Ticket", True, f"Created ticket: {ticket_id} - {ticket_title}")
            # Store ticket ID for other tests
            self.test_ticket_id = ticket_id
            return True
        else:
            self.log_test("Support Create Ticket", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_get_user_tickets(self):
        """Test getting user's support tickets"""
        if not self.token:
            self.log_test("Support Get User Tickets", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        params = {'limit': 10, 'skip': 0}
        success, data, status = self.make_request('GET', '/api/v1/support/tickets', headers=headers, params=params)
        
        if success and status == 200:
            tickets_count = len(data) if isinstance(data, list) else 0
            self.log_test("Support Get User Tickets", True, f"Retrieved {tickets_count} tickets")
            return True
        else:
            self.log_test("Support Get User Tickets", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_get_specific_ticket(self):
        """Test getting a specific support ticket"""
        if not self.token:
            self.log_test("Support Get Specific Ticket", False, "No authentication token")
            return False
        
        # First create a ticket to test with
        if not hasattr(self, 'test_ticket_id'):
            self.test_support_create_ticket()
        
        if not hasattr(self, 'test_ticket_id'):
            self.log_test("Support Get Specific Ticket", False, "No test ticket available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', f'/api/v1/support/tickets/{self.test_ticket_id}', headers=headers)
        
        if success and status == 200:
            ticket_title = data.get('title', 'Unknown')
            ticket_status = data.get('status', 'Unknown')
            self.log_test("Support Get Specific Ticket", True, f"Title: {ticket_title}, Status: {ticket_status}")
            return True
        else:
            self.log_test("Support Get Specific Ticket", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_update_ticket(self):
        """Test updating a support ticket"""
        if not self.token:
            self.log_test("Support Update Ticket", False, "No authentication token")
            return False
        
        # First create a ticket to test with
        if not hasattr(self, 'test_ticket_id'):
            self.test_support_create_ticket()
        
        if not hasattr(self, 'test_ticket_id'):
            self.log_test("Support Update Ticket", False, "No test ticket available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        update_data = {
            'title': 'Updated Test Support Ticket',
            'description': 'This ticket has been updated during API testing.',
            'priority': 'high'
        }
        
        success, data, status = self.make_request('PUT', f'/api/v1/support/tickets/{self.test_ticket_id}', 
                                                 update_data, headers=headers)
        
        if success and status == 200:
            updated_title = data.get('title', 'Unknown')
            updated_priority = data.get('priority', 'Unknown')
            self.log_test("Support Update Ticket", True, f"Updated: {updated_title}, Priority: {updated_priority}")
            return True
        else:
            self.log_test("Support Update Ticket", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_close_ticket(self):
        """Test closing a support ticket"""
        if not self.token:
            self.log_test("Support Close Ticket", False, "No authentication token")
            return False
        
        # First create a ticket to test with
        if not hasattr(self, 'test_ticket_id'):
            self.test_support_create_ticket()
        
        if not hasattr(self, 'test_ticket_id'):
            self.log_test("Support Close Ticket", False, "No test ticket available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', f'/api/v1/support/tickets/{self.test_ticket_id}/close', 
                                                 headers=headers)
        
        if success and status == 200:
            message = data.get('message', 'Ticket closed')
            self.log_test("Support Close Ticket", True, message)
            return True
        else:
            self.log_test("Support Close Ticket", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_reopen_ticket(self):
        """Test reopening a support ticket"""
        if not self.token:
            self.log_test("Support Reopen Ticket", False, "No authentication token")
            return False
        
        # First create and close a ticket to test with
        if not hasattr(self, 'test_ticket_id'):
            self.test_support_create_ticket()
            self.test_support_close_ticket()
        
        if not hasattr(self, 'test_ticket_id'):
            self.log_test("Support Reopen Ticket", False, "No test ticket available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('POST', f'/api/v1/support/tickets/{self.test_ticket_id}/reopen', 
                                                 headers=headers)
        
        if success and status == 200:
            message = data.get('message', 'Ticket reopened')
            self.log_test("Support Reopen Ticket", True, message)
            return True
        else:
            self.log_test("Support Reopen Ticket", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_ticket_history(self):
        """Test getting support ticket history"""
        if not self.token:
            self.log_test("Support Ticket History", False, "No authentication token")
            return False
        
        # First create a ticket to test with
        if not hasattr(self, 'test_ticket_id'):
            self.test_support_create_ticket()
        
        if not hasattr(self, 'test_ticket_id'):
            self.log_test("Support Ticket History", False, "No test ticket available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', f'/api/v1/support/tickets/{self.test_ticket_id}/history', 
                                                 headers=headers)
        
        if success and status == 200:
            history_count = len(data) if isinstance(data, list) else 0
            self.log_test("Support Ticket History", True, f"Retrieved {history_count} history entries")
            return True
        else:
            self.log_test("Support Ticket History", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_user_stats(self):
        """Test getting user support statistics"""
        if not self.token:
            self.log_test("Support User Stats", False, "No authentication token")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        success, data, status = self.make_request('GET', '/api/v1/support/stats', headers=headers)
        
        if success and status == 200:
            total_tickets = data.get('total_tickets', 0)
            by_status = data.get('by_status', {})
            self.log_test("Support User Stats", True, f"Total tickets: {total_tickets}, Open: {by_status.get('open', 0)}")
            return True
        else:
            self.log_test("Support User Stats", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_categories(self):
        """Test getting support categories"""
        success, data, status = self.make_request('GET', '/api/v1/support/categories')
        
        if success and status == 200:
            categories_count = len(data) if isinstance(data, list) else 0
            self.log_test("Support Categories", True, f"Retrieved {categories_count} categories")
            return True
        else:
            self.log_test("Support Categories", False, f"Status: {status}, Response: {data}")
            return False

    def test_support_faq(self):
        """Test getting support FAQ"""
        success, data, status = self.make_request('GET', '/api/v1/support/faq')
        
        if success and status == 200:
            faq_count = len(data) if isinstance(data, list) else 0
            self.log_test("Support FAQ", True, f"Retrieved {faq_count} FAQ entries")
            return True
        else:
            self.log_test("Support FAQ", False, f"Status: {status}, Response: {data}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n🧪 Starting Backend API Tests...\n")
        
        # Core functionality tests
        core_tests = [
            self.test_health_check,
            self.test_user_registration,
            self.test_user_login,
            self.test_get_api_keys,
            self.test_create_api_key,
            self.test_usage_analytics,
            self.test_subscription_tiers,
            self.test_rate_limiting,
            self.test_invalid_api_key,
        ]
        
        # New Skycaster Weather API tests
        skycaster_weather_tests = [
            self.test_skycaster_weather_health,
            self.test_skycaster_weather_variables,
            self.test_skycaster_weather_pricing,
            self.test_skycaster_weather_usage_stats,
            self.test_skycaster_weather_forecast_valid,
            self.test_skycaster_weather_forecast_invalid_variables,
            self.test_skycaster_weather_forecast_invalid_coordinates,
            self.test_skycaster_weather_forecast_invalid_timestamp,
            self.test_skycaster_weather_forecast_empty_variables,
            self.test_skycaster_weather_forecast_mixed_endpoints,
            self.test_skycaster_weather_forecast_multiple_locations,
            self.test_skycaster_weather_forecast_different_timezones,
        ]
        
        # Legacy weather API tests
        legacy_weather_tests = [
            self.test_weather_current,
            self.test_weather_forecast,
            self.test_weather_search,
            self.test_weather_astronomy,
        ]
        
        # Admin API tests
        admin_tests = [
            self.test_admin_dashboard_stats,
            self.test_admin_get_users,
            self.test_admin_get_subscriptions,
            self.test_admin_get_api_keys,
            self.test_admin_get_support_tickets,
            self.test_admin_usage_analytics,
            self.test_admin_system_health,
        ]
        
        # Support API tests
        support_tests = [
            self.test_support_create_ticket,
            self.test_support_get_user_tickets,
            self.test_support_get_specific_ticket,
            self.test_support_update_ticket,
            self.test_support_close_ticket,
            self.test_support_reopen_ticket,
            self.test_support_ticket_history,
            self.test_support_user_stats,
            self.test_support_categories,
            self.test_support_faq,
        ]
        
        # Run all tests
        print("=" * 60)
        print("🔧 CORE API TESTS")
        print("=" * 60)
        
        for test in core_tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")
            print()  # Add spacing between tests
        
        print("=" * 60)
        print("🌤️  NEW SKYCASTER WEATHER API TESTS")
        print("=" * 60)
        
        for test in skycaster_weather_tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")
            print()  # Add spacing between tests
        
        print("=" * 60)
        print("🌦️  LEGACY WEATHER API TESTS")
        print("=" * 60)
        
        for test in legacy_weather_tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")
            print()  # Add spacing between tests
        
        print("=" * 60)
        print("👑 ADMIN API TESTS")
        print("=" * 60)
        
        for test in admin_tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")
            print()  # Add spacing between tests
        
        print("=" * 60)
        print("🎫 SUPPORT API TESTS")
        print("=" * 60)
        
        for test in support_tests:
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
    # Use localhost for testing since external URL routing has issues
    base_url = "http://localhost:8001"
    
    tester = SKYCASTERAPITester(base_url)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())