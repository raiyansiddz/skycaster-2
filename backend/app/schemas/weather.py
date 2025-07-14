from pydantic import BaseModel
from typing import Optional, Dict, Any

class WeatherRequest(BaseModel):
    location: str
    days: Optional[int] = None
    date: Optional[str] = None

class WeatherResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: str = "weatherapi.com"
    usage_cost: float = 1.0
    
class WeatherCurrentResponse(BaseModel):
    location: Dict[str, Any]
    current: Dict[str, Any]
    
class WeatherForecastResponse(BaseModel):
    location: Dict[str, Any]
    current: Dict[str, Any]
    forecast: Dict[str, Any]
    
class WeatherHistoryResponse(BaseModel):
    location: Dict[str, Any]
    forecast: Dict[str, Any]
    
class WeatherAstronomyResponse(BaseModel):
    location: Dict[str, Any]
    astronomy: Dict[str, Any]

class WeatherSearchResponse(BaseModel):
    locations: list[Dict[str, Any]]