import httpx
from typing import Dict, Any, Optional
from .base import WeatherProvider, WeatherResponse
import logging

logger = logging.getLogger(__name__)

class WeatherAPIProvider(WeatherProvider):
    """WeatherAPI.com provider implementation"""
    
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key, base_url)
        self.client = httpx.AsyncClient()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> WeatherResponse:
        """Make HTTP request to WeatherAPI.com"""
        try:
            params['key'] = self.api_key
            url = f"{self.base_url}/{endpoint}"
            
            logger.info(f"Making request to: {url} with params: {params}")
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return WeatherResponse(
                    success=True,
                    data=data,
                    provider="weatherapi.com",
                    usage_cost=1.0  # 1 credit per request
                )
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WeatherResponse(
                    success=False,
                    error=error_msg,
                    provider="weatherapi.com"
                )
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return WeatherResponse(
                success=False,
                error=error_msg,
                provider="weatherapi.com"
            )
    
    async def get_current_weather(self, location: str) -> WeatherResponse:
        """Get current weather for a location"""
        return await self._make_request("current.json", {"q": location})
    
    async def get_forecast(self, location: str, days: int = 3) -> WeatherResponse:
        """Get weather forecast for a location"""
        return await self._make_request("forecast.json", {"q": location, "days": days})
    
    async def get_future(self, location: str, date: str) -> WeatherResponse:
        """Get future weather data"""
        return await self._make_request("future.json", {"q": location, "dt": date})
    
    async def get_history(self, location: str, date: str) -> WeatherResponse:
        """Get historical weather data"""
        return await self._make_request("history.json", {"q": location, "dt": date})
    
    async def get_marine(self, location: str) -> WeatherResponse:
        """Get marine weather data"""
        return await self._make_request("marine.json", {"q": location})
    
    async def search_locations(self, query: str) -> WeatherResponse:
        """Search for locations"""
        try:
            params = {"q": query}
            params['key'] = self.api_key
            url = f"{self.base_url}/search.json"
            
            logger.info(f"Making request to: {url} with params: {params}")
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                # WeatherAPI search returns a list, so we wrap it in a dict
                return WeatherResponse(
                    success=True,
                    data={"locations": data},  # Wrap list in dict
                    provider="weatherapi.com",
                    usage_cost=1.0
                )
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WeatherResponse(
                    success=False,
                    error=error_msg,
                    provider="weatherapi.com"
                )
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return WeatherResponse(
                success=False,
                error=error_msg,
                provider="weatherapi.com"
            )
    
    async def get_ip_lookup(self, ip: str) -> WeatherResponse:
        """Get IP location data"""
        return await self._make_request("ip.json", {"q": ip})
    
    async def get_timezone(self, location: str) -> WeatherResponse:
        """Get timezone information"""
        return await self._make_request("timezone.json", {"q": location})
    
    async def get_astronomy(self, location: str, date: str) -> WeatherResponse:
        """Get astronomy data"""
        return await self._make_request("astronomy.json", {"q": location, "dt": date})
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()