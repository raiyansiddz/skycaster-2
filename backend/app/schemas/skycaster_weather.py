from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class WeatherForecastRequest(BaseModel):
    """Request model for Skycaster weather forecast"""
    
    list_lat_lon: List[List[float]] = Field(
        ...,
        description="List of latitude and longitude pairs",
        example=[[28.6139, 77.2090], [19.0760, 72.8777]]
    )
    
    timestamp: str = Field(
        ...,
        description="Timestamp in YYYY-MM-DD HH:MM:SS format",
        example="2025-07-18 14:00:00"
    )
    
    variables: List[str] = Field(
        ...,
        description="List of weather variables to fetch",
        example=["ambient_temp(K)", "relative_humidity(%)", "ghi(W/m2)"]
    )
    
    timezone: str = Field(
        default="Asia/Kolkata",
        description="Timezone for timestamp formatting",
        example="Asia/Kolkata"
    )
    
    @validator('list_lat_lon')
    def validate_coordinates(cls, v):
        for coord in v:
            if len(coord) != 2:
                raise ValueError('Each coordinate must be a [latitude, longitude] pair')
            lat, lon = coord
            if not -90 <= lat <= 90:
                raise ValueError(f'Latitude {lat} must be between -90 and 90')
            if not -180 <= lon <= 180:
                raise ValueError(f'Longitude {lon} must be between -180 and 180')
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError('Timestamp must be in YYYY-MM-DD HH:MM:SS format')
        return v
    
    @validator('variables')
    def validate_variables(cls, v):
        if not v:
            raise ValueError('At least one variable must be specified')
        
        # List of all supported variables
        supported_variables = [
            # Omega endpoint
            "ambient_temp(K)", "wind_10m", "wind_100m", "relative_humidity(%)",
            # Nova endpoint
            "temperature(K)", "surface_pressure(Pa)", "cumulus_precipitation(mm)",
            "ghi(W/m2)", "ghi_farms(W/m2)", "clear_sky_ghi_farms(W/m2)", "albedo",
            # Arc endpoint
            "ct", "pc", "pcph"
        ]
        
        invalid_vars = [var for var in v if var not in supported_variables]
        if invalid_vars:
            raise ValueError(f'Unsupported variables: {invalid_vars}. Supported variables: {supported_variables}')
        
        return v

class WeatherForecastResponse(BaseModel):
    """Response model for Skycaster weather forecast"""
    
    location_data: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Weather data for each location",
        example={
            "28.6139,77.2090": {
                "ambient_temp(K)": 303.5,
                "relative_humidity(%)": 65.0,
                "ghi(W/m2)": 789.2
            }
        }
    )
    
    metadata: Dict[str, Any] = Field(
        ...,
        description="Request metadata and pricing information",
        example={
            "timestamp": "2025-07-18 14:00:00",
            "timezone": "Asia/Kolkata",
            "endpoints_called": ["omega", "nova"],
            "variables_requested": ["ambient_temp(K)", "relative_humidity(%)", "ghi(W/m2)"],
            "locations_count": 2,
            "total_cost": "6.00",
            "currency": "INR",
            "tax_applied": "Yes",
            "tax_rate": "18%",
            "tax_amount": "1.08",
            "final_amount": "7.08"
        }
    )

class VariableInfo(BaseModel):
    """Information about a weather variable"""
    
    variable_name: str = Field(..., description="Name of the variable")
    endpoint_type: str = Field(..., description="Endpoint type (omega, nova, arc)")
    description: str = Field(..., description="Description of the variable")
    unit: str = Field(..., description="Unit of measurement")
    data_type: str = Field(..., description="Data type")

class SupportedVariablesResponse(BaseModel):
    """Response model for supported variables"""
    
    variables: List[VariableInfo] = Field(
        ...,
        description="List of supported weather variables"
    )
    
    endpoints: Dict[str, List[str]] = Field(
        ...,
        description="Variables grouped by endpoint",
        example={
            "omega": ["ambient_temp(K)", "wind_10m", "wind_100m", "relative_humidity(%)"],
            "nova": ["temperature(K)", "surface_pressure(Pa)", "cumulus_precipitation(mm)", "ghi(W/m2)", "ghi_farms(W/m2)", "clear_sky_ghi_farms(W/m2)", "albedo"],
            "arc": ["ct", "pc", "pcph"]
        }
    )

class PricingInfo(BaseModel):
    """Pricing information for a variable"""
    
    variable_name: str = Field(..., description="Name of the variable")
    endpoint_type: str = Field(..., description="Endpoint type")
    base_price: float = Field(..., description="Base price per variable per location")
    currency: str = Field(..., description="Currency code")
    tax_rate: float = Field(..., description="Tax rate percentage")
    tax_enabled: bool = Field(..., description="Whether tax is enabled")

class PricingResponse(BaseModel):
    """Response model for pricing information"""
    
    pricing: List[PricingInfo] = Field(
        ...,
        description="Pricing information for all variables"
    )
    
    calculation_example: Dict[str, Any] = Field(
        ...,
        description="Example pricing calculation",
        example={
            "variables": ["ambient_temp(K)", "ghi(W/m2)"],
            "locations": 2,
            "cost_per_variable_per_location": 1.0,
            "total_cost": 4.0,
            "tax_rate": 18.0,
            "tax_amount": 0.72,
            "final_amount": 4.72,
            "currency": "INR"
        }
    )

class WeatherRequestLog(BaseModel):
    """Model for weather request log"""
    
    id: str = Field(..., description="Request ID")
    user_id: Optional[str] = Field(None, description="User ID")
    api_key_id: Optional[str] = Field(None, description="API key ID")
    locations: List[List[float]] = Field(..., description="Requested locations")
    variables: List[str] = Field(..., description="Requested variables")
    timestamp: str = Field(..., description="Request timestamp")
    timezone: str = Field(..., description="Request timezone")
    endpoints_called: List[str] = Field(..., description="Endpoints called")
    response_status: int = Field(..., description="Response status code")
    response_time: float = Field(..., description="Response time in seconds")
    success: bool = Field(..., description="Whether request was successful")
    total_cost: float = Field(..., description="Total cost")
    currency: str = Field(..., description="Currency")
    tax_applied: float = Field(..., description="Tax amount applied")
    final_amount: float = Field(..., description="Final amount")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    country_code: Optional[str] = Field(None, description="Country code")
    created_at: datetime = Field(..., description="Request creation time")

class WeatherUsageStatsResponse(BaseModel):
    """Response model for weather usage statistics"""
    
    total_requests: int = Field(..., description="Total number of requests")
    total_cost: float = Field(..., description="Total cost")
    currency: str = Field(..., description="Currency")
    variables_used: Dict[str, int] = Field(..., description="Usage count per variable")
    endpoints_used: Dict[str, int] = Field(..., description="Usage count per endpoint")
    locations_queried: int = Field(..., description="Total locations queried")
    average_response_time: float = Field(..., description="Average response time in seconds")
    success_rate: float = Field(..., description="Success rate percentage")
    recent_requests: List[WeatherRequestLog] = Field(..., description="Recent requests")

class ErrorResponse(BaseModel):
    """Standard error response"""
    
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")