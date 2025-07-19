from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"

class SubscriptionPlan(enum.Enum):
    FREE = "free"
    DEVELOPER = "developer"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    plan = Column(Enum(SubscriptionPlan, values_callable=lambda x: [e.value for e in x]), nullable=False, default=SubscriptionPlan.FREE)
    status = Column(Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Stripe details
    stripe_subscription_id = Column(String)
    stripe_customer_id = Column(String)
    stripe_price_id = Column(String)
    
    # Billing
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Usage tracking
    current_month_usage = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan})>"