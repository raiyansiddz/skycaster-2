from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.core.config import settings

class SubscriptionService:
    @staticmethod
    def get_subscription(db: Session, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID"""
        return db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    @staticmethod
    def get_user_subscription(db: Session, user_id: str) -> Optional[Subscription]:
        """Get current subscription for user"""
        return db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
    
    @staticmethod
    def create_subscription(db: Session, user_id: str, plan: SubscriptionPlan) -> Subscription:
        """Create new subscription"""
        # Deactivate existing subscriptions
        existing_subs = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        for sub in existing_subs:
            sub.status = SubscriptionStatus.CANCELLED
        
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            current_month_usage=0
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    def update_subscription(db: Session, subscription_id: str, update_data: SubscriptionUpdate) -> Optional[Subscription]:
        """Update subscription"""
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(subscription, field, value)
        
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    def cancel_subscription(db: Session, subscription_id: str) -> Optional[Subscription]:
        """Cancel subscription"""
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            return None
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancel_at_period_end = True
        
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    def get_plan_limits(plan: SubscriptionPlan) -> dict:
        """Get limits for a subscription plan"""
        return settings.RATE_LIMITS.get(plan.value, settings.RATE_LIMITS["free"])
    
    @staticmethod
    def get_plan_info(plan: SubscriptionPlan) -> dict:
        """Get detailed plan information"""
        limits = SubscriptionService.get_plan_limits(plan)
        plan_info = settings.SUBSCRIPTION_PLANS.get(plan.value, settings.SUBSCRIPTION_PLANS["free"])
        
        features = []
        if plan == SubscriptionPlan.FREE:
            features = [
                "Basic weather data access",
                "5,000 API calls/month",
                "60 calls/minute",
                "Community support"
            ]
        elif plan == SubscriptionPlan.DEVELOPER:
            features = [
                "Full weather data access",
                "50,000 API calls/month", 
                "600 calls/minute",
                "Email support",
                "Usage analytics"
            ]
        elif plan == SubscriptionPlan.BUSINESS:
            features = [
                "Full weather data access",
                "200,000 API calls/month",
                "1,800 calls/minute", 
                "Priority support",
                "Advanced analytics",
                "Custom integrations"
            ]
        elif plan == SubscriptionPlan.ENTERPRISE:
            features = [
                "Full weather data access",
                "1,000,000 API calls/month",
                "6,000 calls/minute",
                "Dedicated support",
                "Custom analytics",
                "SLA guarantee",
                "White-label options"
            ]
        
        return {
            "name": plan_info["name"],
            "plan_key": plan.value,
            "requests_per_minute": limits["requests_per_minute"],
            "requests_per_month": limits["requests_per_month"],
            "price": plan_info["price"],
            "features": features
        }
    
    @staticmethod
    def get_all_plans() -> List[dict]:
        """Get all available subscription plans"""
        return [
            SubscriptionService.get_plan_info(plan)
            for plan in SubscriptionPlan
        ]
    
    @staticmethod
    def increment_usage(db: Session, user_id: str, amount: int = 1) -> Optional[Subscription]:
        """Increment usage for user's subscription"""
        subscription = SubscriptionService.get_user_subscription(db, user_id)
        if not subscription:
            return None
        
        subscription.current_month_usage += amount
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    def reset_monthly_usage(db: Session, subscription_id: str) -> Optional[Subscription]:
        """Reset monthly usage for subscription"""
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            return None
        
        subscription.current_month_usage = 0
        subscription.current_period_start = datetime.utcnow()
        subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
        
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    def get_expired_subscriptions(db: Session) -> List[Subscription]:
        """Get subscriptions that have expired"""
        return db.query(Subscription).filter(
            Subscription.current_period_end < datetime.utcnow(),
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
    
    @staticmethod
    def get_all_subscriptions(db: Session, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """Get all subscriptions (admin only)"""
        return db.query(Subscription).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_subscription_stats(db: Session) -> dict:
        """Get subscription statistics"""
        from sqlalchemy import func
        
        stats = db.query(
            Subscription.plan,
            func.count(Subscription.id).label('count')
        ).group_by(Subscription.plan).all()
        
        plan_stats = {}
        for stat in stats:
            plan_stats[stat.plan.value] = stat.count
        
        return {
            "total_subscriptions": sum(plan_stats.values()),
            "plan_distribution": plan_stats
        }