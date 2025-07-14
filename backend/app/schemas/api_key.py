from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApiKeyBase(BaseModel):
    name: str

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class ApiKeyResponse(ApiKeyBase):
    id: str
    key: str
    is_active: bool
    total_requests: int
    last_used: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApiKeyWithUsage(ApiKeyResponse):
    daily_requests: int
    monthly_requests: int
    success_rate: float