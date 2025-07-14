from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.services.billing import BillingService
from app.schemas.invoice import InvoiceResponse

router = APIRouter()

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_user_invoices(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all invoices for current user"""
    invoices = BillingService.get_user_invoices(db, current_user.id)
    return invoices

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get specific invoice"""
    invoice = BillingService.get_invoice(db, invoice_id)
    if not invoice or invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice

@router.get("/summary", response_model=dict)
async def get_billing_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get billing summary for current user"""
    summary = BillingService.get_billing_summary(db, current_user.id)
    return summary

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe signature"
            )
        
        event = BillingService.handle_webhook(payload, signature)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload"
            )
        
        # Process different event types
        event_type = event["event_type"]
        event_data = event["data"]
        
        if event_type == "customer.subscription.created":
            # Handle subscription creation
            pass
        elif event_type == "customer.subscription.updated":
            # Handle subscription updates
            pass
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            pass
        elif event_type == "invoice.payment_succeeded":
            # Handle successful payment
            pass
        elif event_type == "invoice.payment_failed":
            # Handle failed payment
            pass
        
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )

@router.get("/payment-methods", response_model=dict)
async def get_payment_methods(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get user's payment methods"""
    # This would integrate with Stripe to get payment methods
    return {
        "payment_methods": [],
        "message": "Payment methods feature coming soon"
    }

@router.post("/payment-methods")
async def add_payment_method(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Add a new payment method"""
    # This would integrate with Stripe to add payment methods
    return {
        "message": "Payment method addition feature coming soon"
    }

@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Remove a payment method"""
    # This would integrate with Stripe to remove payment methods
    return {
        "message": "Payment method removal feature coming soon"
    }