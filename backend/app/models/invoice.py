from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class InvoiceStatus(enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(String, ForeignKey("subscriptions.id"))
    
    # Invoice details
    invoice_number = Column(String, unique=True, nullable=False)
    status = Column(Enum(InvoiceStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=InvoiceStatus.DRAFT)
    
    # Stripe details
    stripe_invoice_id = Column(String)
    stripe_payment_intent_id = Column(String)
    
    # Amounts (in cents)
    subtotal = Column(Integer, nullable=False)
    tax = Column(Integer, default=0)
    total = Column(Integer, nullable=False)
    amount_paid = Column(Integer, default=0)
    amount_due = Column(Integer, nullable=False)
    
    # Dates
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True))
    
    # Billing period
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    # Line items
    line_items = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, user_id={self.user_id})>"