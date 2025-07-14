import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from loguru import logger
from jinja2 import Template

from app.core.config import settings

class EmailService:
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = to_email
            
            # Add text part
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user_email: str, user_name: str) -> bool:
        """Send welcome email to new user"""
        subject = "Welcome to SKYCASTER Weather API!"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Welcome to SKYCASTER, {{ user_name }}!</h2>
            <p>Thank you for signing up for our Weather API service.</p>
            
            <h3>Getting Started:</h3>
            <ol>
                <li>Verify your email address</li>
                <li>Generate your API key</li>
                <li>Start making weather API calls</li>
            </ol>
            
            <h3>Your Free Plan Includes:</h3>
            <ul>
                <li>5,000 API calls per month</li>
                <li>60 requests per minute</li>
                <li>Access to all weather endpoints</li>
                <li>Community support</li>
            </ul>
            
            <p>Visit our documentation at <a href="https://docs.skycaster.com">docs.skycaster.com</a> to get started.</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(user_name=user_name)
        
        return EmailService.send_email(user_email, subject, html_content)
    
    @staticmethod
    def send_password_reset_email(user_email: str, reset_token: str) -> bool:
        """Send password reset email"""
        subject = "Reset Your SKYCASTER Password"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password for your SKYCASTER account.</p>
            
            <p>Click the link below to reset your password:</p>
            <p><a href="https://skycaster.com/reset-password?token={{ reset_token }}">Reset Password</a></p>
            
            <p>This link will expire in 1 hour.</p>
            
            <p>If you didn't request this, please ignore this email.</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(reset_token=reset_token)
        
        return EmailService.send_email(user_email, subject, html_content)
    
    @staticmethod
    def send_email_verification(user_email: str, verification_token: str) -> bool:
        """Send email verification"""
        subject = "Verify Your SKYCASTER Email"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Verify Your Email Address</h2>
            <p>Please verify your email address to complete your SKYCASTER registration.</p>
            
            <p>Click the link below to verify your email:</p>
            <p><a href="https://skycaster.com/verify-email?token={{ verification_token }}">Verify Email</a></p>
            
            <p>This link will expire in 24 hours.</p>
            
            <p>If you didn't create this account, please ignore this email.</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(verification_token=verification_token)
        
        return EmailService.send_email(user_email, subject, html_content)
    
    @staticmethod
    def send_usage_alert(user_email: str, user_name: str, usage_percent: float, plan_name: str) -> bool:
        """Send usage alert email"""
        subject = f"SKYCASTER Usage Alert - {usage_percent}% of quota used"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Usage Alert</h2>
            <p>Hi {{ user_name }},</p>
            
            <p>You have used {{ usage_percent }}% of your monthly API quota on your {{ plan_name }} plan.</p>
            
            <p>To avoid service interruption, consider:</p>
            <ul>
                <li>Optimizing your API usage</li>
                <li>Upgrading to a higher plan</li>
                <li>Implementing caching</li>
            </ul>
            
            <p>Visit your dashboard to monitor usage and manage your plan.</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            user_name=user_name,
            usage_percent=usage_percent,
            plan_name=plan_name
        )
        
        return EmailService.send_email(user_email, subject, html_content)
    
    @staticmethod
    def send_invoice_email(user_email: str, user_name: str, invoice_number: str, amount: float) -> bool:
        """Send invoice email"""
        subject = f"Invoice {invoice_number} - SKYCASTER"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Invoice {{ invoice_number }}</h2>
            <p>Hi {{ user_name }},</p>
            
            <p>Your invoice for SKYCASTER services is ready.</p>
            
            <p><strong>Amount: ${{ amount }}</strong></p>
            
            <p>You can view and pay your invoice in your dashboard.</p>
            
            <p>Thank you for using SKYCASTER!</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            user_name=user_name,
            invoice_number=invoice_number,
            amount=amount
        )
        
        return EmailService.send_email(user_email, subject, html_content)
    
    @staticmethod
    def send_subscription_cancelled_email(user_email: str, user_name: str, plan_name: str) -> bool:
        """Send subscription cancelled email"""
        subject = "Subscription Cancelled - SKYCASTER"
        
        html_template = """
        <html>
        <head></head>
        <body>
            <h2>Subscription Cancelled</h2>
            <p>Hi {{ user_name }},</p>
            
            <p>Your {{ plan_name }} subscription has been cancelled.</p>
            
            <p>You'll continue to have access until the end of your current billing period.</p>
            
            <p>We're sorry to see you go. If you change your mind, you can reactivate your subscription at any time.</p>
            
            <p>Best regards,<br>The SKYCASTER Team</p>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            user_name=user_name,
            plan_name=plan_name
        )
        
        return EmailService.send_email(user_email, subject, html_content)