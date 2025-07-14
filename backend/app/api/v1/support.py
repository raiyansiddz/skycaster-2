from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.support_ticket import SupportTicket, TicketStatus, TicketPriority
from app.models.user import User
from app.services.email import EmailService
from app.schemas.support_ticket import (
    SupportTicketCreate, 
    SupportTicketResponse, 
    SupportTicketUpdate,
    SupportTicketWithUser
)
from datetime import datetime

router = APIRouter()

@router.post("/tickets", response_model=SupportTicketResponse)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new support ticket"""
    
    # Create the ticket
    ticket = SupportTicket(
        user_id=current_user.id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        status=TicketStatus.OPEN
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Send notification email to support team
    try:
        user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
        EmailService.send_support_ticket_notification(
            user_email=current_user.email,
            user_name=user_name,
            ticket_id=ticket.id,
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            priority=ticket.priority.value
        )
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send support ticket notification: {e}")
    
    return ticket

@router.get("/tickets", response_model=List[SupportTicketResponse])
async def get_user_support_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None)
):
    """Get current user's support tickets"""
    
    query = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(SupportTicket.status == status)
    
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    
    # Order by creation date (newest first)
    query = query.order_by(SupportTicket.created_at.desc())
    
    # Apply pagination
    tickets = query.offset(skip).limit(limit).all()
    
    return tickets

@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific support ticket"""
    
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == current_user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    return ticket

@router.put("/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: str,
    ticket_update: SupportTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a support ticket (users can only update title, description, and priority)"""
    
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == current_user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Users can only update certain fields
    allowed_fields = ['title', 'description', 'priority']
    update_data = ticket_update.dict(exclude_unset=True, include=set(allowed_fields))
    
    # Update ticket fields
    for field, value in update_data.items():
        setattr(ticket, field, value)
    
    ticket.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.post("/tickets/{ticket_id}/close")
async def close_support_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Close a support ticket"""
    
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == current_user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Only allow closing if ticket is not already closed
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket is already closed"
        )
    
    ticket.status = TicketStatus.CLOSED
    ticket.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Support ticket closed successfully"}

@router.post("/tickets/{ticket_id}/reopen")
async def reopen_support_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reopen a closed support ticket"""
    
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == current_user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Only allow reopening if ticket is closed or resolved
    if ticket.status not in [TicketStatus.CLOSED, TicketStatus.RESOLVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket can only be reopened if it's closed or resolved"
        )
    
    ticket.status = TicketStatus.OPEN
    ticket.updated_at = datetime.utcnow()
    ticket.resolved_at = None
    
    db.commit()
    
    return {"message": "Support ticket reopened successfully"}

@router.get("/tickets/{ticket_id}/history", response_model=List[dict])
async def get_support_ticket_history(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get support ticket history/timeline"""
    
    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.user_id == current_user.id
    ).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Build history timeline
    history = []
    
    # Ticket creation
    history.append({
        "action": "created",
        "timestamp": ticket.created_at,
        "details": f"Ticket created with priority: {ticket.priority.value}"
    })
    
    # Status changes (simplified - in a real app you'd have an audit log)
    if ticket.status == TicketStatus.IN_PROGRESS:
        history.append({
            "action": "status_changed",
            "timestamp": ticket.updated_at,
            "details": "Status changed to: In Progress"
        })
    
    if ticket.status == TicketStatus.RESOLVED:
        history.append({
            "action": "resolved",
            "timestamp": ticket.resolved_at,
            "details": "Ticket resolved"
        })
    
    if ticket.status == TicketStatus.CLOSED:
        history.append({
            "action": "closed",
            "timestamp": ticket.updated_at,
            "details": "Ticket closed"
        })
    
    # Sort by timestamp
    history.sort(key=lambda x: x["timestamp"])
    
    return history

@router.get("/stats", response_model=dict)
async def get_user_support_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's support ticket statistics"""
    
    # Count tickets by status
    total_tickets = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id).count()
    
    open_tickets = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.status == TicketStatus.OPEN
    ).count()
    
    in_progress_tickets = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.status == TicketStatus.IN_PROGRESS
    ).count()
    
    resolved_tickets = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.status == TicketStatus.RESOLVED
    ).count()
    
    closed_tickets = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.status == TicketStatus.CLOSED
    ).count()
    
    # Count by priority
    high_priority = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.priority == TicketPriority.HIGH
    ).count()
    
    urgent_priority = db.query(SupportTicket).filter(
        SupportTicket.user_id == current_user.id,
        SupportTicket.priority == TicketPriority.URGENT
    ).count()
    
    return {
        "total_tickets": total_tickets,
        "by_status": {
            "open": open_tickets,
            "in_progress": in_progress_tickets,
            "resolved": resolved_tickets,
            "closed": closed_tickets
        },
        "by_priority": {
            "high": high_priority,
            "urgent": urgent_priority
        }
    }

@router.get("/categories", response_model=List[dict])
async def get_support_categories():
    """Get available support ticket categories"""
    
    categories = [
        {
            "id": "api_issue",
            "name": "API Issue",
            "description": "Problems with API endpoints, rate limiting, or authentication"
        },
        {
            "id": "billing",
            "name": "Billing",
            "description": "Questions about billing, invoices, or subscription changes"
        },
        {
            "id": "feature_request",
            "name": "Feature Request",
            "description": "Suggestions for new features or improvements"
        },
        {
            "id": "account",
            "name": "Account",
            "description": "Account-related issues, profile updates, or access problems"
        },
        {
            "id": "technical",
            "name": "Technical Support",
            "description": "General technical support and troubleshooting"
        },
        {
            "id": "other",
            "name": "Other",
            "description": "Any other questions or issues"
        }
    ]
    
    return categories

@router.get("/faq", response_model=List[dict])
async def get_support_faq():
    """Get frequently asked questions"""
    
    faq = [
        {
            "question": "How do I get started with the Weather API?",
            "answer": "After registering and verifying your email, you'll receive a default API key. You can then make requests to our weather endpoints using this key in the X-API-Key header."
        },
        {
            "question": "What are the rate limits?",
            "answer": "Rate limits depend on your subscription plan. Free plans have lower limits, while paid plans offer higher limits. You can check your current limits in your dashboard."
        },
        {
            "question": "How do I upgrade my subscription?",
            "answer": "Visit your dashboard and go to the Subscriptions section. You can upgrade or downgrade your plan at any time."
        },
        {
            "question": "What weather data is available?",
            "answer": "Our API provides current weather, forecasts, historical data, and weather alerts for locations worldwide."
        },
        {
            "question": "How do I report an API issue?",
            "answer": "Create a support ticket with the 'API Issue' category. Include details about the endpoint, your request, and any error messages."
        },
        {
            "question": "Can I get historical weather data?",
            "answer": "Yes, historical weather data is available for premium subscribers. Check our API documentation for available endpoints."
        }
    ]
    
    return faq