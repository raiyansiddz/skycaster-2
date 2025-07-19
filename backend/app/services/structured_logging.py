"""
Enhanced Logging Service for Skycaster Weather API System
Provides structured logging for API calls, authentication events, queue operations, and system metrics
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from loguru import logger

class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "debug"
    INFO = "info" 
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogCategory(Enum):
    """Log category enumeration"""
    API_CALL = "api_call"
    AUTHENTICATION = "authentication"
    TASK_EVENT = "task_event"
    SECURITY = "security"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    QUEUE = "queue"
    DATABASE = "database"
    USER_ACTIVITY = "user_activity"

@dataclass
class LogEntry:
    """Structured log entry data class"""
    timestamp: str
    level: str
    category: str
    event_type: str
    message: str
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    task_id: Optional[str] = None
    queue_name: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StructuredLogger:
    """Enhanced structured logging service"""
    
    def __init__(self):
        self.logger = logger
        self._setup_log_files()
    
    def _setup_log_files(self):
        """Setup different log files for different categories"""
        # Main application log
        self.logger.add(
            "logs/skycaster_main.log",
            rotation="10 MB",
            retention="1 week",
            compression="gz",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
        # API calls log
        self.logger.add(
            "logs/api_calls.log",
            rotation="10 MB",
            retention="1 week",
            compression="gz",
            filter=lambda record: record["extra"].get("category") == "api_call",
            format="{time:YYYY-MM-DD HH:mm:ss} | {extra[category]} | {message}"
        )
        
        # Queue events log
        self.logger.add(
            "logs/queue_events.log",
            rotation="10 MB",
            retention="1 week",
            compression="gz",
            filter=lambda record: record["extra"].get("category") in ["task_event", "queue"],
            format="{time:YYYY-MM-DD HH:mm:ss} | {extra[category]} | {message}"
        )
        
        # Security events log
        self.logger.add(
            "logs/security.log",
            rotation="10 MB",
            retention="1 week",
            compression="gz",
            filter=lambda record: record["extra"].get("category") == "security",
            format="{time:YYYY-MM-DD HH:mm:ss} | SECURITY | {message}"
        )
        
        # System metrics log
        self.logger.add(
            "logs/system_metrics.log",
            rotation="10 MB",
            retention="1 week", 
            compression="gz",
            filter=lambda record: record["extra"].get("category") == "system",
            format="{time:YYYY-MM-DD HH:mm:ss} | SYSTEM | {message}"
        )

    def log_structured(self, log_entry: LogEntry):
        """Log a structured entry"""
        extra_data = asdict(log_entry)
        
        # Convert to JSON for structured format
        log_message = json.dumps({
            "timestamp": log_entry.timestamp,
            "level": log_entry.level,
            "category": log_entry.category,
            "event_type": log_entry.event_type,
            "message": log_entry.message,
            **{k: v for k, v in extra_data.items() if v is not None and k not in ['timestamp', 'level', 'category', 'event_type', 'message']}
        })
        
        # Add category to extra for filtering
        extra = {"category": log_entry.category}
        
        # Log at appropriate level
        if log_entry.level == LogLevel.DEBUG.value:
            self.logger.bind(**extra).debug(log_message)
        elif log_entry.level == LogLevel.INFO.value:
            self.logger.bind(**extra).info(log_message)
        elif log_entry.level == LogLevel.WARNING.value:
            self.logger.bind(**extra).warning(log_message)
        elif log_entry.level == LogLevel.ERROR.value:
            self.logger.bind(**extra).error(log_message)
        elif log_entry.level == LogLevel.CRITICAL.value:
            self.logger.bind(**extra).critical(log_message)

    def log_api_call(self, endpoint: str, method: str, status_code: int, 
                     response_time: float, user_id: Optional[str] = None,
                     api_key: Optional[str] = None, error: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """Log API call events"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.ERROR.value if status_code >= 400 else LogLevel.INFO.value,
            category=LogCategory.API_CALL.value,
            event_type="api_request",
            message=f"{method} {endpoint} - {status_code}",
            user_id=user_id,
            api_key=api_key[-8:] + "..." if api_key else None,  # Mask API key
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            error=error,
            metadata=metadata
        )
        self.log_structured(log_entry)

    def log_authentication_event(self, event_type: str, user_id: Optional[str] = None,
                                email: Optional[str] = None, success: bool = True,
                                error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Log authentication events"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO.value if success else LogLevel.WARNING.value,
            category=LogCategory.AUTHENTICATION.value,
            event_type=event_type,
            message=f"Authentication {event_type} for user {email or user_id} - {'Success' if success else 'Failed'}",
            user_id=user_id,
            error=error,
            metadata={**(metadata or {}), "email": email, "success": success}
        )
        self.log_structured(log_entry)

    def log_queue_event(self, task_name: str, status: str, task_id: Optional[str] = None,
                       queue_name: str = "redis_main", user_id: Optional[str] = None,
                       api_key: Optional[str] = None, error: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log queue/task events"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.ERROR.value if status == "failed" else LogLevel.INFO.value,
            category=LogCategory.TASK_EVENT.value,
            event_type=status,
            message=f"Task {task_name} {status}",
            user_id=user_id,
            api_key=api_key[-8:] + "..." if api_key else None,
            task_id=task_id,
            queue_name=queue_name,
            error=error,
            metadata={**(metadata or {}), "task": task_name}
        )
        self.log_structured(log_entry)

    def log_security_event(self, event_type: str, user_id: Optional[str] = None,
                          api_key: Optional[str] = None, endpoint: Optional[str] = None,
                          severity: str = "medium", error: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Log security events"""
        level = LogLevel.CRITICAL.value if severity == "high" else LogLevel.WARNING.value
        
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            category=LogCategory.SECURITY.value,
            event_type=event_type,
            message=f"Security event: {event_type} - {severity} severity",
            user_id=user_id,
            api_key=api_key[-8:] + "..." if api_key else None,
            endpoint=endpoint,
            error=error,
            metadata={**(metadata or {}), "severity": severity}
        )
        self.log_structured(log_entry)

    def log_billing_event(self, event_type: str, user_id: str, amount: Optional[float] = None,
                         currency: str = "USD", success: bool = True,
                         error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Log billing events"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO.value if success else LogLevel.ERROR.value,
            category=LogCategory.BILLING.value,
            event_type=event_type,
            message=f"Billing {event_type} for user {user_id} - {amount} {currency}",
            user_id=user_id,
            error=error,
            metadata={**(metadata or {}), "amount": amount, "currency": currency, "success": success}
        )
        self.log_structured(log_entry)

    def log_rate_limit_event(self, user_id: Optional[str] = None, api_key: Optional[str] = None,
                           endpoint: Optional[str] = None, limit_type: str = "requests_per_minute",
                           limit_value: int = 0, current_usage: int = 0, blocked: bool = False,
                           metadata: Optional[Dict[str, Any]] = None):
        """Log rate limiting events"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.WARNING.value if blocked else LogLevel.INFO.value,
            category=LogCategory.RATE_LIMIT.value,
            event_type="rate_limit_check",
            message=f"Rate limit check: {current_usage}/{limit_value} {limit_type} - {'Blocked' if blocked else 'Allowed'}",
            user_id=user_id,
            api_key=api_key[-8:] + "..." if api_key else None,
            endpoint=endpoint,
            metadata={**(metadata or {}), "limit_type": limit_type, "limit_value": limit_value, "current_usage": current_usage, "blocked": blocked}
        )
        self.log_structured(log_entry)

    def log_system_metric(self, metric_name: str, metric_value: Any, metric_type: str = "gauge",
                         metadata: Optional[Dict[str, Any]] = None):
        """Log system metrics"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO.value,
            category=LogCategory.SYSTEM.value,
            event_type="metric",
            message=f"System metric: {metric_name} = {metric_value}",
            metadata={**(metadata or {}), "metric_name": metric_name, "metric_value": metric_value, "metric_type": metric_type}
        )
        self.log_structured(log_entry)

    def log_database_event(self, operation: str, table: str, duration: Optional[float] = None,
                          error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Log database operations"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.ERROR.value if error else LogLevel.DEBUG.value,
            category=LogCategory.DATABASE.value,
            event_type=operation,
            message=f"Database {operation} on {table}" + (f" ({duration:.3f}s)" if duration else ""),
            error=error,
            metadata={**(metadata or {}), "table": table, "duration": duration}
        )
        self.log_structured(log_entry)

    def log_user_activity(self, activity_type: str, user_id: str, details: str,
                         metadata: Optional[Dict[str, Any]] = None):
        """Log user activity"""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=LogLevel.INFO.value,
            category=LogCategory.USER_ACTIVITY.value,
            event_type=activity_type,
            message=f"User activity: {activity_type} - {details}",
            user_id=user_id,
            metadata=metadata
        )
        self.log_structured(log_entry)

# Global structured logger instance
structured_logger = StructuredLogger()

# Helper functions for easy access
def log_api_call(*args, **kwargs):
    structured_logger.log_api_call(*args, **kwargs)

def log_authentication_event(*args, **kwargs):
    structured_logger.log_authentication_event(*args, **kwargs)

def log_queue_event(*args, **kwargs):
    structured_logger.log_queue_event(*args, **kwargs)

def log_security_event(*args, **kwargs):
    structured_logger.log_security_event(*args, **kwargs)

def log_billing_event(*args, **kwargs):
    structured_logger.log_billing_event(*args, **kwargs)

def log_rate_limit_event(*args, **kwargs):
    structured_logger.log_rate_limit_event(*args, **kwargs)

def log_system_metric(*args, **kwargs):
    structured_logger.log_system_metric(*args, **kwargs)

def log_database_event(*args, **kwargs):
    structured_logger.log_database_event(*args, **kwargs)

def log_user_activity(*args, **kwargs):
    structured_logger.log_user_activity(*args, **kwargs)