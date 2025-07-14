from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.services.subscription import SubscriptionService
from app.services.billing import BillingService
from app.schemas.subscription import SubscriptionResponse, SubscriptionPlanInfo
from app.models.subscription import SubscriptionPlan

router = APIRouter()

@router.get("/plans", response_model=List[SubscriptionPlanInfo])
async def get_subscription_plans():
    """Get all available subscription plans"""
    plans = SubscriptionService.get_all_plans()
    return plans

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get current user's subscription"""
    subscription = SubscriptionService.get_user_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    return subscription

@router.post("/subscribe/{plan}")
async def subscribe_to_plan(
    plan: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Subscribe to a plan"""
    try:
        subscription_plan = SubscriptionPlan(plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription plan"
        )
    
    if subscription_plan == SubscriptionPlan.FREE:
        # Direct subscription to free plan
        subscription = SubscriptionService.create_subscription(db, current_user.id, subscription_plan)
        return {
            "message": "Subscribed to free plan successfully",
            "subscription": subscription,
            "checkout_url": None
        }
    else:
        # Create Stripe checkout session for paid plans
        checkout_url = BillingService.create_checkout_session(db, current_user.id, subscription_plan)
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create checkout session"
            )
        
        return {
            "message": "Checkout session created",
            "checkout_url": checkout_url,
            "subscription": None
        }

@router.post("/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Cancel current subscription"""
    subscription = SubscriptionService.get_user_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    cancelled_subscription = BillingService.cancel_subscription(db, subscription.id)
    if not cancelled_subscription:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )
    
    return {
        "message": "Subscription cancelled successfully",
        "subscription": cancelled_subscription
    }

@router.get("/usage", response_model=dict)
async def get_subscription_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get current subscription usage"""
    subscription = SubscriptionService.get_user_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    limits = SubscriptionService.get_plan_limits(subscription.plan)
    
    return {
        "subscription_id": subscription.id,
        "plan": subscription.plan.value,
        "current_usage": subscription.current_month_usage,
        "monthly_limit": limits["requests_per_month"],
        "minute_limit": limits["requests_per_minute"],
        "usage_percentage": (subscription.current_month_usage / limits["requests_per_month"]) * 100,
        "period_start": subscription.current_period_start,
        "period_end": subscription.current_period_end
    }

@router.post("/upgrade/{plan}")
async def upgrade_subscription(
    plan: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Upgrade subscription to a higher plan"""
    try:
        new_plan = SubscriptionPlan(plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription plan"
        )
    
    current_subscription = SubscriptionService.get_user_subscription(db, current_user.id)
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Create checkout session for upgrade
    checkout_url = BillingService.create_checkout_session(db, current_user.id, new_plan)
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )
    
    return {
        "message": "Upgrade checkout session created",
        "checkout_url": checkout_url,
        "current_plan": current_subscription.plan.value,
        "new_plan": new_plan.value
    }

@router.post("/downgrade/{plan}")
async def downgrade_subscription(
    plan: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Downgrade subscription to a lower plan"""
    try:
        new_plan = SubscriptionPlan(plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription plan"
        )
    
    current_subscription = SubscriptionService.get_user_subscription(db, current_user.id)
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    if new_plan == SubscriptionPlan.FREE:
        # Direct downgrade to free plan
        subscription = SubscriptionService.create_subscription(db, current_user.id, new_plan)
        return {
            "message": "Downgraded to free plan successfully",
            "subscription": subscription
        }
    else:
        # Create checkout session for paid downgrade
        checkout_url = BillingService.create_checkout_session(db, current_user.id, new_plan)
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create checkout session"
            )
        
        return {
            "message": "Downgrade checkout session created",
            "checkout_url": checkout_url,
            "current_plan": current_subscription.plan.value,
            "new_plan": new_plan.value
        }