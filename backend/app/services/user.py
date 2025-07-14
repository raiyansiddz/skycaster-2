from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.user import User, UserRole
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.schemas.user import UserUpdate

class UserService:
    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def deactivate_user(db: Session, user_id: str) -> Optional[User]:
        """Deactivate user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def activate_user(db: Session, user_id: str) -> Optional[User]:
        """Activate user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def verify_user_email(db: Session, user_id: str) -> Optional[User]:
        """Verify user email"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.is_verified = True
        user.email_verification_token = None
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_with_subscription(db: Session, user_id: str) -> Optional[dict]:
        """Get user with current subscription information"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get current subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        return {
            "user": user,
            "subscription": subscription
        }
    
    @staticmethod
    def get_user_usage_stats(db: Session, user_id: str) -> dict:
        """Get user usage statistics"""
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
                UsageLog.user_id == user_id,
                func.date_trunc('month', UsageLog.created_at) == current_month
            )
        ).first()
        
        # Get all-time stats
        all_time_stats = db.query(
            func.count(UsageLog.id).label('total_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == True).label('successful_requests'),
            func.count(UsageLog.id).filter(UsageLog.success == False).label('failed_requests'),
            func.sum(UsageLog.cost).label('total_cost'),
            func.avg(UsageLog.response_time).label('avg_response_time')
        ).filter(UsageLog.user_id == user_id).first()
        
        return {
            "current_month": {
                "total_requests": month_stats.total_requests or 0,
                "successful_requests": month_stats.successful_requests or 0,
                "failed_requests": month_stats.failed_requests or 0,
                "total_cost": float(month_stats.total_cost or 0),
                "avg_response_time": float(month_stats.avg_response_time or 0)
            },
            "all_time": {
                "total_requests": all_time_stats.total_requests or 0,
                "successful_requests": all_time_stats.successful_requests or 0,
                "failed_requests": all_time_stats.failed_requests or 0,
                "total_cost": float(all_time_stats.total_cost or 0),
                "avg_response_time": float(all_time_stats.avg_response_time or 0)
            }
        }
    
    @staticmethod
    def search_users(db: Session, query: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by email or name"""
        return db.query(User).filter(
            func.lower(User.email).contains(query.lower()) |
            func.lower(User.first_name).contains(query.lower()) |
            func.lower(User.last_name).contains(query.lower())
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_admin_users(db: Session) -> List[User]:
        """Get all admin users"""
        return db.query(User).filter(User.role == UserRole.ADMIN).all()
    
    @staticmethod
    def promote_to_admin(db: Session, user_id: str) -> Optional[User]:
        """Promote user to admin"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.role = UserRole.ADMIN
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def demote_from_admin(db: Session, user_id: str) -> Optional[User]:
        """Demote admin to regular user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        user.role = UserRole.USER
        db.commit()
        db.refresh(user)
        return user