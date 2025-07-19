import httpx
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pytz
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pricing_config import PricingConfig, CurrencyConfig, VariableMapping, WeatherRequest
from app.models.user import User
from app.models.api_key import ApiKey

class SkycasterWeatherService:
    """
    Intelligent weather service that routes requests to appropriate Skycaster endpoints
    based on selected variables and handles dynamic pricing.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock  # Flag for testing with mock data
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Endpoint mappings
        self.endpoint_variables = {
            "omega": ["ambient_temp(K)", "wind_10m", "wind_100m", "relative_humidity(%)"],
            "nova": ["temperature(K)", "surface_pressure(Pa)", "cumulus_precipitation(mm)", 
                    "ghi(W/m2)", "ghi_farms(W/m2)", "clear_sky_ghi_farms(W/m2)", "albedo"],
            "arc": ["ct", "pc", "pcph"]
        }
        
        # Reverse mapping for quick lookup
        self.variable_to_endpoint = {}
        for endpoint, variables in self.endpoint_variables.items():
            for var in variables:
                self.variable_to_endpoint[var] = endpoint
    
    async def get_forecast(
        self,
        locations: List[List[float]],
        variables: List[str],
        timestamp: str,
        timezone: str = "Asia/Kolkata",
        user: User = None,
        api_key: ApiKey = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Get weather forecast with intelligent endpoint routing
        
        Args:
            locations: List of [lat, lon] pairs
            variables: List of variable names to fetch
            timestamp: Timestamp in "YYYY-MM-DD HH:MM:SS" format
            timezone: Timezone for timestamp formatting
            user: User making the request
            api_key: API key used for the request
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Unified weather response with pricing information
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate timestamp is in the future
            try:
                # Parse the timestamp
                timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                # Add timezone awareness
                tz = pytz.timezone(timezone)
                timestamp_dt = tz.localize(timestamp_dt)
                
                # Check if timestamp is in the future (allowing 1 hour buffer)
                current_time = datetime.now(tz)
                if timestamp_dt <= current_time:
                    raise ValueError(f"Timestamp must be in the future. Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}, Requested: {timestamp_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
            except Exception as e:
                if "Timestamp must be in the future" in str(e):
                    raise e
                else:
                    raise ValueError(f"Invalid timestamp format. Expected 'YYYY-MM-DD HH:MM:SS': {e}")
            
            # Validate variables
            invalid_vars = [var for var in variables if var not in self.variable_to_endpoint]
            if invalid_vars:
                raise ValueError(f"Invalid variables: {invalid_vars}")
            
            # Group variables by endpoint
            endpoint_groups = self._group_variables_by_endpoint(variables)
            
            # Get pricing information
            db = next(get_db())
            pricing_info = await self._calculate_pricing(db, variables, len(locations), user, ip_address)
            
            # Make parallel API calls to different endpoints
            endpoint_responses = await self._make_parallel_requests(
                endpoint_groups, locations, timestamp, timezone
            )
            
            # Merge responses
            unified_response = self._merge_endpoint_responses(endpoint_responses, locations)
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log the request
            await self._log_weather_request(
                db, user, api_key, locations, variables, timestamp, timezone,
                list(endpoint_groups.keys()), 200, response_time, True, pricing_info,
                ip_address, user_agent
            )
            
            # Build final response
            response = {
                "location_data": unified_response,
                "metadata": {
                    "timestamp": timestamp,
                    "timezone": timezone,
                    "endpoints_called": list(endpoint_groups.keys()),
                    "variables_requested": variables,
                    "locations_count": len(locations),
                    **pricing_info
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in weather forecast: {str(e)}")
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log failed request
            if user and api_key:
                db = next(get_db())
                await self._log_weather_request(
                    db, user, api_key, locations, variables, timestamp, timezone,
                    [], 500, response_time, False, {"total_cost": 0, "currency": "INR"},
                    ip_address, user_agent
                )
            
            raise e
    
    def _group_variables_by_endpoint(self, variables: List[str]) -> Dict[str, List[str]]:
        """Group variables by their corresponding endpoints"""
        groups = {}
        
        for var in variables:
            endpoint = self.variable_to_endpoint[var]
            if endpoint not in groups:
                groups[endpoint] = []
            groups[endpoint].append(var)
        
        return groups
    
    async def _make_parallel_requests(
        self,
        endpoint_groups: Dict[str, List[str]],
        locations: List[List[float]],
        timestamp: str,
        timezone: str
    ) -> Dict[str, Any]:
        """Make parallel requests to different Skycaster endpoints"""
        
        if self.use_mock:
            return await self._get_mock_responses(endpoint_groups, locations)
        
        # Create tasks for parallel execution
        tasks = []
        endpoint_urls = {
            "omega": "https://apidelta.skycaster.in/forecast/multiple/omega",
            "nova": "https://apidelta.skycaster.in/forecast/multiple/nova",
            "arc": "https://apidelta.skycaster.in/forecast/multiple/arc"
        }
        
        for endpoint, variables in endpoint_groups.items():
            url = endpoint_urls[endpoint]
            payload = {
                "list_lat_lon": locations,
                "timestamp": timestamp,
                "variables": variables,
                "timezone": timezone
            }
            
            task = self._make_endpoint_request(endpoint, url, payload)
            tasks.append(task)
        
        # Execute all requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        responses = {}
        for i, result in enumerate(results):
            endpoint = list(endpoint_groups.keys())[i]
            if isinstance(result, Exception):
                logger.error(f"Error in {endpoint} endpoint: {result}")
                responses[endpoint] = {"error": str(result)}
            else:
                responses[endpoint] = result
        
        return responses
    
    async def _make_endpoint_request(
        self,
        endpoint: str,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make request to a single Skycaster endpoint"""
        try:
            logger.info(f"Making request to {endpoint} endpoint: {url}")
            logger.debug(f"Payload: {payload}")
            
            response = await self.client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "endpoint": endpoint,
                    "variables": payload["variables"]
                }
            else:
                # Try to parse JSON error response
                try:
                    error_data = response.json()
                    if "Error" in error_data:
                        error_msg = f"Skycaster API Error: {error_data['Error']}"
                    else:
                        error_msg = f"HTTP {response.status_code}: {error_data}"
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                
                logger.error(f"Error from {endpoint}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "endpoint": endpoint,
                    "variables": payload["variables"]
                }
                
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"Error in {endpoint} request: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "endpoint": endpoint,
                "variables": payload["variables"]
            }
    
    def _merge_endpoint_responses(
        self,
        endpoint_responses: Dict[str, Any],
        locations: List[List[float]]
    ) -> Dict[str, Dict[str, Any]]:
        """Merge responses from different endpoints into unified format"""
        unified_response = {}
        
        # Initialize location data structure
        for location in locations:
            location_key = f"{location[0]},{location[1]}"
            unified_response[location_key] = {}
        
        # Merge data from each endpoint
        for endpoint, response in endpoint_responses.items():
            logger.info(f"Processing {endpoint} endpoint response: success={response.get('success')}")
            if response.get("success") and "data" in response:
                data = response["data"]
                variables = response["variables"]
                logger.info(f"{endpoint} data type: {type(data)}, variables: {variables}")
                
                # Handle the data structure from Skycaster API
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]  # Extract the actual data array
                
                # Process location data
                for i, location in enumerate(locations):
                    location_key = f"{location[0]},{location[1]}"
                    
                    # Extract data for this location from the response
                    if isinstance(data, list) and i < len(data):
                        location_data = data[i]
                        logger.info(f"{endpoint} location {i} data keys: {list(location_data.keys()) if location_data else 'None'}")
                    elif isinstance(data, dict) and location_key in data:
                        location_data = data[location_key]
                    else:
                        # Try to find location data in various formats
                        location_data = self._extract_location_data(data, location, i)
                    
                    # Add variable data to unified response
                    if location_data:
                        for var in variables:
                            # Handle variable name mapping for wind data
                            mapped_var = self._map_variable_name(var, location_data)
                            if mapped_var and mapped_var in location_data:
                                unified_response[location_key][var] = location_data[mapped_var]
                            elif var in location_data:
                                unified_response[location_key][var] = location_data[var]
                            else:
                                logger.warning(f"Variable {var} (mapped: {mapped_var}) not found in {endpoint} response for location {location_key}")
            else:
                logger.warning(f"{endpoint} endpoint failed: {response.get('error', 'Unknown error')}")
        
        return unified_response
    
    def _extract_location_data(self, data: Any, location: List[float], index: int) -> Dict[str, Any]:
        """Extract location data from various response formats"""
        # Handle different response formats from Skycaster API
        if isinstance(data, dict):
            # Try different key formats
            location_key = f"{location[0]},{location[1]}"
            possible_keys = [
                location_key,
                f"{location[0]}_{location[1]}",
                f"lat_{location[0]}_lon_{location[1]}",
                str(index)
            ]
            
            for key in possible_keys:
                if key in data:
                    return data[key]
        
        elif isinstance(data, list) and index < len(data):
            return data[index]
        
        return {}
    
    def _map_variable_name(self, requested_var: str, location_data: Dict[str, Any]) -> Optional[str]:
        """Map requested variable names to API response field names"""
        
        # Wind variable mappings
        wind_mappings = {
            "wind_10m": "wind_speed_10",
            "wind_100m": "wind_speed_100"
        }
        
        # Check if we have a direct mapping
        if requested_var in wind_mappings:
            mapped_name = wind_mappings[requested_var]
            if mapped_name in location_data:
                return mapped_name
        
        # For complex wind data, we might need to combine speed and direction
        if requested_var == "wind_10m" and "wind_speed_10" in location_data and "direction_10" in location_data:
            # For now, return just the speed component
            # In the future, could return structured wind data with both speed and direction
            return "wind_speed_10"
        
        if requested_var == "wind_100m" and "wind_speed_100" in location_data and "direction_100" in location_data:
            return "wind_speed_100"
        
        return None
    
    async def _get_mock_responses(
        self,
        endpoint_groups: Dict[str, List[str]],
        locations: List[List[float]]
    ) -> Dict[str, Any]:
        """Generate mock responses for testing"""
        responses = {}
        
        for endpoint, variables in endpoint_groups.items():
            location_data = {}
            
            for i, location in enumerate(locations):
                location_key = f"{location[0]},{location[1]}"
                var_data = {}
                
                for var in variables:
                    # Generate mock data based on variable type
                    if "temp" in var.lower():
                        var_data[var] = 298.15 + (i * 2)  # Temperature in Kelvin
                    elif "wind" in var.lower():
                        var_data[var] = 5.5 + (i * 0.5)  # Wind speed
                    elif "humidity" in var.lower():
                        var_data[var] = 65.0 + (i * 2)  # Humidity percentage
                    elif "pressure" in var.lower():
                        var_data[var] = 101325 + (i * 100)  # Pressure in Pa
                    elif "precipitation" in var.lower():
                        var_data[var] = 0.5 + (i * 0.1)  # Precipitation in mm
                    elif "ghi" in var.lower():
                        var_data[var] = 800 + (i * 50)  # GHI in W/m2
                    elif "albedo" in var.lower():
                        var_data[var] = 0.15 + (i * 0.01)  # Albedo
                    else:
                        var_data[var] = 0.8 + (i * 0.1)  # Default value
                
                location_data[location_key] = var_data
            
            responses[endpoint] = {
                "success": True,
                "data": location_data,
                "endpoint": endpoint,
                "variables": variables
            }
        
        return responses
    
    async def _calculate_pricing(
        self,
        db: Session,
        variables: List[str],
        location_count: int,
        user: User,
        ip_address: str
    ) -> Dict[str, Any]:
        """Calculate pricing for the request"""
        # Get pricing configs
        pricing_configs = db.query(PricingConfig).filter(
            PricingConfig.variable_name.in_(variables),
            PricingConfig.is_active == True
        ).all()
        
        # Calculate base cost
        total_cost = 0.0
        currency = "INR"
        
        for config in pricing_configs:
            # Use plan-specific pricing if available
            plan_price = self._get_plan_price(config, user)
            variable_cost = plan_price * location_count
            total_cost += variable_cost
        
        # Handle missing pricing configs (fallback to ₹1 per variable per location)
        configured_variables = [config.variable_name for config in pricing_configs]
        missing_variables = [var for var in variables if var not in configured_variables]
        total_cost += len(missing_variables) * location_count * 1.0
        
        # Get currency based on IP address
        if ip_address:
            currency = await self._get_currency_from_ip(db, ip_address)
        
        # Convert currency if needed
        if currency != "INR":
            total_cost = await self._convert_currency(db, total_cost, "INR", currency)
        
        # Calculate tax
        tax_rate = 18.0  # Default GST rate
        tax_enabled = True
        
        if pricing_configs:
            # Use tax settings from first config (assuming all have same tax settings)
            tax_rate = pricing_configs[0].tax_rate
            tax_enabled = pricing_configs[0].tax_enabled
        
        tax_amount = (total_cost * tax_rate / 100) if tax_enabled else 0.0
        final_amount = total_cost + tax_amount
        
        return {
            "total_cost": f"{total_cost:.2f}",
            "currency": currency,
            "tax_applied": "Yes" if tax_enabled else "No",
            "tax_rate": f"{tax_rate}%",
            "tax_amount": f"{tax_amount:.2f}",
            "final_amount": f"{final_amount:.2f}"
        }
    
    def _get_plan_price(self, config: PricingConfig, user: User) -> float:
        """Get plan-specific price for a variable"""
        if not user:
            return config.base_price
        
        # Get user's subscription plan
        # This would need to be implemented based on your subscription model
        user_plan = "free"  # Default, should be fetched from user's subscription
        
        plan_price_map = {
            "free": config.free_plan_price,
            "developer": config.developer_plan_price,
            "business": config.business_plan_price,
            "enterprise": config.enterprise_plan_price
        }
        
        return plan_price_map.get(user_plan) or config.base_price
    
    async def _get_currency_from_ip(self, db: Session, ip_address: str) -> str:
        """Get currency based on IP address geolocation"""
        # This is a simplified implementation
        # In production, you'd use a proper IP geolocation service
        
        # For now, return INR as default
        # You can integrate with services like ipapi.co, ipstack.com, etc.
        return "INR"
    
    async def _convert_currency(self, db: Session, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        # Get exchange rates
        to_currency_config = db.query(CurrencyConfig).filter(
            CurrencyConfig.currency_code == to_currency,
            CurrencyConfig.is_active == True
        ).first()
        
        if not to_currency_config:
            return amount  # Return original amount if currency not found
        
        # Convert from INR to target currency
        return amount * to_currency_config.exchange_rate
    
    async def _log_weather_request(
        self,
        db: Session,
        user: User,
        api_key: ApiKey,
        locations: List[List[float]],
        variables: List[str],
        timestamp: str,
        timezone: str,
        endpoints_called: List[str],
        response_status: int,
        response_time: float,
        success: bool,
        pricing_info: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """Log weather request to database"""
        try:
            # Extract pricing values
            total_cost = float(pricing_info.get("total_cost", "0").replace(",", ""))
            tax_amount = float(pricing_info.get("tax_amount", "0").replace(",", ""))
            final_amount = float(pricing_info.get("final_amount", "0").replace(",", ""))
            currency = pricing_info.get("currency", "INR")
            
            # Detect country from IP (simplified)
            country_code = "IN"  # Default, would use IP geolocation service
            
            weather_request = WeatherRequest(
                user_id=user.id if user else None,
                api_key_id=api_key.id if api_key else None,
                locations=json.dumps(locations),
                variables=json.dumps(variables),
                timestamp=timestamp,
                timezone=timezone,
                endpoints_called=json.dumps(endpoints_called),
                response_status=response_status,
                response_time=response_time,
                success=success,
                total_cost=total_cost,
                currency=currency,
                tax_applied=tax_amount,
                final_amount=final_amount,
                ip_address=ip_address,
                user_agent=user_agent,
                country_code=country_code
            )
            
            db.add(weather_request)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging weather request: {e}")
            db.rollback()
    
    def _format_timezone(self, timestamp: str, timezone: str) -> str:
        """Format timestamp according to specified timezone"""
        try:
            # Parse timestamp
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            # Set timezone
            tz = pytz.timezone(timezone)
            dt = tz.localize(dt)
            
            # Return formatted timestamp
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            
        except Exception as e:
            logger.error(f"Error formatting timezone: {e}")
            return timestamp
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def get_supported_variables(self) -> Dict[str, List[str]]:
        """Get list of supported variables grouped by endpoint"""
        return self.endpoint_variables.copy()
    
    def get_variable_info(self, db: Session) -> List[Dict[str, Any]]:
        """Get detailed information about all supported variables"""
        variables = db.query(VariableMapping).filter(
            VariableMapping.is_active == True
        ).all()
        
        return [
            {
                "variable_name": var.variable_name,
                "endpoint_type": var.endpoint_type,
                "description": var.description,
                "unit": var.unit,
                "data_type": var.data_type
            }
            for var in variables
        ]