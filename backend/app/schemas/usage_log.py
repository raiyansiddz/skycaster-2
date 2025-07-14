from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class UsageLogBase(BaseModel):
    endpoint: str
    method: str
    location: Optional[str] = None

class UsageLogCreate(UsageLogBase):
    request_params: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, Any]] = None
    response_status: int
    response_size: Optional[int] = None
    response_time: Optional[float] = None
    success: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    cost: Optional[float] = 0.0

class UsageLogResponse(UsageLogBase):
    id: str
    user_id: str
    api_key_id: str
    request_params: Optional[Dict[str, Any]] = None
    response_status: int
    response_size: Optional[int] = None
    response_time: Optional[float] = None
    success: bool
    ip_address: Optional[str] = None
    cost: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class UsageStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_cost: float
    avg_response_time: float
    unique_locations: int
    
class UsageAnalytics(BaseModel):
    today: UsageStats
    this_week: UsageStats
    this_month: UsageStats
    all_time: UsageStats