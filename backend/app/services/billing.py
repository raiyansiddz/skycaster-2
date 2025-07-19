import stripe
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger

from app.core.config import settings
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.services.subscription import SubscriptionService

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingService:
    @staticmethod
    def create_stripe_customer(user: User) -> Optional[stripe.Customer]:
        """Create a Stripe customer for a user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={
                    "user_id": user.id,
                    "platform": "skycaster"
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None
    
    @staticmethod
    def create_subscription(db: Session, user_id: str, plan: SubscriptionPlan) -> Optional[Dict[str, Any]]:
        """Create a new subscription with Stripe"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Create or get Stripe customer
            customer = BillingService.create_stripe_customer(user)
            if not customer:
                return None
            
            # Get plan info
            plan_info = settings.SUBSCRIPTION_PLANS.get(plan.value)
            if not plan_info or plan.value == "free":
                # Handle free plan
                subscription = SubscriptionService.create_subscription(db, user_id, plan)
                return {
                    "subscription": subscription,
                    "checkout_url": None,
                    "stripe_subscription_id": None
                }
            
            # Create Stripe subscription
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    'price': plan_info["stripe_price_id"],
                }],
                metadata={
                    "user_id": user_id,
                    "plan": plan.value
                }
            )
            
            # Create local subscription
            subscription = Subscription(
                user_id=user_id,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=customer.id,
                stripe_price_id=plan_info["stripe_price_id"],
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            return {
                "subscription": subscription,
                "checkout_url": None,
                "stripe_subscription_id": stripe_subscription.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe subscription: {e}")
            return None
    
    @staticmethod
    def create_checkout_session(db: Session, user_id: str, plan: SubscriptionPlan) -> Optional[str]:
        """Create a Stripe checkout session for subscription"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            plan_info = settings.SUBSCRIPTION_PLANS.get(plan.value)
            if not plan_info or plan.value == "free":
                return None
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan_info["stripe_price_id"],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://your-domain.com/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://your-domain.com/cancel',
                metadata={
                    "user_id": user_id,
                    "plan": plan.value
                }
            )
            
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None
    
    @staticmethod
    def cancel_subscription(db: Session, subscription_id: str) -> Optional[Subscription]:
        """Cancel a subscription"""
        try:
            subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
            if not subscription:
                return None
            
            # Cancel in Stripe if it exists
            if subscription.stripe_subscription_id:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            # Update local subscription
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancel_at_period_end = True
            
            db.commit()
            db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return None
    
    @staticmethod
    def handle_webhook(payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            return {
                "event_type": event['type'],
                "data": event['data']
            }
            
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return None
    
    @staticmethod
    def generate_invoice(db: Session, subscription_id: str, period_start: datetime, period_end: datetime) -> Optional[Invoice]:
        """Generate an invoice for a subscription period"""
        try:
            subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
            if not subscription:
                return None
            
            # Calculate usage and costs
            plan_info = settings.SUBSCRIPTION_PLANS.get(subscription.plan.value)
            if not plan_info:
                return None
            
            # Generate invoice number
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{subscription.user_id[:8]}"
            
            # Create invoice
            invoice = Invoice(
                user_id=subscription.user_id,
                subscription_id=subscription_id,
                invoice_number=invoice_number,
                status=InvoiceStatus.OPEN,
                subtotal=plan_info["price"],
                total=plan_info["price"],
                amount_due=plan_info["price"],
                invoice_date=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=30),
                period_start=period_start,
                period_end=period_end,
                line_items=[
                    {
                        "description": f"{plan_info['name']} Plan",
                        "quantity": 1,
                        "unit_price": plan_info["price"],
                        "total": plan_info["price"]
                    }
                ]
            )
            
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to generate invoice: {e}")
            return None
    
    @staticmethod
    def get_user_invoices(db: Session, user_id: str) -> List[Invoice]:
        """Get all invoices for a user"""
        return db.query(Invoice).filter(Invoice.user_id == user_id).all()
    
    @staticmethod
    def get_invoice(db: Session, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    @staticmethod
    def mark_invoice_paid(db: Session, invoice_id: str) -> Optional[Invoice]:
        """Mark an invoice as paid"""
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None
        
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        invoice.amount_paid = invoice.total
        invoice.amount_due = 0
        
        db.commit()
        db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    def get_billing_summary(db: Session, user_id: str) -> Dict[str, Any]:
        """Get billing summary for a user"""
        # Get current subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        # Get recent invoices
        invoices = db.query(Invoice).filter(
            Invoice.user_id == user_id
        ).order_by(Invoice.created_at.desc()).limit(5).all()
        
        # Calculate total paid
        total_paid = sum(inv.amount_paid or 0 for inv in invoices)
        
        # Get outstanding balance
        outstanding_balance = sum(inv.amount_due or 0 for inv in invoices if inv.status == InvoiceStatus.OPEN)
        
        # Convert subscription to dict if it exists
        subscription_dict = None
        if subscription:
            subscription_dict = {
                "id": subscription.id,
                "user_id": subscription.user_id,
                "plan": subscription.plan.value if subscription.plan else None,
                "status": subscription.status.value if subscription.status else None,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "created_at": subscription.created_at.isoformat() if subscription.created_at else None
            }
        
        # Convert invoices to list of dicts
        invoices_list = []
        for inv in invoices:
            invoices_list.append({
                "id": inv.id,
                "user_id": inv.user_id,
                "invoice_number": inv.invoice_number,
                "status": inv.status.value if inv.status else None,
                "subtotal": float(inv.subtotal or 0),
                "total": float(inv.total or 0),
                "amount_due": float(inv.amount_due or 0),
                "amount_paid": float(inv.amount_paid or 0),
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None
            })
        
        return {
            "current_subscription": subscription_dict,
            "recent_invoices": invoices_list,
            "total_paid": float(total_paid),
            "outstanding_balance": float(outstanding_balance),
            "next_billing_date": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None
        }
    
    @staticmethod
    def get_revenue_stats(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get revenue statistics (admin only)"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get invoices in period
        invoices = db.query(Invoice).filter(
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).all()
        
        # Calculate stats
        total_revenue = sum(inv.amount_paid for inv in invoices)
        total_outstanding = sum(inv.amount_due for inv in invoices if inv.status == InvoiceStatus.OPEN)
        
        # Revenue by plan
        from sqlalchemy import func
        plan_revenue = db.query(
            Subscription.plan,
            func.sum(Invoice.amount_paid).label('revenue')
        ).join(Invoice).filter(
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).group_by(Subscription.plan).all()
        
        return {
            "period_days": days,
            "total_revenue": total_revenue,
            "total_outstanding": total_outstanding,
            "total_invoices": len(invoices),
            "plan_revenue": [
                {"plan": stat.plan.value, "revenue": float(stat.revenue or 0)}
                for stat in plan_revenue
            ]
        }