from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class WeatherResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: str
    usage_cost: float = 0.0  # Cost in credits/units

class WeatherProvider(ABC):
    """Base class for weather providers"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    async def get_current_weather(self, location: str) -> WeatherResponse:
        """Get current weather for a location"""
        pass
    
    @abstractmethod
    async def get_forecast(self, location: str, days: int = 3) -> WeatherResponse:
        """Get weather forecast for a location"""
        pass
    
    @abstractmethod
    async def get_history(self, location: str, date: str) -> WeatherResponse:
        """Get historical weather data"""
        pass
    
    @abstractmethod
    async def search_locations(self, query: str) -> WeatherResponse:
        """Search for locations"""
        pass
    
    @abstractmethod
    async def get_astronomy(self, location: str, date: str) -> WeatherResponse:
        """Get astronomy data"""
        pass