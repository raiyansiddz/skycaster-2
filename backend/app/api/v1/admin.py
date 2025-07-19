from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import io

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User, UserRole
from app.models.subscription import Subscription
from app.models.api_key import ApiKey
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority
from app.models.usage_log import UsageLog
from app.models.invoice import Invoice
from app.models.pricing_config import PricingConfig, CurrencyConfig, VariableMapping
from app.services.user import UserService
from app.services.subscription import SubscriptionService
from app.services.api_key import ApiKeyService
from app.services.usage_log import UsageLogService
from app.services.billing import BillingService
from app.services.pricing_service import PricingService, CurrencyService, VariableService
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.subscription import SubscriptionResponse
from app.schemas.api_key import ApiKeyResponse
from app.schemas.support_ticket import SupportTicketResponse, SupportTicketUpdate, SupportTicketWithUser
from app.schemas.usage_log import UsageLogResponse
from app.schemas.invoice import InvoiceResponse
from app.schemas.pricing import (
    PricingConfigCreate, PricingConfigUpdate, PricingConfigResponse,
    CurrencyConfigCreate, CurrencyConfigUpdate, CurrencyConfigResponse,
    VariableMappingCreate, VariableMappingUpdate, VariableMappingResponse,
    BulkPricingUpdate, PricingAnalytics, RevenueAnalytics,
    PricingExportRequest, PricingImportRequest, PricingImportResult
)

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

# ============ COMPREHENSIVE PRICING MANAGEMENT ============

# Pricing Configuration Management
@router.get("/pricing/configs", response_model=List[PricingConfigResponse])
async def get_pricing_configs(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    endpoint_type: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get all pricing configurations with advanced filtering"""
    try:
        configs = PricingService.get_pricing_configs(
            db=db,
            skip=skip,
            limit=limit,
            endpoint_type=endpoint_type,
            currency=currency,
            is_active=is_active,
            search=search
        )
        return configs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pricing configurations: {str(e)}"
        )

@router.get("/pricing/configs/{config_id}", response_model=PricingConfigResponse)
async def get_pricing_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get specific pricing configuration by ID"""
    config = PricingService.get_pricing_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing configuration not found"
        )
    return config

@router.post("/pricing/configs", response_model=PricingConfigResponse)
async def create_pricing_config(
    pricing_config: PricingConfigCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create new pricing configuration"""
    try:
        config = PricingService.create_pricing_config(
            db=db,
            pricing_config=pricing_config,
            created_by=current_admin.id
        )
        return config
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating pricing configuration: {str(e)}"
        )

@router.put("/pricing/configs/{config_id}", response_model=PricingConfigResponse)
async def update_pricing_config(
    config_id: str,
    pricing_config: PricingConfigUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update pricing configuration"""
    try:
        config = PricingService.update_pricing_config(
            db=db,
            config_id=config_id,
            pricing_config=pricing_config
        )
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing configuration not found"
            )
        return config
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating pricing configuration: {str(e)}"
        )

@router.delete("/pricing/configs/{config_id}")
async def delete_pricing_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete pricing configuration"""
    try:
        success = PricingService.delete_pricing_config(db, config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing configuration not found"
            )
        return {"message": "Pricing configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting pricing configuration: {str(e)}"
        )

@router.post("/pricing/configs/bulk-update")
async def bulk_update_pricing_configs(
    bulk_update: BulkPricingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Bulk update pricing configurations"""
    try:
        result = PricingService.bulk_update_pricing(
            db=db,
            bulk_update=bulk_update,
            updated_by=current_admin.id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing bulk update: {str(e)}"
        )

# Currency Management
@router.get("/pricing/currencies", response_model=List[CurrencyConfigResponse])
async def get_currencies(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    is_active: Optional[bool] = Query(None)
):
    """Get all currency configurations"""
    try:
        currencies = CurrencyService.get_currencies(db, is_active=is_active)
        return currencies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving currencies: {str(e)}"
        )

@router.post("/pricing/currencies", response_model=CurrencyConfigResponse)
async def create_currency(
    currency: CurrencyConfigCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create new currency configuration"""
    try:
        new_currency = CurrencyService.create_currency(db, currency)
        return new_currency
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating currency: {str(e)}"
        )

@router.put("/pricing/currencies/{currency_id}", response_model=CurrencyConfigResponse)
async def update_currency(
    currency_id: str,
    currency: CurrencyConfigUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update currency configuration"""
    try:
        updated_currency = CurrencyService.update_currency(db, currency_id, currency)
        if not updated_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currency configuration not found"
            )
        return updated_currency
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating currency: {str(e)}"
        )

# Variable Mapping Management
@router.get("/pricing/variables", response_model=List[VariableMappingResponse])
async def get_variables(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    endpoint_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """Get all variable mappings"""
    try:
        variables = VariableService.get_variables(
            db, endpoint_type=endpoint_type, is_active=is_active
        )
        return variables
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving variables: {str(e)}"
        )

@router.post("/pricing/variables", response_model=VariableMappingResponse)
async def create_variable(
    variable: VariableMappingCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create new variable mapping"""
    try:
        new_variable = VariableService.create_variable(db, variable)
        return new_variable
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating variable: {str(e)}"
        )

@router.put("/pricing/variables/{variable_id}", response_model=VariableMappingResponse)
async def update_variable(
    variable_id: str,
    variable: VariableMappingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update variable mapping"""
    try:
        updated_variable = VariableService.update_variable(db, variable_id, variable)
        if not updated_variable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variable mapping not found"
            )
        return updated_variable
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating variable: {str(e)}"
        )

# Analytics and Reporting
@router.get("/pricing/analytics", response_model=PricingAnalytics)
async def get_pricing_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get comprehensive pricing analytics"""
    try:
        analytics = PricingService.get_pricing_analytics(db)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pricing analytics: {str(e)}"
        )

@router.get("/pricing/revenue-analytics", response_model=RevenueAnalytics)
async def get_revenue_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics")
):
    """Get revenue analytics for specified period"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        analytics = PricingService.get_revenue_analytics(db, start_date, end_date)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving revenue analytics: {str(e)}"
        )

# Data Export/Import
@router.post("/pricing/export")
async def export_pricing_data(
    export_request: PricingExportRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Export pricing data in specified format"""
    try:
        export_data = PricingService.export_pricing_data(db, export_request)
        
        # Determine content type and filename
        if export_request.format == "json":
            content_type = "application/json"
            filename = f"pricing_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        elif export_request.format == "csv":
            content_type = "text/csv"
            filename = f"pricing_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_request.format == "xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"pricing_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(export_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting pricing data: {str(e)}"
        )

@router.post("/pricing/import", response_model=PricingImportResult)
async def import_pricing_data(
    import_request: PricingImportRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Import pricing data from JSON/CSV format"""
    try:
        result = PricingService.import_pricing_data(
            db=db,
            import_request=import_request,
            imported_by=current_admin.id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing pricing data: {str(e)}"
        )

@router.post("/pricing/import/file", response_model=PricingImportResult)
async def import_pricing_file(
    file: UploadFile = File(...),
    import_mode: str = Query("update", regex="^(create|update|replace)$"),
    validate_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Import pricing data from uploaded file (CSV, JSON, or Excel)"""
    try:
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        if file.filename.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
        elif file.filename.endswith('.csv'):
            import pandas as pd
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            data = df.to_dict('records')
        elif file.filename.endswith(('.xlsx', '.xls')):
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content))
            data = df.to_dict('records')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please use JSON, CSV, or Excel files."
            )
        
        # Create import request
        import_request = PricingImportRequest(
            data=data,
            import_mode=import_mode,
            validate_only=validate_only
        )
        
        # Process import
        result = PricingService.import_pricing_data(
            db=db,
            import_request=import_request,
            imported_by=current_admin.id
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing file: {str(e)}"
        )