from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False)
    
    # Request details
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    request_params = Column(JSON)
    request_headers = Column(JSON)
    
    # Response details
    response_status = Column(Integer, nullable=False)
    response_size = Column(Integer)  # in bytes
    response_time = Column(Float)  # in seconds
    success = Column(Boolean, nullable=False)
    
    # Location and context
    ip_address = Column(String)
    user_agent = Column(String)
    location = Column(String)  # Weather location requested
    
    # Billing
    cost = Column(Float, default=0.0)  # Cost in credits
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("ApiKey", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<UsageLog(id={self.id}, endpoint={self.endpoint}, user_id={self.user_id})>"