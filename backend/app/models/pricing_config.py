from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.core.database import Base

class PricingConfig(Base):
    """Model for storing dynamic pricing configuration"""
    __tablename__ = "pricing_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Pricing details
    variable_name = Column(String(100), nullable=False, unique=True)
    endpoint_type = Column(String(20), nullable=False)  # omega, nova, arc
    base_price = Column(Float, nullable=False, default=1.0)  # Base price per variable per location
    currency = Column(String(5), nullable=False, default="INR")
    
    # Tax configuration
    tax_rate = Column(Float, nullable=False, default=0.0)  # GST percentage
    tax_enabled = Column(Boolean, nullable=False, default=True)
    hsn_sac_code = Column(String(20), nullable=True)
    
    # Plan-based overrides
    free_plan_price = Column(Float, nullable=True)
    developer_plan_price = Column(Float, nullable=True)
    business_plan_price = Column(Float, nullable=True)
    enterprise_plan_price = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship("User", back_populates="pricing_configs")

class CurrencyConfig(Base):
    """Model for storing currency configuration"""
    __tablename__ = "currency_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Currency details
    currency_code = Column(String(5), nullable=False, unique=True)
    currency_symbol = Column(String(10), nullable=False)
    currency_name = Column(String(50), nullable=False)
    
    # Country mapping
    country_codes = Column(Text, nullable=True)  # JSON array of country codes
    
    # Exchange rate (base currency INR)
    exchange_rate = Column(Float, nullable=False, default=1.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VariableMapping(Base):
    """Model for storing variable to endpoint mapping"""
    __tablename__ = "variable_mapping"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Variable details
    variable_name = Column(String(100), nullable=False, unique=True)
    endpoint_type = Column(String(20), nullable=False)  # omega, nova, arc
    endpoint_url = Column(String(200), nullable=False)
    
    # Variable metadata
    description = Column(Text, nullable=True)
    unit = Column(String(20), nullable=True)
    data_type = Column(String(20), nullable=False, default="float")
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WeatherRequest(Base):
    """Model for storing weather request logs with new Skycaster system"""
    __tablename__ = "weather_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request details
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    
    # Request parameters
    locations = Column(Text, nullable=False)  # JSON array of [lat, lon] pairs
    variables = Column(Text, nullable=False)  # JSON array of variable names
    timestamp = Column(String(50), nullable=False)
    timezone = Column(String(50), nullable=False, default="Asia/Kolkata")
    
    # Response details
    endpoints_called = Column(Text, nullable=True)  # JSON array of endpoints called
    response_status = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False)
    
    # Pricing details
    total_cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String(5), nullable=False, default="INR")
    tax_applied = Column(Float, nullable=False, default=0.0)
    final_amount = Column(Float, nullable=False, default=0.0)
    
    # Request metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    country_code = Column(String(5), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="weather_requests")
    api_key = relationship("ApiKey", back_populates="weather_requests")