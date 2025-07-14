from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.invoice import InvoiceStatus

class InvoiceBase(BaseModel):
    subtotal: int
    tax: int
    total: int

class InvoiceCreate(InvoiceBase):
    user_id: str
    subscription_id: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    line_items: Optional[List[Dict[str, Any]]] = None

class InvoiceResponse(InvoiceBase):
    id: str
    invoice_number: str
    status: InvoiceStatus
    amount_paid: int
    amount_due: int
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class InvoiceWithUser(InvoiceResponse):
    user_email: str
    user_name: Optional[str] = None