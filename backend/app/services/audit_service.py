"""
Advanced Audit Service for detailed activity logging
"""
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.models.audit_log import AuditLog, SecurityEvent, UserActivity, PerformanceMetric
from app.models.user import User
from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)


class AuditService:
    """Service for comprehensive audit logging"""
    
    @staticmethod
    def log_authentication_event(
        db: Session,
        event_type: str,  # login_success, login_failure, register_success, etc.
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        attempted_email: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log authentication-specific events with detailed context"""
        try:
            # Determine severity based on event type
            severity = "LOW"
            if "failure" in event_type or "invalid" in event_type:
                severity = "MEDIUM"
            elif "suspicious" in event_type or "blocked" in event_type:
                severity = "HIGH"
            
            # Create security event
            security_event = SecurityEvent(
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                user_email=user_email,
                attempted_email=attempted_email,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=user_agent,
                description=AuditService._get_event_description(event_type, user_email or attempted_email),
                details=additional_data or {},
                action_taken="logged" if "success" in event_type else "flagged"
            )
            
            db.add(security_event)
            
            # Also log as user activity if user is identified
            if user_id:
                user_activity = UserActivity(
                    user_id=user_id,
                    request_id=request_id,
                    activity_type="authentication",
                    activity_name=event_type,
                    activity_description=AuditService._get_event_description(event_type, user_email),
                    success="success" in event_type,
                    activity_data=additional_data or {}
                )
                db.add(user_activity)
            
            db.commit()
            logger.info(f"Authentication event logged: {event_type} for {user_email or attempted_email}")
            
        except Exception as e:
            logger.error(f"Error logging authentication event: {e}")
            db.rollback()
    
    @staticmethod
    def log_api_key_event(
        db: Session,
        event_type: str,  # api_key_created, api_key_deleted, api_key_used, etc.
        user_id: str,
        api_key_id: Optional[str] = None,
        api_key_name: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log API key management events"""
        try:
            user_activity = UserActivity(
                user_id=user_id,
                request_id=request_id,
                activity_type="api_key_management",
                activity_name=event_type,
                activity_description=f"API key {event_type.replace('_', ' ')} - {api_key_name or 'Unknown'}",
                success=True,
                activity_data={
                    "api_key_id": api_key_id,
                    "api_key_name": api_key_name,
                    "client_ip": client_ip,
                    **(additional_data or {})
                }
            )
            
            db.add(user_activity)
            db.commit()
            logger.info(f"API key event logged: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging API key event: {e}")
            db.rollback()
    
    @staticmethod
    def log_subscription_event(
        db: Session,
        event_type: str,  # subscription_created, subscription_upgraded, etc.
        user_id: str,
        subscription_plan: Optional[str] = None,
        previous_plan: Optional[str] = None,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log subscription-related events"""
        try:
            user_activity = UserActivity(
                user_id=user_id,
                request_id=request_id,
                activity_type="subscription_management",
                activity_name=event_type,
                activity_description=f"Subscription {event_type.replace('_', ' ')} - {subscription_plan}",
                success=True,
                activity_data={
                    "subscription_plan": subscription_plan,
                    "previous_plan": previous_plan,
                    "client_ip": client_ip,
                    **(additional_data or {})
                }
            )
            
            db.add(user_activity)
            db.commit()
            logger.info(f"Subscription event logged: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging subscription event: {e}")
            db.rollback()
    
    @staticmethod
    def log_weather_api_usage(
        db: Session,
        user_id: str,
        api_key_id: str,
        endpoint: str,
        variables: List[str],
        location: str,
        subscription_plan: str,
        processing_time_ms: float,
        success: bool,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log weather API usage with detailed metrics"""
        try:
            # Log user activity
            user_activity = UserActivity(
                user_id=user_id,
                request_id=request_id,
                activity_type="weather_api_usage",
                activity_name=f"Weather API - {endpoint}",
                activity_description=f"Weather data request for {location}",
                success=success,
                duration_ms=processing_time_ms,
                activity_data={
                    "api_key_id": api_key_id,
                    "endpoint": endpoint,
                    "variables": variables,
                    "location": location,
                    "subscription_plan": subscription_plan,
                    "client_ip": client_ip,
                    **(additional_data or {})
                }
            )
            
            db.add(user_activity)
            
            # Log performance metric
            performance_metric = PerformanceMetric(
                metric_type="weather_api_response_time",
                metric_name=f"Weather API - {endpoint}",
                value=processing_time_ms,
                unit="ms",
                endpoint=endpoint,
                user_id=user_id,
                request_id=request_id,
                extra_metadata={
                    "variables": variables,
                    "location": location,
                    "subscription_plan": subscription_plan,
                    "success": success
                },
                tags=["weather_api", endpoint.replace("/", "_"), subscription_plan]
            )
            
            db.add(performance_metric)
            db.commit()
            
            logger.info(f"Weather API usage logged: {endpoint} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging weather API usage: {e}")
            db.rollback()
    
    @staticmethod
    def log_security_incident(
        db: Session,
        incident_type: str,
        severity: str,  # LOW, MEDIUM, HIGH, CRITICAL
        description: str,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_id: Optional[str] = None,
        action_taken: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security incidents and suspicious activities"""
        try:
            security_event = SecurityEvent(
                event_type=incident_type,
                severity=severity,
                user_id=user_id,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=user_agent,
                endpoint=endpoint,
                description=description,
                details=additional_data or {},
                action_taken=action_taken,
                automatic_response=action_taken is not None
            )
            
            db.add(security_event)
            db.commit()
            
            logger.warning(f"Security incident logged: {incident_type} - {severity}")
            
        except Exception as e:
            logger.error(f"Error logging security incident: {e}")
            db.rollback()
    
    @staticmethod
    def get_user_activity_summary(
        db: Session,
        user_id: str,
        limit: int = 50,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user activity summary for analytics"""
        try:
            query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
            
            if activity_type:
                query = query.filter(UserActivity.activity_type == activity_type)
            
            activities = query.order_by(UserActivity.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    "id": str(activity.id),
                    "activity_type": activity.activity_type,
                    "activity_name": activity.activity_name,
                    "description": activity.activity_description,
                    "timestamp": activity.timestamp.isoformat(),
                    "success": activity.success,
                    "duration_ms": activity.duration_ms,
                    "data": activity.activity_data
                }
                for activity in activities
            ]
            
        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return []
    
    @staticmethod
    def get_security_events_summary(
        db: Session,
        limit: int = 50,
        severity: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get security events summary for monitoring"""
        try:
            query = db.query(SecurityEvent)
            
            if severity:
                query = query.filter(SecurityEvent.severity == severity)
            
            if event_type:
                query = query.filter(SecurityEvent.event_type == event_type)
            
            events = query.order_by(SecurityEvent.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "description": event.description,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "client_ip": event.client_ip,
                    "action_taken": event.action_taken,
                    "details": event.details
                }
                for event in events
            ]
            
        except Exception as e:
            logger.error(f"Error getting security events summary: {e}")
            return []
    
    @staticmethod
    def _get_event_description(event_type: str, email: Optional[str]) -> str:
        """Get human-readable description for event types"""
        descriptions = {
            "login_success": f"Successful login for {email}",
            "login_failure": f"Failed login attempt for {email}",
            "register_success": f"New user registration for {email}",
            "register_failure": f"Failed registration attempt for {email}",
            "password_reset_request": f"Password reset requested for {email}",
            "password_reset_success": f"Password successfully reset for {email}",
            "token_refresh": f"Token refresh for {email}",
            "logout": f"User logout for {email}",
            "api_key_created": f"New API key created for {email}",
            "api_key_deleted": f"API key deleted for {email}",
            "subscription_created": f"New subscription created for {email}",
            "subscription_upgraded": f"Subscription upgraded for {email}",
            "subscription_cancelled": f"Subscription cancelled for {email}"
        }
        
        return descriptions.get(event_type, f"Authentication event: {event_type} for {email}")