from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
import time

from app.core.database import get_db
from app.core.dependencies import get_api_key_user
from app.services.weather import WeatherService
from app.services.usage_log import UsageLogService
from app.schemas.weather import WeatherResponse, WeatherRequest
from app.schemas.usage_log import UsageLogCreate

router = APIRouter()

# Initialize weather service
weather_service = WeatherService()

async def log_weather_request(
    db: Session,
    user_id: str,
    api_key_id: str,
    request: Request,
    endpoint: str,
    location: str,
    response_status: int,
    response_time: float,
    success: bool,
    cost: float = 1.0
):
    """Log weather API request"""
    usage_log = UsageLogCreate(
        endpoint=endpoint,
        method=request.method,
        location=location,
        request_params=dict(request.query_params),
        request_headers=dict(request.headers),
        response_status=response_status,
        response_time=response_time,
        success=success,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        cost=cost
    )
    
    UsageLogService.create_usage_log(db, usage_log, user_id, api_key_id)

@router.get("/current", response_model=dict)
async def get_current_weather(
    location: str,
    request: Request,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get current weather conditions for a location
    
    - **location**: City name, coordinates, or postal code
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_current_weather(location)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/current",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/current",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/forecast", response_model=dict)
async def get_weather_forecast(
    location: str,
    days: int = 3,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get weather forecast for a location
    
    - **location**: City name, coordinates, or postal code
    - **days**: Number of forecast days (1-10, default: 3)
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    # Validate days parameter
    if days < 1 or days > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 10"
        )
    
    try:
        response = await weather_service.get_forecast(location, days)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/forecast",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/forecast",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history", response_model=dict)
async def get_weather_history(
    location: str,
    date: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get historical weather data for a location
    
    - **location**: City name, coordinates, or postal code
    - **date**: Date in YYYY-MM-DD format
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_history(location, date)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/history",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/history",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/search", response_model=dict)
async def search_locations(
    query: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Search for locations
    
    - **query**: Search query (city name, coordinates, etc.)
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.search_locations(query)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/search",
            query, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/search",
            query, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/astronomy", response_model=dict)
async def get_astronomy_data(
    location: str,
    date: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get astronomy data for a location
    
    - **location**: City name, coordinates, or postal code
    - **date**: Date in YYYY-MM-DD format
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_astronomy(location, date)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/astronomy",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/astronomy",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/future", response_model=dict)
async def get_future_weather(
    location: str,
    date: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get future weather data for a location
    
    - **location**: City name, coordinates, or postal code
    - **date**: Future date in YYYY-MM-DD format (up to 365 days ahead)
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_future(location, date)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/future",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/future",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/marine", response_model=dict)
async def get_marine_weather(
    location: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get marine weather data for a location
    
    - **location**: City name, coordinates, or postal code
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_marine(location)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/marine",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/marine",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/timezone", response_model=dict)
async def get_timezone_info(
    location: str,
    request: Request = None,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get timezone information for a location
    
    - **location**: City name, coordinates, or postal code
    """
    user, api_key, subscription = auth_data
    start_time = time.time()
    
    try:
        response = await weather_service.get_timezone(location)
        response_time = time.time() - start_time
        
        # Log the request
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/timezone",
            location, 200 if response.success else 500, response_time,
            response.success, response.usage_cost
        )
        
        if response.success:
            return {
                "success": True,
                "data": response.data,
                "provider": response.provider,
                "usage_cost": response.usage_cost
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        response_time = time.time() - start_time
        await log_weather_request(
            db, user.id, api_key.id, request, "/weather/timezone",
            location, 500, response_time, False, 0
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/endpoints", response_model=dict)
async def get_supported_endpoints():
    """Get list of all supported weather endpoints"""
    return {
        "endpoints": weather_service.get_supported_endpoints(),
        "authentication": "API Key required in X-API-Key header",
        "rate_limits": "Based on subscription plan"
    }