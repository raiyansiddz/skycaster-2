"""
Audit Analytics API endpoints for viewing comprehensive logs
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin_user
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog, SecurityEvent, UserActivity, PerformanceMetric
from app.models.user import User

router = APIRouter()


@router.get("/audit-logs", tags=["Audit Analytics"])
async def get_audit_logs(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=1000, description="Number of logs to retrieve"),
    offset: int = Query(0, description="Offset for pagination"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    log_level: Optional[str] = Query(None, description="Filter by log level"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter")
):
    """Get comprehensive audit logs (Admin only)"""
    try:
        query = db.query(AuditLog)
        
        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if activity_type:
            query = query.filter(AuditLog.activity_type == activity_type)
        
        if log_level:
            query = query.filter(AuditLog.log_level == log_level)
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
        
        # Format response
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": str(log.id),
                "request_id": log.request_id,
                "timestamp": log.timestamp.isoformat(),
                "method": log.method,
                "endpoint": log.endpoint,
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user_email,
                "response_status_code": log.response_status_code,
                "processing_time_ms": log.processing_time_ms,
                "client_ip": log.client_ip,
                "auth_method": log.auth_method,
                "activity_type": log.activity_type,
                "log_level": log.log_level,
                "extra_metadata": log.extra_metadata,
                "tags": log.tags
            })
        
        return {
            "logs": formatted_logs,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving audit logs: {str(e)}"
        )


@router.get("/security-events", tags=["Audit Analytics"])
async def get_security_events(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=1000),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    event_type: Optional[str] = Query(None, description="Filter by event type")
):
    """Get security events (Admin only)"""
    events = AuditService.get_security_events_summary(db, limit, severity, event_type)
    return {"security_events": events, "count": len(events)}


@router.get("/user-activity", tags=["Audit Analytics"])
async def get_user_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    activity_type: Optional[str] = Query(None, description="Filter by activity type")
):
    """Get current user's activity history"""
    activities = AuditService.get_user_activity_summary(
        db, str(current_user.id), limit, activity_type
    )
    return {"activities": activities, "count": len(activities)}


@router.get("/user-activity/{user_id}", tags=["Audit Analytics"])
async def get_user_activity_by_id(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    activity_type: Optional[str] = Query(None)
):
    """Get specific user's activity history (Admin only)"""
    activities = AuditService.get_user_activity_summary(db, user_id, limit, activity_type)
    return {"user_id": user_id, "activities": activities, "count": len(activities)}


@router.get("/performance-metrics", tags=["Audit Analytics"])
async def get_performance_metrics(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, le=1000),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get system performance metrics (Admin only)"""
    try:
        query = db.query(PerformanceMetric)
        
        if metric_type:
            query = query.filter(PerformanceMetric.metric_type == metric_type)
        
        if endpoint:
            query = query.filter(PerformanceMetric.endpoint == endpoint)
        
        if start_date:
            query = query.filter(PerformanceMetric.timestamp >= start_date)
        
        if end_date:
            query = query.filter(PerformanceMetric.timestamp <= end_date)
        
        metrics = query.order_by(PerformanceMetric.timestamp.desc()).limit(limit).all()
        
        formatted_metrics = []
        for metric in metrics:
            formatted_metrics.append({
                "id": str(metric.id),
                "metric_type": metric.metric_type,
                "metric_name": metric.metric_name,
                "value": metric.value,
                "unit": metric.unit,
                "endpoint": metric.endpoint,
                "timestamp": metric.timestamp.isoformat(),
                "extra_metadata": metric.extra_metadata,
                "tags": metric.tags
            })
        
        return {"metrics": formatted_metrics, "count": len(formatted_metrics)}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving performance metrics: {str(e)}"
        )


@router.get("/analytics-dashboard", tags=["Audit Analytics"])
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze")
):
    """Get analytics dashboard data (Admin only)"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get basic statistics
        total_requests = db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date
        ).count()
        
        successful_requests = db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.response_status_code < 400
        ).count()
        
        security_incidents = db.query(SecurityEvent).filter(
            SecurityEvent.timestamp >= start_date
        ).count()
        
        high_severity_incidents = db.query(SecurityEvent).filter(
            SecurityEvent.timestamp >= start_date,
            SecurityEvent.severity.in_(["HIGH", "CRITICAL"])
        ).count()
        
        # Get average response time
        avg_response_time = db.query(
            db.func.avg(AuditLog.processing_time_ms)
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.processing_time_ms.isnot(None)
        ).scalar()
        
        # Get top endpoints
        top_endpoints = db.query(
            AuditLog.endpoint,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date
        ).group_by(AuditLog.endpoint).order_by(
            db.func.count(AuditLog.id).desc()
        ).limit(10).all()
        
        # Get top users by activity
        top_users = db.query(
            AuditLog.user_email,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.user_email.isnot(None)
        ).group_by(AuditLog.user_email).order_by(
            db.func.count(AuditLog.id).desc()
        ).limit(10).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "statistics": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                "security_incidents": security_incidents,
                "high_severity_incidents": high_severity_incidents,
                "average_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0
            },
            "top_endpoints": [
                {"endpoint": endpoint, "count": count} 
                for endpoint, count in top_endpoints
            ],
            "top_users": [
                {"user_email": user_email, "request_count": count}
                for user_email, count in top_users
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analytics dashboard: {str(e)}"
        )


@router.get("/real-time-activity", tags=["Audit Analytics"])
async def get_real_time_activity(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    minutes: int = Query(5, description="Minutes of recent activity")
):
    """Get real-time activity for monitoring (Admin only)"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Recent audit logs
        recent_logs = db.query(AuditLog).filter(
            AuditLog.timestamp >= cutoff_time
        ).order_by(AuditLog.timestamp.desc()).limit(20).all()
        
        # Recent security events
        recent_security = db.query(SecurityEvent).filter(
            SecurityEvent.timestamp >= cutoff_time
        ).order_by(SecurityEvent.timestamp.desc()).limit(10).all()
        
        # Activity by minute
        activity_by_minute = db.query(
            db.func.date_trunc('minute', AuditLog.timestamp).label('minute'),
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= cutoff_time
        ).group_by(
            db.func.date_trunc('minute', AuditLog.timestamp)
        ).order_by('minute').all()
        
        return {
            "time_window": {
                "start": cutoff_time.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "minutes": minutes
            },
            "recent_activity": [
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "method": log.method,
                    "endpoint": log.endpoint,
                    "user_email": log.user_email,
                    "status_code": log.response_status_code,
                    "client_ip": log.client_ip
                }
                for log in recent_logs
            ],
            "recent_security_events": [
                {
                    "id": str(event.id),
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "description": event.description,
                    "client_ip": event.client_ip
                }
                for event in recent_security
            ],
            "activity_timeline": [
                {
                    "minute": minute.isoformat(),
                    "request_count": count
                }
                for minute, count in activity_by_minute
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting real-time activity: {str(e)}"
        )