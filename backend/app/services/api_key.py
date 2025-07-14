from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import secrets
import string

from app.models.api_key import ApiKey
from app.models.usage_log import UsageLog
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate

class ApiKeyService:
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"sk_{key}"
    
    @staticmethod
    def create_api_key(db: Session, user_id: str, api_key_data: ApiKeyCreate) -> ApiKey:
        """Create a new API key"""
        api_key = ApiKey(
            user_id=user_id,
            name=api_key_data.name,
            key=ApiKeyService.generate_api_key(),
            is_active=True
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key
    
    @staticmethod
    def get_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
        """Get API key by ID"""
        return db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    
    @staticmethod
    def get_api_key_by_key(db: Session, key: str) -> Optional[ApiKey]:
        """Get API key by key string"""
        return db.query(ApiKey).filter(ApiKey.key == key, ApiKey.is_active == True).first()
    
    @staticmethod
    def get_user_api_keys(db: Session, user_id: str) -> List[ApiKey]:
        """Get all API keys for a user"""
        return db.query(ApiKey).filter(ApiKey.user_id == user_id).all()
    
    @staticmethod
    def update_api_key(db: Session, api_key_id: str, api_key_update: ApiKeyUpdate) -> Optional[ApiKey]:
        """Update API key"""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            return None
        
        update_data = api_key_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(api_key, field, value)
        
        db.commit()
        db.refresh(api_key)
        return api_key
    
    @staticmethod
    def deactivate_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
        """Deactivate API key"""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            return None
        
        api_key.is_active = False
        db.commit()
        db.refresh(api_key)
        return api_key
    
    @staticmethod
    def activate_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
        """Activate API key"""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            return None
        
        api_key.is_active = True
        db.commit()
        db.refresh(api_key)
        return api_key
    
    @staticmethod
    def delete_api_key(db: Session, api_key_id: str) -> bool:
        """Delete API key"""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            return False
        
        db.delete(api_key)
        db.commit()
        return True
    
    @staticmethod
    def get_api_key_usage_stats(db: Session, api_key_id: str) -> dict:
        """Get usage statistics for an API key"""
        # Get current month usage
        current_month = func.date_trunc('month', func.now())
        
        month_stats = db.query(
            func.count(UsageLog.id).label('total_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == True).label('successful_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == False).label('failed_requests'),
            func.sum(UsageLog.cost).label('total_cost'),
            func.avg(UsageLog.response_time).label('avg_response_time')
        ).filter(
            and_(
                UsageLog.api_key_id == api_key_id,
                func.date_trunc('month', UsageLog.created_at) == current_month
            )
        ).first()
        
        # Get today's usage
        today = func.date_trunc('day', func.now())
        
        today_stats = db.query(
            func.count(UsageLog.id).label('total_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == True).label('successful_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == False).label('failed_requests')
        ).filter(
            and_(
                UsageLog.api_key_id == api_key_id,
                func.date_trunc('day', UsageLog.created_at) == today
            )
        ).first()
        
        return {
            "current_month": {
                "total_requests": month_stats.total_requests or 0,
                "successful_requests": month_stats.successful_requests or 0,
                "failed_requests": month_stats.failed_requests or 0,
                "total_cost": float(month_stats.total_cost or 0),
                "avg_response_time": float(month_stats.avg_response_time or 0)
            },
            "today": {
                "total_requests": today_stats.total_requests or 0,
                "successful_requests": today_stats.successful_requests or 0,
                "failed_requests": today_stats.failed_requests or 0
            }
        }
    
    @staticmethod
    def get_all_api_keys(db: Session, skip: int = 0, limit: int = 100) -> List[ApiKey]:
        """Get all API keys (admin only)"""
        return db.query(ApiKey).offset(skip).limit(limit).all()
    
    @staticmethod
    def regenerate_api_key(db: Session, api_key_id: str) -> Optional[ApiKey]:
        """Regenerate API key"""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            return None
        
        api_key.key = ApiKeyService.generate_api_key()
        api_key.total_requests = 0
        api_key.last_used = None
        
        db.commit()
        db.refresh(api_key)
        return api_key