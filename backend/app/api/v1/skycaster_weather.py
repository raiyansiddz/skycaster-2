from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, List
import time
import json
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_api_key_user
from app.core.config import settings
from app.services.skycaster_weather import SkycasterWeatherService
from app.schemas.skycaster_weather import (
    WeatherForecastRequest,
    WeatherForecastResponse,
    SupportedVariablesResponse,
    PricingResponse,
    WeatherUsageStatsResponse,
    ErrorResponse,
    VariableInfo,
    PricingInfo,
    WeatherRequestLog
)
from app.models.pricing_config import PricingConfig, WeatherRequest

router = APIRouter()

# Initialize Skycaster weather service
# Use mock data if USE_MOCK_WEATHER is set to True in environment
use_mock = settings.__dict__.get("USE_MOCK_WEATHER", False)
skycaster_service = SkycasterWeatherService(use_mock=use_mock)

@router.post("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    request_data: WeatherForecastRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get weather forecast using Skycaster's intelligent routing system
    
    This endpoint automatically routes requests to the appropriate Skycaster endpoints
    (omega, nova, arc) based on the selected variables. It supports:
    
    - **Batch location processing**: Multiple locations in a single request
    - **Variable-based routing**: Intelligent endpoint selection
    - **Dynamic pricing**: Per-variable, per-location pricing
    - **Timezone handling**: Configurable timezone for timestamps
    - **Currency conversion**: IP-based currency detection
    
    **Supported Variables:**
    - **Omega**: ambient_temp(K), wind_10m, wind_100m, relative_humidity(%)
    - **Nova**: temperature(K), surface_pressure(Pa), cumulus_precipitation(mm), ghi(W/m2), ghi_farms(W/m2), clear_sky_ghi_farms(W/m2), albedo
    - **Arc**: ct, pc, pcph
    
    **Pricing**: ₹1 per variable per location (+ applicable taxes)
    """
    user, api_key, subscription = auth_data
    
    try:
        # Get client information
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Make request to Skycaster service
        response = await skycaster_service.get_forecast(
            locations=request_data.list_lat_lon,
            variables=request_data.variables,
            timestamp=request_data.timestamp,
            timezone=request_data.timezone,
            user=user,
            api_key=api_key,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return WeatherForecastResponse(**response)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Weather forecast request failed: {str(e)}"
        )

@router.get("/variables", response_model=SupportedVariablesResponse)
async def get_supported_variables(
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get list of all supported weather variables
    
    Returns detailed information about all available weather variables,
    grouped by their respective endpoints (omega, nova, arc).
    """
    try:
        # Get variable information from database
        variable_info = skycaster_service.get_variable_info(db)
        
        # Get supported variables grouped by endpoint
        endpoints = skycaster_service.get_supported_variables()
        
        # Convert to response format
        variables = [
            VariableInfo(
                variable_name=var["variable_name"],
                endpoint_type=var["endpoint_type"],
                description=var["description"],
                unit=var["unit"],
                data_type=var["data_type"]
            )
            for var in variable_info
        ]
        
        return SupportedVariablesResponse(
            variables=variables,
            endpoints=endpoints
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch supported variables: {str(e)}"
        )

@router.get("/pricing", response_model=PricingResponse)
async def get_pricing_information(
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get pricing information for all weather variables
    
    Returns current pricing configuration including:
    - Base price per variable per location
    - Tax rates and tax enablement
    - Plan-specific pricing (if applicable)
    - Currency information
    """
    try:
        # Get pricing configurations
        pricing_configs = db.query(PricingConfig).filter(
            PricingConfig.is_active == True
        ).all()
        
        # Convert to response format
        pricing_info = [
            PricingInfo(
                variable_name=config.variable_name,
                endpoint_type=config.endpoint_type,
                base_price=config.base_price,
                currency=config.currency,
                tax_rate=config.tax_rate,
                tax_enabled=config.tax_enabled
            )
            for config in pricing_configs
        ]
        
        # Create calculation example
        example_variables = ["ambient_temp(K)", "ghi(W/m2)"]
        example_locations = 2
        cost_per_variable_per_location = 1.0
        total_cost = len(example_variables) * example_locations * cost_per_variable_per_location
        tax_rate = 18.0
        tax_amount = total_cost * tax_rate / 100
        final_amount = total_cost + tax_amount
        
        calculation_example = {
            "variables": example_variables,
            "locations": example_locations,
            "cost_per_variable_per_location": cost_per_variable_per_location,
            "total_cost": total_cost,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "final_amount": final_amount,
            "currency": "INR"
        }
        
        return PricingResponse(
            pricing=pricing_info,
            calculation_example=calculation_example
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pricing information: {str(e)}"
        )

@router.get("/usage/stats", response_model=WeatherUsageStatsResponse)
async def get_weather_usage_stats(
    limit: int = 10,
    db: Session = Depends(get_db),
    auth_data: tuple = Depends(get_api_key_user)
):
    """
    Get weather API usage statistics for the authenticated user
    
    Returns comprehensive usage statistics including:
    - Total requests and costs
    - Variable and endpoint usage breakdown
    - Success rates and response times
    - Recent request history
    """
    user, api_key, subscription = auth_data
    
    try:
        # Get user's weather requests
        weather_requests = db.query(WeatherRequest).filter(
            WeatherRequest.user_id == user.id
        ).all()
        
        if not weather_requests:
            return WeatherUsageStatsResponse(
                total_requests=0,
                total_cost=0.0,
                currency="INR",
                variables_used={},
                endpoints_used={},
                locations_queried=0,
                average_response_time=0.0,
                success_rate=0.0,
                recent_requests=[]
            )
        
        # Calculate statistics
        total_requests = len(weather_requests)
        total_cost = sum(req.final_amount for req in weather_requests)
        currency = weather_requests[0].currency if weather_requests else "INR"
        
        # Variables usage
        variables_used = {}
        for req in weather_requests:
            variables = json.loads(req.variables)
            for var in variables:
                variables_used[var] = variables_used.get(var, 0) + 1
        
        # Endpoints usage
        endpoints_used = {}
        for req in weather_requests:
            if req.endpoints_called:
                endpoints = json.loads(req.endpoints_called)
                for endpoint in endpoints:
                    endpoints_used[endpoint] = endpoints_used.get(endpoint, 0) + 1
        
        # Locations queried
        locations_queried = 0
        for req in weather_requests:
            locations = json.loads(req.locations)
            locations_queried += len(locations)
        
        # Average response time
        avg_response_time = sum(req.response_time for req in weather_requests) / total_requests
        
        # Success rate
        successful_requests = sum(1 for req in weather_requests if req.success)
        success_rate = (successful_requests / total_requests) * 100
        
        # Recent requests
        recent_requests = sorted(weather_requests, key=lambda x: x.created_at, reverse=True)[:limit]
        recent_logs = []
        
        for req in recent_requests:
            log = WeatherRequestLog(
                id=req.id,
                user_id=req.user_id,
                api_key_id=req.api_key_id,
                locations=json.loads(req.locations),
                variables=json.loads(req.variables),
                timestamp=req.timestamp,
                timezone=req.timezone,
                endpoints_called=json.loads(req.endpoints_called) if req.endpoints_called else [],
                response_status=req.response_status,
                response_time=req.response_time,
                success=req.success,
                total_cost=req.total_cost,
                currency=req.currency,
                tax_applied=req.tax_applied,
                final_amount=req.final_amount,
                ip_address=req.ip_address,
                user_agent=req.user_agent,
                country_code=req.country_code,
                created_at=req.created_at
            )
            recent_logs.append(log)
        
        return WeatherUsageStatsResponse(
            total_requests=total_requests,
            total_cost=total_cost,
            currency=currency,
            variables_used=variables_used,
            endpoints_used=endpoints_used,
            locations_queried=locations_queried,
            average_response_time=avg_response_time,
            success_rate=success_rate,
            recent_requests=recent_logs
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage statistics: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for Skycaster weather service
    """
    return {
        "status": "healthy",
        "service": "Skycaster Weather API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "omega": "https://apidelta.skycaster.in/forecast/multiple/omega",
            "nova": "https://apidelta.skycaster.in/forecast/multiple/nova",
            "arc": "https://apidelta.skycaster.in/forecast/multiple/arc"
        },
        "mock_mode": use_mock
    }

# Legacy endpoints for backward compatibility (will be deprecated)
@router.get("/endpoints", response_model=dict)
async def get_supported_endpoints():
    """
    Get list of all supported weather endpoints (Legacy)
    
    **⚠️ DEPRECATED**: This endpoint is kept for backward compatibility.
    Use `/variables` instead for comprehensive variable information.
    """
    endpoints = skycaster_service.get_supported_variables()
    return {
        "endpoints": endpoints,
        "message": "This endpoint is deprecated. Use /weather/variables for detailed information.",
        "authentication": "API Key required in X-API-Key header",
        "new_system": "Skycaster intelligent routing system"
    }