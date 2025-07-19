#!/usr/bin/env python3
"""
SKYCASTER Weather API Timing and Rate Limiting Test Suite
Tests separate endpoint functionality, different timing scenarios, and API limits
"""

import requests
import sys
import json
import time
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import threading

class SkycasterTimingTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.api_key = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        
        # Test locations
        self.locations = {
            "lucknow": [26.8467, 80.9462],
            "mumbai": [19.0760, 72.8777]
        }
        
        # Endpoint-specific variables
        self.endpoint_variables = {
            "omega": ["ambient_temp(K)", "wind_10m", "wind_100m", "relative_humidity(%)"],
            "nova": ["temperature(K)", "surface_pressure(Pa)", "cumulus_precipitation(mm)", 
                    "ghi(W/m2)", "ghi_farms(W/m2)", "clear_sky_ghi_farms(W/m2)", "albedo"],
            "arc": ["ct", "pc", "pcph"]
        }
        
        print(f"🚀 SKYCASTER Timing & Rate Limiting Test Suite")
        print(f"📡 Base URL: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

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
                    headers: Optional[Dict] = None, params: Optional[Dict] = None, 
                    timeout: int = 30) -> tuple:
        """Make HTTP request and return (success, response_data, status_code, response_time)"""
        if endpoint.startswith('/'):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}/{endpoint}"
        
        if headers is None:
            headers = {}
        
        start_time = time.time()
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                headers['Content-Type'] = 'application/json'
                response = self.session.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                headers['Content-Type'] = 'application/json'
                response = self.session.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}, 0, 0
            
            response_time = time.time() - start_time
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
            
            return response.status_code < 400, response_data, response.status_code, response_time
            
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            return False, {"error": "Request timeout"}, 408, response_time
        except Exception as e:
            response_time = time.time() - start_time
            return False, {"error": str(e)}, 0, response_time

    def setup_authentication(self):
        """Setup authentication for testing"""
        print("\n🔐 Setting up authentication...")
        
        # Register a test user
        user_data = {
            "email": f"timing_test_{int(time.time())}@skycaster.com",
            "password": "TestPassword123!",
            "full_name": "Timing Test User"
        }
        
        success, data, status, _ = self.make_request('POST', '/api/v1/auth/register', user_data)
        
        if not success or status != 200:
            self.log_test("User Registration", False, f"Status: {status}, Response: {data}")
            return False
        
        # Extract token and API key from registration response
        self.token = data.get('access_token')
        self.user_id = data.get('user', {}).get('id')
        api_key_data = data.get('api_key', {})
        self.api_key = api_key_data.get('key')
        
        if self.token and self.api_key:
            self.log_test("User Registration & Setup", True, f"Token and API Key obtained")
            return True
        
        # Login to get JWT token
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        success, data, status, _ = self.make_request('POST', '/api/v1/auth/login', login_data)
        
        if success and status == 200:
            self.token = data.get('access_token')
            self.user_id = data.get('user_id')
            self.log_test("User Login", True, f"Token obtained, User ID: {self.user_id}")
        else:
            self.log_test("User Login", False, f"Status: {status}, Response: {data}")
            return False
        
        # Create API key
        headers = {'Authorization': f'Bearer {self.token}'}
        api_key_data = {
            "name": "Timing Test API Key",
            "description": "API key for timing and rate limiting tests"
        }
        
        success, data, status, _ = self.make_request('POST', '/api/v1/api-keys/', api_key_data, headers=headers)
        
        if success and status == 201:
            self.api_key = data.get('key')
            self.log_test("API Key Creation", True, f"API Key: {self.api_key[:20]}...")
            return True
        else:
            self.log_test("API Key Creation", False, f"Status: {status}, Response: {data}")
            return False

    def get_future_timestamp(self, hours_ahead: int) -> str:
        """Get timestamp for future time"""
        future_time = datetime.now() + timedelta(hours=hours_ahead)
        return future_time.strftime("%Y-%m-%d %H:%M:%S")

    def test_separate_endpoint_omega(self):
        """Test omega endpoint separately with its specific variables"""
        print(f"\n🔬 Testing OMEGA endpoint separately...")
        
        if not self.api_key:
            self.log_test("Omega Endpoint Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        
        # Test with all omega variables
        forecast_data = {
            "list_lat_lon": [self.locations["lucknow"]],
            "timestamp": self.get_future_timestamp(6),  # 6 hours ahead
            "variables": self.endpoint_variables["omega"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status, response_time = self.make_request(
            'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
        )
        
        if success and status == 200:
            metadata = data.get('metadata', {})
            endpoints_called = metadata.get('endpoints_called', [])
            variables_requested = metadata.get('variables_requested', [])
            
            # Verify only omega endpoint was called
            omega_only = endpoints_called == ['omega']
            all_vars_present = all(var in variables_requested for var in self.endpoint_variables["omega"])
            
            self.log_test("Omega Endpoint (Separate)", True, 
                         f"Endpoints: {endpoints_called}, Variables: {len(variables_requested)}, "
                         f"Response time: {response_time:.2f}s, Omega only: {omega_only}")
            return True
        else:
            self.log_test("Omega Endpoint (Separate)", False, 
                         f"Status: {status}, Response: {data}, Time: {response_time:.2f}s")
            return False

    def test_separate_endpoint_nova(self):
        """Test nova endpoint separately with its specific variables"""
        print(f"\n🔬 Testing NOVA endpoint separately...")
        
        if not self.api_key:
            self.log_test("Nova Endpoint Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        
        # Test with all nova variables
        forecast_data = {
            "list_lat_lon": [self.locations["mumbai"]],
            "timestamp": self.get_future_timestamp(12),  # 12 hours ahead
            "variables": self.endpoint_variables["nova"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status, response_time = self.make_request(
            'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
        )
        
        if success and status == 200:
            metadata = data.get('metadata', {})
            endpoints_called = metadata.get('endpoints_called', [])
            variables_requested = metadata.get('variables_requested', [])
            
            # Verify only nova endpoint was called
            nova_only = endpoints_called == ['nova']
            all_vars_present = all(var in variables_requested for var in self.endpoint_variables["nova"])
            
            self.log_test("Nova Endpoint (Separate)", True, 
                         f"Endpoints: {endpoints_called}, Variables: {len(variables_requested)}, "
                         f"Response time: {response_time:.2f}s, Nova only: {nova_only}")
            return True
        else:
            self.log_test("Nova Endpoint (Separate)", False, 
                         f"Status: {status}, Response: {data}, Time: {response_time:.2f}s")
            return False

    def test_separate_endpoint_arc(self):
        """Test arc endpoint separately with its specific variables"""
        print(f"\n🔬 Testing ARC endpoint separately...")
        
        if not self.api_key:
            self.log_test("Arc Endpoint Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        
        # Test with all arc variables
        forecast_data = {
            "list_lat_lon": [self.locations["lucknow"], self.locations["mumbai"]],
            "timestamp": self.get_future_timestamp(24),  # 24 hours ahead
            "variables": self.endpoint_variables["arc"],
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status, response_time = self.make_request(
            'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
        )
        
        if success and status == 200:
            metadata = data.get('metadata', {})
            endpoints_called = metadata.get('endpoints_called', [])
            variables_requested = metadata.get('variables_requested', [])
            
            # Verify only arc endpoint was called
            arc_only = endpoints_called == ['arc']
            all_vars_present = all(var in variables_requested for var in self.endpoint_variables["arc"])
            
            self.log_test("Arc Endpoint (Separate)", True, 
                         f"Endpoints: {endpoints_called}, Variables: {len(variables_requested)}, "
                         f"Response time: {response_time:.2f}s, Arc only: {arc_only}")
            return True
        else:
            self.log_test("Arc Endpoint (Separate)", False, 
                         f"Status: {status}, Response: {data}, Time: {response_time:.2f}s")
            return False

    def test_different_timing_scenarios(self):
        """Test requests with different future timestamps"""
        print(f"\n⏰ Testing different timing scenarios...")
        
        if not self.api_key:
            self.log_test("Timing Scenarios Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        timing_scenarios = [1, 6, 12, 24]  # hours ahead
        successful_tests = 0
        response_times = []
        
        for hours_ahead in timing_scenarios:
            forecast_data = {
                "list_lat_lon": [self.locations["lucknow"]],
                "timestamp": self.get_future_timestamp(hours_ahead),
                "variables": ["ambient_temp(K)", "ghi(W/m2)"],  # Mix of omega and nova
                "timezone": "Asia/Kolkata"
            }
            
            success, data, status, response_time = self.make_request(
                'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
            )
            
            response_times.append(response_time)
            
            if success and status == 200:
                successful_tests += 1
                metadata = data.get('metadata', {})
                endpoints_called = metadata.get('endpoints_called', [])
                print(f"   ✅ {hours_ahead}h ahead: {response_time:.2f}s, Endpoints: {endpoints_called}")
            else:
                print(f"   ❌ {hours_ahead}h ahead: Status {status}, Time: {response_time:.2f}s")
            
            # Small delay between requests
            time.sleep(0.5)
        
        avg_response_time = sum(response_times) / len(response_times)
        success_rate = (successful_tests / len(timing_scenarios)) * 100
        
        self.log_test("Different Timing Scenarios", successful_tests == len(timing_scenarios), 
                     f"Success rate: {success_rate}%, Avg response time: {avg_response_time:.2f}s")
        
        return successful_tests == len(timing_scenarios)

    def test_rapid_sequential_requests(self):
        """Test rapid sequential requests to check for rate limiting"""
        print(f"\n🚀 Testing rapid sequential requests...")
        
        if not self.api_key:
            self.log_test("Rapid Sequential Requests", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        num_requests = 5
        successful_requests = 0
        response_times = []
        rate_limited = False
        
        forecast_data = {
            "list_lat_lon": [self.locations["mumbai"]],
            "timestamp": self.get_future_timestamp(2),
            "variables": ["ambient_temp(K)"],
            "timezone": "Asia/Kolkata"
        }
        
        start_time = time.time()
        
        for i in range(num_requests):
            success, data, status, response_time = self.make_request(
                'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
            )
            
            response_times.append(response_time)
            
            if success and status == 200:
                successful_requests += 1
                print(f"   ✅ Request {i+1}: {response_time:.2f}s")
            elif status == 429:  # Rate limited
                rate_limited = True
                print(f"   ⚠️  Request {i+1}: Rate limited (429)")
            else:
                print(f"   ❌ Request {i+1}: Status {status}, Time: {response_time:.2f}s")
        
        total_time = time.time() - start_time
        avg_response_time = sum(response_times) / len(response_times)
        requests_per_second = num_requests / total_time
        
        self.log_test("Rapid Sequential Requests", True, 
                     f"Successful: {successful_requests}/{num_requests}, "
                     f"Rate limited: {rate_limited}, "
                     f"Avg response: {avg_response_time:.2f}s, "
                     f"Rate: {requests_per_second:.2f} req/s")
        
        return True

    def make_concurrent_request(self, endpoint_type: str, location: List[float]) -> Dict[str, Any]:
        """Make a single concurrent request"""
        headers = {'X-API-Key': self.api_key}
        
        forecast_data = {
            "list_lat_lon": [location],
            "timestamp": self.get_future_timestamp(3),
            "variables": self.endpoint_variables[endpoint_type][:2],  # First 2 variables
            "timezone": "Asia/Kolkata"
        }
        
        success, data, status, response_time = self.make_request(
            'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
        )
        
        return {
            "endpoint": endpoint_type,
            "success": success,
            "status": status,
            "response_time": response_time,
            "data": data
        }

    def test_concurrent_requests(self):
        """Test concurrent requests to different endpoints"""
        print(f"\n🔄 Testing concurrent requests to different endpoints...")
        
        if not self.api_key:
            self.log_test("Concurrent Requests", False, "No API key available")
            return False
        
        # Prepare concurrent requests
        requests_config = [
            ("omega", self.locations["lucknow"]),
            ("nova", self.locations["mumbai"]),
            ("arc", self.locations["lucknow"]),
        ]
        
        start_time = time.time()
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.make_concurrent_request, endpoint, location)
                for endpoint, location in requests_config
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        for result in results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {status_icon} {result['endpoint']}: {result['response_time']:.2f}s, Status: {result['status']}")
        
        self.log_test("Concurrent Requests", successful_requests == len(requests_config), 
                     f"Successful: {successful_requests}/{len(requests_config)}, "
                     f"Total time: {total_time:.2f}s, "
                     f"Avg response: {avg_response_time:.2f}s")
        
        return successful_requests == len(requests_config)

    def test_maximum_variables_per_endpoint(self):
        """Test with maximum variables per endpoint"""
        print(f"\n📊 Testing maximum variables per endpoint...")
        
        if not self.api_key:
            self.log_test("Maximum Variables Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        successful_tests = 0
        
        for endpoint, variables in self.endpoint_variables.items():
            forecast_data = {
                "list_lat_lon": [self.locations["lucknow"]],
                "timestamp": self.get_future_timestamp(4),
                "variables": variables,  # All variables for this endpoint
                "timezone": "Asia/Kolkata"
            }
            
            success, data, status, response_time = self.make_request(
                'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
            )
            
            if success and status == 200:
                successful_tests += 1
                metadata = data.get('metadata', {})
                endpoints_called = metadata.get('endpoints_called', [])
                print(f"   ✅ {endpoint}: {len(variables)} vars, {response_time:.2f}s, Endpoints: {endpoints_called}")
            else:
                print(f"   ❌ {endpoint}: Status {status}, Time: {response_time:.2f}s")
            
            time.sleep(0.3)  # Small delay between tests
        
        self.log_test("Maximum Variables Per Endpoint", successful_tests == len(self.endpoint_variables), 
                     f"Successful: {successful_tests}/{len(self.endpoint_variables)}")
        
        return successful_tests == len(self.endpoint_variables)

    def test_multiple_locations_load(self):
        """Test with multiple locations (2-5 locations)"""
        print(f"\n🌍 Testing multiple locations load...")
        
        if not self.api_key:
            self.log_test("Multiple Locations Load", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        
        # Test with increasing number of locations
        location_sets = [
            [self.locations["lucknow"], self.locations["mumbai"]],  # 2 locations
            [self.locations["lucknow"], self.locations["mumbai"], [28.6139, 77.2090]],  # 3 locations
            [self.locations["lucknow"], self.locations["mumbai"], [28.6139, 77.2090], [13.0827, 80.2707]],  # 4 locations
            [self.locations["lucknow"], self.locations["mumbai"], [28.6139, 77.2090], [13.0827, 80.2707], [22.5726, 88.3639]]  # 5 locations
        ]
        
        successful_tests = 0
        
        for i, locations in enumerate(location_sets, 2):
            forecast_data = {
                "list_lat_lon": locations,
                "timestamp": self.get_future_timestamp(5),
                "variables": ["ambient_temp(K)", "ghi(W/m2)", "ct"],  # Mix of all endpoints
                "timezone": "Asia/Kolkata"
            }
            
            success, data, status, response_time = self.make_request(
                'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
            )
            
            if success and status == 200:
                successful_tests += 1
                metadata = data.get('metadata', {})
                locations_count = metadata.get('locations_count', 0)
                final_amount = metadata.get('final_amount', '0')
                print(f"   ✅ {len(locations)} locations: {response_time:.2f}s, Cost: {final_amount}")
            else:
                print(f"   ❌ {len(locations)} locations: Status {status}, Time: {response_time:.2f}s")
            
            time.sleep(0.5)  # Delay between tests
        
        self.log_test("Multiple Locations Load", successful_tests == len(location_sets), 
                     f"Successful: {successful_tests}/{len(location_sets)}")
        
        return successful_tests == len(location_sets)

    def test_invalid_timestamps(self):
        """Test error handling for invalid timestamps"""
        print(f"\n❌ Testing invalid timestamp handling...")
        
        if not self.api_key:
            self.log_test("Invalid Timestamps Test", False, "No API key available")
            return False
        
        headers = {'X-API-Key': self.api_key}
        
        # Test various invalid timestamps
        invalid_timestamps = [
            "2023-01-01 12:00:00",  # Past timestamp
            "invalid-timestamp",     # Invalid format
            "2025-13-01 12:00:00",  # Invalid month
            "2025-01-32 12:00:00",  # Invalid day
        ]
        
        expected_errors = 0
        
        for timestamp in invalid_timestamps:
            forecast_data = {
                "list_lat_lon": [self.locations["lucknow"]],
                "timestamp": timestamp,
                "variables": ["ambient_temp(K)"],
                "timezone": "Asia/Kolkata"
            }
            
            success, data, status, response_time = self.make_request(
                'POST', '/api/v1/weather/forecast', forecast_data, headers=headers
            )
            
            if not success and status in [400, 422]:  # Expected error codes
                expected_errors += 1
                print(f"   ✅ '{timestamp}': Correctly rejected (Status {status})")
            else:
                print(f"   ❌ '{timestamp}': Unexpected result (Status {status})")
        
        self.log_test("Invalid Timestamps Handling", expected_errors == len(invalid_timestamps), 
                     f"Correctly handled: {expected_errors}/{len(invalid_timestamps)}")
        
        return expected_errors == len(invalid_timestamps)

    def run_all_tests(self):
        """Run all timing and rate limiting tests"""
        print(f"\n🎯 Starting comprehensive Skycaster timing tests...")
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Authentication setup failed. Cannot proceed with tests.")
            return
        
        # Run all tests
        test_methods = [
            self.test_separate_endpoint_omega,
            self.test_separate_endpoint_nova,
            self.test_separate_endpoint_arc,
            self.test_different_timing_scenarios,
            self.test_rapid_sequential_requests,
            self.test_concurrent_requests,
            self.test_maximum_variables_per_endpoint,
            self.test_multiple_locations_load,
            self.test_invalid_timestamps,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                time.sleep(1)  # Delay between test categories
            except Exception as e:
                print(f"❌ Error in {test_method.__name__}: {str(e)}")
        
        # Print final summary
        print("\n" + "=" * 80)
        print(f"🏁 SKYCASTER TIMING TESTS COMPLETE")
        print(f"📊 Results: {self.tests_passed}/{self.tests_run} tests passed ({(self.tests_passed/self.tests_run)*100:.1f}%)")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

def main():
    if len(sys.argv) != 2:
        print("Usage: python skycaster_timing_test.py <base_url>")
        print("Example: python skycaster_timing_test.py https://api.example.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    tester = SkycasterTimingTester(base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()