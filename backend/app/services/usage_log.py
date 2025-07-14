from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta

from app.models.usage_log import UsageLog
from app.schemas.usage_log import UsageLogCreate

class UsageLogService:
    @staticmethod
    def create_usage_log(db: Session, usage_data: UsageLogCreate, user_id: str, api_key_id: str) -> UsageLog:
        """Create a new usage log entry"""
        usage_log = UsageLog(
            user_id=user_id,
            api_key_id=api_key_id,
            **usage_data.dict()
        )
        
        db.add(usage_log)
        db.commit()
        db.refresh(usage_log)
        return usage_log
    
    @staticmethod
    def get_usage_log(db: Session, log_id: str) -> Optional[UsageLog]:
        """Get usage log by ID"""
        return db.query(UsageLog).filter(UsageLog.id == log_id).first()
    
    @staticmethod
    def get_user_usage_logs(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[UsageLog]:
        """Get usage logs for a user"""
        return db.query(UsageLog).filter(
            UsageLog.user_id == user_id
        ).order_by(desc(UsageLog.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_api_key_usage_logs(db: Session, api_key_id: str, skip: int = 0, limit: int = 100) -> List[UsageLog]:
        """Get usage logs for an API key"""
        return db.query(UsageLog).filter(
            UsageLog.api_key_id == api_key_id
        ).order_by(desc(UsageLog.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_usage_stats(db: Session, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        base_query = db.query(UsageLog).filter(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
        )
        
        # Total stats
        total_requests = base_query.count()
        successful_requests = base_query.filter(UsageLog.success == True).count()
        failed_requests = base_query.filter(UsageLog.success == False).count()
        
        # Cost and response time stats
        cost_sum = base_query.with_entities(func.sum(UsageLog.cost)).scalar() or 0
        avg_response_time = base_query.with_entities(func.avg(UsageLog.response_time)).scalar() or 0
        
        # Endpoint usage
        endpoint_stats = db.query(
            UsageLog.endpoint,
            func.count(UsageLog.id).label('count')
        ).filter(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
        ).group_by(UsageLog.endpoint).all()
        
        # Location usage
        location_stats = db.query(
            UsageLog.location,
            func.count(UsageLog.id).label('count')
        ).filter(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date,
                UsageLog.location != None
            )
        ).group_by(UsageLog.location).order_by(desc('count')).limit(10).all()
        
        # Daily usage (last 30 days)
        daily_stats = db.query(
            func.date_trunc('day', UsageLog.created_at).label('day'),
            func.count(UsageLog.id).label('requests'),
            func.count(UsageLog.id).filter(UsageLog.success == True).label('successful'),
            func.sum(UsageLog.cost).label('cost')
        ).filter(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
        ).group_by(func.date_trunc('day', UsageLog.created_at)).order_by('day').all()
        
        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_cost": float(cost_sum),
            "avg_response_time": float(avg_response_time),
            "endpoint_usage": [
                {"endpoint": stat.endpoint, "count": stat.count}
                for stat in endpoint_stats
            ],
            "top_locations": [
                {"location": stat.location, "count": stat.count}
                for stat in location_stats
            ],
            "daily_usage": [
                {
                    "date": stat.day.strftime('%Y-%m-%d'),
                    "requests": stat.requests,
                    "successful": stat.successful,
                    "cost": float(stat.cost or 0)
                }
                for stat in daily_stats
            ]
        }
    
    @staticmethod
    def get_system_usage_stats(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get system-wide usage statistics (admin only)"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        base_query = db.query(UsageLog).filter(
            and_(
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
        )
        
        # Total stats
        total_requests = base_query.count()
        successful_requests = base_query.filter(UsageLog.success == True).count()
        failed_requests = base_query.filter(UsageLog.success == False).count()
        unique_users = base_query.with_entities(func.count(func.distinct(UsageLog.user_id))).scalar() or 0
        
        # Cost stats
        total_cost = base_query.with_entities(func.sum(UsageLog.cost)).scalar() or 0
        avg_response_time = base_query.with_entities(func.avg(UsageLog.response_time)).scalar() or 0
        
        # Top endpoints
        top_endpoints = db.query(
            UsageLog.endpoint,
            func.count(UsageLog.id).label('count')
        ).filter(
            and_(
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
        ).group_by(UsageLog.endpoint).order_by(desc('count')).limit(10).all()
        
        # Top locations
        top_locations = db.query(
            UsageLog.location,
            func.count(UsageLog.id).label('count')
        ).filter(
            and_(
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date,
                UsageLog.location != None
            )
        ).group_by(UsageLog.location).order_by(desc('count')).limit(10).all()
        
        # Error analysis
        error_stats = db.query(
            UsageLog.response_status,
            func.count(UsageLog.id).label('count')
        ).filter(
            and_(
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date,
                UsageLog.success == False
            )
        ).group_by(UsageLog.response_status).order_by(desc('count')).all()
        
        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "unique_users": unique_users,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_cost": float(total_cost),
            "avg_response_time": float(avg_response_time),
            "top_endpoints": [
                {"endpoint": stat.endpoint, "count": stat.count}
                for stat in top_endpoints
            ],
            "top_locations": [
                {"location": stat.location, "count": stat.count}
                for stat in top_locations
            ],
            "error_analysis": [
                {"status_code": stat.response_status, "count": stat.count}
                for stat in error_stats
            ]
        }
    
    @staticmethod
    def get_all_usage_logs(db: Session, skip: int = 0, limit: int = 100) -> List[UsageLog]:
        """Get all usage logs (admin only)"""
        return db.query(UsageLog).order_by(desc(UsageLog.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def delete_old_logs(db: Session, days: int = 90) -> int:
        """Delete usage logs older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = db.query(UsageLog).filter(
            UsageLog.created_at < cutoff_date
        ).delete()
        
        db.commit()
        return deleted_count