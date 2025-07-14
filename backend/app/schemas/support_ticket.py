from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.support_ticket import TicketStatus, TicketPriority

class SupportTicketBase(BaseModel):
    title: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM

class SupportTicketCreate(SupportTicketBase):
    pass

class SupportTicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None

class SupportTicketResponse(SupportTicketBase):
    id: str
    status: TicketStatus
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SupportTicketWithUser(SupportTicketResponse):
    user_email: str
    user_name: Optional[str] = None