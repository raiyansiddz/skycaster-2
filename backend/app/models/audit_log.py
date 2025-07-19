"""
Advanced Audit Logging Models for comprehensive activity tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.models import Base


class AuditLog(Base):
    """
    Comprehensive audit log for all system activities
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request Information
    request_id = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(500), nullable=False, index=True)
    full_url = Column(Text)
    
    # User Context
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    api_key_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Request Details
    request_headers = Column(JSON, nullable=True)
    request_body = Column(Text, nullable=True)
    request_params = Column(JSON, nullable=True)
    request_size = Column(Integer, default=0)
    
    # Response Details
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(Text, nullable=True)
    response_size = Column(Integer, default=0)
    
    # Performance Metrics
    processing_time_ms = Column(Float, nullable=True)
    database_query_count = Column(Integer, default=0)
    database_query_time_ms = Column(Float, default=0.0)
    
    # Network Information
    client_ip = Column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    
    # Geographic Information
    country = Column(String(2), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Authentication & Security
    auth_method = Column(String(50), nullable=True)  # jwt, api_key, none
    auth_success = Column(Boolean, nullable=True)
    rate_limit_applied = Column(Boolean, default=False)
    rate_limit_remaining = Column(Integer, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Classification
    log_level = Column(String(20), default="INFO", index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    activity_type = Column(String(50), nullable=True, index=True)  # auth, api_call, admin, billing, etc.
    
    # Additional Context
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags for categorization
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, method={self.method}, endpoint={self.endpoint}, user_id={self.user_id}, timestamp={self.timestamp})>"


class SecurityEvent(Base):
    """
    Security-specific events and incidents
    """
    __tablename__ = "security_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event Classification
    event_type = Column(String(100), nullable=False, index=True)  # login_failure, rate_limit_exceeded, etc.
    severity = Column(String(20), default="LOW", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    
    # User Context
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    attempted_email = Column(String(255), nullable=True, index=True)  # For failed logins
    
    # Request Context
    request_id = Column(String(255), nullable=True, index=True)
    client_ip = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(500), nullable=True)
    
    # Event Details
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Response Actions
    action_taken = Column(String(100), nullable=True)  # blocked, flagged, allowed, etc.
    automatic_response = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, event_type={self.event_type}, severity={self.severity}, timestamp={self.timestamp})>"


class UserActivity(Base):
    """
    User activity tracking for analytics and behavior analysis
    """
    __tablename__ = "user_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Context
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Activity Details
    activity_type = Column(String(100), nullable=False, index=True)  # login, api_call, subscription_change, etc.
    activity_name = Column(String(255), nullable=False)
    activity_description = Column(Text, nullable=True)
    
    # Context
    endpoint = Column(String(500), nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    
    # Metadata
    activity_data = Column(JSON, nullable=True)
    
    # Performance
    duration_ms = Column(Float, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Success/Failure
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, activity_type={self.activity_type}, timestamp={self.timestamp})>"


class PerformanceMetric(Base):
    """
    System performance tracking
    """
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric Classification
    metric_type = Column(String(100), nullable=False, index=True)  # api_response_time, db_query_time, etc.
    metric_name = Column(String(255), nullable=False, index=True)
    
    # Values
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)  # ms, seconds, count, bytes, etc.
    
    # Context
    endpoint = Column(String(500), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    request_id = Column(String(255), nullable=True, index=True)
    
    # Additional Data
    metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<PerformanceMetric(id={self.id}, metric_type={self.metric_type}, value={self.value}, unit={self.unit}, timestamp={self.timestamp})>"