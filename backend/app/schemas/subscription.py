from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.subscription import SubscriptionPlan, SubscriptionStatus

class SubscriptionBase(BaseModel):
    plan: SubscriptionPlan

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    plan: Optional[SubscriptionPlan] = None
    status: Optional[SubscriptionStatus] = None

class SubscriptionResponse(SubscriptionBase):
    id: str
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    current_month_usage: int
    cancel_at_period_end: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SubscriptionPlanInfo(BaseModel):
    name: str
    plan_key: str
    requests_per_minute: int
    requests_per_month: int
    price: float
    features: list[str]
    
class SubscriptionWithPlan(SubscriptionResponse):
    plan_info: SubscriptionPlanInfo