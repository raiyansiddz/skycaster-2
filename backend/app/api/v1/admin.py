from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User, UserRole
from app.models.subscription import Subscription
from app.models.api_key import ApiKey
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority
from app.models.usage_log import UsageLog
from app.models.invoice import Invoice
from app.services.user import UserService
from app.services.subscription import SubscriptionService
from app.services.api_key import ApiKeyService
from app.services.usage_log import UsageLogService
from app.services.billing import BillingService
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.subscription import SubscriptionResponse
from app.schemas.api_key import ApiKeyResponse
from app.schemas.support_ticket import SupportTicketResponse, SupportTicketUpdate, SupportTicketWithUser
from app.schemas.usage_log import UsageLogResponse
from app.schemas.invoice import InvoiceResponse

router = APIRouter()

# Dashboard Analytics
@router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get dashboard statistics for admin"""
    
    # User statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
    
    # Subscription statistics
    total_subscriptions = db.query(Subscription).count()
    active_subscriptions = db.query(Subscription).filter(Subscription.is_active == True).count()
    
    # API Key statistics
    total_api_keys = db.query(ApiKey).count()
    active_api_keys = db.query(ApiKey).filter(ApiKey.is_active == True).count()
    
    # Support ticket statistics
    total_tickets = db.query(SupportTicket).count()
    open_tickets = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.OPEN).count()
    resolved_tickets = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.RESOLVED).count()
    
    # Usage statistics (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_usage = db.query(UsageLog).filter(UsageLog.timestamp >= thirty_days_ago).count()
    
    # Revenue statistics
    total_revenue = db.query(Invoice).filter(Invoice.status == "paid").with_entities(
        db.func.sum(Invoice.amount)
    ).scalar() or 0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "admins": admin_users
        },
        "subscriptions": {
            "total": total_subscriptions,
            "active": active_subscriptions
        },
        "api_keys": {
            "total": total_api_keys,
            "active": active_api_keys
        },
        "support_tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "resolved": resolved_tickets
        },
        "usage": {
            "last_30_days": recent_usage
        },
        "revenue": {
            "total": float(total_revenue)
        }
    }

# User Management
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None)
):
    """Get all users with filtering and pagination"""
    
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.company.ilike(f"%{search}%"))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    
    # Order by creation date (newest first)
    query = query.order_by(User.created_at.desc())
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user information"""
    updated_user = UserService.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

@router.post("/users/{user_id}/promote")
async def promote_user_to_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Promote user to admin"""
    user = UserService.promote_to_admin(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User promoted to admin successfully"}

@router.post("/users/{user_id}/demote")
async def demote_admin_to_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Demote admin to regular user"""
    user = UserService.demote_from_admin(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "Admin demoted to user successfully"}

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Activate user account"""
    user = UserService.activate_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User activated successfully"}

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Deactivate user account"""
    user = UserService.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deactivated successfully"}

# Subscription Management
@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    plan_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """Get all subscriptions with filtering and pagination"""
    
    query = db.query(Subscription)
    
    # Apply filters
    if plan_type:
        query = query.filter(Subscription.plan_type == plan_type)
    
    if is_active is not None:
        query = query.filter(Subscription.is_active == is_active)
    
    # Order by creation date (newest first)
    query = query.order_by(Subscription.created_at.desc())
    
    # Apply pagination
    subscriptions = query.offset(skip).limit(limit).all()
    
    return subscriptions

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription_by_id(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get subscription by ID"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription

# API Key Management
@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def get_all_api_keys(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    user_id: Optional[str] = Query(None)
):
    """Get all API keys with filtering and pagination"""
    
    query = db.query(ApiKey)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(ApiKey.is_active == is_active)
    
    if user_id:
        query = query.filter(ApiKey.user_id == user_id)
    
    # Order by creation date (newest first)
    query = query.order_by(ApiKey.created_at.desc())
    
    # Apply pagination
    api_keys = query.offset(skip).limit(limit).all()
    
    return api_keys

@router.post("/api-keys/{api_key_id}/activate")
async def activate_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Activate API key"""
    api_key = ApiKeyService.activate_api_key(db, api_key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    return {"message": "API key activated successfully"}

@router.post("/api-keys/{api_key_id}/deactivate")
async def deactivate_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Deactivate API key"""
    api_key = ApiKeyService.deactivate_api_key(db, api_key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    return {"message": "API key deactivated successfully"}

# Support Ticket Management
@router.get("/support-tickets", response_model=List[SupportTicketWithUser])
async def get_all_support_tickets(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    assigned_to: Optional[str] = Query(None)
):
    """Get all support tickets with filtering and pagination"""
    
    query = db.query(SupportTicket).join(User, SupportTicket.user_id == User.id)
    
    # Apply filters
    if status:
        query = query.filter(SupportTicket.status == status)
    
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    
    if assigned_to:
        query = query.filter(SupportTicket.assigned_to == assigned_to)
    
    # Order by creation date (newest first)
    query = query.order_by(SupportTicket.created_at.desc())
    
    # Apply pagination
    tickets = query.offset(skip).limit(limit).all()
    
    # Convert to response format with user info
    ticket_responses = []
    for ticket in tickets:
        user = db.query(User).filter(User.id == ticket.user_id).first()
        ticket_response = SupportTicketWithUser(
            **ticket.__dict__,
            user_email=user.email,
            user_name=f"{user.first_name} {user.last_name}".strip() if user.first_name else None
        )
        ticket_responses.append(ticket_response)
    
    return ticket_responses

@router.get("/support-tickets/{ticket_id}", response_model=SupportTicketWithUser)
async def get_support_ticket_by_id(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get support ticket by ID"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    user = db.query(User).filter(User.id == ticket.user_id).first()
    ticket_response = SupportTicketWithUser(
        **ticket.__dict__,
        user_email=user.email,
        user_name=f"{user.first_name} {user.last_name}".strip() if user.first_name else None
    )
    
    return ticket_response

@router.put("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: str,
    ticket_update: SupportTicketUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update support ticket"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Update ticket fields
    update_data = ticket_update.dict(exclude_unset=True)
    
    # If resolving ticket, set resolved_at timestamp
    if update_data.get("status") == TicketStatus.RESOLVED and ticket.status != TicketStatus.RESOLVED:
        update_data["resolved_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(ticket, field, value)
    
    ticket.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.post("/support-tickets/{ticket_id}/assign")
async def assign_support_ticket(
    ticket_id: str,
    assigned_to: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Assign support ticket to admin"""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Verify assigned_to is an admin user
    assigned_user = db.query(User).filter(User.id == assigned_to, User.role == UserRole.ADMIN).first()
    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    ticket.assigned_to = assigned_to
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Support ticket assigned successfully"}

# Usage Analytics
@router.get("/usage-analytics", response_model=dict)
async def get_usage_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    days: int = Query(30, ge=1, le=365)
):
    """Get usage analytics for the specified number of days"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total requests
    total_requests = db.query(UsageLog).filter(UsageLog.timestamp >= start_date).count()
    
    # Requests by endpoint
    endpoint_stats = db.query(
        UsageLog.endpoint,
        db.func.count(UsageLog.id).label('count')
    ).filter(UsageLog.timestamp >= start_date).group_by(UsageLog.endpoint).all()
    
    # Requests by status code
    status_stats = db.query(
        UsageLog.status_code,
        db.func.count(UsageLog.id).label('count')
    ).filter(UsageLog.timestamp >= start_date).group_by(UsageLog.status_code).all()
    
    # Top users by requests
    user_stats = db.query(
        User.email,
        db.func.count(UsageLog.id).label('count')
    ).join(UsageLog, User.id == UsageLog.user_id).filter(
        UsageLog.timestamp >= start_date
    ).group_by(User.email).order_by(db.func.count(UsageLog.id).desc()).limit(10).all()
    
    return {
        "total_requests": total_requests,
        "period_days": days,
        "endpoint_stats": [{"endpoint": stat.endpoint, "count": stat.count} for stat in endpoint_stats],
        "status_stats": [{"status_code": stat.status_code, "count": stat.count} for stat in status_stats],
        "top_users": [{"email": stat.email, "count": stat.count} for stat in user_stats]
    }

# System Management
@router.get("/system/health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get system health status"""
    
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check recent error rates
    recent_errors = db.query(UsageLog).filter(
        UsageLog.timestamp >= datetime.utcnow() - timedelta(hours=1),
        UsageLog.status_code >= 400
    ).count()
    
    recent_total = db.query(UsageLog).filter(
        UsageLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
    ).count()
    
    error_rate = (recent_errors / recent_total * 100) if recent_total > 0 else 0
    
    return {
        "status": "healthy" if db_status == "healthy" and error_rate < 10 else "degraded",
        "database": db_status,
        "error_rate_1h": round(error_rate, 2),
        "timestamp": datetime.utcnow().isoformat()
    }