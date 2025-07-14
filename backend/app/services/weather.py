import httpx
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config import settings
from app.schemas.weather import WeatherResponse

class WeatherService:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = settings.WEATHER_API_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> WeatherResponse:
        """Make HTTP request to WeatherAPI.com"""
        try:
            # Add API key to parameters
            params['key'] = self.api_key
            url = f"{self.base_url}/{endpoint}"
            
            logger.info(f"Making weather API request to: {url}")
            logger.debug(f"Request parameters: {params}")
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return WeatherResponse(
                    success=True,
                    data=data,
                    provider="weatherapi.com",
                    usage_cost=1.0
                )
            else:
                error_msg = f"Weather API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WeatherResponse(
                    success=False,
                    error=error_msg,
                    provider="weatherapi.com",
                    usage_cost=0.0
                )
                
        except httpx.TimeoutException:
            error_msg = "Weather API request timed out"
            logger.error(error_msg)
            return WeatherResponse(
                success=False,
                error=error_msg,
                provider="weatherapi.com",
                usage_cost=0.0
            )
        except Exception as e:
            error_msg = f"Weather API request failed: {str(e)}"
            logger.error(error_msg)
            return WeatherResponse(
                success=False,
                error=error_msg,
                provider="weatherapi.com",
                usage_cost=0.0
            )
    
    async def get_current_weather(self, location: str) -> WeatherResponse:
        """Get current weather for a location"""
        return await self._make_request("current.json", {"q": location})
    
    async def get_forecast(self, location: str, days: int = 3) -> WeatherResponse:
        """Get weather forecast for a location"""
        if days > 10:
            days = 10  # API limit
        return await self._make_request("forecast.json", {"q": location, "days": days})
    
    async def get_history(self, location: str, date: str) -> WeatherResponse:
        """Get historical weather data"""
        return await self._make_request("history.json", {"q": location, "dt": date})
    
    async def get_future(self, location: str, date: str) -> WeatherResponse:
        """Get future weather data"""
        return await self._make_request("future.json", {"q": location, "dt": date})
    
    async def search_locations(self, query: str) -> WeatherResponse:
        """Search for locations"""
        response = await self._make_request("search.json", {"q": query})
        
        # WeatherAPI returns a list for search, but we want consistent structure
        if response.success and isinstance(response.data, list):
            response.data = {"locations": response.data}
        
        return response
    
    async def get_astronomy(self, location: str, date: str) -> WeatherResponse:
        """Get astronomy data for a location"""
        return await self._make_request("astronomy.json", {"q": location, "dt": date})
    
    async def get_marine(self, location: str) -> WeatherResponse:
        """Get marine weather data"""
        return await self._make_request("marine.json", {"q": location})
    
    async def get_ip_lookup(self, ip: str) -> WeatherResponse:
        """Get location data for an IP address"""
        return await self._make_request("ip.json", {"q": ip})
    
    async def get_timezone(self, location: str) -> WeatherResponse:
        """Get timezone information for a location"""
        return await self._make_request("timezone.json", {"q": location})
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def get_supported_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Get list of supported weather endpoints"""
        return {
            "current": {
                "name": "Current Weather",
                "description": "Get real-time weather conditions",
                "parameters": ["location"],
                "example": "/weather/current?location=London"
            },
            "forecast": {
                "name": "Weather Forecast",
                "description": "Get weather forecast up to 10 days",
                "parameters": ["location", "days (optional, default=3)"],
                "example": "/weather/forecast?location=London&days=7"
            },
            "history": {
                "name": "Historical Weather",
                "description": "Get historical weather data",
                "parameters": ["location", "date (YYYY-MM-DD)"],
                "example": "/weather/history?location=London&date=2023-01-01"
            },
            "future": {
                "name": "Future Weather",
                "description": "Get future weather data up to 365 days",
                "parameters": ["location", "date (YYYY-MM-DD)"],
                "example": "/weather/future?location=London&date=2024-06-01"
            },
            "search": {
                "name": "Location Search",
                "description": "Search for locations",
                "parameters": ["query"],
                "example": "/weather/search?query=London"
            },
            "astronomy": {
                "name": "Astronomy Data",
                "description": "Get sunrise, sunset, and moon phase data",
                "parameters": ["location", "date (YYYY-MM-DD)"],
                "example": "/weather/astronomy?location=London&date=2023-01-01"
            },
            "marine": {
                "name": "Marine Weather",
                "description": "Get marine weather and tide information",
                "parameters": ["location"],
                "example": "/weather/marine?location=London"
            },
            "timezone": {
                "name": "Timezone",
                "description": "Get timezone information",
                "parameters": ["location"],
                "example": "/weather/timezone?location=London"
            }
        }